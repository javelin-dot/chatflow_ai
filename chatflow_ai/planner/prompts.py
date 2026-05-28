# -*- coding: utf-8 -*-
"""
LLM prompts for the workflow planner.

Two design choices worth knowing:

1. The system prompt is the *contract* between us and the LLM. It spells
   out the Flow YAML conventions exhaustively because the planner output
   must parse cleanly and reference real operationIds — we can't recover
   from an LLM that invents new YAML keys.

2. The few-shot example covers the typical pattern (collect → call →
   write back response slot → call again). Multiple examples bloat the
   prompt without adding much; one solid example beats three vague ones.
"""

from __future__ import annotations

PLANNER_SYSTEM_PROMPT = """你是 ChatFlow Flow YAML 规划师。

任务：根据用户的业务描述 + 提供的 OpenAPI 接口目录，输出一份可直接执行的 Flow YAML。

## Flow YAML 格式

顶层结构：

```
flows:
  <flow_id>:
    description: <一句话说明这条 flow 做什么>
    steps:
      - id: <step_id>
        ...
        next: <next_step_id 或 end>
```

### 步骤类型（看字段判断）

- collect 步骤：收集一个槽位
  ```
  - id: ask_xxx
    collect: <slot_name>
    next: <next_step>
  ```

- action 步骤：执行一个动作
  ```
  - id: do_xxx
    action: <action_name>
    next: <next_step>
  ```

- 调用 OpenAPI 接口（最常用的 action）：
  ```
  - id: call_xxx
    action: action_call_openapi
    metadata:
      openapi:
        service: <已注册服务名>
        operation_id: <该服务的 operationId>
        parameters:               # path / query / header 参数
          <param_name>: "slot:<slot_name>"
        request_body:             # JSON 请求体字段
          <field>: "slot:<slot_name>"
        response:
          slots:                  # 把响应字段写回槽位，供后续步骤使用
            <slot_name>: "body.<json_path>"
          success_message: "已完成，{<slot_name>}"
          failure_message: "失败原因：{status_code}"
    next: <next_step>
  ```

## 槽位映射语法

- `"slot:user_id"`   从同名槽位取值
- `"const:APPROVED"` 字面常量
- `"{user_id}"`      success_message / failure_message 中的模板替换

## 响应字段路径

- `body.data.id`       JSON 响应体内的字段
- `body.list.0.name`   数组下标
- `status_code`        HTTP 状态码
- `headers.x-trace-id` 响应头

## 规划原则

1. **拆解业务描述**：把整个流程拆成多个步骤，每步通常对应一次 API 调用
2. **先 collect 再调用**：API 调用所需的必填参数，如果不能由前一步响应提供，必须先用 collect 步骤收集；slot 名建议沿用 API 参数/字段名
3. **串接上下游**：上一步响应的关键字段（如新建对象的 id）通过 `response.slots` 写入槽位，下一步用 `"slot:<name>"` 引用
4. **只用提供的服务和 operationId**：绝对不要编造接口；如果业务描述涉及目录里没有的功能，直接说明缺失并留 TODO
5. **末尾**：最后一步的 `next: end`
6. **输出纯 YAML**：不要 markdown 代码块，不要任何解释文字、注释或 ```yaml 包裹

## 示例

业务描述："为新用户开户并完成 KYC 审核通过"

接口目录：

```
# service: user (2 operations)

POST   /users :: createUser — 创建新用户
  body:*
    * name: string — 姓名
    * phone: string — 手机号

POST   /users/{id}/kyc/approve :: approveKyc — KYC 审核通过
  params:
    * id (path, string) — 用户ID
```

输出：

```
flows:
  onboard_and_approve_kyc:
    description: 为新用户开户并完成 KYC 审核通过
    steps:
      - id: ask_name
        collect: name
        next: ask_phone
      - id: ask_phone
        collect: phone
        next: do_create_user
      - id: do_create_user
        action: action_call_openapi
        metadata:
          openapi:
            service: user
            operation_id: createUser
            request_body:
              name: "slot:name"
              phone: "slot:phone"
            response:
              slots:
                user_id: "body.data.id"
              success_message: "已创建用户 {user_id}"
        next: do_approve_kyc
      - id: do_approve_kyc
        action: action_call_openapi
        metadata:
          openapi:
            service: user
            operation_id: approveKyc
            parameters:
              id: "slot:user_id"
            response:
              success_message: "KYC 审核已通过"
        next: end
```
"""


PLANNER_USER_PROMPT_TEMPLATE = """# 已注册的接口目录

{catalog}

# 业务描述

{description}

请直接输出 Flow YAML（纯 YAML，无 markdown 代码块）。
"""


def build_planner_messages(description: str, catalog: str) -> list[dict]:
    """Compose the message list for a planning LLM call."""
    return [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PLANNER_USER_PROMPT_TEMPLATE.format(
                catalog=catalog,
                description=description.strip(),
            ),
        },
    ]


def strip_code_fence(text: str) -> str:
    """LLMs sometimes wrap YAML in ```yaml ... ``` despite being asked not to.

    Strip a single leading/trailing fence; leave inner content alone.
    """
    stripped = text.strip()
    if not stripped:
        return stripped
    if stripped.startswith("```"):
        # Drop the first line (```lang) and the trailing ``` if present.
        lines = stripped.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped

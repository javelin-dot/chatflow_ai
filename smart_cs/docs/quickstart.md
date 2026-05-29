# 快速开始

## 1. 安装

本仓库与 `chatflow_ai` 平级。建议直接在仓库根目录用虚拟环境：

```bash
cd /Users/jiangjianmin/ai/code/chatflow_ai
python -m venv .venv
source .venv/bin/activate
pip install -r smart_cs/requirements.txt
pip install -e smart_cs
```

> 当前阶段 0 只依赖 Pydantic + Click + PyYAML 等轻量包，不强制安装 LLM SDK。
> 后续接入 OpenAI/Qwen 时再装。

## 2. Hello World：跟最小 FAQ 对话

```bash
python -m smart_cs shell --config smart_cs/examples/hello/config.yml
```

预期效果：

```
[smart_cs] tenant=demo workspace=default
You> 营业时间
Bot> 我们的客服在线时间是 09:00-22:00（北京时间，全年无休）。

You> 怎么退款
Bot> 在「我的订单」→ 选择订单 → 点击「申请退款」即可发起退款。

You> 帮我转人工
Bot> 已为您转接到人工客服，请稍候。（mock：本示例未对接真实人工坐席）

You> exit
```

不依赖任何 LLM：演示走的是 **FAQ 关键词匹配** + **转人工 Skill**，
目的是验证「接 → 知 → 答 → 控」全链路可跑通。

## 3. 配置文件解读

`smart_cs/examples/hello/config.yml`：

```yaml
version: "0.1"

tenant:
  id: demo
  name: Demo Company
  workspace: default

reception:
  channels:
    - type: console

knowledge:
  bases:
    - id: faq_main
      type: faq_yaml
      source: ./kb/faq.yml

skills:
  enabled:
    - faq_answer        # 走 KB 查 FAQ
    - handoff           # 用户主动转人工

policies:
  - type: kb_policy
    priority: 50
  - type: handoff_policy
    priority: 30
  - type: fallback_policy
    priority: 10

governance:
  guardrail:
    enabled: true
    block_patterns: []
  audit:
    enabled: true
    sink: stdout
  quota:
    session_max_turns: 50
```

`kb/faq.yml`：

```yaml
- id: business_hours
  question: 营业时间
  keywords: [营业时间, 工作时间, 几点上班]
  answer: 我们的客服在线时间是 09:00-22:00（北京时间，全年无休）。

- id: refund
  question: 怎么退款
  keywords: [退款, 退钱, 申请退款]
  answer: 在「我的订单」→ 选择订单 → 点击「申请退款」即可发起退款。
```

## 4. 加一个新 FAQ

编辑 `kb/faq.yml` 追加：

```yaml
- id: shipping
  question: 多久能发货
  keywords: [发货, 物流, 多久到]
  answer: 北上广深次日达，其他地区 3 个工作日内。
```

无需重启（默认开启文件监听重载——阶段 1 完整化）。

## 5. 加一个新 Skill

最小骨架：

```python
# smart_cs/skills/builtin/check_order.py
from smart_cs.skills.skill import Skill, SkillContext, SkillResult

class CheckOrder(Skill):
    name = "check_order"
    triggers = ["查订单", "订单状态", "我的订单"]

    async def run(self, ctx: SkillContext) -> SkillResult:
        # 在这里调你的订单系统 API
        order_id = ctx.slots.get("order_id")
        return SkillResult.reply(f"订单 {order_id} 状态：已发货")
```

在 `config.yml.skills.enabled` 追加 `- check_order` 即可启用。

## 6. 接入真实 LLM

在 `config.yml` 加：

```yaml
llm:
  default:
    provider: openai          # 或 anthropic / dashscope
    model: gpt-4o-mini
    api_key: ${OPENAI_API_KEY}
```

并切换 `policies` 优先级让 LLM 兜底：

```yaml
policies:
  - type: kb_policy
    priority: 50
  - type: llm_policy           # 新增（待阶段 1 实现）
    priority: 20
  - type: fallback_policy
    priority: 10
```

## 7. 启 HTTP 服务

```bash
python -m smart_cs run --config smart_cs/examples/hello/config.yml --host 0.0.0.0 --port 8080
```

然后：

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: demo" \
  -d '{"session_id": "u123", "message": "营业时间"}'
```

## 8. 下一步

- 看 [architecture.md](./architecture.md) 了解整体设计
- 看 [business_insight.md](./business_insight.md) 了解为什么这样设计
- 看 [roadmap.md](./roadmap.md) 了解后续计划

# ChatFlow AI 对接异构系统的 OpenAPI 设计

## 设计目标

ChatFlow AI 不关心外部系统使用 Java、Go、Python 还是其他语言。只要对方系统提供符合 OpenAPI 3.x 的接口文档，ChatFlow AI 就可以通过 Flow 收集槽位，再用通用动作 `action_call_openapi` 调用对应接口。

典型场景：

- Java 用户系统提供注册接口
- OpenAPI 文档中有 `operationId: registerUser`
- 用户通过对话提供用户名、手机号、密码等信息
- ChatFlow AI 自动调用注册接口创建用户

## 核心思路

现有 `Dialogue Understanding` 继续负责理解用户意图和提取槽位，不新增复杂理解层。

新增的能力只做一件事：

```text
Flow step metadata -> action_call_openapi -> OpenAPI operation -> 外部系统
```

这样业务系统变化时，只需要改 Flow 配置和 OpenAPI 文档，不需要改 ChatFlow AI 核心对话代码。

## Flow 示例：自动注册用户

```yaml
flows:
  register_user:
    description: "注册新用户"
    persisted_slots:
      - created_user_id
    steps:
      - id: "ask_username"
        collect: username
        next: "ask_phone"

      - id: "ask_phone"
        collect: phone
        next: "ask_password"

      - id: "ask_password"
        collect: password
        next: "create_user"

      - id: "create_user"
        action: action_call_openapi
        next: "end"
        metadata:
          openapi:
            spec: "./openapi/user-service.yml"
            base_url: "http://localhost:8080"
            operation_id: "registerUser"
            request_body:
              username: "slot:username"
              phone: "slot:phone"
              password: "slot:password"
            response:
              slots:
                created_user_id: "body.data.id"
              success_message: "注册成功，用户ID是 {created_user_id}。"
              failure_message: "注册失败，请稍后再试。"
```

## Domain 示例

```yaml
slots:
  username:
    type: text
    mappings:
      - type: from_llm
    description: "用户名"

  phone:
    type: text
    mappings:
      - type: from_llm
    description: "手机号"

  password:
    type: text
    mappings:
      - type: from_llm
    description: "登录密码"

  created_user_id:
    type: text
    mappings:
      - type: controlled
    description: "外部用户系统返回的用户ID"

responses:
  utter_ask_username:
    - text: "请告诉我用户名。"
  utter_ask_phone:
    - text: "请告诉我手机号。"
  utter_ask_password:
    - text: "请设置登录密码。"

actions:
  - action_call_openapi
```

## OpenAPI 示例

```yaml
openapi: 3.0.3
info:
  title: User Service
  version: 1.0.0
servers:
  - url: http://localhost:8080
paths:
  /api/users/register:
    post:
      operationId: registerUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [username, phone, password]
              properties:
                username:
                  type: string
                phone:
                  type: string
                password:
                  type: string
      responses:
        "200":
          description: Created
```

## 当前支持的配置

`metadata.openapi` 支持：

- `spec`: OpenAPI JSON/YAML 本地路径或 HTTP(S) URL
- `base_url`: 服务地址；不填时读取 OpenAPI `servers[0].url`
- `operation_id`: 要调用的 OpenAPI operationId
- `headers`: 请求头映射
- `parameters`: path/query 参数映射
- `request_body`: JSON 请求体映射
- `response.slots`: 把响应字段写回槽位
- `response.success_message`: 2xx 时回复
- `response.failure_message`: 非 2xx 时回复
- `timeout`: 请求超时秒数，默认 30

映射值支持：

- `slot:username`: 从同名槽位取值
- `const:value`: 固定值
- `"{username}"`: 简单模板替换

响应字段路径示例：

- `body.id`
- `body.data.id`
- `body.data.user.id`

## 边界

这个方案不把 Java 接口“编译成 SDK”，也不自动决定任何接口都能调用。可调用能力必须显式写在 Flow 中，避免 LLM 自行调用未授权接口。

后续可以继续增强：

- 根据 OpenAPI schema 自动校验必填参数
- 支持 OAuth2、API Key、Bearer Token 配置
- 支持表单、multipart、文件上传
- 增加接口白名单和审计日志

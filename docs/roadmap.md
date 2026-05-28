# 路线图

> 与 [status.md](./status.md) 对应。
> **原则**：先完成核心功能，不做功能以外的扩展。
> **核心功能** = 让公司业务人员（测试 / 运营 / 风控 / 客服等）能在内网通过对话稳定可靠地调用公司各异构后端的 OpenAPI 接口。
> 时间估算是单人工程小时，不含 review/讨论。

---

## 阶段 0：完成 OpenAPI 集成核心闭环

**目标**：让任何一个真实的内网 Java 服务，业务人员都能通过对话调用成功。
**结束标准**：选 1-2 个真实业务服务（如用户、KYC、订单），跑通 5+ 个真实 operationId，业务人员不需要工程师陪同。

### 1. OpenAPI 认证支持
- **Why**：企业内 Java 接口都需要鉴权，当前一个真实接口都调不通。
- **How**：在 `metadata.openapi` 增 `auth` 配置，支持三种最常见方案：
  - `bearer`: 从 env / Vault 读 token
  - `api_key`: header 或 query
  - `oauth2_client_credentials`: 启动期换 access_token，过期自动刷新
- **位置**：`integrations/openapi.py` 增 `AuthProvider` 抽象；`OpenAPIClient` 调用前注入 Authorization header。
- **工时**：2 天

### 2. 表单 / multipart / 文件上传
- **Why**：Java 后端常见，当前完全调不了。
- **How**：`metadata.openapi.body_type` 增 `json`（默认）/ `form` / `multipart`；`OpenAPIClient.call_operation` 按 type 分支用 httpx 对应参数（`data=` / `files=`）。
- **工时**：1 天

### 3. Spec 缓存 + 多 spec 注册
- **Why**：当前每次调用重新加载 spec，对接 5+ 服务时延迟和 IO 都不可接受。
- **How**：
  - 启动期扫描 `endpoints.yml` 里声明的所有 spec，预加载到 `OpenAPIRegistry`（新增）；
  - `ActionCallOpenAPI` 改为按 `service_name + operation_id` 查注册表；
  - spec 变更走文件 mtime / HTTP ETag 失效。
- **工时**：1 天

### 4. 错误信息透传
- **Why**：业务人员看到"调用失败"但不知道原因，排查只能找工程师。
- **How**：`ActionCallOpenAPI` 失败时把 HTTP status + 响应体的 `message/code/error` 字段格式化展示；可配置 `error_template`。
- **位置**：`agent/actions.py:644-648` 改写。
- **工时**：4h

### 5. Schema 校验必填参数
- **Why**：LLM 抽错槽位时，提前在框架层报错比让服务端 400 更易调试。
- **How**：用 OpenAPI spec 里的 `required` 数组在 `OpenAPIClient.call_operation` 前校验；缺失时 raise `OpenAPICallError` 并把缺哪些字段告诉对话端，让 LLM 二次追问。
- **工时**：1 天

### 6. 接口白名单 + 审计日志
- **Why**：多角色权限是产品必需；调用必须可追溯。
- **How**：
  - `endpoints.yml` 里给每个 spec 声明 `allowed_roles: [ops, qa]`
  - `ActionCallOpenAPI` 执行前查 `tracker` 里的当前用户角色 vs 白名单
  - 调用结果写审计表（user, role, operation_id, request, response, timestamp）；TrackerStore 同库即可
- **工时**：2 天

### 7. 用户与角色模型
- **Why**：当前 `tracker.sender_id` 只是会话标识，无角色概念。第 6 项需要它。
- **How**：
  - `core/tracker.py` 增 `user_context: {user_id, role, tenant_id?}` 字段；
  - 通道入口（REST / WS）从请求头 `X-User-Id` / `X-User-Role` 注入（信任公司 SSO 网关）；
  - 提供 mock 模式让本地开发能 `--as-user=ops_a` 切换角色。
- **工时**：1 天

**阶段 0 合计：约 1.5–2 周。**

---

## 阶段 1：降低业务人员使用门槛

**目标**：业务人员能自助使用，不需要工程师陪同。
**结束标准**：业务方提供新 OpenAPI 文档后，工程师 < 30 分钟即可让对话端跑起来；业务人员能在对话里自然发现"我能干啥"。

### 8. 从 OpenAPI 自动生成 Flow 模板
- **Why**：当前每个 operationId 都要手写 Flow YAML——业务方 200 个接口 = 工程师写 200 份 Flow，这是落地最大瓶颈。
- **How**：新增 `chatflow generate-flows --spec ./openapi/xx.yml --out flows/` CLI：
  - 每个 operationId 生成一个 Flow 模板
  - 自动从 schema 推断 slot 类型和 `collect` 步骤顺序
  - `description` 取自 OpenAPI 的 `summary` + `description`
  - 工程师只需 review + 调整描述
- **工时**：3 天

### 9. "我能干啥" 能力索引
- **Why**：业务人员首次打开对话无从下手。
- **How**：
  - 启动期扫描所有已加载 Flow，按角色过滤后生成"能力清单"
  - 用户输入"我能做什么 / help / 帮助" → 触发 `ActionListCapabilities`（新增），按业务域分组展示
  - 长期：基于 Flow `description` 做嵌入检索，"我想审核 KYC" → 推荐相关 Flow
- **工时**：2 天

### 10. 响应数据结构化展示
- **Why**：查询类场景（"查张三近 10 笔交易"）当前只能拼字符串塞模板，体验差。
- **How**：
  - `metadata.openapi.response.display` 增 `table` / `card` / `text` 三种模板
  - 通道层（REST/SocketIO）协议支持 `data` 字段携带结构化结果，前端按 type 渲染
  - 对纯文本通道（console）降级为格式化文本
- **工时**：2 天

### 11. 二次确认机制
- **Why**：写操作（创建用户、冻账户、退款）当前直接执行，业务人员手抖即生效。
- **How**：
  - `metadata.openapi.requires_confirmation: true` 时，先回显参数让用户确认 → 用户回"确认" → 真正调用
  - 复用现有 `ClarifyCommand` 链路
- **工时**：1 天

### 12. Mock 模式
- **Why**：业务人员第一次用某 Flow 想先验证流程，不想真实操作。
- **How**：
  - 用户/系统级 `mock_mode: true` 开关
  - `ActionCallOpenAPI` 检测到 mock 时不打实际 HTTP，按 OpenAPI 的 `example` / `examples` 生成假响应；无 example 时按 schema 用 Faker 造
- **工时**：2 天

**阶段 1 合计：约 2 周。**

---

## 阶段 2：高频业务能力增强

**目标**：覆盖业务场景的"批量"与"链式"高频需求。

### 13. 批量调用原语
- **Why**：测试场景"造 10 个用户"、运营场景"批量审 50 个 KYC"是日常需求。
- **How**：
  - Flow 增 `BATCH` 步骤类型：`for_each: {count: 10}` 或 `for_each: {items: "slot:application_ids"}`
  - 内部循环执行 sub-steps；汇总结果到 slot
  - 限流：默认串行，可配并发度
- **工时**：3 天

### 14. 链式调用上下文传递
- **Why**：常见"创建用户→建账户→发起交易"需要把前一调用结果传给后一调用。当前能用 `response.slots` 实现但语义不直观。
- **How**：现有机制基本够，做的是"易用化"：
  - 增加 `step.use_outputs_from: [step_id]` 显式声明依赖
  - 在 `chatflow validate` 里检测循环依赖
- **工时**：1 天

### 15. 测试数据生成器
- **Why**：测试场景常要"造一个看起来真实的手机号/身份证/邮箱"。
- **How**：内置 Faker 集成；slot 映射增 `fake:zh_CN.phone_number` / `fake:email` 等语法
- **工时**：1 天

### 16. 操作历史与回放
- **Why**：业务人员"刚才那操作再来一次/改个参数重做"是高频需求。
- **How**：
  - 第 6 项的审计日志提供基础数据
  - 增 `chatflow history --user ops_a --last 10` CLI 列出最近操作
  - 对话端"重做上一次" → 复用上次 slot + Flow 再执行一遍
- **工时**：2 天

**阶段 2 合计：约 1.5 周。**

---

## 阶段 3：上生产前的工程化

**目标**：从"内网试用"过渡到"正式生产环境"。**只在阶段 0-2 完成且有真实用户后启动。**

| # | 项 | 工时 |
|---|---|---|
| 17 | 核心路径测试覆盖（Tracker / Policy / FlowExecutor / ActionCallOpenAPI / 鉴权 / 审计）目标 50% | 5 天 |
| 18 | OpenTelemetry：在 ActionCallOpenAPI 加 span，记录 service+operationId+latency+status；导出 OTLP | 2 天 |
| 19 | 错误恢复：HTTP 失败时的重试（幂等性判断 + tenacity） | 1 天 |
| 20 | CORS 默认改 `[]` 并校验与 credentials 冲突；如直接暴露公网，加 API Key 中间件 | 半天 |
| 21 | 动态加载 `actions/*.py` 收口：限定目录 + AST 校验 | 半天 |
| 22 | `predict_sync` 异步统一 | 2h |
| 23 | 注册 Action 失败 fail-fast | 30min |
| 24 | 依赖锁定（uv / pip-tools） | 2h |
| 25 | 密钥治理：YAML 占位符强制 + Vault 适配 | 半天 |
| 26 | TrackerStore 默认 JSON + filelock；Redis 适配 | 1 天 |
| 27 | DB schema 迁移（Alembic） | 1 天 |
| 28 | 默认 DB 名清理（`atguigu_ai` → `chatflow_ai`） | 10min |
| 29 | CI（ruff + mypy + pytest + bandit） | 1 天 |
| 30 | 文档同步检查脚本 | 半天 |

**阶段 3 合计：约 2.5–3 周。**

---

## 暂不做的事

以下方向**不在当前路线图**，明确不做或后置到产品验证后再评估：

- ❌ **Flow 双实现的合并** —— 不阻挡功能，等真正卡到再说
- ❌ **Flow 条件表达式升级（and/or/比较）** —— OpenAPI 对话场景多数能绕过；真有需求时再做
- ❌ **巨石文件拆分** —— 不影响功能
- ❌ **每轮 LLM 调用优化（并行/缓存/熔断）** —— 内网工具人数少；先关 Rephraser 即可
- ❌ **RAG / 知识问答增强** —— 本产品定位不是 RAG；`EnterpriseSearchPolicy` 留着但不投入
- ❌ **训练 / 微调** —— `training/` 当前只是 YAML 打包，与产品价值无关，可后期评估是否删除
- ❌ **Flow 静态分析器、Flow 可视化编辑器、文档站** —— 等业务真正用起来再说
- ❌ **多 LLM Provider 路由 / Fallback** —— 单 Provider 出问题再做
- ❌ **向量库 Retriever（Chroma/PGVector 等）** —— 本产品不依赖向量检索
- ❌ **多语言/多租户 SaaS 化** —— 内部工具不需要

---

## 节奏建议

| 阶段 | 时长 | 阻塞 |
|---|---|---|
| 阶段 0：OpenAPI 集成核心闭环 | 1.5–2 周 | **必须先完成**，否则产品不成立 |
| 阶段 1：业务人员易用性 | 2 周 | 阶段 0 完成后立即开始 |
| 阶段 2：批量 / 链式 / 业务能力 | 1.5 周 | 阶段 1 完成后看真实用户反馈再排细节 |
| 阶段 3：生产工程化 | 2.5–3 周 | **只在阶段 0-2 完成 + 有真实用户后**启动 |

**首 4 周聚焦阶段 0 + 阶段 1**，让一两个真实业务场景（如 KYC 审核、测试数据生成）跑起来。之后基于真实使用反馈再决定 2/3 的细节。

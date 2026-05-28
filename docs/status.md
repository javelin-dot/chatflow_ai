# 现状与未完成点

> 截至 commit `d3079fd`。
> 本文档以**产品目标——对话式 OpenAPI 操作台**——为参照系评估现状，不是按通用框架视角。
> 与 [roadmap.md](./roadmap.md) 配对阅读。

## 1. 总体评估

项目处于 **MVP 阶段**：底层对话框架（Tracker / Flow / Command / Policy）骨架完整、能跑通；但**支撑产品价值的 OpenAPI 集成只完成约 30%**，距离"业务人员可直接使用"还有明确差距。

| 维度 | 状态 |
|---|---|
| 对话底座（Flow / Command / Policy 闭环） | 🟢 可用 |
| **OpenAPI 调用核心**（核心价值） | 🟡 基础能跑，企业关键能力缺失 |
| **多角色 / 权限**（产品必需） | 🔴 完全未做 |
| **批量与链式数据生成**（高频需求） | 🔴 完全未做 |
| 业务人员易用性（Flow 自动生成等） | 🔴 未做，目前需要工程师手写 Flow |
| 持久化 | 🟡 MySQL 可用，默认 memory |
| 公网安全（CORS、认证） | 🔴 不足，但**内网部署下可暂缓** |
| 测试 / 可观测性 | 🔴 0，**功能完成后再补** |

## 2. OpenAPI 集成的具体缺口（🔴 P0，直接阻挡产品落地）

参考 `chatflow_ai/integrations/openapi.py`（213 行）+ `agent/actions.py:584` 的 `ActionCallOpenAPI` 当前实现：

### 2.1 认证机制完全缺失
**现状**：只支持透传 `default_headers`（`integrations/openapi.py:52`），没有 OAuth2 / API Key 注入 / Bearer Token 刷新等机制。
**影响**：企业内 Java 服务基本都需要鉴权，**当前调不通任何受保护接口**。
**位置**：`integrations/openapi.py`、`agent/actions.py:584`。

### 2.2 仅支持 JSON request body
**现状**：`OpenAPIClient.call_operation`（`integrations/openapi.py:101`）只走 `json=request_body`。
**影响**：真实 Java 接口常用 `application/x-www-form-urlencoded`、`multipart/form-data`（含文件上传）；**这类接口完全调不了**。

### 2.3 Spec 每次调用都重新加载
**现状**：`ActionCallOpenAPI.run` 每次都调 `OpenAPIClient.from_source`（`agent/actions.py:628`），从本地文件或 HTTP 重读 spec、解析 YAML。
**影响**：单次对话 N 个接口调用 = N 次 spec 加载。生产部署对接 5+ 微服务时，延迟与 IO 都不可接受。

### 2.4 无 schema 校验
**现状**：参数缺失只在 HTTP 调用时由服务端返回 4xx 才发现。
**影响**：对话期间 LLM 抽错槽位（如把日期填到金额字段），错误信息要绕一圈才能反馈给业务人员；调试体验差。

### 2.5 无接口白名单 + 无审计日志
**现状**：任何 Flow 都能写任意 `operation_id`，无角色级访问控制；调用结果只 `add_event("openapi_called", ...)`（`agent/actions.py:658`），无持久化审计。
**影响**：
- **运营/客服/风控场景必须有审计**——谁、什么时候、改了谁的数据，要可追溯。
- **多角色权限是产品功能而非可选**——风控能冻账户，客服不能；当前完全不区分。

### 2.6 错误信息不透传
**现状**：4xx/5xx 时只 `add_response(f"接口调用失败：{e}")`（`agent/actions.py:646`），把 HTTP 响应体的 `{"code": "X", "msg": "Y"}` 吞了。
**影响**：业务人员看到"调用失败"但不知道原因（是参数错？权限不够？业务规则拒绝？），排查只能找工程师。

### 2.7 业务人员需要工程师手写 Flow
**现状**：每个 OpenAPI 接口要手写一份 Flow YAML（参考 `docs/openapi-integration-design.md`）。
**影响**：业务方有 200 个接口 = 工程师写 200 份 Flow。**这是产品落地最大的人力瓶颈**。

### 2.8 无链式/批量调用原语
**现状**：可以靠 Flow `CALL` 串多个 step，但每个 step 仍是单次调用，没有"循环 N 次"、"对列表中每项调一次"的原语。
**影响**：测试场景"造 10 个用户"、运营场景"批量审核 50 个 KYC 申请"做不了。

### 2.9 无 Mock 模式
**现状**：要么真打接口，要么不调。
**影响**：业务人员第一次试用某个 Flow 时，会真实创建/修改数据；想"先验证一下对话流程"做不到。

## 3. 多角色 / 权限模型（🔴 P0，产品必需）

**现状**：完全没有"用户"这个概念。所有对话端没区分调用方身份。
**影响**：
- 无法实现"运营 A 不能调用风控接口"
- 无法记录"是谁做的这次操作"
- 无法给不同角色配不同 Flow 集

**位置**：当前 `core/tracker.py` 有 `sender_id`（会话标识），但没有"用户角色"字段，也没有任何 Policy/Action 在执行时校验角色。

## 4. 业务人员易用性差距（🔴 P0）

### 4.1 不知道"我能干啥"
**现状**：业务人员打开对话，没有任何"可用能力"提示。
**影响**：上手成本高，得有人手把手教。

### 4.2 响应数据无格式化
**现状**：`ActionCallOpenAPI` 成功时只回一句 `success_message`，要展示订单详情、用户信息这类**结构化数据**只能拼字符串塞模板。
**影响**：查询类场景体验差（"查一下张三的近 10 笔交易" → 一坨文本）。

### 4.3 无操作回滚/撤销
**现状**：一旦 `action_call_openapi` 执行就生效。
**影响**：业务人员点错、参数错没法快速撤销，得手动反向操作。

## 5. 已知工程缺陷（按对当前定位的影响排序）

### 🟡 P2（重要但不直接阻挡产品）

| 项 | 位置 | 说明 |
|---|---|---|
| `predict_sync` 异步反模式 | `policies/policy_ensemble.py` | 在 FastAPI 路由内调用会爆 `RuntimeError`；FastAPI 入口当前规避了，但易踩坑 |
| Flow 双实现（FlowExecutor / FlowPolicy._process_step） | `flow/flow_executor.py` + `policies/flow_policy.py` | 逻辑漂移已存在；不阻挡功能但增加未来维护成本 |
| Flow 条件表达式只支持 `==/!=` | `flow_executor.py:368-423` | 复杂业务规则要在 Action 里写——OpenAPI 对话场景多数能绕过 |
| 注册 Action 失败被吞 | `agent/agent.py:95-99` | 启动假象成功；建议改 fail-fast |
| 默认 DB 名仍为 `atguigu_ai` | `shared/config.py:758` | 改名遗留 |
| 巨石文件 | `actions.py` 869L 等 | 影响新人入门，不影响功能 |
| RAG Prompt 硬编码 | `policies/enterprise_search_policy.py` | 本产品定位下 RAG 是次要能力，可忽略 |
| 每轮可能 3 次串行 LLM | Command Gen → ESP → Rephraser | 内部工具人数少、可忍受；Rephraser 建议默认关 |

### 🟢 P3（内网工具下可暂缓，公网部署前必须做）

| 项 | 说明 |
|---|---|
| API 无认证 | 内部部署可走公司 SSO 网关兜底；如直接暴露公网必须先做 |
| CORS 默认 `["*"] + credentials=True` | 浏览器规范禁止；FE 集成时会撞墙，应改默认 `[]` |
| 动态加载 `actions/*.py` 可 RCE | 部署目录可控的情况下风险有限 |
| 零自动化测试 | 功能完成后再建测试基线 |
| 依赖未锁定 | 可复现性问题，CI 接入时一并解决 |
| 密钥明文 | 接 Vault / 公司 KMS |

## 6. 未实现 / 占位（与当前定位无关，可忽略）

下列在当前产品定位下**不是关键路径**，列出仅供参考：

- `training/` —— `Trainer.train` 实际只是"加载+校验+打包 YAML"，不训练任何模型。对本产品定位没用，可考虑后续重命名或删除。
- `training/finetune/` —— 微调数据合成，未集成。
- `retrieval/` —— 当前主要服务 RAG/Flow 检索，本产品定位下用处有限（除非业务方有"查文档"类需求）。
- `nlg/response_rephraser.py` —— LLM 重述，建议默认关闭（每条响应一次额外 LLM 调用）。
- `channels/inspect_proxy.py` —— 调试通道，可保留。

## 7. 文档与代码一致性

之前 7 份 AI 生成长文档已删除。当前 3 份文档（architecture / status / roadmap）的关键事实（包名、类名、Policy 优先级、`max_actions`、`action_call_openapi` metadata 结构等）均与代码核对过。后续改动需在 PR 中同步更新文档。

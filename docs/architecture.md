# ChatFlow AI 架构

> 本文档描述 chatflow_ai 当前代码（commit `d3079fd`）的真实结构，不是设计愿景。
> 所有 `file:line` 引用均可在仓库中验证。

## 1. 定位

ChatFlow AI 是一个**企业内"对话式 OpenAPI 操作台"**。目标价值是：**让公司内的业务人员用自然语言对话驱动各种异构后端（Java/Go/Node 等）的 OpenAPI 接口，完成原本需要登录多个后台、手动调接口才能做的业务操作**。

**目标用户是企业内的多种业务角色**，不限于某一类：

| 角色 | 典型场景 |
|---|---|
| 测试工程师 | 批量造"KYC 通过的香港用户 + 各 3 笔交易"等测试数据 |
| 运营 | 审核 KYC 申请、调整用户标签、批量发券 |
| 风控 | 查用户近期行为、临时冻结/解冻、加白加黑名单 |
| 客服 | 查改订单状态、退款、补发 |
| 财务 | 对账查询、手动结算、调账 |

共同特征：这些操作背后都是企业已有的 Java/Go 等后端服务的 OpenAPI 接口，只是当前需要打开多个内部系统、登录多个账号、手动填多个表单才能完成。**ChatFlow AI 把它们简化为一句话对话。**

**核心机制**：

1. 业务系统提供 OpenAPI 3.x 文档（spec）
2. ChatFlow AI 通过 Flow 声明哪些 operationId 可被对话调用、由哪些角色调用
3. 业务人员用自然语言描述需求，LLM 抽取参数槽位
4. `action_call_openapi`（`integrations/openapi.py`）执行真实 HTTP 调用，写回结果给对话上下文

**不做的事**：

- 不是通用客服/聊天机器人（虽然底层架构借鉴了 Rasa Pro CALM）
- 不替代 Postman/Swagger UI 这类手动调接口工具——本工具的价值在"对话编排 + 多接口组合 + 角色权限"
- 不做接口编译成 SDK；可调用接口必须显式在 Flow 中声明，避免 LLM 自行调用未授权接口
- 不替代企业 BI / 数据平台——本工具偏"操作执行"，不偏"查询展示"

## 2. 技术栈

| 层 | 选型 | 备注 |
|---|---|---|
| Web | FastAPI ≥ 0.100 + Uvicorn | REST + WebSocket |
| 编排 | LangGraph ≥ 0.2 | StateGraph 5 节点 |
| LLM | LangChain ≥ 0.3 | 多 Provider: OpenAI / Anthropic / Azure / Qwen(DashScope) |
| 校验 | Pydantic ≥ 2.0 | 配置、请求体 |
| 存储 | SQLAlchemy ≥ 2.0 + PyMySQL | MySQL TrackerStore |
| 检索 | sentence-transformers + Neo4j GraphRAG | 可选，向量库未默认接入 |
| 配置 | ruamel.yaml + PyYAML | YAML 为主，支持 `${VAR}` 占位 |
| CLI | Click | 入口命令 `chatflow`（`setup.py:266`） |
| Python | ≥ 3.10 | |

## 3. 目录结构

```
chatflow_ai/
├── agent/                       # 对话代理与编排
│   ├── agent.py                 # Agent 类，工厂方法 Agent.load()
│   ├── actions.py               # Action 基类 + 16 个内置 Action
│   ├── message_processor.py     # 向后兼容的同步处理器
│   └── graph/                   # LangGraph 编排
│       ├── builder.py           # build_message_processing_graph()
│       ├── state.py             # MessageProcessingState (TypedDict)
│       ├── edges.py             # should_execute_action / should_continue
│       └── nodes/               # understand / policy / action / guard / response
├── api/
│   └── server.py                # ChatFlowServer (FastAPI)
├── channels/                    # 通道适配
│   ├── rest_channel.py
│   ├── socketio_channel.py
│   ├── console_channel.py
│   └── inspect_proxy.py
├── cli/                         # ChatFlowCLI (Click)
│   ├── init.py / train.py / run.py / shell.py / inspect.py / export.py
├── core/                        # 对话状态核心
│   ├── tracker.py               # DialogueStateTracker
│   ├── domain.py                # Domain 加载
│   ├── slots.py                 # 6 种 Slot 类型
│   └── stores/                  # TrackerStore: memory / json / mysql
├── dialogue_understanding/
│   ├── commands/                # 14 个 Command 类
│   ├── flow/                    # Flow / FlowStep / FlowExecutor / FlowLoader
│   ├── generator/               # LLMCommandGenerator + PromptBuilder + CommandParser
│   ├── processor/               # CommandProcessor (含 force_slot_filling)
│   └── stack/                   # DialogueStack + 6 种 StackFrame
├── policies/
│   ├── base_policy.py           # Policy 抽象 + PolicyPrediction
│   ├── flow_policy.py           # FlowPolicy (priority=100)
│   ├── enterprise_search_policy.py  # EnterpriseSearchPolicy (priority=50)
│   └── policy_ensemble.py       # PolicyEnsemble
├── nlg/
│   ├── template_nlg.py          # 模板填充
│   └── response_rephraser.py    # LLM 润色（可选）
├── retrieval/
│   ├── base_retriever.py        # InformationRetrieval 抽象
│   ├── embedder.py              # sentence-transformers
│   └── flow_retriever.py        # Flow 语义检索
├── shared/
│   ├── config.py                # 配置类层级
│   ├── constants.py / exceptions.py / yaml_loader.py
│   └── llm/                     # LLMClient 工厂 + LangChainClient
├── training/
│   ├── trainer.py               # Trainer: 加载 + 校验 + 打包（非模型训练）
│   ├── model_storage.py
│   └── finetune/                # 微调数据生成（未集成）
└── integrations/
    └── openapi.py               # OpenAPI 外部接口
```

代码体量约 **18,300 行**（含空行注释）。

## 4. 核心抽象

### 4.1 DialogueStateTracker（`core/tracker.py`）

单会话的状态聚合：
- `slots: Dict[str, Slot]` —— 槽位
- `dialogue_stack: DialogueStack` —— LIFO 栈，唯一状态源
- `dialogue_turns: List[DialogueTurn]` —— 历史轮次（默认上限 100）
- `latest_message: UserMessage` —— 最新输入
- `latest_action_name: str` —— 最近执行的 action

派生属性 `active_flow`（`tracker.py:196-200`）从 stack 顶部计算，不冗余存储。

### 4.2 DialogueStack 与 StackFrame（`dialogue_understanding/stack/`）

对话栈采用 LIFO，每帧表示一段"上下文意图"。6 种帧：

| 帧类型 | 含义 | 由谁压栈 |
|---|---|---|
| `FlowStackFrame` | 正在跑某个 Flow | `StartFlowCommand` |
| `SearchStackFrame` | 走 RAG 检索 | `KnowledgeAnswerCommand` |
| `ChitChatStackFrame` | 闲聊回应 | `ChitChatAnswerCommand` |
| `CannotHandleStackFrame` | LLM 自认无法处理 | `CannotHandleCommand` |
| `CompletedStackFrame` | Flow 完成的占位 | FlowPolicy 内部 |
| `HumanHandoffStackFrame` | 转人工 | `HumanHandoffCommand` |

`SearchStackFrame` / `ChitChatStackFrame` **不存业务字段**（如 query），运行时从 `tracker.latest_message` 读取——刻意减少冗余但代价是隔轮无法回溯原始 query。

### 4.3 Flow 与 FlowStep（`dialogue_understanding/flow/flow.py`）

Flow 用 YAML 声明，7 种步骤：
- `ACTION` —— 执行一个 action
- `COLLECT` —— 收集槽位
- `CONDITION` —— 条件分支
- `LINK` —— 切换到另一 Flow（goto 语义）
- `CALL` —— 嵌套调用另一 Flow（函数调用语义，完成后回到 next）
- `SET_SLOT` —— 直接赋值槽位
- `END` —— 结束

**关键约束**：`condition` 字段只支持 `==`、`!=`、布尔字面量（`flow_executor.py:368-423`）。复杂逻辑要写到 Action 里。

### 4.4 Command（`dialogue_understanding/commands/`）

LLM 输出的"意图原子"。14 个 Command 类，按职责分组：

| 分组 | 类 | 文件 |
|---|---|---|
| Flow 控制 | `StartFlowCommand` `CancelFlowCommand` `ChangeFlowCommand` | `flow_commands.py` |
| 槽位 | `SetSlotCommand` `ResetSlotCommand` | `slot_commands.py` |
| 应答 | `ChitChatAnswerCommand` `CannotHandleCommand` `KnowledgeAnswerCommand` `FreeFormAnswerCommand` | `answer_commands.py` |
| 会话 | `SessionStartCommand` `ClarifyCommand` `HumanHandoffCommand` `RestartCommand` `NoopCommand` | `session_commands.py` |
| 错误 | `ErrorCommand` `InternalErrorCommand` `ParseErrorCommand` | `error_commands.py` |

Command 由 `LLMCommandGenerator` 生成 → `CommandParser` 解析 → `CommandProcessor.execute()` 执行（多数 Command 的副作用是**改 Tracker 或压栈帧**，而非直接产生响应）。

### 4.5 Policy 与 Action

**Policy** 决定"下一步执行哪个 Action"。`PolicyEnsemble` 按 `priority` 降序询问各 Policy，取第一个 `confidence > 0` 的预测。

| Policy | priority | 职责 |
|---|---|---|
| `FlowPolicy` | 100 | Flow 步骤推进；栈顶是 FlowStackFrame 时绝对优先 |
| `EnterpriseSearchPolicy` | 50 | 处理 Search/ChitChat/CannotHandle/Completed/HumanHandoff 5 类帧；RAG 兜底 |

数值差 50 是"硬性优先"——只要 FlowPolicy 不 abstain，ESP 永远不会被选中。

**Action** 是最终执行单元。`Action.run()` 返回 `ActionResult`（含 responses、events、next_action）。16 个内置 Action（`agent/actions.py`），包括 `ActionListen`、`ActionExtractSlots`（自带 LLM 抽槽）、`ActionUtter`（模板填充）、`ActionTriggerSearch`（压 SearchStackFrame）、`ActionCallOpenAPI` 等。自定义 Action 通过项目目录下的 `actions/*.py` 自动加载（`agent/agent.py:43-105`）。

## 5. 消息处理流程（LangGraph）

`agent/graph/builder.py:37-107` 定义的 5 节点图：

```
START
  ↓
understand_node     # LLM 生成 Commands → 写入 tracker
  ↓
policy_node         # PolicyEnsemble 预测 next_action
  ↓
[should_execute_action]
  ├─→ response_node  # 如果 action=action_listen 或 is_finished
  └─→ action_node    # 执行 Action，写 events
        ↓
       guard_node    # 防死循环：检查 action_count / max_actions(默认10)
        ↓
       [should_continue]
         ├─→ policy_node   # 继续多步执行
         └─→ response_node
  ↓
END
```

`MessageProcessingState`（`graph/state.py`）用 `TypedDict` 承载全部状态，复杂对象用 `Any` 标注避免 LangGraph 运行时类型解析问题。

图是**单例**（`get_message_processing_graph()`），无状态、节省构建开销；状态全部在 invoke 参数里。

## 6. 配置与运行时

- **`config.yml`**：声明 pipeline（`LLMCommandGenerator`）、policies（`FlowPolicy` + `EnterpriseSearchPolicy`）、language、版本等。
- **`endpoints.yml`**：LLM API key、TrackerStore 连接、检索后端等运行时连接信息。
- **环境变量替换**：YAML 中 `${VAR_NAME:default}` 在 `shared/yaml_loader.py` 解析。
- **入口**：
  - CLI：`chatflow init / train / run / shell / inspect / export`
  - 模块：`python -m chatflow_ai <command>`
  - Server：`from chatflow_ai.api.server import create_app`

## 7. 关键设计决策与取舍

### 7.1 为什么 Command 由 LLM 生成，而不是 NLU 分类器

传统 Rasa 用 intent classifier + entity extractor 两个模型。本框架用单次 LLM 调用产出结构化 Command 列表。**取舍**：

- 优点：新 Flow 即时生效，无需标数据训模型；天然支持多意图。
- 代价：每轮至少 1 次 LLM 调用（延迟 + 成本）；输出格式依赖 LLM 自觉，错则 `ParseErrorCommand` 兜底。

### 7.2 为什么 Command 与 Action 分两层

Command 只改状态/压栈（无副作用），Action 执行业务/产生响应。**取舍**：

- 优点：Command 可重放、可审计；Policy 可在下一 tick 看到完整栈再决策（如 SearchStackFrame 压栈后由 ESP 在下一节点真正执行 RAG）。
- 代价：理解成本高——新人看不出 "ActionTriggerSearch 只压栈，真正 RAG 在 EnterpriseSearchPolicy 里" 的分工。

### 7.3 为什么用 LIFO 栈而不是状态机

业务客服场景常见"用户中途插问"（如收集地址时问运费）。LIFO 栈天然支持中断恢复：插问压新帧，处理完弹出回到原 Flow。**取舍**：

- 优点：嵌套与恢复语义简单。
- 代价：栈状态不如状态图直观，可观测性弱。

### 7.4 为什么 FlowPolicy=100 / ESP=50

不是加权融合，而是用差值实现**硬性优先级**：FlowPolicy 不 abstain，ESP 永远落选。这让"Flow 收集中"绝不会被 RAG 抢走控制。

### 7.5 force_slot_filling 的取舍

`command_processor.py:340-388`：在 COLLECT 步骤中，只允许 `SetSlotCommand` 设置当前正在收集的槽位，丢弃其他 `SetSlotCommand` 和 `StartFlowCommand`。

- 优点：防止 LLM 在收集"地址"时被用户一句话带偏去开新 Flow。
- 代价：用户主动切换意图（"算了我先查个订单"）会被吃掉——这是已知 UX 限制。

### 7.6 SearchStackFrame 不存 query

`stack_frame.py:170` 注释明示。每次检索都从 `tracker.latest_message` 取。

- 优点：状态最小化，避免双写不一致。
- 代价：跨轮重试 RAG 时拿不到原始 query，必须在当轮完成。

### 7.7 为什么自己造 LLMClient 工厂而不直接用 LangChain

已经依赖 `langchain-core`，仍封一层 `LLMClient`（`shared/llm/base_client.py`）。

- 原因：隔离 vendor 差异（Qwen thinking 模式、Azure `api_version`、Anthropic 系统消息位置），让上层 Policy/Generator 不需要懂 LangChain；同时统一 sync/async 接口。
- 代价：又一层抽象，新 Provider 接入需双侧改动。

### 7.8 TrackerStore 默认 memory

`config.py` 默认 `tracker_store: memory`。重启即失忆，仅适合开发。

- 取舍：把"持久化"留给部署者决定（json / mysql / 自定义）。生产必须显式配置。

## 8. OpenAPI 集成（核心能力）

**这是产品的灵魂。** Flow 的所有其他能力都是为它服务。

### 8.1 数据流

以"运营人员审核 KYC"为例：

```
运营说："把申请编号 K-2024-001 的 KYC 审核通过"
        ↓
LLMCommandGenerator 抽取 → StartFlowCommand(flow="approve_kyc") + SetSlotCommand(application_id="K-2024-001")
        ↓
FlowExecutor 走到 step.action = "action_call_openapi"
        ↓
ActionCallOpenAPI 读 step.metadata.openapi:
  - spec: "./openapi/kyc-service.yml"    # 业务方提供
  - base_url: "http://kyc.internal:8080"
  - operation_id: "approveKycApplication"
  - parameters: {application_id: "slot:application_id"}
  - request_body: {reviewer: "slot:current_user", decision: "const:APPROVED"}
  - response.slots: {kyc_status: "body.data.status"}
        ↓
OpenAPIClient.from_source → call_operation → 真实 HTTP 调用 Java 后端
        ↓
响应回写 slot；可串接下一 step（如通知用户）
```

同样的机制服务测试场景（造数据）、客服场景（改订单）等，区别仅在 Flow YAML 里挂的是哪个 operationId。

### 8.2 当前支持

详见 [openapi-integration-design.md](./openapi-integration-design.md)。要点：

| 能力 | 状态 |
|---|---|
| Spec 加载（本地路径 / HTTP URL / YAML / JSON） | ✅ |
| operationId 路由 → method + path | ✅ |
| Path / query / header 参数 | ✅ |
| JSON request body | ✅ |
| 槽位映射 `slot:xxx` / `const:xxx` / 模板 `{xxx}` | ✅ |
| 响应字段回写 `body.data.id` → slot | ✅ |
| 成功/失败消息模板 | ✅ |
| 认证（OAuth2 / API Key / Bearer） | ❌ 未实现 |
| 表单 / multipart / 文件上传 | ❌ 未实现 |
| Spec 缓存 | ❌ 每次调用都重新加载 |
| 接口白名单 + 审计日志 | ❌ 未实现 |
| Schema 自动校验必填参数 | ❌ 未实现 |
| 从 OpenAPI 自动生成 Flow 模板 | ❌ 未实现 |

未实现项详见 [roadmap.md](./roadmap.md) P0/P1。

### 8.3 为什么这样设计

- **声明式 metadata**：Flow YAML 里写清楚"哪个 slot 喂哪个字段"，让业务变更只改 YAML 不动 Python。
- **operationId 而非 URL**：业务方升级接口后只要 operationId 不变，对话端无感。
- **显式 Flow 声明 vs 让 LLM 自由选接口**：后者风险大（误调删除接口、误传金额）。当前选择显式，代价是每个新接口要新写 Flow——但 P1 会做"从 OpenAPI 自动生成 Flow 模板"来降负担。

## 9. 与 Rasa Pro CALM 的关系

术语（Tracker/Slot/Domain/Policy/Action/Flow/`utter_*`）和"Command Generator → Flow"的思路几乎是 Rasa Pro CALM 的开源 Python 复刻，区别：

| 维度 | Rasa Pro CALM | ChatFlow AI |
|---|---|---|
| 编排 | 内置 MessageProcessor | LangGraph StateGraph |
| LLM 抽象 | 自有 | LangChain |
| 闭源/开源 | 闭源 | 开源 |
| 训练机制 | DIET / ResponseSelector 等模型 | 无 ML 模型，`train` 只校验 + 打包 YAML |
| 生产就绪度 | 是 | 否（见 [status.md](./status.md)） |

## 10. 入口速查

| 想做 | 看哪 |
|---|---|
| 看一条消息怎么走完全流程 | `agent/graph/builder.py` → `nodes/*.py` |
| 加自定义 Action | 项目 `actions/` 下新建 `.py`，继承 `Action`，实现 `run()` |
| 加自定义 Command | `dialogue_understanding/commands/` 下新建文件，`@register_command` |
| 改 Flow 引擎行为 | `dialogue_understanding/flow/flow_executor.py` |
| 改策略选择逻辑 | `policies/policy_ensemble.py:115-148` |
| 加新 LLM Provider | `shared/llm/langchain_client.py` 的 `_create_llm` |
| 加新通道 | `channels/` 下继承 `OutputChannel`/`InputChannel` |
| 加新 TrackerStore | `core/stores/` 下继承 `TrackerStore` |

## 10. 相关文档

- [status.md](./status.md) —— 当前未完成点与已知缺陷
- [roadmap.md](./roadmap.md) —— 下一步推进方向
- [openapi-integration-design.md](./openapi-integration-design.md) —— OpenAPI Action 设计

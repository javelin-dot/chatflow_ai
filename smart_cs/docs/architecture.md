# smart_cs 架构

> 通用智能客服底座 —— B 端企业内部客服 PaaS。
>
> 业务设计灵感见 [business_insight.md](./business_insight.md)。
> 当前文档描述「目标设计」，与代码同步演进；不是愿景蓝图。

## 1. 定位

smart_cs 是一个**面向 B 端企业的智能客服底座**：

- **底座，不是成品**：提供框架、抽象与可插拔能力，不绑定行业；行业能力以
  「业务包（pack）」形态注入。
- **企业内部，不是 C 端 SaaS**：默认部署在企业内网或私有云，多租户首先是
  「企业内多业务线」隔离，而非公有云多客户。
- **AI-native, Agent-ready**：从第一天就把 LLM/Agent 视为一等参与者，
  把「人请求」与「Agent 请求」并列治理。

不做：
- 不做企业内通用 OpenAPI 操作台（那是仓库另一个项目 `chatflow_ai` 的定位）
- 不做客服领域的 BI / 报表大屏（接管数据出口，不做可视化）
- 不替代企业自有 IM / 工单系统，而是与之集成

## 2. 顶层架构：「接-知-答-控」四环节

```
              ┌─────────────────────────────────────────────────────┐
              │                    租户与配置                        │
              │  Tenant / Workspace / Config Loader / Secret Vault  │
              └─────────────────────────────────────────────────────┘
                                       │
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        ▼              ▼               ▼               ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌────────────┐   ┌──────────┐   ┌─────────┐
   │  接     │   │  知     │   │   答       │   │  控      │   │ 可观测  │
   │Reception│   │Knowledge│   │ Answer/Act │   │ Control  │   │Observe  │
   └────┬────┘   └────┬────┘   └─────┬──────┘   └────┬─────┘   └────┬────┘
        │             │              │                │              │
        ▼             ▼              ▼                ▼              ▼
   Channel        KB / Retriever  Orchestrator   Guardrail       Metrics
   Gateway        Document        (LangGraph)    AuditLog        Tracing
   Identity       Indexer         Skill/Flow     QualityCheck    Logger
   SessionStore   CustomerProfile ToolGuard      PII / Quota
                                  Handoff
                                  Ticket
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   LLM Clients   │
                              │ OpenAI/Claude/Qwen
                              └─────────────────┘
```

## 3. 目录结构

```
smart_cs/
├── docs/                       # 设计文档
├── examples/                   # 示例（hello-world + 行业 quickstart）
├── tests/
└── smart_cs/                   # Python 包
    ├── tenancy/                # 多租户
    ├── config/                 # 配置加载（YAML + 环境变量）
    ├── reception/              # 「接」—— 多渠道接入
    │   ├── gateway.py          # ChannelGateway：渠道统一入口
    │   ├── channel.py          # Channel 抽象
    │   ├── identity.py         # IdentityResolver：跨渠道身份打通
    │   └── channels/           # console/api/web/email/...
    ├── session/                # 会话状态
    │   ├── session.py          # Session/Conversation
    │   ├── turn.py             # 对话轮次
    │   ├── slots.py            # 槽位
    │   ├── stack.py            # 对话栈（借鉴 LIFO）
    │   └── store/              # memory/redis/mysql
    ├── customer/               # 客户与画像
    ├── knowledge/              # 「知」—— 知识与检索
    │   ├── base.py             # KnowledgeBase 抽象
    │   ├── document.py         # Document/Chunk
    │   ├── retriever.py        # 检索（向量/全文/规则）
    │   ├── embedder.py
    │   └── store/              # memory/qdrant/faiss
    ├── nlu/                    # 意图理解与路由
    │   ├── router.py           # IntentRouter
    │   └── command_generator.py
    ├── skills/                 # 「答」—— 技能/Flow/Action
    │   ├── skill.py            # Skill 抽象
    │   ├── flow.py             # Flow 定义
    │   ├── action.py           # Action 抽象
    │   ├── builtin/            # faq/handoff/ticket/outreach/...
    │   └── tools/              # 工具门控（核心：ToolGuard）
    ├── handoff/                # 转人工
    ├── ticket/                 # 工单
    ├── orchestrator/           # 编排（LangGraph）
    │   ├── graph.py
    │   ├── state.py
    │   └── nodes/              # perceive/understand/route/retrieve/act/respond/audit
    ├── policy/                 # 决策策略
    ├── governance/             # 「控」—— 治理
    │   ├── audit.py
    │   ├── guardrail.py        # 敏感词/合规
    │   ├── qa.py               # 自动质检
    │   ├── pii.py              # PII 脱敏
    │   └── quota.py            # 配额
    ├── observability/          # 指标/追踪/日志
    ├── llm/                    # LLM 客户端封装
    ├── api/                    # FastAPI server
    ├── cli/                    # CLI 入口（init/run/shell/index/...）
    ├── packs/                  # 行业业务包（可选）
    └── shared/                 # 工具/异常/类型/常量
```

## 4. 核心抽象

### 4.1 Tenant / Workspace

`Tenant` 表达「企业」或「业务线」级别隔离。`Workspace` 在租户内细分（如
某业务线下的「售前」「售后」两个客服坐席组）。

所有面向数据的对象（Session、Customer、KB、Ticket）都带 `tenant_id`，
按租户隔离查询。`TenantContext` 是请求级上下文（contextvar），中间件
注入，下层无需显式传递。

### 4.2 Channel / ChannelGateway

`Channel` 抽象一个具体接入方式。两组接口：

- `InputChannel`: 上行（用户消息进入系统）
- `OutputChannel`: 下行（系统消息发回给用户）

`ChannelGateway` 是上行入口的统一聚合，把不同渠道的原始事件（HTTP 请求 /
WebSocket 帧 / 邮件 / 微信回调）归一化为 `InboundMessage`，注入租户上下文，
派发给 `Orchestrator`。

参考万里汇「一套 API 接入 300+ 本地支付」——这里是「一套对话内核 + N 个 Channel 适配」。

### 4.3 Session

`Session` = 一次对话生命周期的状态聚合：

- `slots: Dict[str, Slot]`
- `turns: List[Turn]`
- `stack: DialogueStack`（LIFO，支持多任务嵌套与中断恢复）
- `customer: Optional[Customer]`
- `actor: SessionActor`（`human` / `agent` / `mixed`）—— **一等公民**

`SessionStore` 提供持久化：默认 memory，生产用 Redis 或 MySQL。

### 4.4 KnowledgeBase / Retriever

`KnowledgeBase` 抽象一组知识源。一个租户可以挂多个 KB（FAQ 库、产品文档、
工单历史、业务数据 API）。`Retriever` 在多 KB 上检索并融合。

支持三类检索：
- **关键词检索**（基于 BM25 / 倒排）—— 默认实现
- **向量检索**（sentence-transformers / 外部 embedding）—— 可选
- **图谱检索 / 业务系统 API**（通过 `KBAdapter`）—— 可选

**借鉴本地清算优先**：先查 FAQ/缓存命中，再走 LLM，降低成本与延迟。

### 4.5 Skill / Flow / Action / Tool

- **Skill** 是面向用户的能力单元（如「查订单」「申请退款」「咨询政策」）。
- **Flow** 是 Skill 的内部编排（多步业务办理）。
- **Action** 是 Flow 内一步执行单元（如调外部 API、查 KB、回复文本）。
- **Tool** 是 Action 内可被 Agent 自主调用的能力（如 `query_order`）。

**ToolGuard**（参见 [business_insight.md](./business_insight.md) §2.4）：

```python
ToolGuard(
    tools=["query_order", "query_logistics"],  # 白名单
    quota=ToolQuota(calls=20, tokens=10000),   # 单会话配额
    require_confirmation=["refund", "cancel_order"],  # 二次确认
    expire_after=timedelta(minutes=30),         # 会话结束自动回收
)
```

每个 Skill/Agent 实例运行时拿到的不是「无限工具集」，而是一份**受限工具凭证**，
类似万里汇 VCC：用完即销，可控可审计。

### 4.6 Orchestrator

`Orchestrator` 用 LangGraph 编排消息处理流。节点：

```
perceive → understand → route → retrieve → act → respond → audit
                          ↓        ↓        ↓
                          ↓        ↓     handoff?
                          ↓     skill.run
                       skill选择
```

- `perceive`：从 InboundMessage 构建/恢复 Session
- `understand`：NLU（意图、槽位、命令生成）
- `route`：选择 Skill / 决定走 Flow 还是 KB 还是转人工
- `retrieve`：触发 KB 检索（如果需要）
- `act`：执行 Skill / Flow / Action / Tool
- `respond`：生成最终回复
- `audit`：写审计日志、上报指标

### 4.7 Policy

`PolicyEnsemble` 按 priority 排序询问各 Policy，取第一个出非弃权的预测：

| Policy | priority | 职责 |
|---|---|---|
| `FlowPolicy` | 100 | 推进 Flow（栈顶为 FlowFrame 时绝对优先） |
| `KBPolicy` | 50 | KB 命中走问答 |
| `HandoffPolicy` | 30 | 触发转人工（用户主动 / 系统触发 / SLA 兜底） |
| `FallbackPolicy` | 10 | 兜底（LLM 自由生成 / 模板「我没听懂」） |

### 4.8 Governance（控）

- `Guardrail`：上下行内容审核，敏感词/合规模板
- `PIIScrubber`：日志/审计前的 PII 脱敏
- `Quota`：租户级/Agent 级/工具级配额
- `AuditLog`：结构化审计事件（who/when/what/result）
- `QualityCheck`：会话结束后自动评分（CSAT 预测、违规检测）

## 5. 消息处理时序

```
用户消息（任意渠道）
  ↓ Channel.receive
ChannelGateway → InboundMessage(+TenantContext)
  ↓ Orchestrator.invoke
Graph: perceive → understand → route
                                 │
                  ┌──────────────┼─────────────┐
                  ▼              ▼             ▼
              FlowPolicy      KBPolicy   HandoffPolicy
                  │              │             │
                  └──────────────┼─────────────┘
                                 ▼
                         act → respond → audit
                                 │
                                 ▼
                     OutputChannel.send（同一通道或转人工通道）
```

## 6. 多租户与配置

- `config/settings.py`：Pydantic Settings，环境变量 / `.env` / YAML 优先级
- `tenants.yml`：声明租户、Workspace、可用通道、可用技能、可用 KB、配额
- `${VAR_NAME:default}` 占位语法（与 chatflow_ai 一致）
- 密钥不入 YAML：走 env / Vault / 公司 KMS

## 7. 与 chatflow_ai 的关系

| 维度 | chatflow_ai | smart_cs |
|---|---|---|
| 定位 | 对话式 OpenAPI 操作台 | 通用智能客服底座 |
| 主用户 | 企业内业务人员（运营/风控/测试） | 企业客户 + 内部客服 + Agent |
| 核心机制 | LLM 抽参 → 调 OpenAPI | 多渠道接入 → NLU → 多技能编排 → 治理 |
| 共享思路 | LIFO 对话栈、Command/Action 分层、Flow YAML、LangGraph 编排 | 同 ← 借鉴成熟做法 |
| 共享 | 同一个仓库，按需各取所需 | 同 |

smart_cs **不依赖** chatflow_ai 包，但概念上借鉴了它的对话栈、Command/Action
分层、Policy Ensemble 等设计；某些 utils 可能复制粘贴而不是依赖，确保两个
项目可以独立演进。

## 8. 技术栈

| 层 | 选型 | 备注 |
|---|---|---|
| Web | FastAPI + Uvicorn | REST + WebSocket |
| 编排 | LangGraph | StateGraph 多节点 |
| LLM | LangChain (OpenAI/Anthropic/Qwen) | 自封一层 `LLMClient` 隔离差异 |
| 校验 | Pydantic v2 | 配置 + 请求体 |
| 存储 | SQLAlchemy + Redis | 默认 memory；生产用 Redis/MySQL |
| 检索 | sentence-transformers (可选) + BM25 | 默认关键词，向量按需开启 |
| 配置 | ruamel.yaml | YAML + ${VAR} 占位 |
| CLI | Click | 入口 `smart-cs` |
| Python | ≥ 3.10 | |

## 9. 关键设计决策

### 9.1 为什么「接-知-答-控」而不是「NLU-DM-NLG」

传统对话系统是「NLU → DM → NLG」三段式。客服业务实际更接近
「接-知-答-控」四段：

- 「接」单独成段是因为渠道复杂度本身就是一个产品问题（弃单率随入口体验差）
- 「控」单独成段是因为治理在企业级是硬约束，不能塞进 NLG 后置打补丁

### 9.2 为什么把 ToolGuard 当一等抽象

照搬万里汇 VCC 思路：Agent 自主调工具是趋势，但「Agent 直连主账户」是事故根源。
把「能调什么、调多少、调失败怎么办、调完怎么回收」做成框架级抽象，业务无需
为每个 Skill 自己重新实现一遍。

### 9.3 为什么 Session.actor 分 human/agent/mixed

文章核心论断之一是「支付主体从人变成 AI 和人并存」。客服同理。从第一天
就让限流、审计、计费按 `actor` 维度切分，避免后续重写。

### 9.4 为什么本地命中优先

每条消息默认先过 FAQ/缓存/规则，命中即返回；只有未命中才进 LLM。
直接借鉴万里汇「能用本地清算解决的，就不走跨境通道」。

### 9.5 为什么行业能力做成 pack 而不是核心

万里汇用「万里汇 + Alipay+ + Antom + Bettr」组合不同企业。客服行业差异
（电商售后 vs 金融合规 vs 内部 IT）远大于共性。底座只做正交基础设施，
行业能力做 pack，避免底座被某一行业绑架。

## 10. 入口速查

| 想做 | 看哪 |
|---|---|
| 看一条消息怎么走完整流程 | `orchestrator/graph.py` → `orchestrator/nodes/*.py` |
| 加新渠道 | `reception/channels/` 下继承 `Channel` |
| 加新技能 | `skills/builtin/` 或业务包，继承 `Skill` |
| 加新工具（Agent 可调） | `skills/tools/` 注册 + 配 `ToolGuard` |
| 加新 KB | `knowledge/store/` 下实现 `KnowledgeStore` |
| 加 LLM Provider | `llm/` 下实现 `LLMClient` |
| 改路由策略 | `policy/` 下加 Policy 并在 ensemble 注册 |
| 加治理规则 | `governance/guardrail.py` 注册规则 |
| 起服务 | `smart-cs run --config examples/hello/config.yml` |
| 对话调试 | `smart-cs shell --config examples/hello/config.yml` |

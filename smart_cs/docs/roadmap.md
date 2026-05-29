# smart_cs 路线图

> 与 [architecture.md](./architecture.md) 配对阅读。
> **原则**：先完成底座 MVP，再做行业 pack，最后做生产工程化。
> 时间是单人工程小时估算。

---

## 阶段 0：底座最小可跑（当前轮交付）

**目标**：搭出「接-知-答-控」四环节骨架，跑通 hello-world。

| # | 项 | 状态 |
|---|---|---|
| 0.1 | 目录骨架 + 包结构 + `__init__.py` | ✅ 本轮 |
| 0.2 | 4 份核心文档（architecture / business_insight / roadmap / quickstart） | ✅ 本轮 |
| 0.3 | 核心抽象：Tenant / Channel / Session / KB / Skill / Tool / Policy | ✅ 本轮 |
| 0.4 | 最小可跑：console channel + memory session + FAQ KB + faq_answer skill | ✅ 本轮 |
| 0.5 | CLI `smart-cs init / run / shell` 骨架 | ✅ 本轮 |

**结束标准**：`python -m smart_cs shell --config examples/hello/config.yml`
能跟最小 FAQ 知识库对话。

---

## 阶段 1：可对外提供服务的 MVP

**目标**：能被一个真实企业场景试用。

### 1.1 NLU 与编排
- LLM-based IntentRouter（接入 OpenAI/Qwen/Claude）—— 2 天
- LangGraph 五节点完整化（perceive/understand/route/act/respond） —— 2 天
- 对话栈 LIFO 完整实现 + 中断恢复 —— 1 天

### 1.2 渠道
- HTTP REST channel（FastAPI）—— 1 天
- WebSocket / SocketIO channel —— 1 天
- Console channel 已 done

### 1.3 知识库
- BM25 关键词检索默认实现 —— 1 天
- 向量检索（sentence-transformers）可选 —— 1 天
- Document 增量索引 + 文件变更监听 —— 1 天

### 1.4 转人工与工单
- HandoffManager + 简单排队 —— 2 天
- TicketService（创建 / 流转 / 关闭）—— 2 天
- SLA 兜底（X 秒无应答自动升级）—— 1 天

### 1.5 治理基础
- Guardrail（敏感词 + 简单 LLM 内容审核）—— 1 天
- AuditLog（结构化日志写文件 / DB）—— 1 天
- Quota（租户 / 会话 级 Token 配额）—— 1 天

**阶段 1 合计：约 3 周。**
**结束标准**：能在测试环境跑一个电商售后/SaaS 工单的 demo。

---

## 阶段 2：Agent-ready 与行业包

**目标**：兑现 "Agent 客服一等公民"、"行业能力可插拔" 两条承诺。

### 2.1 ToolGuard（核心，VCC 思想落地）
- ToolGuard 抽象 + 凭证签发 + 调用拦截 + 自动回收 —— 3 天
- 工具白名单 / 配额 / 二次确认机制 —— 2 天
- Agent Session 类型与限流维度区分 —— 1 天
- 审计日志按 Agent 维度可查询 —— 1 天

### 2.2 行业 pack 框架
- `BusinessPack` 抽象 + 加载机制 —— 2 天
- pack 注册扩展点：Skill / Tool / Channel / KB / Guardrail —— 2 天
- 内置一个示例 pack（如 `packs/ecommerce`）跑通 —— 2 天

### 2.3 客户画像与多源融合
- CustomerProfile 抽象 + 简单融合规则 —— 2 天
- 与业务系统 API 集成（KB 适配器形式）—— 2 天

**阶段 2 合计：约 3 周。**

---

## 阶段 3：生产工程化

**目标**：从「能跑」过渡到「能在企业生产环境用」。**只在阶段 0-2 完成
且有真实试用后启动。**

| # | 项 | 工时 |
|---|---|---|
| 3.1 | 持久化默认从 memory → Redis + MySQL | 3 天 |
| 3.2 | 多租户隔离：行级安全 / Schema 隔离 / 缓存键前缀 | 3 天 |
| 3.3 | OpenTelemetry：核心路径 span | 2 天 |
| 3.4 | 自动质检（QA）模型 | 3 天 |
| 3.5 | 密钥治理：Vault 适配 | 2 天 |
| 3.6 | DB schema 迁移（Alembic） | 1 天 |
| 3.7 | 单元测试覆盖核心抽象 50% | 5 天 |
| 3.8 | CI（ruff + mypy + pytest） | 1 天 |
| 3.9 | 性能压测 + 限流与熔断 | 3 天 |
| 3.10 | 部署文档 + Docker / Helm | 2 天 |

**阶段 3 合计：约 5 周。**

---

## 阶段 4：差异化能力（视真实用户反馈优先级）

候选项，按真实需求挑：

- **嵌入式 SDK / 白标**（借鉴万里汇白标）：JS SDK 嵌入企业自有 App
- **主动外呼 / 触达**：会话主动发起，结合营销/通知场景
- **多模态**：语音通道、图片识别（截图客诉）
- **预测式路由**（借鉴 Falcon）：基于历史对话预测意图分布，预生成答案
- **跨会话记忆**：长期客户偏好建模
- **多语言 + 本地化**：与渠道协同的语言/时区/合规切换

---

## 暂不做（明确）

- ❌ **可视化对话流编辑器**：等真实业务用起来再说
- ❌ **完整的对话日志检索 UI**：底层 API 提供即可，UI 留给业务自建
- ❌ **机器学习训练（DIET 等）**：MVP 阶段全靠 LLM + 检索，不引入训练
- ❌ **多 Agent 协同（Multi-Agent）**：单 Agent + ToolGuard 已能覆盖 80% 场景
- ❌ **从 OpenAPI 自动生成 Flow**：那是 chatflow_ai 的范畴，不重复造
- ❌ **接管已有客服系统的迁移工具**：业务包形式提供适配器即可

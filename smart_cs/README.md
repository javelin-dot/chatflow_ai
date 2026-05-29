# smart_cs

**通用智能客服底座** — 面向 B 端企业内部客服 PaaS。

> 本仓库与同目录的 `chatflow_ai` 平级、独立。两者共享一个仓库但代码隔离；
> 概念上 smart_cs 借鉴了 chatflow_ai 的若干设计（LIFO 对话栈、Skill/Tool
> 分层、Policy Ensemble），但不以 chatflow_ai 包为依赖。

## 设计哲学

借鉴万里汇（WorldFirst / 蚂蚁国际）AI 出海全球收付一体化解决方案的
「**收-管-付-控**」四环节范式，平移为客服领域的「**接-知-答-控**」：

- **接**（Reception）：多渠道接入，一套对话内核 + N 个 Channel 适配器
- **知**（Knowledge）：多源知识与上下文，本地命中优先（FAQ/缓存 命中即返回）
- **答**（Answer/Action）：技能/Flow/Action，Agent 工具调用走 ToolGuard
- **控**（Control）：质检/审计/风控/配额；ToolGuard 灵感来自 VCC 虚拟卡

详见 [docs/business_insight.md](./docs/business_insight.md) 与
[docs/architecture.md](./docs/architecture.md)。

## 快速开始

```bash
cd /Users/jiangjianmin/ai/code/chatflow_ai
pip install -r smart_cs/requirements.txt
python -m smart_cs shell --config smart_cs/examples/hello/config.yml
```

不依赖任何 LLM Key，演示走的是 **关键词 FAQ 匹配 + 转人工 + 兜底应答**，
跑通「接 → 知 → 答 → 控」最小闭环。

## 文档

- [docs/architecture.md](./docs/architecture.md) — 整体架构与目录
- [docs/business_insight.md](./docs/business_insight.md) — 万里汇业务借鉴映射
- [docs/roadmap.md](./docs/roadmap.md) — 路线图
- [docs/quickstart.md](./docs/quickstart.md) — 快速开始与配置详解

## 状态

当前为 **阶段 0（底座最小可跑）**：

- ✅ 四环节目录骨架与抽象类
- ✅ Console 通道 + FAQ KB + 关键词路由 + 三种内置 Skill（faq_answer / handoff / fallback）
- ✅ Guardrail / AuditLog / SessionQuota
- ✅ ToolGuard 抽象（VCC 思想落地，待 Phase 2 接 LLM 工具调用）
- ⏳ Phase 1：LLM 路由、HTTP/WebSocket 通道、BM25/向量检索、工单 SLA
- ⏳ Phase 2：行业 pack 框架、Agent 自主调用工具实战
- ⏳ Phase 3：生产工程化（持久化、可观测性、测试、CI、密钥治理）

详见 [docs/roadmap.md](./docs/roadmap.md)。

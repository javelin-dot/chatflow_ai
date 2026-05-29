# hello — smart_cs 最小示例

无需任何 LLM Key，演示「接 → 知 → 答 → 控」全链路最小闭环。

## 跑起来

在仓库根目录：

```bash
cd /Users/jiangjianmin/ai/code/chatflow_ai
python -m pip install -r smart_cs/requirements.txt
python -m smart_cs.cli.main shell --config smart_cs/examples/hello/config.yml
```

或者从 `smart_cs/` 目录直接：

```bash
cd smart_cs
python -m smart_cs shell --config examples/hello/config.yml
```

## 试一试

```
You> 你好
Bot> 您好！我是 smart_cs 智能客服 demo，您可以问我「营业时间」「怎么退款」「物流多久」，或者输入「人工」转接客服。

You> 营业时间
Bot> 我们的客服在线时间是 09:00-22:00（北京时间，全年无休）。

You> 怎么退款
Bot> 在「我的订单」→ 选择订单 → 点击「申请退款」即可发起退款，资金将在 3 个工作日内原路退回。

You> 人工
Bot> 已为您转接到人工客服，请稍候。

You> 早上几点能吃猪
Bot> 抱歉，我暂时没理解您的问题，可以换个说法或输入「人工」转接客服。

You> exit
```

每一轮还会在 stderr 输出一条 `[audit] {...}` 审计事件 —— 这是「控」环节的最小演示。

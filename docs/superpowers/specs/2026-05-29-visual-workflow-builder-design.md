# 可视化业务流程编排系统 — MVP 设计文档

## 背景与目标

当前 `chatflow_ai` 已具备 OpenAPI 集成、服务注册、自然语言生成 Flow YAML 等能力，但缺少面向业务用户的可视化编排界面。业务人员（测试 / 运营 / 风控）需要能够：

1. 输入 Swagger 链接，系统自动解析并展示可用接口
2. 以步骤列表的方式组合接口调用，配置参数映射
3. 执行编排好的流程，真实调用测试环境接口
4. 查看执行结果和响应数据

## 设计决策

| 维度 | 决策 | 原因 |
|------|------|------|
| 目标用户 | 业务 / 非技术用户 | 开发者可直接维护 YAML |
| 数据策略 | 真实调用测试环境 | 用户明确要求 |
| 认证方式 | 登录接口获取 token，后续自动注入 | 测试环境无独立认证系统 |
| 编排复杂度 | 线性流水线 | MVP 够用，V2 再扩展分支/循环 |
| 前端形态 | **步骤列表式**（非节点编辑器） | 线性流程表达力等价，开发成本 1/3 |
| 技术栈 | FastAPI + React (Ant Design) | 前后端分离，最灵活 |

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      React 前端 (Ant Design)                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ 服务管理页   │  │ 流程编排页    │  │ 流程执行页               │ │
│  │ - Swagger URL│  │ - 步骤列表    │  │ - 执行按钮               │ │
│  │ - 接口浏览   │  │ - 接口选择    │  │ - 实时日志               │ │
│  │ - 手动触发   │  │ - 参数映射    │  │ - 响应展示               │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ REST API
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI 后端                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Service API │  │ Workflow API │  │  Execute API            │ │
│  │ /services   │  │ /workflows   │  │  /workflows/{id}/run    │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
│                              │                                    │
│  ┌───────────────────────────┼──────────────────────────────┐    │
│  │              核心引擎（复用 + 扩展）                         │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │    │
│  │  │OpenAPIRegistry│ │WorkflowRunner│ │SessionTokenMgr  │  │    │
│  │  │（已有）      │  │（新增）      │  │（新增）         │  │    │
│  │  └─────────────┘  └──────────────┘  └─────────────────┘  │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 数据模型

### WorkflowTemplate（流程模板）

```python
class WorkflowTemplate(BaseModel):
    id: str                      # UUID
    name: str                    # 用户命名，如"创建KYC客户"
    description: str             # 可选描述
    service_id: str              # 关联的Swagger服务ID
    steps: List[WorkflowStep]
    created_at: datetime
    updated_at: datetime

class WorkflowStep(BaseModel):
    id: str                      # step_1, step_2...
    name: str                    # 用户可编辑，默认取接口summary
    operation_id: str            # 选中的OpenAPI operationId
    # 参数映射：key=参数名，value=映射规则
    parameter_mapping: Dict[str, ParameterMapping]
    body_mapping: Optional[Dict[str, ParameterMapping]]
    # 是否将响应写入上下文供后续步骤使用
    save_response_to: Optional[str]   # 如 "login_result"

class ParameterMapping(BaseModel):
    source: Literal["const", "context", "prompt"]   # 来源类型
    value: str                                        # 具体值
    # const:"13800138000"
    # context:"step_1.data.token"
    # prompt:"请输入手机号"   —— 执行时弹出输入框
```

### 执行上下文（运行时）

```python
class ExecutionContext(BaseModel):
    workflow_id: str
    run_id: str
    status: Literal["running", "success", "failed"]
    step_results: Dict[str, StepResult]   # step_id -> 结果
    # 全局变量池，支持任意步骤写入、任意步骤读取
    variables: Dict[str, Any]

class StepResult(BaseModel):
    step_id: str
    status: Literal["pending", "running", "success", "failed", "skipped"]
    request: Dict[str, Any]       # 实际发出的请求（脱敏后）
    response: Dict[str, Any]      # 接口原始响应
    extracted: Dict[str, Any]     # 从响应提取的变量
    error: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
```

## API 设计

### Service 管理

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/services` | 注册Swagger服务（输入URL，后台解析） |
| GET | `/api/v1/services` | 列出已注册服务 |
| GET | `/api/v1/services/{id}/operations` | 获取服务下所有接口 |
| GET | `/api/v1/services/{id}/operations/{op_id}` | 获取接口详情（参数、body schema） |
| DELETE | `/api/v1/services/{id}` | 移除服务 |

### 工作流管理

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/workflows` | 创建工作流模板 |
| GET | `/api/v1/workflows` | 列出自己的工作流 |
| GET | `/api/v1/workflows/{id}` | 获取工作流详情 |
| PUT | `/api/v1/workflows/{id}` | 更新工作流 |
| DELETE | `/api/v1/workflows/{id}` | 删除工作流 |

### 执行控制

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/workflows/{id}/runs` | 发起一次执行 |
| GET | `/api/v1/workflows/{id}/runs` | 列出执行历史 |
| GET | `/api/v1/runs/{run_id}` | 查询执行状态/结果 |
| GET | `/api/v1/runs/{run_id}/logs` | SSE 实时日志流 |

### 会话认证（测试环境专用）

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/sessions` | 登录测试环境（调用注册/登录接口） |
| DELETE | `/api/v1/sessions` | 清除当前会话/token |
| GET | `/api/v1/sessions` | 查询当前会话状态 |

## 前端页面设计

### 页面1：服务管理（Service Manager）

布局：表单区 + 接口列表区

- **注册服务**：输入 Swagger URL（如 `http://test-kyc.internal/v3/api-docs`），后端解析后展示服务名称和接口数量
- **接口浏览器**：表格展示所有接口（operationId, method, path, summary），支持按tag筛选、关键字搜索
- **快速测试**：在接口列表中点击"测试"，弹出参数表单，直接调用并展示响应（无需编排，单接口调试）

### 页面2：流程编排（Workflow Builder）

布局：左侧面板（步骤列表）+ 右侧详情区

- **步骤列表**：垂直排列的Step卡片，每个卡片显示序号、接口名、method/path
  - 支持拖拽排序（上下移动）
  - 支持添加、删除步骤
  - 点击卡片展开右侧详情
- **右侧详情区**：
  - 接口选择下拉框（从已注册服务中选择）
  - 参数映射表格：
    - 参数名 | 必填 | 来源类型 | 值
    - 来源类型：`常量` / `上一步响应` / `执行时输入`
    - 选择`上一步响应`时，级联选择前序步骤 + JSONPath
  - Body映射：JSON结构可视化编辑器（递归展开object字段，每个叶子节点选择来源）
  - 响应保存：输入变量名（如 `login_token`），供后续步骤引用

### 页面3：流程执行（Workflow Runner）

布局：执行控制区 + 步骤结果区

- **执行控制**：选择要执行的工作流 → 点击"运行"
- **步骤结果区**：每个Step展示一个卡片
  - 运行中：旋转loading + 实时日志（SSE推送）
  - 成功：绿色勾 + 请求/响应折叠面板
  - 失败：红色叉 + 错误信息 + 响应体
  - 支持"从当前步骤重试"、"单步调试"

## Token 管理机制（SessionTokenManager）

测试环境认证流程：

1. 用户在"会话管理"页面配置登录接口（选择 operationId，填写用户名/密码）
2. 后端调用登录接口，从响应中提取 token（支持配置 JSONPath，如 `data.token`）
3. Token 存入内存/Redis（键：`session:{user_id}`），后续所有接口调用自动注入 `Authorization: Bearer {token}`
4. Token 过期策略：
   - 首次 401 时自动触发登录刷新
   - 或用户手动点击"刷新Token"

```python
class SessionTokenManager:
    async def login(self, service_id: str, operation_id: str, credentials: dict) -> str:
        """调用登录接口，提取并存储token"""

    async def get_token(self, service_id: str) -> Optional[str]:
        """获取当前有效token"""

    def inject_auth(self, headers: dict, service_id: str) -> dict:
        """向请求头注入认证信息"""
```

## 执行引擎（WorkflowRunner）

执行流程：

```
1. 加载 WorkflowTemplate
2. 初始化 ExecutionContext（variables = {}）
3. FOR each step IN template.steps:
   a. 从 OpenAPIRegistry 获取 operation 定义
   b. 解析 parameter_mapping：
      - const: 直接用值
      - context: 从 variables 中按路径读取
      - prompt: 暂不支持（MVP先不做交互式输入，后续扩展）
   c. 解析 body_mapping（递归解析嵌套对象）
   d. 调用 SessionTokenManager.inject_auth 注入token
   e. 通过 OpenAPIClient.call_operation 发送请求
   f. 将响应存入 step_results[step.id]
   g. 如果配置了 save_response_to，提取字段写入 variables
   h. 如果失败，停止执行（或根据策略跳过/重试）
4. 返回完整 ExecutionContext
```

## 错误处理

| 场景 | 行为 |
|------|------|
| Swagger URL 不可访问 | 前端提示"无法访问该地址，请检查网络和URL" |
| 接口调用 4xx/5xx | 步骤卡片变红，展示HTTP状态码 + 响应体；执行停止 |
| 参数映射缺失必填字段 | 执行前校验，提前报错"步骤X缺少必填参数Y" |
| Token 失效 | 自动触发一次登录刷新；若仍失败则提示"请检查登录配置" |
| 上一步响应字段不存在 | 步骤执行时报错"变量X未找到" |

## 与现有代码的集成点

| 新功能 | 复用/改造点 |
|--------|------------|
| Swagger 解析 | 直接复用 `OpenAPIClient.from_source` + `extract_catalog` |
| 接口调用 | 复用 `OpenAPIClient.call_operation`，扩展 `headers` 注入 |
| 服务注册 | 复用 `OpenAPIRegistry.register`，新增 HTTP API 封装 |
| Flow 概念对齐 | WorkflowTemplate.steps 与现有 Flow.steps 语义兼容，未来可互转 |

## 存储策略（MVP）

- **WorkflowTemplate**：JSON 文件存储（`~/.chatflow/workflows/`），MVP 阶段无需数据库
- **SessionToken**：内存存储（单用户/单进程），后续多用户时换 Redis
- **ExecutionHistory**：JSON 文件存储，保留最近 100 次执行记录

## 不做的事（明确边界）

- ❌ 不支持分支/循环（V2）
- ❌ 不支持交互式执行时输入（prompt 类型映射）
- ❌ 不支持多用户并发（MVP 单用户本地运行）
- ❌ 不支持接口Mock（真实调用优先）
- ❌ 不做复杂权限模型（测试环境内部工具）
- ❌ 前端不做拖拽节点编辑器（步骤列表足够）

## 估算

| 模块 | 工时 |
|------|------|
| FastAPI 后端 API + WorkflowRunner | 2 天 |
| SessionTokenManager + 认证注入 | 1 天 |
| React 前端（3个页面 + API 对接） | 3 天 |
| 前后端联调 + 测试 | 1 天 |
| **总计** | **~1 周** |

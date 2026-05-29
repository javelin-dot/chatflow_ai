# 存储层架构与数据库迁移设计

## 当前状态（MVP）

MVP 使用 **JSON 文件存储**，数据目录统一在：

```
~/.chatflow/mvp-data/
├── registry/          # 已注册服务配置（ServiceSpec）
│   ├── snpcsc.json
│   └── auth-service.json
└── workflows/
    ├── templates/     # 流程模板（WorkflowTemplate）
    │   ├── wf-xxx.json
    │   └── wf-yyy.json
    └── history/       # 执行记录（ExecutionContext）
        ├── run-aaa.json
        └── run-bbb.json
```

### 为什么 MVP 用 JSON 文件

- **零依赖**：不需要安装/配置 PostgreSQL、MySQL
- **零迁移**：模型变更时不需要执行 alembic migrate
- **易调试**：直接打开 JSON 文件即可查看数据状态

### 代码位置

| 模块 | 文件 | 说明 |
|------|------|------|
| 服务注册 | `chatflow_ai/integrations/registry_storage.py` | `RegistryStorage` |
| 工作流 | `chatflow_ai/workflow/storage.py` | `WorkflowStorage` |
| 协议定义 | `chatflow_ai/shared/storage_protocol.py` | `RegistryStorageProtocol` / `WorkflowStorageProtocol` |

---

## 未来迁移到标准数据库

### 第一步：实现 SQLAlchemy 存储层

创建新的存储实现：

```python
# chatflow_ai/integrations/sqlalchemy_registry_storage.py
class SqlAlchemyRegistryStorage:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def save(self, spec: ServiceSpec) -> None:
        async with self.session_factory() as session:
            # upsert into service_specs table
            ...

    async def load(self, name: str) -> ServiceSpec | None:
        ...

    async def list_names(self) -> list[str]:
        ...

    async def delete(self, name: str) -> bool:
        ...
```

```python
# chatflow_ai/workflow/sqlalchemy_storage.py
class SqlAlchemyWorkflowStorage:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def save_workflow(self, workflow: WorkflowTemplate) -> None:
        ...

    async def load_workflow(self, workflow_id: str) -> WorkflowTemplate | None:
        ...

    # ... 其他方法
```

### 第二步：数据表设计（建议）

```sql
-- 服务注册表
CREATE TABLE service_specs (
    name            VARCHAR PRIMARY KEY,
    spec_url        TEXT NOT NULL,
    base_url        TEXT,
    token_env       TEXT,
    token_header    TEXT DEFAULT 'Authorization',
    token_prefix    TEXT DEFAULT 'Bearer ',
    timeout         FLOAT DEFAULT 30.0,
    default_headers JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 工作流模板表
CREATE TABLE workflow_templates (
    id          VARCHAR PRIMARY KEY,
    name        VARCHAR NOT NULL,
    description TEXT,
    service_id  VARCHAR NOT NULL,
    steps       JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 执行记录表
CREATE TABLE execution_history (
    run_id          UUID PRIMARY KEY,
    workflow_id     VARCHAR NOT NULL,
    status          VARCHAR NOT NULL,
    step_results    JSONB NOT NULL,
    variables       JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 会话认证表（替代内存中的 token/cookie）
CREATE TABLE service_sessions (
    service_id      VARCHAR PRIMARY KEY,
    token           TEXT,
    cookies         JSONB,
    config          JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 第三步：切换存储后端

修改入口点，注入 SQLAlchemy 存储：

```python
# chatflow_ai/integrations/registry.py
from chatflow_ai.integrations.sqlalchemy_registry_storage import SqlAlchemyRegistryStorage

# 在应用启动时
engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/chatflow")
session_factory = async_sessionmaker(engine)

_GLOBAL_REGISTRY = OpenAPIRegistry(
    storage=SqlAlchemyRegistryStorage(session_factory)
)
```

```python
# chatflow_ai/api/workflow_routes.py
_storage = WorkflowStorage(
    backend=SqlAlchemyWorkflowStorage(session_factory)
)
```

### 第四步：一次性数据迁移

```bash
# 1. 启动带 DB 的新版本服务
# 2. 运行迁移脚本
python scripts/migrate_json_to_db.py

# migrate_json_to_db.py 逻辑：
# - 读取 ~/.chatflow/mvp-data/registry/*.json -> insert into service_specs
# - 读取 ~/.chatflow/mvp-data/workflows/templates/*.json -> insert into workflow_templates
# - 读取 ~/.chatflow/mvp-data/workflows/history/*.json -> insert into execution_history
```

---

## 接口契约（重要）

所有存储层实现必须遵守 `chatflow_ai/shared/storage_protocol.py` 中定义的 Protocol。

这样上层代码（`OpenAPIRegistry`、`WorkflowRunner`、`workflow_routes.py`）**不需要任何修改**，只需替换存储实例即可。

---

## 何时应该迁移

| 条件 | 建议 |
|------|------|
| 单机开发/MVP | 继续用 JSON 文件 |
| 多实例部署 | 必须迁移到共享数据库 |
| 高并发写入 | 必须迁移到数据库 |
| 需要审计/查询历史 | 建议迁移到数据库 |
| 生产环境 | 建议 PostgreSQL |

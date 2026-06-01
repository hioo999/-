# M2 验收清单：Agent 基础服务、登录、安全边界和本地闭环

> 项目：律师本地数据主权型 AI 案件知识库工作台  
> 工程目录：`harness-engineering/`  
> 阶段：M2 收口验收  
> 日期：2026-05-22

---

## 1. M2 阶段目标

M2 目标是把 M1 工程骨架推进到可验证的 Agent 基础服务阶段：

```text
Agent 可登录
Agent 可查看状态
本地文件可安全入库
任务状态可追踪
RAG 问答有来源且按案件隔离
模型配置不泄露凭证
平台白名单和健康上报边界可测试
```

---

## 2. 当前实现口径

当前仍保留 stdlib HTTP + SQLite 可运行原型，同时补齐 FastAPI/PostgreSQL/Redis/Qdrant 的目标目录和占位模块。

| 项 | 当前口径 |
|---|---|
| 可运行服务 | `services/platform-api/server.py`、`services/agent-api/server.py` |
| 当前运行时 | Python stdlib HTTP + SQLite |
| 目标运行时 | FastAPI + PostgreSQL + Redis/RQ + Qdrant |
| 当前测试 | `unittest` 32 个用例 |
| 当前部署校验 | Docker Compose config 通过 |
| 当前平台边界 | 平台不接收业务字段，健康上报白名单校验 |

---

## 3. M2 已完成能力

| 能力 | 状态 | 验收方式 |
|---|---|---|
| Platform 控制面原型 | 完成 | 组织、授权、Agent 注册、心跳、健康、审计 API 可用 |
| Agent 数据面原型 | 完成 | 本地目录、案件、文件、解析、RAG、引用 API 可用 |
| FastAPI 目标结构 | 完成 | `services/*/app/` 目录存在 |
| 本地登录 | 完成 | `POST /api/agent/auth/login` |
| Bearer token | 完成 | 未登录访问管理接口返回 401 |
| Agent 状态接口 | 完成 | `GET /api/agent/status` |
| 文件上传安全 | 完成 | 扩展名、路径穿越、base64、大小限制测试 |
| 目录权限检测 | 完成 | `POST /api/agent/data-sources/check-permission` |
| 任务列表和详情 | 完成 | `GET /api/agent/tasks`、`GET /api/agent/tasks/{id}` |
| 失败任务重试 | 完成 | `POST /api/agent/tasks/{id}/retry` |
| RAG 案件隔离 | 完成 | 双案件隔离测试通过 |
| 来源引用结构 | 完成 | citation 返回 case/file/chunk/paragraph/quote 字段 |
| 无依据提示 | 完成 | `insufficient_evidence=true` |
| 问答历史 | 完成 | `GET /api/agent/chats?case_id=...` |
| 模型配置 | 完成 | `GET/POST /api/agent/model-configs` |
| API Key 遮罩 | 完成 | 仅返回 `api_key_masked` |
| 模型测试占位 | 完成 | `test-chat`、`test-embedding` 返回不调用模型的占位结果 |
| 平台白名单复用 | 完成 | server 复用 app/security 和 app/schemas 规则 |
| Agent 健康上报映射 | 完成 | `health_reporter.to_platform_health_payload()` |
| 禁止字段注入测试 | 完成 | 平台健康接口注入 `file_name` 返回 400 |

---

## 4. M2 接口清单

### 4.1 Platform 控制面

| Method | Path | 说明 |
|---|---|---|
| GET | `/health` | 平台健康检查 |
| POST | `/api/platform/organizations` | 创建组织 |
| POST | `/api/platform/licenses` | 创建授权 |
| POST | `/api/platform/agents/register` | Agent 注册 |
| POST | `/api/platform/agents/heartbeat` | Agent 心跳 |
| POST | `/api/platform/agents/health` | Agent 脱敏健康上报 |
| GET | `/api/platform/agents` | Agent 列表 |
| GET | `/api/platform/audit-logs` | 平台审计日志 |

### 4.2 Agent 数据面

| Method | Path | 说明 |
|---|---|---|
| GET | `/health` | Agent 脱敏健康 payload |
| POST | `/api/agent/auth/login` | 本地登录 |
| GET | `/api/agent/auth/me` | 当前用户 |
| POST | `/api/agent/auth/logout` | 登出 |
| GET | `/api/agent/status` | Agent 本地服务状态 |
| POST | `/api/agent/activate` | Agent 激活 |
| POST | `/api/agent/report-health` | 向平台上报脱敏健康 |
| POST | `/api/agent/data-sources/check-permission` | 目录权限检查 |
| GET | `/api/agent/data-sources` | 目录列表 |
| POST | `/api/agent/data-sources` | 添加目录 |
| GET | `/api/agent/tasks` | 任务列表 |
| GET | `/api/agent/tasks/{id}` | 任务详情 |
| POST | `/api/agent/tasks/{id}/retry` | 失败任务重试 |
| GET | `/api/agent/cases` | 案件列表 |
| POST | `/api/agent/cases` | 创建案件 |
| GET | `/api/agent/files` | 文件列表 |
| POST | `/api/agent/files/upload` | 文件上传 |
| POST | `/api/agent/files/parse` | 文件解析和索引 |
| POST | `/api/agent/rag/query` | 案件问答 |
| GET | `/api/agent/chats?case_id=...` | 案件问答历史 |
| GET | `/api/agent/chats/{session_id}` | 会话消息 |
| GET | `/api/agent/model-configs` | 模型配置列表 |
| POST | `/api/agent/model-configs` | 保存模型配置 |
| POST | `/api/agent/model-configs/{id}/test-chat` | Chat 模型测试占位 |
| POST | `/api/agent/model-configs/{id}/test-embedding` | Embedding 模型测试占位 |

---

## 5. M2 安全门禁

| 门禁 | 状态 | 测试覆盖 |
|---|---|---|
| 平台 API 禁止业务字段 | 通过 | `test_m2_platform_health_whitelist_reuse.py` |
| 平台健康只接收白名单字段 | 通过 | `test_m2_security_scaffold.py` |
| 平台数据库无业务表 | 通过 | `test_mvp.py`、`test_m2_security_scaffold.py` |
| Agent 管理接口需要登录 | 通过 | `test_m2_agent_auth_status.py` |
| 文件上传防路径穿越 | 通过 | `test_m2_file_ingestion_tasks.py` |
| 非法扩展名拒绝 | 通过 | `test_m2_file_ingestion_tasks.py` |
| RAG 不串案 | 通过 | `test_m2_case_isolation_citations.py` |
| 无依据不输出确定结论 | 通过 | `test_mvp.py`、`test_m2_case_isolation_citations.py` |
| API Key 不明文回显 | 通过 | `test_m2_model_config_security.py` |
| Agent 健康不含 API Key | 通过 | `test_m2_model_config_security.py` |
| 平台健康注入 file_name 被拒绝 | 通过 | `test_m2_platform_health_whitelist_reuse.py` |

上线红线：

```text
平台业务数据暴露量 = 0
```

---

## 6. 验证命令

标准 M2 验证：

```bash
bash scripts/verify-m2.sh
```

该脚本会执行：

```text
环境检查
32 个 unittest 测试
Platform Docker Compose config 校验
Agent Docker Compose config 校验
```

手动验证命令：

```bash
bash scripts/check-env.sh
python3 -m unittest discover -s tests -p 'test_*.py'
docker compose -f deploy/docker-compose.platform.yml config >/dev/null
docker compose -f deploy/docker-compose.agent.yml config >/dev/null
```

---

## 7. 已知限制

| 限制 | 说明 | 后续阶段 |
|---|---|---|
| 运行时仍是 stdlib HTTP | FastAPI 目标结构已建，尚未正式切换运行入口 | M3/M4 |
| 当前数据库仍是 SQLite | PostgreSQL migration 已建，尚未接入运行时 | M3/M4 |
| Redis/RQ 是 Compose 占位 | 当前任务仍是同步执行 | M4 |
| Qdrant 是 Compose 占位 | 当前检索仍是本地关键词索引 | M6/M7 |
| OCR 是简化占位 | 图片返回 OCR_PENDING 文本 | M6 |
| 模型调用是占位 | test-chat/test-embedding 不调用真实模型 | M7/M8 |
| 前端尚未实现 | 只有目录和 README | M3 |
| 数据库连接器未做 | 一期不做，MVP+ 第四期 | 后置 |
| FastAPI adapter routers 拆分 | M15 已完成，仍需补齐接口文档和交付材料 | M16/M18 |

---

## 8. M2 验收结论

M2 当前达到以下标准：

```text
Agent 可登录
Agent 状态可查看
文件入库和任务可追踪
RAG 有来源且按案件隔离
模型 API Key 不明文回显
平台白名单和健康上报边界可测试
32 个测试通过
Compose 配置通过
```

M2 可判定为：

```text
通过工程级阶段验收，可进入 M3 Agent Console 前端骨架或继续后端 FastAPI/PostgreSQL 迁移。
```

阶段会议补充结论：

```text
FastAPI adapter 路由拆分已在 M15 完成。
当前 adapter 已拆分为领域 routers，并继续复用 Store 业务能力。
下一阶段继续推进接口文档补齐、测试覆盖补强和部署交付材料收口。
```

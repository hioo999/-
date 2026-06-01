# harness-engineering 工程管理说明

> 项目：律师本地数据主权型 AI 案件知识库工作台  
> 工程目录：`harness-engineering/`  
> 管理方式：Harness Engineering 单一工程目录管理  
> 日期：2026-05-22

---

## 1. 目录定位

`harness-engineering/` 是本项目唯一程序工程目录。

以后所有程序代码、工程配置、服务脚本、部署脚本、测试工程、接口文档、工程说明均放入该目录。

项目根目录不得再新增多个程序目录，例如：

```text
platform/
agent/
frontend/
backend/
server/
client/
api/
web/
```

所有工程内容统一归入：

```text
harness-engineering/
```

---

## 2. 项目根目录职责

项目根目录只保留非程序资料：

```text
0 基础配置/
成本估算/
角色库/
需求文档/
harness-engineering/
```

其中：

| 目录 | 说明 |
|---|---|
| `0 基础配置/` | 项目基础配置、参考资料 |
| `成本估算/` | 成本、工期、报价相关文档 |
| `角色库/` | 虚拟团队角色定义 |
| `需求文档/` | PRD、MVP、评审结论等产品需求 |
| `harness-engineering/` | 唯一程序工程目录 |

---

## 3. 工程管理原则

| 原则 | 说明 |
|---|---|
| 单一工程目录 | 所有代码和工程配置只能放在 `harness-engineering/` 下 |
| 控制面和数据面分离 | 平台控制台代码与 Agent 本地代码需要逻辑隔离 |
| 平台不可见 | 平台工程不得设计任何业务数据入口 |
| Agent 本地处理 | 文件、数据库、解析、向量、问答、审计由 Agent 侧工程处理 |
| 模块边界清晰 | 平台、Agent、前端、数据库连接器、RAG、部署、测试分模块管理 |
| 可测试可验收 | 工程结构必须支持平台不可见、数据库只读、权限隔离测试 |

---

## 4. 建议工程结构

V4.1 MVP 建议采用以下结构：

```text
harness-engineering/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── deployment.md
│   ├── security.md
│   └── testing.md
├── apps/
│   ├── platform-console/
│   └── agent-console/
├── services/
│   ├── platform-api/
│   └── agent-api/
├── packages/
│   ├── shared-types/
│   ├── ui-components/
│   └── sdk/
├── agent-modules/
│   ├── file-ingestion/
│   ├── db-connector/
│   ├── document-parser/
│   ├── rag-engine/
│   ├── audit-log/
│   └── health-reporter/
├── deploy/
│   ├── docker-compose.agent.yml
│   ├── docker-compose.platform.yml
│   └── env.example
├── tests/
│   ├── e2e/
│   ├── api/
│   ├── security/
│   └── fixtures/
└── scripts/
    ├── setup-agent.sh
    ├── check-env.sh
    └── export-diagnostics.sh
```

当前已实现 V4.1 MVP M25 工程基线，包含 `platform-api`、`agent-api`、Agent 控制台、部署脚本、分层测试、API 契约、脱敏诊断包、平台不可见验收报告、Agent 运行入口灰度切换、部署配置安全校验、交付物泄漏扫描、交付包边界校验、可复现交付包导出、交付归档自校验、交付包 SHA-256 完整性校验、交付验收证据报告、案件成员访问控制闭环、案件工作台权限态可视化、案件可访问集合状态同步、任务页案件上下文与角色权限展示、交付验证入口和工程文档。

当前默认可运行骨架仍保留 stdlib HTTP + SQLite 原型。M20 在不删除旧入口的前提下，保留可并行运行的 FastAPI 入口，已将 adapter 拆分为领域 routers，并支持通过 `AGENT_RUNTIME=stdlib|fastapi` 灰度切换统一启动入口。

---

## 4.1 MVP 当前实现状态

已实现：

```text
platform-api：组织、授权、Agent 注册、心跳、脱敏健康上报、平台审计日志
agent-api：本地登录、PBKDF2 密码 hash、session 清理、状态、目录权限检查、目录新增、资料目录访问边界、敏感路径拒绝、OCR 命令白名单、目录扫描、案件、文件上传、内容哈希去重、任务入队、待处理任务批量消费、Worker 单轮处理、常驻 Worker、失败自动重试、解析、可选本地 OCR、批量 Embedding 生成、本地向量存储、Qdrant 可选批量 upsert/search、Qdrant 补偿同步、向量相似检索、重试、RAG、真实模型回答生成、引用来源、问答历史、模型配置、API Key 本地加密、模型/Qdrant URL 本地地址约束、模型连通性测试、本地审计日志
agent-console：案件创建/选择、文件上传入队、目录权限检查/新增/扫描、任务刷新/重试/运行待处理/Worker 单轮、模型配置/连通性测试、Qdrant 向量同步、OCR 配置状态、RAG 问答和模型参与状态
tests：API、安全、RAG、平台不可见、凭证安全、案件隔离、健康上报白名单、密码 hash、API Key 加密、URL 约束、session 清理、目录扫描、资料路径边界、OCR 命令白名单、去重、任务入队/批量消费、Worker 自动处理/重试、模型连通性、模型参与 RAG 回答、Embedding 向量检索、Qdrant 适配、批量 Embedding/Qdrant upsert、Qdrant 补偿同步、OCR 适配
deploy：平台和 Agent 的 Docker Compose 示例，含 PostgreSQL、Redis、Qdrant 占位
scripts：本地启动、FastAPI 并行入口启动、环境检查、OpenAPI 导出、脱敏诊断包导出、平台不可见报告导出、部署配置安全校验、交付物泄漏扫描、交付包边界校验、可复现交付包导出、交付归档自校验、交付包 SHA-256 完整性校验、交付验收证据报告、M2 快速验证、MVP 交付验证脚本
```

M20 已完成能力：

| 能力 | 状态 |
|---|---|
| Agent 本地登录和 Bearer token | 完成 |
| 管理员密码 PBKDF2 hash | 完成 |
| 过期 session 清理 | 完成 |
| Agent 状态接口 | 完成 |
| 文件上传安全校验 | 完成 |
| 目录权限检查 | 完成 |
| 任务列表、详情、失败重试 | 完成 |
| RAG `case_id` 隔离 | 完成 |
| 来源引用结构 | 完成 |
| 问答历史查询 | 完成 |
| 模型配置和 API Key 遮罩 | 完成 |
| API Key v1 本地加密封装 | 完成 |
| 旧 base64 凭证兼容读取 | 完成 |
| 模型 URL 本地/内网地址约束 | 完成 |
| Qdrant URL 本地/内网地址约束 | 完成 |
| 资料目录允许根限制 | 完成 |
| 系统/敏感路径拒绝 | 完成 |
| OCR 命令白名单 | 完成 |
| 生产 env.agent.example | 完成 |
| 验证脚本覆盖 Worker 脚本、前端检查和前端构建 | 完成 |
| 平台白名单复用 | 完成 |
| Agent 健康上报白名单映射 | 完成 |
| 禁止字段注入测试 | 完成 |
| 目录新增不隐式创建路径 | 完成 |
| 目录扫描入库 | 完成 |
| 上传文件自动入队 | 完成 |
| 内容 SHA-256 去重 | 完成 |
| 任务重试入口 | 完成 |
| 待处理任务批量消费入口 | 完成 |
| Worker 单轮处理入口 | 完成 |
| 常驻 Worker 启动脚本 | 完成 |
| Worker 自动重试失败任务 | 完成 |
| Worker 可触发 Qdrant 补偿同步 | 完成 |
| OpenAI-compatible 模型连通性探测 | 完成 |
| OpenAI-compatible Chat 参与 RAG 回答 | 完成 |
| OpenAI-compatible Embedding 生成 | 完成 |
| 单文件批量 Embedding 请求 | 完成 |
| SQLite 本地向量存储 | 完成 |
| Qdrant 可选适配层 | 完成 |
| Qdrant collection 自动创建 | 完成 |
| Qdrant points upsert | 完成 |
| Qdrant points 批量 upsert | 完成 |
| 本地向量补偿同步到 Qdrant | 完成 |
| Qdrant 同步后更新 vector refs | 完成 |
| 可选本地 OCR 命令适配 | 完成 |
| OCR 未配置占位回退 | 完成 |
| OCR 失败本地错误标记 | 完成 |
| Qdrant search 优先、SQLite/关键词回退 | 完成 |
| 向量相似检索优先、关键词回退 | 完成 |
| 模型失败时回退来源摘要回答 | 完成 |
| RAG 模型调用密钥不出响应 | 完成 |
| FastAPI 并行入口 | 完成 |
| FastAPI 复用现有 Store 业务能力 | 完成 |
| FastAPI 暴露登录、状态、任务、案件、文件、模型、RAG 主 API | 完成 |
| FastAPI 专用启动脚本 | 完成 |
| Agent Compose 并行 FastAPI 服务 | 完成 |
| Agent API Dockerfile 构建期安装依赖 | 完成 |
| FastAPI uvicorn 真实启动 smoke test | 完成 |
| server.py 导入不再立即创建 SQLite Store | 完成 |
| FastAPI adapter 领域 routers 拆分 | 完成 |
| Agent API OpenAPI 导出脚本 | 完成 |
| Agent API 契约文档 | 完成 |
| 脱敏诊断包预览和确认导出 | 完成 |
| 平台不可见验收报告导出 | 完成 |
| `AGENT_RUNTIME=stdlib|fastapi` 统一启动入口 | 完成 |
| 统一 MVP 交付验证脚本 | 完成 |
| React Agent 控制台 M3/M4 操作入口 | 完成 |
| React Agent 控制台 M5 操作入口 | 完成 |
| pytest 测试 | Python 3.11 FastAPI 环境 69 个通过；默认 Python 3.13 环境 64 个通过、5 个 FastAPI runtime/contract 用例跳过 |
| 前端 TypeScript 检查 | 通过 |
| 前端生产构建 | 通过 |

M21 已完成能力：

| 能力 | 状态 |
|---|---|
| `env.agent.example` 明文弱密钥校验 | 完成 |
| `env.platform.example` 明文弱密钥校验 | 完成 |
| Agent/Platform Compose 明文弱密钥校验 | 完成 |
| 关键安全变量缺失校验 | 完成 |
| Agent 本地/内网 URL 边界校验 | 完成 |
| Platform Compose 数据面服务禁入校验 | 完成 |
| MVP 交付验证接入部署配置校验 | 完成 |
| 交付文档和部署材料敏感内容扫描 | 完成 |
| 交付包清单和运行时产物排除校验 | 完成 |
| 基于清单的交付包 tar.gz 导出 | 完成 |
| 交付归档 manifest 一致性和排除规则自校验 | 完成 |
| 交付归档 SHA-256 sidecar 生成和强制校验 | 完成 |
| 交付验收证据报告 JSON 导出 | 完成 |

M22 已完成能力：

| 能力 | 状态 |
|---|---|
| 案件列表按当前用户成员关系过滤 | 完成 |
| 案件详情非成员访问拒绝 | 完成 |
| 文件列表、任务列表、聊天列表按案件成员关系过滤 | 完成 |
| RAG 检索和问答非成员访问拒绝 | 完成 |
| 聊天消息读取按会话所属案件校验 | 完成 |
| 证据列表和证据创建按案件成员关系校验 | 完成 |
| stdlib 和 FastAPI 两套 Agent API 入口权限语义对齐 | 完成 |
| 未授权、授权、撤销授权回归测试 | 完成 |
| pytest 测试 | Python 3.11 FastAPI 环境 134 个通过 |

M23 已完成能力：

| 能力 | 状态 |
|---|---|
| 案件列表页显示当前可访问案件和失去权限提示 | 完成 |
| 案件问答页显示未选择案件、可访问案件和撤权拒答提示 | 完成 |
| Agent Console 前端 TypeScript 检查 | 完成 |
| Agent Console 前端生产构建 | 完成 |
| UI smoke 输出标记稳定化 | 完成 |

M24 已完成能力：

| 能力 | 状态 |
|---|---|
| App 级可访问案件集合状态同步 | 完成 |
| 创建案件、授权、撤销后页面自动失效/刷新 | 完成 |
| 案件列表页与案件权限页联动刷新 | 完成 |
| 前端浏览器 smoke / UI smoke 串行通过 | 完成 |

M25 已完成能力：

| 能力 | 状态 |
|---|---|
| 任务页按当前案件筛选处理任务 | 完成 |
| 任务页展示任务所属案件标题 | 完成 |
| 普通成员隐藏运行队列和 Worker 运维按钮 | 完成 |
| Agent 管理员保留运行待处理和 Worker 单轮入口 | 完成 |
| Agent Console 前端 TypeScript 检查和生产构建 | 完成 |

MVP 简化边界：

```text
OCR：已支持可选本地命令适配；未配置时保留占位提示
向量库：已支持可选 Qdrant HTTP 适配；未配置或失败时回退 SQLite 本地向量和关键词检索
LLM：已支持 OpenAI-compatible Chat 参与 RAG 回答，Embedding 参与检索；模型不可用时回退来源摘要/关键词检索
数据库连接器：MVP+ 后续实现
```

M20 已知限制：

| 限制 | 后续处理 |
|---|---|
| 默认运行脚本仍指向 stdlib HTTP | FastAPI 并行入口已完成，后续灰度切换默认入口 |
| 当前数据库仍是 SQLite | 后续接入 PostgreSQL migration |
| 已支持常驻 Worker 原型，但仍是 SQLite 轮询模式 | 后续接入 Redis/RQ worker |
| Qdrant 当前使用 HTTP 适配层，尚未引入官方 SDK | 后续可替换为 SDK 或独立向量服务模块 |
| OCR 当前是命令适配层，未绑定具体引擎 | 后续按交付环境接入 PaddleOCR/Tesseract |
| Embedding 与 Qdrant upsert 已按单文件批量执行，且支持补偿同步 | 后续优化为常驻 worker 自动重试与分批进度游标 |
| API Key 加密为 stdlib 本地封装 | 后续可接入系统 Keychain/KMS |
| FastAPI adapter routers 拆分 | M15 已完成；M16-M18 已补齐接口契约、诊断包和交付验证入口 |

阶段会议决议执行状态：M15-M20 已完成。FastAPI adapter 已从单文件路由拆分为领域 routers，仍复用现有 Store 业务能力，未改变 URL、认证、响应 envelope、异常映射和业务语义；Agent API 契约、OpenAPI 导出、脱敏诊断包、平台不可见验收报告、Agent 运行入口灰度切换和统一交付验证入口已补齐。

---

## 4.2 本地运行

检查环境：

```bash
bash scripts/check-env.sh
```

启动平台控制平面：

```bash
bash scripts/run-platform.sh
```

启动 Agent 数据平面 stdlib 原型：

```bash
bash scripts/run-agent.sh
```

通过统一入口灰度启动 Agent FastAPI：

```bash
AGENT_RUNTIME=fastapi AGENT_PYTHON=.venv-agent-api/bin/python bash scripts/run-agent.sh
```

启动 Agent 数据平面 FastAPI 并行入口：

```bash
AGENT_PYTHON=.venv-agent-api/bin/python bash scripts/run-agent-fastapi.sh
```

启动 Agent Worker：

```bash
bash scripts/run-agent-worker.sh
```

默认地址：

```text
platform-api: http://127.0.0.1:8100
agent-api stdlib: http://127.0.0.1:8200
agent-api FastAPI: http://127.0.0.1:8201
```

运行测试：

```bash
.venv-agent-api/bin/python -m pytest
```

M2 快速验证：

```bash
bash scripts/verify-m2.sh
```

该脚本会执行环境检查、全量 unittest、脚本语法检查、Platform Compose config 校验和 Agent Compose config 校验。

MVP 交付验证：

```bash
bash scripts/verify-mvp.sh
```

该脚本会执行环境检查、pytest 回归、Agent OpenAPI 导出、诊断包脱敏预览、平台不可见验收报告导出、脚本语法检查、部署配置安全校验、交付物泄漏扫描、交付包边界校验、交付包导出 smoke test、交付归档自校验、交付包 SHA-256 完整性校验、交付验收证据报告导出，并在 Docker 可用时校验 Platform/Agent Compose 配置。

部署配置安全校验：

```bash
python3 scripts/validate-deploy-config.py --mode example
python3 scripts/validate-deploy-config.py --mode production --agent-env path/to/agent.env --platform-env path/to/platform.env
```

该脚本会检查 `env.agent.example`、`env.platform.example`、Agent Compose 和 Platform Compose 是否存在明文弱密钥、关键安全变量缺失、Agent 外部公网端点，以及 Platform Compose 混入数据面服务导致的平台不可见边界破坏。

交付物泄漏扫描：

```bash
python3 scripts/scan-delivery-artifacts.py
```

该脚本默认扫描 README、`deploy/`、`docs/` 和模块说明文档，拒绝高置信 API Key、私钥、数据库明文口令、个人本机路径、真实/仿真案情样例进入交付材料。

交付包边界校验：

```bash
python3 scripts/check-delivery-package.py
python3 scripts/check-delivery-package.py --output /tmp/delivery-manifest.json
```

该脚本按交付 allowlist 生成候选文件清单，并强制排除 `.venv-agent-api`、`node_modules`、`services/*/data/`、`diagnostics/`、`__pycache__`、SQLite 数据库、私有 env、日志和构建产物，避免本地运行时内容被打进交付包。

导出交付包：

```bash
python3 scripts/export-delivery-package.py --output /tmp/harness-engineering-delivery.tar.gz
```

导出脚本复用交付包边界清单，只归档允许文件，并在归档内写入 `DELIVERY-MANIFEST.json` 记录 included/excluded 规则和文件清单，同时生成同名 `.sha256` sidecar。输出路径默认要求在工程根目录之外，避免归档文件被误纳入后续交付。

校验交付归档：

```bash
python3 scripts/verify-delivery-package.py --archive /tmp/harness-engineering-delivery.tar.gz --require-checksum --extract-smoke
```

校验脚本检查归档必须包含且只包含一个 `DELIVERY-MANIFEST.json`，manifest 文件清单必须与归档实际文件一致，并拒绝绝对路径、路径穿越、运行时数据库、私有 env、缓存、依赖目录和构建产物混入最终包。开启 `--require-checksum` 时，校验脚本还会读取同名 `.sha256` 文件并校验归档 SHA-256 摘要。开启 `--extract-smoke` 时，校验脚本会安全解包到临时目录，确认 README、部署 Compose、交付脚本等基础入口文件存在，并使用解包目录内的 `scripts/verify-delivery-package.py` 对原始归档执行一次非递归复验命令 smoke test。

导出交付验收证据报告：

```bash
python3 scripts/export-delivery-acceptance-report.py --archive /tmp/harness-engineering-delivery.tar.gz --output /tmp/delivery-acceptance-report.json
```

验收证据报告为 metadata-only JSON，汇总部署配置校验、交付物泄漏扫描、交付包边界、归档自校验、SHA-256 校验、安全解包 smoke test、Docker/Compose 环境指纹、Platform/Agent Compose config 校验、manifest 计数，以及 V5 P0 知识治理、AI 风控、质量反馈、历史引用、平台不可见专项检查和交付红线证据摘要，不导出归档文件内容、测试输出、数据库值或业务数据。

校验交付验收证据报告：

```bash
python3 scripts/verify-delivery-acceptance-report.py --report /tmp/delivery-acceptance-report.json
```

报告校验脚本会验证 schema、必需检查项、`--require-checksum`/`--extract-smoke` 证据、环境指纹、archive/checksum 元数据、V5 P0 必需证据项和 redaction 标志，防止验收报告格式漂移或漏项。

一键导出完整交付 bundle：

```bash
python3 scripts/export-delivery-bundle.py --output-dir /tmp/harness-engineering-delivery-bundle
```

bundle 导出脚本会一次性生成并校验交付归档、`.sha256`、交付验收证据报告和 `delivery-bundle-manifest.json`。bundle manifest 会记录验收报告 schema、通过状态、metadata-only 标志和 V5 P0 证据项名称摘要。输出目录默认必须在工程根目录之外，避免交付产物被误纳入后续包。

校验完整交付 bundle：

```bash
python3 scripts/verify-delivery-bundle.py --manifest /tmp/harness-engineering-delivery-bundle/delivery-bundle-manifest.json
```

bundle 校验脚本会验证 bundle manifest、归档、checksum、验收报告、V5 P0 证据摘要和步骤状态彼此一致，确保交付目录可独立复验。

解包后复验交付 bundle：

```bash
python3 scripts/smoke-delivery-bundle-extract.py --bundle-dir /tmp/harness-engineering-delivery-bundle
```

该 smoke 会把交付归档解到临时目录，并在解包后的工程目录中运行交付包边界检查、交付物泄漏扫描和验收报告校验，证明客户拿到包后可在解包目录内复验。

扫描验收报告红线字段：

```bash
python3 scripts/scan-delivery-acceptance-report.py --report /tmp/delivery-acceptance-report.json
```

该扫描拒绝 `file_name`、`file_path`、`chunk_text`、`question`、`answer`、`api_key`、`prompt` 等业务字段进入 metadata-only 验收报告。

导出 Agent OpenAPI：

```bash
.venv-agent-api/bin/python scripts/export-agent-openapi.py --output docs/agent-api-openapi.json
```

预览或导出脱敏诊断包：

```bash
bash scripts/export-diagnostics.sh
bash scripts/export-diagnostics.sh --confirm
```

导出平台不可见验收报告：

```bash
.venv-agent-api/bin/python scripts/export-platform-invisibility-report.py --output docs/platform-invisibility-report.json
```

---

## 4.3 API 快速验证

创建组织：

```bash
curl -X POST http://127.0.0.1:8100/api/platform/organizations \
  -H 'Content-Type: application/json' \
  -d '{"name":"测试律所"}'
```

创建授权：

```bash
curl -X POST http://127.0.0.1:8100/api/platform/licenses \
  -H 'Content-Type: application/json' \
  -d '{"organization_id":"替换为组织ID"}'
```

Agent 登录：

```bash
curl -X POST http://127.0.0.1:8200/api/agent/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"account":"admin","password":"admin"}'
```

Agent 激活：

```bash
curl -X POST http://127.0.0.1:8200/api/agent/activate \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer 替换为登录token' \
  -d '{"tenant_id":"替换为组织ID","license_key_hash":"替换为授权hash","agent_id":"ag_local_001"}'
```

创建案件：

```bash
curl -X POST http://127.0.0.1:8200/api/agent/cases \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer 替换为登录token' \
  -d '{"title":"示例案件","cause_of_action":"示例案由"}'
```

上传文件时 `content_base64` 传入 base64 文件内容，然后调用 `/api/agent/files/parse` 解析，再调用 `/api/agent/rag/query` 问答。Agent 管理类接口需要 `Authorization: Bearer <token>`。

M2 验收清单：

```text
docs/m2-acceptance-checklist.md
```

---

## 5. 模块说明

### 5.1 `apps/platform-console/`

平台控制台前端。

只允许展示：

```text
组织
授权
Agent ID
Agent 版本
Agent 在线状态
脱敏任务计数
标准错误码
资源状态
```

禁止展示：

```text
案件
文件名
文件正文
数据库字段值
问答
文书
向量
律师笔记
```

### 5.2 `apps/agent-console/`

Agent 本地管理台、律所管理后台、案件工作台前端。

负责：

```text
Agent 激活
本地目录配置
数据库连接器
任务状态
模型配置
案件工作台
本地问答
证据目录
本地审计日志
```

### 5.3 `services/platform-api/`

平台控制平面后端。

只负责：

```text
账号
组织
授权
Agent 注册
Agent 心跳
脱敏健康状态
平台操作日志
```

不得接收和保存任何业务数据。

### 5.4 `services/agent-api/`

律师侧 Agent 本地 API。

负责：

```text
本地文件管理
本地数据库连接
文档解析
OCR
向量化
RAG 问答
案件权限
审计日志
诊断包导出
```

### 5.5 `agent-modules/db-connector/`

数据库连接器模块。

MVP+ 范围：

```text
MySQL 只读连接
PostgreSQL 只读连接
表/视图选择
字段映射
文件路径关联
手动同步
SQL 白名单
```

### 5.6 `agent-modules/rag-engine/`

本地 RAG 模块。

负责：

```text
文档切片
Embedding
本地向量检索
关键词检索
引用来源
Prompt 组装
模型调用
无依据提示
```

### 5.7 `agent-modules/health-reporter/`

脱敏健康上报模块。

只允许上报白名单字段：

```text
tenant_id
agent_id
agent_version
status
last_heartbeat
task_pending_count
task_running_count
task_failed_count
error_code
cpu_usage
memory_usage
disk_usage
```

禁止上报：

```text
案件名
文件名
文件路径
数据库表内容
字段值
问题文本
答案文本
文书内容
原文片段
```

---

## 6. 开发红线

以下情况不得合并、不得上线：

| 红线 | 说明 |
|---|---|
| 平台 API 接收业务数据 | 违反平台不可见原则 |
| 平台数据库出现案件或文件字段 | 违反平台不可见原则 |
| Agent 心跳包含业务字段 | 违反健康上报白名单 |
| 平台日志出现文件名/案件名 | 说明日志脱敏失败 |
| 数据库连接器可写入业务库 | 违反只读原则 |
| 模型 API Key 上传平台 | 违反凭证本地原则 |
| 平台可查看问答正文 | 违反产品定位 |
| 平台可预览文件 | 违反产品定位 |

---

## 7. 分期开发建议

### 7.1 第一期：Agent 本地知识库闭环

```text
Agent 部署
Agent 激活
本地目录接入
案件空间
PDF/Word 解析
向量化
本地问答
引用来源
```

### 7.2 第二期：平台控制台和安全闭环

```text
平台组织授权
Agent 注册和心跳
脱敏健康上报
本地审计日志
权限系统
错误码规范
诊断包导出
```

### 7.3 第三期：数据库连接器 MVP+

```text
MySQL/PostgreSQL 只读连接
表/视图选择
字段映射
文件路径关联
手动同步
SQL 白名单
```

### 7.4 第四期：案件分析增强

```text
案件摘要
争议焦点
证据目录
证据目录导出
案件笔记
问答历史管理
```

---

## 8. 与需求文档的关系

当前工程目录对应的需求基线为：

```text
需求文档/V4.1-PRD-MVP压缩版-律师本地数据主权型AI案件知识库工作台.md
```

V4 完整版作为愿景和后续路线参考：

```text
需求文档/V4-PRD-律师本地数据主权型AI案件知识库工作台.md
```

开发优先以 V4.1 MVP 压缩版为准。

---

## 9. 最终约定

从现在开始：

```text
所有程序只进入 harness-engineering/
```

根目录不再新增其他程序工程目录。

一句话原则：

```text
需求在需求文档，角色在角色库，成本在成本估算，程序在 harness-engineering。
```

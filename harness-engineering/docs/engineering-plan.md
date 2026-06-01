# Harness Engineering 工程初始化方案

> 项目：律师本地数据主权型 AI 案件知识库工作台  
> 版本：V4.1 MVP  
> 工程目录：`harness-engineering/`  
> 日期：2026-05-22

---

## 1. 工程目标

`harness-engineering/` 是本项目唯一程序工程目录。

V4.1 MVP 工程目标：

```text
搭建平台控制平面
+ 搭建律师侧 Agent 数据平面
+ 跑通本地文件入库
+ 跑通本地 RAG 问答
+ 保证平台不可见律师业务数据
```

---

## 2. 工程边界

### 2.1 平台工程边界

平台工程只处理：

```text
组织
授权
Agent 注册
Agent 心跳
脱敏健康状态
平台操作日志
```

平台工程禁止处理：

```text
案件
文件名
文件正文
数据库字段值
文档切片
向量
问答
文书
笔记
模型 API Key
数据库密码
```

### 2.2 Agent 工程边界

Agent 工程处理：

```text
本地目录
本地文件
本地数据库连接器
文档解析
OCR
切片
向量化
本地问答
引用来源
案件权限
本地审计日志
模型配置
```

---

## 3. 推荐技术栈

### 3.1 MVP 推荐组合

| 层级 | 推荐方案 | 说明 |
|---|---|---|
| 平台控制台前端 | React/Next.js + TypeScript | 只显示控制平面数据 |
| Agent 前端 | React/Next.js + TypeScript | Agent 管理台、律所后台、案件工作台 |
| 平台 API | Python FastAPI 或 Node NestJS | 授权、Agent 注册、心跳 |
| Agent API | Python FastAPI | 文件、解析、RAG、任务队列 |
| Agent 本地数据库 | SQLite 起步，PostgreSQL 可选 | MVP 可用 SQLite 简化部署 |
| 平台数据库 | PostgreSQL | 授权、组织、Agent 状态 |
| 向量数据库 | Qdrant | Agent 本地部署 |
| 任务队列 | Redis + RQ/Celery，或轻量本地队列 | MVP 可先轻量化 |
| 文档解析 | Unstructured / python-docx / PyMuPDF | PDF/Word 解析 |
| OCR | PaddleOCR 或可配置 OCR 服务 | MVP 简化 |
| LLM | 律师自有 DeepSeek/通义 API Key | 不经平台代理 |
| 部署 | Docker Compose | MVP 只支持 Linux + Docker Compose |

---

## 4. 建议目录结构

```text
harness-engineering/
├── README.md
├── docs/
│   ├── engineering-plan.md
│   ├── architecture.md
│   ├── api-boundary.md
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

---

## 5. 应用拆分

### 5.1 platform-console

平台控制台前端。

页面范围：

```text
登录页
组织管理页
授权管理页
Agent 列表页
Agent 脱敏健康详情页
平台操作日志页
```

API 只能调用：

```text
platform-api
```

禁止调用：

```text
agent-api 的业务接口
```

### 5.2 agent-console

Agent 本地前端。

页面范围：

```text
Agent 激活页
Agent 状态页
本地目录配置页
文件处理任务页
模型配置页
本地审计日志页
成员管理页
案件权限页
案件列表页
案件工作台
案件问答页
证据目录页
```

API 调用：

```text
agent-api
```

只有激活、心跳等控制类动作可间接触发平台通信。

---

## 6. 服务拆分

### 6.1 platform-api

职责：

```text
组织管理
授权管理
Agent 注册
Agent 心跳
脱敏健康状态
平台操作日志
```

禁止：

```text
案件 API
文件 API
问答 API
文书 API
数据库查询代理
模型代理
```

### 6.2 agent-api

职责：

```text
本地登录
本地目录配置
文件扫描和上传
案件空间
成员和权限
文档解析
OCR
切片和向量化
RAG 问答
引用来源
证据目录
本地审计日志
模型配置
脱敏健康上报
```

---

## 7. Agent 模块拆分

### 7.1 file-ingestion

负责：

```text
本地目录配置
文件扫描
文件上传
文件哈希
文件状态
```

### 7.2 document-parser

负责：

```text
PDF 解析
Word 解析
图片 OCR
文本清洗
文档切片
```

### 7.3 rag-engine

负责：

```text
Embedding
本地向量入库
关键词检索
语义检索
混合检索
Prompt 组装
模型调用
引用来源
无依据提示
```

### 7.4 audit-log

负责：

```text
本地业务操作日志
权限变更日志
问答日志
导出日志
删除日志
```

### 7.5 health-reporter

负责：

```text
Agent 心跳
脱敏健康上报
白名单字段校验
标准错误码上报
```

### 7.6 db-connector

MVP+ 模块。

负责：

```text
MySQL 只读连接
PostgreSQL 只读连接
表/视图选择
字段映射
文件路径关联
手动同步
SQL 白名单
```

---

## 8. API Client 约束

前端必须拆分 API Client：

```text
platformApiClient
agentApiClient
```

规则：

| Client | 允许调用 | 禁止调用 |
|---|---|---|
| platformApiClient | platform-api | agent-api 业务接口 |
| agentApiClient | agent-api | 上传业务数据到 platform-api |

平台前端不得引用业务数据类型：

```text
Case
File
ChatMessage
DocumentChunk
Evidence
DocumentDraft
```

---

## 9. 环境变量规划

### 9.1 platform-api 环境变量

```text
PLATFORM_DATABASE_URL=
PLATFORM_JWT_SECRET=
PLATFORM_LICENSE_SECRET=
PLATFORM_ALLOWED_HEALTH_FIELDS=
PLATFORM_LOG_LEVEL=
```

不得出现：

```text
MODEL_API_KEY
DB_CONNECTOR_PASSWORD
LAWYER_FILE_PATH
```

### 9.2 agent-api 环境变量

```text
AGENT_ID=
AGENT_LOCAL_DATABASE_URL=
AGENT_VECTOR_DATABASE_URL=
AGENT_REDIS_URL=
AGENT_MASTER_KEY=
AGENT_PLATFORM_BASE_URL=
AGENT_LOCAL_STORAGE_ROOT=
```

模型 API Key 建议存入 Agent 本地加密配置，不建议直接放入平台。

---

## 10. Docker Compose 规划

### 10.1 Agent Compose 服务

```text
agent-api
agent-console
qdrant
redis
postgres 或 sqlite volume
```

### 10.2 Platform Compose 服务

```text
platform-api
platform-console
postgres
```

MVP 可先本地开发，不必完整生产化部署。

---

## 11. 工程红线

以下情况不得提交或合并：

| 红线 | 说明 |
|---|---|
| platform-api 出现 case/file/chat/draft 业务接口 | 违反平台不可见 |
| platform-console 展示业务菜单 | 违反平台不可见 |
| Agent 心跳 payload 含业务字段 | 违反白名单 |
| 平台日志打印业务内容 | 违反平台不可见 |
| 模型 API Key 写入平台配置 | 违反凭证本地原则 |
| db-connector 支持写入 SQL | 违反数据库只读原则 |
| Prompt 经过 platform-api | 违反模型调用边界 |

---

## 12. 测试工程规划

### 12.1 tests/api

测试：

```text
platform-api 白名单
agent-api 权限
Agent 心跳字段
错误码
```

### 12.2 tests/security

测试：

```text
平台不可见
平台日志敏感字段
数据库只读
凭证不上传平台
Prompt 不经过平台
```

### 12.3 tests/e2e

测试：

```text
Agent 激活
本地目录接入
案件创建
文件解析
案件问答
来源引用
```

### 12.4 tests/fixtures

测试样例：

```text
PDF 样例
Word 样例
图片 OCR 样例
错误文件样例
```

注意：fixtures 不得使用真实律师案件材料。

---

## 13. 初始开发顺序

建议按以下顺序初始化工程：

```text
1. 创建 monorepo 基础结构
2. 创建 platform-api 空服务
3. 创建 agent-api 空服务
4. 创建 platform-console 空应用
5. 创建 agent-console 空应用
6. 创建共享类型包 shared-types
7. 定义平台健康上报 schema
8. 定义 Agent 本地核心数据模型
9. 实现 Agent 本地目录配置
10. 实现文件扫描和任务队列
11. 实现 PDF/Word 解析
12. 实现本地向量入库
13. 实现本地 RAG 问答
14. 实现来源引用
15. 实现平台授权和心跳
```

---

## 14. 与需求文档对应关系

| 工程内容 | 对应需求文档 |
|---|---|
| MVP 范围 | `需求文档/V4.1-PRD-MVP压缩版-律师本地数据主权型AI案件知识库工作台.md` |
| 任务拆解 | `需求文档/V4.1-MVP功能拆解与任务清单.md` |
| API 边界 | `需求文档/V4.1-平台不可见数据边界与API白名单.md` |
| 页面范围 | `需求文档/V4.1-页面清单与原型说明.md` |
| 数据模型 | `需求文档/V4.1-数据模型草案.md` |
| 测试验收 | `需求文档/V4.1-验收测试清单.md` |

---

## 15. 最终结论

工程初始化必须服务于 V4.1 的核心目标：

```text
先让 Agent 跑起来，
让本地文件问起来，
让回答来源亮出来，
让平台完全看不到。
```

工程一句话原则：

```text
platform 管授权，agent 管业务；平台只收白名单，业务永不进平台。
```

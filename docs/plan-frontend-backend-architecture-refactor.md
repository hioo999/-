# 前后端架构重构五阶段执行计划

## 1. 计划背景

当前系统已经具备 IP 内容生产、提词器、公众号排版、多平台内容、模型中转、视频任务等能力，但代码组织仍处于快速堆叠期。

本计划用于后续重构执行，目标不是推倒重写，而是在保持现有功能可用的前提下，逐步把系统从“单体工作台 + 大路由 + 大 API 文件”收敛为清晰的 SaaS 产品架构。

相关上下文：

1. `docs/meeting-ip-system-restructure-next-steps.md` 记录了平台化重构和公众号闭环的阶段会议结论。
2. `docs/status-ip-system-restructure-phase1.md` 记录了第一阶段平台化底座已有进展。
3. 本文档作为后续前后端架构重构的执行基准。

## 2. 总体目标

重构后的系统应形成清晰边界：

```text
前端：
Vue Router 定页面边界
Pinia 管跨页面状态
features 管业务模块
api/*.api.ts 管接口协议
components/ui 管基础组件
layouts 管 SaaS 壳层

后端：
api/v1 管 HTTP
schemas 管输入输出
services 管业务用例
repositories 管数据访问
models 管 ORM
integrations 管 AI / 微信 / 视频引擎
tasks 管统一任务状态
```

业务主线长期收敛为：

```text
IpProject
  -> ContentTopic
    -> SourceMaterial
      -> PlatformContent
        -> GenerationTask
          -> UnifiedAsset
            -> PublishRecord / WechatDraftRecord
```

## 3. 执行原则

1. 不一次性推倒重写，按阶段迁移。
2. 每个阶段必须有可验证交付物。
3. 每次迁移优先保证现有核心链路可用。
4. 新架构先兼容旧接口，再逐步迁移调用方。
5. 后续新增功能优先落在新目录、新路由、新 service 中。
6. 旧大文件只做必要修补，不继续扩大职责。
7. 每个阶段完成后更新本文档状态或新增阶段状态记录。

## 4. 当前主要问题

| 问题 | 当前表现 | 重构方向 |
|---|---|---|
| 首页和工作台耦合 | 打开首页即加载提示词、模型、反转剧、提词器等无关接口 | 首页独立为轻量 Dashboard |
| 前端无真正路由 | `CopilotWorkspace.vue` 内手写 hash 切换 | 引入 Vue Router |
| 前端 API 巨石 | `frontend/src/api/index.ts` 聚合大量业务域 | 按业务域拆 `*.api.ts` |
| 前端状态分散 | 登录、工作区、模型、模板、任务散落组件内 | 引入 Pinia store |
| 后端大路由过重 | `copilot_routes.py`、`platform_routes.py` 承担过多业务 | 按领域拆路由 |
| 后端服务层不足 | endpoint 内直接查 DB、拼 prompt、调 AI、写任务 | 抽应用 service |
| ORM 模型混放 | `models/persona.py` 承载大量领域模型 | 按领域拆 model |
| 任务体系不统一 | 视频任务、生成任务、Video AIP 步骤任务并存 | 统一 `GenerationTask` 语义 |

## 5. 五阶段路线图

### 阶段 1：拆首页和路由边界

目标：让首页从全功能工作台中独立出来，打开 `/` 时只加载 Dashboard 必要数据。

| 编号 | 工作项 | 负责人 | 优先级 | 交付物 |
|---|---|---|---|---|
| FE-1.1 | 接入 Vue Router | 前端 | P0 | `frontend/src/router/index.ts`、`App.vue` 使用 `<router-view />` |
| FE-1.2 | 新建全局布局 | 前端/UI | P0 | `frontend/src/layouts/AppLayout.vue` |
| FE-1.3 | 首页独立页面 | 前端 | P0 | `frontend/src/views/HomeView.vue` |
| FE-1.4 | 关键页面路由化 | 前端 | P0 | 内容工作台、提词器、公众号、模型设置、提示词管理具备独立路由 |
| FE-1.5 | 接入 Pinia 基础能力 | 前端 | P0 | `auth.store.ts`、`workspace.store.ts` 最小实现 |
| BE-1.1 | 新增 Dashboard API | 后端 | P0 | `GET /api/dashboard/overview` 或 `/api/v1/dashboard/overview` |
| BE-1.2 | 新增 Dashboard service | 后端 | P0 | `dashboard_service.py` 聚合首页数据 |
| QA-1.1 | 首页首屏冒烟测试 | 测试 | P0 | 首页不加载无关 API，后端失败可局部降级 |

验收标准：

1. 打开 `/` 不触发提示词、模型、反转剧、提词器草稿等无关接口。
2. 首页只请求 Dashboard、认证状态等必要接口。
3. `/tools/teleprompter`、`/tools/wechat`、`/settings/models` 等页面可独立打开。
4. 后端 Dashboard 失败时，首页显示局部错误和重试，不影响导航。
5. `npm run build` 通过。

完成标志：

```text
首页从 CopilotWorkspace 解耦，应用具备真实页面路由边界。
```

### 阶段 2：拆前端 API 巨石

目标：把 `frontend/src/api/index.ts` 按业务域拆分，形成稳定的前后端协议边界。

| 编号 | 工作项 | 负责人 | 优先级 | 交付物 |
|---|---|---|---|---|
| FE-2.1 | 拆 Dashboard API | 前端 | P0 | `dashboard.api.ts` |
| FE-2.2 | 拆提词器 API | 前端 | P0 | `teleprompter.api.ts` |
| FE-2.3 | 拆公众号 API | 前端 | P0 | `wechat.api.ts` |
| FE-2.4 | 拆模型配置 API | 前端 | P0 | `modelConfig.api.ts` |
| FE-2.5 | 拆提示词模板 API | 前端 | P0 | `promptTemplates.api.ts` |
| FE-2.6 | 拆平台内容 API | 前端 | P0 | `platformContent.api.ts` |
| FE-2.7 | 拆 Video AIP API | 前端 | P1 | `videoAip.api.ts` |
| FE-2.8 | 增加统一错误适配 | 前端 | P1 | `api/errors.ts` |

验收标准：

1. 新页面不再从 `api/index.ts` 直接导入新增接口。
2. `api/index.ts` 暂时只作为兼容 re-export，不继续扩大。
3. 每个 API 文件只包含一个业务域的类型和请求函数。
4. 前端能把后端错误转成可展示文案。
5. `npm run build` 通过。

完成标志：

```text
前端接口调用按业务域维护，不再继续扩大 API 巨石。
```

### 阶段 3：拆后端大路由

目标：把 `copilot_routes.py`、`platform_routes.py` 中的混合能力拆到更清晰的领域路由中。

| 编号 | 工作项 | 负责人 | 优先级 | 交付物 |
|---|---|---|---|---|
| BE-3.1 | 新建路由聚合器 | 后端 | P0 | `backend/api/router.py` |
| BE-3.2 | 拆提示词路由 | 后端 | P0 | `api/prompts.py` 或 `api/v1/prompts.py` |
| BE-3.3 | 拆模型路由 | 后端 | P0 | `api/models.py` 或 `api/v1/models.py` |
| BE-3.4 | 拆资产路由 | 后端 | P0 | `api/assets.py` 或 `api/v1/assets.py` |
| BE-3.5 | 拆任务路由 | 后端 | P0 | `api/tasks.py` 或 `api/v1/tasks.py` |
| BE-3.6 | 拆公众号文章路由 | 后端 | P0 | 公众号生成、编辑、草稿、素材统一归口 |
| BE-3.7 | 拆 Video AIP 路由 | 后端 | P1 | `api/video_aip.py` |
| BE-3.8 | 保留旧路由兼容 | 后端 | P0 | 旧路径可继续使用或明确跳转 |

验收标准：

1. 旧接口行为不被破坏。
2. 新接口有清晰 prefix 和 tags。
3. `platform_routes.py` 不再继续承载新的跨领域能力。
4. `copilot_routes.py` 不再继续承载新的模型、提示词、视频任务能力。
5. 后端现有测试通过。

完成标志：

```text
HTTP 路由按领域拆分，大路由进入只减不增状态。
```

### 阶段 4：抽应用服务层

目标：把业务编排从 endpoint 中移出，让路由只负责 HTTP，service 负责用例。

| 编号 | 工作项 | 负责人 | 优先级 | 交付物 |
|---|---|---|---|---|
| BE-4.1 | 抽 DashboardService | 后端 | P0 | 首页聚合逻辑独立 |
| BE-4.2 | 抽 PromptTemplateService | 后端 | P0 | 模板 CRUD、版本、启停、默认模板 |
| BE-4.3 | 抽 ModelConfigService | 后端 | P0 | 模型网关、模型目录、默认模型解析 |
| BE-4.4 | 抽 ContentGenerationService | 后端 | P0 | 素材、模板、模型、AI 调用、结果解析统一编排 |
| BE-4.5 | 抽 PlatformContentService | 后端 | P0 | 平台内容创建、编辑、导出、删除 |
| BE-4.6 | 抽 AssetService | 后端 | P0 | 资产创建、复用、下载、软删除 |
| BE-4.7 | 抽 TaskService | 后端 | P0 | 任务创建、状态、失败、重试 |
| BE-4.8 | 抽 WechatPublishService | 后端 | P0 | preflight、图片上传、HTML 清洗、draft/add |
| BE-4.9 | 抽 VideoJobService | 后端 | P1 | video_engine 调用统一适配 |

验收标准：

1. 新路由中不直接拼复杂 prompt。
2. 新路由中不直接跨多个表写复杂业务流程。
3. AI、微信、视频引擎调用通过 service 或 integration 进入。
4. 关键 service 具备最小单元测试或接口回归测试。
5. 后端测试通过。

完成标志：

```text
业务用例进入 service 层，路由层回归 HTTP 边界。
```

### 阶段 5：统一任务和内容主线

目标：把旧 Copilot、平台内容、公众号、短视频、视频任务逐步统一到同一内容生产链路和任务状态模型。

| 编号 | 工作项 | 负责人 | 优先级 | 交付物 |
|---|---|---|---|---|
| BE-5.1 | 明确统一任务 schema | 后端/前端 | P0 | `task_id`、`status`、`progress`、`stage`、`error`、`result` 字段稳定 |
| BE-5.2 | 扩展任务重试类型 | 后端 | P0 | 生成、图片、草稿、视频任务重试统一 |
| BE-5.3 | 统一任务轮询接口 | 后端/前端 | P0 | `/api/tasks`、`/api/tasks/{id}`、`/api/tasks/{id}/retry` |
| BE-5.4 | 老 Copilot 生成写入新主线 | 后端 | P1 | 旧生成结果进入 `PlatformContent` / `GenerationRecord` |
| BE-5.5 | Video AIP 任务接入统一任务 | 后端 | P1 | Video AIP step 与 `GenerationTask` 建立稳定映射 |
| FE-5.1 | 统一任务中心 UI | 前端/UI | P0 | 首页、平台页、提词器、公众号共用任务状态组件 |
| FE-5.2 | 统一资产引用 UI | 前端/UI | P1 | 脚本、图片、发布包、视频文件统一资产卡片 |
| QA-5.1 | 端到端回归 | 测试 | P0 | 素材输入 -> 生成 -> 编辑 -> 提词/发布/出片 -> 任务/资产留痕 |

统一任务状态：

```text
pending -> running -> succeeded
pending -> running -> failed
pending -> cancelled
failed -> retrying -> running
```

验收标准：

1. 前端不同模块展示任务状态时使用同一套字段。
2. 后端不同长任务使用同一套状态语义。
3. 失败任务具备可解释错误和可控重试。
4. 生成结果、资产、任务、发布记录能沿同一主线追溯。
5. 核心 E2E 回归通过。

完成标志：

```text
系统从功能集合收敛为可追踪、可恢复、可复用的内容生产平台。
```

## 6. 阶段依赖关系

```text
阶段 1：拆首页和路由边界
  ↓
阶段 2：拆前端 API 巨石
  ↓
阶段 3：拆后端大路由
  ↓
阶段 4：抽应用服务层
  ↓
阶段 5：统一任务和内容主线
```

阶段 1 和阶段 2 可以部分并行，但必须先保证路由边界稳定。

阶段 3 和阶段 4 可以穿插推进，但每拆出一个新路由，就应同步抽对应 service，避免只是把大文件拆成多个小大文件。

阶段 5 必须建立在阶段 3、4 的边界基础上推进，否则会继续扩大耦合。

## 7. 后续执行纪律

后续每次执行重构任务时，按以下流程推进：

1. 先确认当前任务属于哪个阶段。
2. 只改当前阶段必要文件，避免跨阶段大范围改动。
3. 每次改动前先确认受影响页面、接口和测试。
4. 每次完成后记录：完成项、未完成项、验证命令、风险。
5. 如果发现计划不适用，先更新计划，再继续执行。
6. 已迁移到新架构的模块，不再回写旧大文件。
7. 新增能力优先进入新路由、新 API 文件、新 service、新 store。

## 8. 当前执行状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| 阶段 1：拆首页和路由边界 | 执行中 | 已接入 Vue Router、Pinia、首页独立路由、Dashboard API；待补更完整首页登录态数据验证和旧 hash 兼容回归 |
| 阶段 2：拆前端 API 巨石 | 执行中 | 已新增 `dashboard.api.ts`、`promptTemplates.api.ts`、`modelConfig.api.ts`、`teleprompter.api.ts`、`wechat.api.ts`、`platformContent.api.ts`、`tasks.api.ts`、`assets.api.ts`，并迁移首页、工作台、公众号、多平台、生产中心和提词器页面的相关调用；待继续拆 videoAip 等领域 API |
| 阶段 3：拆后端大路由 | 待执行 | 可先从 prompts/models/tasks/assets 拆起 |
| 阶段 4：抽应用服务层 | 待执行 | 与阶段 3 穿插，但必须有测试保护 |
| 阶段 5：统一任务和内容主线 | 待执行 | 作为长期收敛目标 |

## 9. 下一步执行项

下一次进入开发时，优先执行阶段 1：

1. 新建前端 `router/`。
2. 新建 `layouts/AppLayout.vue`。
3. 将首页抽成 `HomeView.vue`。
4. 新增 Dashboard API 和 service。
5. 让首页只请求 Dashboard 数据。
6. 保留旧 hash 入口的兼容跳转或临时映射。
7. 跑前端构建和首页冒烟验证。

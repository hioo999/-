# IP全案系统Sprint1后端接口开发清单

## 1. 文档目标

本文档用于指导后端完成Sprint 1全案底座接口开发。

Sprint 1后端目标：

```text
IP资产
内容策略
栏目矩阵
选题库
内容母稿
素材上传
生成任务状态
```

## 2. 数据模型优先级

必须先建：

- ip_assets
- content_strategies
- content_columns
- topics
- content_drafts
- materials
- generation_tasks

预留但Sprint 1可不完整实现：

- platform_contents
- publish_auths
- wechat_sync_records
- export_packages
- operation_logs

## 3. 接口清单

### BE-S1-01 创建IP资产

接口：`POST /api/ip-assets`

验收：

- 必填字段校验。
- 创建成功返回ipId。
- profileStatus正确计算。

### BE-S1-02 查询IP资产列表

接口：`GET /api/ip-assets`

验收：

- 支持分页。
- 支持按type筛选。
- 返回主平台和更新时间。

### BE-S1-03 查询IP资产详情

接口：`GET /api/ip-assets/:id`

验收：

- 返回完整IP字段。
- 不存在返回明确错误。

### BE-S1-04 更新IP资产

接口：`PUT /api/ip-assets/:id`

验收：

- 可更新目标用户、平台、风格、禁用表达。
- 更新后updatedAt变化。

### BE-S1-05 生成内容策略

接口：`POST /api/strategies/generate`

验收：

- 基于ipId生成策略。
- 返回定位、用户画像、痛点、平台分工、转化路径。
- 保存inputSnapshot。
- 创建generation_task记录。

### BE-S1-06 生成栏目矩阵

接口：`POST /api/columns/generate`

验收：

- 栏目不少于6个。
- 每个栏目包含名称、定位、平台、形式、频率、转化动作。
- 栏目保存到content_columns。

### BE-S1-07 批量生成选题

接口：`POST /api/topics/generate`

验收：

- 选题不少于20个。
- 每个选题有关联ipId和columnId。
- 默认状态为todo。

### BE-S1-08 查询选题列表

接口：`GET /api/topics`

验收：

- 支持按ipId筛选。
- 支持按platform筛选。
- 支持按status筛选。

### BE-S1-09 生成内容母稿

接口：`POST /api/content-drafts/generate`

验收：

- 基于ipId和topicId生成母稿。
- 返回痛点、观点、逻辑、案例、金句、转化动作。
- 母稿保存到content_drafts。

### BE-S1-10 更新内容母稿

接口：`PUT /api/content-drafts/:id`

验收：

- 可编辑保存母稿。
- version递增。

### BE-S1-11 上传素材

接口：`POST /api/materials/upload`

验收：

- 支持图片和文本。
- 可绑定ipId。
- 返回materialId和url。

### BE-S1-12 查询生成任务状态

接口：`GET /api/generation-tasks/:id`

验收：

- 返回pending/running/success/failed。
- 失败时返回errorCode和errorMessage。

## 4. AI生成实现策略

Sprint 1允许两种实现：

### 方案A：真实AI生成

后端接入文本模型，根据提示词模板生成结构化结果。

### 方案B：规则Mock生成

如果AI模型暂不可用，后端先返回结构化Mock，保证前后端主链路联调。

产品接受方案B作为Sprint 1通过条件，但必须保留接口结构与真实AI一致。

## 5. 错误码

Sprint 1必须支持：

| 错误码 | 场景 |
|---|---|
| VALIDATION_ERROR | 必填字段缺失 |
| IP_ASSET_NOT_FOUND | IP不存在 |
| TOPIC_NOT_FOUND | 选题不存在 |
| DRAFT_NOT_FOUND | 母稿不存在 |
| AI_GENERATION_FAILED | 生成失败 |
| MATERIAL_UPLOAD_FAILED | 素材上传失败 |

## 6. 后端联调顺序

```text
IP资产接口
↓
策略生成接口
↓
栏目生成接口
↓
选题生成接口
↓
母稿生成接口
↓
素材上传接口
↓
生成任务状态接口
```

## 7. 后端验收标准

- 可创建IP。
- 可生成策略。
- 可生成栏目。
- 可生成选题。
- 可生成母稿。
- 可上传素材。
- 生成任务有状态。
- 所有结果可追溯到ipId。
- 所有失败有错误码。

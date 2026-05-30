# IP全案系统P0数据模型详细说明

## 1. 文档目标

本文档定义P0阶段核心数据对象、字段、关系和追溯链路，供后端建表、前端联调和测试验收使用。

## 2. 建模原则

- 所有平台内容必须能追溯到IP、选题和内容母稿。
- 所有图片素材必须能追溯来源、用途和生成任务。
- 授权密钥必须加密存储。
- AI生成结果必须保留输入快照，方便重生成和排查问题。
- P0只做单用户/单团队基础模型，预留owner字段。

## 3. 核心关系

```text
IPAsset 1 -> N ContentStrategy
IPAsset 1 -> N ContentColumn
IPAsset 1 -> N Topic
IPAsset 1 -> N Material
Topic 1 -> 1 ContentDraft
ContentDraft 1 -> N PlatformContent
PlatformContent 1 -> N Material
PublishAuth 1 -> N WechatSyncRecord
GenerationTask 1 -> 0/1 ResultEntity
```

## 4. ip_assets

用途：保存IP基础资料。

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | IP ID |
| ownerId | string | 否 | 所属用户或团队，P0可预留 |
| name | string | 是 | IP名称 |
| type | enum | 是 | person/expert/boss/brand/product/store/pet/course/service |
| industry | string | 否 | 行业 |
| targetAudience | text | 是 | 目标用户 |
| businessGoal | string | 是 | 商业目标 |
| mainPlatforms | array | 是 | 主平台 |
| secondaryPlatforms | array | 否 | 辅助平台 |
| tone | text | 否 | 表达风格 |
| visualStyle | text | 否 | 视觉风格 |
| conversionPath | text | 否 | 转化路径 |
| forbiddenExpressions | text | 否 | 禁用表达 |
| profileStatus | enum | 是 | incomplete/complete |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |

## 5. content_strategies

用途：保存IP内容策略。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 策略ID |
| ipId | string | 是 | 所属IP |
| positioning | text | 是 | IP定位一句话 |
| targetUserProfile | text | 是 | 用户画像 |
| corePainPoints | json | 是 | 核心痛点 |
| accountValue | text | 否 | 账号价值 |
| differentiation | text | 否 | 差异化表达 |
| platformRoles | json | 是 | 平台分工 |
| conversionPath | text | 否 | 转化路径 |
| forbiddenDirections | json | 否 | 禁做方向 |
| inputSnapshot | json | 是 | 生成输入快照 |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |

## 6. content_columns

用途：保存栏目矩阵。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 栏目ID |
| ipId | string | 是 | 所属IP |
| strategyId | string | 否 | 来源策略 |
| name | string | 是 | 栏目名称 |
| positioning | text | 是 | 栏目定位 |
| platforms | array | 是 | 适合平台 |
| targetUser | text | 否 | 目标用户 |
| problemSolved | text | 否 | 解决问题 |
| contentFormat | string | 否 | 内容形式 |
| frequency | string | 否 | 推荐频率 |
| sampleTopics | json | 否 | 代表选题 |
| conversionAction | text | 否 | 转化动作 |
| materialRequirement | text | 否 | 素材要求 |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |

## 7. topics

用途：保存内容选题。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 选题ID |
| ipId | string | 是 | 所属IP |
| columnId | string | 否 | 所属栏目 |
| title | string | 是 | 选题标题 |
| platforms | array | 是 | 目标平台 |
| contentGoal | string | 是 | 内容目标 |
| userPainPoint | text | 否 | 用户痛点 |
| coreViewpoint | text | 否 | 核心观点 |
| angle | text | 否 | 内容角度 |
| status | enum | 是 | todo/in_progress/ready_to_publish/published/reviewed/discarded/failed |
| priority | enum | 否 | high/medium/low |
| plannedPublishAt | datetime | 否 | 计划发布时间 |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |

## 8. content_drafts

用途：保存内容母稿。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 母稿ID |
| ipId | string | 是 | 所属IP |
| topicId | string | 是 | 所属选题 |
| painPoint | text | 是 | 用户痛点 |
| coreViewpoint | text | 是 | 核心观点 |
| logic | text | 是 | 论证逻辑 |
| cases | text | 否 | 案例素材 |
| goldenSentences | json | 否 | 金句 |
| conversionAction | text | 否 | 转化动作 |
| forbiddenExpressions | text | 否 | 禁用表达 |
| inputSnapshot | json | 是 | 生成输入快照 |
| version | integer | 是 | 版本号 |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |

## 9. platform_contents

用途：保存各平台生成结果。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 平台内容ID |
| ipId | string | 是 | 所属IP |
| topicId | string | 是 | 所属选题 |
| draftId | string | 是 | 来源母稿 |
| platform | enum | 是 | wechat/xiaohongshu/douyin/shipinhao/moments |
| contentType | string | 是 | article/note/script/post |
| title | string | 否 | 标题 |
| body | text | 是 | 正文 |
| structuredContent | json | 否 | 结构化内容 |
| images | json | 否 | 图片引用列表 |
| coverMaterialId | string | 否 | 封面素材ID |
| tags | json | 否 | 标签 |
| status | enum | 是 | not_started/generating/generated/edited/exported/synced/failed |
| exportPackageId | string | 否 | 发布包ID |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |

## 10. materials

用途：保存用户上传和AI生成素材。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 素材ID |
| ipId | string | 否 | 所属IP |
| topicId | string | 否 | 所属选题 |
| platformContentId | string | 否 | 关联平台内容 |
| type | enum | 是 | image/text/document/video/audio |
| source | enum | 是 | upload/ai_generated/external |
| usage | string | 否 | cover/body_image/reference/qrcode |
| url | string | 否 | 素材URL |
| textContent | text | 否 | 文本素材 |
| prompt | text | 否 | 生成提示词 |
| metadata | json | 否 | 宽高、大小、格式等 |
| createdAt | datetime | 是 | 创建时间 |

## 11. publish_auths

用途：保存平台授权配置。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 授权ID |
| platform | enum | 是 | wechat/image_model |
| accountName | string | 是 | 账号名称 |
| appId | string | 否 | AppID |
| encryptedSecret | text | 是 | 加密密钥 |
| tokenEncrypted | text | 否 | 加密token |
| tokenExpiresAt | datetime | 否 | token过期时间 |
| status | enum | 是 | not_configured/configured_not_tested/valid/invalid/expired |
| lastTestAt | datetime | 否 | 最近测试时间 |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |

## 12. generation_tasks

用途：保存AI生成和异步任务。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 任务ID |
| taskType | enum | 是 | strategy/column/topic/draft/article/image/sync/export |
| bizId | string | 否 | 关联业务ID |
| status | enum | 是 | pending/running/success/failed/cancelled/timeout |
| progress | integer | 否 | 进度0-100 |
| inputSnapshot | json | 是 | 输入快照 |
| result | json | 否 | 结果 |
| errorCode | string | 否 | 错误码 |
| errorMessage | text | 否 | 错误信息 |
| createdAt | datetime | 是 | 创建时间 |
| updatedAt | datetime | 是 | 更新时间 |
| finishedAt | datetime | 否 | 完成时间 |

## 13. wechat_sync_records

用途：保存公众号草稿同步记录。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 同步记录ID |
| authId | string | 是 | 公众号授权ID |
| platformContentId | string | 是 | 平台内容ID |
| title | string | 是 | 标题 |
| digest | string | 是 | 摘要 |
| thumbMediaId | string | 否 | 微信封面media_id |
| wechatDraftMediaId | string | 否 | 草稿media_id |
| status | enum | 是 | pending/running/synced/failed |
| errorCode | string | 否 | 错误码 |
| errorMessage | text | 否 | 错误信息 |
| syncedAt | datetime | 否 | 同步时间 |
| createdAt | datetime | 是 | 创建时间 |

## 14. export_packages

用途：保存小红书、短视频、朋友圈导出包。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 发布包ID |
| platformContentId | string | 是 | 平台内容ID |
| platform | enum | 是 | xiaohongshu/douyin/shipinhao/moments |
| packageType | enum | 是 | zip/txt/json |
| downloadUrl | string | 否 | 下载地址 |
| copyBlocks | json | 否 | 可复制文本块 |
| status | enum | 是 | generating/ready/failed |
| createdAt | datetime | 是 | 创建时间 |

## 15. operation_logs

用途：记录关键操作。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 日志ID |
| actorId | string | 否 | 操作人 |
| action | string | 是 | 操作类型 |
| targetType | string | 是 | 目标类型 |
| targetId | string | 否 | 目标ID |
| result | enum | 是 | success/failed |
| errorCode | string | 否 | 错误码 |
| metadata | json | 否 | 脱敏元数据 |
| createdAt | datetime | 是 | 创建时间 |

## 16. 索引建议

- ip_assets：ownerId、type、updatedAt。
- topics：ipId、columnId、status、plannedPublishAt。
- content_drafts：ipId、topicId。
- platform_contents：ipId、topicId、draftId、platform、status。
- materials：ipId、topicId、platformContentId、type、source。
- generation_tasks：taskType、bizId、status、createdAt。
- wechat_sync_records：authId、platformContentId、status。

## 17. P0数据模型验收标准

- 创建IP后能生成策略、栏目、选题、母稿。
- 平台内容可追溯到IP、选题、母稿。
- AI图片可追溯到生成任务和使用场景。
- 公众号草稿同步可追溯到授权和平台内容。
- 密钥不明文存储。
- 生成失败可记录错误码和输入快照。

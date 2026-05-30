# IP全案系统P0前端页面组件拆分

## 1. 文档目标

本文档用于指导前端将P0页面拆成可开发组件，明确页面结构、组件职责、状态和接口依赖。

## 2. 前端开发原则

- 先主流程，后细节体验。
- 所有AI生成结果必须可编辑、可复制、可重新生成、可保存。
- 所有生成动作必须有loading、success、failed、retry状态。
- 图片生成按异步任务处理。
- 公众号草稿同步必须展示步骤进度和错误建议。
- 不改提词器模块，只导出提词器文本。

## 3. 页面路由建议

```text
/workspace
/ip-assets
/ip-assets/:id
/topics
/drafts/:id
/wechat
/wechat/articles/:id
/wechat/articles/:id/preview
/wechat/articles/:id/sync
/xhs
/xhs/packages/:id
/video
/video/packages/:id
/moments
/materials
/image-generator
/auth
```

## 4. 通用组件

### 4.1 GenerateButton

用途：所有AI生成按钮。

状态：

```text
idle
loading
success
failed
```

能力：

- 防重复点击。
- 显示生成中。
- 失败后可重试。
- 支持二次确认覆盖。

### 4.2 EditableResultBlock

用途：AI生成文本结果展示和编辑。

能力：

- 编辑。
- 复制。
- 保存。
- 重新生成。
- 显示未保存状态。

### 4.3 ImageGenerationCard

用途：图片生成结果卡片。

字段：

```text
图片用途
图中文字
生成提示词
图片预览
生成状态
重新生成
保存素材库
```

### 4.4 PlatformBadge

用途：展示平台标签。

平台：

```text
公众号
小红书
抖音
视频号
朋友圈
```

### 4.5 ErrorSuggestion

用途：展示错误原因和处理建议。

结构：

```text
错误标题
错误原因
处理建议
重试按钮
```

### 4.6 CopyButton

用途：复制标题、正文、标签、话术。

状态：

```text
默认
复制成功
复制失败
```

## 5. 全案首页组件

页面：`/workspace`

组件：

- CurrentIpSwitcher
- QuickActionGrid
- PlatformEntryCards
- TodoContentList
- AuthStatusAlert
- RecentContentList
- EmptyIpState

接口依赖：

- `GET /api/ip-assets`
- `GET /api/topics`
- `GET /api/platform-contents/recent`
- `GET /api/auth/status`

验收：

- 无IP时展示创建IP引导。
- 有IP时展示四平台入口。
- 未配置公众号授权时展示提醒。

## 6. IP资产页面组件

页面：`/ip-assets`、`/ip-assets/:id`

组件：

- IpAssetTable
- IpAssetFilter
- IpAssetForm
- IpTypeSelector
- PlatformSelector
- MaterialBindPanel
- RequiredFieldNotice

接口依赖：

- `GET /api/ip-assets`
- `POST /api/ip-assets`
- `PUT /api/ip-assets/:id`
- `POST /api/materials/upload`

验收：

- 必填缺失时禁止保存。
- 保存成功后可进入内容策略。
- 上传素材后显示在绑定素材区。

## 7. 内容母稿页面组件

页面：`/drafts/:id`

组件：

- TopicSummaryPanel
- IpContextPanel
- DraftEditor
- DraftGenerateToolbar
- PlatformDistributeBar
- RegenerateConfirmModal

接口依赖：

- `GET /api/topics/:id`
- `POST /api/content-drafts/generate`
- `PUT /api/content-drafts/:id`

验收：

- 母稿未生成时显示生成按钮。
- 母稿已生成后可编辑保存。
- 分发按钮能进入对应平台页面。

## 8. 公众号页面组件

页面：`/wechat`、`/wechat/articles/:id`

组件：

- WechatArticleWorkspace
- ArticleTypeSelector
- TitleCandidateList
- DigestEditor
- OutlineEditor
- ArticleBodyEditor
- ConversionBlockEditor
- WechatCoverPanel
- WechatImagePanel
- WechatTemplateSelector
- WechatActionSidebar

接口依赖：

- `POST /api/wechat/articles/generate`
- `POST /api/images/generate`
- `GET /api/images/tasks/:taskId`

验收：

- 标题候选可选择。
- 摘要和正文可编辑。
- 封面生成状态可见。
- 可进入排版预览。

## 9. 公众号预览组件

页面：`/wechat/articles/:id/preview`

组件：

- WechatMobilePreview
- TemplateSwitcher
- HtmlWarningPanel
- PreviewToolbar

接口依赖：

- `POST /api/wechat/layout/render`

验收：

- 能渲染移动端预览。
- 能切换模板。
- HTML风险可展示。
- 可跳转同步草稿。

## 10. 公众号同步组件

页面：`/wechat/articles/:id/sync`

组件：

- WechatAuthStatusCard
- SyncPrecheckList
- SyncStepProgress
- SyncResultPanel
- WechatErrorSuggestion

接口依赖：

- `POST /api/wechat/auth/test`
- `POST /api/wechat/media/upload-cover`
- `POST /api/wechat/drafts/create`

验收：

- 同步步骤清晰。
- 成功后显示草稿同步成功。
- 失败后显示原因和处理建议。

## 11. 小红书组件

页面：`/xhs`、`/xhs/packages/:id`

组件：

- XhsWorkspace
- XhsNoteTypeSelector
- XhsTitleCandidates
- XhsBodyEditor
- XhsTagEditor
- XhsCommentGuideEditor
- XhsDmScriptEditor
- XhsImagePlanList
- XhsPackagePreview
- XhsExportActions

接口依赖：

- `POST /api/xhs/notes/generate`
- `POST /api/images/generate`
- `GET /api/images/tasks/:taskId`
- `POST /api/xhs/packages/export`

验收：

- 标题、正文、标签可编辑。
- 图片卡片可逐张重生成。
- 发布包可复制文案和下载图片。

## 12. 短视频组件

页面：`/video`、`/video/packages/:id`

组件：

- VideoWorkspace
- VideoPlatformSwitcher
- VideoGoalSelector
- HookEditor
- SpokenScriptEditor
- StoryboardTable
- SubtitleHighlightEditor
- TeleprompterExportPanel
- VideoPackagePreview

接口依赖：

- `POST /api/videos/scripts/generate`
- `POST /api/videos/teleprompter/export`

验收：

- 抖音/视频号切换明显。
- 分镜表格可编辑。
- 提词器稿可复制或下载。
- 不调用提词器功能。

## 13. 朋友圈组件

页面：`/moments`

组件：

- MomentsWorkspace
- MomentsTypeSelector
- MomentsBodyEditor
- FirstCommentEditor
- DmScriptEditor
- WeeklyPlanTable
- MomentsCopyActions

接口依赖：

- `POST /api/private-domain/posts/generate`

验收：

- 朋友圈正文可编辑复制。
- 评论区第一条可编辑复制。
- 私聊承接话术可编辑复制。
- 一周计划可展示。

## 14. 图片生成中心组件

页面：`/image-generator`

组件：

- ImageUsageSelector
- PlatformImageConfigForm
- ReferenceMaterialPicker
- ImagePromptPreview
- ImageTaskList
- ImageResultGrid

接口依赖：

- `POST /api/images/generate`
- `GET /api/images/tasks/:taskId`
- `POST /api/materials/save-generated`

验收：

- 可选择图片用途。
- 可上传或选择参考图。
- 可查看生成提示词。
- 可保存到素材库。

## 15. 发布授权组件

页面：`/auth`

组件：

- WechatAuthForm
- ImageModelAuthForm
- AuthStatusBadge
- SecretMaskedDisplay
- DeleteAuthConfirmModal
- AuthTestResultPanel

接口依赖：

- `POST /api/wechat/auth/save`
- `POST /api/wechat/auth/test`
- `POST /api/image-model/auth/save`
- `POST /api/image-model/auth/test`

验收：

- 密钥输入后不回显明文。
- 授权测试结果明确。
- 删除授权需要确认。

## 16. 前端开发顺序

```text
通用组件
↓
全案首页 + IP资产
↓
内容母稿
↓
公众号工作台 + 预览 + 同步
↓
小红书工作台 + 发布包
↓
短视频工作台
↓
朋友圈工作台
↓
图片生成中心 + 发布授权
```

## 17. 前端验收标准

- P0主流程页面都能串起来。
- 生成中、失败、重试状态完整。
- 所有AI结果可编辑可复制。
- 图片异步任务有状态展示。
- 公众号同步有步骤进度。
- 小红书发布包可以下载和复制。
- 提词器模块不被改动。

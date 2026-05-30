# IP全案系统P0-AI生成任务状态机

## 1. 文档目标

本文档定义P0阶段AI生成任务、图片生成任务、公众号同步任务和发布包导出任务的状态机，保证前端、后端和测试对任务状态理解一致。

## 2. 任务类型

P0任务类型包括：

```text
strategy_generation
column_generation
topic_generation
draft_generation
wechat_article_generation
wechat_layout_render
image_generation
wechat_sync
xhs_note_generation
video_script_generation
moments_post_generation
package_export
teleprompter_export
```

## 3. 通用任务状态

```text
pending
running
success
failed
cancelled
timeout
```

状态含义：

| 状态 | 含义 | 前端表现 |
|---|---|---|
| pending | 任务已创建，等待执行 | 排队中 |
| running | 任务执行中 | 生成中/同步中/导出中 |
| success | 任务成功 | 展示结果 |
| failed | 任务失败 | 展示错误和重试 |
| cancelled | 用户取消 | 展示已取消 |
| timeout | 任务超时 | 展示超时并允许重试 |

## 4. 通用状态流

```text
pending
↓
running
↓
success
```

异常流：

```text
pending/running
↓
failed 或 timeout 或 cancelled
```

## 5. 文本生成任务状态机

适用任务：策略、栏目、选题、母稿、公众号文章、小红书笔记、短视频脚本、朋友圈文案。

### 状态流

```text
not_started
↓ 点击生成
pending
↓
running
↓
success
↓
edited
↓
saved
```

异常：

```text
running
↓
failed
↓ 点击重试
pending
```

### 前端要求

- 生成中禁止重复点击。
- 生成成功后结果可编辑。
- 编辑后显示未保存状态。
- 重新生成前提示可能覆盖当前内容。
- 失败后展示错误原因和重试按钮。

## 6. 图片生成任务状态机

适用任务：公众号封面、小红书封面、小红书配图、短视频封面、朋友圈海报。

### 状态流

```text
not_started
↓ 点击生成
pending
↓
running
↓
success
↓
saved_to_materials
```

异常：

```text
running
↓
timeout
↓
retry 或 later_check
```

### 图片任务字段

```text
taskId
usage
platform
prompt
referenceMaterialIds
status
progress
imageUrls
materialIds
errorCode
errorMessage
```

### 前端要求

- 图片生成必须展示任务状态。
- 支持轮询查询。
- 支持单张重生成。
- 支持保存到素材库。
- 超时不应清空用户输入。

## 7. 公众号同步任务状态机

适用任务：公众号草稿同步。

### 详细状态

```text
not_started
↓
checking_auth
↓
getting_token
↓
uploading_cover
↓
processing_images
↓
rendering_html
↓
creating_draft
↓
synced
```

异常状态：

```text
auth_failed
token_failed
cover_upload_failed
image_process_failed
html_invalid
draft_create_failed
timeout
```

### 前端进度文案

| 状态 | 文案 |
|---|---|
| checking_auth | 正在检查公众号授权 |
| getting_token | 正在获取公众号access_token |
| uploading_cover | 正在上传封面素材 |
| processing_images | 正在处理正文图片 |
| rendering_html | 正在生成公众号排版HTML |
| creating_draft | 正在创建公众号草稿 |
| synced | 已成功同步到公众号草稿箱 |

### 错误处理

| 状态 | 用户处理建议 |
|---|---|
| auth_failed | 检查AppID和AppSecret |
| token_failed | 稍后重试或重新测试授权 |
| cover_upload_failed | 检查封面格式和大小 |
| html_invalid | 重新排版或删除不兼容内容 |
| draft_create_failed | 查看接口错误并重试 |
| timeout | 稍后重试 |

## 8. 发布包导出任务状态机

适用任务：小红书发布包、短视频发布包、朋友圈发布包、提词器导入稿。

### 状态流

```text
not_started
↓
generating
↓
ready
↓
downloaded/copied
```

异常：

```text
generating
↓
failed
```

### 前端要求

- 导出中展示进度。
- 导出成功展示下载按钮。
- 复制成功展示短提示。
- 导出失败可重试。

## 9. 重试规则

### 可自动重试

- 网络短暂失败。
- 图片生成超时。
- access_token过期后刷新。

### 必须用户处理后重试

- AppSecret错误。
- IP白名单错误。
- 图片格式不支持。
- 必填字段缺失。
- HTML不兼容。

## 10. 任务取消规则

P0只允许取消以下任务：

- 图片生成任务。
- 长文生成任务。
- 发布包导出任务。

不建议取消：

- 正在创建公众号草稿的任务。

原因：外部接口可能已经成功，取消会导致状态不一致。

## 11. 输入快照要求

每个任务创建时必须保存inputSnapshot：

```text
ipId
topicId
draftId
platform
prompt
selectedMaterials
userRequirement
createdAt
```

用于：

- 失败排查。
- 重新生成。
- 内容追溯。
- 测试复现。

## 12. P0验收标准

- 文本生成有生成中、成功、失败、重试状态。
- 图片生成有异步任务状态和轮询能力。
- 公众号草稿同步有分步骤状态。
- 发布包导出有生成、可下载、失败状态。
- 所有失败状态都有错误码和用户可理解提示。
- 提词器导入稿导出不修改提词器模块。

# IP全案系统P0后端技术预研清单

## 1. 文档目标

本文档用于指导后端在P0正式开发前完成关键技术验证，避免公众号接口、图片模型、密钥安全、异步任务和数据模型在开发中后期阻塞。

## 2. 预研优先级

| 优先级 | 预研项 | 必须产出 |
|---|---|---|
| P0-1 | 公众号草稿同步链路 | 可运行demo和错误码记录 |
| P0-2 | 图片模型调用 | 图片生成demo和失败重试策略 |
| P0-3 | 密钥加密存储 | AppSecret/API Key加密方案 |
| P0-4 | 异步生成任务 | 任务状态模型和查询接口 |
| P0-5 | 核心数据模型 | IP、选题、母稿、平台内容、素材、授权表结构 |
| P0-6 | 发布包导出 | zip生成和下载URL方案 |
| P0-7 | 日志与错误码 | 统一错误码和脱敏日志规范 |

## 3. 公众号草稿同步预研

### 3.1 目标

验证从AppID/AppSecret到公众号草稿箱创建成功的完整链路。

### 3.2 必测链路

```text
保存AppID/AppSecret
↓
获取access_token
↓
上传封面图
↓
生成公众号HTML
↓
调用draft/add
↓
公众号后台草稿箱可见
```

### 3.3 验证点

- AppID/AppSecret是否能成功换取access_token。
- 当前服务器IP是否需要配置白名单。
- 封面图片上传接口是否可用。
- thumb_media_id是否能用于草稿封面。
- HTML内容是否能被公众号草稿接受。
- draft/add接口是否有账号权限要求。
- 草稿创建后公众号后台是否可见。

### 3.4 必须记录

- 请求接口。
- 请求参数。
- 微信返回原始错误码。
- 系统映射错误码。
- 处理建议。

### 3.5 demo验收标准

- 使用测试公众号配置能成功创建一篇草稿。
- 草稿包含标题、作者、摘要、封面、正文。
- 失败时能识别AppSecret错误和IP白名单错误。
- 日志不出现完整AppSecret和access_token。

## 4. 图片模型调用预研

### 4.1 目标

验证ChatGPT Image / image2或其他图片模型能满足公众号封面、小红书封面、小红书配图的P0需求。

### 4.2 必测场景

- 文生图。
- 图生图。
- 带图中文字的封面图。
- 小红书3:4比例图。
- 公众号封面比例图。
- 失败重试。
- 超时处理。

### 4.3 结果记录

每次测试记录：

```text
模型名称
请求参数
生成耗时
图片URL
是否支持参考图
是否支持指定比例
图片文字是否清晰
失败错误码
```

### 4.4 验收标准

- 能生成至少1张公众号封面。
- 能生成至少1张小红书封面。
- 能生成至少3张小红书配图。
- 图片结果可保存到素材库或对象存储。
- 生成失败可返回明确错误。

## 5. 密钥加密存储预研

### 5.1 目标

确保公众号AppSecret、图片模型API Key不会明文泄露。

### 5.2 涉及密钥

- 公众号AppSecret。
- 图片模型API Key。
- 对象存储密钥。
- 后续平台授权token。

### 5.3 要求

- 入库前加密。
- 前端返回脱敏值。
- 日志不输出原文。
- 删除授权时清除密钥和token缓存。
- 密钥更新要重新测试授权。

### 5.4 验收标准

- 数据库不可直接看到明文AppSecret。
- 接口响应不返回明文密钥。
- 错误日志不包含明文密钥。
- 授权测试可正常解密使用。

## 6. 异步任务预研

### 6.1 目标

支持长文、图片等耗时生成任务。

### 6.2 任务类型

```text
strategy_generation
column_generation
topic_generation
draft_generation
wechat_article_generation
image_generation
wechat_sync
package_export
```

### 6.3 任务状态

```text
pending
running
success
failed
cancelled
timeout
```

### 6.4 任务字段

```text
taskId
taskType
bizId
status
progress
inputSnapshot
result
errorCode
errorMessage
createdAt
updatedAt
finishedAt
```

### 6.5 验收标准

- 图片生成可创建任务。
- 前端可轮询任务状态。
- 任务失败有错误信息。
- 任务结果可关联素材或平台内容。

## 7. 核心数据模型预研

### 7.1 必需数据表或集合

```text
ip_assets
content_strategies
content_columns
topics
content_drafts
platform_contents
materials
image_tasks
templates
publish_auths
generation_tasks
operation_logs
```

### 7.2 关键关系

```text
IPAsset 1 -> N Topic
IPAsset 1 -> N Material
Topic 1 -> 1 ContentDraft
ContentDraft 1 -> N PlatformContent
PlatformContent 1 -> N Material
PublishAuth 1 -> N SyncRecord
```

### 7.3 验收标准

- 任意平台内容可追溯到IP、选题和母稿。
- 任意图片素材可追溯来源任务和用途。
- 任意公众号草稿同步可追溯授权账号和文章。

## 8. 发布包导出预研

### 8.1 目标

支持小红书、短视频、朋友圈发布包导出。

### 8.2 导出类型

- 小红书图片zip。
- 小红书文案txt。
- 短视频脚本txt。
- 提词器导入稿txt。
- 朋友圈文案txt。

### 8.3 验收标准

- 可生成zip。
- 下载链接可访问。
- 文件命名清晰。
- 文案文件不乱码。
- 导出失败有错误提示。

## 9. 统一错误码预研

### 9.1 必须覆盖

- 参数校验错误。
- AI生成失败。
- 图片生成超时。
- 素材上传失败。
- 公众号授权失败。
- 公众号IP白名单错误。
- 公众号封面上传失败。
- 公众号草稿创建失败。
- 发布包导出失败。
- 密钥加密失败。

### 9.2 错误响应要求

```json
{
  "success": false,
  "code": "WECHAT_IP_NOT_ALLOWED",
  "message": "当前服务器IP未加入公众号后台白名单。",
  "suggestion": "请进入公众号后台开发设置，添加服务器IP后重试。"
}
```

## 10. 后端预研交付物

后端预研完成后必须提交：

- 公众号草稿同步demo结果。
- 图片模型调用demo结果。
- 密钥加密方案说明。
- 异步任务模型说明。
- 核心数据模型初稿。
- 错误码映射表。
- 发布包导出demo。

## 11. 后端预研验收标准

- 公众号草稿同步可跑通或明确阻塞原因。
- 图片模型可生成P0所需图片或明确替代方案。
- 密钥安全方案通过安全评审。
- 异步任务状态可被前端查询。
- 数据模型支持P0主链路。
- 错误码可被前端直接展示为用户可理解提示。

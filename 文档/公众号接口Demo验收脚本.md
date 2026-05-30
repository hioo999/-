# 公众号接口Demo验收脚本

## 1. 文档目标

本文档用于验收后端公众号接口demo是否满足P0草稿同步预研要求。

Demo不要求接入完整产品页面，但必须验证真实接口链路。

## 2. Demo验收目标

必须跑通：

```text
AppID/AppSecret配置
↓
获取access_token
↓
上传封面图
↓
生成公众号HTML
↓
调用draft/add创建草稿
↓
公众号后台草稿箱可见
```

## 3. 准备项

### 3.1 账号准备

- 测试公众号账号。
- AppID。
- AppSecret。
- 确认账号有草稿接口权限。
- 确认当前服务器IP已加入公众号后台白名单。

### 3.2 素材准备

- 一张测试封面图。
- 一段测试HTML正文。
- 文章标题。
- 文章摘要。
- 作者名称。

### 3.3 环境准备

- 后端服务启动。
- 可访问外网微信接口。
- 日志记录开启。
- 密钥加密能力开启。

## 4. 测试文章样例

标题：

```text
公众号草稿同步测试文章
```

摘要：

```text
这是一篇用于验证IP全案系统公众号草稿同步能力的测试文章。
```

作者：

```text
IP全案系统
```

正文HTML：

```html
<section style="font-size:16px;line-height:1.8;color:#222;">
  <p>这是一篇公众号草稿同步测试文章。</p>
  <p><strong>如果你能在公众号后台草稿箱看到这篇文章，说明同步链路已跑通。</strong></p>
  <hr style="border:none;border-top:1px solid #eee;margin:24px 0;" />
  <p>本文用于验证标题、摘要、作者、封面和正文HTML是否正常进入草稿箱。</p>
</section>
```

## 5. 验收步骤

## 5.1 保存公众号授权

操作：

```text
调用保存授权接口，提交公众号名称、AppID、AppSecret。
```

预期：

- 返回authId。
- 返回脱敏AppID或授权状态。
- 不返回完整AppSecret。
- 数据库不明文保存AppSecret。

验收结果记录：

```text
是否通过：
authId：
备注：
```

## 5.2 测试授权并获取access_token

操作：

```text
调用授权测试接口。
```

预期：

- 成功获取access_token。
- access_token被缓存。
- 返回授权有效状态。
- 日志不输出完整access_token。

失败时必须识别：

- AppID错误。
- AppSecret错误。
- IP白名单错误。
- 微信接口限频。

验收结果记录：

```text
是否通过：
token是否获取：
token是否缓存：
备注：
```

## 5.3 上传封面图

操作：

```text
调用封面上传接口，提交测试封面图。
```

预期：

- 上传成功。
- 返回thumb_media_id。
- 系统记录materialId和thumb_media_id关系。

失败时必须识别：

- 图片格式不支持。
- 图片过大。
- token失效。
- 微信接口返回错误。

验收结果记录：

```text
是否通过：
thumb_media_id：
备注：
```

## 5.4 生成公众号HTML

操作：

```text
使用测试正文HTML，调用HTML渲染或检查接口。
```

预期：

- HTML非空。
- 不包含script。
- 不依赖外部CSS。
- 主要样式为内联CSS。

验收结果记录：

```text
是否通过：
HTML长度：
是否有不兼容标签：
备注：
```

## 5.5 创建公众号草稿

操作：

```text
调用draft/add草稿创建接口。
```

入参必须包含：

```text
authId
title
author
digest
contentHtml
thumb_media_id
commentEnabled
onlyFansCanComment
```

预期：

- 接口返回成功。
- 返回草稿media_id或等价标识。
- 系统记录同步状态为synced。
- 公众号后台草稿箱能看到文章。

验收结果记录：

```text
是否通过：
草稿media_id：
公众号后台是否可见：
备注：
```

## 6. 异常验收

## 6.1 错误AppSecret

操作：

```text
使用错误AppSecret测试授权。
```

预期：

- 返回WECHAT_AUTH_FAILED。
- 用户提示：公众号授权失败，请检查AppID和AppSecret。
- 日志不暴露错误AppSecret全文。

## 6.2 IP白名单错误

操作：

```text
在未配置白名单环境测试授权。
```

预期：

- 返回WECHAT_IP_NOT_ALLOWED。
- 用户提示：当前服务器IP未加入公众号后台白名单。
- 提供处理建议。

## 6.3 封面上传失败

操作：

```text
上传不支持格式或超大图片。
```

预期：

- 返回WECHAT_COVER_UPLOAD_FAILED。
- 提示检查图片格式和大小。

## 6.4 草稿创建失败

操作：

```text
使用空标题、空HTML或无效thumb_media_id创建草稿。
```

预期：

- 返回WECHAT_DRAFT_CREATE_FAILED或VALIDATION_ERROR。
- 提示缺失字段或草稿创建失败原因。

## 7. 日志验收

必须记录：

- 授权保存操作。
- token获取结果。
- 封面上传结果。
- 草稿创建结果。
- 微信接口错误码。

禁止记录：

- 完整AppSecret。
- 完整access_token。
- 完整图片模型API Key。

## 8. Demo验收表

| 验收项 | 是否通过 | 备注 |
|---|---|---|
| 保存授权成功 |  |  |
| AppSecret加密存储 |  |  |
| 授权测试成功 |  |  |
| access_token缓存 |  |  |
| 封面上传成功 |  |  |
| thumb_media_id获取成功 |  |  |
| HTML检查通过 |  |  |
| 草稿创建成功 |  |  |
| 公众号后台草稿可见 |  |  |
| 错误AppSecret可识别 |  |  |
| IP白名单错误可识别 |  |  |
| 封面上传失败可识别 |  |  |
| 草稿创建失败可识别 |  |  |
| 日志脱敏通过 |  |  |

## 9. Demo通过标准

Demo通过必须满足：

- 真实测试公众号草稿箱能看到同步文章。
- 封面能正常显示。
- 标题、摘要、作者、正文能正常显示。
- AppSecret和access_token不明文暴露。
- 至少覆盖AppSecret错误、IP白名单错误、封面上传失败三个异常。
- 后端能给出前端可直接展示的错误message和suggestion。

## 10. Demo不通过处理

如果Demo不通过，必须明确阻塞类型：

```text
账号权限问题
服务器IP白名单问题
接口调用问题
图片上传问题
HTML兼容问题
密钥安全问题
```

并输出：

```text
阻塞原因
复现步骤
微信原始错误码
系统映射错误码
解决建议
预计修复时间
```

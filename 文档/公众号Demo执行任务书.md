# 公众号Demo执行任务书

## 1. 任务目标

后端在Sprint 0完成公众号草稿同步demo，验证P0公众号链路可行。

目标链路：

```text
AppID/AppSecret
↓
access_token
↓
封面上传 thumb_media_id
↓
公众号HTML
↓
draft/add
↓
公众号后台草稿箱可见
```

## 2. 负责人

负责人角色：后端开发

协作角色：产品、测试、安全

验收角色：产品、测试、安全

## 3. 前置条件

必须准备：

- 测试公众号账号。
- AppID。
- AppSecret。
- 当前后端服务外网IP。
- 公众号后台IP白名单配置权限。
- 测试封面图。
- 测试HTML。
- 后端日志脱敏能力。

## 4. 执行步骤

### Step 1：保存授权配置

动作：保存公众号名称、AppID、AppSecret。

要求：

- AppSecret入库前加密。
- 接口响应不返回完整AppSecret。
- 日志不打印完整AppSecret。

验收：

- 返回authId。
- 数据库中AppSecret不是明文。

### Step 2：获取access_token

动作：使用AppID/AppSecret调用微信token接口。

要求：

- 成功时缓存access_token。
- 保存过期时间。
- 日志不打印完整access_token。

验收：

- 能获取token。
- 能识别AppSecret错误。
- 能识别IP白名单错误。

### Step 3：上传封面

动作：使用access_token上传测试封面图。

要求：

- 检查图片格式。
- 检查图片大小。
- 上传成功后保存thumb_media_id。

验收：

- 返回thumb_media_id。
- 上传失败能给出错误原因。

### Step 4：准备测试HTML

动作：准备公众号兼容HTML。

测试HTML：

```html
<section style='font-size:16px;line-height:1.8;color:#222;'>
  <p>这是一篇公众号草稿同步测试文章。</p>
  <p><strong>如果你能在公众号后台草稿箱看到这篇文章，说明同步链路已跑通。</strong></p>
  <hr style='border:none;border-top:1px solid #eee;margin:24px 0;' />
  <p>本文用于验证标题、摘要、作者、封面和正文HTML是否正常进入草稿箱。</p>
</section>
```

验收：

- HTML非空。
- 不含script。
- 不依赖外部CSS。

### Step 5：创建草稿

动作：调用公众号draft/add接口创建单图文草稿。

参数：

```text
title：公众号草稿同步测试文章
author：IP全案系统
digest：这是一篇用于验证IP全案系统公众号草稿同步能力的测试文章。
content：测试HTML
thumb_media_id：Step 3返回值
need_open_comment：1
only_fans_can_comment：0
```

验收：

- 接口返回成功。
- 返回草稿media_id或等价标识。
- 公众号后台草稿箱可见。

## 5. 异常测试

### 异常1：AppSecret错误

要求：

- 返回错误码：WECHAT_AUTH_FAILED。
- 用户提示：公众号授权失败，请检查AppID和AppSecret。

### 异常2：IP白名单错误

要求：

- 返回错误码：WECHAT_IP_NOT_ALLOWED。
- 用户提示：当前服务器IP未加入公众号后台白名单，请到公众号后台配置。

### 异常3：封面上传失败

要求：

- 返回错误码：WECHAT_COVER_UPLOAD_FAILED。
- 用户提示：封面上传失败，请检查格式和大小。

### 异常4：草稿创建失败

要求：

- 返回错误码：WECHAT_DRAFT_CREATE_FAILED。
- 用户提示：草稿同步失败，请查看详情后重试。

## 6. 交付物

后端必须交付：

- Demo调用记录。
- 成功草稿截图或后台可见证明。
- thumb_media_id记录。
- access_token缓存说明。
- 错误码映射记录。
- 日志脱敏证明。
- 阻塞问题清单。

## 7. 验收表

| 项目 | 通过标准 | 是否通过 |
|---|---|---|
| 保存授权 | 返回authId，密钥加密 |  |
| 获取token | access_token获取并缓存 |  |
| 上传封面 | 返回thumb_media_id |  |
| 创建草稿 | 公众号后台草稿箱可见 |  |
| AppSecret错误 | 能识别并提示 |  |
| IP白名单错误 | 能识别并提示 |  |
| 封面上传失败 | 能识别并提示 |  |
| 日志脱敏 | 不暴露密钥和token |  |

## 8. 不通过处理

如不通过，必须输出：

```text
失败步骤
微信原始错误码
系统错误码
失败原因
是否需要公众号后台配置
是否影响P0
解决建议
预计修复时间
```

如果草稿接口权限无法解决，产品需要重新评估P0公众号能力是否降级为“复制HTML + 人工粘贴到公众号后台”。

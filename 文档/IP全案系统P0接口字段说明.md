# IP全案系统P0接口字段说明

## 1. 文档目标

本文档定义P0阶段接口边界、请求字段、响应结构和状态码口径，供前后端联调使用。

P0接口原则：

- 先支持主链路，不为P2自动发布过度设计。
- AI生成任务统一返回任务状态，图片和长文生成允许异步。
- 所有平台内容都归属到IP、选题和内容母稿。
- 所有授权密钥只允许后端加密存储，前端只显示脱敏状态。

## 2. 通用响应结构

成功响应：

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

失败响应：

```json
{
  "success": false,
  "code": "WECHAT_AUTH_FAILED",
  "message": "公众号授权失败，请检查AppID和AppSecret。",
  "detail": "invalid appsecret"
}
```

分页响应：

```json
{
  "success": true,
  "data": {
    "items": [],
    "page": 1,
    "pageSize": 20,
    "total": 100
  },
  "message": "ok"
}
```

## 3. 核心枚举

### 3.1 IP类型

```text
person
expert
boss
brand
product
store
pet
course
service
```

### 3.2 平台

```text
wechat
xiaohongshu
douyin
shipinhao
moments
```

### 3.3 内容状态

```text
not_started
generating
generated
edited
exported
synced
failed
```

### 3.4 选题状态

```text
todo
in_progress
ready_to_publish
published
reviewed
discarded
failed
```

## 4. IP资产接口

## 4.1 创建IP资产

接口：`POST /api/ip-assets`

请求：

```json
{
  "name": "张老师职业规划IP",
  "type": "expert",
  "industry": "职业教育",
  "targetAudience": "大学生和职场新人",
  "businessGoal": "consulting_leads",
  "mainPlatforms": ["shipinhao", "wechat"],
  "secondaryPlatforms": ["xiaohongshu", "moments"],
  "tone": "专业、直接、接地气",
  "visualStyle": "干净、可信、知识感",
  "conversionPath": "内容种草 -> 私信咨询 -> 预约诊断",
  "forbiddenExpressions": "不承诺保offer，不夸大结果"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "ip_001",
    "name": "张老师职业规划IP",
    "type": "expert",
    "status": "created"
  },
  "message": "IP资产创建成功"
}
```

## 4.2 获取IP资产列表

接口：`GET /api/ip-assets?page=1&pageSize=20&type=expert`

响应字段：

```json
{
  "items": [
    {
      "id": "ip_001",
      "name": "张老师职业规划IP",
      "type": "expert",
      "industry": "职业教育",
      "mainPlatforms": ["shipinhao", "wechat"],
      "profileStatus": "complete",
      "updatedAt": "2026-05-23T18:00:00+08:00"
    }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 1
}
```

## 5. 内容策略接口

## 5.1 生成内容策略

接口：`POST /api/strategies/generate`

请求：

```json
{
  "ipId": "ip_001",
  "stage": "cold_start",
  "extraRequirement": "重点做视频号信任和公众号深度文章"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "strategyId": "strategy_001",
    "positioning": "帮大学生和职场新人做现实可落地的职业选择判断。",
    "targetUserProfile": "缺少行业信息、害怕选错方向、需要实用建议的人群。",
    "corePainPoints": ["不知道选什么行业", "简历没有竞争力", "容易被空泛建议误导"],
    "platformRoles": {
      "wechat": "沉淀深度方法论和案例文章",
      "xiaohongshu": "承接搜索和经验分享",
      "douyin": "用强观点获取曝光",
      "shipinhao": "建立信任和私域承接",
      "moments": "持续触达和咨询转化"
    },
    "conversionPath": "短视频建立认知 -> 公众号深度信任 -> 私域咨询转化",
    "forbiddenDirections": ["过度承诺", "制造焦虑", "贬低具体学校"]
  },
  "message": "内容策略生成成功"
}
```

## 6. 栏目和选题接口

## 6.1 生成栏目矩阵

接口：`POST /api/columns/generate`

请求：

```json
{
  "ipId": "ip_001",
  "strategyId": "strategy_001",
  "count": 8
}
```

响应：

```json
{
  "success": true,
  "data": {
    "columns": [
      {
        "id": "column_001",
        "name": "职业选择避坑",
        "positioning": "帮助用户避开高风险选择",
        "platforms": ["douyin", "shipinhao", "xiaohongshu"],
        "contentFormat": "观点口播/经验笔记",
        "frequency": "每周2条",
        "conversionAction": "引导评论区提问或私信咨询",
        "sampleTopics": ["别只看热门专业，要看你能不能留下来"]
      }
    ]
  },
  "message": "栏目矩阵生成成功"
}
```

## 6.2 批量生成选题

接口：`POST /api/topics/generate`

请求：

```json
{
  "ipId": "ip_001",
  "columnIds": ["column_001"],
  "platforms": ["wechat", "xiaohongshu", "shipinhao", "moments"],
  "count": 20
}
```

响应字段：

```json
{
  "topics": [
    {
      "id": "topic_001",
      "title": "为什么你听了很多建议，还是选不对职业方向？",
      "columnId": "column_001",
      "platforms": ["wechat", "shipinhao", "moments"],
      "contentGoal": "trust_building",
      "userPainPoint": "信息太多但缺少判断标准",
      "coreViewpoint": "职业选择不是找热门，而是匹配个人筹码和行业门槛。",
      "status": "todo"
    }
  ]
}
```

## 7. 内容母稿接口

## 7.1 生成内容母稿

接口：`POST /api/content-drafts/generate`

请求：

```json
{
  "ipId": "ip_001",
  "topicId": "topic_001",
  "materialIds": ["material_001"],
  "requirement": "要有一个真实案例，表达直接一点"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "draftId": "draft_001",
    "topicId": "topic_001",
    "painPoint": "用户听了很多建议，但不知道怎么判断哪些适合自己。",
    "coreViewpoint": "职业选择的核心不是追热点，而是看个人筹码和行业门槛是否匹配。",
    "logic": "先指出误区，再给判断框架，最后用案例说明。",
    "cases": "某普通本科学生盲目追互联网运营，后来转向本地教育销售，收入更稳定。",
    "goldenSentences": ["方向不是别人说出来的，是你拿自己的筹码算出来的。"],
    "conversionAction": "引导用户私信发送职业方向，领取诊断清单。",
    "forbiddenExpressions": "不承诺结果，不制造焦虑"
  },
  "message": "内容母稿生成成功"
}
```

## 8. 图片生成接口

## 8.1 创建图片生成任务

接口：`POST /api/images/generate`

请求：

```json
{
  "ipId": "ip_001",
  "platform": "xiaohongshu",
  "usage": "cover",
  "ratio": "3:4",
  "style": "真实、小红书干货感、清爽",
  "theme": "职业选择避坑",
  "textOnImage": "别再盲目追热门专业",
  "referenceMaterialIds": ["material_001"],
  "consistencyRequirement": "保持人物气质和品牌色一致",
  "negativePrompt": "不要夸张表情，不要低质感，不要乱码文字"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "taskId": "image_task_001",
    "status": "generating"
  },
  "message": "图片生成任务已创建"
}
```

## 8.2 查询图片生成任务

接口：`GET /api/images/tasks/:taskId`

响应：

```json
{
  "success": true,
  "data": {
    "taskId": "image_task_001",
    "status": "success",
    "images": [
      {
        "url": "https://example.com/image.png",
        "materialId": "material_002",
        "prompt": "..."
      }
    ]
  },
  "message": "图片生成成功"
}
```

## 9. 公众号接口

## 9.1 生成公众号文章

接口：`POST /api/wechat/articles/generate`

请求：

```json
{
  "ipId": "ip_001",
  "draftId": "draft_001",
  "articleType": "deep_opinion",
  "targetWordCount": 1800,
  "tone": "专业、直接、案例感"
}
```

响应字段：

```json
{
  "articleId": "wx_article_001",
  "titles": ["为什么你听了很多建议，还是选不对职业方向？"],
  "digest": "真正影响职业选择的，不是热门行业，而是你能不能用自己的筹码跨过门槛。",
  "outline": ["常见误区", "判断框架", "真实案例", "行动建议"],
  "contentMarkdown": "# 标题...",
  "goldenSentences": ["方向不是别人说出来的，是算出来的。"],
  "conversionBlock": "如果你正在纠结方向，可以私信我你的专业和城市。"
}
```

## 9.2 渲染公众号HTML

接口：`POST /api/wechat/layout/render`

请求：

```json
{
  "articleId": "wx_article_001",
  "templateId": "wx_template_default",
  "contentMarkdown": "# 标题...",
  "imageMaterialIds": ["material_002"]
}
```

响应：

```json
{
  "html": "<section style='font-size:16px;line-height:1.8'>...</section>",
  "warnings": []
}
```

## 9.3 保存公众号授权

接口：`POST /api/wechat/auth/save`

请求：

```json
{
  "accountName": "张老师职业规划",
  "appId": "wx123456",
  "appSecret": "secret_value",
  "defaultAuthor": "张老师",
  "defaultSourceUrl": "",
  "commentEnabled": true,
  "onlyFansCanComment": false
}
```

响应：

```json
{
  "authId": "wechat_auth_001",
  "accountName": "张老师职业规划",
  "appIdMasked": "wx12****3456",
  "status": "saved"
}
```

## 9.4 创建公众号草稿

接口：`POST /api/wechat/drafts/create`

请求：

```json
{
  "authId": "wechat_auth_001",
  "articleId": "wx_article_001",
  "title": "为什么你听了很多建议，还是选不对职业方向？",
  "digest": "真正影响职业选择的，不是热门行业，而是你能不能用自己的筹码跨过门槛。",
  "author": "张老师",
  "contentHtml": "<section>...</section>",
  "coverMaterialId": "material_002",
  "contentSourceUrl": "",
  "commentEnabled": true,
  "onlyFansCanComment": false
}
```

响应：

```json
{
  "success": true,
  "data": {
    "draftId": "wechat_draft_media_id",
    "status": "synced"
  },
  "message": "公众号草稿创建成功"
}
```

## 10. 小红书接口

## 10.1 生成小红书笔记

接口：`POST /api/xhs/notes/generate`

请求：

```json
{
  "ipId": "ip_001",
  "draftId": "draft_001",
  "noteType": "experience",
  "imageCount": 6,
  "tone": "真实、口语、有收藏价值"
}
```

响应字段：

```json
{
  "noteId": "xhs_note_001",
  "titles": ["职业方向别乱选，先看这3个判断标准"],
  "coverTexts": ["别再盲目追热门专业"],
  "body": "很多人选方向的问题，不是信息太少，而是不会判断...",
  "tags": ["职业规划", "大学生就业", "职场新人"],
  "commentGuide": "你现在最纠结的方向是什么？",
  "dmScript": "你可以把专业、城市、目标岗位发我，我帮你看下方向。",
  "imagePlan": [
    {
      "index": 1,
      "purpose": "封面点击",
      "text": "别再盲目追热门专业",
      "prompt": "小红书干货封面，清爽真实..."
    }
  ]
}
```

## 10.2 导出小红书发布包

接口：`POST /api/xhs/packages/export`

请求：

```json
{
  "noteId": "xhs_note_001",
  "imageMaterialIds": ["material_101", "material_102"]
}
```

响应：

```json
{
  "packageId": "xhs_package_001",
  "downloadUrl": "https://example.com/xhs_package.zip",
  "copyBlocks": {
    "title": "职业方向别乱选，先看这3个判断标准",
    "body": "很多人选方向的问题...",
    "tags": "#职业规划 #大学生就业 #职场新人"
  }
}
```

## 11. 短视频接口

## 11.1 生成短视频脚本

接口：`POST /api/videos/scripts/generate`

请求：

```json
{
  "ipId": "ip_001",
  "draftId": "draft_001",
  "platform": "shipinhao",
  "duration": 60,
  "scriptType": "talking_head"
}
```

响应字段：

```json
{
  "scriptId": "video_script_001",
  "title": "听建议没用，职业方向要这样算",
  "hook": "很多人职业选错，不是因为不努力，而是一开始算法就错了。",
  "spokenScript": "你发现没有，很多建议听起来都对，但落到你身上就没用...",
  "storyboards": [
    {
      "shot": 1,
      "duration": "0-3s",
      "visual": "人物正面口播",
      "line": "很多人职业选错，不是因为不努力。",
      "subtitle": "不是不努力，是算法错了"
    }
  ],
  "subtitleHighlights": ["不是不努力，是算法错了"],
  "commentGuide": "你现在最纠结哪个方向？",
  "privateDomainScript": "可以把你的专业和目标岗位发我。"
}
```

## 11.2 导出提词器导入稿

接口：`POST /api/videos/teleprompter/export`

请求：

```json
{
  "scriptId": "video_script_001",
  "format": "plain_text_with_pauses"
}
```

响应：

```json
{
  "teleprompterText": "很多人职业选错，不是因为不努力。\n[停顿]\n而是一开始算法就错了。",
  "downloadUrl": "https://example.com/teleprompter.txt"
}
```

## 12. 朋友圈接口

## 12.1 生成朋友圈内容

接口：`POST /api/private-domain/posts/generate`

请求：

```json
{
  "ipId": "ip_001",
  "draftId": "draft_001",
  "postType": "trust_building",
  "conversionGoal": "consulting_leads"
}
```

响应字段：

```json
{
  "postId": "moments_post_001",
  "body": "这两天连续看了几个同学的职业方向，发现一个共同问题...",
  "firstComment": "如果你也在纠结方向，可以把专业和城市发我。",
  "dmScript": "你现在的情况我先看三个信息：专业、城市、想去的行业。",
  "weeklyPlan": [
    {
      "day": "周一",
      "type": "专业观点",
      "topic": "职业选择先看门槛，不先看热度",
      "goal": "建立专业信任"
    }
  ]
}
```

## 13. 错误码

| 错误码 | 含义 | 用户提示 |
|---|---|---|
| VALIDATION_ERROR | 参数缺失或格式错误 | 请补充必填信息后重试。 |
| AI_GENERATION_FAILED | AI生成失败 | 生成失败，请稍后重试或调整输入。 |
| IMAGE_GENERATION_TIMEOUT | 图片生成超时 | 图片生成时间较长，请稍后查看或重新生成。 |
| MATERIAL_UPLOAD_FAILED | 素材上传失败 | 素材上传失败，请检查格式和大小。 |
| WECHAT_AUTH_FAILED | 公众号授权失败 | 请检查AppID和AppSecret。 |
| WECHAT_IP_NOT_ALLOWED | 公众号IP白名单错误 | 请在公众号后台添加服务器IP。 |
| WECHAT_COVER_UPLOAD_FAILED | 公众号封面上传失败 | 请检查封面格式和大小。 |
| WECHAT_DRAFT_CREATE_FAILED | 公众号草稿创建失败 | 草稿同步失败，请查看错误详情后重试。 |
| SECRET_ENCRYPT_FAILED | 密钥加密失败 | 授权保存失败，请联系管理员。 |

## 14. 联调顺序

建议前后端按以下顺序联调：

```text
IP资产接口
↓
策略/栏目/选题生成接口
↓
内容母稿接口
↓
图片生成接口
↓
公众号文章生成和HTML渲染
↓
公众号授权和草稿同步
↓
小红书笔记和发布包
↓
短视频脚本和提词器稿
↓
朋友圈内容
```

## 15. P0接口验收标准

- 所有创建类接口必须返回ID。
- 所有AI生成类接口必须有生成失败错误码。
- 图片生成支持任务状态查询。
- 公众号授权接口不得返回完整AppSecret。
- 公众号草稿同步失败必须返回可理解错误信息。
- 所有平台内容必须能追溯到IP、选题和内容母稿。
- 提词器导入稿只作为文本导出，不调用或修改提词器功能。

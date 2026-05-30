# IP全案系统P0前端Mock数据样例

## 1. 文档目标

本文档为前端在Sprint 0和Sprint 1搭建页面骨架提供Mock数据样例。Mock结构应尽量贴近后端接口字段，方便后续替换真实接口。

## 2. 当前IP Mock

```json
{
  "id": "ip_001",
  "name": "张老师职业规划IP",
  "type": "expert",
  "industry": "职业教育",
  "targetAudience": "大学生和职场新人",
  "businessGoal": "consulting_leads",
  "mainPlatforms": ["wechat", "shipinhao"],
  "secondaryPlatforms": ["xiaohongshu", "moments"],
  "tone": "专业、直接、接地气",
  "visualStyle": "干净、可信、知识感",
  "conversionPath": "内容种草 -> 私信咨询 -> 预约诊断",
  "forbiddenExpressions": "不承诺保offer，不夸大结果",
  "profileStatus": "complete"
}
```

## 3. 内容策略 Mock

```json
{
  "strategyId": "strategy_001",
  "ipId": "ip_001",
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
}
```

## 4. 栏目 Mock

```json
[
  {
    "id": "column_001",
    "name": "职业选择避坑",
    "positioning": "帮助用户避开高风险选择",
    "platforms": ["douyin", "shipinhao", "xiaohongshu"],
    "contentFormat": "观点口播/经验笔记",
    "frequency": "每周2条",
    "conversionAction": "引导评论区提问或私信咨询"
  },
  {
    "id": "column_002",
    "name": "真实案例拆解",
    "positioning": "用案例建立专业信任",
    "platforms": ["wechat", "xiaohongshu", "moments"],
    "contentFormat": "长文/图文/朋友圈",
    "frequency": "每周1条",
    "conversionAction": "引导预约诊断"
  }
]
```

## 5. 选题 Mock

```json
[
  {
    "id": "topic_001",
    "ipId": "ip_001",
    "columnId": "column_001",
    "title": "为什么你听了很多建议，还是选不对职业方向？",
    "platforms": ["wechat", "xiaohongshu", "shipinhao", "moments"],
    "contentGoal": "trust_building",
    "userPainPoint": "信息太多但缺少判断标准",
    "coreViewpoint": "职业选择不是找热门，而是匹配个人筹码和行业门槛。",
    "status": "todo",
    "priority": "high"
  }
]
```

## 6. 内容母稿 Mock

```json
{
  "draftId": "draft_001",
  "topicId": "topic_001",
  "ipId": "ip_001",
  "painPoint": "用户听了很多建议，但不知道怎么判断哪些适合自己。",
  "coreViewpoint": "职业选择的核心不是追热点，而是看个人筹码和行业门槛是否匹配。",
  "logic": "先指出误区，再给判断框架，最后用案例说明。",
  "cases": "某普通本科学生盲目追互联网运营，后来转向本地教育销售，收入更稳定。",
  "goldenSentences": ["方向不是别人说出来的，是你拿自己的筹码算出来的。"],
  "conversionAction": "引导用户私信发送职业方向，领取诊断清单。",
  "forbiddenExpressions": "不承诺结果，不制造焦虑",
  "status": "generated"
}
```

## 7. 公众号文章 Mock

```json
{
  "articleId": "wx_article_001",
  "platform": "wechat",
  "titles": ["为什么你听了很多建议，还是选不对职业方向？", "职业方向别乱选，先看这3个判断标准"],
  "recommendedTitle": "为什么你听了很多建议，还是选不对职业方向？",
  "digest": "真正影响职业选择的，不是热门行业，而是你能不能用自己的筹码跨过门槛。",
  "outline": ["常见误区", "判断框架", "真实案例", "行动建议"],
  "contentMarkdown": "# 为什么你听了很多建议，还是选不对职业方向？\n\n很多人选方向时，第一反应是问哪个行业热门...",
  "conversionBlock": "如果你正在纠结方向，可以私信我你的专业和城市。",
  "cover": {
    "materialId": "material_cover_001",
    "url": "https://example.com/wx-cover.png",
    "status": "generated"
  },
  "status": "generated"
}
```

## 8. 公众号同步状态 Mock

```json
{
  "syncId": "wx_sync_001",
  "status": "creating_draft",
  "steps": [
    { "key": "checking_auth", "label": "检查公众号授权", "status": "success" },
    { "key": "getting_token", "label": "获取access_token", "status": "success" },
    { "key": "uploading_cover", "label": "上传封面", "status": "success" },
    { "key": "rendering_html", "label": "生成HTML", "status": "success" },
    { "key": "creating_draft", "label": "创建草稿", "status": "running" }
  ],
  "error": null
}
```

## 9. 小红书发布包 Mock

```json
{
  "packageId": "xhs_package_001",
  "title": "职业方向别乱选，先看这3个判断标准",
  "body": "很多人选职业方向的时候，最容易犯一个错误：上来就问哪个行业更热门...",
  "tags": ["职业规划", "大学生就业", "职场新人", "求职经验"],
  "commentGuide": "你现在最纠结的职业方向是什么？",
  "dmScript": "你可以先发我3个信息：专业、所在城市、目前想去的岗位。",
  "images": [
    {
      "index": 1,
      "purpose": "封面点击",
      "text": "别再盲目追热门专业",
      "url": "https://example.com/xhs-01.png",
      "prompt": "小红书干货封面图，主题是职业规划..."
    },
    {
      "index": 2,
      "purpose": "痛点共鸣",
      "text": "为什么越听建议越迷茫？",
      "url": "https://example.com/xhs-02.png",
      "prompt": "真实生活方式图片，一个年轻人在电脑前查职业建议..."
    }
  ],
  "downloadUrl": "https://example.com/xhs-package.zip",
  "status": "ready"
}
```

## 10. 短视频脚本 Mock

```json
{
  "scriptId": "video_script_001",
  "platform": "shipinhao",
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
  "teleprompterText": "很多人职业选错，不是因为不努力。\n[停顿]\n而是一开始算法就错了。",
  "status": "generated"
}
```

## 11. 朋友圈内容 Mock

```json
{
  "postId": "moments_post_001",
  "body": "这两天连续看了几个同学的职业方向，发现一个共同问题：他们不是没有努力，而是把方向判断交给了热门榜单。",
  "firstComment": "如果你也在纠结方向，可以把专业和城市发我。",
  "dmScript": "你现在的情况我先看三个信息：专业、城市、想去的行业。",
  "weeklyPlan": [
    {
      "day": "周一",
      "type": "专业观点",
      "topic": "职业选择先看门槛，不先看热度",
      "goal": "建立专业信任"
    }
  ],
  "status": "generated"
}
```

## 12. 图片任务 Mock

```json
{
  "taskId": "image_task_001",
  "status": "running",
  "progress": 60,
  "usage": "xhs_cover",
  "platform": "xiaohongshu",
  "prompt": "小红书干货封面图，主题是职业方向选择...",
  "images": [],
  "error": null
}
```

失败状态：

```json
{
  "taskId": "image_task_002",
  "status": "failed",
  "progress": 0,
  "error": {
    "code": "IMAGE_GENERATION_TIMEOUT",
    "message": "图片生成超时，请稍后重试。",
    "suggestion": "可以点击重新生成，或稍后在素材库查看结果。"
  }
}
```

## 13. 前端Mock验收标准

- 首页能展示当前IP和四平台入口。
- IP、策略、栏目、选题、母稿页面能用Mock串起流程。
- 公众号页面能展示文章、封面、同步步骤。
- 小红书页面能展示发布包图片和文案。
- 短视频页面能展示脚本、分镜、提词稿。
- 朋友圈页面能展示正文、评论、私聊话术。
- 图片任务能展示running、success、failed状态。

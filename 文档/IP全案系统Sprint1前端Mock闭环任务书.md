# IP全案系统Sprint1前端Mock闭环任务书

## 1. 文档目标

本文档用于指导前端在Sprint 1使用Mock数据跑通全案底座主流程。

目标：

```text
首页
↓
创建IP
↓
生成策略
↓
生成栏目
↓
生成选题
↓
生成母稿
↓
进入四平台入口
```

## 2. 页面范围

Sprint 1前端必须实现：

- 全案首页。
- IP资产列表页。
- IP资产详情页。
- 内容策略页。
- 栏目矩阵页。
- 选题库页。
- 内容母稿页。
- 素材上传组件。
- 四平台入口占位。

## 3. 路由

```text
/workspace
/ip-assets
/ip-assets/new
/ip-assets/:id
/strategies/:ipId
/columns/:ipId
/topics
/drafts/:topicId
/wechat
/xhs
/video
/moments
```

## 4. 通用组件

必须实现：

- GenerateButton
- EditableResultBlock
- PlatformBadge
- ErrorSuggestion
- CopyButton
- LoadingState
- EmptyState
- SaveStatus

## 5. Mock流程

### FE-S1-01 全案首页

验收：

- 展示当前IP。
- 展示四平台入口。
- 无IP时显示创建IP。
- 点击创建IP进入IP资产详情页。

### FE-S1-02 IP资产详情页

验收：

- 表单字段完整。
- 必填校验有效。
- 保存后生成Mock ipId。
- 跳转内容策略页。

### FE-S1-03 内容策略页

验收：

- 点击生成策略显示loading。
- 显示Mock策略结果。
- 策略可编辑保存。
- 点击生成栏目进入栏目页。

### FE-S1-04 栏目矩阵页

验收：

- 展示不少于6个栏目卡片。
- 栏目可编辑删除。
- 点击生成选题进入选题库。

### FE-S1-05 选题库页

验收：

- 展示选题列表。
- 支持平台和状态筛选。
- 点击选题进入内容母稿页。

### FE-S1-06 内容母稿页

验收：

- 展示选题摘要和IP上下文。
- 点击生成母稿显示loading。
- 展示Mock母稿。
- 母稿可编辑保存。
- 四个平台入口可点击。

### FE-S1-07 四平台入口占位

验收：

- 公众号入口显示“进入公众号工作台”。
- 小红书入口显示“进入小红书工作台”。
- 短视频入口显示“进入短视频工作台”。
- 朋友圈入口显示“进入朋友圈工作台”。
- Sprint 1不要求四平台完整生产能力。

## 6. 状态要求

每个生成动作必须有：

```text
未生成
生成中
生成成功
生成失败
重新生成
已保存
```

失败Mock示例：

```json
{
  "success": false,
  "code": "AI_GENERATION_FAILED",
  "message": "生成失败，请稍后重试。",
  "suggestion": "可以检查输入信息是否完整，或点击重新生成。"
}
```

## 7. Mock数据要求

使用文档：

```text
IP全案系统P0前端Mock数据样例.md
```

必须覆盖：

- 当前IP。
- 内容策略。
- 栏目。
- 选题。
- 内容母稿。
- 图片任务状态。

## 8. 与后端接口切换要求

前端Mock应保留与后端接口一致的数据结构。

建议封装：

```text
services/ipAssets
services/strategies
services/columns
services/topics
services/drafts
services/materials
```

后端接口可用后，只替换service层，不大改页面组件。

## 9. Sprint 1前端验收标准

- 创建IP到生成母稿主流程可点击完成。
- 每一步都有loading和失败状态。
- 所有生成结果可编辑保存。
- 四平台入口在母稿页可见。
- Mock数据结构与后端接口保持一致。
- 提词器入口不被改动。

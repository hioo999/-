# Plan: Production Center Platform Restructure

## 1. Background

The current Production Center does not match the platform restructure direction in `docs/重点需求.md`. It still behaves like a tool-oriented generation page focused on material extraction, short-video scripts, video prompts, and AIP workflows.

The required direction is a project-centered content production platform:

```text
IP Project -> Content Topic -> Platform Content -> Materials / Assets / Tasks / Publish Records
```

The Production Center should become the main production cockpit for an IP project and a content topic, not a single-purpose script or video generation tool.

## 2. Current Problem

The current Production Center is implemented mainly in:

- `frontend/src/views/CopilotWorkspace.vue`
- `workspaceMode === 'ip'`

Current flow:

```text
Material extraction -> Short-video workflow -> Topic strategy -> Talking script -> Video AIP -> Publish package
```

Main issues:

1. It does not use `IP Project` as the first-level production context.
2. It does not use `Content Topic` as the second-level production context.
3. Topic planning is treated as generated content, not as a persisted business entity.
4. Materials are local page input, not reusable project/topic materials.
5. Assets are scattered across tool modules instead of being a unified asset layer.
6. Tasks are scattered inside individual tools instead of being a unified task center.
7. WeChat, Xiaohongshu, Douyin/Video Channel, cinematic video, and drama video are not connected by one topic context.
8. The current page is biased toward short-video and AIP generation, while the PRD requires a multi-platform content production center.
9. `PlatformContentStudio.vue` and `WechatArticlePublisher.vue` are closer to the target architecture, but they are isolated modules rather than part of the Production Center.

## 3. Target Positioning

The Production Center should be a project-level production cockpit.

It should answer four questions at all times:

1. Which IP project is being produced?
2. Which content topic is being produced?
3. Which platform content is being generated or edited?
4. Which materials, tasks, assets, and publish records belong to this topic?

Target flow:

```text
Select/Create IP Project
-> Select/Create Content Topic
-> Add or reuse materials
-> Select target platforms
-> Generate platform content
-> Edit, format, illustrate, storyboard, or render
-> Save outputs to asset library
-> Track all actions in task center
-> Publish, export, or send to draft
-> Save publish records
```

## 4. Target Information Architecture

Recommended page structure:

```text
Production Center
  Top: production context
  Left: project/topic/material navigation
  Center: platform content production area
  Right: task/model/prompt/asset side panel
  Bottom or drawer: task logs, generation records, publish records
```

### 4.1 Top: Production Context

The top area should show and control the active production context:

- Current IP project
- Current content topic
- Topic status
- Target platforms
- Material count
- Platform content count
- Running/failed/succeeded task count
- Last saved time

Example:

```text
Li Teacher Knowledge IP / How to choose a major
Status: Ready to edit
Platforms: WeChat, Xiaohongshu, Douyin
Materials: 3
Platform contents: 2
Tasks: 1 running, 2 succeeded
```

### 4.2 Left: Project, Topic, and Material Navigation

The left side should provide the production hierarchy:

```text
IP Projects
  -> Project detail
  -> Content topics
  -> Topic materials
```

Required capabilities:

- Create IP project
- Select IP project
- Create content topic
- Select content topic
- View topic status
- View materials under the current topic
- View existing platform contents under the topic

`IP Project` is the long-term workspace. `Content Topic` is the business container for one content production cycle.

### 4.3 Center: Platform Content Production Area

The center area should be organized by platform content, not by isolated generation steps.

Recommended tabs:

```text
Topic Overview
Materials
WeChat Article
Xiaohongshu Note
Short Video Script
Cinematic Video
Drama Video
```

Each platform tab owns its own workflow but shares the same project/topic/material/task/asset context.

WeChat flow:

```text
Material/topic input
-> Select WeChat template
-> Generate structured article JSON
-> Rich-text editing
-> Generate cover and inline images
-> Send to WeChat draft box
-> Save draft record
```

Xiaohongshu flow:

```text
Material/topic input
-> Select Xiaohongshu template
-> Generate title/body/tags
-> Generate cover and multi-image assets
-> Copy or download
-> Save export record
```

Short-video flow:

```text
Material/topic input
-> Select Douyin or Video Channel
-> Generate talking script/title/description/tags
-> Generate cover
-> Import to teleprompter
-> Save short-video content
```

Cinematic video flow:

```text
Upload product/person/pet image
-> Subject cleanup
-> Multi-view image
-> Grid storyboard
-> Shot list
-> Video task
-> Save video asset
```

Drama video flow:

```text
Character library
-> Story theme
-> Script
-> Storyboard table
-> Storyboard images
-> Video task
-> Save video asset
```

### 4.4 Right: Production Side Panel

The right panel should no longer be only a generation configuration sidebar.

It should include context-aware support panels:

- Current tasks
- Current assets
- Prompt template selection
- Model selection
- Generation records
- Publish records

All AI generation, image generation, video generation, material parsing, and publishing actions should be visible here as tasks.

## 5. Domain Model

The core entities should follow the PRD structure:

```text
ip_projects
content_topics
source_materials
platform_contents
assets
generation_tasks
generation_records
wechat_draft_records
character_profiles
storyboard_records
```

### 5.1 IP Project

Long-term IP workspace.

Recommended fields:

- Project name
- IP type
- Account positioning
- Default platforms
- Default persona
- Project-level assets

### 5.2 Content Topic

A production unit under an IP project.

Recommended fields:

- Topic name
- Input source type
- Target platforms
- Current status
- Linked materials
- Linked platform contents

Status examples:

```text
draft -> generating -> ready_to_edit -> ready_to_publish -> sent/exported -> archived
```

### 5.3 Platform Content

A platform-specific editable content result.

Recommended content types:

```text
wechat_article
xiaohongshu_note
short_video_script
long_video_plan
drama_script
```

`platform_contents` should not be confused with tasks or assets. It is the editable content object for one platform.

### 5.4 Task

A task represents an executable asynchronous action.

Task types:

```text
material_parse
content_generation
image_generation
video_generation
publish
```

Task status:

```text
pending -> running -> succeeded -> failed -> cancelled -> retrying
```

Every AI generation, image generation, video generation, material parsing, and publish action should create a task.

### 5.5 Asset

An asset is a reusable persisted input or output.

Asset types:

```text
source_material
generated_text
image
video
character
storyboard
publish_record
generation_record
```

Assets should be linked by:

- `project_id`
- `topic_id`
- `platform_content_id` when applicable
- `task_id` when applicable
- `asset_type`
- `platform` when applicable
- `tags`
- `metadata`

## 6. Task Center Logic

The task center should become a unified production layer.

Example: generating a WeChat article.

```text
User clicks generate
-> Create content_generation task
-> Save prompt template/version snapshot
-> Save model/gateway/parameter snapshot
-> Call AI model
-> Save raw AI response
-> Repair/parse JSON if needed
-> Create platform_content: wechat_article
-> Create generation_record
-> Save article asset
-> Mark task succeeded
```

Example: generating a cover image.

```text
User clicks generate cover
-> Create image_generation task
-> Use image model
-> Save raw response
-> Create image asset
-> Bind asset to platform_content.cover_asset_id
-> Mark task succeeded
```

Example: sending to WeChat draft box.

```text
User clicks send draft
-> Create publish task
-> Validate cover image
-> Upload cover to WeChat
-> Upload inline images to WeChat
-> Replace HTML image URLs
-> Call draft/add
-> Create wechat_draft_record
-> Create publish asset
-> Mark task succeeded
```

## 7. Asset Library Logic

The asset library should be the shared persistence layer for all inputs and outputs.

Required capabilities:

- Filter by project
- Filter by topic
- Filter by platform
- Filter by asset type
- Reuse text/image/video/role/storyboard assets
- Tag assets
- Delete user-facing assets without deleting generation logs or publish audit records

The asset library should not be implemented as separate file lists inside each tool.

## 8. Prompt and Model Logic

Prompt templates and models should be configured in admin/system areas, then selected and used in Production Center.

Prompt hierarchy:

```text
Platform -> Scene -> Step -> Template -> Version
```

Each generation record must save:

- `prompt_template_id`
- `prompt_template_version_id`
- `template_key`
- rendered prompt snapshot
- `model_id`
- `gateway_id`
- model parameters
- model snapshot
- raw response
- parsed output

Normal users should see template names and descriptions, not full system prompt text.

## 9. WeChat First-Phase Path

The PRD requires the first phase to prioritize the WeChat official account loop.

Production Center phase 1 should prioritize this path:

```text
Create IP project
-> Create content topic
-> Input material by URL/text/topic
-> Select WeChat template
-> Generate structured WeChat article JSON
-> Enter rich-text editor
-> Generate or upload cover
-> Generate inline images
-> Send to WeChat draft box
-> Save draft record
-> Save assets and task records
```

`WechatArticlePublisher.vue` already contains many required capabilities and should be integrated as the WeChat platform production panel inside the Production Center rather than remaining only an isolated tool page.

## 10. Multi-Platform Path

Xiaohongshu, Douyin, and Video Channel do not need full automatic publishing in phase 1, but they must use the same architecture.

One topic should support multiple platform outputs:

```text
Content Topic
  -> WeChat article
  -> Xiaohongshu note
  -> Douyin talking script
  -> Video Channel talking script
  -> Covers/images
  -> Export records
```

`PlatformContentStudio.vue` is closer to the target architecture and should be reused as the base for the multi-platform production panel.

## 11. Cinematic and Drama Video Path

Cinematic video and drama video should be advanced production flows under the current topic.

Cinematic relationship:

```text
content_topic
  -> cinematic_project
    -> cinematic_steps
    -> tasks
    -> assets
```

Drama relationship:

```text
content_topic
  -> drama_project
    -> characters
    -> scripts
    -> storyboards
    -> tasks
    -> assets
```

They can keep dedicated screens later, but their outputs must return to the topic asset library.

## 12. Recommended Frontend Refactor

Do not keep expanding `CopilotWorkspace.vue`.

Recommended components:

```text
ProductionCenter.vue
ProjectTopicShell.vue
MaterialPanel.vue
PlatformContentTabs.vue
WechatProductionPanel.vue
XiaohongshuProductionPanel.vue
ShortVideoProductionPanel.vue
CinematicProductionPanel.vue
DramaProductionPanel.vue
TaskCenterPanel.vue
AssetLibraryPanel.vue
GenerationConfigPanel.vue
PublishRecordPanel.vue
```

Recommended composables:

```text
useProductionContext()
useProjects()
useTopics()
useMaterials()
usePlatformContents()
useAssets()
useTasks()
usePromptTemplates()
useModelCatalog()
```

The shared production context should be minimal:

```text
currentProjectId
currentTopicId
currentPlatform
currentContentId
```

All panels should load data around these IDs.

## 13. Recommended Backend/API Shape

Backend domains:

```text
projects
topics
materials
platform_contents
assets
tasks
generation_records
wechat
publish_configs
prompt_templates
model_pool
```

Useful endpoint groups:

```text
GET /api/production/overview
GET /api/production/context?project_id=&topic_id=
GET /api/projects
POST /api/projects
GET /api/projects/{id}/topics
POST /api/projects/{id}/topics
POST /api/materials
POST /api/materials/parse-link
GET /api/platform-contents
POST /api/generation/content
POST /api/generation/images
POST /api/generation/videos
GET /api/tasks
POST /api/tasks/{id}/retry
GET /api/assets
POST /api/wechat/drafts
```

A production context aggregate can return:

```json
{
  "project": {},
  "topic": {},
  "materials": [],
  "platform_contents": [],
  "assets": [],
  "tasks": [],
  "generation_records": [],
  "publish_records": []
}
```

## 14. Implementation Sequence

Recommended migration path:

1. Create a standalone `ProductionCenter.vue` instead of continuing to add logic to `CopilotWorkspace.vue`.
2. Add mandatory `IP Project + Content Topic` context to the Production Center top area.
3. Integrate the existing WeChat article workflow as a WeChat platform panel.
4. Integrate the existing Xiaohongshu/Douyin/Video Channel workflow as multi-platform panels.
5. Move current short-video/AIP-heavy production logic into advanced video tabs.
6. Add shared `TaskCenterPanel` and `AssetLibraryPanel` used by all platform panels.
7. Make Home and navigation point users to the new Production Center as the main production entry.
8. Keep existing specialized tool routes as compatibility shortcuts only where useful.

## 15. Navigation Recommendation

Current labels are misleading because `Production Center` is not yet the platform production center and `Publish Tools` contains production capabilities.

Recommended first-stage navigation:

```text
Home
Production Center
Asset Library
Task Center
System Settings
```

Optional shortcuts:

```text
WeChat Formatter
Teleprompter
```

These shortcuts should still use the same project/topic/content/asset/task data model.

## 16. Final Architecture Summary

The Production Center should move from:

```text
Material input -> Script generation -> Video prompts -> Publish package
```

To:

```text
IP Project -> Content Topic -> Material Center -> Platform Content Production -> Task Center -> Asset Library -> Publish Records
```

The existing `WechatArticlePublisher.vue` and `PlatformContentStudio.vue` are closer to this direction than the current `CopilotWorkspace.vue` Production Center. The refactor should turn the current Production Center into a unified production shell and move platform-specific workflows inside that shell.

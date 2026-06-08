# PRD: 短剧脚本工坊 Phase 1 — 模板化与角色组解耦

## 1. 功能名称

短剧脚本工坊 Phase 1（剧情反转模块通用化改造第一期）。

将现有「职场反转剧」从硬编码 Prompt 升级为可配置的三层结构：**剧本类型模板 + 角色组 Cast + 本集变量**，在保留现有生成、自检、合规、历史、Copilot 能力的前提下，支持更多 IP 场景复用。

## 2. 需求背景

当前剧情反转模块（`ReversalDramaPanel` + `reversal_drama_prompts.py`）能力完整，但存在以下结构性限制：

- System Prompt 硬编码「农总 + 淇淇 + 海鸥」铁三角、职场 B 端 AI 产品场景、起承转合结构与 A/B/C 反转套路。
- 前端自定义人物为每次手填，与 IP 项目内的 `CharacterProfile` 角色资产未打通。
- Copilot 改稿未注入 IP 人设（`persona_id` 固定为 0）。
- 模板变更需改代码，无法通过提示词管理后台运营。

用户希望模块更智能化、更通用：角色设定、模板、剧本套路、脚本结构均可自由配置，同时日常使用时仍保持「填产品痛点 → 一键生成」的简洁体验。

## 3. 目标用户

| 用户 | 场景 |
|---|---|
| 企业 IP 运营 | 用固定角色组批量产出产品推广短剧 |
| 短视频编导 | 切换不同剧本类型与反转套路，快速试结构 |
| 多 IP 团队 | 不同项目使用不同角色组，不重复录入 |
| 管理员 | 在提示词管理中维护剧本类型模板，无需发版 |

## 4. 核心目标

Phase 1 只做「解耦硬编码 + 角色组 + 模板选择」，不做系列续集、结构仿写、分镜级局部重写（留 Phase 2/3）。

用户进入页面后：

1. 默认仍是「职场反转 · 铁三角」，老用户无感。
2. 可切换剧本类型、指定反转套路、从 IP 项目或临时角色组载入人物。
3. 生成结果格式不变（概览 / 分镜表 / 结尾字幕 / 自检清单），历史与 Copilot 继续可用。

## 5. Phase 1 范围边界

### 5.1 本期做

| 能力 | 说明 |
|---|---|
| 剧本类型选择 | 内置 3 种：职场反转（默认）、产品种草短剧、自定义模板 |
| 反转套路选择 | A 打脸老板 / B 反讽 AI / C 细节杀 / 自动选择 |
| 角色组 Cast | 从 IP 项目选角色；保存为命名角色组预设；支持临时角色组（不绑项目） |
| 角色剧情功能 | 每人可选：施压者、缓冲者、反转承载者、产品引出者、其他 |
| Prompt 分层注入 | 类型模板 + 角色块 + 结构/套路块 + 用户变量，替换整段硬编码 SYSTEM |
| 历史记录扩展 | 保存 `template_key`、`cast_snapshot`、`reversal_pattern` |
| Copilot 上下文 | 改稿时带上当前模板名与角色组摘要 |

### 5.2 本期不做

- 从历史脚本「结构仿写」
- 系列 / 续集管理
- 分镜级点击修改（只保留现有整篇 Copilot）
- 提示词管理 UI 完整 CRUD（可先内置 3 模板 + 后端 seed，Phase 2 接 PromptAdmin）
- 一键送提词器 / 视频 AIP（已有其他 PRD 覆盖，本期仅预留 `history_id`）

## 6. 第一版剧本类型（已确认：3 种）

| key | 名称 | 定位 | 默认角色组 |
|---|---|---|---|
| `workplace_reversal` | 职场反转 | 现有逻辑迁移；B 端 AI 产品 + 办公室 + 铁三角关系 | 农总 + 淇淇 + 海鸥 |
| `product_seed` | 产品种草短剧 | 更短、更面向 C 端；门店/直播间/生活场景；2–3 人即可 | 博主 + 闺蜜 / 店员 + 顾客（内置预设） |
| `custom` | 自定义模板 | 管理员或高级用户配置的空白结构；仅约束输出格式 | 用户自选角色组 |

**角色绑定策略（默认方案）**：**双模式并存**

- **IP 项目模式**：从当前 IP 项目的 `CharacterProfile` 多选 2–6 人组成 Cast。
- **临时角色组**：不建项目也可保存命名预设（存用户级 `drama_cast_presets`），适合试稿或跨项目复用。

二者可互相「另存为」：临时组可升级为项目角色，项目角色可导出为预设。

## 7. 用户故事

1. 作为运营，我希望默认打开仍是职场反转，不用重新学习。
2. 作为编导，我希望切换「产品种草」并选「套路 B」，同一产品试不同结构。
3. 作为 IP 负责人，我希望从项目角色库勾选 3 人，不用每次手填性格口头禅。
4. 作为管理员，我希望改模板文案走配置而不是改 Python 文件（Phase 1 可先 seed，Phase 2 接管理台）。

## 8. 主流程

```text
进入剧情反转 / 短剧脚本工坊
-> 选择剧本类型（默认 workplace_reversal）
-> 选择或创建角色组（默认铁三角 / 从 IP 项目选 / 临时预设）
-> 选择反转套路（A/B/C/自动）
-> 填写本集变量（产品、痛点、平台、时长、额外要求）
-> 生成脚本
-> Copilot 迭代 / 复制 / 查看合规与自检
-> 历史恢复（含模板与角色组快照）
```

## 9. 页面与交互

### 9.1 表单区改造（`ReversalDramaPanel`）

在现有「产品 / 痛点」之上增加配置区（可折叠，默认收起仅显示类型与套路）：

| 控件 | 类型 | 默认 |
|---|---|---|
| 剧本类型 | 下拉 | 职场反转 |
| 反转套路 | 单选 + 自动 | 自动 |
| 角色来源 | 单选：默认铁三角 / IP 项目 / 临时预设 / 手填 | 默认铁三角 |
| IP 项目 | 下拉（角色来源=IP 项目时） | 当前 workspace 项目 |
| 角色多选 | -checkbox 列表 | — |
| 角色组预设 | 下拉 + 保存按钮 | — |
| 剧情功能 | 每人一行下拉 | 按模板推荐默认值 |

「手填」保留现有 `useCustomCharacters` 卡片 UI，作为兜底。

### 9.2 生成结果区

- 概览增加展示：`剧本类型`、`反转套路`、`角色组名称`。
- 其余分镜表、合规、自检不变。

### 9.3 历史记录

- 列表项增加类型标签（如「职场反转 · A」）。
- 恢复时一并还原模板、套路、角色组快照。

## 10. 数据模型

### 10.1 新增 `drama_cast_presets`（用户级角色组预设）

| 字段 | 说明 |
|---|---|
| id | 主键 |
| user_id | 所属用户 |
| name | 预设名，如「铁三角」「医美二人组」 |
| project_id | 可选；0 表示纯临时 |
| characters_json | 角色数组快照（含 drama_role） |
| is_default | 是否该用户默认 Cast |
| created_at / updated_at | 时间 |

### 10.2 扩展 `reversal_drama_history.params_json`

新增字段：

| 字段 | 说明 |
|---|---|
| template_key | 剧本类型 key |
| reversal_pattern | `auto` / `A` / `B` / `C` |
| cast_preset_id | 可选 |
| cast_snapshot | 生成时角色组完整快照 |

### 10.3 剧本类型模板存储（Phase 1）

**方案 A（推荐）**：新增表 `drama_script_templates`，结构与 Prompt 模板类似但专用于短剧：

| 字段 | 说明 |
|---|---|
| key | 唯一标识 |
| name | 显示名 |
| genre_prompt | 类型与场景定位 |
| structure_prompt | 结构与节奏规则 |
| reversal_patterns_json | 套路库文案 |
| style_prompt | 视觉、台词、推销纪律 |
| output_format_prompt | 固定四段输出格式 |
| default_cast_json | 默认角色组 |
| is_active / sort_order | 管理 |

Phase 1 用 migration seed 写入 3 条内置模板；Phase 2 对接 `PromptAdminPanel` 只读引用或合并分类。

## 11. API 变更

### 11.1 `POST /api/copilot/reversal-drama/generate`

请求体扩展：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| template_key | string | 否 | 默认 `workplace_reversal` |
| reversal_pattern | string | 否 | `auto` / `A` / `B` / `C` |
| cast_preset_id | number | 否 | 角色组预设 ID |
| characters | array | 否 | 与现有一致；含可选 `drama_role` |
| product_name 等 | — | 是 | 保持不变 |

生成逻辑：

1. 按 `template_key` 加载模板各段 Prompt。
2. `build_characters_block()` 升级为 `build_cast_block()`，注入剧情功能与关系说明。
3. `reversal_pattern=auto` 时在 user 消息中要求模型自选 A/B/C 并标注。
4. 解析与历史保存逻辑不变。

### 11.2 新增 Cast 预设 CRUD

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/copilot/drama-casts` | 列表 |
| POST | `/api/copilot/drama-casts` | 创建 |
| PUT | `/api/copilot/drama-casts/{id}` | 更新 |
| DELETE | `/api/copilot/drama-casts/{id}` | 删除 |

### 11.3 新增模板列表（只读）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/copilot/drama-templates` | 返回可用剧本类型（name、key、description、default_cast） |

### 11.4 Copilot modify

`POST /api/copilot/modify/stream` 在 `content_type=reversal_drama` 时，请求体可选传 `template_key` 与 `cast_summary`，注入 system 附加上下文。

## 12. Prompt 组装规则

```text
SYSTEM =
  [genre_prompt from template]
  + [cast_block from preset/characters]
  + [structure_prompt from template]
  + [reversal_patterns: 指定套路或三选一说明]
  + [style_prompt from template]
  + [output_format_prompt from template]

USER =
  产品 / 痛点 / 平台 / 时长 / 额外要求（与现有一致）
```

**铁三角迁移**：现有 `REVERSAL_DRAMA_SYSTEM` 全文拆入 `workplace_reversal` 模板各字段，行为对齐现网，作为回归基线。

## 13. 验收标准

| # | 标准 |
|---|---|
| AC-1 | 不选任何新选项时，生成结果与现网职场反转质量同级（铁三角、A/B/C、四段输出） |
| AC-2 | 切换「产品种草短剧」后，场景与台词风格明显变化，仍输出合法分镜表 |
| AC-3 | 从 IP 项目选 3 个角色生成，剧本出场人物与选定角色一致 |
| AC-4 | 保存角色组预设后，下次一键载入 |
| AC-5 | 指定「套路 A」时，概览中 `reversal_type` 含 A |
| AC-6 | 历史恢复还原 template、套路、角色 |
| AC-7 | 游客仍不可生成；登录用户历史含新字段 |
| AC-8 | 现有 Copilot 改稿、复制、合规检查不回归 |

## 14. 风险与对策

| 风险 | 对策 |
|---|---|
| 模板拆分后质量波动 | 职场反转模板逐段对照旧 Prompt 做 diff 回归 |
| 自定义模板过于自由导致输出不可解析 | `custom` 仍强制 `output_format_prompt`；解析失败时保留 raw_markdown |
| 角色过多导致 token 超限 | Cast 上限 6 人，与 `CharacterProfile` 一致 |
| 与 PromptAdmin 重复建设 | Phase 1 独立 `drama_script_templates`；Phase 2 再合并或双向同步 |

## 15. 实施阶段

| 阶段 | 内容 | 优先级 |
|---|---|---|
| P1-A | 后端模板表 seed + Prompt 组装 + API 扩展 | P0 |
| P1-B | Cast 预设 CRUD + `build_cast_block` | P0 |
| P1-C | 前端配置区 + IP 项目角色选择 | P0 |
| P1-D | 历史字段扩展 + 恢复 | P1 |
| P1-E | Copilot 上下文 + 测试 | P1 |

## 16. 后续 Phase 2/3（备忘）

- Phase 2：PromptAdmin 接入、模板填空、历史结构仿写
- Phase 3：系列续集、智能推荐套路、一键送提词器/视频 AIP

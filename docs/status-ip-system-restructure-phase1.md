# 状态记录：IP 系统重构第一阶段执行进展

## 1. 本次已完成

### 1.1 后端平台底座

已新增正式平台化数据模型：

| 模型 | 状态 | 说明 |
|---|---|---|
| `IpProject` | 已完成 | 承载 `IP 项目` |
| `ContentTopic` | 已完成 | 承载项目下的内容选题 |
| `SourceMaterial` | 已完成 | 承接链接、粘贴原文、主题输入 |
| `PlatformContent` | 已完成 | 承载公众号文章等平台内容主表 |
| `UnifiedAsset` | 已完成 | 统一资产库最小实现 |
| `GenerationTask` | 已完成 | 统一任务中心最小实现 |
| `GenerationRecord` | 已完成 | 保存提示词、模型、原始 AI 返回和解析结果 |

已新增平台化 API：

| 接口 | 状态 | 说明 |
|---|---|---|
| `GET /api/projects` | 已完成 | 查询当前用户 IP 项目 |
| `POST /api/projects` | 已完成 | 创建 IP 项目 |
| `GET /api/projects/{id}/topics` | 已完成 | 查询项目内容选题 |
| `POST /api/projects/{id}/topics` | 已完成 | 创建内容选题 |
| `GET /api/platform-workspace/overview` | 已完成 | 查询多平台工作台总览、关键指标、最近内容、最近任务和保留策略 |
| `GET /api/platform-contents/{id}` | 已完成 | 获取任意平台内容详情，支持小红书和口播内容工作台复用 |
| `PUT /api/platform-contents/{id}` | 已完成 | 保存任意平台内容编辑结果 |
| `GET /api/platform-contents/{id}/export` | 已完成 | 导出小红书/口播复制包和图片清单 |
| `POST /api/platform-contents/{id}/image-assets` | 已完成 | 绑定公网图片 URL 到平台内容和统一资产库 |
| `POST /api/platform-contents/{id}/image-upload` | 已完成 | 上传本地图片文件到受控目录并入统一资产库 |
| `POST /api/platform-contents/{id}/image-slots/{index}/generate` | 已完成 | 为任意平台内容图片位提交图片生成任务 |
| `GET /api/assets/{id}/file` | 已完成 | 受登录态保护下载本地上传的统一资产文件 |
| `POST /api/wechat/articles/generate` | 已完成 | 三种输入生成结构化公众号文章 |
| `POST /api/xiaohongshu/notes` | 已完成 | 生成小红书图文笔记并进入平台内容、资产、任务和生成记录 |
| `POST /api/short-video/scripts` | 已完成 | 生成抖音/视频号口播脚本并进入平台内容、资产、任务和生成记录 |
| `GET /api/wechat/articles/{id}` | 已完成 | 获取公众号文章 |
| `PUT /api/wechat/articles/{id}` | 已完成 | 保存公众号文章编辑结果 |
| `DELETE /api/platform-contents/{id}` | 已完成 | 软删除平台内容，关联资产从工作台隐藏，任务和生成记录保留 |
| `GET /api/platform-publish-configs` | 已完成 | 查询小红书/抖音/视频号发布配置预留项 |
| `POST /api/platform-publish-configs` | 已完成 | 保存平台发布配置预留项，密钥加密且不回显明文 |
| `PUT /api/platform-publish-configs/{id}` | 已完成 | 更新平台发布配置预留项 |
| `DELETE /api/platform-publish-configs/{id}` | 已完成 | 软删除平台发布配置预留项 |
| `GET /api/characters` | 已完成 | 查询项目人物角色库 |
| `POST /api/characters` | 已完成 | 创建人物角色，第一版单项目最多 6 个 |
| `PUT /api/characters/{id}` | 已完成 | 更新人物角色 |
| `DELETE /api/characters/{id}` | 已完成 | 软删除人物角色 |
| `GET /api/storyboards` | 已完成 | 查询项目/选题/平台内容下的分镜记录 |
| `POST /api/storyboards` | 已完成 | 创建分镜记录 |
| `PUT /api/storyboards/{id}` | 已完成 | 更新分镜记录 |
| `DELETE /api/storyboards/{id}` | 已完成 | 软删除分镜记录 |
| `GET /api/tasks` | 已完成 | 查询统一任务 |
| `GET /api/tasks/{id}` | 已完成 | 获取统一任务详情 |
| `POST /api/tasks/{id}/retry` | 已完成 | 支持公众号文章生成、公众号封面图生成、正文图片生成和草稿发送失败任务重试 |
| `GET /api/assets` | 已完成 | 查询统一资产 |
| `POST /api/assets` | 已完成 | 手动创建统一资产，图片资产校验公网 URL |
| `GET /api/assets/{id}` | 已完成 | 获取统一资产详情 |
| `DELETE /api/assets/{id}` | 已完成 | 软删除统一资产 |
| `POST /api/assets/{id}/reuse` | 已完成 | 复用图片资产到公众号封面图或正文图片位 |
| `POST /api/wechat/articles/{id}/cover/generate` | 已完成 | 提交封面图生成任务并绑定封面资产 |
| `POST /api/wechat/articles/{id}/cover` | 已完成 | 设置公网封面图 URL 或图片资产为文章封面 |
| `POST /api/wechat/articles/{id}/image-slots/{index}/generate` | 已完成 | 提交正文图片生成任务并绑定资产 |
| `POST /api/wechat/articles/{id}/image-slots/{index}/insert` | 已完成 | 插入公网图片 URL 或绑定资产到正文图片位 |
| `DELETE /api/wechat/articles/{id}/image-slots/{index}/asset` | 已完成 | 移除正文图片位资产绑定 |

### 1.2 公众号内容生成

已实现：

1. 支持主题、链接、粘贴原文三种输入。
2. 自动创建或复用 IP 项目。
3. 自动创建内容选题。
4. 输入内容进入素材中心。
5. 生成结构化公众号文章。
6. 保存 `PlatformContent`、`UnifiedAsset`、`GenerationTask`、`GenerationRecord`。
7. AI 调用失败或未配置时提供 fallback 初稿，避免闭环中断。
8. 保存原始 AI 返回、模板快照、模型快照和解析结果。

结构化输出字段已覆盖：

1. `title`
2. `subtitle`
3. `author`
4. `summary`
5. `cover_prompt`
6. `content_html_or_delta`
7. `markdown_snapshot`
8. `image_slots`
9. `tags`
10. `compliance_risks`

### 1.3 提示词模板

已新增公众号模板种子：

| 模板 | 类型 | 说明 |
|---|---|---|
| `wechat_article_rewrite` | 分类 | 公众号二创文章分类 |
| `wechat_deep_rewrite_json` | 模板 | 生成公众号文章 JSON 结构 |

模板要求 AI 输出 JSON，并包含封面提示词、插图建议和合规风险字段。

IP 全案工作台统一生成配置侧栏已完成第一版收口：

1. 支持 `text_script`、`image_cover`、`image_character`、`video_clip` 多类型模板。
2. 生成接口可携带口播、封面、视频模板和文本/图片/视频模型配置。
3. 生成历史保存模板 ID、模板版本、模型配置和参数快照。
4. 模板正文生成时注入 AI 消息，但普通生成响应和历史快照不暴露完整后台提示词正文。
5. 模板管理页展示生成次数、编辑率、定稿率、提词转化率和最近生成时间。
6. Copilot 改稿、导出/保存、发送提词器会写入生成后行为事件，用于模板质量复盘。
7. 模板创建/更新已接入风险扫描，阻断疑似密钥、越狱、泄露系统提示词、绕过安全策略等高风险内容。

### 1.4 公众号账号权限

已调整公众号账号策略：

1. 第一版账号由管理员配置。
2. 普通用户只读取启用且授权的公众号账号。
3. 普通用户不能新增、编辑、删除、测试公众号账号。
4. 账号支持 `scope` 和 `authorized_user_ids_json` 预留字段。
5. 旧用户自有账号仍保留兼容可见性。

### 1.5 草稿发送链路

已增强：

1. `WechatDraftPayload` 支持 `platformContentId`。
2. 草稿发送可关联 `PlatformContent`。
3. 草稿记录补充项目、选题、平台内容、任务、主题、封面资产、AI 图片和 preflight 结果字段。
4. 发送成功后会把平台内容状态更新为 `sent_to_draft`。
5. 幂等和 90 秒重复检测纳入 `platformContentId`。
6. 草稿发送尝试会创建 `wechat_draft_send` 统一任务。
7. 草稿发送成功或失败会同步更新统一任务状态、错误码和输出快照。
8. 草稿发送失败任务可通过统一任务重试，重试会生成新的幂等 key，避免命中旧失败记录。

### 1.6 前端公众号内容工作台

已在 `WechatArticlePublisher.vue` 中新增公众号内容工作台：

1. 选择或自动创建 IP 项目。
2. 支持主题、链接、粘贴原文三种输入。
3. 选择公众号提示词模板。
4. 选择文本模型。
5. 生成结构化公众号文章。
6. 生成结果自动带入排版编辑区。
7. 支持保存当前文章到平台内容主表。
8. 展示最近统一任务和统一资产。
9. 最近失败任务可触发重试。
10. 支持手动添加公网图片 URL 到统一资产库。
11. 最近图片资产可复用到正文图片位或设为封面，也可软删除。
12. 封面图支持生成图片、设置公网 URL 和复用图片资产。
13. 正文图片位支持生成图片、插入 URL 和移除绑定。
14. 封面图和正文图片生成任务提交后自动轮询统一任务，完成后刷新文章、资产和预览。
15. 草稿发送失败任务可从最近任务列表重试，重试后刷新草稿记录。
16. 普通用户隐藏公众号账号配置表单，只允许选择账号。
17. 管理员保留账号新增、编辑、删除、测试连接能力。

### 1.7 多平台内容工作台与保留策略

已新增多平台内容工作台入口：

1. 首页快捷入口和顶部导航新增“多平台”。
2. 多平台页接入 `PlatformContentStudio.vue`，支持小红书图文、抖音口播和视频号口播创作。
3. 支持选择/自动创建 IP 项目和内容选题。
4. 支持主题、链接、粘贴原文三种输入方式。
5. 支持选择平台提示词模板、文本模型和图片模型。
6. 支持生成后编辑标题、摘要、标签、封面提示词和正文复制内容。
7. 支持复制/导出平台内容，第一版提供复制文本和图片清单，不自动发布。
8. 支持将抖音/视频号口播稿导入在线提词器。
9. 支持生成、上传或绑定小红书/口播配图，图片进入统一资产库。
10. 支持查看最近平台内容、统一任务、资产列表。
11. 支持保存小红书/抖音/视频号发布配置预留项，密钥加密保存且不回显明文。
12. 支持项目内人物角色库，第一版单项目最多 6 个角色。
13. 支持从当前文案拆出基础分镜并保存分镜记录。
14. 支持平台内容软删除：内容从工作台隐藏，关联资产软删除，统一任务和生成记录继续保留。

## 2. 已验证

| 验证项 | 结果 |
|---|---|
| 后端变更文件语法编译 | 通过 |
| 前端生产构建 `npm run build` | 通过 |
| 前端提示词工具单测 `npm run test:prompt` | 通过 |
| 提示词管理页 Playwright Chromium 冒烟 | 通过，管理员可进入提示词管理页并创建分类/模板 |
| IP 全案工作台模板追踪、指标与风控回归 | 通过，`test_sprint_foundation_api.py` + `test_security_static_scan.py` 共 12 passed |
| 新增平台化后端测试 | 通过，21 passed |
| 现有后端回归测试 | 通过，25 passed |

执行过的命令：

```bash
python -m py_compile "backend/api/platform_routes.py" "backend/tests/test_platform_assets_tasks_api.py"
npm run build
"/var/folders/6y/q47lh4h52gv4925m5fzw2yf40000gn/T/kilo/ip-system-test-venv/bin/python" -m pytest backend/tests/test_platform_assets_tasks_api.py
"/var/folders/6y/q47lh4h52gv4925m5fzw2yf40000gn/T/kilo/ip-system-test-venv/bin/python" -m pytest backend/tests/test_wechat_security.py
"/var/folders/6y/q47lh4h52gv4925m5fzw2yf40000gn/T/kilo/ip-system-test-venv/bin/python" -m pytest backend/tests/test_sprint_foundation_api.py
"/var/folders/6y/q47lh4h52gv4925m5fzw2yf40000gn/T/kilo/ip-system-test-venv/bin/python" -m pytest backend/tests/test_compliance_samples.py
"/var/folders/6y/q47lh4h52gv4925m5fzw2yf40000gn/T/kilo/ip-system-test-venv/bin/python" -m pytest backend/tests/test_security_static_scan.py
```

## 3. 仍未完成

### 3.1 后端工程化

| 工作项 | 状态 | 说明 |
|---|---|---|
| Alembic 正式迁移 | 部分完成 | 已引入 `backend/alembic/` 基线 revision、`scripts/db-upgrade.sh` 与 `ALEMBIC_UPGRADE_ON_START`；增量 revision 待替代补列逻辑 |
| 任务异步执行 | 未完成 | 目前任务为同步执行并记录状态 |
| `/api/tasks/{id}/retry` | 部分完成 | 已支持公众号文章生成、封面图生成、正文图片生成和草稿发送失败任务重试，其他任务类型待扩展 |
| 资产创建/删除/复用接口 | 部分完成 | 已支持手动创建图片资产、统一资产详情、软删除、图片资产复用到公众号封面和图片位；平台内容删除会同步隐藏关联资产并保留日志 |
| 图片生成真实模型调用 | 部分完成 | 封面图和正文插图可提交 Pixelle 图片任务 |
| 图片资产上传入库 | 部分完成 | 图片生成结果和手动公网 URL 可入统一资产库，文件上传存储待补 |

### 3.2 公众号编辑器

| 工作项 | 状态 | 说明 |
|---|---|---|
| 真正富文本编辑器 | 部分完成 | 当前仍以 Markdown textarea + HTML 预览为主，新增了平台工作台 |
| 正文当前位置一键生成图片 | 部分完成 | image_slots 支持生成图片、插入 URL 和资产复用；真正富文本光标插入待补 |
| AI 封面图生成 | 部分完成 | 已接入 Pixelle 图片任务和统一资产库；真正富文本封面管理待增强 |
| 图片插入状态角标 | 未完成 | 需在编辑器内显示本地/已上传/失败状态 |

### 3.3 安全与合规

| 工作项 | 状态 | 说明 |
|---|---|---|
| 提示词注入测试集 | 已完成 | 已覆盖公众号文章生成提示词，验证外部素材只进入用户消息，系统消息明确禁止把外部素材指令当系统指令 |
| 内容合规强门禁 | 已完成 | preflight 和草稿发送接口已阻断绝对化、医疗功效、金融收益和无风险承诺等高风险表达；更细行业规则待补 |
| 管理员审计日志覆盖公众号账号 | 已完成 | 公众号账号创建、更新、删除、测试连接已写入 `AdminOperationLog` |
| SSRF 覆盖链接解析 | 已完成 | 微信图片 URL、统一图片资产、封面图、正文插图 URL、链接解析 URL 与重定向目标已复用公网地址校验，并补充接口级私网/云元数据地址回归；更多平台域名白名单策略待加强 |

### 3.4 产品后续模块

| 模块 | 状态 |
|---|---|
| 小红书内容生成和图片导出 | 部分完成：已支持图文笔记生成、编辑、复制导出、配图资产和发布配置预留；ZIP 包会尝试下载公网图片进 `images/`，失败项写入 `remote-images.json` |
| 抖音/视频号口播独立页面 | 部分完成：已支持口播脚本生成、编辑、复制导出、导入提词器和发布配置预留 |
| 短大片产品流程页面 | 未开始 |
| 剧本短视频基础角色库 | 部分完成：已支持项目内人物角色库和基础分镜记录，完整剧本短视频闭环待补 |
| 小红书/抖音/视频号后台发布配置口 | 部分完成：已支持预留配置 CRUD 和密钥加密保存，自动发布待补 |

## 4. 下一步建议

1. 新增 Alembic 增量 revision，逐步替代 `database.py` 补列逻辑。
2. 将公众号编辑器从 Markdown textarea 升级为真正富文本编辑器。
3. 扩展 ZIP 下载失败重试与更多平台图片位覆盖。
4. 扩展通用任务重试到更多任务类型，并补跨平台任务轮询 UI。
5. 将短大片和剧本短视频从角色/分镜基础库扩展到完整生成链路。
6. 继续扩展行业合规规则、更多平台域名白名单策略和富文本编辑器安全回归。

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  createUnifiedAsset,
  deleteUnifiedAsset,
  listUnifiedAssets,
  reuseUnifiedAsset,
} from '../api/assets.api'
import {
  getUnifiedTask,
  listGenerationRecords,
  listUnifiedTasks,
  retryUnifiedTask,
  type GenerationRecordData,
} from '../api/tasks.api'
import { listModelCatalog, type AIModelConfigData } from '../api/modelConfig.api'
import {
  createContentTopic,
  createIpProject,
  generateWechatArticle,
  generateWechatArticleCover,
  generateWechatArticleSlotImage,
  getWechatArticle,
  insertWechatArticleSlotImage,
  listIpProjects,
  listPlatformContents,
  listProjectTopics,
  removeWechatArticleSlotAsset,
  setWechatArticleCover,
  updateWechatArticle,
  uploadPlatformContentImageAsset,
  type ContentTopicData,
  type IpProjectData,
  type PlatformContentData,
} from '../api/platformContent.api'
import { listPromptTemplates, type PromptTemplateData } from '../api/promptTemplates.api'
import {
  createWechatAccount,
  deleteWechatAccount,
  listWechatAccounts,
  listWechatDrafts,
  listWechatThemes,
  preflightWechatDraft,
  previewWechatFormat,
  sendWechatDraft,
  testWechatAccount,
  updateWechatAccount,
  type WechatAccount,
  type WechatDraftRecord,
} from '../api/wechat.api'

const props = defineProps<{
  initialTitle?: string
  initialContent?: string
  initialInputMode?: 'topic' | 'url' | 'text'
  initialSourceUrl?: string
  initialProjectId?: number
  initialTopicId?: number
  sourceType?: string
  sourceId?: string
  currentUser?: { name?: string; email?: string; is_admin?: boolean; isGuest?: boolean }
}>()

const styleOptions = [
  { value: 'knowledge', label: '知识干货' },
  { value: 'ip', label: '个人 IP' },
  { value: 'business', label: '商业分析' },
  { value: 'emotion', label: '情绪共鸣' },
  { value: 'minimal', label: '极简白底' },
]

const title = ref(props.initialTitle || '未命名公众号文章')
const author = ref('')
const digest = ref('')
const rawContent = ref(props.initialContent || '# 公众号文章标题\n\n请输入或粘贴二创后的文章内容。')
const coverUrl = ref('')
const contentSourceUrl = ref('')
const style = ref('knowledge')
const selectedAccountId = ref(0)
const formattedHtml = ref('')
const preflightResult = ref<{ canSend: boolean; issues: Array<{ level: string; code: string; message: string; suggestion: string }>; imageCount: number; selectedCoverUrl: string } | null>(null)
const feedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const isLoading = ref(false)
const isSending = ref(false)
const accounts = ref<WechatAccount[]>([])
const drafts = ref<WechatDraftRecord[]>([])
const themes = ref<Array<{ id: string; name: string }>>([])
const projects = ref<IpProjectData[]>([])
const topics = ref<ContentTopicData[]>([])
const recentContents = ref<PlatformContentData[]>([])
const generationRecords = ref<GenerationRecordData[]>([])
const promptTemplates = ref<PromptTemplateData[]>([])
const textModels = ref<AIModelConfigData[]>([])
const imageModels = ref<AIModelConfigData[]>([])
const unifiedTasks = ref<any[]>([])
const unifiedAssets = ref<any[]>([])
const selectedProjectId = ref(props.initialProjectId || 0)
const selectedTopicId = ref(props.initialTopicId || 0)
const selectedExistingContentId = ref(0)
const selectedPromptTemplateId = ref(0)
const selectedTextModelId = ref(0)
const selectedImageModelId = ref(0)
const platformContentId = ref(0)
const articleInputMode = ref<'topic' | 'url' | 'text'>(props.initialInputMode || 'topic')
const articleTheme = ref(props.initialInputMode === 'topic' ? props.initialContent || props.initialTitle || '' : props.initialTitle || '')
const articleUrl = ref(props.initialInputMode === 'url' ? props.initialSourceUrl || props.initialContent || '' : '')
const articleSourceText = ref(props.initialInputMode === 'text' ? props.initialContent || '' : '')
const articleExtraRequirements = ref('')
const projectForm = reactive({
  name: '默认 IP 项目',
  ipType: 'personal_ip',
  positioning: '',
  targetAudience: '',
  defaultPlatforms: ['wechat'],
  voiceStyle: {},
})
const generatedArticle = ref<PlatformContentData | null>(null)
const isArticleGenerating = ref(false)
const activeSlotIndex = ref(-1)
const activeTaskId = ref(0)
const activeAssetId = ref(0)
const isCoverGenerating = ref(false)
const pollingTaskIds = ref<number[]>([])
const markdownTextarea = ref<HTMLTextAreaElement | null>(null)
const editorMode = ref<'source' | 'blocks'>('source')

interface ContentBlock {
  id: string
  title: string
  body: string
}

const contentBlocks = ref<ContentBlock[]>([])

const imageSlotSummary = computed(() => {
  const slots = generatedArticle.value?.imageSlots || []
  if (!slots.length) return null
  const ready = slots.filter((slot) => Boolean(slot.imageUrl || slot.assetId)).length
  const failed = slots.filter((slot) => slot.status === 'failed').length
  return { total: slots.length, ready, failed, pending: slots.length - ready - failed }
})

function parseContentBlocks(markdown: string): ContentBlock[] {
  const lines = markdown.split('\n')
  const blocks: ContentBlock[] = []
  let currentTitle = '开篇'
  let currentBody: string[] = []

  const flush = () => {
    blocks.push({
      id: `block-${blocks.length}`,
      title: currentTitle,
      body: currentBody.join('\n').trim(),
    })
    currentBody = []
  }

  for (const line of lines) {
    const heading = line.match(/^##\s+(.+)$/)
    if (heading) {
      if (currentBody.length || blocks.length) flush()
      currentTitle = heading[1].trim() || `段落 ${blocks.length + 1}`
      continue
    }
    currentBody.push(line)
  }
  flush()
  return blocks.filter((block) => block.title || block.body)
}

function syncBlocksFromMarkdown() {
  contentBlocks.value = parseContentBlocks(rawContent.value)
}

function applyBlocksToMarkdown() {
  rawContent.value = contentBlocks.value
    .map((block) => `## ${block.title || '段落'}\n\n${block.body}`.trim())
    .filter(Boolean)
    .join('\n\n')
}

function switchEditorMode(mode: 'source' | 'blocks') {
  if (mode === editorMode.value) return
  if (mode === 'blocks') syncBlocksFromMarkdown()
  else applyBlocksToMarkdown()
  editorMode.value = mode
}

function addContentBlock() {
  contentBlocks.value.push({
    id: `block-${Date.now()}`,
    title: `新段落 ${contentBlocks.value.length + 1}`,
    body: '',
  })
}

function removeContentBlock(blockId: string) {
  contentBlocks.value = contentBlocks.value.filter((block) => block.id !== blockId)
  applyBlocksToMarkdown()
}

function ensureMarkdownSynced() {
  if (editorMode.value === 'blocks') applyBlocksToMarkdown()
}

const accountForm = reactive({
  accountId: 0,
  name: '',
  appId: '',
  appSecret: '',
  originalId: '',
  feishuAccount: '',
  themeId: '',
  apiBase: 'https://feishu2weixin.maolai.cc',
  defaultCoverUrl: '',
  notes: '',
  isDefault: false,
  isActive: true,
})

const selectedAccount = computed(() => accounts.value.find((item) => item.accountId === selectedAccountId.value))
const canSend = computed(() => Boolean(selectedAccountId.value && title.value.trim() && rawContent.value.trim() && !isSending.value))
const previewSrcdoc = computed(() => `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;padding:0;background:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}img{max-width:100%;height:auto;}</style></head><body>${formattedHtml.value}</body></html>`)
const isAdminUser = computed(() => Boolean(props.currentUser?.is_admin))
const articleGenerateDisabledReason = computed(() => {
  if (isArticleGenerating.value) return '正在生成公众号文章。'
  if (articleInputMode.value === 'topic' && !articleTheme.value.trim()) return '请先输入公众号主题。'
  if (articleInputMode.value === 'url' && !articleUrl.value.trim()) return '请先粘贴文章链接。'
  if (articleInputMode.value === 'text' && !articleSourceText.value.trim()) return '请先粘贴原文内容。'
  return ''
})

const quickStartOptions = [
  {
    mode: 'topic' as const,
    title: '输入主题生成',
    desc: '从一个选题直接生成标题、摘要、正文和封面建议。',
    action: '适合从 0 到 1 写公众号文章',
  },
  {
    mode: 'url' as const,
    title: '粘贴链接二创',
    desc: '自动解析公众号、网页、知乎等链接，再改写成原创公众号稿。',
    action: '适合把外部文章整理成自己的观点',
  },
  {
    mode: 'text' as const,
    title: '粘贴原文二创',
    desc: '把已有文章、笔记或资料重组为可发布的公众号长文。',
    action: '适合已有素材快速成稿',
  },
]

const taskTypeLabelMap: Record<string, string> = {
  wechat_article_generate: '文章生成',
  wechat_cover_generate: '封面生成',
  wechat_slot_image_generate: '正文配图',
  wechat_draft_send: '草稿发送',
  image_generation: '图片生成',
  text_generation: '内容生成',
}

const taskStatusLabelMap: Record<string, string> = {
  pending: '排队中',
  running: '生成中',
  retrying: '重试中',
  completed: '已完成',
  success: '已完成',
  failed: '待处理',
  cancelled: '已取消',
}

const assetTypeLabelMap: Record<string, string> = {
  image: '图片素材',
  cover: '封面素材',
  source_material: '选题素材',
  platform_content: '内容素材',
  wechat_draft: '公众号草稿',
}

function formatTaskType(value?: string) {
  return taskTypeLabelMap[String(value || '')] || '内容生成'
}

function formatTaskStatus(value?: string) {
  return taskStatusLabelMap[String(value || '')] || '处理中'
}

function formatAssetType(value?: string) {
  return assetTypeLabelMap[String(value || '')] || '素材'
}

function formatDraftStatus(draft: WechatDraftRecord) {
  if (draft.status === 'sent') return '已发送到公众号草稿箱'
  if (draft.status === 'failed') return draft.errorMessage || '发送未完成'
  if (draft.status === 'pending') return '等待发送'
  return '草稿已保存'
}

function friendlyError(fallback: string) {
  return fallback
}

function selectQuickStart(mode: 'topic' | 'url' | 'text') {
  articleInputMode.value = mode
  feedback.value = null
}

watch(
  () => props.initialContent,
  (value) => {
    if (value?.trim() && rawContent.value.includes('请输入或粘贴二创后的文章内容')) {
      rawContent.value = value
    }
    if (value?.trim() && articleInputMode.value === 'text') {
      articleSourceText.value = value
    }
    if (value?.trim() && articleInputMode.value === 'topic') {
      articleTheme.value = value
    }
    if (value?.trim() && articleInputMode.value === 'url' && !props.initialSourceUrl?.trim()) articleUrl.value = value
  }
)

watch(
  () => props.initialTitle,
  (value) => {
    if (value?.trim() && title.value === '未命名公众号文章') title.value = value
    if (value?.trim() && articleInputMode.value === 'topic' && !props.initialContent?.trim()) articleTheme.value = value
  }
)

watch(
  () => props.initialInputMode,
  (value) => {
    if (!value) return
    articleInputMode.value = value
    if (value === 'text') articleSourceText.value = props.initialContent || ''
    if (value === 'topic') articleTheme.value = props.initialContent || props.initialTitle || ''
    if (value === 'url') articleUrl.value = props.initialSourceUrl || props.initialContent || ''
  }
)

watch(
  () => props.initialSourceUrl,
  (value) => {
    if (articleInputMode.value === 'url') articleUrl.value = value || ''
  }
)

watch(
  () => props.initialProjectId,
  (value) => {
    if (value && value !== selectedProjectId.value) selectedProjectId.value = value
  }
)

watch(
  () => props.initialTopicId,
  (value) => {
    if (value && value !== selectedTopicId.value) selectedTopicId.value = value
  }
)

onMounted(async () => {
  await Promise.all([refreshAccounts(), refreshDrafts(), loadWorkspaceData()])
  await handlePreview()
})

watch(selectedProjectId, async () => {
  await loadProjectTopics()
  if (selectedTopicId.value && !topics.value.some((topic) => topic.topicId === selectedTopicId.value)) selectedTopicId.value = 0
  await Promise.all([loadRecentContents(), refreshTasksAndAssets()])
})

watch(selectedTopicId, async () => {
  await Promise.all([loadRecentContents(), refreshTasksAndAssets()])
})

watch(platformContentId, async () => {
  await Promise.all([refreshTasksAndAssets(), loadGenerationRecords()])
})

async function loadWorkspaceData() {
  await Promise.all([loadProjects(), loadWechatPromptTemplates(), loadTextModels(), loadImageModels()])
  await Promise.all([loadProjectTopics(), loadRecentContents(), refreshTasksAndAssets(), loadGenerationRecords()])
}

async function loadProjects() {
  try {
    const res = await listIpProjects()
    projects.value = res.data.items || []
    if (!selectedProjectId.value && projects.value.length) selectedProjectId.value = projects.value[0].projectId
  } catch {
    projects.value = []
  }
}

async function loadProjectTopics() {
  if (!selectedProjectId.value) {
    topics.value = []
    return
  }
  try {
    const res = await listProjectTopics(selectedProjectId.value)
    topics.value = res.data.items || []
  } catch {
    topics.value = []
  }
}

async function loadRecentContents() {
  try {
    const res = await listPlatformContents({
      projectId: selectedProjectId.value || undefined,
      topicId: selectedTopicId.value || undefined,
      platform: 'wechat',
      contentType: 'wechat_article',
      limit: 8,
    })
    recentContents.value = res.data.items || []
  } catch {
    recentContents.value = []
  }
}

async function loadWechatPromptTemplates() {
  try {
    const res = await listPromptTemplates('', 'wechat_article')
    promptTemplates.value = res.data || []
    if (!selectedPromptTemplateId.value && promptTemplates.value.length) selectedPromptTemplateId.value = promptTemplates.value[0].id
  } catch {
    promptTemplates.value = []
  }
}

async function loadTextModels() {
  try {
    const res = await listModelCatalog('text')
    textModels.value = res.data || []
    const defaultModel = textModels.value.find((item) => item.is_default) || textModels.value[0]
    if (!selectedTextModelId.value && defaultModel?.id) selectedTextModelId.value = defaultModel.id
  } catch {
    textModels.value = []
  }
}

async function loadImageModels() {
  try {
    const res = await listModelCatalog('image')
    imageModels.value = res.data || []
    const defaultModel = imageModels.value.find((item) => item.is_default) || imageModels.value[0]
    if (!selectedImageModelId.value && defaultModel?.id) selectedImageModelId.value = defaultModel.id
  } catch {
    imageModels.value = []
  }
}

async function refreshTasksAndAssets() {
  try {
    const scope = {
      projectId: selectedProjectId.value || undefined,
      topicId: selectedTopicId.value || undefined,
      platformContentId: platformContentId.value || undefined,
    }
    const [taskRes, assetRes] = await Promise.all([listUnifiedTasks({ ...scope, limit: 8 }), listUnifiedAssets({ ...scope, limit: 8 })])
    unifiedTasks.value = taskRes.data.items || []
    unifiedAssets.value = assetRes.data.items || []
  } catch {
    unifiedTasks.value = []
    unifiedAssets.value = []
  }
}

async function loadGenerationRecords() {
  try {
    const res = await listGenerationRecords({
      projectId: selectedProjectId.value || undefined,
      topicId: selectedTopicId.value || undefined,
      platformContentId: platformContentId.value || undefined,
      limit: 5,
    })
    generationRecords.value = res.data.items || []
  } catch {
    generationRecords.value = []
  }
}

async function ensureSelectedProject() {
  if (selectedProjectId.value) return selectedProjectId.value
  const name = projectForm.name.trim() || '默认 IP 项目'
  const res = await createIpProject({ ...projectForm, name })
  projects.value.unshift(res.data)
  selectedProjectId.value = res.data.projectId
  return selectedProjectId.value
}

async function createTopicFromCurrentInput() {
  const projectId = await ensureSelectedProject()
  const topicTitle = (articleTheme.value || title.value || projectForm.name || '未命名公众号选题').trim()
  const res = await createContentTopic(projectId, {
    title: topicTitle,
    inputSourceType: articleInputMode.value,
    targetPlatforms: ['wechat'],
    priority: 'medium',
  })
  topics.value.unshift(res.data)
  selectedTopicId.value = res.data.topicId
  feedback.value = { type: 'success', message: '内容选题已创建。' }
  await loadRecentContents()
  return selectedTopicId.value
}

async function openExistingContent(contentId = selectedExistingContentId.value) {
  if (!contentId) return
  try {
    const res = await getWechatArticle(contentId)
    syncArticleContent(res.data)
    selectedProjectId.value = res.data.projectId || selectedProjectId.value
    selectedTopicId.value = res.data.topicId || selectedTopicId.value
    selectedExistingContentId.value = contentId
    feedback.value = { type: 'success', message: '已打开历史公众号文章。' }
    await Promise.all([handlePreview(), refreshTasksAndAssets(), loadGenerationRecords()])
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('打开历史文章失败') }
  }
}

async function handleGenerateWechatArticle() {
  if (articleGenerateDisabledReason.value) {
    feedback.value = { type: 'error', message: articleGenerateDisabledReason.value }
    return
  }
  isArticleGenerating.value = true
  feedback.value = { type: 'info', message: '正在生成结构化公众号文章...' }
  try {
    const projectId = await ensureSelectedProject()
    const res = await generateWechatArticle({
      projectId,
      topicId: selectedTopicId.value || undefined,
      projectName: projectForm.name,
      topicTitle: articleTheme.value || title.value,
      inputType: articleInputMode.value,
      sourceUrl: articleUrl.value,
      rawText: articleSourceText.value,
      theme: articleTheme.value,
      promptTemplateId: selectedPromptTemplateId.value,
      textModelConfigId: selectedTextModelId.value,
      extraRequirements: articleExtraRequirements.value,
    })
    const content = res.data.content as PlatformContentData
    generatedArticle.value = content
    platformContentId.value = content.contentId
    selectedTopicId.value = content.topicId || selectedTopicId.value
    selectedExistingContentId.value = content.contentId
    title.value = content.title || title.value
    author.value = content.author || author.value
    digest.value = content.summary || digest.value
    rawContent.value = content.markdownSnapshot || content.contentHtml || rawContent.value
    if (content.coverPrompt) {
      articleExtraRequirements.value = articleExtraRequirements.value || `封面提示词：${content.coverPrompt}`
    }
    feedback.value = { type: 'success', message: res.message || '公众号文章已生成，已带入排版编辑区。' }
    await Promise.all([handlePreview(), refreshTasksAndAssets(), loadProjects(), loadProjectTopics(), loadRecentContents(), loadGenerationRecords()])
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('公众号文章生成失败') }
  } finally {
    isArticleGenerating.value = false
  }
}

async function saveCurrentArticle() {
  if (!platformContentId.value) return
  ensureMarkdownSynced()
  try {
    const res = await updateWechatArticle(platformContentId.value, {
      title: title.value,
      author: author.value,
      summary: digest.value,
      contentHtml: formattedHtml.value,
      markdownSnapshot: rawContent.value,
      coverPrompt: generatedArticle.value?.coverPrompt || '',
      imageSlots: generatedArticle.value?.imageSlots || [],
      tags: generatedArticle.value?.tags || [],
      complianceRisks: generatedArticle.value?.complianceRisks || [],
      status: 'editing',
    })
    generatedArticle.value = res.data
    feedback.value = { type: 'success', message: '公众号文章已保存到资产库。' }
    await refreshTasksAndAssets()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('保存公众号文章失败') }
  }
}

function syncArticleContent(content: PlatformContentData) {
  generatedArticle.value = content
  platformContentId.value = content.contentId
  selectedProjectId.value = content.projectId || selectedProjectId.value
  selectedTopicId.value = content.topicId || selectedTopicId.value
  title.value = content.title || title.value
  author.value = content.author || author.value
  digest.value = content.summary || digest.value
  rawContent.value = content.markdownSnapshot || rawContent.value
  coverUrl.value = String(content.content?.cover_url || coverUrl.value || '')
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function refreshCurrentArticle() {
  if (!platformContentId.value) return
  const res = await getWechatArticle(platformContentId.value)
  syncArticleContent(res.data)
}

async function pollTaskUntilSettled(taskId: number) {
  if (!taskId || pollingTaskIds.value.includes(taskId)) return
  pollingTaskIds.value = [...pollingTaskIds.value, taskId]
  try {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const res = await retrySafeGetTask(taskId)
      const task = res?.data
      if (!task || !['pending', 'running'].includes(task.status)) {
        await refreshCurrentArticle()
        await refreshTasksAndAssets()
        await handlePreview()
        feedback.value = { type: task?.status === 'failed' ? 'error' : 'success', message: task?.status === 'failed' ? (task.errorMessage || '图片任务执行失败') : '图片任务已完成，文章和资产已刷新。' }
        return
      }
      await sleep(1500)
    }
    await refreshTasksAndAssets()
    feedback.value = { type: 'info', message: '图片任务仍在执行，可稍后刷新任务和资产。' }
  } finally {
    pollingTaskIds.value = pollingTaskIds.value.filter((item) => item !== taskId)
  }
}

async function retrySafeGetTask(taskId: number) {
  try {
    return await getUnifiedTask(taskId)
  } catch {
    return null
  }
}

async function generateSlotImage(slotIndex: number) {
  if (!platformContentId.value || !generatedArticle.value) return
  const slot = generatedArticle.value.imageSlots?.[slotIndex] || {}
  activeSlotIndex.value = slotIndex
  feedback.value = { type: 'info', message: '正在提交正文图片生成任务...' }
  try {
    const res = await generateWechatArticleSlotImage(platformContentId.value, slotIndex, {
      prompt: String(slot.prompt || ''),
      imageModelConfigId: selectedImageModelId.value || undefined,
      width: 1024,
      height: 768,
      insertToMarkdown: true,
    })
    syncArticleContent(res.data.content)
    feedback.value = { type: 'success', message: res.message || '正文图片任务已提交并插入占位。' }
    await Promise.all([handlePreview(), refreshTasksAndAssets()])
    if (res.data.task?.taskId && ['pending', 'running'].includes(res.data.task.status)) void pollTaskUntilSettled(res.data.task.taskId)
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('正文图片生成失败') }
  } finally {
    activeSlotIndex.value = -1
  }
}

async function generateCoverImage() {
  if (!platformContentId.value || !generatedArticle.value) return
  isCoverGenerating.value = true
  feedback.value = { type: 'info', message: '正在提交封面图生成任务...' }
  try {
    const res = await generateWechatArticleCover(platformContentId.value, {
      prompt: generatedArticle.value.coverPrompt || `公众号封面图，主题：${title.value}`,
      imageModelConfigId: selectedImageModelId.value || undefined,
      width: 900,
      height: 383,
    })
    syncArticleContent(res.data.content)
    coverUrl.value = res.data.asset?.url || res.data.task?.outputSnapshot?.imageUrl || coverUrl.value
    feedback.value = { type: 'success', message: res.message || '封面图任务已提交。' }
    await refreshTasksAndAssets()
    if (res.data.task?.taskId && ['pending', 'running'].includes(res.data.task.status)) void pollTaskUntilSettled(res.data.task.taskId)
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('封面图生成失败') }
  } finally {
    isCoverGenerating.value = false
  }
}

async function setCoverImageUrl() {
  if (!platformContentId.value) return
  const imageUrl = window.prompt('请输入公网可访问的封面图 URL', coverUrl.value)?.trim()
  if (!imageUrl) return
  try {
    const res = await setWechatArticleCover(platformContentId.value, { imageUrl })
    syncArticleContent(res.data.content)
    coverUrl.value = res.data.coverUrl || imageUrl
    feedback.value = { type: 'success', message: res.message || '封面图已设置。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('设置封面失败') }
  }
}

async function uploadCoverFile(event: Event) {
  if (!platformContentId.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const res = await uploadPlatformContentImageAsset(platformContentId.value, {
      file,
      slotIndex: -1,
      insertToMarkdown: false,
      title: `${title.value || '公众号'}封面图`,
      tags: ['wechat', 'cover', 'upload'],
    })
    const assetId = res.data.asset?.assetId
    const coverRes = await setWechatArticleCover(platformContentId.value, { assetId })
    syncArticleContent(coverRes.data.content)
    coverUrl.value = coverRes.data.coverUrl || res.data.asset?.url || coverUrl.value
    feedback.value = { type: 'success', message: '封面图已上传并设置，发送草稿时会上传到微信素材接口。' }
    await refreshTasksAndAssets()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('上传封面失败') }
  } finally {
    input.value = ''
  }
}

async function insertImageAtCursor() {
  if (!platformContentId.value) return
  const imageUrl = window.prompt('请输入要插入到光标位置的图片链接')?.trim()
  if (!imageUrl) return
  const textarea = markdownTextarea.value
  const start = textarea?.selectionStart ?? rawContent.value.length
  const end = textarea?.selectionEnd ?? start
  const markdown = '\n\n![公众号插图](' + imageUrl + ')\n\n'
  rawContent.value = `${rawContent.value.slice(0, start)}${markdown}${rawContent.value.slice(end)}`
  await updateWechatArticle(platformContentId.value, {
    title: title.value,
    author: author.value,
    summary: digest.value,
    markdownSnapshot: rawContent.value,
    coverPrompt: generatedArticle.value?.coverPrompt || '',
    imageSlots: generatedArticle.value?.imageSlots || [],
    tags: generatedArticle.value?.tags || [],
    complianceRisks: generatedArticle.value?.complianceRisks || [],
    status: 'editing',
  })
  await handlePreview()
  window.setTimeout(() => textarea?.focus(), 0)
  feedback.value = { type: 'success', message: '图片已插入到当前光标位置并保存。' }
}

async function insertSlotImageUrl(slotIndex: number) {
  if (!platformContentId.value) return
  const imageUrl = window.prompt('请输入可访问的图片链接')?.trim()
  if (!imageUrl) return
  activeSlotIndex.value = slotIndex
  try {
    const res = await insertWechatArticleSlotImage(platformContentId.value, slotIndex, { imageUrl, insertToMarkdown: true })
    syncArticleContent(res.data)
    feedback.value = { type: 'success', message: res.message || '图片已插入正文。' }
    await Promise.all([handlePreview(), refreshTasksAndAssets()])
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('插入图片失败') }
  } finally {
    activeSlotIndex.value = -1
  }
}

async function removeSlotAsset(slotIndex: number) {
  if (!platformContentId.value) return
  activeSlotIndex.value = slotIndex
  try {
    const res = await removeWechatArticleSlotAsset(platformContentId.value, slotIndex)
    syncArticleContent(res.data)
    feedback.value = { type: 'success', message: res.message || '图片位绑定已移除。' }
    await refreshTasksAndAssets()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('移除图片绑定失败') }
  } finally {
    activeSlotIndex.value = -1
  }
}

async function reuseAssetToArticle(asset: any) {
  if (!platformContentId.value || !generatedArticle.value?.imageSlots?.length) return
  const slotIndex = Math.max(0, generatedArticle.value.imageSlots.findIndex((slot) => !slot.imageUrl))
  activeAssetId.value = asset.assetId
  try {
    const res = await reuseUnifiedAsset(asset.assetId, { platformContentId: platformContentId.value, slotIndex, insertToMarkdown: true })
    syncArticleContent(res.data.content)
    feedback.value = { type: 'success', message: '图片已插入正文。' }
    await Promise.all([handlePreview(), refreshTasksAndAssets()])
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('插入图片失败') }
  } finally {
    activeAssetId.value = 0
  }
}

async function reuseAssetAsCover(asset: any) {
  if (!platformContentId.value) return
  activeAssetId.value = asset.assetId
  try {
    const res = await reuseUnifiedAsset(asset.assetId, { target: 'wechat_article_cover', platformContentId: platformContentId.value, slotIndex: 0, insertToMarkdown: false })
    syncArticleContent(res.data.content)
    coverUrl.value = res.data.coverUrl || asset.url || coverUrl.value
    feedback.value = { type: 'success', message: res.message || '资产已设置为封面图。' }
    await refreshTasksAndAssets()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('设置封面失败') }
  } finally {
    activeAssetId.value = 0
  }
}

async function addImageAssetFromUrl() {
  const imageUrl = window.prompt('请输入可访问的图片链接')?.trim()
  if (!imageUrl) return
  const titleText = window.prompt('请输入图片资产标题', '公众号图片资产')?.trim() || '公众号图片资产'
  try {
    const res = await createUnifiedAsset({
      assetType: 'image',
      sourceType: 'manual_url',
      title: titleText,
      url: imageUrl,
      projectId: selectedProjectId.value || undefined,
      topicId: selectedTopicId.value || undefined,
      platformContentId: platformContentId.value || undefined,
      tags: ['wechat', 'manual'],
      metadata: { source: 'wechat_publisher_manual_url' },
    })
    unifiedAssets.value.unshift(res.data)
    feedback.value = { type: 'success', message: res.message || '图片资产已添加。' }
    await refreshTasksAndAssets()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('添加图片失败') }
  }
}

async function removeUnifiedAsset(asset: any) {
  if (!window.confirm(`确认删除资产「${asset.title || asset.url || asset.assetId}」吗？`)) return
  activeAssetId.value = asset.assetId
  try {
    await deleteUnifiedAsset(asset.assetId)
    feedback.value = { type: 'success', message: '资产已删除。' }
    await refreshTasksAndAssets()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('删除素材失败') }
  } finally {
    activeAssetId.value = 0
  }
}

async function retryTask(task: any) {
  activeTaskId.value = task.taskId
  try {
    const res = await retryUnifiedTask(task.taskId)
    if (res.data?.content) syncArticleContent(res.data.content)
    else if (res.data?.content?.contentId) syncArticleContent(res.data.content)
    feedback.value = { type: res.code === 1 ? 'error' : 'success', message: res.message || '任务已重试。' }
    await Promise.all([refreshTasksAndAssets(), task.taskType === 'wechat_draft_send' || res.data?.draftId ? refreshDrafts() : Promise.resolve()])
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('重试失败') }
  } finally {
    activeTaskId.value = 0
  }
}

async function refreshAccounts() {
  try {
    const res = await listWechatAccounts()
    accounts.value = res.data.items || []
    const defaultAccount = accounts.value.find((item) => item.isDefault) || accounts.value[0]
    if (defaultAccount && !selectedAccountId.value) selectedAccountId.value = defaultAccount.accountId
  } catch {
    accounts.value = []
  }
}

async function refreshDrafts() {
  try {
    const res = await listWechatDrafts({ pageSize: 10 })
    drafts.value = res.data.items || []
  } catch {
    drafts.value = []
  }
}

function editAccount(account: WechatAccount) {
  accountForm.accountId = account.accountId
  accountForm.name = account.name
  accountForm.appId = account.appId
  accountForm.appSecret = ''
  accountForm.originalId = account.originalId || ''
  accountForm.feishuAccount = account.feishuAccount || ''
  accountForm.themeId = account.themeId || ''
  accountForm.apiBase = account.apiBase || 'https://feishu2weixin.maolai.cc'
  accountForm.defaultCoverUrl = account.defaultCoverUrl || ''
  accountForm.notes = account.notes || ''
  accountForm.isDefault = Boolean(account.isDefault)
  accountForm.isActive = account.isActive !== false
  selectedAccountId.value = account.accountId
}

function resetAccountForm() {
  accountForm.accountId = 0
  accountForm.name = ''
  accountForm.appId = ''
  accountForm.appSecret = ''
  accountForm.originalId = ''
  accountForm.feishuAccount = ''
  accountForm.themeId = ''
  accountForm.apiBase = 'https://feishu2weixin.maolai.cc'
  accountForm.defaultCoverUrl = ''
  accountForm.notes = ''
  accountForm.isDefault = false
  accountForm.isActive = true
}

async function saveAccount() {
  if (!isAdminUser.value) {
    feedback.value = { type: 'error', message: '公众号账号由管理员统一配置，请联系管理员。' }
    return
  }
  if (!accountForm.name.trim() || !accountForm.appId.trim()) {
    feedback.value = { type: 'error', message: '请填写公众号名称和 AppID' }
    return
  }
  if (!accountForm.accountId && !accountForm.appSecret.trim()) {
    feedback.value = { type: 'error', message: '首次保存公众号账号必须填写 AppSecret' }
    return
  }
  isLoading.value = true
  try {
    const payload = { ...accountForm }
    const res = accountForm.accountId
      ? await updateWechatAccount(accountForm.accountId, payload)
      : await createWechatAccount(payload)
    feedback.value = { type: 'success', message: res.message || '公众号账号已保存' }
    selectedAccountId.value = res.data.accountId
    resetAccountForm()
    await refreshAccounts()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('公众号账号保存失败') }
  } finally {
    isLoading.value = false
  }
}

async function removeAccount(account: WechatAccount) {
  if (!isAdminUser.value) return
  if (!window.confirm(`确认删除公众号账号「${account.name}」吗？`)) return
  try {
    await deleteWechatAccount(account.accountId)
    if (selectedAccountId.value === account.accountId) selectedAccountId.value = 0
    await refreshAccounts()
    feedback.value = { type: 'success', message: '公众号账号已删除' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('删除失败') }
  }
}

async function testSelectedAccount(accountId = selectedAccountId.value) {
  if (!isAdminUser.value) {
    feedback.value = { type: 'error', message: '公众号连接测试由管理员执行。' }
    return
  }
  if (!accountId) return
  isLoading.value = true
  try {
    const res = await testWechatAccount(accountId)
    feedback.value = { type: res.code === 0 ? 'success' : 'error', message: res.message }
    await refreshAccounts()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('测试连接失败') }
  } finally {
    isLoading.value = false
  }
}

async function loadThemes() {
  if (!accountForm.feishuAccount.trim()) {
    feedback.value = { type: 'error', message: '请先填写 feishu2weixin 账号' }
    return
  }
  isLoading.value = true
  try {
    const res = await listWechatThemes({ feishuAccount: accountForm.feishuAccount, apiBase: accountForm.apiBase })
    themes.value = res.data.themes || []
    feedback.value = { type: 'success', message: themes.value.length ? `已查询到 ${themes.value.length} 个主题` : '该账号暂无已保存主题' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('主题查询失败') }
  } finally {
    isLoading.value = false
  }
}

async function handlePreview() {
  ensureMarkdownSynced()
  if (!rawContent.value.trim()) return
  isLoading.value = true
  try {
    const res = await previewWechatFormat({
      title: title.value,
      rawContent: rawContent.value,
      style: style.value,
      accountId: selectedAccountId.value || undefined,
    })
    if (res.code !== 0) {
      return
    }
    formattedHtml.value = res.data.formattedHtml
    feedback.value = { type: 'success', message: '排版预览已更新' }
    if (platformContentId.value) await saveCurrentArticle()
  } catch {
    formattedHtml.value = ''
  } finally {
    isLoading.value = false
  }
}

async function runPreflight(showSuccess = true) {
  try {
    const res = await preflightWechatDraft({
      accountId: selectedAccountId.value || undefined,
      title: title.value,
      digest: digest.value,
      rawContent: rawContent.value,
      coverUrl: coverUrl.value,
    })
    preflightResult.value = res.data
    if (showSuccess) {
      feedback.value = {
        type: res.data.canSend ? 'success' : 'error',
        message: res.data.canSend ? '发送前检查通过' : '发送前检查未通过，请处理错误项',
      }
    }
    return res.data
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('发送前检查失败') }
    return null
  }
}

function createIdempotencyKey() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function handleSendDraft() {
  if (!canSend.value) return
  const preflight = await runPreflight(false)
  if (!preflight?.canSend) {
    feedback.value = { type: 'error', message: '发送前检查未通过，请先处理错误项。' }
    return
  }
  if (!window.confirm('确认发送到微信公众号草稿箱吗？发送前请确认服务器 IP 已加入公众号 API 白名单。')) return
  isSending.value = true
  try {
    const res = await sendWechatDraft({
      accountId: selectedAccountId.value,
      platformContentId: platformContentId.value || undefined,
      title: title.value,
      author: author.value,
      digest: digest.value,
      rawContent: rawContent.value,
      coverUrl: coverUrl.value,
      contentSourceUrl: contentSourceUrl.value,
      style: style.value,
      idempotencyKey: createIdempotencyKey(),
    })
    if (res.code !== 0) {
      feedback.value = { type: 'error', message: res.message || '发送失败' }
      await refreshDrafts()
      return
    }
    formattedHtml.value = res.data.formattedHtml || formattedHtml.value
    feedback.value = { type: 'success', message: '已发送到公众号草稿箱，可前往公众号后台查看。' }
    await refreshDrafts()
  } catch (err: any) {
    feedback.value = { type: 'error', message: friendlyError('发送草稿失败') }
  } finally {
    isSending.value = false
  }
}

async function copyText(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
    feedback.value = { type: 'success', message: `${label}已复制` }
  } catch {
    feedback.value = { type: 'error', message: '浏览器禁止访问剪贴板，请手动复制' }
  }
}

function setEditorSelection(start: number, end = start) {
  window.setTimeout(() => {
    const textarea = markdownTextarea.value
    textarea?.focus()
    textarea?.setSelectionRange(start, end)
  }, 0)
}

function insertEditorText(text: string, cursorOffset = text.length, selectLength = 0) {
  const textarea = markdownTextarea.value
  const start = textarea?.selectionStart ?? rawContent.value.length
  const end = textarea?.selectionEnd ?? start
  rawContent.value = `${rawContent.value.slice(0, start)}${text}${rawContent.value.slice(end)}`
  const cursor = start + cursorOffset
  setEditorSelection(cursor, cursor + selectLength)
}

function wrapEditorSelection(prefix: string, suffix: string, placeholder: string) {
  const textarea = markdownTextarea.value
  const start = textarea?.selectionStart ?? rawContent.value.length
  const end = textarea?.selectionEnd ?? start
  const selected = rawContent.value.slice(start, end) || placeholder
  const insertion = `${prefix}${selected}${suffix}`
  rawContent.value = `${rawContent.value.slice(0, start)}${insertion}${rawContent.value.slice(end)}`
  setEditorSelection(start + prefix.length, start + prefix.length + selected.length)
}

type EditorBlockKind = 'h2' | 'h3' | 'quote' | 'golden' | 'focus' | 'divider' | 'follow' | 'recommend' | 'ul' | 'ol'

function insertEditorBlock(kind: EditorBlockKind) {
  const blocks: Record<EditorBlockKind, string> = {
    h2: '\n\n## 小标题\n\n',
    h3: '\n\n### 小节标题\n\n',
    quote: '\n\n> 这里填写引用、案例或补充说明。\n\n',
    golden: '\n\n> ==这里填写金句，突出文章核心观点。==\n\n',
    focus: '\n\n==这里填写重点段落或关键结论。==\n\n',
    divider: '\n\n---\n\n',
    follow: '\n\n---\n\n如果这篇内容对你有帮助，欢迎关注我，持续分享更多实用方法。\n\n',
    recommend: '\n\n## 推荐阅读\n\n- [相关阅读标题](https://example.com)\n\n',
    ul: '\n\n- 列表项一\n- 列表项二\n\n',
    ol: '\n\n1. 第一步\n2. 第二步\n\n',
  }
  const insertion = blocks[kind]
  const placeholderStart = insertion.search(/小标题|小节标题|这里填写|相关阅读标题/)
  insertEditorText(insertion, placeholderStart >= 0 ? placeholderStart : insertion.length, placeholderStart >= 0 ? insertion.match(/小标题|小节标题|这里填写[^。\n]*|相关阅读标题/)?.[0]?.length || 0 : 0)
}
</script>

<template>
  <div class="wechat-publisher">
    <header class="wechat-hero">
      <div>
        <span class="section-eyebrow">WeChat Publisher</span>
        <h2>公众号排版与草稿箱发布</h2>
        <p>把二创后的内容整理成公众号排版稿，处理封面和正文图片，并推送到微信公众号草稿箱。</p>
      </div>
      <div class="hero-actions">
        <button class="btn btn-ghost" :disabled="isLoading" @click="() => runPreflight()">发送前检查</button>
        <button class="btn btn-ghost" :disabled="isLoading" @click="handlePreview">更新预览</button>
        <button class="btn btn-primary" :disabled="!canSend" @click="handleSendDraft">
          {{ isSending ? '发送中...' : '发送到公众号草稿箱' }}
        </button>
      </div>
    </header>

    <div v-if="feedback" class="wechat-feedback" :class="feedback.type">{{ feedback.message }}</div>

    <section class="wechat-workbench wechat-card">
      <div class="card-head">
        <div>
          <span class="section-eyebrow">Content Workbench</span>
          <h3>公众号内容工作台</h3>
          <p>选择一个开始方式：输入主题、粘贴链接自动解析二创，或粘贴原文二创。系统会自动创建内部项目和选题，生成结果直接进入排版编辑区。</p>
        </div>
        <button class="btn btn-ghost btn-sm" :disabled="isArticleGenerating" @click="loadWorkspaceData">刷新项目数据</button>
      </div>

      <div class="quick-start-grid" aria-label="公众号快速开始">
        <button
          v-for="option in quickStartOptions"
          :key="option.mode"
          class="quick-start-card"
          :class="{ active: articleInputMode === option.mode }"
          type="button"
          @click="selectQuickStart(option.mode)"
        >
          <strong>{{ option.title }}</strong>
          <span>{{ option.desc }}</span>
          <small>{{ option.action }}</small>
        </button>
      </div>

      <div class="workbench-grid">
        <div class="workbench-column">
          <label>IP 项目
            <select v-model.number="selectedProjectId" class="select wide">
              <option :value="0">自动创建默认项目</option>
              <option v-for="project in projects" :key="project.projectId" :value="project.projectId">{{ project.name }}</option>
            </select>
          </label>
          <div v-if="!selectedProjectId" class="mini-form">
            <label>新项目名称<input v-model="projectForm.name" class="input" placeholder="如：李老师知识 IP" /></label>
            <label>IP 定位<input v-model="projectForm.positioning" class="input" placeholder="账号定位、专业方向、内容风格" /></label>
              <label>目标人群<input v-model="projectForm.targetAudience" class="input" placeholder="如：职场新人、宝妈、企业老板" /></label>
          </div>
          <label v-if="selectedProjectId">内容选题
            <select v-model.number="selectedTopicId" class="select wide">
              <option :value="0">生成时自动创建选题</option>
              <option v-for="topic in topics" :key="topic.topicId" :value="topic.topicId">{{ topic.title }} · {{ topic.status }}</option>
            </select>
          </label>
          <button v-if="selectedProjectId" class="btn btn-ghost btn-sm" :disabled="isArticleGenerating" @click="createTopicFromCurrentInput">用当前输入创建选题</button>
        </div>

        <div class="workbench-column">
          <label>输入方式
            <select v-model="articleInputMode" class="select wide">
              <option value="topic">主题生成</option>
              <option value="url">链接解析二创</option>
              <option value="text">粘贴原文二创</option>
            </select>
          </label>
          <label v-if="articleInputMode === 'topic'">公众号主题<input v-model="articleTheme" class="input" placeholder="输入选题、标题或创作需求" /></label>
          <label v-else-if="articleInputMode === 'url'">原文链接<input v-model="articleUrl" class="input" placeholder="粘贴公众号文章、网页、知乎、小红书等链接，系统会先解析再二创" /></label>
          <label v-else>原文内容<textarea v-model="articleSourceText" class="input textarea compact" placeholder="粘贴需要二创的原文、资料或笔记"></textarea></label>
        </div>

        <div class="workbench-column">
          <label>公众号提示词模板
            <select v-model.number="selectedPromptTemplateId" class="select wide">
              <option :value="0">使用默认公众号模板</option>
              <option v-for="template in promptTemplates" :key="template.id" :value="template.id">{{ template.name }} · {{ template.version }}</option>
            </select>
          </label>
          <label>文案生成方式
            <select v-model.number="selectedTextModelId" class="select wide">
              <option :value="0">推荐设置</option>
              <option v-for="model in textModels" :key="model.id" :value="model.id || 0">{{ model.name }} · {{ model.provider }}</option>
            </select>
          </label>
          <label>图片生成方式
            <select v-model.number="selectedImageModelId" class="select wide">
              <option :value="0">推荐设置</option>
              <option v-for="model in imageModels" :key="model.id" :value="model.id || 0">{{ model.name }} · {{ model.provider }}</option>
            </select>
          </label>
          <label>补充要求<textarea v-model="articleExtraRequirements" class="input textarea compact" placeholder="例如：偏专业干货、少营销、多案例、适合企业家阅读"></textarea></label>
        </div>
      </div>

      <div class="workbench-actions">
        <button class="btn btn-primary" :disabled="isArticleGenerating" @click="handleGenerateWechatArticle">
          {{ isArticleGenerating ? '生成中...' : articleInputMode === 'url' ? '解析链接并二创' : articleInputMode === 'text' ? '二创成公众号文章' : '一键生成公众号文章' }}
        </button>
        <button class="btn btn-ghost" :disabled="!platformContentId" @click="saveCurrentArticle">保存当前文章</button>
        <span v-if="generatedArticle" class="article-status">已生成内容 #{{ generatedArticle.contentId }} · {{ generatedArticle.status }}</span>
        <span v-else-if="articleGenerateDisabledReason" class="article-status muted">{{ articleGenerateDisabledReason }}</span>
      </div>

      <div class="workbench-side-lists">
        <div>
          <div class="list-headline">
            <strong>最近公众号文章</strong>
            <button class="mini-link" @click="loadRecentContents">刷新</button>
          </div>
          <p v-if="!recentContents.length">暂无历史文章。</p>
          <ul v-else>
            <li v-for="content in recentContents.slice(0, 4)" :key="content.contentId" class="inline-list-item">
              <span>{{ content.title || '未命名文章' }} · {{ content.status }}</span>
              <button class="mini-link" :disabled="selectedExistingContentId === content.contentId" @click="openExistingContent(content.contentId)">打开</button>
            </li>
          </ul>
        </div>
        <div>
          <strong>生成进度</strong>
          <p v-if="!unifiedTasks.length">暂无生成进度。</p>
          <ul v-else>
            <li v-for="task in unifiedTasks.slice(0, 4)" :key="task.taskId" class="inline-list-item">
              <span>{{ formatTaskType(task.taskType) }} · {{ formatTaskStatus(task.status) }}</span>
              <button v-if="task.status === 'failed'" class="mini-link" :disabled="activeTaskId === task.taskId" @click="retryTask(task)">重试</button>
            </li>
          </ul>
        </div>
        <div>
          <div class="list-headline">
            <strong>最近生成</strong>
            <button class="mini-link" @click="loadGenerationRecords">刷新</button>
          </div>
          <p v-if="!generationRecords.length">暂无生成内容。</p>
          <ul v-else>
            <li v-for="record in generationRecords.slice(0, 4)" :key="record.recordId" class="inline-list-item">
              <span>{{ record.createdAt?.slice(0, 16) || '刚刚' }} · {{ record.parseStatus === 'failed' ? '待处理' : '已生成' }}</span>
            </li>
          </ul>
        </div>
        <div>
          <div class="list-headline">
            <strong>最近资产</strong>
            <button class="mini-link" @click="addImageAssetFromUrl">添加图片链接</button>
          </div>
          <p v-if="!unifiedAssets.length">暂无资产记录。</p>
          <ul v-else>
            <li v-for="asset in unifiedAssets.slice(0, 4)" :key="asset.assetId" class="inline-list-item">
              <span>{{ formatAssetType(asset.assetType) }} · {{ asset.title || '未命名素材' }}</span>
              <button v-if="asset.assetType === 'image' && platformContentId && generatedArticle?.imageSlots?.length" class="mini-link" :disabled="activeAssetId === asset.assetId" @click="reuseAssetToArticle(asset)">插入正文</button>
              <button v-if="asset.assetType === 'image' && platformContentId" class="mini-link" :disabled="activeAssetId === asset.assetId" @click="reuseAssetAsCover(asset)">设封面</button>
              <button class="mini-link danger" :disabled="activeAssetId === asset.assetId" @click="removeUnifiedAsset(asset)">删除</button>
            </li>
          </ul>
        </div>
      </div>

      <div v-if="generatedArticle?.imageSlots?.length" class="image-slot-panel">
        <div class="card-head compact-head">
          <div>
            <strong>正文图片位</strong>
            <p>生成或选择图片后，可作为正文插图随文章一起整理。</p>
          </div>
        </div>
        <div class="image-slot-list">
          <article v-for="(slot, index) in generatedArticle.imageSlots" :key="index" class="image-slot-card">
            <div>
              <strong>{{ slot.purpose || `正文插图 ${index + 1}` }}</strong>
              <span>{{ slot.position || '未指定位置' }} · {{ slot.status || '待生成' }}</span>
              <p>{{ slot.prompt || '暂无提示词' }}</p>
              <a v-if="slot.imageUrl" :href="slot.imageUrl" target="_blank" rel="noreferrer">查看图片</a>
            </div>
            <div class="slot-actions">
              <button class="btn btn-ghost btn-sm" :disabled="activeSlotIndex === index" @click="generateSlotImage(index)">生成图片</button>
              <button class="btn btn-ghost btn-sm" :disabled="activeSlotIndex === index" @click="insertSlotImageUrl(index)">插入图片链接</button>
              <button class="btn btn-ghost btn-sm" :disabled="activeSlotIndex === index || !slot.imageUrl" @click="removeSlotAsset(index)">移除绑定</button>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section v-if="preflightResult" class="preflight-panel" :class="{ pass: preflightResult.canSend }">
      <div>
          <strong>{{ preflightResult.canSend ? '发送前检查通过' : '发送前检查需处理' }}</strong>
        <span>正文图片 {{ preflightResult.imageCount }} 张，封面：{{ preflightResult.selectedCoverUrl || '未识别' }}</span>
      </div>
      <ul v-if="preflightResult.issues.length">
        <li v-for="issue in preflightResult.issues" :key="issue.code + issue.message" :class="issue.level">
          <strong>{{ issue.level === 'error' ? '需要处理' : '提醒' }}：{{ issue.message }}</strong>
          <span>{{ issue.suggestion }}</span>
        </li>
      </ul>
    </section>

    <section class="wechat-grid wechat-editor-layout">
      <article class="wechat-card editor-card">
        <div class="card-head editor-card-head">
          <div>
            <span class="section-eyebrow">Editor</span>
            <h3>文章内容</h3>
            <p>左侧专注写作，右侧实时预览公众号排版效果。</p>
          </div>
          <select v-model="style" class="select style-select" aria-label="排版风格" @change="handlePreview">
            <option v-for="item in styleOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>

        <div class="editor-meta-grid">
          <label>标题<input v-model="title" class="input title-input" placeholder="公众号文章标题" /></label>
          <label>作者<input v-model="author" class="input" placeholder="可选" /></label>
          <label>原文链接<input v-model="contentSourceUrl" class="input" placeholder="可选" /></label>
          <label class="wide">摘要<textarea v-model="digest" class="input textarea compact" placeholder="可选，建议 60-120 字"></textarea></label>
          <label class="wide">封面图链接<input v-model="coverUrl" class="input" placeholder="粘贴可访问的图片链接；不填则使用正文第一张图或账号默认封面" /></label>
        </div>

        <div class="action-row compact-actions cover-actions">
          <button class="btn btn-ghost btn-sm" :disabled="!platformContentId || isCoverGenerating" @click="generateCoverImage">{{ isCoverGenerating ? '生成中...' : '生成封面图' }}</button>
          <button class="btn btn-ghost btn-sm" :disabled="!platformContentId" @click="setCoverImageUrl">使用图片链接作为封面</button>
          <label class="btn btn-ghost btn-sm upload-btn" :class="{ disabled: !platformContentId }">
            上传封面
            <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" :disabled="!platformContentId" @change="uploadCoverFile" />
          </label>
          <span v-if="generatedArticle?.coverAssetId" class="article-status">封面资产 #{{ generatedArticle.coverAssetId }}</span>
        </div>

        <div v-if="imageSlotSummary" class="image-slot-status-row" aria-label="正文图片位状态">
          <span>正文插图 {{ imageSlotSummary.ready }}/{{ imageSlotSummary.total }} 已就绪</span>
          <span v-if="imageSlotSummary.pending">待处理 {{ imageSlotSummary.pending }}</span>
          <span v-if="imageSlotSummary.failed" class="slot-failed">失败 {{ imageSlotSummary.failed }}</span>
        </div>

        <div class="editor-writing-zone">
          <div class="editor-zone-head">
            <label>文章正文</label>
            <div class="editor-mode-switch" role="tablist" aria-label="编辑器模式">
              <button type="button" class="mode-chip" :class="{ active: editorMode === 'source' }" @click="switchEditorMode('source')">源码</button>
              <button type="button" class="mode-chip" :class="{ active: editorMode === 'blocks' }" @click="switchEditorMode('blocks')">块编辑</button>
            </div>
            <span class="editor-stats">{{ rawContent.length }} 字</span>
          </div>
        <div v-if="editorMode === 'source'" class="wechat-editor-toolbar" aria-label="公众号排版工具栏">
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('h2')">二级标题</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('h3')">小标题</button>
          <button class="toolbar-chip" type="button" @click="wrapEditorSelection('**', '**', '重点文字')">加粗</button>
          <button class="toolbar-chip" type="button" @click="wrapEditorSelection('*', '*', '强调文字')">斜体</button>
          <button class="toolbar-chip" type="button" @click="wrapEditorSelection('~~', '~~', '删除线')">删除线</button>
          <button class="toolbar-chip" type="button" @click="wrapEditorSelection('==', '==', '高亮重点')">高亮</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('ul')">无序列表</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('ol')">有序列表</button>
          <button class="toolbar-chip" type="button" @click="wrapEditorSelection('[', '](https://example.com)', '链接文字')">超链接</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('quote')">引用卡片</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('golden')">金句卡</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('focus')">重点段落</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('divider')">分割线</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('follow')">关注引导</button>
          <button class="toolbar-chip" type="button" @click="insertEditorBlock('recommend')">推荐阅读</button>
        </div>
        <textarea v-if="editorMode === 'source'" ref="markdownTextarea" v-model="rawContent" class="input textarea markdown-input" aria-label="文章正文"></textarea>
        <div v-else class="block-editor">
          <article v-for="block in contentBlocks" :key="block.id" class="block-card">
            <div class="block-head">
              <input v-model="block.title" class="input block-title" aria-label="段落标题" @input="applyBlocksToMarkdown" />
              <button type="button" class="btn btn-ghost btn-sm" @click="removeContentBlock(block.id)">删除</button>
            </div>
            <textarea v-model="block.body" class="input textarea block-body" aria-label="段落正文" @input="applyBlocksToMarkdown" />
          </article>
          <button type="button" class="btn btn-ghost" @click="addContentBlock">新增段落</button>
        </div>
        <p class="editor-helper">{{ editorMode === 'blocks' ? '块编辑按二级标题分段，适合长文逐段调整；预览和发送前会自动合并为 Markdown。' : '工具栏会插入公众号兼容 Markdown，点击“更新预览”后转换为内联样式 HTML，发送草稿时仍由后端清洗过滤。' }}</p>
        <div class="action-row editor-actions">
          <button class="btn btn-ghost" @click="copyText(rawContent, '正文')">复制正文</button>
          <button class="btn btn-ghost" :disabled="!formattedHtml" @click="copyText(formattedHtml, '排版结果')">复制排版结果</button>
          <button class="btn btn-ghost" :disabled="!platformContentId" @click="insertImageAtCursor">在光标处插图</button>
        </div>
        </div>
      </article>

      <article class="wechat-card preview-card">
        <div class="preview-card-head">
          <div>
            <span class="section-eyebrow">Preview</span>
            <h3>公众号预览</h3>
            <p>模拟手机阅读效果，发送前请确认标题、摘要和配图。</p>
          </div>
          <button class="btn btn-ghost btn-sm" :disabled="isLoading" @click="handlePreview">刷新预览</button>
        </div>
        <div class="phone-frame">
          <div class="phone-status"><span>公众号预览</span><span>{{ selectedAccount?.name || '未选择账号' }}</span></div>
          <div class="article-preview">
            <h1>{{ title }}</h1>
            <p class="article-meta">{{ author || '作者未填写' }} · 草稿预览</p>
            <iframe
              v-if="formattedHtml"
              class="rendered-frame"
              title="公众号排版预览"
              sandbox="allow-same-origin"
              :srcdoc="previewSrcdoc"
            ></iframe>
            <div v-else class="empty-preview">点击“更新预览”生成公众号排版效果。</div>
          </div>
        </div>
      </article>

      <aside class="wechat-side">
        <section class="wechat-card account-card">
          <div class="card-head">
            <div>
              <h3>公众号账号</h3>
              <p>{{ isAdminUser ? '管理可用公众号账号和发布设置。' : '请选择可用的公众号账号，发布前系统会自动完成必要检查。' }}</p>
            </div>
            <button v-if="isAdminUser" class="btn btn-ghost btn-sm" @click="resetAccountForm">新建</button>
          </div>

          <label>选择账号
            <select v-model.number="selectedAccountId" class="select wide">
              <option :value="0">请选择公众号</option>
              <option v-for="account in accounts" :key="account.accountId" :value="account.accountId" :disabled="account.isActive === false">{{ account.name }}{{ account.isActive === false ? '（已停用）' : '' }}</option>
            </select>
          </label>
          <div v-if="selectedAccount" class="selected-account">
            <strong>{{ selectedAccount.name }}</strong>
            <span>{{ selectedAccount.lastTestStatus === 'success' ? '连接正常' : selectedAccount.lastTestMessage || '未测试' }}</span>
            <div class="action-row compact-actions">
              <button v-if="isAdminUser" class="btn btn-ghost btn-sm" @click="editAccount(selectedAccount)">编辑</button>
              <button v-if="isAdminUser" class="btn btn-ghost btn-sm" @click="testSelectedAccount(selectedAccount.accountId)">测试连接</button>
              <button v-if="isAdminUser" class="btn btn-danger btn-sm" @click="removeAccount(selectedAccount)">删除</button>
            </div>
          </div>

          <div v-if="isAdminUser" class="account-form">
            <label>账号名称<input v-model="accountForm.name" class="input" placeholder="如：小P增长笔记" /></label>
            <label>AppID<input v-model="accountForm.appId" class="input" placeholder="微信公众号 AppID" /></label>
            <label>AppSecret<input v-model="accountForm.appSecret" class="input" type="password" placeholder="新增必填；编辑留空则不修改" /></label>
            <label>原始 ID<input v-model="accountForm.originalId" class="input" placeholder="可选" /></label>
            <label>feishu2weixin 账号<input v-model="accountForm.feishuAccount" class="input" placeholder="用于调用 md-to-wechat 渲染主题" /></label>
            <label>主题 ID<input v-model="accountForm.themeId" class="input" placeholder="从 feishu2weixin 我的主题复制" /></label>
            <label>排版服务地址<input v-model="accountForm.apiBase" class="input" /></label>
            <label>默认封面 URL<input v-model="accountForm.defaultCoverUrl" class="input" placeholder="正文无图时使用" /></label>
            <label class="check-row"><input v-model="accountForm.isDefault" type="checkbox" />设为默认公众号</label>
            <label class="check-row"><input v-model="accountForm.isActive" type="checkbox" />启用账号</label>
            <div v-if="themes.length" class="theme-list">
              <button v-for="theme in themes" :key="theme.id" type="button" @click="accountForm.themeId = theme.id">{{ theme.name }}</button>
            </div>
            <div class="action-row">
              <button class="btn btn-ghost" :disabled="isLoading" @click="loadThemes">查询主题</button>
              <button class="btn btn-primary" :disabled="isLoading" @click="saveAccount">保存账号</button>
            </div>
          </div>
          <p v-else class="admin-only-note">公众号账号由运营人员统一维护，当前页面仅用于选择账号和发送草稿。</p>
        </section>

        <section class="wechat-card history-card">
          <div class="card-head">
            <div>
              <h3>最近草稿</h3>
              <p>查看最近创建的公众号草稿状态。</p>
            </div>
            <button class="btn btn-ghost btn-sm" @click="refreshDrafts">刷新</button>
          </div>
          <div v-if="drafts.length" class="draft-list">
            <article v-for="draft in drafts" :key="draft.draftId" :class="draft.status">
              <strong>{{ draft.title }}</strong>
              <span>{{ formatDraftStatus(draft) }}</span>
            </article>
          </div>
          <p v-else class="empty-history">暂无公众号草稿记录。</p>
        </section>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.wechat-publisher {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
  overflow: visible;
  padding: 0;
  background: transparent;
}

.wechat-hero,
.wechat-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.wechat-hero {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 22px;
}

.section-eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.wechat-hero h2,
.wechat-card h3 {
  margin: 4px 0 8px;
  color: #0f172a;
}

.wechat-hero p,
.wechat-card p,
.selected-account span,
.draft-list span,
.empty-history {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.hero-actions,
.action-row,
.inline-fields,
.card-head {
  display: flex;
  gap: 10px;
  align-items: center;
}

.hero-actions,
.card-head {
  justify-content: space-between;
}

.wechat-grid {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(340px, 0.92fr);
  gap: 16px;
  align-items: start;
}

.wechat-editor-layout {
  grid-template-columns: minmax(420px, 1.15fr) minmax(360px, 0.85fr);
  gap: 20px;
}

.editor-card-head .style-select {
  min-width: 140px;
}

.editor-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.editor-meta-grid .wide {
  grid-column: 1 / -1;
}

.title-input {
  font-size: 16px;
  font-weight: 700;
}

.cover-actions {
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.editor-writing-zone {
  display: grid;
  gap: 10px;
  padding: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: #f8fafc;
}

.editor-zone-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.editor-zone-head label {
  margin: 0;
  color: #0f172a;
  font-size: 14px;
}

.editor-stats {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.preview-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 4px;
}

.preview-card-head h3 {
  margin: 4px 0 6px;
  font-size: 18px;
}

.preview-card-head p {
  margin: 0;
  max-width: 280px;
}

.image-slot-status-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border: 1px solid rgba(37, 99, 235, 0.14);
  border-radius: 14px;
  background: rgba(239, 246, 255, 0.72);
  color: #1e40af;
  font-size: 12px;
  font-weight: 800;
}

.image-slot-status-row .slot-failed {
  color: #b91c1c;
}

.editor-mode-switch {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  border-radius: 999px;
  background: #eef2f7;
}

.mode-chip {
  padding: 6px 12px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #64748b;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.mode-chip.active {
  background: #fff;
  color: #2457ff;
  box-shadow: inset 0 0 0 1px #dbe6ff;
}

.block-editor {
  display: grid;
  gap: 12px;
}

.block-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: #fff;
}

.block-head {
  display: flex;
  gap: 10px;
  align-items: center;
}

.block-title {
  flex: 1;
  font-weight: 800;
}

.block-body {
  min-height: 120px;
  line-height: 1.75;
}

.wechat-side {
  grid-column: 1 / -1;
}

.wechat-workbench {
  display: grid;
  gap: 16px;
}

.workbench-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 14px;
}

.quick-start-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 12px;
}

.quick-start-card {
  display: grid;
  gap: 7px;
  min-height: 118px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 18px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  color: #0f172a;
  cursor: pointer;
  padding: 16px;
  text-align: left;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.quick-start-card:hover,
.quick-start-card.active {
  border-color: rgba(37, 99, 235, 0.58);
  box-shadow: 0 14px 32px rgba(37, 99, 235, 0.12);
  transform: translateY(-1px);
}

.quick-start-card strong {
  font-size: 15px;
  font-weight: 900;
}

.quick-start-card span,
.quick-start-card small {
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.quick-start-card small {
  color: #2563eb;
  font-weight: 900;
}

.workbench-column:nth-child(3) {
  grid-column: 1 / -1;
}

.workbench-column,
.mini-form {
  display: grid;
  gap: 12px;
}

.workbench-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.article-status {
  color: #1e40af;
  font-size: 13px;
  font-weight: 800;
}

.article-status.muted,
.admin-only-note {
  color: #64748b;
}

.workbench-side-lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(240px, 1fr));
  gap: 12px;
}

.workbench-side-lists > div {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: #fff;
  padding: 12px;
}

.workbench-side-lists strong {
  display: block;
  color: #0f172a;
  margin-bottom: 6px;
}

.list-headline {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.list-headline strong {
  margin-bottom: 0;
}

.workbench-side-lists ul {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
}

.inline-list-item {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.mini-link {
  border: 0;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
  font-weight: 900;
  padding: 0;
  white-space: nowrap;
}

.mini-link.danger {
  color: #dc2626;
}

.mini-link:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.image-slot-panel {
  display: grid;
  gap: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: #f8fafc;
  padding: 14px;
}

.compact-head p {
  max-width: 780px;
}

.image-slot-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(240px, 1fr));
  gap: 10px;
}

.image-slot-card {
  display: grid;
  gap: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: #fff;
  padding: 12px;
}

.image-slot-card span,
.image-slot-card a {
  display: block;
  color: #64748b;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.image-slot-card p {
  margin-top: 4px;
}

.slot-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.wechat-card {
  display: grid;
  gap: 14px;
  padding: 18px;
}

label {
  display: grid;
  gap: 7px;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.inline-fields label {
  flex: 1;
}

.input,
.select {
  width: 100%;
  min-height: 42px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 14px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  padding: 10px 12px;
  outline: none;
}

.textarea {
  resize: vertical;
}

.textarea.compact {
  min-height: 72px;
}

.markdown-input {
  min-height: 480px;
  padding: 16px 18px;
  border-color: rgba(15, 23, 42, 0.1);
  background: #fff;
  color: #111827;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 15px;
  line-height: 1.85;
  letter-spacing: 0.01em;
}

.markdown-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.wechat-editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(248, 250, 252, 0.95));
  padding: 10px;
}

.toolbar-chip {
  min-height: 30px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 999px;
  background: #fff;
  color: #1e40af;
  cursor: pointer;
  font-size: 12px;
  font-weight: 900;
  padding: 0 10px;
}

.toolbar-chip:hover {
  border-color: rgba(37, 99, 235, 0.32);
  background: #eff6ff;
}

.editor-helper {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.btn {
  min-height: 40px;
  border: 0;
  border-radius: 999px;
  padding: 9px 14px;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.btn-sm {
  min-height: 34px;
  padding: 7px 11px;
  font-size: 12px;
}

.btn-primary {
  background: #2457ff;
  color: #fff;
}

.btn-ghost {
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
  color: #0f172a;
}

.btn-danger {
  background: #fee2e2;
  color: #991b1b;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.upload-btn {
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.upload-btn.disabled {
  opacity: 0.55;
  pointer-events: none;
}

.upload-btn input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.wechat-feedback {
  border-radius: 16px;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 800;
}

.wechat-feedback.success { background: #dcfce7; color: #166534; }
.wechat-feedback.error { background: #fee2e2; color: #991b1b; }
.wechat-feedback.info { background: #dbeafe; color: #1e40af; }

.preflight-panel {
  display: grid;
  gap: 10px;
  border: 1px solid #fecaca;
  border-radius: 18px;
  background: #fff7f7;
  color: #7f1d1d;
  padding: 14px 16px;
}

.preflight-panel.pass {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #14532d;
}

.preflight-panel div,
.preflight-panel li {
  display: grid;
  gap: 4px;
}

.preflight-panel ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}

.preflight-panel span {
  font-size: 13px;
  line-height: 1.5;
}

.preflight-panel li.warning {
  color: #92400e;
}

.phone-frame {
  max-width: 390px;
  margin: 0 auto;
  border: 10px solid #d1d5db;
  border-radius: 34px;
  background: #fff;
  overflow: hidden;
}

.phone-status {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.article-preview {
  max-height: 720px;
  overflow: auto;
  padding: 18px;
}

.article-preview h1 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 24px;
  line-height: 1.35;
}

.article-meta {
  margin-bottom: 18px;
  color: #94a3b8;
  font-size: 13px;
}

.rendered-frame {
  width: 100%;
  min-height: 620px;
  border: 0;
  background: #fff;
}

.empty-preview,
.empty-history {
  border: 1px dashed rgba(37, 99, 235, 0.22);
  border-radius: 18px;
  padding: 24px;
  background: #f8fafc;
  text-align: center;
}

.wechat-side {
  display: grid;
  gap: 16px;
}

.selected-account,
.draft-list article {
  display: grid;
  gap: 8px;
  border-radius: 16px;
  background: #f8fafc;
  padding: 12px;
}

.account-form {
  display: grid;
  gap: 12px;
}

.check-row {
  display: flex;
  grid-template-columns: none;
  align-items: center;
}

.theme-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.theme-list button {
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 7px 10px;
  cursor: pointer;
}

.draft-list {
  display: grid;
  gap: 10px;
}

.draft-list article.sent {
  border-left: 4px solid #16a34a;
}

.draft-list article.failed {
  border-left: 4px solid #dc2626;
}

.compact-actions {
  flex-wrap: wrap;
}

@media (max-width: 1180px) {
  .wechat-grid,
  .wechat-editor-layout,
  .editor-meta-grid,
  .quick-start-grid,
  .workbench-grid,
  .workbench-side-lists {
    grid-template-columns: 1fr;
  }

  .workbench-column:nth-child(3),
  .wechat-side {
    grid-column: auto;
  }

  .wechat-hero,
  .inline-fields,
  .hero-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>

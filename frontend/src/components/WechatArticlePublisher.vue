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
const articleInputMode = ref<'topic' | 'url' | 'text'>('topic')
const articleTheme = ref('')
const articleUrl = ref('')
const articleSourceText = ref('')
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

watch(
  () => props.initialContent,
  (value) => {
    if (value?.trim() && rawContent.value.includes('请输入或粘贴二创后的文章内容')) {
      rawContent.value = value
    }
  }
)

watch(
  () => props.initialTitle,
  (value) => {
    if (value?.trim() && title.value === '未命名公众号文章') title.value = value
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '打开历史文章失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '公众号文章生成失败' }
  } finally {
    isArticleGenerating.value = false
  }
}

async function saveCurrentArticle() {
  if (!platformContentId.value) return
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '保存公众号文章失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail?.message || err?.response?.data?.detail || err.message || '正文图片生成失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail?.message || err?.response?.data?.detail || err.message || '封面图生成失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '设置封面失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '上传封面失败' }
  } finally {
    input.value = ''
  }
}

async function insertImageAtCursor() {
  if (!platformContentId.value) return
  const imageUrl = window.prompt('请输入要插入到光标位置的公网图片 URL')?.trim()
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
  const imageUrl = window.prompt('请输入公网可访问的图片 URL')?.trim()
  if (!imageUrl) return
  activeSlotIndex.value = slotIndex
  try {
    const res = await insertWechatArticleSlotImage(platformContentId.value, slotIndex, { imageUrl, insertToMarkdown: true })
    syncArticleContent(res.data)
    feedback.value = { type: 'success', message: res.message || '图片已插入正文。' }
    await Promise.all([handlePreview(), refreshTasksAndAssets()])
  } catch (err: any) {
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '插入图片失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '移除图片绑定失败' }
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
    feedback.value = { type: 'success', message: res.message || '资产已复用到正文图片位。' }
    await Promise.all([handlePreview(), refreshTasksAndAssets()])
  } catch (err: any) {
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '复用资产失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '设置封面失败' }
  } finally {
    activeAssetId.value = 0
  }
}

async function addImageAssetFromUrl() {
  const imageUrl = window.prompt('请输入公网可访问的图片 URL')?.trim()
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '添加图片资产失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '删除资产失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '任务重试失败' }
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
  } catch (err: any) {
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '公众号账号加载失败' }
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
    feedback.value = { type: 'error', message: '第一版公众号账号由管理员统一配置，请联系管理员。' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '公众号账号保存失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '删除失败' }
  }
}

async function testSelectedAccount(accountId = selectedAccountId.value) {
  if (!isAdminUser.value) {
    feedback.value = { type: 'error', message: '第一版公众号连接测试由管理员执行。' }
    return
  }
  if (!accountId) return
  isLoading.value = true
  try {
    const res = await testWechatAccount(accountId)
    feedback.value = { type: res.code === 0 ? 'success' : 'error', message: res.message }
    await refreshAccounts()
  } catch (err: any) {
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '测试连接失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '主题查询失败' }
  } finally {
    isLoading.value = false
  }
}

async function handlePreview() {
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
      feedback.value = { type: 'error', message: res.message || '排版预览失败' }
      return
    }
    formattedHtml.value = res.data.formattedHtml
    feedback.value = { type: 'success', message: '排版预览已更新' }
    if (platformContentId.value) await saveCurrentArticle()
  } catch (err: any) {
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '排版预览失败' }
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
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '发送前检查失败' }
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
    feedback.value = { type: 'success', message: `已发送到公众号草稿箱，media_id：${res.data.wechatMediaId}` }
    await refreshDrafts()
  } catch (err: any) {
    feedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '发送草稿失败' }
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
</script>

<template>
  <div class="wechat-publisher">
    <header class="wechat-hero">
      <div>
        <span class="section-eyebrow">WeChat Publisher</span>
        <h2>公众号排版与草稿箱发布</h2>
        <p>把二创后的内容转成公众号可用 HTML，自动处理封面和正文图片，并推送到微信公众号草稿箱。</p>
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
          <p>先创建项目和选题，再通过链接、原文或主题生成结构化公众号文章，生成结果会自动进入下方排版编辑区。</p>
        </div>
        <button class="btn btn-ghost btn-sm" :disabled="isArticleGenerating" @click="loadWorkspaceData">刷新底座数据</button>
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
              <option value="url">链接二创</option>
              <option value="text">粘贴原文二创</option>
            </select>
          </label>
          <label v-if="articleInputMode === 'topic'">公众号主题<input v-model="articleTheme" class="input" placeholder="输入选题、标题或创作需求" /></label>
          <label v-else-if="articleInputMode === 'url'">原文链接<input v-model="articleUrl" class="input" placeholder="公众号、网页、知乎、小红书等链接" /></label>
          <label v-else>原文内容<textarea v-model="articleSourceText" class="input textarea compact" placeholder="粘贴需要二创的原文、资料或笔记"></textarea></label>
        </div>

        <div class="workbench-column">
          <label>公众号提示词模板
            <select v-model.number="selectedPromptTemplateId" class="select wide">
              <option :value="0">使用默认公众号模板</option>
              <option v-for="template in promptTemplates" :key="template.id" :value="template.id">{{ template.name }} · {{ template.version }}</option>
            </select>
          </label>
          <label>文本模型
            <select v-model.number="selectedTextModelId" class="select wide">
              <option :value="0">使用系统默认文本模型</option>
              <option v-for="model in textModels" :key="model.id" :value="model.id || 0">{{ model.name }} · {{ model.provider }}</option>
            </select>
          </label>
          <label>图片模型
            <select v-model.number="selectedImageModelId" class="select wide">
              <option :value="0">使用系统默认图片模型</option>
              <option v-for="model in imageModels" :key="model.id" :value="model.id || 0">{{ model.name }} · {{ model.provider }}</option>
            </select>
          </label>
          <label>补充要求<textarea v-model="articleExtraRequirements" class="input textarea compact" placeholder="例如：偏专业干货、少营销、多案例、适合企业家阅读"></textarea></label>
        </div>
      </div>

      <div class="workbench-actions">
        <button class="btn btn-primary" :disabled="Boolean(articleGenerateDisabledReason)" @click="handleGenerateWechatArticle">
          {{ isArticleGenerating ? '生成中...' : '生成公众号文章' }}
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
          <strong>最近任务</strong>
          <p v-if="!unifiedTasks.length">暂无任务记录。</p>
          <ul v-else>
            <li v-for="task in unifiedTasks.slice(0, 4)" :key="task.taskId" class="inline-list-item">
              <span>{{ task.taskType }} · {{ task.status }} · {{ task.errorMessage || '无错误' }}</span>
              <button v-if="task.status === 'failed'" class="mini-link" :disabled="activeTaskId === task.taskId" @click="retryTask(task)">重试</button>
            </li>
          </ul>
        </div>
        <div>
          <div class="list-headline">
            <strong>生成记录</strong>
            <button class="mini-link" @click="loadGenerationRecords">刷新</button>
          </div>
          <p v-if="!generationRecords.length">暂无生成记录。</p>
          <ul v-else>
            <li v-for="record in generationRecords.slice(0, 4)" :key="record.recordId" class="inline-list-item">
              <span>#{{ record.recordId }} · {{ record.parseStatus }} · 模型 {{ record.modelSnapshot?.name || record.modelConfigId || '默认' }}</span>
            </li>
          </ul>
        </div>
        <div>
          <div class="list-headline">
            <strong>最近资产</strong>
            <button class="mini-link" @click="addImageAssetFromUrl">添加图片URL</button>
          </div>
          <p v-if="!unifiedAssets.length">暂无资产记录。</p>
          <ul v-else>
            <li v-for="asset in unifiedAssets.slice(0, 4)" :key="asset.assetId" class="inline-list-item">
              <span>{{ asset.assetType }} · {{ asset.title || asset.url || '未命名资产' }}</span>
              <button v-if="asset.assetType === 'image' && platformContentId && generatedArticle?.imageSlots?.length" class="mini-link" :disabled="activeAssetId === asset.assetId" @click="reuseAssetToArticle(asset)">复用</button>
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
            <p>生成或复用图片后会写入图片位，并自动插入到 Markdown，草稿发布时会进入公众号图片上传替换流程。</p>
          </div>
        </div>
        <div class="image-slot-list">
          <article v-for="(slot, index) in generatedArticle.imageSlots" :key="index" class="image-slot-card">
            <div>
              <strong>{{ slot.purpose || `正文插图 ${index + 1}` }}</strong>
              <span>{{ slot.position || '未指定位置' }} · {{ slot.status || '待生成' }}</span>
              <p>{{ slot.prompt || '暂无提示词' }}</p>
              <a v-if="slot.imageUrl" :href="slot.imageUrl" target="_blank" rel="noreferrer">{{ slot.imageUrl }}</a>
            </div>
            <div class="slot-actions">
              <button class="btn btn-ghost btn-sm" :disabled="activeSlotIndex === index" @click="generateSlotImage(index)">生成图片</button>
              <button class="btn btn-ghost btn-sm" :disabled="activeSlotIndex === index" @click="insertSlotImageUrl(index)">插入URL</button>
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
          <strong>{{ issue.level === 'error' ? '错误' : '提醒' }}：{{ issue.message }}</strong>
          <span>{{ issue.suggestion }}</span>
        </li>
      </ul>
    </section>

    <section class="wechat-grid">
      <article class="wechat-card editor-card">
        <div class="card-head">
          <div>
            <h3>文章内容</h3>
            <p>正文使用 Markdown，排版后会转换为公众号内联 HTML。</p>
          </div>
          <select v-model="style" class="select" @change="handlePreview">
            <option v-for="item in styleOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <label>标题<input v-model="title" class="input" placeholder="公众号文章标题" /></label>
        <div class="inline-fields">
          <label>作者<input v-model="author" class="input" placeholder="可选" /></label>
          <label>原文链接<input v-model="contentSourceUrl" class="input" placeholder="可选" /></label>
        </div>
        <label>摘要<textarea v-model="digest" class="input textarea compact" placeholder="可选，建议 60-120 字"></textarea></label>
        <label>封面图 URL<input v-model="coverUrl" class="input" placeholder="公网 JPG/PNG URL；不填则使用正文第一张图或账号默认封面" /></label>
        <div class="action-row compact-actions">
          <button class="btn btn-ghost btn-sm" :disabled="!platformContentId || isCoverGenerating" @click="generateCoverImage">{{ isCoverGenerating ? '生成中...' : '生成封面图' }}</button>
          <button class="btn btn-ghost btn-sm" :disabled="!platformContentId" @click="setCoverImageUrl">设置封面URL</button>
          <label class="btn btn-ghost btn-sm upload-btn" :class="{ disabled: !platformContentId }">
            上传封面
            <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" :disabled="!platformContentId" @change="uploadCoverFile" />
          </label>
          <span v-if="generatedArticle?.coverAssetId" class="article-status">封面资产 #{{ generatedArticle.coverAssetId }}</span>
        </div>
        <label>Markdown 正文<textarea ref="markdownTextarea" v-model="rawContent" class="input textarea markdown-input"></textarea></label>
        <div class="action-row">
          <button class="btn btn-ghost" @click="copyText(rawContent, 'Markdown')">复制 Markdown</button>
          <button class="btn btn-ghost" :disabled="!formattedHtml" @click="copyText(formattedHtml, 'HTML')">复制 HTML</button>
          <button class="btn btn-ghost" :disabled="!platformContentId" @click="insertImageAtCursor">在光标处插图</button>
        </div>
      </article>

      <article class="wechat-card preview-card">
        <div class="phone-frame">
          <div class="phone-status"><span>公众号预览</span><span>{{ selectedAccount?.name || '未选择账号' }}</span></div>
          <div class="article-preview">
            <h1>{{ title }}</h1>
            <p class="article-meta">{{ author || '作者未填写' }} · 草稿预览</p>
            <iframe
              v-if="formattedHtml"
              class="rendered-frame"
              title="公众号 HTML 安全预览"
              sandbox=""
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
              <p>{{ isAdminUser ? '管理员配置公众号账号；AppSecret 加密存储，前端只显示掩码。' : '普通用户只能选择管理员已启用和授权的公众号账号。' }}</p>
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
          <p v-else class="admin-only-note">账号新增、密钥更新和测试连接由管理员在后台完成，避免普通用户接触 AppSecret。</p>
        </section>

        <section class="wechat-card history-card">
          <div class="card-head">
            <div>
              <h3>最近草稿</h3>
              <p>记录每次推送结果和错误原因。</p>
            </div>
            <button class="btn btn-ghost btn-sm" @click="refreshDrafts">刷新</button>
          </div>
          <div v-if="drafts.length" class="draft-list">
            <article v-for="draft in drafts" :key="draft.draftId" :class="draft.status">
              <strong>{{ draft.title }}</strong>
              <span>{{ draft.status === 'sent' ? `已发送：${draft.wechatMediaId}` : draft.errorMessage || draft.status }}</span>
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
  min-height: 420px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  line-height: 1.7;
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

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { downloadUnifiedAssetFile, listUnifiedAssets } from '../api/assets.api'
import { listUnifiedTasks } from '../api/tasks.api'
import {
  addPlatformContentImageAsset,
  createCharacterProfile,
  createContentTopic,
  createIpProject,
  createPlatformPublishConfig,
  createStoryboardRecord,
  deleteCharacterProfile,
  deletePlatformContent,
  deletePlatformPublishConfig,
  deleteStoryboardRecord,
  downloadPlatformContentPackage,
  exportPlatformContent,
  generatePlatformContentSlotImage,
  generateShortVideoScript,
  generateXiaohongshuNote,
  getPlatformContent,
  getPlatformWorkspaceOverview,
  importPlatformContentToTeleprompter,
  listCharacterProfiles,
  listIpProjects,
  listPlatformContents,
  listPlatformPublishConfigs,
  listProjectTopics,
  listStoryboardRecords,
  updatePlatformContent,
  uploadPlatformContentImageAsset,
  type CharacterProfileData,
  type ContentTopicData,
  type IpProjectData,
  type PlatformContentData,
  type PlatformPublishConfigData,
  type PlatformWorkspaceOverviewData,
  type StoryboardRecordData,
} from '../api/platformContent.api'
import { listModelCatalog, type AIModelConfigData } from '../api/modelConfig.api'
import { listPromptTemplates, type PromptTemplateData } from '../api/promptTemplates.api'

type PlatformMode = 'xiaohongshu' | 'douyin' | 'shipinhao'
type InputMode = 'topic' | 'url' | 'text'

const props = defineProps<{
  initialTitle?: string
  initialContent?: string
  initialInputMode?: InputMode
  initialSourceUrl?: string
  initialProjectId?: number
  initialTopicId?: number
  currentUser?: { is_admin?: boolean }
}>()

const mode = ref<PlatformMode>('xiaohongshu')
const inputMode = ref<InputMode>(props.initialInputMode || 'topic')
const feedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const isGenerating = ref(false)
const isSaving = ref(false)
const isPollingSupportData = ref(false)
const selectedProjectId = ref(props.initialProjectId || 0)
const selectedTopicId = ref(props.initialTopicId || 0)
const selectedContentId = ref(0)
const selectedPromptTemplateId = ref(0)
const selectedTextModelId = ref(0)
const selectedImageModelId = ref(0)
const activeSlotIndex = ref(-1)

const projects = ref<IpProjectData[]>([])
const topics = ref<ContentTopicData[]>([])
const contents = ref<PlatformContentData[]>([])
const promptTemplates = ref<PromptTemplateData[]>([])
const textModels = ref<AIModelConfigData[]>([])
const imageModels = ref<AIModelConfigData[]>([])
const tasks = ref<any[]>([])
const assets = ref<any[]>([])
const publishConfigs = ref<PlatformPublishConfigData[]>([])
const characters = ref<CharacterProfileData[]>([])
const storyboards = ref<StoryboardRecordData[]>([])
const currentContent = ref<PlatformContentData | null>(null)
const exportPackage = ref<any | null>(null)
const workspaceOverview = ref<PlatformWorkspaceOverviewData | null>(null)
let supportPollTimer: number | null = null
const isAdminUser = computed(() => props.currentUser?.is_admin === true)

const projectForm = reactive({
  name: '默认 IP 项目',
  ipType: 'personal_ip',
  positioning: '',
  targetAudience: '',
  defaultPlatforms: ['xiaohongshu', 'douyin'],
  voiceStyle: {},
})

const generateForm = reactive({
  topicTitle: props.initialTitle || '',
  theme: props.initialInputMode === 'topic' ? props.initialContent || props.initialTitle || '' : props.initialTitle || '',
  sourceUrl: props.initialInputMode === 'url' ? props.initialSourceUrl || props.initialContent || '' : '',
  rawText: props.initialInputMode === 'text' ? props.initialContent || '' : '',
  extraRequirements: '',
})

const editForm = reactive({
  title: '',
  summary: '',
  markdownSnapshot: '',
  coverPrompt: '',
  tagsText: '',
})

const publishForm = reactive<PlatformPublishConfigData>({
  platform: 'xiaohongshu',
  name: '',
  accountLabel: '',
  apiBase: '',
  authType: 'manual',
  credentials: '',
  status: 'reserved',
  notes: '',
  isActive: true,
})

const characterForm = reactive<CharacterProfileData>({
  projectId: 0,
  name: '',
  role: '',
  identity: '',
  personality: '',
  speakingStyle: '',
  catchphrase: '',
  referenceImages: [],
  profile: {},
  status: 'active',
})

const storyboardForm = reactive<StoryboardRecordData>({
  projectId: 0,
  topicId: 0,
  platformContentId: 0,
  title: '',
  storyboardType: 'drama',
  frames: [],
  assets: [],
  status: 'draft',
})

const platformCards = [
  {
    key: 'xiaohongshu' as PlatformMode,
    title: '小红书创作',
    badge: '图文',
    summary: '生成图文笔记、首图和多图提示词，适合种草与干货分享。',
    nextStep: '生成后可编辑正文、下载图片清单，或继续打磨配图。',
  },
  {
    key: 'douyin' as PlatformMode,
    title: '抖音口播',
    badge: '口播',
    summary: '从主题或素材生成短视频口播稿，直接进入提词器录制。',
    nextStep: '生成后建议导入提词器，或继续拆分分镜做短大片。',
  },
  {
    key: 'shipinhao' as PlatformMode,
    title: '视频号口播',
    badge: '口播',
    summary: '面向视频号语气的口播脚本，强调观点表达与转化引导。',
    nextStep: '生成后可复制导出、导入提词器，或绑定封面图资产。',
  },
]

const platformMeta = computed(() => {
  if (mode.value === 'xiaohongshu') {
    return { label: '小红书创作', contentType: 'xiaohongshu_note', platform: 'xiaohongshu', templateType: 'xiaohongshu_note' }
  }
  return { label: mode.value === 'douyin' ? '抖音口播' : '视频号口播', contentType: 'short_video_script', platform: mode.value, templateType: 'short_video_script' }
})

const activePlatformCard = computed(() => platformCards.find((item) => item.key === mode.value) || platformCards[0])

const canGenerate = computed(() => {
  if (isGenerating.value) return false
  if (inputMode.value === 'topic') return Boolean(generateForm.theme.trim() || generateForm.topicTitle.trim())
  if (inputMode.value === 'url') return Boolean(generateForm.sourceUrl.trim())
  return Boolean(generateForm.rawText.trim())
})

const parsedContent = computed<Record<string, any>>(() => currentContent.value?.content || {})
const imageSlots = computed(() => currentContent.value?.imageSlots || [])
const contentPreview = computed(() => {
  const payload = parsedContent.value
  if (mode.value === 'xiaohongshu') {
    return String(payload.export_text || `${payload.title || editForm.title}\n\n${payload.body || editForm.markdownSnapshot}`)
  }
  return String(payload.teleprompter_text || payload.script || editForm.markdownSnapshot || '')
})
const hasRunningSupportItems = computed(() => {
  const runningTasks = tasks.value.some((task) => ['pending', 'running', 'retrying'].includes(String(task.status || '')))
  const runningAssets = assets.value.some((asset) => ['pending', 'running', 'processing'].includes(String(asset.status || '')))
  return runningTasks || runningAssets
})

const taskTypeLabelMap: Record<string, string> = {
  xiaohongshu_note: '小红书内容',
  short_video_script: '口播内容',
  image_generation: '图片生成',
  video_generation: '视频生成',
  text_generation: '文案生成',
  platform_content_image: '配图生成',
}

const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  editing: '编辑中',
  ready: '可使用',
  pending: '排队中',
  running: '生成中',
  processing: '处理中',
  retrying: '重试中',
  completed: '已完成',
  success: '已完成',
  failed: '待处理',
  reserved: '待启用',
  active: '可用',
  generated_with_fallback: '已生成',
}

const assetTypeLabelMap: Record<string, string> = {
  image: '图片素材',
  cover: '封面素材',
  source_material: '选题素材',
  platform_content: '内容素材',
  video: '视频素材',
}

const storyboardTypeLabelMap: Record<string, string> = {
  drama: '剧本短视频',
  cinematic: '短大片',
  talking_head: '口播',
}

function formatTaskType(value?: string) {
  return taskTypeLabelMap[String(value || '')] || '内容生成'
}

function formatStatus(value?: string) {
  return statusLabelMap[String(value || '')] || '处理中'
}

function formatAssetType(value?: string) {
  return assetTypeLabelMap[String(value || '')] || '素材'
}

function formatStoryboardType(value?: string) {
  return storyboardTypeLabelMap[String(value || '')] || '分镜'
}

watch(mode, async () => {
  publishForm.platform = mode.value
  selectedPromptTemplateId.value = 0
  selectedContentId.value = 0
  currentContent.value = null
  await Promise.all([loadPromptTemplates(), loadContents(), loadPublishConfigs()])
})

watch(
  () => props.initialProjectId,
  (value) => {
    if (value && value !== selectedProjectId.value) selectedProjectId.value = value
  }
)

watch(
  () => props.initialInputMode,
  (value) => {
    if (!value) return
    inputMode.value = value
    if (value === 'topic') generateForm.theme = props.initialContent || props.initialTitle || ''
    if (value === 'url') generateForm.sourceUrl = props.initialSourceUrl || props.initialContent || ''
    if (value === 'text') generateForm.rawText = props.initialContent || ''
  }
)

watch(
  () => props.initialTitle,
  (value) => {
    if (!value?.trim()) return
    generateForm.topicTitle = value
    if (inputMode.value === 'topic' && !props.initialContent?.trim()) generateForm.theme = value
  }
)

watch(
  () => props.initialContent,
  (value) => {
    if (!value?.trim()) return
    if (inputMode.value === 'text') generateForm.rawText = value
    if (inputMode.value === 'topic') generateForm.theme = value
    if (inputMode.value === 'url' && !props.initialSourceUrl?.trim()) generateForm.sourceUrl = value
  }
)

watch(
  () => props.initialSourceUrl,
  (value) => {
    if (inputMode.value === 'url') generateForm.sourceUrl = value || ''
  }
)

watch(
  () => props.initialTopicId,
  (value) => {
    if (value && value !== selectedTopicId.value) selectedTopicId.value = value
  }
)

watch(selectedProjectId, async () => {
  await Promise.all([loadTopics(), loadContents(), refreshSupportData()])
})

watch(selectedTopicId, async () => {
  await Promise.all([loadContents(), refreshSupportData()])
})

watch(selectedContentId, async () => {
  if (selectedContentId.value) await openContent(selectedContentId.value)
})

onMounted(async () => {
  await Promise.all([loadProjects(), loadPromptTemplates(), loadModels(), loadPublishConfigs(), loadWorkspaceOverview()])
  await Promise.all([loadTopics(), loadContents(), refreshSupportData()])
  supportPollTimer = window.setInterval(refreshSupportDataIfActive, 3500)
})

onUnmounted(() => {
  if (supportPollTimer) window.clearInterval(supportPollTimer)
})

function setFeedback(type: 'success' | 'error' | 'info', message: string) {
  feedback.value = { type, message }
}

function getErrorMessage(err: any, fallback: string) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  return err?.message || fallback
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

async function loadTopics() {
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

async function loadContents() {
  try {
    const res = await listPlatformContents({
      projectId: selectedProjectId.value || undefined,
      topicId: selectedTopicId.value || undefined,
      platform: platformMeta.value.platform,
      contentType: platformMeta.value.contentType,
      limit: 20,
    })
    contents.value = res.data.items || []
  } catch {
    contents.value = []
  }
}

async function loadWorkspaceOverview() {
  try {
    const res = await getPlatformWorkspaceOverview()
    workspaceOverview.value = res.data
  } catch {
    workspaceOverview.value = null
  }
}

async function loadPromptTemplates() {
  try {
    const res = await listPromptTemplates('', platformMeta.value.templateType)
    promptTemplates.value = res.data || []
    if (!selectedPromptTemplateId.value && promptTemplates.value.length) selectedPromptTemplateId.value = promptTemplates.value[0].id
  } catch {
    promptTemplates.value = []
  }
}

async function loadModels() {
  try {
    const [textRes, imageRes] = await Promise.all([listModelCatalog('text'), listModelCatalog('image')])
    textModels.value = textRes.data || []
    imageModels.value = imageRes.data || []
    selectedTextModelId.value = textModels.value.find((item) => item.is_default)?.id || textModels.value[0]?.id || 0
    selectedImageModelId.value = imageModels.value.find((item) => item.is_default)?.id || imageModels.value[0]?.id || 0
  } catch {
    textModels.value = []
    imageModels.value = []
  }
}

async function loadPublishConfigs() {
  try {
    const res = await listPlatformPublishConfigs(mode.value)
    publishConfigs.value = res.data.items || []
  } catch {
    publishConfigs.value = []
  }
}

async function refreshSupportData() {
  if (isPollingSupportData.value) return
  isPollingSupportData.value = true
  const scope = {
    projectId: selectedProjectId.value || undefined,
    topicId: selectedTopicId.value || undefined,
    platformContentId: currentContent.value?.contentId || undefined,
  }
  try {
    const [taskRes, assetRes, characterRes, storyboardRes] = await Promise.all([
      listUnifiedTasks({ ...scope, limit: 12 }),
      listUnifiedAssets({ ...scope, limit: 12 }),
      listCharacterProfiles({ projectId: selectedProjectId.value || undefined }),
      listStoryboardRecords({ ...scope }),
    ])
    tasks.value = taskRes.data.items || []
    assets.value = assetRes.data.items || []
    characters.value = characterRes.data.items || []
    storyboards.value = storyboardRes.data.items || []
  } catch {
    tasks.value = []
    assets.value = []
    characters.value = []
    storyboards.value = []
  } finally {
    isPollingSupportData.value = false
  }
}

async function refreshSupportDataIfActive() {
  if (!hasRunningSupportItems.value) return
  await refreshSupportData()
  if (currentContent.value) {
    try {
      const res = await getPlatformContent(currentContent.value.contentId)
      await syncContent(res.data)
    } catch {
      // 轮询失败不打断编辑态。
    }
  }
}

async function ensureProject() {
  if (selectedProjectId.value) return selectedProjectId.value
  const res = await createIpProject(projectForm)
  projects.value.unshift(res.data)
  selectedProjectId.value = res.data.projectId
  return selectedProjectId.value
}

async function ensureTopic(projectId: number) {
  if (selectedTopicId.value) return selectedTopicId.value
  const title = generateForm.topicTitle.trim() || generateForm.theme.trim() || '未命名内容选题'
  const res = await createContentTopic(projectId, {
    title,
    inputSourceType: inputMode.value,
    targetPlatforms: [platformMeta.value.platform],
    priority: 'medium',
  })
  topics.value.unshift(res.data)
  selectedTopicId.value = res.data.topicId
  return selectedTopicId.value
}

async function handleGenerate() {
  if (!canGenerate.value) {
    setFeedback('error', '请先填写当前输入方式需要的主题、链接或原文。')
    return
  }
  isGenerating.value = true
  setFeedback('info', `正在生成${platformMeta.value.label}内容...`)
  try {
    const projectId = await ensureProject()
    const topicId = await ensureTopic(projectId)
    const payload = {
      projectId,
      topicId,
      projectName: projectForm.name,
      topicTitle: generateForm.topicTitle || generateForm.theme,
      inputType: inputMode.value,
      sourceUrl: generateForm.sourceUrl,
      rawText: generateForm.rawText,
      theme: generateForm.theme,
      promptTemplateId: selectedPromptTemplateId.value || undefined,
      textModelConfigId: selectedTextModelId.value || undefined,
      extraRequirements: generateForm.extraRequirements,
      targetPlatform: mode.value,
    }
    const res = mode.value === 'xiaohongshu' ? await generateXiaohongshuNote(payload) : await generateShortVideoScript(payload)
    await syncContent(res.data.content)
    selectedContentId.value = res.data.content.contentId
    setFeedback('success', res.message || '内容已生成并进入资产库。')
    await Promise.all([loadContents(), refreshSupportData()])
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '平台内容生成失败'))
  } finally {
    isGenerating.value = false
  }
}

async function openContent(contentId: number) {
  try {
    const res = await getPlatformContent(contentId)
    await syncContent(res.data)
    setFeedback('success', '已打开平台内容。')
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '打开平台内容失败'))
  }
}

async function syncContent(content: PlatformContentData) {
  currentContent.value = content
  selectedProjectId.value = content.projectId || selectedProjectId.value
  selectedTopicId.value = content.topicId || selectedTopicId.value
  Object.assign(editForm, {
    title: content.title || '',
    summary: content.summary || '',
    markdownSnapshot: content.markdownSnapshot || String(content.content?.export_text || content.content?.teleprompter_text || content.content?.script || content.content?.body || ''),
    coverPrompt: content.coverPrompt || '',
    tagsText: (content.tags || []).join('\n'),
  })
  storyboardForm.projectId = content.projectId
  storyboardForm.topicId = content.topicId
  storyboardForm.platformContentId = content.contentId
  storyboardForm.title = `${content.title || '未命名内容'}分镜`
}

async function handleSaveContent() {
  if (!currentContent.value) return
  isSaving.value = true
  try {
    const tags = editForm.tagsText.split('\n').map((item) => item.trim()).filter(Boolean)
    const res = await updatePlatformContent(currentContent.value.contentId, {
      title: editForm.title,
      summary: editForm.summary,
      content: { ...(currentContent.value.content || {}), edited_text: editForm.markdownSnapshot },
      markdownSnapshot: editForm.markdownSnapshot,
      coverPrompt: editForm.coverPrompt,
      imageSlots: currentContent.value.imageSlots || [],
      tags,
      status: 'editing',
    })
    await syncContent(res.data)
    setFeedback('success', res.message || '平台内容已保存。')
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '保存平台内容失败'))
  } finally {
    isSaving.value = false
  }
}

async function handleDeleteContent(item: PlatformContentData) {
  if (!window.confirm(`确认移除「${item.title || '未命名内容'}」吗？`)) return
  try {
    await deletePlatformContent(item.contentId)
    if (currentContent.value?.contentId === item.contentId) {
      currentContent.value = null
      selectedContentId.value = 0
    }
    setFeedback('success', '内容已从当前工作台移除。')
    await Promise.all([loadContents(), refreshSupportData(), loadWorkspaceOverview()])
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '移除内容失败'))
  }
}

async function handleExport() {
  if (!currentContent.value) return
  try {
    const res = await exportPlatformContent(currentContent.value.contentId)
    exportPackage.value = res.data
    await navigator.clipboard.writeText(res.data.copyText || contentPreview.value)
    setFeedback('success', '复制包已生成，文案已复制到剪贴板。')
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '导出复制包失败'))
  }
}

async function handleDownloadPackage() {
  if (!currentContent.value) return
  try {
    const blob = await downloadPlatformContentPackage(currentContent.value.contentId)
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = `${(currentContent.value.title || currentContent.value.platform || 'platform-content').replace(/[\\/:*?"<>|\s]+/g, '_')}.zip`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
    setFeedback('success', '下载包已生成，包含文案、manifest 和本地图片文件。')
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '下载包生成失败'))
  }
}

async function handleImportTeleprompter() {
  if (!currentContent.value) return
  try {
    const res = await importPlatformContentToTeleprompter({ platformContentId: currentContent.value.contentId, settings: { scrollSpeed: 6 } })
    setFeedback('success', `已导入提词器草稿 #${res.data.draft.draftId}。`)
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '导入提词器失败'))
  }
}

async function handleGenerateImage(slotIndex: number) {
  if (!currentContent.value) return
  const slot = imageSlots.value[slotIndex] || {}
  activeSlotIndex.value = slotIndex
  try {
    const res = await generatePlatformContentSlotImage(currentContent.value.contentId, slotIndex, {
      prompt: String(slot.prompt || editForm.coverPrompt || editForm.title),
      imageModelConfigId: selectedImageModelId.value || undefined,
      width: mode.value === 'xiaohongshu' ? 1080 : 720,
      height: mode.value === 'xiaohongshu' ? 1440 : 1280,
      insertToMarkdown: false,
    })
    await syncContent(res.data.content)
    setFeedback('success', res.message || '图片生成任务已提交。')
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '图片生成失败'))
  } finally {
    activeSlotIndex.value = -1
  }
}

async function handleAddImageUrl(slotIndex = -1) {
  if (!currentContent.value) return
  const imageUrl = window.prompt('请输入可访问的图片链接')?.trim()
  if (!imageUrl) return
  try {
    const res = await addPlatformContentImageAsset(currentContent.value.contentId, {
      imageUrl,
      slotIndex,
      insertToMarkdown: false,
      title: `${editForm.title || platformMeta.value.label}配图`,
      tags: [mode.value, platformMeta.value.contentType],
    })
    await syncContent(res.data.content)
    setFeedback('success', res.message || '图片链接已保存为素材。')
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '添加图片资产失败'))
  }
}

async function handleUploadImageFile(slotIndex: number, event: Event) {
  if (!currentContent.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const res = await uploadPlatformContentImageAsset(currentContent.value.contentId, {
      file,
      slotIndex,
      insertToMarkdown: false,
      title: `${editForm.title || platformMeta.value.label}上传图`,
      tags: [mode.value, platformMeta.value.contentType, 'upload'],
    })
    await syncContent(res.data.content)
    setFeedback('success', res.message || '图片文件已上传并进入资产库。')
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '上传图片失败'))
  } finally {
    input.value = ''
  }
}

async function openAssetFile(asset: any) {
  if (!asset?.assetId) return
  if (asset.url && !String(asset.url).startsWith('/api/assets/')) {
    window.open(asset.url, '_blank', 'noopener,noreferrer')
    return
  }
  try {
    const blob = await downloadUnifiedAssetFile(asset.assetId)
    const objectUrl = URL.createObjectURL(blob)
    window.open(objectUrl, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '打开资产文件失败'))
  }
}

async function handleSavePublishConfig() {
  if (!publishForm.name?.trim()) {
    setFeedback('error', '请填写发布配置名称。')
    return
  }
  try {
    const res = await createPlatformPublishConfig({ ...publishForm, platform: mode.value })
    setFeedback('success', res.message || '发布配置已保存。')
    Object.assign(publishForm, { platform: mode.value, name: '', accountLabel: '', apiBase: '', credentials: '', authType: 'manual', status: 'reserved', notes: '', isActive: true })
    await loadPublishConfigs()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '保存发布配置失败'))
  }
}

async function handleDeletePublishConfig(config: PlatformPublishConfigData) {
  if (!config.configId || !window.confirm(`确认删除发布配置「${config.name}」吗？`)) return
  try {
    await deletePlatformPublishConfig(config.configId)
    setFeedback('success', '发布配置已删除。')
    await loadPublishConfigs()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '删除发布配置失败'))
  }
}

async function handleCreateCharacter() {
  if (!characterForm.name?.trim()) {
    setFeedback('error', '请填写角色名称。')
    return
  }
  try {
    const res = await createCharacterProfile({ ...characterForm, projectId: selectedProjectId.value || 0 })
    setFeedback('success', res.message || '角色已保存。')
    Object.assign(characterForm, { projectId: 0, name: '', role: '', identity: '', personality: '', speakingStyle: '', catchphrase: '', referenceImages: [], profile: {}, status: 'active' })
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '保存角色失败'))
  }
}

async function handleDeleteCharacter(character: CharacterProfileData) {
  if (!character.characterId || !window.confirm(`确认删除角色「${character.name}」吗？`)) return
  try {
    await deleteCharacterProfile(character.characterId)
    setFeedback('success', '角色已删除。')
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '删除角色失败'))
  }
}

function seedStoryboardFromContent() {
  const text = contentPreview.value || editForm.markdownSnapshot
  const parts = text.split(/[\n。]/).map((item) => item.trim()).filter(Boolean).slice(0, 9)
  storyboardForm.frames = (parts.length ? parts : ['开场钩子', '核心观点', '结尾引导']).map((item, index) => ({
    shot: index + 1,
    duration: '3秒',
    visual: item,
    dialogue: item,
    prompt: `${mode.value}竖屏分镜，第${index + 1}镜：${item}`,
  }))
  setFeedback('info', '已按当前文案拆出基础分镜，可直接保存或继续编辑。')
}

async function handleSaveStoryboard() {
  if (!storyboardForm.title?.trim()) {
    setFeedback('error', '请填写分镜标题。')
    return
  }
  try {
    const res = await createStoryboardRecord({ ...storyboardForm, projectId: selectedProjectId.value || 0, topicId: selectedTopicId.value || 0, platformContentId: currentContent.value?.contentId || 0 })
    setFeedback('success', res.message || '分镜记录已保存。')
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '保存分镜失败'))
  }
}

async function handleDeleteStoryboard(storyboard: StoryboardRecordData) {
  if (!storyboard.storyboardId || !window.confirm(`确认删除分镜「${storyboard.title}」吗？`)) return
  try {
    await deleteStoryboardRecord(storyboard.storyboardId)
    setFeedback('success', '分镜记录已删除。')
    await refreshSupportData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '删除分镜失败'))
  }
}
</script>

<template>
  <div class="platform-studio">
    <header class="studio-hero">
      <div>
        <span class="section-eyebrow">平台内容</span>
        <h2>多平台内容工作台</h2>
        <p>在同一个 IP 项目下生成小红书图文、抖音/视频号口播，并整理素材、角色和分镜。</p>
      </div>
      <div class="hero-actions">
        <span v-if="hasRunningSupportItems" class="polling-chip">生成处理中</span>
        <button class="btn btn-ghost" :disabled="isPollingSupportData" @click="refreshSupportData">{{ isPollingSupportData ? '刷新中...' : '刷新资产' }}</button>
        <button class="btn btn-primary" :disabled="isGenerating" @click="handleGenerate">{{ isGenerating ? '生成中...' : `生成${platformMeta.label}` }}</button>
      </div>
    </header>

    <div v-if="feedback" class="studio-feedback" :class="feedback.type">{{ feedback.message }}</div>

    <section class="studio-card generate-card">
      <div class="platform-picker" aria-label="平台类型">
        <button
          v-for="card in platformCards"
          :key="card.key"
          class="platform-card"
          :class="{ active: mode === card.key }"
          type="button"
          @click="mode = card.key"
        >
          <span class="platform-badge">{{ card.badge }}</span>
          <strong>{{ card.title }}</strong>
          <span>{{ card.summary }}</span>
          <small>{{ card.nextStep }}</small>
        </button>
      </div>

      <div v-if="activePlatformCard" class="platform-focus-tip">
        <strong>当前平台：{{ activePlatformCard.title }}</strong>
        <span>{{ activePlatformCard.nextStep }}</span>
      </div>

      <div class="generate-grid">
        <div class="form-panel">
          <h3>项目与选题</h3>
          <label>IP 项目
            <select v-model.number="selectedProjectId" class="input">
              <option :value="0">自动创建默认项目</option>
              <option v-for="project in projects" :key="project.projectId" :value="project.projectId">{{ project.name }}</option>
            </select>
          </label>
          <label v-if="!selectedProjectId">新项目名称<input v-model="projectForm.name" class="input" /></label>
          <label v-if="selectedProjectId">内容选题
            <select v-model.number="selectedTopicId" class="input">
              <option :value="0">生成时自动创建选题</option>
              <option v-for="topic in topics" :key="topic.topicId" :value="topic.topicId">{{ topic.title }} · {{ topic.status }}</option>
            </select>
          </label>
          <label>选题标题<input v-model="generateForm.topicTitle" class="input" placeholder="例如：普通人如何搭建个人 IP 内容系统" /></label>
        </div>

        <div class="form-panel">
          <h3>素材输入</h3>
          <label>输入方式
            <select v-model="inputMode" class="input">
              <option value="topic">主题生成</option>
              <option value="url">链接二创</option>
              <option value="text">粘贴原文</option>
            </select>
          </label>
          <label v-if="inputMode === 'topic'">主题<input v-model="generateForm.theme" class="input" placeholder="一句话说明内容方向" /></label>
          <label v-else-if="inputMode === 'url'">链接<input v-model="generateForm.sourceUrl" class="input" placeholder="粘贴网页或文章链接" /></label>
          <label v-else>原文<textarea v-model="generateForm.rawText" class="input textarea" placeholder="粘贴文章、资料、笔记或卖点"></textarea></label>
          <label>补充要求<textarea v-model="generateForm.extraRequirements" class="input textarea compact" placeholder="语气、结构、禁用表达、目标人群等"></textarea></label>
        </div>

        <div class="form-panel">
          <h3>生成偏好</h3>
          <label>创作模板
            <select v-model.number="selectedPromptTemplateId" class="input">
              <option :value="0">使用默认模板</option>
              <option v-for="template in promptTemplates" :key="template.id" :value="template.id">{{ template.name }} · {{ template.version }}</option>
            </select>
          </label>
          <label>文案生成方式
            <select v-model.number="selectedTextModelId" class="input">
              <option :value="0">推荐设置</option>
              <option v-for="model in textModels" :key="model.id" :value="model.id || 0">{{ model.name }} · {{ model.provider }}</option>
            </select>
          </label>
          <label>图片生成方式
            <select v-model.number="selectedImageModelId" class="input">
              <option :value="0">推荐设置</option>
              <option v-for="model in imageModels" :key="model.id" :value="model.id || 0">{{ model.name }} · {{ model.provider }}</option>
            </select>
          </label>
        </div>
      </div>
    </section>

    <section class="studio-layout">
      <article class="studio-card editor-card">
        <div class="card-head">
          <div>
            <span class="section-eyebrow">内容编辑</span>
            <h3>{{ currentContent ? currentContent.title : '等待生成内容' }}</h3>
            <p>{{ currentContent ? `${formatTaskType(currentContent.contentType)} · ${formatStatus(currentContent.status)}` : '生成小红书或口播后，可在这里编辑、复制和进入下一步工具。' }}</p>
            <p v-if="currentContent" class="content-meta">{{ currentContent.platform }} · {{ currentContent.contentType }} · {{ currentContent.status }}</p>
          </div>
          <div class="card-actions">
            <button class="btn btn-ghost" :disabled="!currentContent || isSaving" @click="handleSaveContent">{{ isSaving ? '保存中...' : '保存' }}</button>
            <button class="btn btn-ghost" :disabled="!currentContent" @click="handleExport">复制/导出</button>
            <button class="btn btn-primary" :disabled="!currentContent" @click="handleDownloadPackage">下载 ZIP 包</button>
            <button class="btn btn-ghost" :disabled="!currentContent || mode === 'xiaohongshu'" @click="handleImportTeleprompter">导入提词器</button>
          </div>
          <p v-if="currentContent && imageSlots.length" class="download-hint">ZIP 包含文案、manifest、已上传本地图片；公网图片链接会写入 remote-images.json。</p>
        </div>

        <div v-if="currentContent" class="editor-grid">
          <label>标题<input v-model="editForm.title" class="input" /></label>
          <label>摘要/描述<textarea v-model="editForm.summary" class="input textarea compact"></textarea></label>
          <label>标签（一行一个）<textarea v-model="editForm.tagsText" class="input textarea compact"></textarea></label>
          <label>封面提示词<textarea v-model="editForm.coverPrompt" class="input textarea compact"></textarea></label>
          <label class="wide">正文/复制内容<textarea v-model="editForm.markdownSnapshot" class="input textarea content-area"></textarea></label>
        </div>
        <div v-else class="empty-box">选择历史内容或点击生成，内容会进入这里。</div>
      </article>

      <aside class="studio-side">
        <section class="studio-card side-card">
          <div class="list-head"><strong>最近内容</strong><button class="mini-link" @click="loadContents">刷新</button></div>
          <p v-if="!contents.length">暂无内容。</p>
          <article v-for="item in contents" :key="item.contentId" class="content-list-item" :class="{ active: selectedContentId === item.contentId }">
            <button class="content-open-btn" @click="selectedContentId = item.contentId">
              <strong>{{ item.title || '未命名内容' }}</strong>
            <span>{{ formatStatus(item.status) }} · {{ item.updatedAt?.slice(0, 10) }}</span>
            </button>
            <button class="mini-link danger" @click="handleDeleteContent(item)">移除</button>
          </article>
        </section>

        <section class="studio-card side-card">
          <div class="list-head"><strong>生成进度</strong><button class="mini-link" :disabled="isPollingSupportData" @click="refreshSupportData">{{ isPollingSupportData ? '刷新中' : '刷新' }}</button></div>
          <p v-if="!tasks.length">暂无生成进度。</p>
          <article v-for="task in tasks.slice(0, 6)" :key="task.taskId" class="compact-item">
            <span>{{ formatTaskType(task.taskType) }}</span>
            <strong>{{ formatStatus(task.status) }} · {{ task.progress }}%</strong>
            <small>{{ task.status === 'failed' ? '生成失败，可稍后重试。' : '正在处理内容生成。' }}</small>
          </article>
        </section>
      </aside>
    </section>

    <section class="studio-grid">
      <article class="studio-card">
        <div class="card-head compact">
          <div><h3>图片与配图</h3><p>小红书默认多图，口播默认封面图；生成、上传或选择图片后进入素材库。</p></div>
          <div class="card-actions">
            <label class="btn btn-ghost btn-sm upload-btn" :class="{ disabled: !currentContent }">
              上传图片
              <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" :disabled="!currentContent" @change="handleUploadImageFile(-1, $event)" />
            </label>
            <button class="btn btn-ghost btn-sm" :disabled="!currentContent" @click="handleAddImageUrl(-1)">添加图片链接</button>
          </div>
        </div>
        <div v-if="imageSlots.length" class="slot-grid">
          <article v-for="(slot, index) in imageSlots" :key="index" class="slot-card">
            <strong>{{ slot.purpose || `配图 ${index + 1}` }}</strong>
            <span>{{ slot.position || '未指定位置' }} · {{ slot.status || '待处理' }}</span>
            <p>{{ slot.prompt || '暂无提示词' }}</p>
            <button v-if="slot.assetId" class="mini-link" @click="openAssetFile({ assetId: slot.assetId, url: slot.imageUrl })">查看图片</button>
            <a v-else-if="slot.imageUrl" :href="slot.imageUrl" target="_blank" rel="noreferrer">查看图片</a>
            <div class="slot-actions">
              <button class="btn btn-ghost btn-sm" :disabled="activeSlotIndex === index" @click="handleGenerateImage(index)">生成</button>
              <label class="btn btn-ghost btn-sm upload-btn">
                上传
                <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" @change="handleUploadImageFile(index, $event)" />
              </label>
              <button class="btn btn-ghost btn-sm" @click="handleAddImageUrl(index)">使用图片链接</button>
            </div>
          </article>
        </div>
        <div v-else class="empty-box">当前内容暂无图片位，生成小红书内容后会出现首图和多图提示词。</div>
        <div class="asset-list">
          <article v-for="asset in assets.slice(0, 8)" :key="asset.assetId" class="compact-item">
            <span>{{ formatAssetType(asset.assetType) }}</span>
            <strong>{{ asset.title || '未命名素材' }}</strong>
            <button v-if="asset.url" class="mini-link" @click="openAssetFile(asset)">查看/下载</button>
          </article>
        </div>
      </article>

      <article v-if="isAdminUser" class="studio-card">
        <div class="card-head compact"><div><h3>平台发布设置</h3><p>用于管理员维护平台账号和发布连接。</p></div><button class="btn btn-primary btn-sm" @click="handleSavePublishConfig">保存设置</button></div>
        <div class="mini-form-grid">
          <label>配置名称<input v-model="publishForm.name" class="input" placeholder="如：小红书主账号" /></label>
          <label>账号标识<input v-model="publishForm.accountLabel" class="input" placeholder="账号昵称或主体" /></label>
          <label>发布服务地址<input v-model="publishForm.apiBase" class="input" placeholder="由管理员填写" /></label>
          <label>账号授权信息<input v-model="publishForm.credentials" class="input" type="password" placeholder="安全保存，列表不回显" /></label>
          <label class="wide">备注<textarea v-model="publishForm.notes" class="input textarea compact"></textarea></label>
        </div>
        <div class="config-list">
          <article v-for="config in publishConfigs" :key="config.configId" class="compact-item">
            <span>{{ config.platform }} · {{ formatStatus(config.status) }}</span>
            <strong>{{ config.name }} · {{ config.accountLabel || '未填账号' }}</strong>
            <small>{{ config.credentialsMasked ? '已完成授权' : '待配置授权' }}</small>
            <button class="mini-link danger" @click="handleDeletePublishConfig(config)">删除</button>
          </article>
        </div>
      </article>

      <article class="studio-card">
        <div class="card-head compact"><div><h3>人物角色库</h3><p>用于管理短视频角色设定，便于后续生成剧情和分镜。</p></div><button class="btn btn-primary btn-sm" @click="handleCreateCharacter">保存角色</button></div>
        <div class="mini-form-grid">
          <label>角色名<input v-model="characterForm.name" class="input" /></label>
          <label>角色身份<input v-model="characterForm.identity" class="input" /></label>
          <label>角色定位<input v-model="characterForm.role" class="input" /></label>
          <label>口头禅<input v-model="characterForm.catchphrase" class="input" /></label>
          <label class="wide">性格<textarea v-model="characterForm.personality" class="input textarea compact"></textarea></label>
          <label class="wide">说话风格<textarea v-model="characterForm.speakingStyle" class="input textarea compact"></textarea></label>
        </div>
        <div class="config-list">
          <article v-for="character in characters" :key="character.characterId" class="compact-item">
            <span>{{ character.role || '角色' }} · {{ formatStatus(character.status) }}</span>
            <strong>{{ character.name }}</strong>
            <small>{{ character.identity || character.personality || '未补充设定' }}</small>
            <button class="mini-link danger" @click="handleDeleteCharacter(character)">删除</button>
          </article>
        </div>
      </article>

      <article class="studio-card">
        <div class="card-head compact"><div><h3>分镜记录</h3><p>将口播或剧情拆成分镜表，用于短大片或剧本短视频创作。</p></div><button class="btn btn-primary btn-sm" @click="handleSaveStoryboard">保存分镜</button></div>
        <div class="mini-form-grid">
          <label>分镜标题<input v-model="storyboardForm.title" class="input" /></label>
          <label>类型<select v-model="storyboardForm.storyboardType" class="input"><option value="drama">剧本短视频</option><option value="cinematic">短大片</option><option value="talking_head">口播</option></select></label>
          <button class="btn btn-ghost wide" :disabled="!currentContent" @click="seedStoryboardFromContent">从当前文案拆分镜</button>
        </div>
        <div v-if="storyboardForm.frames?.length" class="storyboard-preview">
          <article v-for="frame in storyboardForm.frames" :key="frame.shot" class="compact-item">
            <span>第 {{ frame.shot }} 镜 · {{ frame.duration }}</span>
            <strong>{{ frame.visual }}</strong>
            <small>{{ frame.prompt }}</small>
          </article>
        </div>
        <div class="config-list">
          <article v-for="storyboard in storyboards" :key="storyboard.storyboardId" class="compact-item">
            <span>{{ formatStoryboardType(storyboard.storyboardType) }} · {{ formatStatus(storyboard.status) }}</span>
            <strong>{{ storyboard.title }}</strong>
            <small>{{ storyboard.frames?.length || 0 }} 个镜头</small>
            <button class="mini-link danger" @click="handleDeleteStoryboard(storyboard)">删除</button>
          </article>
        </div>
      </article>
    </section>

    <section v-if="exportPackage" class="studio-card export-card">
      <div class="card-head compact"><div><h3>复制/下载包</h3><p>已整理好复制文本和图片清单，可继续下载保存。</p></div></div>
      <div class="export-summary">
        <article>
          <span>正文文件</span>
          <strong>{{ exportPackage.downloadManifest?.files?.length || 0 }} 个</strong>
        </article>
        <article>
          <span>图片素材</span>
          <strong>{{ exportPackage.downloadManifest?.images?.length || 0 }} 张</strong>
        </article>
        <article>
          <span>下载状态</span>
          <strong>已准备</strong>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.platform-studio {
  display: grid;
  gap: 16px;
  min-height: 100%;
  overflow: visible;
  padding: 0;
  background: transparent;
}

.studio-hero,
.studio-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.studio-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 22px;
}

.studio-hero h2,
.studio-card h3 {
  margin: 4px 0 6px;
  color: #0f172a;
  font-weight: 950;
  letter-spacing: -0.04em;
}

.studio-hero h2 { font-size: 30px; }
.studio-card h3 { font-size: 20px; }

.studio-hero p,
.studio-card p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.hero-actions,
.card-actions,
.card-head,
.list-head,
.slot-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-head,
.list-head {
  justify-content: space-between;
}

.card-head.compact {
  align-items: flex-start;
}

.studio-feedback {
  padding: 12px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 850;
}

.studio-feedback.success { background: #dcfce7; color: #166534; }
.studio-feedback.error { background: #fee2e2; color: #991b1b; }
.studio-feedback.info { background: #dbeafe; color: #1e40af; }

.polling-chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 10px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 999px;
  background: rgba(239, 246, 255, 0.9);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 900;
}

.generate-card,
.editor-card,
.side-card,
.studio-grid .studio-card,
.export-card {
  padding: 18px;
}

.content-meta {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 12px;
}

.download-hint {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.platform-picker {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.platform-card,
.content-open-btn,
.mini-link {
  border: 0;
  font: inherit;
  cursor: pointer;
  text-align: left;
}

.platform-card {
  display: grid;
  gap: 8px;
  min-height: 148px;
  padding: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
  color: #0f172a;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.platform-card:hover,
.platform-card.active {
  border-color: rgba(37, 99, 235, 0.42);
  box-shadow: 0 16px 36px rgba(37, 99, 235, 0.1);
  transform: translateY(-1px);
}

.platform-card.active {
  background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
}

.platform-badge {
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 900;
}

.platform-card strong {
  font-size: 18px;
  font-weight: 950;
  letter-spacing: -0.03em;
}

.platform-card span,
.platform-card small {
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.platform-card small {
  color: #2563eb;
  font-weight: 800;
}

.platform-focus-tip {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-top: 14px;
  padding: 12px 16px;
  border: 1px solid rgba(37, 99, 235, 0.14);
  border-radius: 16px;
  background: rgba(239, 246, 255, 0.72);
}

.platform-focus-tip strong {
  color: #0f172a;
  font-size: 14px;
}

.platform-focus-tip span {
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.generate-grid,
.studio-grid,
.mini-form-grid,
.editor-grid {
  display: grid;
  gap: 14px;
}

.generate-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 16px;
}

.generate-grid .form-panel:nth-child(3) {
  grid-column: 1 / -1;
}

.form-panel {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: 18px;
  background: #f8fafc;
}

label {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.input {
  width: 100%;
  min-height: 40px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  font-size: 13px;
}

.textarea {
  min-height: 92px;
  resize: vertical;
}

.textarea.compact {
  min-height: 68px;
}

.content-area {
  min-height: 280px;
  line-height: 1.75;
}

.studio-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  align-items: start;
}

.studio-side {
  display: grid;
  gap: 16px;
}

.editor-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 16px;
}

.wide {
  grid-column: 1 / -1;
}

.content-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: #fff;
  color: #0f172a;
  text-align: left;
}

.content-open-btn {
  display: grid;
  gap: 4px;
  min-width: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.retention-card {
  display: grid;
  gap: 6px;
  padding: 14px 18px;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.retention-card strong {
  color: #0f172a;
}

.content-list-item.active {
  border-color: rgba(37, 99, 235, 0.28);
  background: rgba(37, 99, 235, 0.06);
}

.content-list-item span,
.compact-item span,
.compact-item small,
.slot-card span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.studio-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.slot-grid,
.asset-list,
.config-list,
.storyboard-preview {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.slot-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.slot-card,
.compact-item,
.empty-box {
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: #f8fafc;
}

.slot-card {
  display: grid;
  gap: 8px;
}

.compact-item {
  display: grid;
  gap: 3px;
}

.compact-item strong,
.slot-card strong {
  color: #0f172a;
  font-size: 13px;
}

.mini-form-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 12px;
}

.empty-box {
  margin-top: 12px;
  color: #64748b;
  line-height: 1.7;
}

.mini-link {
  width: fit-content;
  padding: 0;
  background: transparent;
  color: #2563eb;
  font-size: 12px;
  font-weight: 900;
}

.upload-btn {
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.upload-btn.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.upload-btn input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.mini-link.danger {
  color: #dc2626;
}

.export-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.export-summary article {
  display: grid;
  gap: 8px;
  padding: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: #f8fafc;
}

.export-summary span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.export-summary strong {
  color: #0f172a;
  font-size: 22px;
}

@media (max-width: 1100px) {
  .platform-picker {
    grid-template-columns: 1fr;
  }

  .platform-focus-tip {
    flex-direction: column;
    align-items: stretch;
  }

  .generate-grid,
  .studio-layout,
  .studio-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .platform-studio {
    padding: 0;
  }

  .studio-hero,
  .card-head,
  .hero-actions,
  .card-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .editor-grid,
  .mini-form-grid,
  .export-summary {
    grid-template-columns: 1fr;
  }
}
</style>

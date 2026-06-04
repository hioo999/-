<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PlatformContentStudio from './PlatformContentStudio.vue'
import TeleprompterPanel from './TeleprompterPanel.vue'
import WechatArticlePublisher from './WechatArticlePublisher.vue'
import {
  parseText,
  parseUrl,
  reportTeleprompterEvent,
} from '../api'
import { createUnifiedAsset, downloadUnifiedAssetFile, listUnifiedAssets } from '../api/assets.api'
import { listGenerationRecords, listUnifiedTasks, retryUnifiedTask, type GenerationRecordData } from '../api/tasks.api'
import {
  createContentTopic,
  createIpProject,
  listIpProjects,
  listPlatformContents,
  listProjectTopics,
  type ContentTopicData,
  type IpProjectData,
  type PlatformContentData,
} from '../api/platformContent.api'
import { listWechatDrafts, type WechatDraftRecord } from '../api/wechat.api'
import { modePathMap } from '../stores/workspace'

type ProductionTab = 'overview' | 'wechat' | 'platform' | 'teleprompter' | 'advanced'
type MaterialInputMode = 'topic' | 'url' | 'text'
type ProductionTaskKey = 'talkingVideo' | 'wechatArticle' | 'liveScript' | 'reversalDrama'
type WorkflowActionKind = 'createProject' | 'createTopic' | 'saveMaterial' | 'openProduction' | 'reviewDelivery'

interface ProductionTaskOption {
  key: ProductionTaskKey
  label: string
  badge: string
  summary: string
  path: string
  defaultTopic: string
  exampleTitle: string
  exampleMaterial: string
  defaultInputMode: MaterialInputMode
  targetTab: ProductionTab
  targetPlatforms: string[]
  ctaLabel: string
}

interface WorkflowAction {
  kind: WorkflowActionKind
  title: string
  desc: string
  label: string
}

interface ActiveUser {
  name?: string
  email?: string
  token?: string
  isGuest?: boolean
  is_admin?: boolean
}

const props = defineProps<{
  initialTitle?: string
  initialContent?: string
  currentUser?: ActiveUser
}>()

const router = useRouter()
const activeTab = ref<ProductionTab>('overview')
const activeTaskKey = ref<ProductionTaskKey>('talkingVideo')
const assetFilter = ref<'all' | 'prompt'>('all')
const previewAssetId = ref(0)
const selectedProjectId = ref(0)
const selectedTopicId = ref(0)
const isLoading = ref(false)
const isCreatingProject = ref(false)
const isCreatingTopic = ref(false)
const isSavingMaterial = ref(false)
const isRunningGuideAction = ref(false)
const isRetryingTaskId = ref(0)
const feedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const projects = ref<IpProjectData[]>([])
const topics = ref<ContentTopicData[]>([])
const platformContents = ref<PlatformContentData[]>([])
const tasks = ref<any[]>([])
const assets = ref<any[]>([])
const generationRecords = ref<GenerationRecordData[]>([])
const drafts = ref<WechatDraftRecord[]>([])
let pollTimer: number | null = null
const knownDeliveryKeys = ref(new Set<string>())
let deliveryTrackingReady = false
const lastReportedWorkflowStep = ref('')

const projectForm = reactive({
  name: '默认 IP 项目',
  ipType: 'personal_ip',
  positioning: '',
  targetAudience: '',
  defaultPlatforms: ['wechat', 'xiaohongshu', 'douyin'],
  voiceStyle: {},
})

const topicForm = reactive({
  title: props.initialTitle || '未命名内容选题',
  inputSourceType: 'topic',
  targetPlatforms: ['wechat', 'xiaohongshu', 'douyin'],
  priority: 'medium',
})

const materialForm = reactive({
  inputMode: 'topic' as MaterialInputMode,
  title: props.initialTitle || '',
  topic: props.initialTitle || '',
  sourceUrl: '',
  rawText: props.initialContent || '',
  extractedContent: props.initialContent || '',
})

const selectedProject = computed(() => projects.value.find((item) => item.projectId === selectedProjectId.value))
const selectedTopic = computed(() => topics.value.find((item) => item.topicId === selectedTopicId.value))
const teleprompterUser = computed(() => props.currentUser
  ? {
      name: props.currentUser.name || '用户',
      email: props.currentUser.email || '',
      token: props.currentUser.token,
      isGuest: props.currentUser.isGuest,
    }
  : undefined)
const canOpenPromptTool = computed(() => props.currentUser?.is_admin === true)
const runningTasks = computed(() => tasks.value.filter((task) => ['pending', 'running', 'retrying'].includes(String(task.status || ''))))
const failedTasks = computed(() => tasks.value.filter((task) => String(task.status || '') === 'failed'))
const visibleAssets = computed(() => assetFilter.value === 'prompt'
  ? assets.value.filter((asset) => asset.sourceType === 'prompt_tool' || Boolean(getAssetTextContent(asset)))
  : assets.value)
const contentInitialTitle = computed(() => selectedTopic.value?.title || materialForm.title || props.initialTitle || '未命名平台内容')
const contentInitialContent = computed(() => materialForm.extractedContent || materialForm.rawText || materialForm.topic || props.initialContent || '')
const hasActiveWork = computed(() => Boolean(selectedProjectId.value && selectedTopicId.value))
const hasSavedMaterial = computed(() => assets.value.some((asset) => asset.assetType === 'source_material'))
const currentMaterialReady = computed(() => {
  if (hasSavedMaterial.value) return true
  if (materialForm.inputMode === 'topic') return Boolean(materialForm.topic.trim())
  if (materialForm.inputMode === 'url') return Boolean(materialForm.sourceUrl.trim())
  return Boolean(materialForm.rawText.trim())
})

const productionTasks: ProductionTaskOption[] = [
  {
    key: 'talkingVideo',
    label: '生成一条口播视频',
    badge: '口播',
    summary: '从主题或素材生成可录制口播稿，再进入提词器或出片。',
    path: '主题/素材 - 口播文案 - 提词器/出片',
    defaultTopic: '生成一条适合短视频平台的口播内容',
    exampleTitle: '如何用 AI 提升个人 IP 内容生产效率',
    exampleMaterial: '我是一名个人 IP 内容创作者，希望把日常经验快速整理成短视频口播稿，核心观点是 AI 可以帮我减少选题、写稿和改稿时间，但最终表达仍要保留个人风格。',
    defaultInputMode: 'topic',
    targetTab: 'platform',
    targetPlatforms: ['douyin', 'video_channel', 'xiaohongshu'],
    ctaLabel: '开始口播生产',
  },
  {
    key: 'wechatArticle',
    label: '做一篇公众号文章',
    badge: '公众号',
    summary: '把素材二创成长文，完成排版预览并发送公众号草稿箱。',
    path: '素材 - 二创长文 - 公众号排版 - 草稿箱',
    defaultTopic: '把素材整理成一篇公众号图文',
    exampleTitle: '从一篇资料整理成企业 IP 长文',
    exampleMaterial: '企业想通过公众号建立专业信任，但团队资料分散在销售话术、案例复盘和产品介绍里。请整理成一篇适合公众号发布的文章，结构要有痛点、方法、案例和行动建议。',
    defaultInputMode: 'text',
    targetTab: 'wechat',
    targetPlatforms: ['wechat'],
    ctaLabel: '进入公众号闭环',
  },
  {
    key: 'liveScript',
    label: '准备一场直播话术',
    badge: '直播',
    summary: '围绕产品、活动或观点生成直播开场、促单和互动话术。',
    path: '产品/活动 - 直播脚本 - 在线提词器',
    defaultTopic: '准备一场直播间可直接使用的话术',
    exampleTitle: '618 活动直播开场和促单话术',
    exampleMaterial: '直播主题是 618 限时活动，产品是一套 AI 内容生产工具。需要开场留人、福利说明、核心卖点、互动提问和促单话术，语气要专业但有紧迫感。',
    defaultInputMode: 'topic',
    targetTab: 'teleprompter',
    targetPlatforms: ['douyin', 'video_channel'],
    ctaLabel: '准备直播话术',
  },
  {
    key: 'reversalDrama',
    label: '生成一条反转短剧',
    badge: '短剧',
    summary: '从产品、痛点和角色出发，生成剧情脚本、分镜和高级视频生产方案。',
    path: '产品/痛点 - 剧情脚本 - 分镜 - 高级视频',
    defaultTopic: '设计一条带反转钩子的剧情短片',
    exampleTitle: '客户不信任 AI 工具，最后被效率反转',
    exampleMaterial: '角色 A 是传统内容团队负责人，认为 AI 写出来的内容没灵魂；角色 B 用 AI 内容中心把素材、脚本、提词和发布串成闭环，最后用同样素材半小时完成一条可发布内容。',
    defaultInputMode: 'topic',
    targetTab: 'advanced',
    targetPlatforms: ['douyin', 'video_channel'],
    ctaLabel: '规划反转短剧',
  },
]

const platformLabelMap: Record<string, string> = {
  wechat: '公众号',
  xiaohongshu: '小红书',
  douyin: '抖音',
  video_channel: '视频号',
}

const selectedProductionTask = computed(() => productionTasks.find((task) => task.key === activeTaskKey.value) || productionTasks[0])
const workflowSteps = computed(() => {
  const hasGeneratedContent = platformContents.value.length > 0
  const hasDeliveryRecord = drafts.value.length > 0 || assets.value.some((asset) => ['video', 'publish_record', 'wechat_draft'].includes(String(asset.assetType || '')))
  return [
    { label: '选择任务', desc: selectedProductionTask.value.label, done: true, current: false },
    { label: '建立 IP 档案', desc: selectedProject.value?.name || '先选择或创建 IP 项目', done: Boolean(selectedProjectId.value), current: !selectedProjectId.value },
    { label: '创建内容选题', desc: selectedTopic.value?.title || selectedProductionTask.value.defaultTopic, done: Boolean(selectedTopicId.value), current: Boolean(selectedProjectId.value && !selectedTopicId.value) },
    { label: '输入素材', desc: '填写主题、链接或原文', done: hasSavedMaterial.value, current: hasActiveWork.value && !hasSavedMaterial.value },
    { label: '生成与打磨', desc: selectedProductionTask.value.path, done: hasGeneratedContent, current: hasActiveWork.value && hasSavedMaterial.value && !hasGeneratedContent },
    { label: '交付发布', desc: '提词录制、AI 出片、公众号排版或草稿箱', done: hasDeliveryRecord, current: hasGeneratedContent && !hasDeliveryRecord },
  ]
})
const nextWorkflowAction = computed<WorkflowAction>(() => {
  if (!selectedProjectId.value) {
    return {
      kind: 'createProject',
      title: '当前该做：建立 IP 项目',
      desc: '先创建或选择一个 IP 项目，也可以在下方补充定位。',
      label: '创建 IP 项目',
    }
  }
  if (!selectedTopicId.value) {
    return {
      kind: 'createTopic',
      title: '当前该做：创建内容选题',
      desc: `这个选题会承载「${selectedProductionTask.value.label}」的素材、生成内容和交付记录。`,
      label: '创建内容选题',
    }
  }
  if (!hasSavedMaterial.value) {
    return {
      kind: 'saveMaterial',
      title: '当前该做：输入并保存素材',
      desc: '先输入主题、链接或原文，后续生成会围绕这些素材展开。',
      label: currentMaterialReady.value ? '保存素材' : '先填写素材',
    }
  }
  if (!platformContents.value.length) {
    return {
      kind: 'openProduction',
      title: '当前该做：进入内容生成',
      desc: `素材已准备好，下一步进入「${selectedProductionTask.value.label}」对应的生产模块。`,
      label: selectedProductionTask.value.ctaLabel,
    }
  }
  return {
    kind: 'reviewDelivery',
    title: '当前该做：检查交付出口',
    desc: '已有平台内容，继续完成提词录制、AI 出片、公众号排版或草稿箱发布，并查看资产记录。',
    label: '查看交付记录',
  }
})
const quickStartSteps = computed(() => [
  { label: '第 1 步', title: '选任务', desc: selectedProductionTask.value.label },
  { label: '第 2 步', title: '用示例填素材', desc: selectedProductionTask.value.exampleTitle },
  { label: '第 3 步', title: '点下一步', desc: nextWorkflowAction.value.label },
])
const currentWorkflowStepLabel = computed(() => {
  const current = workflowSteps.value.find((step) => step.current)
  if (current) return current.label
  if (workflowSteps.value.every((step) => step.done)) return '交付发布'
  return workflowSteps.value.find((step) => !step.done)?.label || '选择任务'
})

function reportProductionMetric(eventName: string, properties: Record<string, unknown> = {}) {
  reportTeleprompterEvent({
    eventName,
    eventTime: new Date().toISOString(),
    sessionId: `${props.currentUser?.email || 'guest'}:${selectedProjectId.value || 0}:${selectedTopicId.value || 0}`,
    properties: {
      source: 'production_center',
      taskKey: activeTaskKey.value,
      projectId: selectedProjectId.value || undefined,
      topicId: selectedTopicId.value || undefined,
      ...properties,
    },
  }).catch(() => {
    // 埋点失败不影响生产主流程。
  })
}

function reportTargetTabOpened(tab: ProductionTab) {
  if (tab === 'overview') return
  reportProductionMetric('production_target_tab_opened', { tab })
}

function trackDeliveryRecords() {
  const deliveryAssetTypes = new Set(['video', 'publish_record', 'wechat_draft'])
  const nextKeys = new Set<string>()
  for (const draft of drafts.value) {
    if (draft.status !== 'sent') continue
    nextKeys.add(`draft:${draft.draftId}`)
  }
  for (const asset of assets.value) {
    if (!deliveryAssetTypes.has(String(asset.assetType || ''))) continue
    nextKeys.add(`asset:${asset.assetId}`)
  }
  if (!deliveryTrackingReady) {
    knownDeliveryKeys.value = nextKeys
    deliveryTrackingReady = true
    return
  }
  for (const key of nextKeys) {
    if (knownDeliveryKeys.value.has(key)) continue
    knownDeliveryKeys.value.add(key)
    const [kind, id] = key.split(':')
    reportProductionMetric('production_delivery_completed', {
      deliveryKind: kind,
      deliveryId: id,
    })
  }
}

const tabItems: Array<{ key: ProductionTab; label: string; desc: string }> = [
  { key: 'overview', label: '选题总览', desc: '项目、选题、素材和内容统一看板' },
  { key: 'wechat', label: '公众号闭环', desc: '文章生成、排版、封面、草稿箱' },
  { key: 'platform', label: '小红书/口播', desc: '小红书图文、抖音/视频号口播' },
  { key: 'teleprompter', label: '提词器', desc: '把口播稿带入录制或直播' },
  { key: 'advanced', label: '高级视频', desc: '短大片和剧本短视频' },
]

const statusCards = computed(() => [
  { label: '当前项目', value: selectedProject.value?.name || '未选择', hint: selectedProject.value?.ipType || '先选择或创建 IP 项目' },
  { label: '当前选题', value: selectedTopic.value?.title || '未选择', hint: selectedTopic.value?.status || '选题承载跨平台内容' },
  { label: '平台内容', value: String(platformContents.value.length), hint: '公众号、小红书、口播等内容' },
  { label: '生成进度', value: `${runningTasks.value.length} 进行中 / ${failedTasks.value.length} 待处理`, hint: '内容与图片生成状态' },
  { label: '素材资产', value: String(assets.value.length), hint: '素材、文案、图片和视频' },
])

function formatPlatformLabel(platform: string) {
  return platformLabelMap[platform] || platform
}

const taskTypeLabelMap: Record<string, string> = {
  wechat_article_generate: '文章生成',
  wechat_cover_generate: '封面生成',
  wechat_slot_image_generate: '正文配图',
  xiaohongshu_note: '小红书内容',
  short_video_script: '口播内容',
  image_generation: '图片生成',
  video_generation: '视频生成',
  text_generation: '内容生成',
}

const statusLabelMap: Record<string, string> = {
  pending: '排队中',
  running: '生成中',
  retrying: '重试中',
  completed: '已完成',
  success: '已完成',
  failed: '待处理',
  cancelled: '已取消',
  draft: '草稿',
  editing: '编辑中',
  ready: '可使用',
}

const assetTypeLabelMap: Record<string, string> = {
  image: '图片素材',
  cover: '封面素材',
  source_material: '选题素材',
  platform_content: '内容素材',
  video: '视频素材',
  wechat_draft: '公众号草稿',
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

watch(selectedProjectId, async () => {
  selectedTopicId.value = 0
  await Promise.all([loadTopics(), refreshContextData()])
})

watch(selectedTopicId, async () => {
  await refreshContextData()
})

watch(currentWorkflowStepLabel, (step) => {
  if (!step || step === lastReportedWorkflowStep.value) return
  lastReportedWorkflowStep.value = step
  reportProductionMetric('production_step_reached', { step })
}, { immediate: true })

onMounted(async () => {
  await loadInitialData()
  pollTimer = window.setInterval(() => {
    if (runningTasks.value.length) void refreshContextData()
  }, 4000)
})

onUnmounted(() => {
  if (pollTimer) window.clearInterval(pollTimer)
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

async function loadInitialData() {
  isLoading.value = true
  try {
    await loadProjects()
    await loadTopics()
    await refreshContextData()
  } finally {
    isLoading.value = false
  }
}

async function loadProjects() {
  try {
    const res = await listIpProjects()
    projects.value = res.data.items || []
    if (!selectedProjectId.value && projects.value.length) selectedProjectId.value = projects.value[0].projectId
  } catch (err: any) {
    projects.value = []
    setFeedback('error', getErrorMessage(err, 'IP 项目加载失败'))
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
    if (!selectedTopicId.value && topics.value.length) selectedTopicId.value = topics.value[0].topicId
  } catch (err: any) {
    topics.value = []
    setFeedback('error', getErrorMessage(err, '内容选题加载失败'))
  }
}

async function refreshContextData() {
  const projectId = selectedProjectId.value || undefined
  const topicId = selectedTopicId.value || undefined
  try {
    const [contentRes, taskRes, assetRes, recordRes, draftRes] = await Promise.all([
      listPlatformContents({ projectId, topicId, limit: 30 }),
      listUnifiedTasks({ projectId, topicId, limit: 30 }),
      listUnifiedAssets({ projectId, topicId, limit: 30 }),
      listGenerationRecords({ projectId, topicId, limit: 20 }),
      listWechatDrafts({ pageSize: 8 }),
    ])
    platformContents.value = contentRes.data.items || []
    tasks.value = taskRes.data.items || []
    assets.value = assetRes.data.items || []
    generationRecords.value = recordRes.data.items || []
    drafts.value = draftRes.data.items || []
    trackDeliveryRecords()
  } catch (err: any) {
    setFeedback('error', '内容刷新失败，请稍后重试。')
  }
}

async function handleCreateProject() {
  if (!projectForm.name.trim()) {
    setFeedback('error', '请填写 IP 项目名称。')
    return
  }
  isCreatingProject.value = true
  try {
    const res = await createIpProject({ ...projectForm, name: projectForm.name.trim() })
    projects.value.unshift(res.data)
    selectedProjectId.value = res.data.projectId
    setFeedback('success', 'IP 项目已创建。')
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '创建 IP 项目失败'))
  } finally {
    isCreatingProject.value = false
  }
}

async function handleCreateTopic() {
  if (!selectedProjectId.value) {
    setFeedback('error', '请先选择或创建 IP 项目。')
    return
  }
  const title = topicForm.title.trim() || materialForm.title.trim() || materialForm.topic.trim()
  if (!title) {
    setFeedback('error', '请填写内容选题名称。')
    return
  }
  isCreatingTopic.value = true
  try {
    const res = await createContentTopic(selectedProjectId.value, {
      title,
      inputSourceType: materialForm.inputMode,
      targetPlatforms: topicForm.targetPlatforms,
      priority: topicForm.priority,
    })
    topics.value.unshift(res.data)
    selectedTopicId.value = res.data.topicId
    setFeedback('success', '内容选题已创建。')
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '创建内容选题失败'))
  } finally {
    isCreatingTopic.value = false
  }
}

async function ensureProductionContext() {
  if (!selectedProjectId.value) await handleCreateProject()
  if (!selectedProjectId.value) return false
  if (!selectedTopicId.value) await handleCreateTopic()
  return Boolean(selectedProjectId.value && selectedTopicId.value)
}

async function handleSaveMaterial() {
  if (!(await ensureProductionContext())) return
  isSavingMaterial.value = true
  setFeedback('info', '正在保存素材到当前选题...')
  try {
    let extracted = ''
    let sourceTitle = materialForm.title.trim() || selectedTopic.value?.title || '选题素材'
    if (materialForm.inputMode === 'topic') {
      extracted = materialForm.topic.trim()
      sourceTitle = materialForm.title.trim() || extracted.slice(0, 32) || sourceTitle
    } else if (materialForm.inputMode === 'url') {
      const res = await parseUrl(materialForm.sourceUrl.trim())
      extracted = String(res.data?.content || res.data?.text || res.data?.summary || materialForm.sourceUrl)
      sourceTitle = String(res.data?.title || sourceTitle)
    } else {
      const res = await parseText(materialForm.rawText.trim())
      extracted = String(res.data?.content || res.data?.text || res.data?.summary || materialForm.rawText)
    }

    materialForm.extractedContent = extracted
    await createUnifiedAsset({
      assetType: 'source_material',
      sourceType: materialForm.inputMode,
      title: sourceTitle,
      url: materialForm.inputMode === 'url' ? materialForm.sourceUrl.trim() : '',
      projectId: selectedProjectId.value,
      topicId: selectedTopicId.value,
      metadata: {
        source: 'production_center_material_panel',
        inputMode: materialForm.inputMode,
        topic: materialForm.topic,
        rawText: materialForm.rawText,
        extractedContent: extracted,
      },
      tags: ['production-center', materialForm.inputMode],
    })
    setFeedback('success', '素材已保存到当前选题资产库。')
    reportProductionMetric('production_material_saved', {
      inputMode: materialForm.inputMode,
      title: sourceTitle,
    })
    await refreshContextData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '素材保存失败'))
  } finally {
    isSavingMaterial.value = false
  }
}

async function handleRetryTask(task: any) {
  if (!task?.taskId) return
  isRetryingTaskId.value = task.taskId
  try {
    const res = await retryUnifiedTask(task.taskId)
    setFeedback(res.code === 0 ? 'success' : 'error', res.message || '任务已提交重试。')
    await refreshContextData()
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '任务重试失败'))
  } finally {
    isRetryingTaskId.value = 0
  }
}

async function openAsset(asset: any) {
  if (!asset) return
  const textContent = getAssetTextContent(asset)
  if (textContent) {
    previewAssetId.value = previewAssetId.value === asset.assetId ? 0 : asset.assetId
    return
  }
  if (asset.url && !String(asset.url).startsWith('/api/assets/')) {
    window.open(asset.url, '_blank', 'noopener,noreferrer')
    return
  }
  if (!asset.assetId) return
  try {
    const blob = await downloadUnifiedAssetFile(asset.assetId)
    const objectUrl = URL.createObjectURL(blob)
    window.open(objectUrl, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '打开资产失败'))
  }
}

function getAssetTextContent(asset: any) {
  const metadata = asset?.metadata || {}
  return String(metadata.prompt || metadata.extractedContent || metadata.rawText || metadata.topic || '').trim()
}

function getPromptRoleLabel(asset: any) {
  const role = String(asset?.metadata?.role || asset?.metadata?.contentType || asset?.sourceType || '')
  const labels: Record<string, string> = {
    video_aip_prompt_package: 'AIP 总包',
    video_aip_step: 'AIP 步骤',
    video_prompts: '视频提示词',
    storyboard_prompt: '分镜提示词',
    cover_prompt: '封面提示词',
    prompt_tool: '提示词素材',
  }
  return labels[role] || '文本素材'
}

function copyAssetText(asset: any) {
  const textContent = getAssetTextContent(asset)
  if (!textContent) return
  navigator.clipboard.writeText(textContent)
    .then(() => setFeedback('success', '提示词素材已复制。'))
    .catch(() => setFeedback('error', '复制失败，请打开素材后手动复制。'))
}

function applyAssetAsMaterial(asset: any) {
  const textContent = getAssetTextContent(asset)
  if (!textContent) return
  materialForm.inputMode = 'text'
  materialForm.title = asset.title || materialForm.title
  materialForm.rawText = textContent
  materialForm.extractedContent = textContent
  setFeedback('success', '已把该提示词素材填入素材输入区。')
}

function selectProductionTask(task: ProductionTaskOption) {
  activeTaskKey.value = task.key
  materialForm.inputMode = task.defaultInputMode
  topicForm.targetPlatforms = [...task.targetPlatforms]
  if (!selectedTopicId.value && (!topicForm.title.trim() || topicForm.title === '未命名内容选题')) {
    topicForm.title = task.defaultTopic
  }
  if (task.defaultInputMode === 'topic' && !materialForm.topic.trim()) {
    materialForm.topic = task.defaultTopic
  }
  reportProductionMetric('production_task_selected', {
    taskKey: task.key,
    taskLabel: task.label,
    targetTab: task.targetTab,
  })
}

function useSelectedTaskExample() {
  const task = selectedProductionTask.value
  selectProductionTask(task)
  reportProductionMetric('production_example_started', {
    taskKey: task.key,
    exampleTitle: task.exampleTitle,
  })
  if (!projectForm.name.trim() || projectForm.name === '默认 IP 项目') {
    projectForm.name = `${task.badge}生产示例项目`
  }
  if (!projectForm.positioning.trim()) {
    projectForm.positioning = '面向内容创作者和企业 IP 运营者，强调清晰表达、稳定生产和可交付闭环。'
  }
  topicForm.title = task.exampleTitle
  materialForm.title = task.exampleTitle
  materialForm.extractedContent = ''
  materialForm.sourceUrl = ''
  if (task.defaultInputMode === 'text') {
    materialForm.rawText = task.exampleMaterial
    materialForm.topic = ''
    return
  }
  materialForm.topic = task.exampleMaterial
  materialForm.rawText = ''
}

function startSelectedTask() {
  const task = selectedProductionTask.value
  selectProductionTask(task)
  if (!selectedProjectId.value || !selectedTopicId.value || !hasSavedMaterial.value) {
    activeTab.value = 'overview'
    return
  }
  activeTab.value = task.targetTab
  reportTargetTabOpened(task.targetTab)
}

async function runNextWorkflowAction() {
  const action = nextWorkflowAction.value
  isRunningGuideAction.value = true
  try {
    if (action.kind === 'createProject') {
      await handleCreateProject()
      return
    }
    if (action.kind === 'createTopic') {
      selectProductionTask(selectedProductionTask.value)
      await handleCreateTopic()
      return
    }
    if (action.kind === 'saveMaterial') {
      selectProductionTask(selectedProductionTask.value)
      if (!currentMaterialReady.value) {
        setFeedback('info', '请先在素材输入区填写主题、链接或原文。')
        return
      }
      await handleSaveMaterial()
      return
    }
    if (action.kind === 'openProduction') {
      activeTab.value = selectedProductionTask.value.targetTab
      reportTargetTabOpened(selectedProductionTask.value.targetTab)
      return
    }
    activeTab.value = 'overview'
    await refreshContextData()
  } finally {
    isRunningGuideAction.value = false
  }
}

function activate(tab: ProductionTab) {
  activeTab.value = tab
  reportTargetTabOpened(tab)
  if (tab !== 'overview') void refreshContextData()
}

function openPromptTool() {
  if (!canOpenPromptTool.value) {
    feedback.value = { type: 'info', message: '提示词工具为独立后台工具，当前账号暂无访问权限。' }
    return
  }
  void router.push(modePathMap.prompts)
}
</script>

<template>
  <div class="production-center-shell">
    <header class="production-hero">
      <div class="hero-copy">
        <span class="section-eyebrow">生产工作台</span>
        <h1>生产中心</h1>
        <p>围绕一个 IP 项目和一个内容选题，统一组织素材、平台内容和交付资产。</p>
      </div>
      <div class="hero-actions">
        <span v-if="runningTasks.length" class="production-chip active">{{ runningTasks.length }} 项生成中</span>
        <span v-if="failedTasks.length" class="production-chip danger">{{ failedTasks.length }} 项待处理</span>
        <button class="btn btn-ghost" :disabled="isLoading" @click="loadInitialData">{{ isLoading ? '刷新中...' : '刷新内容' }}</button>
      </div>
    </header>

    <div v-if="feedback" class="production-feedback" :class="feedback.type">{{ feedback.message }}</div>

    <section class="production-status-grid" aria-label="内容概览">
      <article v-for="card in statusCards" :key="card.label" class="production-status-card">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </article>
    </section>

    <section class="production-guide production-card" aria-label="生产任务引导">
      <div class="card-head guide-head">
        <div>
          <h2>先选一个生产目标</h2>
          <p>按顺序完成项目、选题、素材和生成步骤。</p>
        </div>
        <button class="btn btn-primary" :disabled="isRunningGuideAction" @click="runNextWorkflowAction">{{ isRunningGuideAction ? '处理中...' : nextWorkflowAction.label }}</button>
      </div>

      <div class="task-entry-grid">
        <button
          v-for="task in productionTasks"
          :key="task.key"
          class="task-entry-card"
          :class="{ active: activeTaskKey === task.key }"
          @click="selectProductionTask(task)"
        >
          <span>{{ task.badge }}</span>
          <strong>{{ task.label }}</strong>
          <small>{{ task.summary }}</small>
          <small class="task-example">示例：{{ task.exampleTitle }}</small>
          <em>{{ task.path }}</em>
        </button>
      </div>

      <div class="quick-start-panel" role="region" aria-label="首单生产向导">
        <div class="quick-start-copy">
          <strong>首单生产向导</strong>
          <p>不理解项目、选题也可以先跑一遍：选任务、用示例填素材、再点下一步。</p>
        </div>
        <div class="quick-start-steps">
          <article v-for="step in quickStartSteps" :key="step.label">
            <span>{{ step.label }}</span>
            <strong>{{ step.title }}</strong>
            <small>{{ step.desc }}</small>
          </article>
        </div>
        <button class="btn btn-ghost" @click="useSelectedTaskExample">用示例开始</button>
      </div>

      <div class="workflow-rail" aria-label="推荐生产顺序">
        <article
          v-for="(step, index) in workflowSteps"
          :key="step.label"
          class="workflow-step"
          :class="{ done: step.done, current: step.current }"
        >
          <i>{{ index + 1 }}</i>
          <div>
            <strong>{{ step.label }}</strong>
            <span>{{ step.desc }}</span>
          </div>
        </article>
      </div>

      <div class="next-action-panel">
        <div>
          <strong>{{ nextWorkflowAction.title }}</strong>
          <p>{{ nextWorkflowAction.desc }}</p>
          <div class="target-platforms" aria-label="当前任务目标平台">
            <span v-for="platform in selectedProductionTask.targetPlatforms" :key="platform">{{ formatPlatformLabel(platform) }}</span>
          </div>
        </div>
        <button class="btn btn-primary" :disabled="isRunningGuideAction" @click="runNextWorkflowAction">{{ isRunningGuideAction ? '处理中...' : nextWorkflowAction.label }}</button>
      </div>

      <div v-if="canOpenPromptTool" class="standalone-tool-row" aria-label="独立工具入口">
        <article class="standalone-tool-card">
          <div>
            <span>独立工具</span>
            <strong>提示词工具</strong>
            <small>提示词模板和分类单独管理，作为生成配置被调用，不放进生产链步骤。</small>
          </div>
          <button class="btn btn-ghost btn-sm" @click="openPromptTool">
            打开提示词工具
          </button>
        </article>
      </div>
    </section>

    <section class="production-context-grid">
      <article class="production-card context-card">
        <div class="card-head compact">
          <div>
            <h3>IP 项目</h3>
            <p>用于管理当前 IP 的定位、选题和内容。</p>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="isCreatingProject" @click="handleCreateProject">{{ isCreatingProject ? '创建中...' : '创建项目' }}</button>
        </div>
        <label>当前项目
          <select v-model.number="selectedProjectId" class="input">
            <option :value="0">选择或创建 IP 项目</option>
            <option v-for="project in projects" :key="project.projectId" :value="project.projectId">{{ project.name }}</option>
          </select>
        </label>
        <div class="mini-form-grid compact-grid">
          <label>项目名称<input v-model="projectForm.name" class="input" /></label>
          <label>IP 类型
            <select v-model="projectForm.ipType" class="input">
              <option value="personal_ip">个人 IP</option>
              <option value="enterprise_ip">企业 IP</option>
              <option value="product_ip">产品 IP</option>
              <option value="pet_ip">宠物 IP</option>
              <option value="virtual_ip">虚拟人 IP</option>
            </select>
          </label>
          <label class="wide">账号定位<textarea v-model="projectForm.positioning" class="input textarea compact" placeholder="专业方向、受众、风格和内容边界"></textarea></label>
        </div>
      </article>

      <article class="production-card context-card">
        <div class="card-head compact">
          <div>
            <h3>内容选题</h3>
            <p>选题用于聚焦一次内容创作。</p>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="!selectedProjectId || isCreatingTopic" @click="handleCreateTopic">{{ isCreatingTopic ? '创建中...' : '创建选题' }}</button>
        </div>
        <label>当前选题
          <select v-model.number="selectedTopicId" class="input" :disabled="!selectedProjectId">
            <option :value="0">选择或创建内容选题</option>
            <option v-for="topic in topics" :key="topic.topicId" :value="topic.topicId">{{ topic.title }} · {{ topic.status }}</option>
          </select>
        </label>
        <div class="mini-form-grid compact-grid">
          <label class="wide">选题名称<input v-model="topicForm.title" class="input" placeholder="例如：如何选择专业" /></label>
          <label>优先级
            <select v-model="topicForm.priority" class="input">
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>
          <label>输入来源
            <select v-model="materialForm.inputMode" class="input">
              <option value="topic">主题</option>
              <option value="url">链接</option>
              <option value="text">粘贴原文</option>
            </select>
          </label>
        </div>
      </article>

      <article class="production-card material-card">
        <div class="card-head compact">
          <div>
            <h3>素材输入</h3>
            <p>主题、链接和原文会整理为当前选题素材，便于生成公众号、小红书和口播内容。</p>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="isSavingMaterial" @click="handleSaveMaterial">{{ isSavingMaterial ? '保存中...' : '保存素材' }}</button>
        </div>
        <label>素材标题<input v-model="materialForm.title" class="input" placeholder="可选，用于资产库展示" /></label>
        <label v-if="materialForm.inputMode === 'topic'">主题<input v-model="materialForm.topic" class="input" placeholder="一句话说明内容方向" /></label>
        <label v-else-if="materialForm.inputMode === 'url'">链接<input v-model="materialForm.sourceUrl" class="input" placeholder="粘贴公众号文章、网页或商品页链接" /></label>
        <label v-else>原文<textarea v-model="materialForm.rawText" class="input textarea" placeholder="粘贴文章、资料、笔记、卖点或口播初稿"></textarea></label>
        <label>解析结果快照<textarea v-model="materialForm.extractedContent" class="input textarea compact" placeholder="保存素材后会写入解析结果或主题快照"></textarea></label>
      </article>
    </section>

    <nav class="production-tabs" aria-label="生产中心模块">
      <button
        v-for="tab in tabItems"
        :key="tab.key"
        :class="{ active: activeTab === tab.key }"
        @click="activate(tab.key)"
      >
        <strong>{{ tab.label }}</strong>
        <span>{{ tab.desc }}</span>
      </button>
    </nav>

    <section class="production-layout">
      <main class="production-main-panel">
        <section v-if="activeTab === 'overview'" class="production-card overview-panel">
          <div class="card-head">
            <div>
              <span class="section-eyebrow">选题总览</span>
              <h2>{{ selectedTopic?.title || '等待选择内容选题' }}</h2>
              <p>{{ hasActiveWork ? '当前选题下的平台内容和素材资产会在这里汇总。' : '先选择或创建 IP 项目与内容选题，再开始生产。' }}</p>
            </div>
            <div class="card-actions">
              <button class="btn btn-primary" :disabled="!hasActiveWork" @click="activate('wechat')">进入公众号闭环</button>
              <button class="btn btn-ghost" :disabled="!hasActiveWork" @click="activate('platform')">生成小红书/口播</button>
            </div>
          </div>
          <div class="overview-columns">
            <article class="selected-task-summary">
              <h3>当前任务路径</h3>
              <strong>{{ selectedProductionTask.label }}</strong>
              <p>{{ selectedProductionTask.summary }}</p>
              <button class="btn btn-primary btn-sm" :disabled="!hasActiveWork" @click="startSelectedTask">{{ selectedProductionTask.ctaLabel }}</button>
            </article>
            <article>
              <h3>平台内容</h3>
              <p v-if="!platformContents.length">当前选题暂无平台内容。</p>
              <button v-for="content in platformContents.slice(0, 8)" :key="content.contentId" class="overview-list-item" @click="activate(content.platform === 'wechat' ? 'wechat' : 'platform')">
                <strong>{{ content.title || '未命名内容' }}</strong>
                <span>{{ formatPlatformLabel(content.platform) }} · {{ formatTaskType(content.contentType) }} · {{ formatStatus(content.status) }}</span>
              </button>
            </article>
            <article>
              <h3>最近草稿</h3>
              <p v-if="!drafts.length">暂无公众号草稿记录。</p>
              <div v-for="draft in drafts.slice(0, 6)" :key="draft.draftId" class="overview-static-item">
                <strong>{{ draft.title }}</strong>
                <span>{{ draft.status }} · {{ draft.createdAt?.slice(0, 16) }}</span>
              </div>
            </article>
          </div>
        </section>

        <WechatArticlePublisher
          v-else-if="activeTab === 'wechat'"
          :key="`wechat-${selectedProjectId}-${selectedTopicId}`"
          :initial-title="contentInitialTitle"
          :initial-content="contentInitialContent"
          :initial-project-id="selectedProjectId"
          :initial-topic-id="selectedTopicId"
          source-type="production-center"
          :source-id="String(selectedTopicId || selectedProjectId || '')"
          :current-user="currentUser"
        />

        <PlatformContentStudio
          v-else-if="activeTab === 'platform'"
          :key="`platform-${selectedProjectId}-${selectedTopicId}`"
          :initial-title="contentInitialTitle"
          :initial-content="contentInitialContent"
          :initial-project-id="selectedProjectId"
          :initial-topic-id="selectedTopicId"
          :current-user="currentUser"
        />

        <TeleprompterPanel
          v-else-if="activeTab === 'teleprompter'"
          :initial-text="contentInitialContent"
          :current-user="teleprompterUser"
        />

        <section v-else class="production-card advanced-panel">
          <span class="section-eyebrow">Advanced Video</span>
          <h2>高级视频生产入口</h2>
          <p>短大片和剧本短视频后续会沿用当前项目和选题，形成完整视频资产。</p>
          <div class="advanced-grid">
            <article>
              <strong>短大片工厂</strong>
              <span>产品图、人物图或宠物图进入主体清理、多视图、九宫格、分镜和视频任务。</span>
            </article>
            <article>
              <strong>剧本短视频</strong>
              <span>角色库、多集剧本、分镜表、分镜图和视频生成统一归档到当前选题。</span>
            </article>
          </div>
        </section>
      </main>

      <aside class="production-side-panel">
        <section class="production-card side-card">
          <div class="side-head"><strong>生成进度</strong><button class="mini-link" @click="refreshContextData">刷新</button></div>
          <p v-if="!tasks.length">暂无生成进度。</p>
          <article v-for="task in tasks.slice(0, 8)" :key="task.taskId" class="compact-item task-item">
            <span>{{ formatTaskType(task.taskType) }}</span>
            <strong>{{ formatStatus(task.status) }} · {{ task.progress || 0 }}%</strong>
            <small>{{ task.status === 'failed' ? '生成失败，可点击重试。' : '正在处理内容生成。' }}</small>
            <button v-if="task.status === 'failed'" class="mini-link danger" :disabled="isRetryingTaskId === task.taskId" @click="handleRetryTask(task)">重试</button>
          </article>
        </section>

        <section class="production-card side-card">
          <div class="side-head"><strong>资产库</strong><button class="mini-link" @click="refreshContextData">刷新</button></div>
          <div v-if="assets.length" class="asset-filter-row" aria-label="资产筛选">
            <button class="filter-chip" :class="{ active: assetFilter === 'all' }" @click="assetFilter = 'all'">全部</button>
            <button class="filter-chip" :class="{ active: assetFilter === 'prompt' }" @click="assetFilter = 'prompt'">提示词素材</button>
          </div>
          <p v-if="!visibleAssets.length">{{ assetFilter === 'prompt' ? '暂无提示词素材。' : '暂无资产。' }}</p>
          <article v-for="asset in visibleAssets.slice(0, 8)" :key="asset.assetId" class="compact-item asset-item">
            <span>{{ formatAssetType(asset.assetType) }}</span>
            <strong>{{ asset.title || '未命名素材' }}</strong>
            <span v-if="getAssetTextContent(asset)" class="prompt-role-pill">{{ getPromptRoleLabel(asset) }}</span>
            <small v-if="getAssetTextContent(asset)">{{ getAssetTextContent(asset).slice(0, 80) }}</small>
            <div v-if="previewAssetId === asset.assetId && getAssetTextContent(asset)" class="asset-preview-box">
              <pre>{{ getAssetTextContent(asset) }}</pre>
              <small v-if="asset.metadata?.promptHash">Hash：{{ asset.metadata.promptHash }}</small>
            </div>
            <div class="asset-actions">
              <button class="mini-link" @click="openAsset(asset)">{{ previewAssetId === asset.assetId ? '收起' : '查看' }}</button>
              <button v-if="getAssetTextContent(asset)" class="mini-link" @click="copyAssetText(asset)">复制</button>
              <button v-if="getAssetTextContent(asset)" class="mini-link" @click="applyAssetAsMaterial(asset)">应用</button>
            </div>
          </article>
        </section>

        <section class="production-card side-card">
          <div class="side-head"><strong>最近生成</strong><button class="mini-link" @click="refreshContextData">刷新</button></div>
          <p v-if="!generationRecords.length">暂无生成内容。</p>
          <article v-for="record in generationRecords.slice(0, 6)" :key="record.recordId" class="compact-item">
            <span>{{ record.createdAt?.slice(0, 16) || '刚刚' }}</span>
            <strong>{{ record.promptSnapshot?.name || '内容生成' }}</strong>
            <small>{{ record.parseStatus === 'failed' ? '需要处理' : '生成完成' }}</small>
          </article>
        </section>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.production-center-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
}

.production-hero,
.production-card,
.production-status-card,
.production-tabs {
  border: 1px solid var(--color-border);
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.production-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 24px;
  border-radius: 28px;
  background:
    radial-gradient(circle at 92% 0%, rgba(36, 87, 255, 0.1), transparent 34%),
    linear-gradient(135deg, #fff 0%, #fff 58%, #f5f7ff 100%);
}

.hero-copy h1 {
  margin: 4px 0 8px;
  color: #111827;
  font-size: clamp(28px, 4vw, 44px);
  letter-spacing: -1.6px;
}

.hero-copy p {
  max-width: 760px;
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.hero-actions,
.card-actions,
.side-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.production-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 800;
}

.production-chip.danger {
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}

.production-feedback {
  border-radius: 16px;
  padding: 12px 14px;
  font-weight: 750;
}

.production-feedback.success { background: rgba(22, 163, 74, 0.1); color: #15803d; }
.production-feedback.error { background: rgba(220, 38, 38, 0.1); color: #b91c1c; }
.production-feedback.info { background: rgba(37, 99, 235, 0.1); color: #1d4ed8; }

.production-status-grid,
.production-context-grid,
.overview-columns,
.advanced-grid {
  display: grid;
  gap: 14px;
}

.production-status-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.production-status-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 104px;
  padding: 16px;
  border-radius: 22px;
}

.production-status-card span,
.production-status-card small,
.overview-static-item span,
.compact-item span,
.compact-item small {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.production-status-card strong {
  color: var(--color-text-primary);
  font-size: 18px;
  letter-spacing: -0.5px;
}

.production-guide {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.95), #fff 42%),
    #fff;
}

.guide-head {
  margin-bottom: 0;
}

.guide-head h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: 24px;
  letter-spacing: -0.8px;
}

.task-entry-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.task-entry-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  min-height: 190px;
  padding: 16px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 20px;
  background: #fff;
  color: var(--color-text-primary);
  text-align: left;
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.task-entry-card:hover {
  transform: translateY(-2px);
  border-color: rgba(37, 99, 235, 0.28);
  box-shadow: 0 16px 30px rgba(37, 99, 235, 0.1);
}

.task-entry-card:active {
  transform: translateY(0);
}

.task-entry-card.active {
  border-color: #bcd0ff;
  background: linear-gradient(180deg, #eef4ff, #fff);
  box-shadow: inset 0 0 0 1px #dbe6ff, 0 18px 34px rgba(37, 99, 235, 0.1);
}

.task-entry-card span {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 850;
}

.task-entry-card strong {
  font-size: 17px;
  letter-spacing: -0.35px;
}

.task-entry-card small {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.55;
}

.task-entry-card .task-example {
  color: #475569;
  font-weight: 800;
}

.task-entry-card em {
  margin-top: auto;
  color: #1d4ed8;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
  line-height: 1.45;
}

.quick-start-panel {
  display: grid;
  grid-template-columns: minmax(180px, 0.8fr) minmax(0, 1.8fr) auto;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 22px;
  background: #fff;
}

.quick-start-copy strong {
  display: block;
  color: var(--color-text-primary);
  font-size: 18px;
  letter-spacing: -0.4px;
}

.quick-start-copy p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.quick-start-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.quick-start-steps article {
  display: grid;
  gap: 4px;
  min-height: 94px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.86);
}

.quick-start-steps span {
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 850;
}

.quick-start-steps strong {
  color: var(--color-text-primary);
  font-size: 14px;
}

.quick-start-steps small {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.workflow-rail {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
}

.workflow-step {
  display: flex;
  gap: 10px;
  min-height: 100px;
  padding: 12px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.74);
}

.workflow-step i {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #e5e7eb;
  color: #4b5563;
  font-size: 12px;
  font-style: normal;
  font-weight: 850;
}

.workflow-step div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.workflow-step strong {
  color: var(--color-text-primary);
  font-size: 13px;
}

.workflow-step span {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.workflow-step.done {
  border-color: rgba(22, 163, 74, 0.22);
  background: rgba(240, 253, 244, 0.78);
}

.workflow-step.done i {
  background: #16a34a;
  color: #fff;
}

.workflow-step.current {
  border-color: rgba(37, 99, 235, 0.32);
  background: rgba(239, 246, 255, 0.86);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.workflow-step.current i {
  background: #2563eb;
  color: #fff;
}

.standalone-tool-row {
  display: grid;
}

.standalone-tool-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1px dashed rgba(37, 99, 235, 0.32);
  border-radius: 20px;
  background: rgba(239, 246, 255, 0.58);
}

.standalone-tool-card div {
  display: grid;
  gap: 4px;
}

.standalone-tool-card span {
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 850;
}

.standalone-tool-card strong {
  color: var(--color-text-primary);
  font-size: 16px;
}

.standalone-tool-card small {
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.next-action-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 20px;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.12), transparent 30%),
    #f8fbff;
}

.next-action-panel strong {
  display: block;
  color: var(--color-text-primary);
  font-size: 18px;
  letter-spacing: -0.4px;
}

.next-action-panel p {
  max-width: 780px;
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.target-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.target-platforms span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #fff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 850;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.18);
}

.production-context-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.material-card {
  grid-column: 1 / -1;
}

.production-card {
  border-radius: 24px;
  padding: 18px;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.card-head.compact h3,
.side-card strong,
.overview-panel h2,
.advanced-panel h2 {
  margin: 0;
}

.card-head p {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.production-card label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 750;
}

.mini-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.compact-grid .wide,
.mini-form-grid .wide {
  grid-column: 1 / -1;
}

.production-tabs {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  padding: 8px;
  border-radius: 24px;
}

.production-tabs button {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-height: 70px;
  padding: 12px;
  border: 0;
  border-radius: 18px;
  background: transparent;
  color: var(--color-text-secondary);
  text-align: left;
  cursor: pointer;
}

.production-tabs button.active {
  background: #eef3ff;
  color: var(--color-accent-primary);
  box-shadow: inset 0 0 0 1px #dbe6ff;
}

.production-tabs button span {
  font-size: 12px;
  line-height: 1.35;
  opacity: 0.78;
}

.production-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  align-items: start;
}

.production-main-panel,
.production-side-panel {
  min-width: 0;
}

.production-side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: sticky;
  top: 86px;
}

.overview-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.selected-task-summary {
  grid-column: 1 / -1;
  padding: 16px;
  border-radius: 20px;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.1), transparent 34%),
    rgba(248, 250, 252, 0.9);
}

.selected-task-summary h3,
.selected-task-summary p {
  margin: 0;
}

.selected-task-summary strong {
  display: block;
  margin: 8px 0 6px;
  color: var(--color-text-primary);
  font-size: 20px;
  letter-spacing: -0.5px;
}

.selected-task-summary p {
  max-width: 720px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.selected-task-summary .btn {
  margin-top: 12px;
}

.overview-list-item,
.overview-static-item,
.compact-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  width: 100%;
  margin-top: 10px;
  padding: 12px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.8);
  color: var(--color-text-primary);
  text-align: left;
}

button.overview-list-item {
  cursor: pointer;
}

.side-card {
  padding: 14px;
}

.side-head {
  justify-content: space-between;
  margin-bottom: 8px;
}

.mini-link {
  border: 0;
  background: transparent;
  color: #2563eb;
  font-weight: 800;
  cursor: pointer;
}

.mini-link.danger {
  color: #dc2626;
}

.asset-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.filter-chip {
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 999px;
  background: #fff;
  color: #2563eb;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
}

.filter-chip.active {
  background: #eff6ff;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
}

.prompt-role-pill {
  width: fit-content;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #475569;
  font-size: 11px;
  font-weight: 850;
}

.asset-preview-box {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
  padding: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: #f8fafc;
}

.asset-preview-box pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: #0f172a;
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
  font-size: 12px;
  line-height: 1.55;
}

.asset-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.advanced-panel p {
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.advanced-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.advanced-grid article {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.86);
}

.advanced-grid span {
  color: var(--color-text-secondary);
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .production-status-grid,
  .production-context-grid,
  .production-layout,
  .production-tabs,
  .task-entry-grid,
  .quick-start-panel,
  .quick-start-steps,
  .workflow-rail,
  .overview-columns,
  .advanced-grid {
    grid-template-columns: 1fr;
  }

  .production-side-panel {
    position: static;
  }
}

@media (max-width: 720px) {
  .production-hero,
  .card-head,
  .next-action-panel,
  .standalone-tool-card {
    flex-direction: column;
    align-items: stretch;
  }

  .mini-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

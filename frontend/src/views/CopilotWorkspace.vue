<script setup lang="ts">
import { ref, reactive, nextTick, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import HomeToolCards, { type ToolKey } from '../components/HomeToolCards.vue'
import TeleprompterPanel from '../components/TeleprompterPanel.vue'
import WechatArticlePublisher from '../components/WechatArticlePublisher.vue'
import PlatformContentStudio from '../components/PlatformContentStudio.vue'
import ProductionCenter from '../components/ProductionCenter.vue'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Sprint1CaseWorkspace from './Sprint1CaseWorkspace.vue'
import { modePathMap } from '../stores/workspace'
import {
  parseUrl,
  parseText,
  parseFile,
  generateFullCase,
  copilotModifyStream,
  listPersonas,
  listColumns,
  createColumn,
  generateVideoAipPlan,
  createVideoAipProject,
  createVideoAipProjectFromShortVideo,
  getVideoAipProject,
  updateVideoAipStep,
  runVideoAipStep,
  runNextVideoAipStep,
  runAllVideoAipSteps,
  retryVideoAipStep,
  getVideoTask,
  videoTaskMediaFileUrl,
  generateTopicPlan,
  optimizeHooks,
  generatePublishPackage,
  qualityCheck,
  buildShortVideoWorkflow,
  saveShortVideoProject,
  generateReversalDrama,
  listReversalDramaHistory,
  deleteReversalDramaHistory,
  clearReversalDramaHistory,
  analyzeVideoAssets,
  type GenerateParams,
  type ContentColumnData,
  type VideoAipStepTask,
  type ReversalCharacter,
  type ReversalDramaResult,
  type VideoAssetAnalysisItem,
} from '../api'
import {
  createPromptTemplate,
  createPromptTemplateCategory,
  deletePromptTemplate,
  deletePromptTemplateCategory,
  getPromptTemplate,
  listPromptTemplateCategories,
  listPromptTemplates,
  listPromptTemplateVersions,
  updatePromptTemplate,
  updatePromptTemplateCategory,
  type PromptTemplateCategoryData,
  type PromptTemplateData,
  type PromptTemplateVersionData,
} from '../api/promptTemplates.api'
import {
  createModelConfig,
  createModelGateway,
  deleteModelConfig,
  deleteModelGateway,
  getModelDefaults,
  listModelCatalog,
  listModelConfigs,
  listModelGateways,
  setGlobalModelDefault,
  setModelDefault,
  syncModelGatewayModels,
  testModelGateway,
  updateModelCatalogItem,
  type AIModelConfigData,
  type ModelDefaultsData,
  type ModelGatewayData,
} from '../api/modelConfig.api'

// ─── State ──────────────────────────────────────────────────

const activeTab = ref<'extracted' | 'shortVideo' | 'strategy' | 'script' | 'video' | 'cover' | 'publish'>('extracted')
const inputMode = ref<'topic' | 'url' | 'text' | 'file' | 'media'>('topic')
const topicInput = ref('')
const urlInput = ref('')
const textInput = ref('')
const fileInput = ref<any>(null)
const mediaFiles = ref<File[]>([])
const analyzedAssets = ref<VideoAssetAnalysisItem[]>([])

const isLoading = ref(false)
const isGenerating = ref(false)
const isCopilotStreaming = ref(false)
const extractedContent = ref('')
const scriptContent = ref('')
const videoPrompts = ref('')
const coverPrompt = ref('')
const teleprompterInitialText = ref('')

const personas = ref<any[]>([])
const columns = ref<ContentColumnData[]>([])
const promptTemplateCategories = ref<PromptTemplateCategoryData[]>([])
const promptTemplates = ref<PromptTemplateData[]>([])
const coverPromptTemplates = ref<PromptTemplateData[]>([])
const videoPromptTemplates = ref<PromptTemplateData[]>([])
const promptManagerTemplates = ref<PromptTemplateData[]>([])
const textModelConfigs = ref<AIModelConfigData[]>([])
const imageModelConfigs = ref<AIModelConfigData[]>([])
const videoModelConfigs = ref<AIModelConfigData[]>([])
const modelManagerConfigs = ref<AIModelConfigData[]>([])
const modelGateways = ref<ModelGatewayData[]>([])
const modelDefaults = ref<ModelDefaultsData>({})
const selectedPersonaId = ref(0)
const selectedColumnId = ref(0)
const selectedPromptCategory = ref('knowledge_talk')
const selectedPromptTemplateId = ref(1)
const selectedCoverPromptTemplateId = ref(0)
const selectedVideoPromptTemplateId = ref(0)
const selectedTextModelConfigId = ref(0)
const selectedCoverModelConfigId = ref(0)
const selectedVideoModelConfigId = ref(0)
const coverAspectRatio = ref('9:16')
const coverTitle = ref('')
const videoAspectRatio = ref('9:16')
const videoDuration = ref('15秒')
const videoWorkflowType = ref<'standard' | 'product_tvc' | 'drama'>('standard')
const showPromptTemplateDetail = ref(false)
const targetPlatform = ref('veo')
const extraRequirements = ref('')
const isStrategyLoading = ref(false)
const isCreatingColumn = ref(false)
const promptManagerCategoryKey = ref('')
const promptManagerFeedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const isSavingPromptCategory = ref(false)
const isSavingPromptTemplate = ref(false)
const isSavingModelConfig = ref(false)
const isSavingModelGateway = ref(false)
const modelGatewayFeedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const modelGatewayBusy = reactive<Record<number, boolean>>({})
const editingPromptCategoryKey = ref('')
const editingPromptTemplateId = ref(0)
const promptTemplateVersions = ref<PromptTemplateVersionData[]>([])

const promptCategoryForm = reactive<PromptTemplateCategoryData>({
  key: '',
  name: '',
  description: '',
  sort_order: 0,
  is_active: true,
})

const promptTemplateForm = reactive<PromptTemplateData>({
  id: 0,
  key: '',
  category_key: '',
  platform: '',
  scene: '',
  step: '',
  name: '',
  description: '',
  scenario: '',
  output_structure: '',
  writing_rules: [],
  prompt_body: '',
  version: '1.0.0',
  is_default: false,
  is_active: true,
  sort_order: 0,
  change_note: '',
})
const promptTemplateRulesText = ref('')

const modelConfigForm = reactive<AIModelConfigData>({
  name: '',
  model_type: 'text',
  provider: 'custom',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model_id: '',
  is_openai_compatible: true,
  is_default: false,
  is_active: true,
  timeout_seconds: 180,
  max_retries: 2,
  sort_order: 0,
  notes: '',
})

const modelGatewayForm = reactive<ModelGatewayData>({
  name: '',
  scope: 'user',
  provider_type: 'openai_compatible',
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  is_active: true,
})

const quickColumn = reactive<ContentColumnData>({
  name: '老板60秒',
  goal: '建信任',
  target_platform: '视频号+抖音',
  duration: '30-60秒',
  structure: '痛点开场 → 真实案例 → 方法拆解 → 一句话总结 → 关注/私信 CTA',
  opening_style: '痛点直击型',
  cta: '想要模板，评论区打「资料」。',
})

const strategyOutputs = reactive({
  shortVideoWorkflow: null as any,
  topics: null as any,
  hooks: null as any,
  publishPackage: null as any,
  quality: null as any,
})

const isShortVideoLoading = ref(false)
const isSavingShortVideoProject = ref(false)
const isCreatingAipFromShortVideo = ref(false)
const savedShortVideoProjectId = ref(0)
const isVideoAipPlanning = ref(false)
const isSavingVideoAipProject = ref(false)
const isRunningVideoAipNext = ref(false)
const isRunningVideoAipAll = ref(false)
const runningVideoAipStepIds = reactive<Record<number, boolean>>({})
const videoAipPlan = ref<any>(null)
const videoAipProject = ref<any>(null)
const videoAipProductName = ref('')
const videoAipCharacterNotes = ref('')

const videoAipDisplaySteps = computed<any[]>(() => {
  if (videoAipProject.value?.steps?.length) {
    return videoAipProject.value.steps.map((step: any) => ({
      ...step,
      displayKey: step.step_key,
      displayStatus: step.status,
      isPersistedTask: true,
      task_type: step.output?.task_type || step.output?.media_type || 'text',
      artifact_type: step.output?.artifact_type || '',
    }))
  }
  return (videoAipPlan.value?.steps || []).map((step: any) => ({
    ...step,
    id: 0,
    output: {},
    displayKey: step.key,
    displayStatus: 'planned',
    isPersistedTask: false,
  }))
})
const shortVideoForm = reactive({
  user_input: '',
  requested_intent: 'auto',
  subject_name: '',
  platform: '小红书/抖音',
  aspect_ratio: '9:16',
  duration: '15秒',
  model: '即梦2.0',
  style: '高级、真实、有记忆点',
  target_audience: '',
  core_message: '',
})

const shortVideoIntentOptions = [
  { value: 'auto', label: '自动识别' },
  { value: 'product_tvc', label: '产品TVC' },
  { value: 'pet_vlog', label: '宠物Vlog' },
  { value: 'ip_character', label: '人物IP短片' },
  { value: 'knowledge_talk', label: '知识口播' },
  { value: 'lifestyle', label: '生活方式种草' },
  { value: 'space_store', label: '空间探店' },
]

const selectedColumn = computed(() =>
  columns.value.find((column) => column.id === selectedColumnId.value) || null
)

const selectedPromptTemplate = computed<any>(() =>
  promptTemplates.value.find((template) => template.id === selectedPromptTemplateId.value) || null
)

const scriptPromptCategories = computed(() =>
  promptTemplateCategories.value.filter((category) => !category.template_type || category.template_type === 'text_script')
)

const selectedCoverPromptTemplate = computed(() =>
  coverPromptTemplates.value.find((template) => template.id === selectedCoverPromptTemplateId.value) || null
)

const selectedVideoPromptTemplate = computed(() =>
  videoPromptTemplates.value.find((template) => template.id === selectedVideoPromptTemplateId.value) || null
)

const selectedTextModelConfig = computed(() => textModelConfigs.value.find((model) => model.id === selectedTextModelConfigId.value) || null)
const selectedCoverModelConfig = computed(() => imageModelConfigs.value.find((model) => model.id === selectedCoverModelConfigId.value) || null)
const selectedVideoModelConfig = computed(() => videoModelConfigs.value.find((model) => model.id === selectedVideoModelConfigId.value) || null)

const modelTypeLabels: Record<string, string> = {
  text: '文字',
  image: '图片',
  video: '视频',
  multimodal: '多模态',
  unknown: '待标注',
}

const modelResolutionLabels: Record<string, string> = {
  user_default: '个人默认',
  global_default: '全局默认',
  recommendation_fallback: '推荐兜底',
  none: '未配置',
}

const modelCapabilityGroups = computed(() => [
  { type: 'text', label: '生文字', models: modelManagerConfigs.value.filter((model) => ['text', 'multimodal'].includes(model.model_type)) },
  { type: 'image', label: '生图片', models: modelManagerConfigs.value.filter((model) => ['image', 'multimodal'].includes(model.model_type)) },
  { type: 'video', label: '生视频', models: modelManagerConfigs.value.filter((model) => ['video', 'multimodal'].includes(model.model_type)) },
])

function modelOptionLabel(model: AIModelConfigData) {
  const badges = [model.provider, model.is_default ? '全局默认' : '', model.recommendation_label || ''].filter(Boolean)
  return `${model.name}${badges.length ? ` · ${badges.join(' · ')}` : ''}`
}

function modelHint(model: AIModelConfigData | null, fallback: string) {
  if (!model) return fallback
  const parts = [model.recommendation_label, model.recommendation_reason, model.risk_note].filter(Boolean)
  return parts.length ? parts.join('｜') : `${model.name} 当前可用于${modelTypeLabels[model.model_type] || model.model_type}任务。`
}

function resolvedDefaultName(modelType: string) {
  const bucket = (modelDefaults.value as Record<string, any>)[modelType]
  return bucket?.resolved?.name || '未配置'
}

function resolvedDefaultLabel(modelType: string) {
  const bucket = (modelDefaults.value as Record<string, any>)[modelType]
  return modelResolutionLabels[bucket?.resolved?.resolved_by || 'none'] || '未配置'
}

// Chat
interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
}
const chatMessages = reactive<ChatMessage[]>([
  {
    role: 'system',
    content: '👋 你好！我是你的 IP 打造助手。上传素材后点击「一键生成」，我会为你生成口播文案和视频提示词。生成完成后，你可以在这里对我说出修改意见，我会实时帮你调整内容。',
    timestamp: Date.now(),
  },
])
const chatInput = ref('')
const chatContainerRef = ref<HTMLElement | null>(null)

const platforms = [
  { value: 'veo', label: 'Google Veo' },
  { value: 'doubao', label: '豆包 (ByteDance)' },
  { value: 'jimeng', label: '即梦 (Jimeng)' },
]

// ─── 内容输出状态 ───────────────────────────────────────

const currentContent = computed(() => {
  switch (activeTab.value) {
    case 'extracted': return extractedContent.value
    case 'shortVideo': return strategyOutputs.shortVideoWorkflow ? JSON.stringify(strategyOutputs.shortVideoWorkflow, null, 2) : ''
    case 'strategy': return strategyOutputs.topics ? JSON.stringify(strategyOutputs.topics, null, 2) : ''
    case 'script': return scriptContent.value
    case 'video': return videoPrompts.value
    case 'cover': return coverPrompt.value
    case 'publish': return (strategyOutputs.publishPackage || strategyOutputs.quality)
      ? JSON.stringify({ publish_package: strategyOutputs.publishPackage, quality: strategyOutputs.quality }, null, 2)
      : ''
    default: return ''
  }
})

const outputStatus = computed(() => (strategyOutputs.publishPackage || strategyOutputs.quality ? '已输出' : '待输出'))

const shortVideoWorkflowContent = computed(() => (
  strategyOutputs.shortVideoWorkflow ? JSON.stringify(strategyOutputs.shortVideoWorkflow, null, 2) : ''
))

const strategyContent = computed(() => (
  strategyOutputs.topics || strategyOutputs.hooks
    ? JSON.stringify({ topics: strategyOutputs.topics, hooks: strategyOutputs.hooks }, null, 2)
    : ''
))

const publishContent = computed(() => (
  strategyOutputs.publishPackage || strategyOutputs.quality
    ? JSON.stringify({ publish_package: strategyOutputs.publishPackage, quality: strategyOutputs.quality }, null, 2)
    : ''
))

const parseDisabledReason = computed(() => {
  if (isLoading.value) return ''
  if (inputMode.value === 'topic' && !topicInput.value.trim()) return '请先输入选题、标题或口播主题。'
  if (inputMode.value === 'url' && !urlInput.value.trim()) return '请先粘贴文章链接。'
  if (inputMode.value === 'text' && !textInput.value.trim()) return '请先粘贴文章内容。'
  if (inputMode.value === 'file' && !fileInput.value) return '请先选择 TXT / PDF / DOCX 文件。'
  if (inputMode.value === 'media' && !mediaFiles.value.length) return '请先选择图片或视频素材。'
  return ''
})

const canParseInput = computed(() => !parseDisabledReason.value)

const generateCaseReason = computed(() => {
  if (isGenerating.value) return '正在生成，请稍候。'
  if (!extractedContent.value.trim()) return '请先输入主题，或解析链接、文本、文件、媒体素材。'
  return ''
})

const strategyActionHint = computed(() => {
  if (!extractedContent.value.trim()) return '先提取内容后可生成选题。'
  if (!scriptContent.value.trim()) return '生成口播文案后可做黄金3秒、发布全案和质检。'
  return '选题、开头、发布和质检已可使用。'
})

const contentTypeMap: Record<string, string> = {
  extracted: 'extracted',
  shortVideo: 'short_video_workflow',
  strategy: 'strategy',
  script: 'script',
  video: 'video_prompts',
  cover: 'cover_prompt',
  publish: 'publish_package',
}

// ─── Actions ────────────────────────────────────────────────

async function loadPersonas() {
  try {
    const res = await listPersonas()
    personas.value = res.data || []
  } catch {
    // silently fail
  }
}
loadPersonas()

async function loadColumns() {
  try {
    const res = await listColumns(selectedPersonaId.value)
    columns.value = res.data || []
    if (selectedColumnId.value && !columns.value.some((c) => c.id === selectedColumnId.value)) {
      selectedColumnId.value = 0
    }
  } catch {
    columns.value = []
  }
}
loadColumns()
watch(selectedPersonaId, () => loadColumns())
async function loadPromptTemplateCategories() {
  try {
    const res = await listPromptTemplateCategories()
    promptTemplateCategories.value = res.data || []
    if (!selectedPromptCategory.value && promptTemplateCategories.value.length) {
      selectedPromptCategory.value = promptTemplateCategories.value[0].key
    }
    if (!promptManagerCategoryKey.value && promptTemplateCategories.value.length) {
      promptManagerCategoryKey.value = promptTemplateCategories.value[0].key
    }
  } catch {
    promptTemplateCategories.value = []
  }
}

async function loadPromptTemplates() {
  try {
    const res = await listPromptTemplates(selectedPromptCategory.value, 'text_script')
    promptTemplates.value = res.data || []
    if (!promptTemplates.value.some((template) => template.id === selectedPromptTemplateId.value)) {
      selectedPromptTemplateId.value = promptTemplates.value[0]?.id || 0
    }
  } catch {
    promptTemplates.value = []
    selectedPromptTemplateId.value = 0
  }
}

async function loadGenerationSidecarData() {
  try {
    const [coverRes, videoRes, textModelRes, imageModelRes, videoModelRes, defaultsRes] = await Promise.all([
      listPromptTemplates('', 'image_cover'),
      listPromptTemplates('', 'video_clip'),
      listModelCatalog('text'),
      listModelCatalog('image'),
      listModelCatalog('video'),
      getModelDefaults(),
    ])
    coverPromptTemplates.value = coverRes.data || []
    videoPromptTemplates.value = videoRes.data || []
    textModelConfigs.value = textModelRes.data || []
    imageModelConfigs.value = imageModelRes.data || []
    videoModelConfigs.value = videoModelRes.data || []
    modelDefaults.value = defaultsRes.data || {}
    if (!selectedCoverPromptTemplateId.value) selectedCoverPromptTemplateId.value = coverPromptTemplates.value[0]?.id || 0
    if (!selectedVideoPromptTemplateId.value) selectedVideoPromptTemplateId.value = videoPromptTemplates.value[0]?.id || 0
    const resolvedText = modelDefaults.value.text?.resolved?.id || textModelConfigs.value[0]?.id || 0
    const resolvedImage = modelDefaults.value.image?.resolved?.id || imageModelConfigs.value[0]?.id || 0
    const resolvedVideo = modelDefaults.value.video?.resolved?.id || videoModelConfigs.value[0]?.id || 0
    if (!selectedTextModelConfigId.value || !textModelConfigs.value.some((model) => model.id === selectedTextModelConfigId.value)) selectedTextModelConfigId.value = resolvedText
    if (!selectedCoverModelConfigId.value || !imageModelConfigs.value.some((model) => model.id === selectedCoverModelConfigId.value)) selectedCoverModelConfigId.value = resolvedImage
    if (!selectedVideoModelConfigId.value || !videoModelConfigs.value.some((model) => model.id === selectedVideoModelConfigId.value)) selectedVideoModelConfigId.value = resolvedVideo
  } catch {
    try {
      const [coverRes, videoRes, textModelRes, imageModelRes, videoModelRes] = await Promise.all([
        listPromptTemplates('', 'image_cover'),
        listPromptTemplates('', 'video_clip'),
        listModelConfigs('text'),
        listModelConfigs('image'),
        listModelConfigs('video'),
      ])
      coverPromptTemplates.value = coverRes.data || []
      videoPromptTemplates.value = videoRes.data || []
      textModelConfigs.value = textModelRes.data || []
      imageModelConfigs.value = imageModelRes.data || []
      videoModelConfigs.value = videoModelRes.data || []
      if (!selectedTextModelConfigId.value) selectedTextModelConfigId.value = textModelConfigs.value[0]?.id || 0
      if (!selectedCoverModelConfigId.value) selectedCoverModelConfigId.value = imageModelConfigs.value[0]?.id || 0
      if (!selectedVideoModelConfigId.value) selectedVideoModelConfigId.value = videoModelConfigs.value[0]?.id || 0
    } catch {
      coverPromptTemplates.value = []
      videoPromptTemplates.value = []
      textModelConfigs.value = []
      imageModelConfigs.value = []
      videoModelConfigs.value = []
    }
  }
}

async function loadModelManagerConfigs() {
  try {
    const res = await listModelCatalog()
    modelManagerConfigs.value = res.data || []
  } catch {
    try {
      const res = await listModelConfigs()
      modelManagerConfigs.value = res.data || []
    } catch {
      modelManagerConfigs.value = []
    }
  }
}

async function loadModelGateways() {
  try {
    const res = await listModelGateways()
    modelGateways.value = res.data || []
  } catch {
    modelGateways.value = []
  }
}

async function loadModelDefaults() {
  try {
    const res = await getModelDefaults()
    modelDefaults.value = res.data || {}
  } catch {
    modelDefaults.value = {}
  }
}

async function loadPromptManagerTemplates() {
  try {
    const res = await listPromptTemplates(promptManagerCategoryKey.value)
    promptManagerTemplates.value = res.data || []
  } catch {
    promptManagerTemplates.value = []
  }
}

loadPromptTemplateCategories()
loadPromptTemplates()
loadPromptManagerTemplates()
loadGenerationSidecarData()
loadModelManagerConfigs()
loadModelGateways()
loadModelDefaults()
watch(selectedPromptCategory, () => loadPromptTemplates())
watch(promptManagerCategoryKey, () => {
  resetPromptTemplateForm()
  loadPromptManagerTemplates()
})
watch(selectedColumnId, () => {
  const column = selectedColumn.value
  if (!column) return
  Object.assign(quickColumn, {
    name: column.name,
    goal: column.goal,
    target_platform: column.target_platform,
    duration: column.duration,
    structure: column.structure,
    opening_style: column.opening_style,
    cta: column.cta,
    default_template: column.default_template,
    default_voice: column.default_voice,
    default_bgm: column.default_bgm,
    notes: column.notes,
    sort_order: column.sort_order,
  })
})

function resetPromptCategoryForm() {
  editingPromptCategoryKey.value = ''
  Object.assign(promptCategoryForm, {
    key: '',
    name: '',
    description: '',
    sort_order: 0,
    is_active: true,
  })
}

function editPromptCategory(category: PromptTemplateCategoryData) {
  editingPromptCategoryKey.value = category.key
  Object.assign(promptCategoryForm, {
    key: category.key,
    name: category.name,
    description: category.description,
    sort_order: category.sort_order || 0,
    is_active: category.is_active !== false,
  })
}

function resetPromptTemplateForm() {
  editingPromptTemplateId.value = 0
  Object.assign(promptTemplateForm, {
    id: 0,
    key: '',
    category_key: promptManagerCategoryKey.value || selectedPromptCategory.value || 'knowledge_talk',
    platform: '',
    scene: '',
    step: '',
    name: '',
    description: '',
    scenario: '',
    output_structure: '',
    writing_rules: [],
    prompt_body: '',
    version: '1.0.0',
    is_default: false,
    is_active: true,
    sort_order: 0,
    change_note: '',
  })
  promptTemplateRulesText.value = ''
  promptTemplateVersions.value = []
}

async function refreshPromptData() {
  await loadPromptTemplateCategories()
  await loadPromptTemplates()
  await loadPromptManagerTemplates()
  await loadGenerationSidecarData()
  await loadModelManagerConfigs()
  await loadModelGateways()
  await loadModelDefaults()
}

function resetModelGatewayForm() {
  Object.assign(modelGatewayForm, {
    name: '',
    scope: 'user',
    provider_type: 'openai_compatible',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    is_active: true,
  })
}

async function handleCreateModelGateway() {
  if (isSavingModelGateway.value) return
  if (!modelGatewayForm.name?.trim() || !modelGatewayForm.base_url?.trim() || !modelGatewayForm.api_key?.trim()) {
    modelGatewayFeedback.value = { type: 'error', message: '请填写配置名称、Base URL 和 API Key。' }
    return
  }
  isSavingModelGateway.value = true
  try {
    await createModelGateway(modelGatewayForm)
    modelGatewayFeedback.value = { type: 'success', message: '模型中转已创建，请点击“测试”或“同步模型”。' }
    resetModelGatewayForm()
    await refreshPromptData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '创建模型中转失败。' }
  } finally {
    isSavingModelGateway.value = false
  }
}

async function handleTestModelGateway(gateway: ModelGatewayData) {
  if (!gateway.id) return
  modelGatewayBusy[gateway.id] = true
  try {
    const res = await testModelGateway(gateway.id)
    modelGatewayFeedback.value = { type: res.data?.ok ? 'success' : 'error', message: res.data?.message || res.message || '测试完成。' }
    await loadModelGateways()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '测试连接失败。' }
  } finally {
    modelGatewayBusy[gateway.id] = false
  }
}

async function handleSyncModelGateway(gateway: ModelGatewayData) {
  if (!gateway.id) return
  modelGatewayBusy[gateway.id] = true
  try {
    const res = await syncModelGatewayModels(gateway.id)
    modelGatewayFeedback.value = { type: 'success', message: res.message || `已同步 ${res.data?.length || 0} 个模型。` }
    await refreshPromptData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '同步模型失败。' }
  } finally {
    modelGatewayBusy[gateway.id] = false
  }
}

async function handleDeleteModelGateway(gateway: ModelGatewayData) {
  if (!gateway.id) return
  const confirmed = await requestConfirmation({
    title: '停用模型中转',
    message: `确认停用中转「${gateway.name}」及其同步模型吗？停用后相关生成任务将不再使用该中转。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deleteModelGateway(gateway.id)
    modelGatewayFeedback.value = { type: 'success', message: `已停用中转「${gateway.name}」。` }
    await refreshPromptData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用中转失败。' }
  }
}

async function handleSetPersonalDefault(modelType: string, modelId: number) {
  try {
    await setModelDefault(modelType, modelId)
    modelGatewayFeedback.value = { type: 'success', message: `个人默认${modelTypeLabels[modelType] || modelType}模型已更新。` }
    await refreshPromptData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '设置个人默认失败。' }
  }
}

async function handleSetGlobalDefault(modelType: string, modelId: number) {
  try {
    await setGlobalModelDefault(modelType, modelId)
    modelGatewayFeedback.value = { type: 'success', message: `全局默认${modelTypeLabels[modelType] || modelType}模型已更新。` }
    await refreshPromptData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '设置全局默认失败。' }
  }
}

async function handleUpdateModelCapability(model: AIModelConfigData, modelType: string) {
  if (!model.id) return
  try {
    await updateModelCatalogItem(model.id, {
      model_type: modelType,
      recommendation_label: model.recommendation_label || '',
      recommendation_reason: model.recommendation_reason || '',
      risk_note: model.risk_note || '',
      sort_order: model.sort_order || 0,
      is_active: modelType !== 'unknown',
    })
    modelGatewayFeedback.value = { type: 'success', message: `模型「${model.name}」能力已更新。` }
    await refreshPromptData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '更新模型能力失败。' }
  }
}

function handleUpdateModelCapabilityFromEvent(model: AIModelConfigData, event: Event) {
  const target = event.target as HTMLSelectElement | null
  if (!target) return
  handleUpdateModelCapability(model, target.value)
}

function resetModelConfigForm() {
  Object.assign(modelConfigForm, {
    name: '',
    model_type: 'text',
    provider: 'custom',
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    model_id: '',
    is_openai_compatible: true,
    is_default: false,
    is_active: true,
    timeout_seconds: 180,
    max_retries: 2,
    sort_order: 0,
    notes: '',
  })
}

async function handleSaveModelConfig() {
  if (isSavingModelConfig.value) return
  if (!modelConfigForm.name.trim()) {
    promptManagerFeedback.value = { type: 'error', message: '请填写模型名称。' }
    return
  }
  isSavingModelConfig.value = true
  try {
    await createModelConfig(modelConfigForm)
    promptManagerFeedback.value = { type: 'success', message: '模型配置已创建。' }
    resetModelConfigForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '保存模型配置失败。' }
  } finally {
    isSavingModelConfig.value = false
  }
}

async function handleDeleteModelConfig(model: AIModelConfigData) {
  if (!model.id) return
  const confirmed = await requestConfirmation({
    title: '停用模型',
    message: `确认停用模型「${model.name}」吗？停用后它不会再出现在生成模型选择中。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deleteModelConfig(model.id)
    promptManagerFeedback.value = { type: 'success', message: `已停用模型「${model.name}」。` }
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用模型失败。' }
  }
}

async function handleSavePromptCategory() {
  if (isSavingPromptCategory.value) return
  if (!promptCategoryForm.key.trim() || !promptCategoryForm.name.trim()) {
    promptManagerFeedback.value = { type: 'error', message: '请填写分类 Key 和分类名称。' }
    return
  }
  isSavingPromptCategory.value = true
  try {
    if (editingPromptCategoryKey.value) {
      await updatePromptTemplateCategory(editingPromptCategoryKey.value, promptCategoryForm)
      promptManagerFeedback.value = { type: 'success', message: '提示词分类已更新。' }
    } else {
      await createPromptTemplateCategory(promptCategoryForm)
      promptManagerFeedback.value = { type: 'success', message: '提示词分类已创建。' }
    }
    promptManagerCategoryKey.value = promptCategoryForm.key
    resetPromptCategoryForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '保存分类失败。' }
  } finally {
    isSavingPromptCategory.value = false
  }
}

async function handleDeletePromptCategory(category: PromptTemplateCategoryData) {
  const confirmed = await requestConfirmation({
    title: '停用提示词分类',
    message: `确认停用提示词分类「${category.name}」吗？该分类下模板也会停用。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deletePromptTemplateCategory(category.key)
    promptManagerFeedback.value = { type: 'success', message: `已停用分类「${category.name}」。` }
    if (promptManagerCategoryKey.value === category.key) promptManagerCategoryKey.value = ''
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用分类失败。' }
  }
}

async function editPromptTemplate(template: PromptTemplateData) {
  try {
    const res = await getPromptTemplate(template.id)
    const detail = res.data as PromptTemplateData
    editingPromptTemplateId.value = detail.id
    Object.assign(promptTemplateForm, {
      ...detail,
      platform: detail.platform || '',
      scene: detail.scene || '',
      step: detail.step || '',
      writing_rules: detail.writing_rules || [],
      prompt_body: detail.prompt_body || '',
      is_active: detail.is_active !== false,
      change_note: '',
    })
    promptTemplateRulesText.value = (detail.writing_rules || []).join('\n')
    const versions = await listPromptTemplateVersions(template.id)
    promptTemplateVersions.value = versions.data.items || []
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '读取模板详情失败。' }
  }
}

async function handleSavePromptTemplate() {
  if (isSavingPromptTemplate.value) return
  if (!promptTemplateForm.key.trim() || !promptTemplateForm.name.trim() || !promptTemplateForm.category_key.trim()) {
    promptManagerFeedback.value = { type: 'error', message: '请填写模板 Key、模板名称和所属分类。' }
    return
  }
  isSavingPromptTemplate.value = true
  try {
    const payload: PromptTemplateData = {
      ...promptTemplateForm,
      change_note: promptTemplateForm.change_note || (editingPromptTemplateId.value ? '后台更新模板' : '后台创建模板'),
      writing_rules: promptTemplateRulesText.value.split('\n').map((item) => item.trim()).filter(Boolean),
    }
    if (editingPromptTemplateId.value) {
      await updatePromptTemplate(editingPromptTemplateId.value, payload)
      promptManagerFeedback.value = { type: 'success', message: '提示词模板已更新。' }
    } else {
      await createPromptTemplate(payload)
      promptManagerFeedback.value = { type: 'success', message: '提示词模板已创建。' }
    }
    promptManagerCategoryKey.value = payload.category_key
    resetPromptTemplateForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '保存模板失败。' }
  } finally {
    isSavingPromptTemplate.value = false
  }
}

async function handleDeletePromptTemplate(template: PromptTemplateData) {
  const confirmed = await requestConfirmation({
    title: '停用提示词模板',
    message: `确认停用提示词模板「${template.name}」吗？停用后前端生成页不会继续选择它。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deletePromptTemplate(template.id)
    promptManagerFeedback.value = { type: 'success', message: `已停用模板「${template.name}」。` }
    if (editingPromptTemplateId.value === template.id) resetPromptTemplateForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用模板失败。' }
  }
}

function getErrorMessage(err: any, fallback = '请求失败') {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  if (err?.code === 'ERR_NETWORK' || err?.message === 'Network Error') {
    return '无法连接后端服务。请确认后端已启动，或检查 API 地址 / 跨域配置。'
  }
  if (err?.code === 'ECONNABORTED') {
    return '请求超时，请稍后重试，或改为手动粘贴文章正文。'
  }
  return err?.message || fallback
}

async function handleParse() {
  if (isLoading.value) return
  if (parseDisabledReason.value) {
    addChatMessage('system', parseDisabledReason.value)
    return
  }

  isLoading.value = true
  try {
    let res: any

    if (inputMode.value === 'topic') {
      const topic = topicInput.value.trim()
      if (!topic) return
      extractedContent.value = `选题主题：${topic}`
      activeTab.value = 'extracted'
      addChatMessage('assistant', '✅ 已记录口播主题！你可以继续选择提示词模板和 IP 人设，然后点击「生成全案」。')
      return
    } else if (inputMode.value === 'url') {
      if (!urlInput.value.trim()) return
      res = await parseUrl(urlInput.value.trim())
    } else if (inputMode.value === 'text') {
      if (!textInput.value.trim()) return
      extractedContent.value = textInput.value.trim()
      activeTab.value = 'extracted'
      res = await parseText(textInput.value.trim())
    } else if (inputMode.value === 'file' && fileInput.value) {
      res = await parseFile(fileInput.value)
    } else if (inputMode.value === 'media') {
      if (!mediaFiles.value.length) return
      const res = await analyzeVideoAssets(mediaFiles.value)
      analyzedAssets.value = res.assets || []
      extractedContent.value = res.extracted_content
      activeTab.value = 'extracted'
      addChatMessage('assistant', `✅ 已分析 ${analyzedAssets.value.length} 个图片/视频素材，并整理为可生成全案的素材理解。`)
      return
    } else {
      return
    }

    extractedContent.value = res.data?.extracted_content || extractedContent.value
    activeTab.value = 'extracted'

    addChatMessage('assistant', '✅ 内容已成功提取！你可以在「内容提取」版块中查看和编辑。准备好后，选择一个 IP 人设，然后点击「生成全案」。')
  } catch (err: any) {
    addChatMessage('assistant', `❌ 内容提取失败：${getErrorMessage(err)}`)
  } finally {
    isLoading.value = false
  }
}

async function handleGenerate() {
  if (isGenerating.value || !extractedContent.value) return

  isGenerating.value = true
  addChatMessage('assistant', '⏳ 正在为你生成口播文案、分镜提示词和封面提示词，请稍候...')

  try {
    const params: GenerateParams = {
      extracted_content: extractedContent.value,
      persona_id: selectedPersonaId.value,
      column_id: selectedColumnId.value,
      target_platform: targetPlatform.value,
      extra_requirements: extraRequirements.value,
      prompt_template_id: selectedPromptTemplateId.value || undefined,
      prompt_template_key: selectedPromptTemplate.value?.key,
      prompt_template_category: selectedPromptCategory.value,
      text_model_config_id: selectedTextModelConfigId.value || undefined,
      cover_prompt_template_id: selectedCoverPromptTemplateId.value || undefined,
      cover_model_config_id: selectedCoverModelConfigId.value || undefined,
      video_prompt_template_id: selectedVideoPromptTemplateId.value || undefined,
      video_model_config_id: selectedVideoModelConfigId.value || undefined,
      cover_aspect_ratio: coverAspectRatio.value,
      cover_title: coverTitle.value,
      video_aspect_ratio: videoAspectRatio.value,
      video_duration: videoDuration.value,
      video_workflow_type: videoWorkflowType.value,
    }
    const res = await generateFullCase(params)

    scriptContent.value = res.data.script_content
    videoPrompts.value = res.data.video_prompts
    coverPrompt.value = res.data.cover_prompt
    activeTab.value = 'script'

    addChatMessage('assistant', '🎉 全案生成完成！口播文案、视频分镜提示词和封面提示词已就绪。\n\n你可以在下方模块区查看各项内容。如需修改，直接告诉我，例如：\n- 「把开头改得更有冲击力」\n- 「第三个分镜改为户外场景」\n- 「封面加上科技感元素」')
  } catch (err: any) {
    addChatMessage('assistant', `❌ 生成失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isGenerating.value = false
  }
}

async function handleUseTopicAndGenerate() {
  if (isLoading.value || isGenerating.value) return
  if (inputMode.value !== 'topic') return
  const topic = topicInput.value.trim()
  if (!topic) {
    addChatMessage('system', '请先输入选题、标题或口播主题。')
    return
  }
  extractedContent.value = `选题主题：${topic}`
  activeTab.value = 'extracted'
  addChatMessage('assistant', '✅ 已记录口播主题，并开始生成全案。')
  await nextTick()
  await handleGenerate()
}

async function handleCreateColumn() {
  if (isCreatingColumn.value || !quickColumn.name?.trim()) return
  isCreatingColumn.value = true
  try {
    const res = await createColumn({
      ...quickColumn,
      persona_id: selectedPersonaId.value,
      default_template: quickColumn.default_template || '1080x1920/image_default.html',
      default_voice: quickColumn.default_voice || 'zh-CN-YunjianNeural',
      default_bgm: quickColumn.default_bgm || '',
    })
    await loadColumns()
    selectedColumnId.value = res.data.id
    addChatMessage('assistant', `✅ 已创建栏目「${res.data.name}」，后续全案会按该栏目结构生成。`)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 栏目创建失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isCreatingColumn.value = false
  }
}

async function handleGenerateTopics() {
  if (isStrategyLoading.value) return
  if (!extractedContent.value.trim()) {
    addChatMessage('assistant', '⚠️ 请先提取内容或分析素材，再生成选题。')
    return
  }
  isStrategyLoading.value = true
  activeTab.value = 'strategy'
  try {
    const res = await generateTopicPlan({
      extracted_content: extractedContent.value,
      persona_id: selectedPersonaId.value,
      column_id: selectedColumnId.value,
      count: 6,
      extra_requirements: extraRequirements.value,
    })
    strategyOutputs.topics = res.data
    addChatMessage('assistant', '🧭 已生成选题策划，可在「选题策略」版块查看。')
  } catch (err: any) {
    addChatMessage('assistant', `❌ 选题策划失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isStrategyLoading.value = false
  }
}

async function handleOptimizeHooks() {
  if (isStrategyLoading.value) return
  if (!scriptContent.value.trim()) {
    addChatMessage('assistant', '⚠️ 请先生成口播文案，再优化黄金 3 秒开头。')
    return
  }
  isStrategyLoading.value = true
  activeTab.value = 'strategy'
  try {
    const res = await optimizeHooks({
      script_content: scriptContent.value,
      persona_id: selectedPersonaId.value,
      column_id: selectedColumnId.value,
      count: 5,
    })
    strategyOutputs.hooks = res.data
    addChatMessage('assistant', '⚡ 已生成黄金 3 秒开头备选，可在「选题策略」版块查看。')
  } catch (err: any) {
    addChatMessage('assistant', `❌ 开头优化失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isStrategyLoading.value = false
  }
}

async function handleGeneratePublishPackage() {
  if (isStrategyLoading.value) return
  if (!scriptContent.value.trim()) {
    addChatMessage('assistant', '⚠️ 请先生成口播文案，再生成发布全案。')
    return
  }
  isStrategyLoading.value = true
  activeTab.value = 'publish'
  try {
    const res = await generatePublishPackage({
      script_content: scriptContent.value,
      cover_prompt: coverPrompt.value,
      target_platform: targetPlatform.value,
      persona_id: selectedPersonaId.value,
      column_id: selectedColumnId.value,
    })
    strategyOutputs.publishPackage = res.data
    addChatMessage('assistant', '📣 已生成标题、发布文案、评论区引导和私信承接话术。')
  } catch (err: any) {
    addChatMessage('assistant', `❌ 发布全案生成失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isStrategyLoading.value = false
  }
}

async function handleQualityCheck() {
  if (isStrategyLoading.value) return
  if (!scriptContent.value.trim()) {
    addChatMessage('assistant', '⚠️ 请先生成口播文案，再做发布前质检。')
    return
  }
  isStrategyLoading.value = true
  activeTab.value = 'publish'
  try {
    const res = await qualityCheck({
      script_content: scriptContent.value,
      cover_prompt: coverPrompt.value,
      publish_copy: strategyOutputs.publishPackage ? JSON.stringify(strategyOutputs.publishPackage) : '',
      persona_id: selectedPersonaId.value,
      column_id: selectedColumnId.value,
    })
    strategyOutputs.quality = res.data
    addChatMessage('assistant', `✅ 发布前质检完成，总分：${res.data.total_score ?? '-'}。`)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 质检失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isStrategyLoading.value = false
  }
}

async function handleBuildShortVideoWorkflow() {
  if (isShortVideoLoading.value) return
  const userInput = shortVideoForm.user_input.trim() || extractedContent.value.trim()
  if (!userInput) {
    addChatMessage('assistant', '⚠️ 请先输入短视频需求，或先提取/分析素材。')
    return
  }

  isShortVideoLoading.value = true
  activeTab.value = 'shortVideo'
  try {
    const res = await buildShortVideoWorkflow({
      ...shortVideoForm,
      user_input: userInput,
      subject_name: shortVideoForm.subject_name.trim() || '主体',
      target_audience: shortVideoForm.target_audience.trim() || '目标用户',
      core_message: shortVideoForm.core_message.trim() || '核心卖点或核心观点',
    })
    strategyOutputs.shortVideoWorkflow = res.data
    const intent = res.data.intent
    if (intent.intent === 'unknown') {
      addChatMessage('assistant', '🎞️ 暂未识别出明确短视频场景，已生成补问信息。')
    } else {
      addChatMessage('assistant', `🎞️ 已识别为「${intent.label}」，置信度 ${Math.round(intent.confidence * 100)}%，并生成完整工作流提示词。`)
    }
  } catch (err: any) {
    addChatMessage('assistant', `❌ 短视频工作流生成失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isShortVideoLoading.value = false
  }
}

function buildVideoAipParams() {
  return {
    title: videoAipProductName.value || videoAipCharacterNotes.value || undefined,
    workflow_type: videoWorkflowType.value,
    source_content: extractedContent.value,
    script_content: scriptContent.value,
    product_name: videoAipProductName.value || shortVideoForm.subject_name,
    character_notes: videoAipCharacterNotes.value,
    media_notes: analyzedAssets.value.map((asset) => `${asset.filename || '素材'}：${asset.description || ''}`),
    source_assets: analyzedAssets.value.map((asset) => ({
      filename: asset.filename,
      path: asset.path,
      type: asset.type,
      description: asset.description,
    })),
    aspect_ratio: videoAspectRatio.value,
    duration: videoDuration.value,
    style: shortVideoForm.style,
    user_requirements: extraRequirements.value || shortVideoForm.user_input,
    text_model_config_id: selectedTextModelConfigId.value || undefined,
    video_prompt_template_id: selectedVideoPromptTemplateId.value || undefined,
    video_model_config_id: selectedVideoModelConfigId.value || undefined,
  }
}

async function handleGenerateVideoAipPlan() {
  if (isVideoAipPlanning.value) return
  const userInput = extractedContent.value.trim() || shortVideoForm.user_input.trim() || scriptContent.value.trim()
  if (!userInput && videoWorkflowType.value !== 'drama') {
    addChatMessage('assistant', '⚠️ 请先上传产品图/媒体素材，或输入产品宣传需求。')
    return
  }
  if (videoWorkflowType.value === 'drama' && !videoAipCharacterNotes.value.trim() && !userInput) {
    addChatMessage('assistant', '⚠️ 请先上传人物图片，或填写人物关系和剧情要求。')
    return
  }

  isVideoAipPlanning.value = true
  activeTab.value = 'video'
  try {
    const res = await generateVideoAipPlan(buildVideoAipParams())
    videoAipPlan.value = res.data
    videoAipProject.value = null
    videoPrompts.value = res.data.steps?.map((step: any) => `## ${step.title}\n${step.prompt}`).join('\n\n') || ''
    addChatMessage('assistant', `✅ 已生成「${res.data.title}」，可在视频 AIP 板块逐步复制或应用提示词。`)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 视频 AIP 链路生成失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isVideoAipPlanning.value = false
  }
}

async function handleCreateVideoAipProject() {
  if (isSavingVideoAipProject.value) return
  const userInput = extractedContent.value.trim() || shortVideoForm.user_input.trim() || scriptContent.value.trim() || videoAipCharacterNotes.value.trim()
  if (!userInput) {
    addChatMessage('assistant', '⚠️ 请先输入需求、上传素材，或填写人物关系后再创建 AIP 项目。')
    return
  }
  isSavingVideoAipProject.value = true
  activeTab.value = 'video'
  try {
    const res = await createVideoAipProject(buildVideoAipParams())
    videoAipProject.value = res.data
    videoAipPlan.value = res.data.plan || null
    videoPrompts.value = (res.data.steps || []).map((step: VideoAipStepTask) => `## ${step.title}\n${step.prompt}`).join('\n\n')
    addChatMessage('assistant', `✅ 已创建视频 AIP 项目「${res.data.title}」，步骤状态已保存。`)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 创建视频 AIP 项目失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isSavingVideoAipProject.value = false
  }
}

async function markVideoAipStep(step: VideoAipStepTask | any, status: 'running' | 'succeeded' | 'failed') {
  if (!videoAipProject.value || !step.id) return
  try {
    const res = await updateVideoAipStep(videoAipProject.value.id, step.id, {
      status,
      output: status === 'succeeded' ? { prompt: step.prompt, completed_at: new Date().toISOString() } : {},
      error_message: status === 'failed' ? '用户手动标记失败' : '',
    })
    videoAipProject.value = res.data
    addChatMessage('system', `已更新「${step.title}」为 ${status}。`)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 更新 AIP 步骤失败：${err?.response?.data?.detail || err.message}`)
  }
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function patchVideoAipStep(stepId: number, patch: Partial<VideoAipStepTask>) {
  if (!videoAipProject.value?.steps) return
  const idx = videoAipProject.value.steps.findIndex((item: any) => item.id === stepId)
  if (idx < 0) return
  videoAipProject.value.steps[idx] = {
    ...videoAipProject.value.steps[idx],
    ...patch,
    output: {
      ...(videoAipProject.value.steps[idx].output || {}),
      ...(patch.output || {}),
    },
  }
}

function isRemoteMediaUrl(url: string) {
  return /^https?:\/\//i.test(url)
}

function videoAipArtifactUrl(step: any) {
  const output = step?.output || {}
  if (output.media_file_url) return output.media_file_url
  if (output.media_url && isRemoteMediaUrl(output.media_url)) return output.media_url
  if (output.task_id && (step?.status === 'succeeded' || step?.displayStatus === 'succeeded')) return videoTaskMediaFileUrl(output.task_id)
  return ''
}

function isVideoAipVideoStep(step: any) {
  const output = step?.output || {}
  return output.media_type === 'video' || output.task_type === 'video' || step.task_type === 'video'
}

function videoAipProgressText(step: any) {
  const output = step?.output || {}
  if (typeof output.progress !== 'number') return ''
  return `${Math.round(output.progress * 100)}%`
}

async function pollVideoAipStepTask(step: VideoAipStepTask | any, taskId: string) {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    await sleep(attempt === 0 ? 1200 : 2000)
    const task = await getVideoTask(taskId)
    const output = {
      ...(step.output || {}),
      task_id: task.task_id,
      task_status: task.status,
      progress: task.progress,
      current_event: task.current_event,
      media_type: task.media_type || step.output?.media_type,
      media_url: task.media_url,
      media_path: task.media_path,
      media_file_url: (task.media_path || task.video_path) ? videoTaskMediaFileUrl(task.task_id) : task.media_url,
      video_path: task.video_path,
      duration: task.duration,
      file_size: task.file_size,
    }
    patchVideoAipStep(step.id, { status: task.status as VideoAipStepTask['status'], output })

    if (task.status === 'succeeded') {
      if (videoAipProject.value) {
        const res = await updateVideoAipStep(videoAipProject.value.id, step.id, {
          status: 'succeeded',
          output,
          error_message: '',
        })
        videoAipProject.value = res.data
      }
      addChatMessage('assistant', `✅ 「${step.title}」真实模型任务已完成，产物已回写到 AIP 步骤。`)
      return
    }

    if (task.status === 'failed') {
      if (videoAipProject.value) {
        const res = await updateVideoAipStep(videoAipProject.value.id, step.id, {
          status: 'failed',
          output,
          error_message: task.error || '模型任务失败',
        })
        videoAipProject.value = res.data
      }
      addChatMessage('assistant', `❌ 「${step.title}」真实模型任务失败：${task.error || '未知错误'}`)
      return
    }
  }
  addChatMessage('assistant', `⚠️ 「${step.title}」任务仍在运行，可稍后刷新项目查看结果。`)
}

async function handleRunVideoAipStep(step: VideoAipStepTask | any) {
  if (!videoAipProject.value || !step.id || runningVideoAipStepIds[step.id]) return
  runningVideoAipStepIds[step.id] = true
  try {
    const res = await runVideoAipStep(videoAipProject.value.id, step.id)
    videoAipProject.value = res.data.project
    const taskId = res.data.task.task_id
    addChatMessage('assistant', `🚀 已提交「${step.title}」真实${res.data.task.media_type === 'video' ? '视频' : '图片'}模型任务，开始轮询生成结果。`)
    await pollVideoAipStepTask(step, taskId)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 执行 AIP 步骤失败：${err?.response?.data?.detail?.message || err?.response?.data?.detail || err.message}`)
  } finally {
    runningVideoAipStepIds[step.id] = false
  }
}

async function pollVideoAipProject(projectId: number) {
  for (let attempt = 0; attempt < 240; attempt += 1) {
    await sleep(attempt === 0 ? 1200 : 3000)
    const res = await getVideoAipProject(projectId)
    videoAipProject.value = res.data
    videoAipPlan.value = res.data.plan || videoAipPlan.value
    if (res.data.status === 'succeeded') {
      addChatMessage('assistant', `✅ 视频 AIP 项目「${res.data.title}」已全部执行完成。`)
      return
    }
    if (res.data.status === 'failed') {
      addChatMessage('assistant', `❌ 视频 AIP 项目「${res.data.title}」执行中断，请查看失败步骤后重试。`)
      return
    }
  }
  addChatMessage('assistant', '⚠️ 视频 AIP 项目仍在后台执行，可稍后刷新项目状态。')
}

async function handleRunNextVideoAipStep() {
  if (!videoAipProject.value || isRunningVideoAipNext.value) return
  isRunningVideoAipNext.value = true
  try {
    const res = await runNextVideoAipStep(videoAipProject.value.id)
    const task = res.data?.task
    videoAipProject.value = res.data?.project || res.data
    videoAipPlan.value = videoAipProject.value?.plan || videoAipPlan.value
    if (task?.task_id) {
      const step = videoAipProject.value?.steps?.find((item: any) => item.output?.task_id === task.task_id)
      addChatMessage('assistant', '🚀 已提交下一步真实媒体任务，开始轮询结果。')
      if (step) await pollVideoAipStepTask(step, task.task_id)
    } else {
      addChatMessage('assistant', res.message || '没有待执行步骤。')
    }
  } catch (err: any) {
    addChatMessage('assistant', `❌ 执行下一步失败：${err?.response?.data?.detail?.message || err?.response?.data?.detail || err.message}`)
  } finally {
    isRunningVideoAipNext.value = false
  }
}

async function handleRunAllVideoAipSteps() {
  if (!videoAipProject.value || isRunningVideoAipAll.value) return
  isRunningVideoAipAll.value = true
  try {
    const projectId = videoAipProject.value.id
    const res = await runAllVideoAipSteps(projectId)
    videoAipProject.value = res.data
    videoAipPlan.value = res.data.plan || videoAipPlan.value
    addChatMessage('assistant', '🚀 已开始后台顺序执行全部 AIP 步骤，页面会自动刷新项目状态。')
    await pollVideoAipProject(projectId)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 执行全部失败：${err?.response?.data?.detail?.message || err?.response?.data?.detail || err.message}`)
  } finally {
    isRunningVideoAipAll.value = false
  }
}

async function handleRetryVideoAipStep(step: VideoAipStepTask | any) {
  if (!videoAipProject.value || !step.id || runningVideoAipStepIds[step.id]) return
  runningVideoAipStepIds[step.id] = true
  try {
    const res = await retryVideoAipStep(videoAipProject.value.id, step.id)
    videoAipProject.value = res.data.project
    const taskId = res.data.task.task_id
    addChatMessage('assistant', `🔁 已重试「${step.title}」并提交真实模型任务。`)
    await pollVideoAipStepTask(step, taskId)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 重试 AIP 步骤失败：${err?.response?.data?.detail?.message || err?.response?.data?.detail || err.message}`)
  } finally {
    runningVideoAipStepIds[step.id] = false
  }
}

function applyShortVideoStepToTab(stepKey: string, prompt: string) {
  if (stepKey === 'script') {
    scriptContent.value = prompt
    activeTab.value = 'script'
  } else if (stepKey === 'final_prompt' || stepKey === 'storyboard' || stepKey === 'four_views') {
    videoPrompts.value = prompt
    activeTab.value = 'video'
  } else if (stepKey === 'publish') {
    strategyOutputs.publishPackage = { short_video_prompt: prompt }
    activeTab.value = 'publish'
  } else {
    extractedContent.value = prompt
    activeTab.value = 'extracted'
  }
  addChatMessage('system', `已应用「${stepKey}」提示词到对应内容版块。`)
}

function applyVideoAipStep(step: { key?: string; step_key?: string; prompt: string; title: string }) {
  videoPrompts.value = step.prompt
  activeTab.value = 'video'
  addChatMessage('system', `已应用「${step.title}」到视频提示词版块。`)
}

function copyVideoAipPlan() {
  if (!videoAipPlan.value) return
  copyToClipboard(videoAipPlan.value.steps.map((step: any) => `## ${step.title}\n目标：${step.goal}\n\n${step.prompt}`).join('\n\n'))
}

function safeFilename(value: string) {
  return (value || '短视频工作流')
    .replace(/[\\/:*?"<>|]/g, '-')
    .replace(/\s+/g, '-')
    .slice(0, 80)
}

function downloadTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function buildContentMarkdown(title: string, content: string) {
  const createdAt = new Date().toLocaleString('zh-CN', { hour12: false })
  return [
    `# ${title}`,
    '',
    `- 导出时间：${createdAt}`,
    `- 当前平台：${targetPlatform.value}`,
    `- 内容类型：${activeTabLabelMap[activeTab.value]}`,
    '',
    '## 内容正文',
    '',
    '```text',
    content,
    '```',
    '',
    '## 下一步',
    '',
    '- 复制给团队复核',
    '- 发送到提词器演练',
    '- 发布前做质检和平台适配',
  ].join('\n')
}

function exportCurrentContentMarkdown() {
  if (!currentContent.value.trim()) {
    addChatMessage('system', '当前内容版块还没有可导出的内容。')
    return
  }

  const title = activeTabLabelMap[activeTab.value]
  const date = new Date().toISOString().slice(0, 10)
  downloadTextFile(`${date}-${safeFilename(title)}-导出.md`, buildContentMarkdown(title, currentContent.value))
  addChatMessage('system', `${title} 已导出为 Markdown 文件。`)
}

function buildShortVideoArchiveMarkdown() {
  const workflow = strategyOutputs.shortVideoWorkflow
  if (!workflow) return ''

  const createdAt = new Date().toLocaleString('zh-CN', { hour12: false })
  const title = shortVideoForm.subject_name || workflow.variables['主体名称'] || workflow.intent.label
  const lines: string[] = []

  lines.push(`# ${title} - AI短视频工作流归档`)
  lines.push('')
  lines.push('## 项目信息')
  lines.push('')
  lines.push(`- 创建时间：${createdAt}`)
  lines.push(`- 识别场景：${workflow.intent.label}`)
  lines.push(`- 置信度：${Math.round(workflow.intent.confidence * 100)}%`)
  lines.push(`- 推荐命令：${workflow.workflow?.recommended_command || '-'}`)
  lines.push(`- 模板文档：${workflow.workflow?.template_doc || '-'}`)
  lines.push(`- 命中关键词：${workflow.intent.matched_keywords.length ? workflow.intent.matched_keywords.join('、') : '-'}`)
  lines.push('')
  lines.push('## 变量')
  lines.push('')
  Object.entries(workflow.variables).forEach(([key, value]) => {
    lines.push(`- ${key}：${value}`)
  })

  if (workflow.questions?.length) {
    lines.push('')
    lines.push('## 需要补充的信息')
    lines.push('')
    workflow.questions.forEach((question: any, idx: number) => {
      lines.push(`${idx + 1}. ${question}`)
    })
  }

  if (workflow.steps.length) {
    lines.push('')
    lines.push('## 工作流步骤')
    workflow.steps.forEach((step: any, idx: number) => {
      lines.push('')
      lines.push(`### ${idx + 1}. ${step.label}`)
      lines.push('')
      lines.push(`说明：${step.description}`)
      lines.push('')
      lines.push('```text')
      lines.push(step.prompt)
      lines.push('```')
    })
  }

  if (workflow.next_actions.length) {
    lines.push('')
    lines.push('## 下一步建议')
    lines.push('')
    workflow.next_actions.forEach((action: any, idx: number) => {
      lines.push(`${idx + 1}. ${action}`)
    })
  }

  lines.push('')
  lines.push('## 复盘记录')
  lines.push('')
  lines.push('```text')
  lines.push('生成结果：')
  lines.push('主体一致性问题：')
  lines.push('镜头连续性问题：')
  lines.push('发布平台：')
  lines.push('发布时间：')
  lines.push('数据表现：')
  lines.push('下一轮优化：')
  lines.push('```')

  return lines.join('\n')
}

function exportShortVideoWorkflowMarkdown() {
  const markdown = buildShortVideoArchiveMarkdown()
  if (!markdown) return
  const subject = shortVideoForm.subject_name || strategyOutputs.shortVideoWorkflow?.intent.label || '短视频工作流'
  const date = new Date().toISOString().slice(0, 10)
  downloadTextFile(`${date}-${safeFilename(subject)}-短视频工作流归档.md`, markdown)
  addChatMessage('system', '📦 短视频工作流归档已导出为 Markdown 文件')
}

async function saveShortVideoWorkflowProject() {
  const workflow = strategyOutputs.shortVideoWorkflow
  if (isSavingShortVideoProject.value || !workflow) return 0

  const markdown = buildShortVideoArchiveMarkdown()
  const title = shortVideoForm.subject_name || workflow.variables['主体名称'] || workflow.intent.label
  isSavingShortVideoProject.value = true
  try {
    const res = await saveShortVideoProject({
      title: `${title} - ${workflow.intent.label}`,
      subject_name: shortVideoForm.subject_name || workflow.variables['主体名称'] || '',
      intent_key: workflow.intent.intent,
      intent_label: workflow.intent.label,
      confidence: workflow.intent.confidence,
      platform: shortVideoForm.platform,
      aspect_ratio: shortVideoForm.aspect_ratio,
      duration: shortVideoForm.duration,
      model: shortVideoForm.model,
      style: shortVideoForm.style,
      target_audience: shortVideoForm.target_audience,
      core_message: shortVideoForm.core_message,
      user_input: shortVideoForm.user_input || workflow.variables['视频主题'] || '',
      workflow,
      archive_markdown: markdown,
    })
    savedShortVideoProjectId.value = res.data.id
    addChatMessage('assistant', `✅ 已保存到短视频项目库：#${res.data.id} ${res.data.title}`)
    return res.data.id
  } catch (err: any) {
    addChatMessage('assistant', `❌ 保存短视频项目失败：${err?.response?.data?.detail || err.message}`)
    return 0
  } finally {
    isSavingShortVideoProject.value = false
  }
}

async function handleCreateVideoAipFromShortVideoProject() {
  const workflow = strategyOutputs.shortVideoWorkflow
  if (isCreatingAipFromShortVideo.value || !workflow) return
  isCreatingAipFromShortVideo.value = true
  activeTab.value = 'video'
  try {
    const projectId = savedShortVideoProjectId.value || await saveShortVideoWorkflowProject()
    if (!projectId) return
    const res = await createVideoAipProjectFromShortVideo(projectId)
    videoAipProject.value = res.data
    videoAipPlan.value = res.data.plan || null
    videoPrompts.value = (res.data.steps || []).map((step: VideoAipStepTask) => `## ${step.title}\n${step.prompt}`).join('\n\n')
    addChatMessage('assistant', `✅ 已从短视频工作流创建视频 AIP 项目「${res.data.title}」。`)
  } catch (err: any) {
    addChatMessage('assistant', `❌ 转入视频 AIP 失败：${err?.response?.data?.detail || err.message}`)
  } finally {
    isCreatingAipFromShortVideo.value = false
  }
}

// ─── 视频引擎 actions ──────────────────────────────────────

async function handleChatSend() {
  const msg = chatInput.value.trim()
  if (!msg || isCopilotStreaming.value) return

  addChatMessage('user', msg)
  chatInput.value = ''

  if (!currentContent.value) {
    addChatMessage('assistant', '⚠️ 当前没有可修改的内容。请先上传素材并生成全案。')
    return
  }

  isCopilotStreaming.value = true
  let accumulatedContent = ''

  // Add placeholder assistant message
  const assistantIdx = chatMessages.length
  chatMessages.push({
    role: 'assistant',
    content: '',
    timestamp: Date.now(),
  })

  copilotModifyStream(
    {
      content_type: contentTypeMap[activeTab.value],
      current_content: currentContent.value,
      user_instruction: msg,
      persona_id: selectedPersonaId.value,
    },
    (chunk: string) => {
      accumulatedContent += chunk
      chatMessages[assistantIdx].content = accumulatedContent
      scrollChatToBottom()
    },
    () => {
      // On done - update the left panel with modified content
      const finalContent = accumulatedContent
      const separator = finalContent.lastIndexOf('---')
      const updatedContent = separator > 0 ? finalContent.substring(0, separator).trim() : finalContent

      switch (activeTab.value) {
        case 'script': scriptContent.value = updatedContent; break
        case 'video': videoPrompts.value = updatedContent; break
        case 'cover': coverPrompt.value = updatedContent; break
        case 'extracted': extractedContent.value = updatedContent; break
        default:
          addChatMessage('system', '该内容版块暂不支持自动回写，已在对话中生成修改稿，请复制后手动应用。')
      }

      isCopilotStreaming.value = false
      scrollChatToBottom()
    },
    (err: string) => {
      chatMessages[assistantIdx].content = `❌ 修改失败：${err}`
      isCopilotStreaming.value = false
    }
  )
}

function addChatMessage(role: 'user' | 'assistant' | 'system', content: string) {
  chatMessages.push({ role, content, timestamp: Date.now() })
  scrollChatToBottom()
}

function scrollChatToBottom() {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
    }
  })
}

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    fileInput.value = target.files[0]
  }
}

function handleMediaFilesChange(e: Event) {
  const target = e.target as HTMLInputElement
  mediaFiles.value = target.files ? Array.from(target.files) : []
  analyzedAssets.value = []
}

function handleChatKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleChatSend()
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
    .then(() => addChatMessage('system', '📋 内容已复制到剪贴板'))
    .catch(() => addChatMessage('system', '复制失败：浏览器禁止访问剪贴板，请手动选中文本复制。'))
}

// ─── 反转剧编剧 State ───────────────────────────────────────

type WorkspaceMode = 'home' | ToolKey

interface WorkspaceUser {
  name: string
  email: string
  token?: string
  isGuest?: boolean
  is_admin?: boolean
}

interface ReversalDramaHistoryItem {
  id: string
  createdAt: string
  title: string
  productName: string
  painPoint: string
  params: {
    product_name: string
    product_function: string
    pain_point: string
    characters: ReversalCharacter[] | null
    platform: string
    duration: string
    extra_requirements: string
  }
  result: ReversalDramaResult
}

const props = defineProps<{
  currentUser?: WorkspaceUser
  initialMode?: WorkspaceMode
}>()

const emit = defineEmits<{
  logout: []
}>()

const REVERSAL_HISTORY_KEY = 'ip-case-reversal-drama-history'
const router = useRouter()
const isGuestUser = computed(() => props.currentUser?.isGuest === true && !props.currentUser?.token)
const isAdminUser = computed(() => props.currentUser?.is_admin === true || (Boolean(props.currentUser?.token) && props.currentUser?.is_admin !== false))

const workspaceMode = ref<WorkspaceMode>('home')
const liveStatusMessage = computed(() => {
  return modelGatewayFeedback.value?.message
    || promptManagerFeedback.value?.message
    || dramaFeedback.value?.message
    || ''
})

const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: '确认',
  cancelText: '取消',
  tone: 'danger' as 'danger' | 'warning' | 'default',
})
let confirmResolver: ((value: boolean) => void) | null = null

function requestConfirmation(options: {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  tone?: 'danger' | 'warning' | 'default'
}) {
  confirmState.open = true
  confirmState.title = options.title
  confirmState.message = options.message
  confirmState.confirmText = options.confirmText || '确认'
  confirmState.cancelText = options.cancelText || '取消'
  confirmState.tone = options.tone || 'danger'
  return new Promise<boolean>((resolve) => {
    confirmResolver = resolve
  })
}

function resolveConfirmation(value: boolean) {
  confirmState.open = false
  confirmResolver?.(value)
  confirmResolver = null
}

const workspaceMetrics = computed(() => [
  { label: '输入素材', value: extractedContent.value.trim() ? '已解析' : '待解析', state: extractedContent.value.trim() ? 'done' : 'pending' },
  { label: '脚本文案', value: scriptContent.value.trim() ? '已生成' : '待生成', state: scriptContent.value.trim() ? 'done' : 'pending' },
  { label: '内容输出', value: outputStatus.value, state: outputStatus.value === '已输出' ? 'done' : 'pending' },
])

const productionSteps = computed(() => [
  { label: '提取素材', done: Boolean(extractedContent.value.trim()) },
  { label: '生成脚本', done: Boolean(scriptContent.value.trim()) },
  { label: '发送提词', done: Boolean(teleprompterInitialText.value.trim()) },
  { label: '整理输出', done: outputStatus.value === '已输出' },
])

const activeTabLabelMap: Record<typeof activeTab.value, string> = {
  extracted: '内容提取',
  shortVideo: '短视频工作流',
  strategy: '选题策略',
  script: '口播文案',
  video: '视频提示词',
  cover: '封面提示词',
  publish: '发布全案',
}

const workspaceHashMap: Record<ToolKey, string> = {
  ip: 'ip',
  sprint1: 'sprint1',
  platform: 'platform',
  reversal: 'reversal',
  teleprompter: 'teleprompter',
  wechat: 'wechat',
  models: 'models',
  prompts: 'prompts',
}

const modeFromHash = (hash = window.location.hash): WorkspaceMode => {
  if (isGuestUser.value) return 'teleprompter'
  const value = hash.replace(/^#\/?/, '')
  if (value === 'prompts' && !isAdminUser.value) return 'home'
  if (value === 'ip' || value === 'sprint1' || value === 'platform' || value === 'reversal' || value === 'teleprompter' || value === 'wechat' || value === 'models' || value === 'prompts') return value
  return props.initialMode || 'home'
}

workspaceMode.value = modeFromHash()

function selectWorkspaceMode(mode: WorkspaceMode) {
  if (isGuestUser.value && mode !== 'teleprompter') {
    workspaceMode.value = 'teleprompter'
    if (window.location.hash !== '#/teleprompter') window.location.hash = '#/teleprompter'
    return
  }
  if (mode === 'prompts' && !isAdminUser.value) {
    workspaceMode.value = 'home'
    if (window.location.hash) history.pushState(null, '', window.location.pathname + window.location.search)
    return
  }

  workspaceMode.value = mode
  const nextHash = mode === 'home' ? '' : `#/${workspaceHashMap[mode]}`
  const nextPath = modePathMap[mode]
  if (nextPath && router.currentRoute.value.path !== nextPath) {
    router.push(nextPath)
    return
  }
  if (window.location.hash !== nextHash) {
    if (mode === 'home') {
      history.pushState(null, '', window.location.pathname + window.location.search)
    } else {
      window.location.hash = nextHash
    }
  }
}

function handleHashChange() {
  workspaceMode.value = modeFromHash()
  if (isGuestUser.value && window.location.hash !== '#/teleprompter') {
    window.location.hash = '#/teleprompter'
  }
}

watch(
  () => props.initialMode,
  (mode) => {
    if (!mode || isGuestUser.value) return
    if (mode === 'prompts' && !isAdminUser.value) {
      workspaceMode.value = 'home'
      return
    }
    workspaceMode.value = mode
  }
)

watch(
  () => props.currentUser?.is_admin,
  () => {
    if (workspaceMode.value === 'prompts' && !isAdminUser.value) {
      selectWorkspaceMode('home')
      return
    }
    if (window.location.hash.replace(/^#\/?/, '') === 'prompts' && isAdminUser.value) {
      workspaceMode.value = 'prompts'
    }
  }
)

function openVoiceTeleprompter(text = currentContent.value) {
  if (!text.trim()) {
    addChatMessage('system', '当前内容版块还没有可跟读的内容。')
    return
  }

  teleprompterInitialText.value = text
  selectWorkspaceMode('teleprompter')
}

onMounted(() => {
  window.addEventListener('hashchange', handleHashChange)
  if (isGuestUser.value) selectWorkspaceMode('teleprompter')
})

onUnmounted(() => {
  window.removeEventListener('hashchange', handleHashChange)
})

const drama = reactive({
  product_name: '',
  product_function: '',
  pain_point: '',
  platform: '视频号+抖音',
  duration: '30-60秒',
  extra_requirements: '',
  useCustomCharacters: false,
})

const dramaCharacters = reactive<ReversalCharacter[]>([
  { name: '', gender: '', role: '', personality: '', catchphrase: '' },
])

const isGeneratingDrama = ref(false)
const dramaResult = ref<ReversalDramaResult | null>(null)
const dramaFeedback = ref<{ type: 'info' | 'success' | 'error'; message: string } | null>(null)
const reversalHistory = ref<ReversalDramaHistoryItem[]>([])

const dramaRequiredReason = computed(() => {
  if (!drama.product_name.trim()) return '请先填写推销产品的产品名。'
  if (!drama.product_function.trim()) return '请先填写产品的一句话功能。'
  if (!drama.pain_point.trim()) return '请先填写要打的痛点。'
  return ''
})

const dramaGenerateReason = computed(() => {
  if (isGuestUser.value) return '游客模式不能生成反转剧。请注册或登录后使用，生成结果会自动保存到历史记录。'
  return dramaRequiredReason.value
})

const reversalComplianceChecks = computed(() => {
  const text = [
    dramaResult.value?.raw_markdown || '',
    dramaResult.value?.overview?.title || '',
    dramaResult.value?.overview?.pain_point || '',
  ].join('\n')
  const hasAny = (keywords: string[]) => keywords.some((keyword) => text.includes(keyword))

  return [
    {
      label: '避免绝对化用语',
      passed: !hasAny(['最好', '第一', '顶级', '全网唯一', '绝对', '百分百', '100%']),
      suggestion: '将“最好/第一/绝对/百分百”改成“更适合/更高效/有机会提升”。',
    },
    {
      label: '避免效果或收益承诺',
      passed: !hasAny(['保证', '稳赚', '躺赚', '包过', '一定赚钱', '保证有效']),
      suggestion: '用“帮助改善/降低试错成本/视实际情况而定”替换确定性承诺。',
    },
    {
      label: '避免恶意贬损竞品或人群',
      passed: !hasAny(['吊打', '秒杀竞品', '垃圾', '废物', '傻子']),
      suggestion: '用“相比传统方式更适合某场景”替代攻击性表达。',
    },
    {
      label: '高风险行业发布前人工复核',
      passed: !hasAny(['医美', '金融', '理财', '贷款', '教育包过', '招商加盟', '保健', '治疗']),
      suggestion: '涉及医美、金融、教育、健康、招商加盟时，发布前必须人工审查。',
    },
  ]
})

watch(
  () => [drama.product_name, drama.product_function, drama.pain_point],
  () => {
    if (!isGeneratingDrama.value && dramaFeedback.value?.type === 'error') {
      dramaFeedback.value = null
    }
  }
)

watch(
  () => props.currentUser?.email,
  () => loadReversalHistory(),
  { immediate: true }
)

function getReversalHistoryStorageKey() {
  return `${REVERSAL_HISTORY_KEY}:${props.currentUser?.email || 'anonymous'}`
}

async function loadReversalHistory() {
  if (!props.currentUser || props.currentUser.isGuest) {
    reversalHistory.value = []
    return
  }

  try {
    const res = await listReversalDramaHistory(30)
    reversalHistory.value = res.data as ReversalDramaHistoryItem[]
    return
  } catch {
    // 后端不可用时保留本地历史兜底，避免用户资产在开发环境不可见。
  }

  try {
    const raw = window.localStorage.getItem(getReversalHistoryStorageKey())
    const items = raw ? JSON.parse(raw) : []
    reversalHistory.value = Array.isArray(items) ? items : []
  } catch {
    reversalHistory.value = []
  }
}

function saveLocalReversalHistory(params: ReversalDramaHistoryItem['params'], result: ReversalDramaResult) {
  if (!props.currentUser || props.currentUser.isGuest) return

  const item: ReversalDramaHistoryItem = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    title: result.overview?.title || params.product_name || '未命名反转剧',
    productName: params.product_name,
    painPoint: params.pain_point,
    params,
    result,
  }

  reversalHistory.value = [item, ...reversalHistory.value].slice(0, 30)
  persistReversalHistory()
}

function persistReversalHistory() {
  if (!props.currentUser || props.currentUser.isGuest) return
  window.localStorage.setItem(getReversalHistoryStorageKey(), JSON.stringify(reversalHistory.value))
}

function restoreReversalHistory(item: ReversalDramaHistoryItem) {
  drama.product_name = item.params.product_name
  drama.product_function = item.params.product_function
  drama.pain_point = item.params.pain_point
  drama.platform = item.params.platform
  drama.duration = item.params.duration
  drama.extra_requirements = item.params.extra_requirements
  drama.useCustomCharacters = Boolean(item.params.characters?.length)
  dramaCharacters.splice(0, dramaCharacters.length, ...(item.params.characters?.length ? item.params.characters : [{ name: '', gender: '', role: '', personality: '', catchphrase: '' }]))
  dramaResult.value = item.result
  dramaFeedback.value = { type: 'success', message: `已恢复历史记录：《${item.title}》。` }
}

async function deleteReversalHistory(item: ReversalDramaHistoryItem) {
  const confirmed = await requestConfirmation({
    title: '删除历史记录',
    message: `确认删除历史记录《${item.title}》吗？删除后该条本地/云端历史将不再出现在列表中。`,
    confirmText: '删除',
  })
  if (!confirmed) return
  try {
    await deleteReversalDramaHistory(item.id)
  } catch {
    // 本地兜底删除继续执行。
  }
  reversalHistory.value = reversalHistory.value.filter((record) => record.id !== item.id)
  persistReversalHistory()
  if (dramaResult.value === item.result) {
    dramaResult.value = null
  }
  dramaFeedback.value = { type: 'info', message: '已删除该历史记录。' }
}

async function clearReversalHistory() {
  if (!reversalHistory.value.length) return
  const confirmed = await requestConfirmation({
    title: '清空反转剧历史',
    message: '确认清空全部反转剧历史记录吗？此操作不可撤销。',
    confirmText: '清空全部',
  })
  if (!confirmed) return
  try {
    await clearReversalDramaHistory()
  } catch {
    // 本地兜底清空继续执行。
  }
  reversalHistory.value = []
  persistReversalHistory()
  dramaFeedback.value = { type: 'info', message: '已清空反转剧历史记录。' }
}

function formatDramaHistoryTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function addDramaCharacter() {
  dramaCharacters.push({ name: '', gender: '', role: '', personality: '', catchphrase: '' })
}

function removeDramaCharacter(idx: number) {
  if (dramaCharacters.length <= 1) return
  dramaCharacters.splice(idx, 1)
}

async function handleGenerateDrama() {
  if (isGeneratingDrama.value) return
  if (dramaGenerateReason.value) {
    dramaFeedback.value = { type: 'error', message: dramaGenerateReason.value }
    addChatMessage('assistant', `⚠️ ${dramaGenerateReason.value}`)
    return
  }

  isGeneratingDrama.value = true
  dramaResult.value = null
  dramaFeedback.value = { type: 'info', message: '反转剧编剧智能体正在创作中，预计 15-30 秒。请不要重复点击。' }
  addChatMessage('assistant', '🎬 反转剧编剧智能体正在创作中，预计 15-30 秒...')

  const customChars = drama.useCustomCharacters
    ? dramaCharacters.filter((c) => c.name && c.name.trim())
    : null

  const params = {
    product_name: drama.product_name.trim(),
    product_function: drama.product_function.trim(),
    pain_point: drama.pain_point.trim(),
    characters: customChars && customChars.length ? customChars : null,
    platform: drama.platform,
    duration: drama.duration,
    extra_requirements: drama.extra_requirements,
  }

  try {
    const res = await generateReversalDrama(params)
    dramaResult.value = res.data
    try {
      await loadReversalHistory()
    } catch {
      saveLocalReversalHistory(params, res.data)
    }
    if (!reversalHistory.value.some((item) => Number(item.id) === Number(res.data.history_id))) {
      saveLocalReversalHistory(params, res.data)
    }
    const passed = res.data.checklist.filter((c) => c.passed).length
    const total = res.data.checklist.length
    dramaFeedback.value = {
      type: 'success',
      message: `剧本已生成，自检通过 ${passed}/${total} 项，并已保存到历史记录。`,
    }
    addChatMessage(
      'assistant',
      `🎉 剧本已生成！自检通过 ${passed}/${total} 项。\n标题：《${res.data.overview.title || '未命名'}》\n你可以在右侧的对话框告诉我「第3镜画面再夸张点」「反转改成 B 套路」等指令进一步打磨。`
    )
  } catch (err: any) {
    const message = err?.response?.data?.detail || err.message || '未知错误'
    dramaFeedback.value = { type: 'error', message: `反转剧生成失败：${message}` }
    addChatMessage('assistant', `❌ 反转剧生成失败：${message}`)
  } finally {
    isGeneratingDrama.value = false
  }
}

function copyDramaMarkdown() {
  if (!dramaResult.value) return
  copyToClipboard(dramaResult.value.raw_markdown)
}
</script>

<template>
  <div class="workspace" :class="{ 'workspace-home': workspaceMode === 'home', 'workspace-ip': workspaceMode === 'ip' }">
    <!-- ═══ Header ═══ -->
    <WorkspaceHeader
      :workspace-mode="workspaceMode"
      :current-user="props.currentUser"
      :is-guest-user="isGuestUser"
      :is-admin-user="isAdminUser"
      :is-generating-drama="isGeneratingDrama"
      :drama-generate-reason="dramaGenerateReason"
      @select="selectWorkspaceMode"
      @logout="emit('logout')"
      @generate-drama="handleGenerateDrama"
    />
    <p class="sr-only" role="status" aria-live="polite" :aria-label="liveStatusMessage"></p>

    <!-- ═══ Main Content ═══ -->
    <main class="workspace-main">
      <!-- ─── Home Tool Cards ─── -->
      <section v-if="workspaceMode === 'home'" class="panel panel-full">
        <HomeToolCards @select="selectWorkspaceMode" />
      </section>

      <section v-else-if="workspaceMode === 'sprint1'" class="panel panel-full">
        <Sprint1CaseWorkspace />
      </section>

      <section v-else-if="workspaceMode === 'platform'" class="panel panel-full">
        <PlatformContentStudio
          :initial-title="coverTitle || topicInput || '未命名平台内容'"
          :initial-content="scriptContent || extractedContent"
        />
      </section>

      <section v-else-if="workspaceMode === 'models'" class="panel panel-full glass-card prompt-manager-panel model-gateway-panel">
        <div class="prompt-manager-head">
          <div>
            <span class="section-eyebrow">Model Gateway</span>
            <h1>大模型中转与默认模型</h1>
            <p>填写兼容 OpenAI 的 Base URL 和 API Key 后，系统自动拉取该 Key 下的可用模型，并按文字、图片、视频任务设置默认模型。</p>
          </div>
          <div class="prompt-manager-actions">
            <button class="btn btn-ghost btn-sm" @click="refreshPromptData">刷新</button>
            <button class="btn btn-primary btn-sm" @click="selectWorkspaceMode('ip')">返回生成工作台</button>
          </div>
        </div>

        <div v-if="modelGatewayFeedback" class="prompt-feedback" :class="modelGatewayFeedback.type">
          {{ modelGatewayFeedback.message }}
        </div>

        <div class="model-gateway-grid">
          <section class="prompt-admin-card model-gateway-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>添加大模型中转</h3>
                <p>先测试连接，再同步模型列表。普通用户创建个人中转，管理员可创建全局中转。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetModelGatewayForm">清空表单</button>
            </div>

            <div class="prompt-form model-gateway-form">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">配置名称</label>
                  <input v-model="modelGatewayForm.name" class="input" placeholder="例：我的中转账号" />
                </div>
                <div class="form-row">
                  <label class="form-label">作用范围</label>
                  <select v-model="modelGatewayForm.scope" class="input">
                    <option value="user">个人可用</option>
                    <option v-if="isAdminUser" value="global">全局可用</option>
                  </select>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">Base URL</label>
                  <input v-model="modelGatewayForm.base_url" class="input" placeholder="https://example.com/v1" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">API Key</label>
                  <input v-model="modelGatewayForm.api_key" class="input" type="password" autocomplete="off" placeholder="只加密保存，前端不回显明文" />
                </div>
              </div>
              <div class="prompt-form-actions">
                <label class="checkbox-row">
                  <input v-model="modelGatewayForm.is_active" type="checkbox" />
                  启用中转
                </label>
                <button class="btn btn-primary btn-sm" :disabled="isSavingModelGateway" @click="handleCreateModelGateway">
                  {{ isSavingModelGateway ? '保存中...' : '创建中转' }}
                </button>
              </div>
            </div>
          </section>

          <section class="prompt-admin-card model-gateway-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>默认模型策略</h3>
                <p>生成时优先使用个人默认；没有个人默认时使用后台全局默认；仍没有则按推荐排序兜底。</p>
              </div>
            </div>
            <div class="default-model-grid">
              <article v-for="group in modelCapabilityGroups" :key="group.type" class="default-model-card">
                <span>{{ group.label }}</span>
                <strong>{{ resolvedDefaultName(group.type) }}</strong>
                <small>{{ resolvedDefaultLabel(group.type) }}</small>
                <div class="default-model-actions">
                  <button
                    v-for="model in group.models.slice(0, 3)"
                    :key="model.id"
                    class="btn btn-ghost btn-sm"
                    @click="handleSetPersonalDefault(group.type, model.id || 0)"
                  >设个人默认：{{ model.name }}</button>
                </div>
              </article>
            </div>
          </section>
        </div>

        <section class="prompt-admin-card model-gateway-card">
          <div class="prompt-admin-card-head">
            <div>
              <h3>中转账号</h3>
              <p>测试连接会验证 Key 是否可用；同步模型会调用 `/models` 并写入模型目录。</p>
            </div>
          </div>
          <div class="model-gateway-list">
            <article v-for="gateway in modelGateways" :key="gateway.id" class="model-gateway-item">
              <div>
                <strong>{{ gateway.name }}</strong>
                <span>{{ gateway.scope === 'global' ? '全局' : '个人' }} · {{ gateway.provider_type || 'openai_compatible' }}</span>
                <p>{{ gateway.base_url }}</p>
                <small>Key：{{ gateway.api_key_masked || '未填写' }} · 状态：{{ gateway.last_test_status || 'untested' }} · 模型数：{{ gateway.last_model_count || 0 }}</small>
              </div>
              <div class="prompt-table-actions">
                <button v-if="gateway.scope !== 'global' || isAdminUser" class="btn btn-ghost btn-sm" :disabled="Boolean(gateway.id && modelGatewayBusy[gateway.id])" @click="handleTestModelGateway(gateway)">测试</button>
                <button v-if="gateway.scope !== 'global' || isAdminUser" class="btn btn-primary btn-sm" :disabled="Boolean(gateway.id && modelGatewayBusy[gateway.id])" @click="handleSyncModelGateway(gateway)">同步模型</button>
                <button v-if="gateway.scope !== 'global' || isAdminUser" class="btn btn-ghost btn-sm" @click="handleDeleteModelGateway(gateway)">停用</button>
              </div>
            </article>
            <div v-if="!modelGateways.length" class="module-empty-state prompt-empty-state">
              <strong>暂无模型中转</strong>
              <span>创建中转后点击同步，即可把该 API Key 下的模型加入选择列表。</span>
            </div>
          </div>
        </section>

        <section class="prompt-admin-card model-gateway-card">
          <div class="prompt-admin-card-head">
            <div>
              <h3>模型目录</h3>
              <p>系统会自动猜测模型能力；无法识别的模型请手动标注后再用于生成。</p>
            </div>
          </div>
          <div class="model-catalog-list">
            <article v-for="model in modelManagerConfigs" :key="model.id" class="model-catalog-item">
              <div class="model-catalog-main">
                <strong>{{ model.name }}</strong>
                <span>{{ model.provider }} · {{ model.model_id || '未设置模型 ID' }}</span>
                <p>{{ model.recommendation_label || '暂无推荐标签' }}{{ model.recommendation_reason ? `｜${model.recommendation_reason}` : '' }}</p>
                <small v-if="model.risk_note">风险提示：{{ model.risk_note }}</small>
              </div>
              <div class="model-catalog-controls">
                <select :value="model.model_type" class="input" @change="handleUpdateModelCapabilityFromEvent(model, $event)">
                  <option value="text">文字</option>
                  <option value="image">图片</option>
                  <option value="video">视频</option>
                  <option value="multimodal">多模态</option>
                  <option value="unknown">待标注</option>
                </select>
                <button class="btn btn-ghost btn-sm" @click="handleSetPersonalDefault(model.model_type, model.id || 0)">设个人默认</button>
                <button v-if="isAdminUser" class="btn btn-ghost btn-sm" @click="handleSetGlobalDefault(model.model_type, model.id || 0)">设全局默认</button>
              </div>
            </article>
            <div v-if="!modelManagerConfigs.length" class="module-empty-state prompt-empty-state">
              <strong>暂无可用模型</strong>
              <span>请先添加中转账号并同步模型，或由管理员配置全局模型。</span>
            </div>
          </div>
        </section>
      </section>

      <section v-else-if="workspaceMode === 'prompts' && isAdminUser" class="panel panel-full glass-card prompt-manager-panel">
        <div class="prompt-manager-head">
          <div>
            <span class="section-eyebrow">Prompt Admin</span>
            <h1>提示词分类与模板管理</h1>
            <p>管理前端可选择的口播提示词分类和模板，生成时只注入已启用模板。</p>
          </div>
          <div class="prompt-manager-actions">
            <button class="btn btn-ghost btn-sm" @click="refreshPromptData">刷新</button>
            <button class="btn btn-primary btn-sm" @click="selectWorkspaceMode('ip')">返回生成工作台</button>
          </div>
        </div>

        <div v-if="promptManagerFeedback" class="prompt-feedback" :class="promptManagerFeedback.type">
          {{ promptManagerFeedback.message }}
        </div>

        <div class="prompt-manager-grid">
          <section class="prompt-admin-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>提示词分类</h3>
                <p>分类用于前端筛选模板，例如知识口播、带货种草、直播话术。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetPromptCategoryForm">新建分类</button>
            </div>

            <div class="prompt-category-list">
              <button
                v-for="category in promptTemplateCategories"
                :key="category.key"
                class="prompt-category-item"
                :class="{ active: promptManagerCategoryKey === category.key }"
                @click="promptManagerCategoryKey = category.key"
              >
                <strong>{{ category.name }}</strong>
                <span>{{ category.key }}</span>
              </button>
              <button
                v-if="currentContent"
                class="btn btn-ghost"
                data-testid="copilot-export-current"
                @click="exportCurrentContentMarkdown"
              >导出当前结果</button>
            </div>

            <div class="prompt-form compact-prompt-form">
              <div class="form-row">
                <label class="form-label">分类 Key</label>
                <input v-model="promptCategoryForm.key" class="input" placeholder="knowledge_talk" />
              </div>
              <div class="form-row">
                <label class="form-label">分类名称</label>
                <input v-model="promptCategoryForm.name" class="input" placeholder="知识口播" />
              </div>
              <div class="form-row">
                <label class="form-label">分类说明</label>
                <textarea v-model="promptCategoryForm.description" class="input" rows="2" placeholder="说明该分类适合什么场景"></textarea>
              </div>
              <div class="form-row-inline">
                <div class="form-row">
                  <label class="form-label">排序</label>
                  <input v-model.number="promptCategoryForm.sort_order" class="input" type="number" />
                </div>
                <label class="checkbox-row">
                  <input v-model="promptCategoryForm.is_active" type="checkbox" />
                  启用
                </label>
              </div>
              <div class="prompt-form-actions">
                <button class="btn btn-primary btn-sm" :disabled="isSavingPromptCategory" @click="handleSavePromptCategory">
                  {{ isSavingPromptCategory ? '保存中...' : editingPromptCategoryKey ? '更新分类' : '创建分类' }}
                </button>
                <button class="btn btn-ghost btn-sm" @click="resetPromptCategoryForm">清空</button>
              </div>
            </div>

            <div class="prompt-table-list">
              <article v-for="category in promptTemplateCategories" :key="category.key" class="prompt-table-item">
                <div>
                  <strong>{{ category.name }}</strong>
                  <span>{{ category.description || '暂无说明' }}</span>
                </div>
                <div class="prompt-table-actions">
                  <button class="btn btn-ghost btn-sm" @click="editPromptCategory(category)">编辑</button>
                  <button class="btn btn-ghost btn-sm" @click="handleDeletePromptCategory(category)">停用</button>
                </div>
              </article>
            </div>
          </section>

          <section class="prompt-admin-card prompt-template-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>提示词模板</h3>
                <p>模板正文由后台控制，前端生成页只展示名称、说明和结构。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetPromptTemplateForm">新建模板</button>
            </div>

            <div class="prompt-template-toolbar">
              <label class="selector-label">当前分类</label>
              <select v-model="promptManagerCategoryKey" class="select select-compact">
                <option v-for="category in promptTemplateCategories" :key="category.key" :value="category.key">
                  {{ category.name }}
                </option>
              </select>
              <span>{{ promptManagerTemplates.length }} 个已启用模板</span>
            </div>

            <div class="prompt-template-list">
              <article v-for="template in promptManagerTemplates" :key="template.id" class="prompt-template-item">
                <div>
                  <strong>{{ template.name }}</strong>
                  <span>{{ template.key }} · {{ template.platform || '全平台' }} / {{ template.scene || template.scenario || '未设置场景' }} / {{ template.step || '未设置步骤' }} · v{{ template.version }}</span>
                  <p>{{ template.description || '暂无说明' }}</p>
                  <small>结构：{{ template.output_structure || '未设置' }}</small>
                </div>
                <div class="prompt-table-actions">
                  <span v-if="template.is_default" class="default-pill">默认</span>
                  <button class="btn btn-ghost btn-sm" @click="editPromptTemplate(template)">编辑</button>
                  <button class="btn btn-ghost btn-sm" @click="handleDeletePromptTemplate(template)">停用</button>
                </div>
              </article>
              <div v-if="!promptManagerTemplates.length" class="module-empty-state prompt-empty-state">
                <strong>当前分类暂无模板</strong>
                <span>创建一个模板后，IP 全案工作台即可选择使用。</span>
              </div>
            </div>

            <div class="prompt-form prompt-template-form">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">模板 Key</label>
                  <input v-model="promptTemplateForm.key" class="input" placeholder="three_part_knowledge" />
                </div>
                <div class="form-row">
                  <label class="form-label">模板名称</label>
                  <input v-model="promptTemplateForm.name" class="input" placeholder="三段式干货" />
                </div>
                <div class="form-row">
                  <label class="form-label">所属分类</label>
                  <select v-model="promptTemplateForm.category_key" class="input">
                    <option v-for="category in promptTemplateCategories" :key="category.key" :value="category.key">
                      {{ category.name }}
                    </option>
                  </select>
                </div>
                <div class="form-row">
                  <label class="form-label">适用场景</label>
                  <input v-model="promptTemplateForm.scenario" class="input" placeholder="干货分享" />
                </div>
                <div class="form-row">
                  <label class="form-label">平台</label>
                  <input v-model="promptTemplateForm.platform" class="input" placeholder="wechat / xiaohongshu / douyin" />
                </div>
                <div class="form-row">
                  <label class="form-label">业务场景</label>
                  <input v-model="promptTemplateForm.scene" class="input" placeholder="二创 / 口播 / 封面 / 分镜" />
                </div>
                <div class="form-row">
                  <label class="form-label">生成步骤</label>
                  <input v-model="promptTemplateForm.step" class="input" placeholder="正文生成 / 图片提示词 / 视频提示词" />
                </div>
                <div class="form-row">
                  <label class="form-label">版本</label>
                  <input v-model="promptTemplateForm.version" class="input" placeholder="1.0.0" />
                </div>
                <div class="form-row">
                  <label class="form-label">版本说明</label>
                  <input v-model="promptTemplateForm.change_note" class="input" placeholder="这次调整了什么" />
                </div>
                <div class="form-row">
                  <label class="form-label">排序</label>
                  <input v-model.number="promptTemplateForm.sort_order" class="input" type="number" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">模板说明</label>
                  <textarea v-model="promptTemplateForm.description" class="input" rows="2" placeholder="说明模板适合什么场景"></textarea>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">输出结构</label>
                  <textarea v-model="promptTemplateForm.output_structure" class="input" rows="2" placeholder="黄金3秒钩子 -> 核心观点 -> 方法拆解 -> CTA"></textarea>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">写作规则（一行一条）</label>
                  <textarea v-model="promptTemplateRulesText" class="input" rows="3" placeholder="开头必须有明确痛点\n不得做绝对效果承诺"></textarea>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">后台模板正文</label>
                  <textarea v-model="promptTemplateForm.prompt_body" class="input" rows="5" placeholder="可选。这里填写更完整的后台控制提示词正文，前端生成页不会直接展示。"></textarea>
                </div>
              </div>
              <div class="prompt-form-actions">
                <label class="checkbox-row">
                  <input v-model="promptTemplateForm.is_default" type="checkbox" />
                  设为分类默认
                </label>
                <label class="checkbox-row">
                  <input v-model="promptTemplateForm.is_active" type="checkbox" />
                  启用模板
                </label>
                <button class="btn btn-primary btn-sm" :disabled="isSavingPromptTemplate" @click="handleSavePromptTemplate">
                  {{ isSavingPromptTemplate ? '保存中...' : editingPromptTemplateId ? '更新模板' : '创建模板' }}
                </button>
                <button class="btn btn-ghost btn-sm" @click="resetPromptTemplateForm">清空</button>
              </div>
              <div v-if="promptTemplateVersions.length" class="prompt-version-list">
                <strong>版本历史</strong>
                <article v-for="version in promptTemplateVersions" :key="version.versionId" class="compact-item">
                  <span>v{{ version.version }} · {{ version.platform || '全平台' }} / {{ version.scene || '场景未填' }} / {{ version.step || '步骤未填' }}</span>
                  <small>{{ version.changeNote || '无变更说明' }} · {{ version.createdAt?.slice(0, 16) }}</small>
                </article>
              </div>
            </div>
          </section>

          <section class="prompt-admin-card model-config-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>大模型配置</h3>
                <p>快速添加模型：名称 + 类型 + API Key 即可；高级场景可补 Base URL 和模型 ID。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetModelConfigForm">清空表单</button>
            </div>

            <div class="prompt-template-list">
              <article v-for="model in modelManagerConfigs" :key="model.id" class="prompt-template-item">
                <div>
                  <strong>{{ model.name }}</strong>
                  <span>{{ model.model_type }} · {{ model.provider }} · {{ model.model_id || '默认模型' }}</span>
                  <p>{{ model.base_url }}</p>
                  <small>Key：{{ model.api_key_masked || '未填写' }} {{ model.is_default ? '· 默认' : '' }}</small>
                </div>
                <div class="prompt-table-actions">
                  <button class="btn btn-ghost btn-sm" @click="handleDeleteModelConfig(model)">停用</button>
                </div>
              </article>
              <div v-if="!modelManagerConfigs.length" class="module-empty-state prompt-empty-state">
                <strong>暂无模型配置</strong>
                <span>不配置也可以继续使用环境变量里的系统默认 AI 模型。</span>
              </div>
            </div>

            <div class="prompt-form model-config-form">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">模型名称</label>
                  <input v-model="modelConfigForm.name" class="input" placeholder="例：即梦图片 / GPT 文本" />
                </div>
                <div class="form-row">
                  <label class="form-label">模型类型</label>
                  <select v-model="modelConfigForm.model_type" class="input">
                    <option value="text">文本</option>
                    <option value="image">图片</option>
                    <option value="video">视频</option>
                    <option value="multimodal">多模态</option>
                  </select>
                </div>
                <div class="form-row">
                  <label class="form-label">供应商</label>
                  <input v-model="modelConfigForm.provider" class="input" placeholder="custom / openai / jimeng / kling" />
                </div>
                <div class="form-row">
                  <label class="form-label">API Key</label>
                  <input v-model="modelConfigForm.api_key" class="input" type="password" placeholder="后台保存，前端列表脱敏展示" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">Base URL</label>
                  <input v-model="modelConfigForm.base_url" class="input" placeholder="https://api.openai.com/v1" />
                </div>
                <div class="form-row">
                  <label class="form-label">模型 ID</label>
                  <input v-model="modelConfigForm.model_id" class="input" placeholder="gpt-4.1 / kling-v1 / jimeng-image" />
                </div>
                <div class="form-row">
                  <label class="form-label">排序</label>
                  <input v-model.number="modelConfigForm.sort_order" class="input" type="number" />
                </div>
              </div>
              <div class="prompt-form-actions">
                <label class="checkbox-row">
                  <input v-model="modelConfigForm.is_default" type="checkbox" />
                  设为类型默认
                </label>
                <label class="checkbox-row">
                  <input v-model="modelConfigForm.is_openai_compatible" type="checkbox" />
                  OpenAI 兼容
                </label>
                <button class="btn btn-primary btn-sm" :disabled="isSavingModelConfig" @click="handleSaveModelConfig">
                  {{ isSavingModelConfig ? '保存中...' : '创建模型' }}
                </button>
              </div>
            </div>
          </section>
        </div>
      </section>

      <!-- ─── Production Center ─── -->
      <section v-else-if="workspaceMode === 'ip'" class="panel panel-full">
        <ProductionCenter
          :initial-title="coverTitle || topicInput || '未命名内容选题'"
          :initial-content="scriptContent || extractedContent"
          :current-user="props.currentUser"
        />
      </section>

      <!-- ─── Legacy IP Workspace (保留代码，当前不作为主入口渲染) ─── -->
      <section v-else-if="false" class="panel panel-full glass-card panel-stack">
        <div class="workspace-overview">
          <div class="overview-copy">
            <span class="section-eyebrow">IP Production Flow</span>
            <h1>IP 全案内容生产工作台</h1>
            <p>按“素材解析、脚本生成、提词直播、内容输出”的链路推进，把主要模块直接摆到一级标题下。</p>
            <div class="overview-actions">
              <button
                class="btn btn-primary"
                :title="generateCaseReason || '根据提取内容生成完整全案'"
                :disabled="Boolean(generateCaseReason)"
                @click="handleGenerate"
              >
                <span v-if="isGenerating" class="typing-indicator" style="padding: 0;">
                  <span></span><span></span><span></span>
                </span>
                <template v-else>生成全案</template>
              </button>
            </div>
          </div>
          <div class="overview-metrics">
            <article v-for="metric in workspaceMetrics" :key="metric.label" :class="metric.state">
              <span>{{ metric.label }}</span>
              <strong>{{ metric.value }}</strong>
            </article>
          </div>
          <div class="output-status-badge">内容输出状态：{{ outputStatus }}</div>
          <div class="workspace-filter-bar">
            <div class="selector-group">
              <label class="selector-label">IP 人设</label>
              <select v-model="selectedPersonaId" class="select select-compact">
                <option :value="0">无特定人设（专业中性）</option>
                <option v-for="p in personas" :key="p.id" :value="p.id">
                  {{ p.name }}（{{ p.tone }}）
                </option>
              </select>
            </div>
            <div class="selector-group">
              <label class="selector-label">目标平台</label>
              <select v-model="targetPlatform" class="select select-compact">
                <option v-for="p in platforms" :key="p.value" :value="p.value">
                  {{ p.label }}
                </option>
              </select>
            </div>
            <div class="selector-group">
              <label class="selector-label">栏目</label>
              <select v-model="selectedColumnId" class="select select-compact">
                <option :value="0">通用结构</option>
                <option v-for="c in columns" :key="c.id" :value="c.id">
                  {{ c.name }}
                </option>
              </select>
            </div>
            <div class="selector-group">
              <label class="selector-label">提示词分类</label>
              <select v-model="selectedPromptCategory" class="select select-compact">
                <option v-for="category in scriptPromptCategories" :key="category.key" :value="category.key">
                  {{ category.name }}
                </option>
              </select>
            </div>
            <div class="selector-group selector-group-wide">
              <label class="selector-label">提示词模板</label>
              <select v-model="selectedPromptTemplateId" class="select select-compact">
                <option :value="0">通用口播模板</option>
                <option v-for="template in promptTemplates" :key="template.id" :value="template.id">
                  {{ template.name }} · {{ template.scenario }}
                </option>
              </select>
            </div>
            <div v-if="selectedPromptTemplate" class="template-hint template-hint-card">
              <div>
                <strong>{{ selectedPromptTemplate.name }} · v{{ selectedPromptTemplate.version }}</strong>
                <span>{{ selectedPromptTemplate.description }}｜结构：{{ selectedPromptTemplate.output_structure }}</span>
              </div>
              <button class="btn btn-ghost btn-sm" @click="showPromptTemplateDetail = !showPromptTemplateDetail">
                {{ showPromptTemplateDetail ? '收起规则' : '查看规则' }}
              </button>
            </div>
            <div v-if="selectedPromptTemplate && showPromptTemplateDetail" class="template-detail-preview">
              <p><strong>适用场景：</strong>{{ selectedPromptTemplate.scenario || '未设置' }}</p>
              <p><strong>输出结构：</strong>{{ selectedPromptTemplate.output_structure || '未设置' }}</p>
              <p><strong>模板版本：</strong>{{ selectedPromptTemplate.version }}</p>
              <p><strong>写作规则：</strong>{{ selectedPromptTemplate.writing_rules?.length ? selectedPromptTemplate.writing_rules.join('；') : '未设置' }}</p>
            </div>
          </div>
        </div>

        <div class="smart-suggestion-strip" data-testid="copilot-smart-suggestions" aria-label="智能生产建议">
          <article class="info">
            <strong>先输入素材</strong>
            <span>主题、链接、文本、文件和媒体都能作为生产起点。</span>
          </article>
          <article class="warning">
            <strong>再选模型和模板</strong>
            <span>人设、栏目、提示词和目标平台会影响生成质量。</span>
          </article>
          <article class="success">
            <strong>最后归档发布</strong>
            <span>脚本、提词、分镜和发布包统一沉淀。</span>
          </article>
        </div>

        <div class="production-stepper" aria-label="内容生产进度">
          <div v-for="(step, index) in productionSteps" :key="step.label" class="production-step" :class="{ done: step.done }">
            <i>{{ index + 1 }}</i>
            <span>{{ step.label }}</span>
          </div>
        </div>

        <div class="ip-workbench-layout">
          <div class="ip-main-flow">
        <!-- Input Area -->
        <div class="input-area">
          <div class="input-mode-toggle" aria-label="输入方式">
            <button
              v-for="mode in [
                { key: 'topic', label: '主题', icon: '' },
                { key: 'url', label: '链接', icon: '' },
                { key: 'text', label: '文本', icon: '' },
                { key: 'file', label: '文件', icon: '' },
                { key: 'media', label: '媒体素材', icon: '' },
              ]"
              :key="mode.key"
              class="tab-item"
              :class="{ active: inputMode === mode.key }"
              :aria-pressed="inputMode === mode.key"
              @click="inputMode = mode.key as any"
            >
              {{ mode.label }}
            </button>
          </div>

          <div class="input-box">
            <template v-if="inputMode === 'topic'">
              <div class="input-row">
                <input
                  v-model="topicInput"
                  class="input"
                  placeholder="输入一个口播主题 / 选题 / 标题，例如：AI 工具如何提升短视频选题效率"
                  @keydown.enter="handleParse"
                />
                <button class="btn btn-primary" :disabled="isLoading || !canParseInput" @click="handleParse">
                  {{ isLoading ? '记录中...' : '使用主题' }}
                </button>
                <button class="btn btn-ghost" :disabled="isLoading || isGenerating || !canParseInput" @click="handleUseTopicAndGenerate">
                  {{ isGenerating ? '生成中...' : '使用主题并生成' }}
                </button>
              </div>
            </template>
            <template v-else-if="inputMode === 'url'">
              <div class="input-row">
                <input
                  v-model="urlInput"
                  class="input"
                  placeholder="粘贴文章链接（公众号、小红书、知乎等）"
                  @keydown.enter="handleParse"
                />
                <button class="btn btn-primary" :disabled="isLoading || !canParseInput" @click="handleParse">
                  {{ isLoading ? '解析中...' : '解析' }}
                </button>
              </div>
            </template>
            <template v-else-if="inputMode === 'text'">
              <textarea
                v-model="textInput"
                class="input"
                rows="3"
                placeholder="直接粘贴文章内容..."
                @input="extractedContent = textInput; activeTab = 'extracted'"
              ></textarea>
              <button class="btn btn-primary btn-sm" style="margin-top: 8px;" :disabled="isLoading || !canParseInput" @click="handleParse">
                {{ isLoading ? '处理中...' : '提取核心内容' }}
              </button>
            </template>
            <template v-else>
              <div v-if="inputMode === 'media'" class="file-upload-area media-upload-area">
                <input
                  type="file"
                  accept="image/*,video/*"
                  multiple
                  @change="handleMediaFilesChange"
                  id="media-upload"
                  hidden
                />
                <label for="media-upload" class="file-upload-label">
                  <span class="file-icon">Media</span>
                  <span v-if="mediaFiles.length">已选择 {{ mediaFiles.length }} 个图片/视频素材</span>
                  <span v-else>点击选择图片 / 视频素材</span>
                </label>
                <div v-if="mediaFiles.length" class="media-file-list">
                  <span v-for="file in mediaFiles" :key="file.name + file.size" class="media-file-chip">
                    {{ file.name }}
                  </span>
                </div>
                <div class="media-action-row">
                  <button class="btn btn-primary btn-sm" :disabled="isLoading || !canParseInput" @click="handleParse">
                    {{ isLoading ? '分析中...' : '分析素材并生成全案输入' }}
                  </button>
                </div>
              </div>

              <div v-else class="file-upload-area">
                <input type="file" accept=".txt,.md,.pdf,.docx" @change="handleFileChange" id="file-upload" hidden />
                <label for="file-upload" class="file-upload-label">
                  <span class="file-icon">Doc</span>
                  <span v-if="fileInput">{{ fileInput.name }}</span>
                  <span v-else>点击选择文件（TXT / PDF / DOCX）</span>
                </label>
                <button v-if="fileInput" class="btn btn-primary btn-sm" style="margin-top: 8px;" :disabled="isLoading || !canParseInput" @click="handleParse">
                  {{ isLoading ? '解析中...' : '上传并解析' }}
                </button>
              </div>
            </template>

            <p v-if="parseDisabledReason" class="flow-helper">{{ parseDisabledReason }}</p>
          </div>
        </div>

        <div class="content-display content-workbench">
          <section class="content-module-section" @click="activeTab = 'extracted'">
            <div class="content-module-head">
              <div>
                <span class="module-index">01</span>
                <h3>内容提取</h3>
                <p>承接链接、文本、文件或媒体素材的解析结果，作为后续全案生成的统一输入。</p>
              </div>
              <div v-if="extractedContent" class="content-actions">
                <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(extractedContent)">复制</button>
                <button class="btn btn-ghost btn-sm" @click.stop="openVoiceTeleprompter(extractedContent)">发送到提词器</button>
                <button class="btn btn-ghost btn-sm" data-testid="export-extracted" @click.stop="activeTab = 'extracted'; exportCurrentContentMarkdown()">导出</button>
              </div>
            </div>
            <div v-if="!extractedContent" class="module-empty-state">
              <strong>等待素材解析</strong>
              <span>上传素材后将在这里展示提取出的核心内容。</span>
            </div>
            <pre v-else class="content-text">{{ extractedContent }}</pre>
          </section>

          <section class="content-module-section" @click="activeTab = 'shortVideo'">
            <div class="content-module-head">
              <div>
                <span class="module-index">02</span>
                <h3>短视频工作流</h3>
                <p>自动识别短视频场景，并把主体清理、分镜、动态脚本和最终提示词链路收束到同一版块。</p>
              </div>
              <div v-if="strategyOutputs.shortVideoWorkflow" class="content-actions">
                <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(shortVideoWorkflowContent)">复制全部</button>
                <button class="btn btn-ghost btn-sm" @click.stop="openVoiceTeleprompter(shortVideoWorkflowContent)">发送到提词器</button>
                <button class="btn btn-ghost btn-sm" @click.stop="exportShortVideoWorkflowMarkdown">导出归档</button>
                <button
                  class="btn btn-ghost btn-sm"
                  :disabled="isSavingShortVideoProject"
                  @click.stop="saveShortVideoWorkflowProject"
                >{{ isSavingShortVideoProject ? '保存中...' : '保存到项目库' }}</button>
                <button
                  class="btn btn-ghost btn-sm"
                  :disabled="isCreatingAipFromShortVideo"
                  @click.stop="handleCreateVideoAipFromShortVideoProject"
                >{{ isCreatingAipFromShortVideo ? '转入中...' : '转入视频 AIP' }}</button>
              </div>
            </div>

            <div class="module-control-panel">
              <div class="strategy-grid">
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">短视频需求</label>
                  <textarea
                    v-model="shortVideoForm.user_input"
                    class="input"
                    rows="2"
                    placeholder="例：我上传的是一款无糖杏仁甘露饮料，做15秒小红书短视频，风格高级清爽"
                  ></textarea>
                </div>
                <div class="form-row">
                  <label class="form-label">场景</label>
                  <select v-model="shortVideoForm.requested_intent" class="input">
                    <option v-for="intent in shortVideoIntentOptions" :key="intent.value" :value="intent.value">
                      {{ intent.label }}
                    </option>
                  </select>
                </div>
                <div class="form-row">
                  <label class="form-label">主体名称</label>
                  <input v-model="shortVideoForm.subject_name" class="input" placeholder="例：无糖杏仁甘露 / 布偶猫 / 张老师IP" />
                </div>
                <div class="form-row">
                  <label class="form-label">平台</label>
                  <input v-model="shortVideoForm.platform" class="input" placeholder="小红书/抖音" />
                </div>
                <div class="form-row">
                  <label class="form-label">比例</label>
                  <select v-model="shortVideoForm.aspect_ratio" class="input">
                    <option>9:16</option>
                    <option>16:9</option>
                    <option>1:1</option>
                  </select>
                </div>
                <div class="form-row">
                  <label class="form-label">时长</label>
                  <input v-model="shortVideoForm.duration" class="input" placeholder="15秒" />
                </div>
                <div class="form-row">
                  <label class="form-label">视频模型</label>
                  <input v-model="shortVideoForm.model" class="input" placeholder="即梦2.0" />
                </div>
                <div class="form-row">
                  <label class="form-label">风格</label>
                  <input v-model="shortVideoForm.style" class="input" placeholder="高级、真实、有记忆点" />
                </div>
                <div class="form-row">
                  <label class="form-label">目标受众</label>
                  <input v-model="shortVideoForm.target_audience" class="input" placeholder="例：关注健康饮品的年轻女性" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">核心表达</label>
                  <input v-model="shortVideoForm.core_message" class="input" placeholder="例：无糖、东方包装、高级清爽" />
                </div>
              </div>
              <div class="strategy-action-row">
                <button class="btn btn-primary btn-sm" :disabled="isShortVideoLoading" @click.stop="handleBuildShortVideoWorkflow">
                  {{ isShortVideoLoading ? '识别中...' : '自动识别并生成工作流' }}
                </button>
              </div>
            </div>

            <div v-if="!strategyOutputs.shortVideoWorkflow" class="module-empty-state">
              <strong>等待工作流识别</strong>
              <span>输入需求或先提取素材后，这里会展示自动识别结果和完整提示词链路。</span>
            </div>
            <div v-else class="content-body strategy-result short-video-workflow">
              <div class="workflow-status-row">
                <span
                  class="intent-pill"
                  :class="{ unknown: strategyOutputs.shortVideoWorkflow.intent.intent === 'unknown' }"
                >{{ strategyOutputs.shortVideoWorkflow.intent.label }}</span>
                <span class="video-event-tag">
                  置信度 {{ Math.round(strategyOutputs.shortVideoWorkflow.intent.confidence * 100) }}%
                </span>
              </div>

              <section v-if="strategyOutputs.shortVideoWorkflow.workflow" class="strategy-section workflow-summary-card">
                <h3>识别结果</h3>
                <div class="strategy-card">
                  <strong>{{ strategyOutputs.shortVideoWorkflow.workflow.label }}</strong>
                  <p>推荐命令：{{ strategyOutputs.shortVideoWorkflow.workflow.recommended_command }}</p>
                  <p>模板文档：{{ strategyOutputs.shortVideoWorkflow.workflow.template_doc }}</p>
                  <small v-if="strategyOutputs.shortVideoWorkflow.intent.matched_keywords.length">
                    命中关键词：{{ strategyOutputs.shortVideoWorkflow.intent.matched_keywords.join(' / ') }}
                  </small>
                </div>
              </section>

              <section v-if="strategyOutputs.shortVideoWorkflow.questions?.length" class="strategy-section">
                <h3>需要补充的信息</h3>
                <div class="strategy-card" v-for="question in strategyOutputs.shortVideoWorkflow.questions" :key="question">
                  <p>{{ question }}</p>
                </div>
              </section>

              <section v-if="strategyOutputs.shortVideoWorkflow.steps.length" class="strategy-section">
                <h3>工作流步骤</h3>
                <div
                  v-for="(step, idx) in strategyOutputs.shortVideoWorkflow.steps"
                  :key="step.key"
                  class="workflow-step-card"
                >
                  <div class="workflow-step-head">
                    <div>
                      <small>Step {{ idx + 1 }}</small>
                      <strong>{{ step.label }}</strong>
                      <p>{{ step.description }}</p>
                    </div>
                    <div class="workflow-step-actions">
                      <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(step.prompt)">复制</button>
                      <button class="btn btn-ghost btn-sm" @click.stop="applyShortVideoStepToTab(step.key, step.prompt)">应用</button>
                    </div>
                  </div>
                  <pre class="workflow-prompt">{{ step.prompt }}</pre>
                </div>
              </section>

              <section v-if="strategyOutputs.shortVideoWorkflow.next_actions.length" class="strategy-section">
                <h3>下一步</h3>
                <div class="strategy-card" v-for="action in strategyOutputs.shortVideoWorkflow.next_actions" :key="action">
                  <p>{{ action }}</p>
                </div>
              </section>
            </div>
          </section>

          <section class="content-module-section" @click="activeTab = 'strategy'">
            <div class="content-module-head">
              <div>
                <span class="module-index">03</span>
                <h3>选题策略</h3>
                <p>围绕栏目结构生成选题、黄金 3 秒开头和运营角度，让内容生产先定方向再写稿。</p>
              </div>
              <div v-if="strategyOutputs.topics || strategyOutputs.hooks" class="content-actions">
                <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(strategyContent)">复制策略 JSON</button>
                <button class="btn btn-ghost btn-sm" @click.stop="openVoiceTeleprompter(strategyContent)">发送到提词器</button>
                <button class="btn btn-ghost btn-sm" @click.stop="activeTab = 'strategy'; exportCurrentContentMarkdown()">导出</button>
              </div>
            </div>

            <div class="module-control-panel">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">快速创建栏目</label>
                  <input v-model="quickColumn.name" class="input" placeholder="例：老板60秒" />
                </div>
                <div class="form-row">
                  <label class="form-label">栏目目标</label>
                  <select v-model="quickColumn.goal" class="input">
                    <option>涨粉</option>
                    <option>建信任</option>
                    <option>转化</option>
                    <option>教育用户</option>
                  </select>
                </div>
                <div class="form-row">
                  <label class="form-label">推荐时长</label>
                  <input v-model="quickColumn.duration" class="input" placeholder="30-60秒" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">栏目固定结构</label>
                  <textarea v-model="quickColumn.structure" class="input" rows="2"></textarea>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">默认 CTA</label>
                  <input v-model="quickColumn.cta" class="input" placeholder="例：想要模板，评论区打资料" />
                </div>
              </div>
              <div class="strategy-action-row">
                <button class="btn btn-ghost btn-sm" :disabled="isCreatingColumn" @click.stop="handleCreateColumn">
                  {{ isCreatingColumn ? '创建中...' : '保存为栏目' }}
                </button>
                <button class="btn btn-ghost btn-sm" :disabled="isStrategyLoading || !extractedContent.trim()" @click.stop="handleGenerateTopics">生成选题</button>
                <button class="btn btn-ghost btn-sm" :disabled="isStrategyLoading || !scriptContent.trim()" @click.stop="handleOptimizeHooks">黄金3秒</button>
              </div>
              <p class="flow-helper strategy-helper">{{ strategyActionHint }}</p>
            </div>

            <div v-if="!strategyOutputs.topics && !strategyOutputs.hooks" class="module-empty-state">
              <strong>等待策略生成</strong>
              <span>点击「生成选题」或「黄金3秒」，这里会展示运营策略结果。</span>
            </div>
            <div v-else class="content-body strategy-result">
              <section v-if="strategyOutputs.topics?.topics" class="strategy-section">
                <h3>选题策划</h3>
                <div v-for="topic in strategyOutputs.topics.topics" :key="topic.title" class="strategy-card">
                  <strong>{{ topic.title }}</strong>
                  <p>{{ topic.angle }}</p>
                  <small>{{ topic.content_type }} · {{ topic.purpose }} · {{ topic.platform }} · 评分 {{ topic.score }}</small>
                  <p class="strategy-hook">{{ topic.opening_hook }}</p>
                </div>
              </section>
              <section v-if="strategyOutputs.hooks?.hooks" class="strategy-section">
                <h3>黄金 3 秒开头</h3>
                <div v-for="hook in strategyOutputs.hooks.hooks" :key="hook.hook" class="strategy-card">
                  <strong>{{ hook.type }}</strong>
                  <p>{{ hook.hook }}</p>
                  <small>{{ hook.why }} · {{ hook.best_for }}</small>
                </div>
              </section>
            </div>
          </section>

          <section class="content-module-section" @click="activeTab = 'script'">
            <div class="content-module-head">
              <div>
                <span class="module-index">04</span>
                <h3>口播文案</h3>
                <p>全案生成后的主稿内容，直接用于提词器跟读、继续改稿和后续发布包装。</p>
              </div>
              <div v-if="scriptContent" class="content-actions">
                <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(scriptContent)">复制</button>
                <button class="btn btn-ghost btn-sm" @click.stop="openVoiceTeleprompter(scriptContent)">发送到提词器</button>
                <button class="btn btn-ghost btn-sm" data-testid="export-script" @click.stop="activeTab = 'script'; exportCurrentContentMarkdown()">导出</button>
              </div>
            </div>
            <div v-if="!scriptContent" class="module-empty-state">
              <strong>等待口播文案</strong>
              <span>点击「生成全案」后将在这里展示口播主稿。</span>
            </div>
            <pre v-else class="content-text">{{ scriptContent }}</pre>
          </section>

          <section class="content-module-panel" @click="activeTab = 'video'">
            <div class="content-module-head">
              <div>
                <span class="module-index">05</span>
                <h3>视频 AIP 链路</h3>
                <p>把产品宣传大片或人物短剧拆成主体清理、多视图、分镜图和最终视频提示词，先把逻辑链路跑通。</p>
              </div>
              <div v-if="videoAipPlan || videoPrompts" class="content-actions">
                <button v-if="videoAipPlan" class="btn btn-ghost btn-sm" @click.stop="copyVideoAipPlan">复制 AIP 全链路</button>
                <button v-if="videoPrompts" class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(videoPrompts)">复制当前视频提示词</button>
                <button v-if="videoPrompts" class="btn btn-ghost btn-sm" data-testid="export-video" @click.stop="activeTab = 'video'; exportCurrentContentMarkdown()">导出</button>
              </div>
            </div>

            <div class="module-control-panel video-aip-control-panel">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">产品名称</label>
                  <input v-model="videoAipProductName" class="input" placeholder="产品大片可填：产品名/品牌名" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">人物关系 / 剧情要求</label>
                  <input v-model="videoAipCharacterNotes" class="input" placeholder="短剧可填：角色身份、关系、冲突和反转" />
                </div>
                <div class="form-row">
                  <label class="form-label">当前链路</label>
                  <select v-model="videoWorkflowType" class="input">
                    <option value="standard">标准视频</option>
                    <option value="product_tvc">产品宣传大片</option>
                    <option value="drama">人物短剧</option>
                  </select>
                </div>
              </div>
              <div class="strategy-action-row">
                <button class="btn btn-primary btn-sm" :disabled="isVideoAipPlanning" @click.stop="handleGenerateVideoAipPlan">
                  {{ isVideoAipPlanning ? '规划中...' : '生成视频 AIP 链路' }}
                </button>
                <button class="btn btn-ghost btn-sm" :disabled="isSavingVideoAipProject" @click.stop="handleCreateVideoAipProject">
                  {{ isSavingVideoAipProject ? '保存中...' : '保存为 AIP 项目' }}
                </button>
                <span class="flow-helper">右侧侧栏选择视频模板、比例、时长和模型；这里生成分步可复制提示词。</span>
              </div>
            </div>

            <div v-if="videoAipProject" class="strategy-card video-aip-project-card">
              <strong>已保存项目：#{{ videoAipProject.id }} {{ videoAipProject.title }}</strong>
              <p>状态：{{ videoAipProject.status }} · 当前步骤：{{ videoAipProject.current_step_key || '未开始' }}</p>
              <p v-if="videoAipProject.source && videoAipProject.source.type !== 'manual'">
                来源：{{ videoAipProject.source.label }} #{{ videoAipProject.source.refId }} · {{ videoAipProject.source.title || '未命名来源' }}
                <span v-if="videoAipProject.source.meta"> · {{ videoAipProject.source.meta }}</span>
              </p>
              <small>点击步骤里的「执行生成」，会提交真实图片/视频模型任务并把生成产物回写到后端。</small>
              <div class="strategy-action-row video-aip-project-actions">
                <button class="btn btn-primary btn-sm" :disabled="isRunningVideoAipNext || isRunningVideoAipAll" @click.stop="handleRunNextVideoAipStep">
                  {{ isRunningVideoAipNext ? '执行中...' : '执行下一步' }}
                </button>
                <button class="btn btn-ghost btn-sm" :disabled="isRunningVideoAipAll || isRunningVideoAipNext" @click.stop="handleRunAllVideoAipSteps">
                  {{ isRunningVideoAipAll ? '后台执行中...' : '执行全部' }}
                </button>
              </div>
            </div>

            <div v-if="!videoAipPlan && !videoPrompts" class="module-empty-state">
              <strong>等待视频链路规划</strong>
              <span>产品图走“主体清理 → 四视图 → 九/三十六宫格 → 视频”；人物图走“多角色四视图 → 剧情 → 图片分镜 → 视频”。</span>
            </div>

            <div v-if="videoAipPlan" class="content-body strategy-result video-aip-result">
              <section class="strategy-section">
                <h3>{{ videoAipPlan.title }}</h3>
                <div class="strategy-card">
                  <p>{{ videoAipPlan.summary }}</p>
                  <small>{{ videoAipPlan.handoff }}</small>
                </div>
              </section>
              <section class="strategy-section">
                <h3>分步真实任务</h3>
                <div v-for="step in videoAipDisplaySteps" :key="step.displayKey" class="workflow-step-card">
                  <div class="workflow-step-head">
                    <div>
                      <small>{{ step.displayKey }} · {{ step.displayStatus }}</small>
                      <strong>{{ step.title }}</strong>
                      <p>{{ step.goal }}</p>
                      <p v-if="step.output?.artifact_type || step.task_type" class="video-aip-task-meta">
                        {{ step.output?.artifact_type || step.artifact_type || 'artifact' }} · {{ step.output?.media_type || step.task_type || 'text' }}
                        <span v-if="videoAipProgressText(step)"> · {{ videoAipProgressText(step) }}</span>
                      </p>
                    </div>
                    <div class="workflow-step-actions">
                      <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(step.prompt)">复制</button>
                      <button class="btn btn-ghost btn-sm" @click.stop="applyVideoAipStep(step)">应用</button>
                      <template v-if="videoAipProject && step.isPersistedTask">
                        <button
                          class="btn btn-primary btn-sm"
                          :disabled="runningVideoAipStepIds[step.id] || step.output?.task_type === 'text'"
                          @click.stop="handleRunVideoAipStep(step)"
                        >
                          {{ runningVideoAipStepIds[step.id] ? '生成中...' : '执行生成' }}
                        </button>
                        <button class="btn btn-ghost btn-sm" @click.stop="markVideoAipStep(step, 'succeeded')">完成</button>
                        <button class="btn btn-ghost btn-sm" @click.stop="markVideoAipStep(step, 'failed')">失败</button>
                        <button class="btn btn-ghost btn-sm" :disabled="runningVideoAipStepIds[step.id] || step.output?.task_type === 'text'" @click.stop="handleRetryVideoAipStep(step)">重试</button>
                      </template>
                    </div>
                  </div>
                  <div v-if="videoAipArtifactUrl(step)" class="video-aip-artifact">
                    <video
                      v-if="isVideoAipVideoStep(step)"
                      :src="videoAipArtifactUrl(step)"
                      controls
                      playsinline
                    ></video>
                    <img v-else :src="videoAipArtifactUrl(step)" :alt="step.title" />
                    <a :href="videoAipArtifactUrl(step)" target="_blank" rel="noreferrer">打开生成产物</a>
                  </div>
                  <pre class="workflow-prompt">{{ step.prompt }}</pre>
                </div>
              </section>
            </div>

            <pre v-else-if="videoPrompts" class="content-text">{{ videoPrompts }}</pre>
          </section>

          <section class="content-module-section" @click="activeTab = 'publish'">
            <div class="content-module-head">
              <div>
                <span class="module-index">06</span>
                <h3>发布全案</h3>
                <p>沉淀标题、发布文案、评论区引导、私信承接和发布前质检，完成内容输出闭环。</p>
              </div>
              <div v-if="strategyOutputs.publishPackage || strategyOutputs.quality" class="content-actions">
                <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(publishContent)">复制发布全案</button>
                <button class="btn btn-ghost btn-sm" @click.stop="openVoiceTeleprompter(publishContent)">发送到提词器</button>
                <button class="btn btn-ghost btn-sm" data-testid="export-publish-package" @click.stop="activeTab = 'publish'; exportCurrentContentMarkdown()">导出</button>
              </div>
            </div>

            <div class="module-control-panel compact-control-panel">
              <div class="strategy-action-row">
                <button class="btn btn-ghost btn-sm" :disabled="isStrategyLoading || !scriptContent.trim()" @click.stop="handleGeneratePublishPackage">发布全案</button>
                <button class="btn btn-ghost btn-sm" :disabled="isStrategyLoading || !scriptContent.trim()" @click.stop="handleQualityCheck">发布质检</button>
              </div>
            </div>

            <div v-if="!strategyOutputs.publishPackage && !strategyOutputs.quality" class="module-empty-state">
              <strong>等待发布内容包</strong>
              <span>点击「发布全案」或「发布质检」，这里会展示可发布内容包和审核建议。</span>
            </div>
            <div v-else class="content-body strategy-result">
              <section v-if="strategyOutputs.publishPackage" class="strategy-section">
                <h3>发布全案</h3>
                <div class="strategy-card">
                  <strong>短标题</strong>
                  <p>{{ strategyOutputs.publishPackage.short_titles?.join(' / ') }}</p>
                  <strong>发布文案</strong>
                  <p>{{ strategyOutputs.publishPackage.caption }}</p>
                  <strong>置顶评论</strong>
                  <p>{{ strategyOutputs.publishPackage.comment_pin }}</p>
                  <strong>私信承接</strong>
                  <p>{{ strategyOutputs.publishPackage.private_message_reply }}</p>
                </div>
              </section>
              <section v-if="strategyOutputs.quality" class="strategy-section">
                <h3>发布前质检</h3>
                <div class="strategy-card">
                  <strong>总分：{{ strategyOutputs.quality.total_score ?? '-' }}</strong>
                  <p v-if="strategyOutputs.quality.optimized_opening">建议开头：{{ strategyOutputs.quality.optimized_opening }}</p>
                  <p v-if="strategyOutputs.quality.issues?.length">问题：{{ strategyOutputs.quality.issues.join('；') }}</p>
                  <p v-if="strategyOutputs.quality.suggestions?.length">建议：{{ strategyOutputs.quality.suggestions.join('；') }}</p>
                </div>
              </section>
            </div>

            <details v-if="videoPrompts || coverPrompt" class="support-assets-panel">
              <summary>发布辅助素材</summary>
              <div class="support-assets-grid">
                <article v-if="videoPrompts">
                  <div class="support-assets-head">
                    <strong>分镜提示词</strong>
                    <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(videoPrompts)">复制</button>
                  </div>
                  <pre class="content-text support-assets-text">{{ videoPrompts }}</pre>
                </article>
                <article v-if="coverPrompt">
                  <div class="support-assets-head">
                    <strong>封面提示词</strong>
                    <button class="btn btn-ghost btn-sm" @click.stop="copyToClipboard(coverPrompt)">复制</button>
                  </div>
                  <pre class="content-text support-assets-text">{{ coverPrompt }}</pre>
                </article>
              </div>
            </details>

          </section>
        </div>
          </div>

          <aside class="generation-sidecar" aria-label="生成配置侧栏">
            <div class="sidecar-head">
              <span class="section-eyebrow">Generate Control</span>
              <h3>生成配置侧栏</h3>
              <p>文案、封面、视频都在这里选择后台模板、模型和补充提示词；后台控制系统提示词，用户只改本次生成要求。</p>
            </div>

            <section class="sidecar-card">
              <div class="sidecar-card-head">
                <strong>口播文案</strong>
                <span>{{ selectedPromptTemplate?.name || '通用模板' }}</span>
              </div>
              <label class="form-label">提示词分类</label>
              <select v-model="selectedPromptCategory" class="input">
                <option v-for="category in scriptPromptCategories" :key="category.key" :value="category.key">
                  {{ category.name }}
                </option>
              </select>
              <label class="form-label">提示词模板</label>
              <select v-model="selectedPromptTemplateId" class="input">
                <option :value="0">通用口播模板</option>
                <option v-for="template in promptTemplates" :key="template.id" :value="template.id">
                  {{ template.name }} · {{ template.scenario }}
                </option>
              </select>
              <label class="form-label">文本模型</label>
              <select v-model="selectedTextModelConfigId" class="input">
                <option :value="0">系统默认模型</option>
                <option v-for="model in textModelConfigs" :key="model.id" :value="model.id">
                  {{ modelOptionLabel(model) }}
                </option>
              </select>
              <p class="sidecar-hint">{{ modelHint(selectedTextModelConfig, selectedPromptTemplate?.user_prompt_hint || '补充平台、受众、语气、时长、转化目标等要求。') }}</p>
            </section>

            <section class="sidecar-card">
              <div class="sidecar-card-head">
                <strong>封面/人物图片</strong>
                <span>{{ selectedCoverPromptTemplate?.name || '封面模板' }}</span>
              </div>
              <label class="form-label">封面模板</label>
              <select v-model="selectedCoverPromptTemplateId" class="input">
                <option :value="0">通用封面提示词</option>
                <option v-for="template in coverPromptTemplates" :key="template.id" :value="template.id">
                  {{ template.name }} · {{ template.scenario }}
                </option>
              </select>
              <div class="sidecar-two-col">
                <div>
                  <label class="form-label">比例</label>
                  <select v-model="coverAspectRatio" class="input">
                    <option>9:16</option><option>4:5</option><option>3:4</option><option>1:1</option><option>16:9</option>
                  </select>
                </div>
                <div>
                  <label class="form-label">图片模型</label>
                  <select v-model="selectedCoverModelConfigId" class="input">
                    <option :value="0">只生成提示词</option>
                    <option v-for="model in imageModelConfigs" :key="model.id" :value="model.id">
                      {{ modelOptionLabel(model) }}
                    </option>
                  </select>
                </div>
              </div>
              <label class="form-label">封面标题</label>
              <input v-model="coverTitle" class="input" placeholder="不填则从口播文案自动提炼" />
              <p class="sidecar-hint">{{ modelHint(selectedCoverModelConfig, '人物图、产品图和媒体素材先通过上方“媒体素材”上传；本期先生成可复制提示词，真实出图由图片模型链路承接。') }}</p>
            </section>

            <section class="sidecar-card aip-card">
              <div class="sidecar-card-head">
                <strong>视频 AIP 链路</strong>
                <span>{{ selectedVideoPromptTemplate?.name || '标准视频链路' }}</span>
              </div>
              <label class="form-label">链路类型</label>
              <select v-model="videoWorkflowType" class="input">
                <option value="standard">标准：脚本 → 分镜 → 视频提示词</option>
                <option value="product_tvc">产品宣传大片：主体图 → 四视图 → 九/三十六宫格 → 视频</option>
                <option value="drama">人物短剧：多角色四视图 → 剧情 → 图片分镜 → 视频</option>
              </select>
              <label class="form-label">视频模板</label>
              <select v-model="selectedVideoPromptTemplateId" class="input">
                <option :value="0">通用视频提示词</option>
                <option v-for="template in videoPromptTemplates" :key="template.id" :value="template.id">
                  {{ template.name }} · {{ template.scenario }}
                </option>
              </select>
              <div class="sidecar-two-col">
                <div>
                  <label class="form-label">比例</label>
                  <select v-model="videoAspectRatio" class="input">
                    <option>9:16</option><option>16:9</option><option>1:1</option>
                  </select>
                </div>
                <div>
                  <label class="form-label">时长</label>
                  <select v-model="videoDuration" class="input">
                    <option>10秒</option><option>15秒</option><option>30秒</option><option>60秒</option>
                  </select>
                </div>
              </div>
              <label class="form-label">视频模型</label>
              <select v-model="selectedVideoModelConfigId" class="input">
                <option :value="0">只生成提示词</option>
                <option v-for="model in videoModelConfigs" :key="model.id" :value="model.id">
                  {{ modelOptionLabel(model) }}
                </option>
              </select>
              <p class="sidecar-hint">{{ modelHint(selectedVideoModelConfig, '视频模型默认用于 AIP 最终视频步骤；如只生成提示词，可保持不选择。') }}</p>
              <ol class="aip-steps">
                <li>产品链路：主体抠图/清理 → 三视图或四视图 → 九/三十六宫格分镜 → 最终视频提示词。</li>
                <li>短剧链路：多人物四视图 → 剧情提示词 → 图片分镜图 → 剧本/分镜/参考图合成视频提示词。</li>
              </ol>
              <button class="btn btn-ghost sidecar-generate-btn" :disabled="isVideoAipPlanning" @click="handleGenerateVideoAipPlan">
                {{ isVideoAipPlanning ? '规划链路中...' : '只生成视频 AIP 链路' }}
              </button>
              <button class="btn btn-ghost sidecar-generate-btn" :disabled="isSavingVideoAipProject" @click="handleCreateVideoAipProject">
                {{ isSavingVideoAipProject ? '保存项目中...' : '创建可执行 AIP 项目' }}
              </button>
            </section>

            <section class="sidecar-card">
              <label class="form-label">用户补充提示词</label>
              <textarea v-model="extraRequirements" class="input" rows="5" placeholder="写清楚想要的效果、情绪、平台、禁忌、卖点、人物关系或镜头节奏。"></textarea>
              <button class="btn btn-primary sidecar-generate-btn" :disabled="Boolean(generateCaseReason)" @click="handleGenerate">
                {{ isGenerating ? '生成中...' : '按当前配置生成全案' }}
              </button>
            </section>
          </aside>
        </div>
      </section>

      <!-- ─── Left Panel (反转剧编剧模式) ─── -->
      <section v-else-if="workspaceMode === 'reversal'" class="panel panel-left glass-card drama-panel">
        <div class="drama-form-area">
          <h3 class="drama-section-title">短剧脚本工坊</h3>
          <p class="drama-subtitle">输入产品、痛点和人物关系，生成可拍摄、可检查、可迭代的 30-60 秒反转剧分镜脚本。</p>

          <div v-if="dramaFeedback" class="drama-feedback" :class="`feedback-${dramaFeedback.type}`">
            {{ dramaFeedback.message }}
          </div>

          <div v-else-if="dramaGenerateReason" class="drama-feedback feedback-info">
            {{ dramaGenerateReason }}
          </div>

          <div class="form-row">
            <label class="form-label">推销产品 · 产品名 <span class="required">*</span></label>
            <input v-model="drama.product_name" class="input" placeholder="例：AI 在线考试系统" />
          </div>

          <div class="form-row">
            <label class="form-label">推销产品 · 一句话功能 <span class="required">*</span></label>
            <textarea v-model="drama.product_function" class="input" rows="2"
              placeholder="例：自动组卷、AI 监考、自动判卷、数据推送到老板群"></textarea>
          </div>

          <div class="form-row">
            <label class="form-label">要打的痛点 <span class="required">*</span></label>
            <textarea v-model="drama.pain_point" class="input" rows="3"
              placeholder="例：线下考试组织麻烦、卷子改不完、老板拿不到即时反馈"></textarea>
          </div>

          <div class="form-row form-row-inline">
            <div class="form-col">
              <label class="form-label">发布平台</label>
              <input v-model="drama.platform" class="input" placeholder="视频号+抖音" />
            </div>
            <div class="form-col">
              <label class="form-label">时长</label>
              <input v-model="drama.duration" class="input" placeholder="30-60秒" />
            </div>
          </div>

          <div class="form-row">
            <label class="form-label drama-switch-label">
              <input type="checkbox" v-model="drama.useCustomCharacters" />
              <span>替换默认铁三角（农总 + 淇淇 + 海鸥），使用自定义人物</span>
            </label>
          </div>

          <div v-if="drama.useCustomCharacters" class="custom-characters">
            <div v-for="(ch, idx) in dramaCharacters" :key="idx" class="character-card">
              <div class="character-card-header">
                <span class="character-card-title">人物 #{{ idx + 1 }}</span>
                <button
                  v-if="dramaCharacters.length > 1"
                  class="btn btn-ghost btn-sm"
                  @click="removeDramaCharacter(idx)"
                >移除</button>
              </div>
              <div class="character-grid">
                <input v-model="ch.name" class="input" placeholder="名字（必填）" />
                <input v-model="ch.gender" class="input" placeholder="性别" />
                <input v-model="ch.role" class="input" placeholder="岗位（如 CEO / 技术）" />
                <input v-model="ch.catchphrase" class="input" placeholder="口头禅" />
              </div>
              <textarea v-model="ch.personality" class="input" rows="2"
                placeholder="性格底色（例：极致效率追求者，管理狂魔）"
                style="margin-top: 6px;"></textarea>
            </div>
            <button class="btn btn-ghost btn-sm" @click="addDramaCharacter">+ 添加人物</button>
          </div>

          <div class="form-row">
            <label class="form-label">额外要求</label>
            <textarea v-model="drama.extra_requirements" class="input" rows="2"
              placeholder="可选。例：本集突出『打脸老板』，结尾要带一个心率彩蛋"></textarea>
          </div>

          <div class="drama-form-actions">
            <button
              class="btn btn-primary"
              :disabled="isGeneratingDrama || Boolean(dramaGenerateReason)"
              @click="handleGenerateDrama"
            >
              <span v-if="isGeneratingDrama" class="typing-indicator" style="padding: 0;">
                <span></span><span></span><span></span>
              </span>
              <template v-else>生成反转剧</template>
            </button>
            <span class="flow-helper">{{ dramaGenerateReason || '信息已完整，可以开始生成；生成后会自动保存历史。' }}</span>
          </div>
        </div>

        <div v-if="!isGuestUser" class="drama-history-panel">
          <div class="drama-history-head">
            <h3 class="drama-section-title">历史记录</h3>
            <div class="drama-history-meta">
              <span>{{ reversalHistory.length ? `已保存 ${reversalHistory.length} 条` : '暂无保存记录' }}</span>
              <button v-if="reversalHistory.length" class="btn btn-ghost btn-sm" @click="clearReversalHistory">清空</button>
            </div>
          </div>
          <div v-if="reversalHistory.length" class="drama-history-list">
            <div
              v-for="item in reversalHistory"
              :key="item.id"
              class="drama-history-item"
            >
              <button class="drama-history-main" @click="restoreReversalHistory(item)">
                <strong>{{ item.title }}</strong>
                <span>{{ formatDramaHistoryTime(item.createdAt) }} · {{ item.productName }} · {{ item.painPoint }}</span>
              </button>
              <button class="history-delete-btn" title="删除历史" @click="deleteReversalHistory(item)">删除</button>
            </div>
          </div>
        </div>

        <div v-else class="drama-history-panel guest-locked-panel">
          <strong>游客模式不支持生成和保存反转剧</strong>
          <span>请退出游客身份后注册或登录正式账号，生成结果会自动保存到你的历史记录。</span>
          <button class="btn btn-primary btn-sm" @click="emit('logout')">去登录 / 注册</button>
        </div>

        <!-- 结果区 -->
        <div class="drama-result-area" v-if="dramaResult">
          <div class="drama-result-header">
            <h3 class="drama-section-title">📜 生成结果</h3>
            <button class="btn btn-ghost btn-sm" @click="copyDramaMarkdown">📋 复制全文 Markdown</button>
          </div>

          <!-- 剧本概览 -->
          <div class="overview-card" v-if="dramaResult.overview && dramaResult.overview.title">
            <h4 class="overview-title">《{{ dramaResult.overview.title }}》</h4>
            <div class="overview-meta">
              <span v-if="dramaResult.overview.duration" class="meta-chip">⏱ {{ dramaResult.overview.duration }}</span>
              <span v-if="dramaResult.overview.reversal_type" class="meta-chip meta-chip-accent">🌀 {{ dramaResult.overview.reversal_type }}</span>
              <span v-if="dramaResult.overview.characters" class="meta-chip">👥 {{ dramaResult.overview.characters }}</span>
            </div>
            <p v-if="dramaResult.overview.product" class="overview-row"><strong>产品：</strong>{{ dramaResult.overview.product }}</p>
            <p v-if="dramaResult.overview.pain_point" class="overview-row"><strong>痛点：</strong>{{ dramaResult.overview.pain_point }}</p>
          </div>

          <!-- 分镜表 -->
          <div v-if="dramaResult.scenes && dramaResult.scenes.length" class="scenes-table-wrap">
            <h4 class="overview-title">分镜表</h4>
            <table class="scenes-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>时长</th>
                  <th>画面</th>
                  <th>台词 / 旁白</th>
                  <th>BGM / 音效</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="sc in dramaResult.scenes" :key="sc.shot">
                  <td class="scene-shot">{{ sc.shot }}</td>
                  <td class="scene-duration">{{ sc.duration }}</td>
                  <td>{{ sc.visual }}</td>
                  <td>{{ sc.dialogue }}</td>
                  <td>{{ sc.bgm }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 结尾字幕 -->
          <div v-if="dramaResult.ending_subtitle" class="ending-subtitle">
            🎯 {{ dramaResult.ending_subtitle }}
          </div>

          <div class="compliance-card">
            <h4 class="overview-title">发布前合规检查</h4>
            <p class="compliance-note">以下为规则提示，不替代人工审核；涉及高风险行业或投放前请二次复核。</p>
            <ul class="compliance-list">
              <li v-for="item in reversalComplianceChecks" :key="item.label" :class="{ passed: item.passed }">
                <span>{{ item.passed ? '通过' : '需复核' }}</span>
                <strong>{{ item.label }}</strong>
                <small>{{ item.passed ? '未命中明显风险词。' : item.suggestion }}</small>
              </li>
            </ul>
          </div>

          <!-- 自检清单 -->
          <div v-if="dramaResult.checklist && dramaResult.checklist.length" class="checklist-wrap">
            <h4 class="overview-title">自检清单</h4>
            <ul class="checklist">
              <li v-for="(c, i) in dramaResult.checklist" :key="i" :class="{ passed: c.passed }">
                <span class="check-mark">{{ c.passed ? '✅' : '❌' }}</span>
                {{ c.item }}
              </li>
            </ul>
          </div>

          <!-- Raw markdown 折叠 -->
          <details class="raw-md-details">
            <summary>查看原始 Markdown</summary>
            <pre class="content-text">{{ dramaResult.raw_markdown }}</pre>
          </details>
        </div>

        <div v-else-if="!isGeneratingDrama" class="drama-empty">
          <div class="empty-icon">🎬</div>
          <p class="empty-text">填好上面的表单，点右上角「生成反转剧」按钮开始创作。</p>
        </div>

        <div v-else class="drama-empty">
          <div class="typing-indicator"><span></span><span></span><span></span></div>
          <p class="empty-text">AI 正在打磨剧本和自检...</p>
        </div>
      </section>

      <!-- ─── Teleprompter ─── -->
      <section v-else-if="workspaceMode === 'teleprompter'" class="panel panel-full">
        <TeleprompterPanel :initial-text="teleprompterInitialText || scriptContent" :current-user="props.currentUser" />
      </section>

      <!-- ─── WeChat Publisher ─── -->
      <section v-else-if="workspaceMode === 'wechat'" class="panel panel-full">
        <WechatArticlePublisher
          :initial-title="coverTitle || '未命名公众号文章'"
          :initial-content="scriptContent || extractedContent"
          source-type="copilot"
          :source-id="String(selectedPersonaId || '')"
          :current-user="props.currentUser"
        />
      </section>

      <!-- ─── Resizer ─── -->
      <!-- ─── Right Panel (Copilot Chat) ─── -->
      <section v-if="workspaceMode === 'reversal'" class="panel panel-right glass-card">
        <div class="chat-header">
          <div class="chat-title">
            <span class="chat-icon" aria-hidden="true">AI</span>
            <span>AI Copilot</span>
          </div>
          <span class="badge badge-success">在线</span>
        </div>

        <!-- Chat Messages -->
        <div class="chat-messages" ref="chatContainerRef">
          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            class="chat-bubble-wrapper animate-fade-in-up"
            :class="[`chat-${msg.role}`]"
          >
            <div class="chat-avatar" v-if="msg.role !== 'user'" aria-hidden="true">AI</div>
            <div class="chat-bubble" :class="[`bubble-${msg.role}`]">
              <p class="chat-content" style="white-space: pre-wrap;">{{ msg.content }}</p>
            </div>
            <div class="chat-avatar" v-if="msg.role === 'user'" aria-hidden="true">ME</div>
          </div>

          <!-- Streaming indicator -->
          <div v-if="isCopilotStreaming" class="chat-bubble-wrapper chat-assistant">
            <div class="chat-avatar" aria-hidden="true">AI</div>
            <div class="chat-bubble bubble-assistant">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Chat Input -->
        <div class="chat-input-area">
          <textarea
            v-model="chatInput"
            class="input chat-textarea"
            placeholder="告诉我你想如何修改..."
            rows="2"
            @keydown="handleChatKeydown"
            :disabled="isCopilotStreaming"
          ></textarea>
          <button
            class="btn btn-primary btn-send"
            :disabled="!chatInput.trim() || isCopilotStreaming"
            @click="handleChatSend"
          >
            发送
          </button>
        </div>
      </section>
    </main>
    <ConfirmDialog
      :open="confirmState.open"
      :title="confirmState.title"
      :message="confirmState.message"
      :confirm-text="confirmState.confirmText"
      :cancel-text="confirmState.cancelText"
      :tone="confirmState.tone"
      @confirm="resolveConfirmation(true)"
      @cancel="resolveConfirmation(false)"
    />
  </div>
</template>

<style scoped>
/* ═══ Workspace Layout ═══ */
.workspace {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  position: relative;
  z-index: 1;
  background: var(--color-bg-primary);
}

.workspace-home {
  background: var(--color-bg-primary);
}

/* ═══ Header ═══ */
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: nowrap;
  gap: 16px;
  min-height: 68px;
  padding: 10px 22px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
  z-index: 10;
}

.workspace-home .workspace-header {
  background: rgba(255, 255, 255, 0.74);
  border-bottom-color: var(--glass-border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
}

.workspace-home .logo-text {
  color: #1d1d1f;
}

.workspace-home .badge-accent {
  background: rgba(29, 29, 31, 0.06);
  border-color: rgba(29, 29, 31, 0.08);
  color: #515154;
}

.workspace-home .mode-switcher {
  background: rgba(29, 29, 31, 0.06);
}

.workspace-home .mode-switcher .tab-item {
  color: #515154;
}

.workspace-home .mode-switcher .tab-item:hover {
  background: rgba(255, 255, 255, 0.74);
  color: #1d1d1f;
}

.workspace-home .mode-switcher .tab-item.active {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.1), var(--shadow-sm);
}

.header-left {
  display: flex;
  align-items: center;
  flex: 1 1 auto;
  gap: 14px;
  min-width: 0;
}

.btn-back-home {
  flex: 0 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.logo-icon {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 10px;
  background: var(--color-accent-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: -0.04em;
  line-height: 1;
}

.logo-text {
  font-size: 16px;
  font-weight: 850;
  color: #1d1d1f;
  letter-spacing: -0.7px;
  white-space: nowrap;
}

.header-center {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  gap: 12px;
  padding: 7px;
  border: 1px solid rgba(29, 29, 31, 0.07);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 7px;
}

.selector-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.select-compact {
  width: auto;
  min-width: 170px;
  padding: 7px 32px 7px 12px;
  font-size: 13px;
  border-radius: 999px;
}

.header-right {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 12px;
}

.global-search {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
  padding: 9px 10px 9px 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.92);
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.global-search kbd {
  padding: 3px 7px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 900;
}

.user-chip {
  display: inline-flex;
  max-width: 140px;
  align-items: center;
  padding: 7px 12px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 999px;
  background: rgba(29, 29, 31, 0.05);
  color: #515154;
  font-size: 12px;
  font-weight: 800;
}

.user-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guest-scope-chip {
  padding: 7px 11px;
  border: 1px solid rgba(245, 158, 11, 0.24);
  border-radius: 999px;
  background: rgba(255, 251, 235, 0.9);
  color: #92400e;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

/* ═══ Main Layout ═══ */
.workspace-main {
  flex: 1;
  display: block;
  gap: 18px;
  padding: 18px;
  overflow: visible;
}

.workspace-home .workspace-main {
  padding: 0;
  background: transparent;
}

.workspace-ip .workspace-main {
  gap: 0;
  padding: 0;
}

.workspace-ip .panel-full {
  border-radius: 0;
}

.panel {
  display: flex;
  flex-direction: column;
  overflow: visible;
}

.panel-left {
  flex: 1.2;
  margin-right: 0;
}

.panel-right {
  flex: 0.8;
  margin-left: 0;
}

.panel-full {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.panel-stack {
  display: grid;
  gap: 18px;
}

.panel-resizer {
  display: none;
  width: 0;
  cursor: col-resize;
  background: transparent;
  transition: background var(--transition-fast);
  border-radius: var(--radius-full);
}
.panel-resizer:hover {
  background: var(--color-accent-primary);
}

.content-section-index {
  display: none;
  gap: 10px;
  padding: 14px 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.74);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
}

.content-section-index button {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 13px 14px;
  border: 0;
  border-radius: 18px;
  background: #f8fafc;
  color: #64748b;
  text-align: left;
  cursor: pointer;
}

.content-section-index button.active {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.content-section-index strong {
  font-size: 13px;
  font-weight: 950;
}

.content-section-index span {
  font-size: 12px;
  font-weight: 700;
  opacity: 0.7;
}

.section-eyebrow {
  display: inline-flex;
  margin-bottom: 8px;
  color: #2563eb;
  font-size: 11px;
  font-weight: 950;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.platform-workbench-panel {
  gap: 18px;
  padding: 24px;
  overflow-y: auto;
  background:
    radial-gradient(circle at 6% 8%, rgba(37, 99, 235, 0.1), transparent 28%),
    radial-gradient(circle at 92% 12%, rgba(14, 165, 233, 0.1), transparent 30%),
    rgba(255, 255, 255, 0.86);
}

.platform-workbench-head,
.platform-retention-card,
.platform-list-card header,
.platform-channel-card,
.platform-content-item,
.platform-task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.platform-workbench-head h1,
.platform-retention-card h3,
.platform-list-card h3,
.platform-channel-card h3 {
  margin: 0;
  color: #0f172a;
  font-weight: 950;
  letter-spacing: -0.04em;
}

.platform-workbench-head h1 {
  font-size: clamp(26px, 3vw, 38px);
}

.platform-workbench-head p,
.platform-retention-card p,
.platform-list-card p,
.platform-channel-card p,
.platform-content-item p {
  margin: 7px 0 0;
  color: #64748b;
  line-height: 1.7;
}

.platform-metric-grid,
.platform-channel-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.platform-metric-card,
.platform-channel-card,
.platform-list-card,
.platform-retention-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.06);
}

.platform-metric-card {
  display: grid;
  gap: 7px;
  padding: 18px;
}

.platform-metric-card span,
.platform-channel-card span,
.platform-content-item span,
.platform-task-item span,
.platform-task-item small,
.retention-stats span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.platform-metric-card strong {
  color: #0f172a;
  font-size: 30px;
  font-weight: 950;
}

.platform-metric-card small {
  color: #64748b;
  line-height: 1.5;
}

.platform-channel-card,
.platform-retention-card {
  padding: 18px;
}

.platform-channel-card span {
  color: #2563eb;
}

.platform-workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
  gap: 16px;
}

.platform-list-card {
  display: grid;
  gap: 14px;
  min-height: 320px;
  padding: 18px;
}

.platform-content-list,
.platform-task-list {
  display: grid;
  gap: 12px;
}

.platform-content-item,
.platform-task-item {
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.82);
}

.platform-content-item strong,
.platform-task-item strong {
  display: block;
  color: #0f172a;
  font-size: 15px;
  font-weight: 900;
}

.platform-item-actions,
.retention-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.platform-task-item.failed {
  border-color: rgba(239, 68, 68, 0.24);
  background: rgba(254, 242, 242, 0.82);
}

.platform-task-item.succeeded {
  border-color: rgba(34, 197, 94, 0.2);
  background: rgba(240, 253, 244, 0.76);
}

.retention-stats span {
  padding: 8px 10px;
  border: 1px solid rgba(37, 99, 235, 0.14);
  border-radius: 999px;
  background: rgba(239, 246, 255, 0.9);
  color: #1d4ed8;
}

.workspace-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.86fr);
  gap: 20px;
  padding: 24px 24px 18px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.07);
  background:
    radial-gradient(circle at 92% 12%, rgba(37, 99, 235, 0.12), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(248, 250, 252, 0.78) 100%);
}

.overview-copy h1 {
  margin: 0;
  color: #0f172a;
  font-size: clamp(26px, 3vw, 36px);
  font-weight: 950;
  letter-spacing: -0.055em;
}

.overview-copy p {
  max-width: 680px;
  margin: 10px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.75;
}

.overview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.overview-metrics article {
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
}

.overview-metrics article.done {
  box-shadow: inset 0 3px 0 #16a34a;
}

.overview-metrics article.active {
  box-shadow: inset 0 3px 0 #2563eb;
}

.overview-metrics article.pending {
  box-shadow: inset 0 3px 0 #cbd5e1;
}

.overview-metrics span {
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.overview-metrics strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 950;
}

.workspace-filter-bar {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
}

.selector-group-wide {
  grid-column: span 2;
}

.template-hint {
  grid-column: 1 / -1;
  margin: 0;
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(37, 99, 235, 0.06);
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
}

.template-hint-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.template-hint-card > div {
  display: grid;
  gap: 3px;
}

.template-hint-card strong {
  color: #1d4ed8;
}

.template-detail-preview {
  grid-column: 1 / -1;
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.9);
  color: #475569;
  font-size: 12px;
  line-height: 1.7;
}

.template-detail-preview p {
  margin: 0;
}

.production-stepper {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.07);
  background: rgba(255, 255, 255, 0.72);
}

.production-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 999px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.production-step i {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  font-style: normal;
}

.production-step.done {
  border-color: rgba(37, 99, 235, 0.18);
  background: rgba(37, 99, 235, 0.06);
  color: #1d4ed8;
}

.production-step.done i {
  background: #2563eb;
  color: #fff;
}

.smart-suggestion-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.07);
  background: rgba(255, 255, 255, 0.56);
}

.smart-suggestion-strip article {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.smart-suggestion-strip article.info {
  box-shadow: inset 3px 0 0 #2563eb, 0 10px 28px rgba(15, 23, 42, 0.04);
}

.smart-suggestion-strip article.warning {
  box-shadow: inset 3px 0 0 #f59e0b, 0 10px 28px rgba(15, 23, 42, 0.04);
}

.smart-suggestion-strip article.success {
  box-shadow: inset 3px 0 0 #22c55e, 0 10px 28px rgba(15, 23, 42, 0.04);
}

.smart-suggestion-strip div {
  display: grid;
  gap: 5px;
}

.smart-suggestion-strip strong {
  color: #0f172a;
  font-size: 14px;
}

.smart-suggestion-strip span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

/* ═══ Input Area ═══ */
.input-area {
  padding: 20px 22px 18px;
  border-bottom: 1px solid var(--color-border);
  background: linear-gradient(180deg, #fff 0%, #fbfbfd 100%);
}

.input-mode-toggle {
  display: flex;
  gap: 2px;
  padding: 4px;
  background: #f5f5f7;
  border-radius: 18px;
  margin-bottom: 14px;
  width: fit-content;
}

.input-mode-toggle .tab-item {
  padding: 5px 14px;
  font-size: 12px;
}

.input-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.flow-helper {
  margin: 0;
  color: #b45309;
  font-size: 12px;
  line-height: 1.6;
}

.strategy-helper {
  margin-top: 8px;
}

.input-row {
  display: flex;
  gap: 8px;
}

.input-row .input {
  flex: 1;
}

.file-upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.file-upload-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 24px;
  border: 1px dashed rgba(29, 29, 31, 0.16);
  border-radius: 22px;
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: 14px;
  transition: all var(--transition-normal);
}

.file-upload-label:hover {
  border-color: var(--color-accent-primary);
  color: var(--color-text-primary);
  background: rgba(36, 87, 255, 0.06);
}

.file-icon {
  display: inline-flex;
  min-width: 48px;
  justify-content: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 950;
}

.media-upload-area {
  gap: 10px;
}

.media-file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  width: 100%;
}

.media-file-chip {
  max-width: 100%;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(36, 87, 255, 0.1);
  color: #1d4ed8;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.media-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}

/* ═══ Content Display ═══ */
.ip-workbench-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
  min-height: 0;
  gap: 18px;
  padding: 0 22px 22px;
}

.ip-main-flow {
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.62);
}

.generation-sidecar {
  display: flex;
  position: sticky;
  top: 18px;
  max-height: calc(100vh - 142px);
  min-height: 0;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 28px;
  background: #fff;
  color: #0f172a;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.sidecar-head h3 {
  margin: 4px 0 6px;
  color: #0f172a;
  font-size: 20px;
  font-weight: 950;
  letter-spacing: -0.04em;
}

.sidecar-head p,
.sidecar-hint,
.aip-steps {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.65;
}

.sidecar-card {
  display: grid;
  gap: 9px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: #f8fafc;
}

.sidecar-card .form-label {
  color: #475569;
}

.sidecar-card .input {
  border-color: rgba(15, 23, 42, 0.1);
  background: #fff;
  color: #0f172a;
}

.sidecar-card .input::placeholder {
  color: #64748b;
}

.sidecar-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.sidecar-card-head strong {
  color: #0f172a;
  font-size: 14px;
  font-weight: 950;
}

.sidecar-card-head span {
  max-width: 150px;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 800;
  text-align: right;
}

.sidecar-two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.aip-card {
  box-shadow: inset 3px 0 0 #60a5fa;
}

.aip-steps {
  padding-left: 18px;
}

.sidecar-generate-btn {
  width: 100%;
  margin-top: 2px;
}

.content-display {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
  background:
    radial-gradient(circle at 0% 0%, rgba(37, 99, 235, 0.05), transparent 28%),
    rgba(255, 255, 255, 0.54);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  min-height: 320px;
}

.empty-icon {
  display: inline-flex;
  min-width: 76px;
  justify-content: center;
  padding: 8px 12px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.07);
  color: #2563eb;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.04em;
}

.empty-text {
  color: var(--color-text-muted);
  font-size: 14px;
  text-align: center;
  max-width: 300px;
  line-height: 1.6;
}

.content-body {
  position: relative;
}

.content-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

.content-text {
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  background: rgba(248, 250, 252, 0.86);
  padding: 18px;
  border-radius: 22px;
  border: 1px solid var(--color-border);
}

.content-workbench {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.content-module-section,
.content-module-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  cursor: pointer;
}

.content-module-section:focus-visible,
.content-module-panel:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.24);
  outline-offset: 3px;
}

.content-module-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.content-module-head h3 {
  margin: 5px 0 6px;
  color: #0f172a;
  font-size: 22px;
  font-weight: 950;
  letter-spacing: -0.04em;
}

.content-module-head p {
  max-width: 760px;
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.module-index {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 950;
  letter-spacing: 0.08em;
}

.module-control-panel {
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.82);
}

.module-control-panel .strategy-grid {
  margin-top: 0;
}

.compact-control-panel {
  padding: 10px 14px;
}

.compact-control-panel .strategy-action-row {
  margin-top: 0;
}

.module-empty-state {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-height: 96px;
  justify-content: center;
  padding: 18px;
  border: 1px dashed rgba(15, 23, 42, 0.14);
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.66);
}

.module-empty-state strong {
  color: #0f172a;
  font-size: 14px;
  font-weight: 950;
}

.module-empty-state span {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.workflow-status-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

/* ═══ Chat Panel ═══ */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--color-border);
  background: linear-gradient(180deg, #fff 0%, #fbfbfd 100%);
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 800;
  color: #1d1d1f;
}

.chat-icon {
  font-size: 20px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-bubble-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.chat-user {
  flex-direction: row-reverse;
}

.chat-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: #f0f0f3;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.chat-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 18px;
  font-size: 13px;
  line-height: 1.7;
}

.bubble-user {
  background: var(--color-accent-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble-assistant, .bubble-system {
  background: #f5f5f7;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
}

.bubble-system {
  background: rgba(36, 87, 255, 0.08);
  border-color: rgba(36, 87, 255, 0.16);
}

.chat-content {
  margin: 0;
}

/* ═══ Chat Input ═══ */
.chat-input-area {
  padding: 14px 16px 16px;
  border-top: 1px solid var(--color-border);
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-textarea {
  flex: 1;
  min-height: 40px;
  max-height: 100px;
  resize: none;
  padding: 8px 12px;
  font-size: 13px;
}

.btn-send {
  padding: 8px 18px;
  height: 40px;
  flex-shrink: 0;
}

/* ═══ Mode Switcher ═══ */
.mode-switcher {
  display: flex;
  flex: 0 1 auto;
  gap: 6px;
  min-width: 0;
  max-width: min(820px, 58vw);
  padding: 5px;
  overflow-x: auto;
  background: rgba(241, 245, 249, 0.88);
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 999px;
  margin-left: 8px;
  scrollbar-width: none;
}

.app-mode-tabs {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78), 0 12px 28px rgba(15, 23, 42, 0.06);
}

.mode-switcher::-webkit-scrollbar {
  display: none;
}
.mode-switcher .tab-item {
  flex: 0 0 auto;
  padding: 9px 14px;
  font-size: 12px;
  line-height: 1;
  color: #515154;
  white-space: nowrap;
  border-radius: 999px;
}

.mode-switcher .tab-item:hover {
  background: rgba(29, 29, 31, 0.06);
  color: #1d1d1f;
}

.mode-switcher .tab-item:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.mode-switcher .tab-item:disabled:hover {
  background: transparent;
  color: #515154;
}

.mode-switcher .tab-item.active {
  background: #eef3ff;
  color: var(--color-accent-primary);
  box-shadow: inset 0 0 0 1px #dbe6ff;
}

/* ═══ 提示词管理面板 ═══ */
.prompt-manager-panel {
  display: grid;
  gap: 18px;
  align-content: start;
  overflow-y: auto;
  padding: 24px;
  background: var(--color-bg-primary);
}

.prompt-manager-head,
.prompt-admin-card-head,
.prompt-form-actions,
.prompt-template-toolbar,
.prompt-table-actions,
.prompt-manager-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.prompt-manager-head,
.prompt-admin-card-head {
  justify-content: space-between;
}

.prompt-manager-head h1 {
  margin: 6px 0 8px;
  color: #0f172a;
  font-size: 30px;
  font-weight: 950;
}

.prompt-manager-head p,
.prompt-admin-card-head p,
.prompt-template-item p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.prompt-feedback {
  padding: 12px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 850;
}

.prompt-feedback.success {
  background: rgba(22, 163, 74, 0.1);
  color: #15803d;
}

.prompt-feedback.error {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}

.prompt-feedback.info {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.prompt-manager-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.72fr) minmax(0, 1.28fr);
  gap: 18px;
  align-items: start;
}

.prompt-admin-card {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.06);
}

.prompt-admin-card h3 {
  margin: 0 0 6px;
  color: #0f172a;
  font-size: 20px;
  font-weight: 950;
}

.prompt-category-list,
.prompt-template-list,
.prompt-table-list {
  display: grid;
  gap: 10px;
}

.prompt-category-item,
.prompt-table-item,
.prompt-template-item {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: #f8fafc;
}

.prompt-category-item {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.prompt-category-item.active {
  border-color: rgba(37, 99, 235, 0.2);
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
}

.prompt-category-item strong,
.prompt-template-item strong,
.prompt-table-item strong {
  color: #0f172a;
  font-size: 14px;
  font-weight: 950;
}

.prompt-category-item span,
.prompt-table-item span,
.prompt-template-item span,
.prompt-template-item small,
.prompt-template-toolbar span {
  color: #64748b;
  font-size: 12px;
  font-weight: 750;
  line-height: 1.6;
}

.prompt-table-item,
.prompt-template-item {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
}

.prompt-table-item > div:first-child,
.prompt-template-item > div:first-child {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.prompt-form {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.8);
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 13px;
  font-weight: 850;
}

.default-pill {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 900;
}

.model-gateway-panel {
  grid-template-columns: 1fr;
}

.model-gateway-grid,
.default-model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  align-items: start;
}

.model-gateway-list,
.model-catalog-list {
  display: grid;
  gap: 12px;
}

.model-gateway-item,
.model-catalog-item,
.default-model-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: #f8fafc;
}

.model-gateway-item,
.model-catalog-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
}

.model-gateway-item > div:first-child,
.model-catalog-main {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.model-gateway-item strong,
.model-catalog-main strong,
.default-model-card strong {
  color: #0f172a;
  font-size: 14px;
  font-weight: 950;
}

.model-gateway-item span,
.model-gateway-item small,
.model-catalog-main span,
.model-catalog-main small,
.default-model-card span,
.default-model-card small {
  color: #64748b;
  font-size: 12px;
  font-weight: 750;
  line-height: 1.6;
}

.model-gateway-item p,
.model-catalog-main p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}

.default-model-card {
  display: grid;
  gap: 8px;
  padding: 14px;
}

.default-model-actions,
.model-catalog-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.model-catalog-controls {
  justify-content: flex-end;
  min-width: 260px;
}

.model-catalog-controls .input {
  min-width: 120px;
}

.prompt-empty-state {
  margin: 0;
}

/* ═══ 反转剧编剧面板 ═══ */
.drama-panel {
  overflow-y: auto;
  padding: 0;
}

.drama-form-area {
  padding: 24px 28px 16px;
  border-bottom: 1px solid var(--color-border);
  background: linear-gradient(180deg, #fff 0%, #fbfbfd 100%);
}

.drama-section-title {
  font-size: 22px;
  font-weight: 850;
  margin: 0 0 8px;
  color: var(--color-text-primary);
}

.drama-subtitle {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 0 0 16px;
  line-height: 1.6;
}

.drama-feedback {
  margin: 0 0 16px;
  padding: 12px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.6;
}

.feedback-info {
  border: 1px solid rgba(14, 165, 233, 0.18);
  background: rgba(239, 246, 255, 0.9);
  color: #075985;
}

.feedback-success {
  border: 1px solid rgba(16, 185, 129, 0.18);
  background: rgba(236, 253, 245, 0.9);
  color: #047857;
}

.feedback-error {
  border: 1px solid rgba(239, 68, 68, 0.18);
  background: rgba(254, 242, 242, 0.9);
  color: #991b1b;
}

.drama-form-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

.drama-history-panel {
  margin: 16px 18px 0;
  padding: 16px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
}

.drama-history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.drama-history-head .drama-section-title {
  margin: 0;
  font-size: 18px;
}

.drama-history-head span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.drama-history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drama-history-list {
  display: grid;
  gap: 8px;
}

.drama-history-item {
  display: flex;
  width: 100%;
  align-items: stretch;
  gap: 8px;
  padding: 0;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  text-align: left;
  overflow: hidden;
}

.drama-history-item:hover {
  border-color: rgba(36, 87, 255, 0.28);
  background: rgba(36, 87, 255, 0.06);
}

.drama-history-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.history-delete-btn {
  flex: 0 0 auto;
  padding: 0 12px;
  border: 0;
  border-left: 1px solid rgba(29, 29, 31, 0.08);
  background: rgba(239, 68, 68, 0.06);
  color: #991b1b;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.history-delete-btn:hover {
  background: rgba(239, 68, 68, 0.12);
}

.drama-history-item strong {
  color: var(--color-text-primary);
  font-size: 13px;
}

.drama-history-item span,
.guest-locked-panel span {
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.guest-locked-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-color: rgba(245, 158, 11, 0.22);
  background: rgba(255, 251, 235, 0.86);
}

.guest-locked-panel strong {
  color: #92400e;
  font-size: 13px;
}

.guest-locked-panel .btn {
  width: fit-content;
  margin-top: 8px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.form-row-inline {
  flex-direction: row;
  gap: 12px;
}
.form-row-inline .form-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 800;
}

.form-label .required {
  color: #e74c3c;
  margin-left: 2px;
}

.drama-switch-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 500;
}

.custom-characters {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: #f7f7fa;
  border-radius: 20px;
  margin-bottom: 12px;
}

.character-card {
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: #fff;
}

.character-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.character-card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.character-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.drama-result-area {
  padding: 20px 28px 28px;
  background: #fff;
}

.drama-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.overview-card {
  background: #f7f7fa;
  border: 1px solid var(--color-border);
  border-radius: 22px;
  padding: 18px;
  margin-bottom: 16px;
}

.overview-title {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 10px;
}

.overview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: #fff;
  border-radius: var(--radius-full);
  font-size: 12px;
  color: var(--color-text-secondary);
}

.meta-chip-accent {
  background: rgba(108, 92, 231, 0.15);
  color: var(--color-accent-primary);
  font-weight: 600;
}

.overview-row {
  font-size: 13px;
  line-height: 1.7;
  margin: 4px 0;
  color: var(--color-text-primary);
}

.scenes-table-wrap {
  margin-bottom: 16px;
  overflow-x: auto;
}

.scenes-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.scenes-table th,
.scenes-table td {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
  line-height: 1.6;
}

.scenes-table thead {
  background: #f5f5f7;
}

.scenes-table th {
  font-weight: 600;
  color: var(--color-text-secondary);
}

.scene-shot {
  text-align: center;
  font-weight: 700;
  color: var(--color-accent-primary);
  width: 36px;
}

.scene-duration {
  text-align: center;
  width: 50px;
  color: var(--color-text-muted);
}

.ending-subtitle {
  padding: 14px 16px;
  background: rgba(36, 87, 255, 0.08);
  border-left: 3px solid var(--color-accent-primary);
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 16px;
}

.compliance-card {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 20px;
  background: rgba(255, 251, 235, 0.78);
}

.compliance-note {
  margin: 0 0 12px;
  color: #92400e;
  font-size: 12px;
  line-height: 1.7;
}

.compliance-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.compliance-list li {
  display: grid;
  grid-template-columns: auto minmax(120px, 0.55fr) minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  padding: 10px;
  border: 1px solid rgba(245, 158, 11, 0.16);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
}

.compliance-list li.passed {
  border-color: rgba(16, 185, 129, 0.16);
  background: rgba(236, 253, 245, 0.72);
}

.compliance-list span {
  padding: 4px 7px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.14);
  color: #92400e;
  font-size: 11px;
  font-weight: 900;
}

.compliance-list li.passed span {
  background: rgba(16, 185, 129, 0.14);
  color: #047857;
}

.compliance-list strong {
  color: var(--color-text-primary);
  font-size: 12px;
}

.compliance-list small {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.checklist-wrap {
  margin-bottom: 16px;
}

.checklist {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.checklist li {
  font-size: 13px;
  padding: 4px 0;
  color: var(--color-text-secondary);
}

.checklist li.passed {
  color: var(--color-text-primary);
}

.check-mark {
  margin-right: 6px;
}

.raw-md-details {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f7f7fa;
  border-radius: 18px;
  font-size: 12px;
}

.raw-md-details summary {
  cursor: pointer;
  color: var(--color-text-muted);
  font-weight: 500;
}

.drama-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  gap: 12px;
}

/* ═══ Responsive ═══ */
@media (max-width: 900px) {
  .workspace-header {
    align-items: center;
    flex-direction: row;
    gap: 10px;
    min-height: 52px;
    padding: 0 12px;
  }

  .header-left {
    align-items: center;
    flex: 1 1 auto;
    flex-direction: row;
    gap: 8px;
    min-width: 0;
  }

  .mode-switcher {
    flex: 1 1 auto;
    max-width: none;
    margin-left: 0;
    overflow-x: auto;
  }

  .mode-switcher .tab-item {
    min-width: max-content;
  }

  .header-right {
    flex: 0 0 auto;
    width: auto;
    gap: 6px;
  }

  .header-right .btn {
    flex: 0 0 auto;
    padding: 7px 10px;
    font-size: 12px;
  }

  .workspace-main {
    flex-direction: column;
  }

  .platform-metric-grid,
  .platform-channel-grid,
  .platform-workbench-grid {
    grid-template-columns: 1fr;
  }

  .platform-workbench-head,
  .platform-retention-card,
  .platform-content-item,
  .platform-task-item {
    align-items: flex-start;
    flex-direction: column;
  }

  .platform-item-actions,
  .retention-stats {
    justify-content: flex-start;
  }

  .panel-left, .panel-right {
    flex: 1;
    margin: 0 0 8px 0;
  }
  .panel-resizer {
    display: none;
  }
  .header-center {
    display: none;
  }
}

@media (max-width: 640px) {
  .logo-text,
  .workspace-header .badge-accent {
    display: none;
  }

  .logo-icon {
    font-size: 20px;
  }

  .mode-switcher .tab-item {
    padding: 7px 10px;
  }

  .header-right .btn-ghost {
    display: none;
  }
}

/* ─── 内容策略区 ─────────────────────────────────────── */
.strategy-panel {
  margin: 12px 0 0;
  padding: 12px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.7);
}
.strategy-panel summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  color: var(--color-text-primary);
  list-style: none;
}
.strategy-panel summary::-webkit-details-marker {
  display: none;
}
.video-options-hint {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-muted);
}
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 12px;
  margin-top: 12px;
}
.strategy-grid .form-row {
  margin-bottom: 0;
}
.strategy-grid-wide {
  grid-column: span 3;
}
.strategy-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.strategy-result {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.strategy-section h3 {
  margin: 0 0 10px;
  font-size: 15px;
}
.strategy-card {
  padding: 12px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  margin-bottom: 10px;
}
.strategy-card p {
  margin: 6px 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}
.strategy-card small {
  color: var(--color-text-muted);
}
.strategy-hook {
  color: #1d4ed8 !important;
  font-weight: 700;
}
.short-video-workflow {
  gap: 18px;
}
.intent-pill {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  border-radius: 999px;
  background: rgba(36, 87, 255, 0.1);
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 800;
}
.intent-pill.unknown {
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}
.workflow-step-card {
  padding: 14px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(251, 251, 255, 0.78) 100%);
  margin-bottom: 12px;
}
.workflow-step-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.workflow-step-head small {
  display: block;
  margin-bottom: 3px;
  color: #6b7280;
  font-weight: 700;
  text-transform: uppercase;
}
.workflow-step-head strong {
  display: block;
  color: #1d1d1f;
  font-size: 15px;
}
.workflow-step-head p {
  margin: 5px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}
.workflow-step-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}
.workflow-prompt {
  max-height: 280px;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border-radius: 14px;
  background: #f7f7fa;
  color: #1f2937;
  border: 1px solid rgba(29, 29, 31, 0.07);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 1.7;
}
.video-aip-task-meta {
  color: #1d4ed8 !important;
  font-weight: 800;
}
.video-aip-artifact {
  display: grid;
  gap: 8px;
  margin: 10px 0;
  padding: 10px;
  border-radius: 14px;
  background: rgba(36, 87, 255, 0.06);
  border: 1px solid rgba(36, 87, 255, 0.12);
}
.video-aip-artifact img,
.video-aip-artifact video {
  max-width: 100%;
  max-height: 360px;
  object-fit: contain;
  border-radius: 12px;
  background: #f8fafc;
}
.video-aip-artifact a {
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 800;
  text-decoration: none;
}
.video-event-tag {
  font-size: 12px;
  color: #6b7280;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

/* ═══ Global Layout Refinement: spacing-only, color-safe ═══ */
.workspace:not(.workspace-home) .workspace-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  min-height: 64px;
  padding: 10px 24px;
}

.workspace:not(.workspace-home) .header-left {
  gap: 16px;
}

.workspace:not(.workspace-home) .mode-switcher {
  max-width: min(820px, 58vw);
  padding: 5px;
  background: rgba(241, 245, 249, 0.86);
}

.workspace:not(.workspace-home) .header-center {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding: 8px;
  border-radius: 24px;
}

.workspace:not(.workspace-home) .selector-group {
  min-width: 0;
  align-items: stretch;
  flex-direction: column;
  gap: 5px;
}

.workspace:not(.workspace-home) .selector-label {
  padding-left: 4px;
  font-size: 11px;
  line-height: 1;
}

.workspace:not(.workspace-home) .select-compact {
  width: 100%;
  min-width: 0;
}

.workspace:not(.workspace-home) .workspace-main {
  display: block;
  gap: 22px;
  max-width: 1680px;
  width: 100%;
  margin: 0 auto;
  padding: 22px;
}

.workspace-ip:not(.workspace-home) .workspace-main {
  gap: 0;
  max-width: none;
  padding: 0;
}

.workspace:not(.workspace-home) .panel-left {
  flex: 1 1 auto;
  min-width: 0;
}

.workspace:not(.workspace-home) .panel-right {
  flex: 0 0 clamp(340px, 28vw, 460px);
  min-width: 320px;
}

.panel-left.glass-card,
.panel-right.glass-card {
  border-radius: 32px;
}

.input-area {
  display: grid;
  grid-template-columns: minmax(170px, 220px) minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
  padding: 24px;
}

.input-mode-toggle {
  display: grid;
  grid-template-columns: 1fr;
  align-content: start;
  gap: 6px;
  width: 100%;
  margin: 0;
  padding: 6px;
}

.input-mode-toggle .tab-item {
  justify-content: flex-start;
  padding: 10px 14px;
  text-align: left;
}

.input-box {
  justify-content: center;
  min-width: 0;
}

.strategy-panel {
  margin: 16px 22px 0;
  padding: 16px;
}

.content-display {
  padding: 22px;
}

.content-body {
  width: 100%;
}

.content-actions {
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 0;
}

.content-text {
  padding: 24px;
  font-size: 15px;
  line-height: 1.9;
}

.strategy-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.strategy-grid-wide {
  grid-column: span 2;
}

.strategy-action-row {
  justify-content: flex-end;
}

.chat-header {
  padding: 22px 24px;
}

.chat-messages {
  gap: 16px;
  padding: 22px;
}

.chat-bubble-wrapper {
  gap: 10px;
}

.chat-bubble {
  max-width: min(86%, 360px);
  padding: 12px 15px;
  font-size: 13px;
}

.chat-input-area {
  gap: 10px;
  padding: 18px;
}

.chat-textarea {
  min-height: 48px;
  padding: 12px 14px;
}

.btn-send {
  height: 48px;
  padding: 10px 20px;
}

.drama-panel {
  display: grid;
  grid-template-columns: minmax(360px, 0.92fr) minmax(0, 1.08fr);
  align-items: stretch;
  overflow: hidden;
}

.drama-form-area,
.drama-result-area,
.drama-empty {
  min-height: 0;
  overflow-y: auto;
}

.drama-form-area {
  padding: 28px;
  border-bottom: 0;
}

.drama-result-area,
.drama-empty {
  padding: 28px;
}

.drama-result-header {
  gap: 14px;
}

.form-row {
  margin-bottom: 16px;
}

.form-row-inline {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.overview-card,
.strategy-card,
.character-card {
  padding: 18px;
}

.scenes-table th,
.scenes-table td {
  padding: 13px 14px;
}

@media (max-width: 1320px) {
  .workspace:not(.workspace-home) .workspace-header {
    flex-wrap: wrap;
  }

  .workspace:not(.workspace-home) .header-center {
    width: 100%;
  }

  .workspace:not(.workspace-home) .mode-switcher {
    max-width: min(620px, 52vw);
  }

  .strategy-grid,
  .video-options-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1040px) {
  .workspace:not(.workspace-home) .workspace-header {
    display: flex;
    flex-direction: row;
    align-items: center;
    min-height: auto;
  }

  .workspace:not(.workspace-home) .header-left,
  .workspace:not(.workspace-home) .header-right {
    width: auto;
  }

  .workspace:not(.workspace-home) .header-right {
    justify-content: flex-end;
  }

  .workspace:not(.workspace-home) .mode-switcher {
    max-width: none;
  }

  .workspace:not(.workspace-home) .workspace-main {
    flex-direction: column;
    overflow-y: auto;
  }

  .workspace-sidebar {
    flex: none;
    width: 100%;
  }

  .sidebar-nav {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .sidebar-task-center {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .sidebar-section-title {
    grid-column: 1 / -1;
  }

  .workspace-overview {
    grid-template-columns: 1fr;
  }

  .ip-workbench-layout {
    grid-template-columns: 1fr;
  }

  .generation-sidecar {
    position: static;
    max-height: none;
  }

  .prompt-manager-grid {
    grid-template-columns: 1fr;
  }

  .prompt-manager-head,
  .prompt-admin-card-head,
  .prompt-table-item,
  .prompt-template-item {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace:not(.workspace-home) .panel-left,
  .workspace:not(.workspace-home) .panel-right {
    flex: none;
    width: 100%;
    min-height: 70vh;
  }

  .drama-panel {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .drama-form-area,
  .drama-result-area,
  .drama-empty {
    overflow: visible;
  }
}

@media (max-width: 760px) {
  .workspace-home .workspace-header {
    gap: 10px;
    padding: 8px 12px;
  }

  .workspace-home .header-left {
    min-width: 0;
  }

  .workspace-home .logo-text,
  .workspace-home .badge-accent,
  .workspace-home .global-search,
  .workspace-home .user-chip {
    display: none;
  }

  .workspace-home .mode-switcher {
    flex: 1 1 auto;
    max-width: calc(100vw - 142px);
    overflow-x: auto;
    scrollbar-width: none;
  }

  .workspace-home .mode-switcher::-webkit-scrollbar {
    display: none;
  }

  .workspace-home .mode-switcher .tab-item {
    flex: 0 0 auto;
    min-height: 32px;
    padding: 7px 11px;
    font-size: 12px;
  }

  .workspace-home .header-right {
    gap: 8px;
  }

  .workspace:not(.workspace-home) .workspace-header {
    flex-wrap: nowrap;
    gap: 10px;
    padding: 10px 14px;
  }

  .workspace:not(.workspace-home) .header-left {
    flex: 1 1 auto;
    min-width: 0;
  }

  .workspace:not(.workspace-home) .header-right {
    flex: 0 0 auto;
    gap: 8px;
  }

  .workspace:not(.workspace-home) .btn-back-home,
  .workspace:not(.workspace-home) .badge-accent,
  .workspace:not(.workspace-home) .user-chip {
    display: none;
  }

  .logo-text {
    overflow: hidden;
    max-width: 148px;
    text-overflow: ellipsis;
  }

  .workspace:not(.workspace-home) .workspace-main {
    gap: 14px;
    padding: 14px;
  }

  .workspace-sidebar {
    display: none;
  }

  .mobile-module-nav {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    min-height: 48px;
    align-items: center;
    padding: 6px;
    border: 1px solid rgba(15, 23, 42, 0.07);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.9);
  }

  .mobile-module-nav button {
    flex: 0 0 auto;
    min-height: 34px;
    padding: 8px 12px;
    border: 0;
    border-radius: 999px;
    background: transparent;
    color: #64748b;
    font-family: var(--font-sans);
    font-size: 12px;
    font-weight: 900;
  }

  .mobile-module-nav button.active {
    background: #eef3ff;
    color: var(--color-accent-primary);
    box-shadow: inset 0 0 0 1px #dbe6ff;
  }

  .workspace:not(.workspace-home) .header-center,
  .input-area,
  .overview-metrics,
  .workspace-filter-bar,
  .ip-workbench-layout,
  .sidecar-two-col,
  .production-stepper,
  .smart-suggestion-strip,
  .strategy-grid,
  .prompt-manager-grid,
  .model-gateway-grid,
  .default-model-grid,
  .form-row-inline {
    grid-template-columns: 1fr;
  }

  .model-gateway-item,
  .model-catalog-item,
  .model-catalog-controls {
    align-items: stretch;
    flex-direction: column;
    min-width: 0;
  }

  .global-search {
    display: none;
  }

  .sidebar-nav,
  .sidebar-task-center {
    grid-template-columns: 1fr;
  }

  .content-module-head,
  .workflow-step-head {
    align-items: stretch;
    flex-direction: column;
  }

  .input-area,
  .content-display,
  .drama-form-area,
  .drama-result-area,
  .drama-empty {
    padding: 18px;
  }

  .content-module-section {
    padding: 16px;
  }

  .strategy-panel,
  .content-module-section {
    margin-right: 18px;
    margin-left: 18px;
  }

  .strategy-grid-wide {
    grid-column: span 1;
  }

  .prompt-manager-panel {
    padding: 16px;
  }

  .prompt-form-actions,
  .prompt-template-toolbar,
  .prompt-table-actions,
  .prompt-manager-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .selector-group-wide,
  .template-hint {
    grid-column: 1 / -1;
  }

}
</style>

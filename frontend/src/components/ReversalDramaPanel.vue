<script setup lang="ts">
import { ref, reactive, nextTick, computed, watch } from 'vue'
import ConfirmDialog from './ConfirmDialog.vue'
import { useConfirmDialog } from '../composables/useConfirmDialog'
import {
  reportGenerationActionEvent,
  copilotModifyStream,
  generateReversalDrama,
  listReversalDramaHistory,
  deleteReversalDramaHistory,
  clearReversalDramaHistory,
  listDramaScriptTemplates,
  listDramaCastPresets,
  createDramaCastPreset,
  listIpProjects,
  listCharacterProfiles,
  type ReversalCharacter,
  type ReversalDramaParams,
  type ReversalDramaResult,
  type ReversalCastSource,
  type ReversalPattern,
  type DramaScriptTemplateData,
  type DramaCastPresetData,
  type IpProjectData,
  type CharacterProfileData,
} from '../api'

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
  params: ReversalDramaParams
  result: ReversalDramaResult
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
}

const props = defineProps<{
  currentUser?: WorkspaceUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const REVERSAL_HISTORY_KEY = 'ip-case-reversal-drama-history'
const DRAMA_ROLE_OPTIONS = [
  { value: '', label: '自动' },
  { value: 'pressure', label: '施压者' },
  { value: 'buffer', label: '缓冲者' },
  { value: 'reversal_carrier', label: '反转承载者' },
  { value: 'product_introducer', label: '产品引出者' },
  { value: 'other', label: '其他' },
]
const REVERSAL_PATTERN_OPTIONS: { value: ReversalPattern; label: string }[] = [
  { value: 'auto', label: '自动选择' },
  { value: 'A', label: 'A · 打脸/质疑反转' },
  { value: 'B', label: 'B · 反讽反转' },
  { value: 'C', label: 'C · 细节杀' },
]
const { confirmState, requestConfirmation, resolveConfirmation } = useConfirmDialog()

const isGuestUser = computed(() => !props.currentUser?.token)
const isAdminUser = computed(() => props.currentUser?.is_admin === true)
const liveStatusMessage = computed(() => dramaFeedback.value?.message || '')

const isCopilotStreaming = ref(false)
const currentGenerationHistoryId = ref(0)

const chatMessages = reactive<ChatMessage[]>([
  {
    role: 'system',
    content: '👋 你好！我是你的 IP 打造助手。生成反转剧脚本后，你可以在这里告诉我修改意见。',
    timestamp: Date.now(),
  },
])
const chatInput = ref('')
const chatContainerRef = ref<HTMLElement | null>(null)

const drama = reactive({
  product_name: '',
  product_function: '',
  pain_point: '',
  template_key: 'workplace_reversal',
  reversal_pattern: 'auto' as ReversalPattern,
  cast_source: 'default' as ReversalCastSource,
  cast_preset_id: 0,
  project_id: 0,
  platform: '视频号+抖音',
  duration: '30-60秒',
  extra_requirements: '',
})

const dramaTemplates = ref<DramaScriptTemplateData[]>([])
const dramaCastPresets = ref<DramaCastPresetData[]>([])
const ipProjects = ref<IpProjectData[]>([])
const projectCharacters = ref<CharacterProfileData[]>([])
const selectedCharacterIds = ref<number[]>([])
const castPresetName = ref('')
const showDramaConfig = ref(false)

const dramaCharacters = reactive<ReversalCharacter[]>([
  { name: '', gender: '', role: '', personality: '', catchphrase: '', drama_role: '' },
])

const isGeneratingDrama = ref(false)
const dramaResult = ref<ReversalDramaResult | null>(null)
const dramaFeedback = ref<{ type: 'info' | 'success' | 'error'; message: string } | null>(null)
const reversalHistory = ref<ReversalDramaHistoryItem[]>([])

const currentContent = computed(() => dramaResult.value?.raw_markdown || '')

const selectedTemplate = computed(() =>
  dramaTemplates.value.find((item) => item.key === drama.template_key) || null
)

const groupedDramaTemplates = computed(() => {
  const groups = new Map<string, DramaScriptTemplateData[]>()
  for (const tpl of dramaTemplates.value) {
    const category = tpl.category || '通用'
    const bucket = groups.get(category) || []
    bucket.push(tpl)
    groups.set(category, bucket)
  }
  return Array.from(groups.entries()).map(([category, items]) => ({ category, items }))
})

function selectDramaTemplate(key: string) {
  drama.template_key = key
}

const castSummary = computed(() => {
  if (drama.cast_source === 'preset') {
    const preset = dramaCastPresets.value.find((item) => item.castPresetId === drama.cast_preset_id)
    return preset?.name || ''
  }
  if (drama.cast_source === 'ip_project') {
    const names = projectCharacters.value
      .filter((item) => selectedCharacterIds.value.includes(item.characterId || 0))
      .map((item) => item.name)
    return names.length ? names.join('、') : ''
  }
  if (drama.cast_source === 'manual') {
    const names = dramaCharacters.filter((item) => item.name.trim()).map((item) => item.name.trim())
    return names.length ? names.join('、') : ''
  }
  return selectedTemplate.value?.name ? `${selectedTemplate.value.name} 默认角色组` : '默认角色组'
})

const dramaRequiredReason = computed(() => {
  if (!drama.product_name.trim()) return '请先填写推销产品的产品名。'
  if (!drama.product_function.trim()) return '请先填写产品的一句话功能。'
  if (!drama.pain_point.trim()) return '请先填写要打的痛点。'
  return ''
})

const dramaGenerateReason = computed(() => {
  if (isGuestUser.value) return '游客模式不能生成反转剧。请注册或登录后使用，生成结果会自动保存到历史记录。'
  if (drama.cast_source === 'preset' && !drama.cast_preset_id) {
    return '请先选择一个已保存的角色组，或切换为其他角色来源。'
  }
  if (drama.cast_source === 'ip_project' && !selectedCharacterIds.value.length) {
    return '请先从 IP 项目角色库中勾选至少 1 个角色。'
  }
  if (drama.cast_source === 'manual' && !dramaCharacters.some((item) => item.name.trim())) {
    return '手动填写模式下请至少填写 1 个角色名字。'
  }
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
  () => {
    loadReversalHistory()
    loadDramaStudioData()
  },
  { immediate: true }
)

watch(
  () => drama.project_id,
  (projectId) => {
    if (drama.cast_source === 'ip_project' && projectId) {
      void loadProjectCharacters(projectId)
    }
  }
)

async function loadDramaStudioData() {
  if (isGuestUser.value) return
  try {
    const [templatesRes, castsRes, projectsRes] = await Promise.all([
      listDramaScriptTemplates(),
      listDramaCastPresets(),
      listIpProjects(),
    ])
    dramaTemplates.value = templatesRes.data || []
    dramaCastPresets.value = castsRes.data || []
    ipProjects.value = projectsRes.data?.items || []
    if (!drama.project_id && ipProjects.value.length) {
      drama.project_id = ipProjects.value[0].projectId
    }
  } catch {
    dramaTemplates.value = []
    dramaCastPresets.value = []
    ipProjects.value = []
  }
}

async function loadProjectCharacters(projectId: number) {
  try {
    const res = await listCharacterProfiles({ projectId })
    projectCharacters.value = res.data?.items || []
    selectedCharacterIds.value = selectedCharacterIds.value.filter((id) =>
      projectCharacters.value.some((item) => item.characterId === id)
    )
  } catch {
    projectCharacters.value = []
    selectedCharacterIds.value = []
  }
}

function toggleProjectCharacter(characterId?: number) {
  if (!characterId) return
  if (selectedCharacterIds.value.includes(characterId)) {
    selectedCharacterIds.value = selectedCharacterIds.value.filter((id) => id !== characterId)
    return
  }
  if (selectedCharacterIds.value.length >= 6) {
    dramaFeedback.value = { type: 'error', message: '最多选择 6 个角色。' }
    return
  }
  selectedCharacterIds.value = [...selectedCharacterIds.value, characterId]
}

function characterProfileToReversal(item: CharacterProfileData): ReversalCharacter {
  return {
    name: item.name,
    role: item.role || item.identity || '',
    personality: item.personality || '',
    catchphrase: item.catchphrase || '',
    speaking_style: item.speakingStyle || '',
    character_id: item.characterId,
    drama_role: '',
  }
}

function resolveCharactersForGenerate(): ReversalCharacter[] | null {
  if (drama.cast_source === 'manual') {
    const manual = dramaCharacters.filter((item) => item.name.trim())
    return manual.length ? manual : null
  }
  if (drama.cast_source === 'ip_project') {
    const selected = projectCharacters.value
      .filter((item) => selectedCharacterIds.value.includes(item.characterId || 0))
      .map(characterProfileToReversal)
    return selected.length ? selected : null
  }
  return null
}

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
    // 后端不可用时保留本地历史兜底。
  }

  try {
    const raw = window.localStorage.getItem(getReversalHistoryStorageKey())
    const items = raw ? JSON.parse(raw) : []
    reversalHistory.value = Array.isArray(items) ? items : []
  } catch {
    reversalHistory.value = []
  }
}

function saveLocalReversalHistory(params: ReversalDramaParams, result: ReversalDramaResult) {
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
  selectedSchemeKey.value = item.params.scheme_key || selectedSchemeKey.value
  drama.template_key = item.params.template_key || 'workplace_reversal'
  drama.reversal_pattern = (item.params.reversal_pattern || 'auto') as ReversalPattern
  drama.cast_source = item.params.cast_source || (item.params.characters?.length ? 'manual' : 'default')
  drama.cast_preset_id = item.params.cast_preset_id || 0
  drama.project_id = item.params.project_id || drama.project_id
  drama.platform = item.params.platform || drama.platform
  drama.duration = item.params.duration || drama.duration
  drama.extra_requirements = item.params.extra_requirements || ''
  if (drama.cast_source === 'manual' && item.params.characters?.length) {
    dramaCharacters.splice(0, dramaCharacters.length, ...item.params.characters)
  } else {
    dramaCharacters.splice(0, dramaCharacters.length, { name: '', gender: '', role: '', personality: '', catchphrase: '', drama_role: '' })
  }
  if (drama.cast_source === 'ip_project' && item.params.characters?.length) {
    selectedCharacterIds.value = item.params.characters
      .map((item) => item.character_id)
      .filter((id): id is number => Boolean(id))
    void loadProjectCharacters(drama.project_id)
  }
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
  if (dramaCharacters.length >= 6) return
  dramaCharacters.push({ name: '', gender: '', role: '', personality: '', catchphrase: '', drama_role: '' })
}

async function saveCurrentCastPreset() {
  const name = castPresetName.value.trim()
  if (!name) {
    dramaFeedback.value = { type: 'error', message: '请先填写角色组名称。' }
    return
  }
  const characters = resolveCharactersForGenerate()
  if (!characters?.length) {
    dramaFeedback.value = { type: 'error', message: '当前没有可保存的角色，请先选择或填写角色。' }
    return
  }
  try {
    const res = await createDramaCastPreset({
      name,
      project_id: drama.cast_source === 'ip_project' ? drama.project_id : 0,
      characters,
      relationship_hint: selectedTemplate.value?.relationshipHint || '',
    })
    dramaCastPresets.value = [res.data, ...dramaCastPresets.value]
    drama.cast_source = 'preset'
    drama.cast_preset_id = res.data.castPresetId
    castPresetName.value = ''
    dramaFeedback.value = { type: 'success', message: `角色组「${res.data.name}」已保存。` }
  } catch {
    dramaFeedback.value = { type: 'error', message: '角色组保存失败，请稍后重试。' }
  }
}

function applyCastPreset(presetId: number) {
  const preset = dramaCastPresets.value.find((item) => item.castPresetId === presetId)
  if (!preset) return
  drama.cast_preset_id = presetId
  if (preset.projectId) {
    drama.project_id = preset.projectId
  }
}

function removeDramaCharacter(idx: number) {
  if (dramaCharacters.length <= 1) return
  dramaCharacters.splice(idx, 1)
}

async function reportCurrentGenerationAction(eventType: 'edited' | 'saved' | 'teleprompter_opened', metadata: Record<string, unknown> = {}) {
  if (!currentGenerationHistoryId.value || isGuestUser.value) return
  try {
    await reportGenerationActionEvent({
      history_id: currentGenerationHistoryId.value,
      event_type: eventType,
      content_type: 'reversal_drama',
      metadata,
    })
  } catch {
    // 埋点失败不能阻断用户继续写稿。
  }
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
  dramaFeedback.value = { type: 'info', message: '反转剧脚本正在创作中，预计 15-30 秒。请不要重复点击。' }
  addChatMessage('assistant', '反转剧脚本正在创作中，预计 15-30 秒...')

  const params = {
    product_name: drama.product_name.trim(),
    product_function: drama.product_function.trim(),
    pain_point: drama.pain_point.trim(),
    template_key: drama.template_key,
    reversal_pattern: drama.reversal_pattern,
    cast_source: drama.cast_source,
    cast_preset_id: drama.cast_source === 'preset' ? drama.cast_preset_id : 0,
    project_id: drama.cast_source === 'ip_project' ? drama.project_id : 0,
    characters: resolveCharactersForGenerate(),
    platform: drama.platform,
    duration: drama.duration,
    extra_requirements: drama.extra_requirements,
  }

  try {
    const res = await generateReversalDrama(params)
    dramaResult.value = res.data
    if (res.data.history_id) {
      currentGenerationHistoryId.value = Number(res.data.history_id)
    }
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
  } catch {
    dramaFeedback.value = { type: 'error', message: '反转剧生成失败，请调整输入内容。' }
    addChatMessage('assistant', '反转剧生成失败，请调整输入内容。')
  } finally {
    isGeneratingDrama.value = false
  }
}

function copyDramaMarkdown() {
  if (!dramaResult.value) return
  copyToClipboard(dramaResult.value.raw_markdown)
}

async function handleChatSend() {
  const msg = chatInput.value.trim()
  if (!msg || isCopilotStreaming.value) return

  addChatMessage('user', msg)
  chatInput.value = ''

  if (!currentContent.value) {
    addChatMessage('assistant', '⚠️ 当前没有可修改的剧本。请先生成反转剧脚本。')
    return
  }

  isCopilotStreaming.value = true
  let accumulatedContent = ''
  const assistantIdx = chatMessages.length
  chatMessages.push({ role: 'assistant', content: '', timestamp: Date.now() })

  copilotModifyStream(
    {
      content_type: 'reversal_drama',
      current_content: currentContent.value,
      user_instruction: msg,
      persona_id: 0,
      template_key: drama.template_key,
      cast_summary: castSummary.value,
    },
    (chunk: string) => {
      accumulatedContent += chunk
      chatMessages[assistantIdx].content = accumulatedContent
      scrollChatToBottom()
    },
    () => {
      const finalContent = accumulatedContent
      const separator = finalContent.lastIndexOf('---')
      const updatedContent = separator > 0 ? finalContent.substring(0, separator).trim() : finalContent
      if (dramaResult.value && updatedContent) {
        dramaResult.value = { ...dramaResult.value, raw_markdown: updatedContent }
      }
      void reportCurrentGenerationAction('edited', { via: 'copilot', instruction: msg.slice(0, 200) })
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

defineExpose({
  generateDrama: handleGenerateDrama,
  isGeneratingDrama,
  dramaGenerateReason,
})
</script>

<template>
  <div class="workspace workspace-embedded">
    <p class="sr-only" role="status" aria-live="polite" :aria-label="liveStatusMessage"></p>

    <main class="workspace-main workspace-main-embedded">
      <section class="panel panel-left glass-card drama-panel">
        <div class="drama-form-area">
          <h3 class="drama-section-title">短剧脚本工坊</h3>
          <p class="drama-subtitle">选择剧本类型与角色组，输入产品和痛点，生成可拍摄、可检查、可迭代的 30-60 秒反转剧分镜脚本。</p>

          <div class="drama-config-toggle">
            <button class="btn btn-ghost btn-sm" type="button" @click="showDramaConfig = !showDramaConfig">
              {{ showDramaConfig ? '收起剧本配置' : '展开剧本配置（类型 / 套路 / 角色组）' }}
            </button>
          </div>

          <div v-if="showDramaConfig" class="drama-config-panel">
            <div class="form-row">
              <label class="form-label">剧本类型</label>
              <div v-if="dramaTemplates.length" class="template-gallery">
                <div v-for="group in groupedDramaTemplates" :key="group.category" class="template-group">
                  <span class="template-group-label">{{ group.category }}</span>
                  <div class="template-card-grid">
                    <button
                      v-for="tpl in group.items"
                      :key="tpl.key"
                      type="button"
                      class="template-card"
                      :class="{ active: drama.template_key === tpl.key }"
                      @click="selectDramaTemplate(tpl.key)"
                    >
                      <strong>{{ tpl.name }}</strong>
                      <small>{{ tpl.description }}</small>
                      <em v-if="tpl.exampleHint">{{ tpl.exampleHint }}</em>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="form-row">
              <label class="form-label">反转套路</label>
              <select v-model="drama.reversal_pattern" class="input">
                <option v-for="opt in REVERSAL_PATTERN_OPTIONS" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <p v-if="selectedTemplate?.relationshipHint" class="drama-config-hint">
              人物关系：{{ selectedTemplate.relationshipHint }}
            </p>

            <div class="form-row">
              <label class="form-label">角色来源</label>
              <select v-model="drama.cast_source" class="input">
                <option value="default">模板默认角色组</option>
                <option value="preset">已保存角色组</option>
                <option value="ip_project">IP 项目角色库</option>
                <option value="manual">手动填写角色</option>
              </select>
            </div>

            <div v-if="drama.cast_source === 'preset'" class="form-row">
              <label class="form-label">选择角色组</label>
              <select
                v-model.number="drama.cast_preset_id"
                class="input"
                @change="applyCastPreset(drama.cast_preset_id)"
              >
                <option :value="0" disabled>请选择角色组</option>
                <option v-for="preset in dramaCastPresets" :key="preset.castPresetId" :value="preset.castPresetId">
                  {{ preset.name }}
                </option>
              </select>
            </div>

            <div v-if="drama.cast_source === 'ip_project'" class="drama-ip-cast-panel">
              <div class="form-row">
                <label class="form-label">IP 项目</label>
                <select v-model.number="drama.project_id" class="input">
                  <option v-for="project in ipProjects" :key="project.projectId" :value="project.projectId">
                    {{ project.name }}
                  </option>
                </select>
              </div>
              <div v-if="projectCharacters.length" class="character-select-list">
                <label
                  v-for="character in projectCharacters"
                  :key="character.characterId"
                  class="character-select-item"
                >
                  <input
                    type="checkbox"
                    :checked="selectedCharacterIds.includes(character.characterId || 0)"
                    @change="toggleProjectCharacter(character.characterId)"
                  />
                  <span>
                    <strong>{{ character.name }}</strong>
                    <small>{{ character.role || character.identity || '未设置岗位' }}</small>
                  </span>
                </label>
              </div>
              <p v-else class="drama-config-hint">当前项目暂无角色，请先在 IP 资产中创建人物角色。</p>
            </div>

            <div v-if="drama.cast_source === 'manual'" class="custom-characters">
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
                  <select v-model="ch.drama_role" class="input">
                    <option v-for="opt in DRAMA_ROLE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                  </select>
                  <input v-model="ch.catchphrase" class="input" placeholder="口头禅" />
                </div>
                <textarea v-model="ch.personality" class="input" rows="2"
                  placeholder="性格底色（例：极致效率追求者，管理狂魔）"
                  style="margin-top: 6px;"></textarea>
              </div>
              <button class="btn btn-ghost btn-sm" @click="addDramaCharacter">+ 添加人物</button>
            </div>

            <div v-if="drama.cast_source !== 'default' && !isGuestUser" class="cast-preset-save-row">
              <input v-model="castPresetName" class="input" placeholder="角色组名称（保存当前选择）" />
              <button class="btn btn-ghost btn-sm" type="button" @click="saveCurrentCastPreset">保存为角色组</button>
            </div>
          </div>

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

          <div v-if="workMode === 'advanced'" class="form-row">
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
                <span>{{ formatDramaHistoryTime(item.createdAt) }} · {{ item.params.template_key || 'workplace_reversal' }} · {{ item.productName }}</span>
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

        <div class="drama-result-area" v-if="dramaResult">
          <div class="drama-result-header">
            <h3 class="drama-section-title">📜 生成结果</h3>
            <div class="drama-result-actions">
              <button
                class="btn btn-ghost btn-sm"
                :disabled="isDeliveringTeleprompter"
                @click="handleSendToTeleprompter"
              >{{ isDeliveringTeleprompter ? '送入中…' : '送提词器' }}</button>
              <button
                class="btn btn-ghost btn-sm"
                :disabled="isDeliveringVideo"
                @click="handleSendToVideoAip"
              >{{ isDeliveringVideo ? '创建中…' : '送视频出片' }}</button>
              <button class="btn btn-ghost btn-sm" @click="copyDramaMarkdown">复制全文</button>
            </div>
          </div>

          <div class="overview-card" v-if="dramaResult.overview && dramaResult.overview.title">
            <h4 class="overview-title">《{{ dramaResult.overview.title }}》</h4>
            <div class="overview-meta">
              <span v-if="dramaResult.scheme_name" class="meta-chip">📦 {{ dramaResult.scheme_name }}</span>
              <span v-if="dramaResult.template_name" class="meta-chip">🎭 {{ dramaResult.template_name }}</span>
              <span v-if="dramaResult.reversal_pattern" class="meta-chip">📐 {{ dramaResult.reversal_pattern === 'auto' ? '自动套路' : `套路 ${dramaResult.reversal_pattern}` }}</span>
              <span v-if="dramaResult.overview.duration" class="meta-chip">⏱ {{ dramaResult.overview.duration }}</span>
              <span v-if="dramaResult.overview.reversal_type" class="meta-chip meta-chip-accent">🌀 {{ dramaResult.overview.reversal_type }}</span>
              <span v-if="dramaResult.overview.characters" class="meta-chip">👥 {{ dramaResult.overview.characters }}</span>
            </div>
            <p v-if="dramaResult.overview.product" class="overview-row"><strong>产品：</strong>{{ dramaResult.overview.product }}</p>
            <p v-if="dramaResult.overview.pain_point" class="overview-row"><strong>痛点：</strong>{{ dramaResult.overview.pain_point }}</p>
          </div>

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

          <div v-if="dramaResult.checklist && dramaResult.checklist.length" class="checklist-wrap">
            <h4 class="overview-title">自检清单</h4>
            <ul class="checklist">
              <li v-for="(c, i) in dramaResult.checklist" :key="i" :class="{ passed: c.passed }">
                <span class="check-mark">{{ c.passed ? '✅' : '❌' }}</span>
                {{ c.item }}
              </li>
            </ul>
          </div>

          <details v-if="isAdminUser" class="raw-md-details">
            <summary>查看原始内容</summary>
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

      <section class="panel panel-right glass-card">
        <div class="chat-header">
          <div class="chat-title">
            <span class="chat-icon" aria-hidden="true">AI</span>
            <span>AI Copilot</span>
          </div>
          <span class="badge badge-success">在线</span>
        </div>

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

          <div v-if="isCopilotStreaming" class="chat-bubble-wrapper chat-assistant">
            <div class="chat-avatar" aria-hidden="true">AI</div>
            <div class="chat-bubble bubble-assistant">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

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

<style scoped src="../styles/copilot-workspace.css"></style>
<style scoped>
.work-mode-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 12px;
}

.scheme-gallery {
  display: grid;
  gap: 12px;
}

.scheme-card strong {
  font-size: 13px;
}

.drama-result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.drama-config-toggle {
  margin: 8px 0 12px;
}

.drama-config-panel {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
}

.drama-config-hint {
  margin: 0 0 10px;
  color: rgba(255, 255, 255, 0.62);
  font-size: 13px;
  line-height: 1.5;
}

.character-select-list {
  display: grid;
  gap: 8px;
}

.character-select-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
}

.character-select-item strong {
  display: block;
}

.character-select-item small {
  color: rgba(255, 255, 255, 0.55);
}

.cast-preset-save-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  margin-top: 10px;
}

.template-gallery {
  display: grid;
  gap: 12px;
}

.template-group-label {
  display: block;
  margin-bottom: 6px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.template-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
}

.template-card {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.template-card:hover,
.template-card.active {
  border-color: rgba(99, 179, 237, 0.55);
  background: rgba(99, 179, 237, 0.08);
}

.template-card strong {
  font-size: 14px;
}

.template-card small {
  color: rgba(255, 255, 255, 0.62);
  font-size: 12px;
  line-height: 1.4;
}

.template-card em {
  color: rgba(255, 255, 255, 0.45);
  font-size: 11px;
  font-style: normal;
  line-height: 1.4;
}
</style>

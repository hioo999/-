<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import IpSectionAssistPanel from '../components/IpSectionAssistPanel.vue'
import {
  fullExampleIpForm,
  ipFieldHints,
  ipSectionLabels,
  ipSectionTemplates,
  platformOptions,
  togglePlatformCsv,
  type IpSectionKey,
} from '../config/ipAssetTemplates'
import {
  createSprint1IpAsset,
  generateSprint1IpAssetSection,
  getSprint1IpAsset,
  listSprint1IpAssets,
  updateSprint1IpAsset,
  type Sprint1IpAsset,
  type Sprint1IpAssetPayload,
} from '../api'
import { useGuestAccess } from '../composables/useGuestAccess'
import {
  clearIpAssetDraft,
  hasStoredIpAssetDraft,
  persistIpAssetDraft,
  restoreIpAssetDraft,
} from '../composables/useIpAssetDraft'
import type { ActiveUser } from '../stores/auth'

const props = defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  requestLogin: [path?: string | null]
}>()

const { promptLogin } = useGuestAccess()
const isGuestUser = computed(() => !props.currentUser?.token)
const preserveDraftOnNextLoad = ref(false)

type StageKey = 'home' | IpSectionKey

interface StageItem {
  key: StageKey
  label: string
}

interface IpAssetForm {
  name: string
  type: string
  industry: string
  targetAudience: string
  businessGoal: string
  mainPlatforms: string
  secondaryPlatforms: string
  tone: string
  visualStyle: string
  conversionPath: string
  forbiddenExpressions: string
}

const stages: StageItem[] = [
  { key: 'home', label: 'IP 列表' },
  { key: 'ip', label: 'IP 资料' },
  { key: 'strategy', label: '人设定位' },
  { key: 'columns', label: '平台配置' },
  { key: 'topics', label: '内容规则' },
]

const wizardStageKeys: Array<Exclude<StageKey, 'home'>> = ['ip', 'strategy', 'columns', 'topics']

const wizardStepHints: Record<Exclude<StageKey, 'home'>, string> = {
  ip: '填写 IP 名称、类型和商业目标，让系统知道你在为谁生产内容。',
  strategy: '补齐行业与目标用户，后续选题和文案会更贴近受众。',
  columns: '配置主平台和辅助平台，决定内容优先分发到哪里。',
  topics: '设定语气、视觉和转化路径，约束生成内容的风格边界。',
}

const exampleIpForm = fullExampleIpForm

const currentStage = ref<StageKey>('home')
const selectedIpId = ref('')
const availableIps = ref<Sprint1IpAsset[]>([])
const currentIp = ref<Sprint1IpAsset | null>(null)
const isLoading = ref(false)
const generatingSection = ref<IpSectionKey | ''>('')
const statusMessage = ref('')
const selectedTemplateKeys = reactive<Record<IpSectionKey, string>>({
  ip: ipSectionTemplates.ip[0]?.key || '',
  strategy: ipSectionTemplates.strategy[0]?.key || '',
  columns: ipSectionTemplates.columns[0]?.key || '',
  topics: ipSectionTemplates.topics[0]?.key || '',
})

const ipForm = reactive<IpAssetForm>({
  name: '',
  type: '',
  industry: '',
  targetAudience: '',
  businessGoal: '',
  mainPlatforms: '',
  secondaryPlatforms: '',
  tone: '',
  visualStyle: '',
  conversionPath: '',
  forbiddenExpressions: '',
})

const currentIpName = computed(() => currentIp.value?.name || '尚未选择 IP')

const requiredFieldGroups: Array<{ stage: StageKey; label: string; fields: Array<keyof IpAssetForm> }> = [
  { stage: 'ip', label: 'IP 资料', fields: ['name', 'type', 'businessGoal'] },
  { stage: 'strategy', label: '人设定位', fields: ['industry', 'targetAudience'] },
  { stage: 'columns', label: '平台配置', fields: ['mainPlatforms'] },
  { stage: 'topics', label: '内容规则', fields: ['tone', 'visualStyle', 'conversionPath'] },
]

const ipCompleteness = computed(() => {
  const fields = requiredFieldGroups.flatMap((group) => group.fields)
  const completed = fields.filter((field) => String(ipForm[field] || '').trim()).length
  const percent = fields.length ? Math.round((completed / fields.length) * 100) : 0
  const missingGroups = requiredFieldGroups
    .map((group) => ({
      ...group,
      missing: group.fields.filter((field) => !String(ipForm[field] || '').trim()),
    }))
    .filter((group) => group.missing.length)

  return {
    percent,
    completed,
    total: fields.length,
    missingGroups,
    status: percent >= 100 ? '完整' : percent >= 60 ? '可生成，建议完善' : '需优化',
  }
})

const nextMissingGroup = computed(() => ipCompleteness.value.missingGroups[0] || null)
const requiredFieldLabels: Record<keyof IpAssetForm, string> = {
  name: '名称',
  type: '类型',
  industry: '行业',
  targetAudience: '目标用户',
  businessGoal: '商业目标',
  mainPlatforms: '主平台',
  secondaryPlatforms: '辅助平台',
  tone: '表达语气',
  visualStyle: '视觉风格',
  conversionPath: '转化路径',
  forbiddenExpressions: '禁用表达',
}

const missingRequiredFields = computed(() => new Set(
  requiredFieldGroups.flatMap((group) => group.fields).filter((field) => !String(ipForm[field] || '').trim())
))

function isFieldMissing(field: keyof IpAssetForm) {
  return missingRequiredFields.value.has(field)
}

function getStagePercent(stage: StageKey) {
  if (stage === 'home') return availableIps.value.length ? 100 : 0
  const group = requiredFieldGroups.find((item) => item.stage === stage)
  if (!group) return 0
  const completed = group.fields.filter((field) => String(ipForm[field] || '').trim()).length
  return Math.round((completed / group.fields.length) * 100)
}

function goNextMissingStage() {
  const nextStage = nextMissingGroup.value?.stage
  if (nextStage) currentStage.value = nextStage
}

const isWizardActive = computed(() => currentStage.value !== 'home')
const showWelcomeGuide = computed(() => currentStage.value === 'home' && !availableIps.value.length)
const showListGuide = computed(() => currentStage.value === 'home' && availableIps.value.length > 0)
const currentWizardStepIndex = computed(() => {
  if (currentStage.value === 'home') return -1
  return wizardStageKeys.indexOf(currentStage.value)
})
const currentWizardHint = computed(() => {
  if (currentStage.value === 'home') return ''
  return wizardStepHints[currentStage.value]
})
const workflowSteps = computed(() => wizardStageKeys.map((key) => {
  const stageItem = stages.find((item) => item.key === key)
  const percent = getStagePercent(key)
  return {
    key,
    label: stageItem?.label || key,
    percent,
    done: percent === 100,
    current: currentStage.value === key,
  }
}))

function getStageMissingLabels(stage: StageKey) {
  const group = requiredFieldGroups.find((item) => item.stage === stage)
  if (!group) return []
  return group.fields
    .filter((field) => !String(ipForm[field] || '').trim())
    .map((field) => requiredFieldLabels[field])
}

function goPrevWizardStep() {
  const index = currentWizardStepIndex.value
  if (index > 0) {
    currentStage.value = wizardStageKeys[index - 1]
    statusMessage.value = ''
  }
}

function goNextWizardStep() {
  const stage = currentStage.value
  if (stage === 'home') return
  const missing = getStageMissingLabels(stage)
  if (missing.length) {
    statusMessage.value = `请先补齐：${missing.join('、')}`
    return
  }
  const index = currentWizardStepIndex.value
  if (index < wizardStageKeys.length - 1) {
    currentStage.value = wizardStageKeys[index + 1]
    statusMessage.value = ''
  }
}

function fillExampleAndStart() {
  currentIp.value = null
  selectedIpId.value = ''
  Object.assign(ipForm, exampleIpForm)
  currentStage.value = 'ip'
  statusMessage.value = '已填入完整示例，可按步骤调整后保存'
}

function buildFormContext() {
  return {
    name: ipForm.name.trim(),
    type: ipForm.type.trim(),
    industry: ipForm.industry.trim(),
    targetAudience: ipForm.targetAudience.trim(),
    businessGoal: ipForm.businessGoal.trim(),
    mainPlatforms: ipForm.mainPlatforms.trim(),
    secondaryPlatforms: ipForm.secondaryPlatforms.trim(),
    tone: ipForm.tone.trim(),
    visualStyle: ipForm.visualStyle.trim(),
    conversionPath: ipForm.conversionPath.trim(),
    forbiddenExpressions: ipForm.forbiddenExpressions.trim(),
  }
}

function applyFieldsToForm(fields: Record<string, string>) {
  for (const [key, value] of Object.entries(fields)) {
    if (key in ipForm) {
      ipForm[key as keyof IpAssetForm] = value
    }
  }
}

function applySectionTemplate(section: IpSectionKey) {
  const template = ipSectionTemplates[section].find((item) => item.key === selectedTemplateKeys[section])
    || ipSectionTemplates[section][0]
  if (!template) return
  applyFieldsToForm(template.fields as Record<string, string>)
  statusMessage.value = `已套用「${template.label}」模板，可继续微调后保存`
}

async function generateSectionContent(section: IpSectionKey) {
  generatingSection.value = section
  statusMessage.value = `正在生成${ipSectionLabels[section]}...`
  try {
    const res = await generateSprint1IpAssetSection({
      section,
      templateKey: selectedTemplateKeys[section],
      mode: 'smart',
      context: buildFormContext(),
    })
    applyFieldsToForm(res.data.fields)
    const sourceLabel = res.data.source === 'ai' ? 'AI' : res.data.source === 'template' ? '模板' : '智能推荐'
    statusMessage.value = `${ipSectionLabels[section]}已生成（${sourceLabel}），请确认后保存`
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    statusMessage.value = typeof detail === 'string'
      ? detail
      : detail?.message || error?.message || '生成失败，请稍后重试'
    applySectionTemplate(section)
  } finally {
    generatingSection.value = ''
  }
}

async function generateAllSections() {
  if (currentStage.value === 'home') {
    createNewIp()
  }
  for (const section of wizardStageKeys) {
    currentStage.value = section
    await generateSectionContent(section)
  }
  statusMessage.value = '已生成完整 IP 档案草稿，请逐步确认后保存'
}

function generateCurrentSection() {
  if (currentStage.value === 'home') return
  void generateSectionContent(currentStage.value)
}

function isPlatformSelected(field: 'mainPlatforms' | 'secondaryPlatforms', platformKey: string) {
  return ipForm[field].split(',').map((item) => item.trim()).includes(platformKey)
}

function togglePlatformField(field: 'mainPlatforms' | 'secondaryPlatforms', platformKey: string) {
  ipForm[field] = togglePlatformCsv(ipForm[field], platformKey)
}

function parseCsv(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

function getApiErrorMessage(error: unknown, fallback: string) {
  const err = error as { response?: { status?: number; data?: { detail?: string | { message?: string } } }; message?: string }
  const status = err.response?.status
  const detail = err.response?.data?.detail
  if (status === 401) {
    return typeof detail === 'string' ? detail : '请先登录后再保存 IP 档案'
  }
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && detail.message) return detail.message
  return err.message || fallback
}

function isAuthError(error: unknown) {
  return (error as { response?: { status?: number } })?.response?.status === 401
}

function requireLoginForSave() {
  preserveDraftOnNextLoad.value = true
  persistDraft()
  statusMessage.value = '保存 IP 档案需要先登录，登录后会保留当前填写内容'
  promptLogin('/workspace/ip-assets')
  emit('requestLogin', '/workspace/ip-assets')
}

function joinCsv(value: string[]) {
  return value.join(',')
}

function setStage(stage: StageKey) {
  currentStage.value = stage
}

function hydrateForm(ip: Sprint1IpAsset) {
  ipForm.name = ip.name
  ipForm.type = ip.type
  ipForm.industry = ip.industry
  ipForm.targetAudience = ip.targetAudience
  ipForm.businessGoal = ip.businessGoal
  ipForm.mainPlatforms = joinCsv(ip.mainPlatforms)
  ipForm.secondaryPlatforms = joinCsv(ip.secondaryPlatforms)
  ipForm.tone = ip.tone
  ipForm.visualStyle = ip.visualStyle
  ipForm.conversionPath = ip.conversionPath
  ipForm.forbiddenExpressions = ip.forbiddenExpressions
}

function resetForm() {
  ipForm.name = ''
  ipForm.type = ''
  ipForm.industry = ''
  ipForm.targetAudience = ''
  ipForm.businessGoal = ''
  ipForm.mainPlatforms = ''
  ipForm.secondaryPlatforms = ''
  ipForm.tone = ''
  ipForm.visualStyle = ''
  ipForm.conversionPath = ''
  ipForm.forbiddenExpressions = ''
}

function hasDraftFormInput() {
  return Object.values(ipForm).some((value) => String(value || '').trim())
}

function buildDraftSnapshot() {
  return {
    form: { ...ipForm },
    stage: currentStage.value,
    selectedTemplateKeys: { ...selectedTemplateKeys },
    updatedAt: new Date().toISOString(),
  }
}

function persistDraft() {
  persistIpAssetDraft(buildDraftSnapshot())
}

function applyDraftSnapshot() {
  const draft = restoreIpAssetDraft()
  if (!draft) return false
  Object.assign(ipForm, draft.form)
  if (draft.stage) currentStage.value = draft.stage as StageKey
  if (draft.selectedTemplateKeys) Object.assign(selectedTemplateKeys, draft.selectedTemplateKeys)
  currentIp.value = null
  selectedIpId.value = ''
  return true
}

function shouldPreserveDraft(options: { preserveDraft?: boolean } = {}) {
  return Boolean(
    options.preserveDraft
    || preserveDraftOnNextLoad.value
    || hasDraftFormInput()
    || hasStoredIpAssetDraft(),
  )
}

function restoreDraftIfNeeded(message = '已恢复你填写的内容，确认无误后可保存') {
  const restoredFromStorage = applyDraftSnapshot()
  const restored = restoredFromStorage || hasDraftFormInput()
  if (restored) {
    statusMessage.value = message
  }
  preserveDraftOnNextLoad.value = false
  return restored
}

function buildPayload(): Sprint1IpAssetPayload {
  return {
    name: ipForm.name.trim(),
    type: ipForm.type.trim(),
    industry: ipForm.industry.trim(),
    targetAudience: ipForm.targetAudience.trim(),
    businessGoal: ipForm.businessGoal.trim(),
    mainPlatforms: parseCsv(ipForm.mainPlatforms),
    secondaryPlatforms: parseCsv(ipForm.secondaryPlatforms),
    tone: ipForm.tone.trim(),
    visualStyle: ipForm.visualStyle.trim(),
    conversionPath: ipForm.conversionPath.trim(),
    forbiddenExpressions: ipForm.forbiddenExpressions.trim(),
  }
}

async function loadIpAssets(options: { preserveDraft?: boolean } = {}) {
  isLoading.value = true
  try {
    const res = await listSprint1IpAssets({ pageSize: 100 })
    availableIps.value = res.data.items
    if (!availableIps.value.length) {
      currentIp.value = null
      selectedIpId.value = ''
      if (currentStage.value !== 'home' || hasDraftFormInput() || hasStoredIpAssetDraft()) {
        restoreDraftIfNeeded('新建 IP')
        return
      }
      resetForm()
      statusMessage.value = '暂无 IP'
      currentStage.value = 'home'
      return
    }

    if (shouldPreserveDraft(options) && !currentIp.value) {
      restoreDraftIfNeeded()
      return
    }

    const nextIpId = selectedIpId.value && availableIps.value.some((item) => item.id === selectedIpId.value)
      ? selectedIpId.value
      : availableIps.value[0].id
    selectedIpId.value = nextIpId
    await loadIpDetails(nextIpId)
  } catch (error) {
    if (isAuthError(error)) {
      statusMessage.value = getApiErrorMessage(error, '请先登录后再保存 IP 档案')
      requireLoginForSave()
      return
    }
    statusMessage.value = getApiErrorMessage(error, '加载失败')
  } finally {
    isLoading.value = false
  }
}

async function loadIpDetails(ipId: string) {
  if (!ipId) {
    currentIp.value = null
    resetForm()
    return
  }

  isLoading.value = true
  try {
    const res = await getSprint1IpAsset(ipId)
    currentIp.value = res.data
    hydrateForm(res.data)
    statusMessage.value = `已加载 ${res.data.name}`
  } catch (error) {
    statusMessage.value = (error as Error)?.message || '加载 IP 失败'
  } finally {
    isLoading.value = false
  }
}

async function switchIp(ipId: string) {
  if (!ipId) return
  selectedIpId.value = ipId
  currentStage.value = 'home'
  clearIpAssetDraft()
  await loadIpDetails(ipId)
}

function createNewIp() {
  currentIp.value = null
  selectedIpId.value = ''
  resetForm()
  clearIpAssetDraft()
  currentStage.value = 'ip'
  statusMessage.value = '新建 IP'
}

async function saveIpAsset() {
  const payload = buildPayload()
  if (!payload.name || !payload.type || !payload.industry || !payload.targetAudience || !payload.businessGoal) {
    const missing = Array.from(missingRequiredFields.value).map((field) => requiredFieldLabels[field]).join('、')
    statusMessage.value = `请补齐必填项：${missing}`
    return
  }

  if (isGuestUser.value) {
    requireLoginForSave()
    return
  }

  isLoading.value = true
  try {
    if (currentIp.value) {
      const res = await updateSprint1IpAsset(currentIp.value.id, payload)
      currentIp.value = res.data
      selectedIpId.value = res.data.id
      statusMessage.value = '已保存 IP 资料'
    } else {
      const res = await createSprint1IpAsset(payload)
      currentIp.value = res.data.asset
      selectedIpId.value = res.data.asset.id
      statusMessage.value = '已创建 IP'
    }

    await loadIpAssets()
    clearIpAssetDraft()
  } catch (error) {
    if (isAuthError(error)) {
      statusMessage.value = getApiErrorMessage(error, '登录已失效，请重新登录后再保存')
      requireLoginForSave()
      return
    }
    statusMessage.value = getApiErrorMessage(error, '保存失败，请稍后重试')
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  if (hasStoredIpAssetDraft()) {
    restoreDraftIfNeeded('已恢复上次填写的内容')
  }
  if (props.currentUser?.token) {
    void loadIpAssets({ preserveDraft: hasDraftFormInput() || hasStoredIpAssetDraft() })
    return
  }
  statusMessage.value = hasDraftFormInput()
    ? '已恢复上次填写的内容，登录后可保存到云端'
    : '登录后可保存 IP 档案到云端'
})

watch(
  () => ({ ...ipForm }),
  () => {
    persistDraft()
  },
  { deep: true },
)

watch(
  () => [currentStage.value, selectedTemplateKeys.ip, selectedTemplateKeys.strategy, selectedTemplateKeys.columns, selectedTemplateKeys.topics] as const,
  () => {
    persistDraft()
  },
)

watch(
  () => props.currentUser?.token,
  (token, previous) => {
    if (token && !previous) {
      restoreDraftIfNeeded('登录成功，已恢复你填写的内容，确认后可保存')
      void loadIpAssets({ preserveDraft: true })
    }
  },
)
</script>

<template>
  <div class="sprint-shell" :class="{ 'sprint-focus': isWizardActive }">
    <div v-if="isGuestUser" class="guest-save-banner" role="note">
      <div>
        <strong>当前未登录</strong>
        <span>可以先填写并生成内容；登录后会自动恢复当前填写，无需重填。</span>
      </div>
      <button class="primary-pill" type="button" @click="requireLoginForSave">登录 / 注册</button>
    </div>

    <header class="sprint-hero">
      <div>
        <h2>IP 档案</h2>
        <p v-if="!isWizardActive" class="hero-lead">先建好 IP 档案，后续选题、生成和发布会更稳定。</p>
        <div class="completeness-summary" data-testid="ip-completeness-summary">
          <div class="completeness-meter">
            <span :style="{ width: `${ipCompleteness.percent}%` }"></span>
          </div>
          <strong data-testid="ip-completeness-percent">完整度 {{ ipCompleteness.percent }}%</strong>
          <small>
            {{ ipCompleteness.status }} · {{ ipCompleteness.completed }}/{{ ipCompleteness.total }} 项已补齐
          </small>
          <button v-if="nextMissingGroup && !isWizardActive" class="next-action-link" @click="goNextMissingStage">
            下一步：补齐{{ nextMissingGroup.label }}
          </button>
        </div>
      </div>
      <div class="hero-actions">
        <select v-model="selectedIpId" class="ip-switcher" :disabled="isLoading || !availableIps.length" @change="switchIp(selectedIpId)">
          <option value="">选择已有 IP</option>
          <option v-for="ip in availableIps" :key="ip.id" :value="ip.id">{{ ip.name }}</option>
        </select>
        <button class="primary-pill" @click="createNewIp">新建 IP</button>
      </div>
    </header>

    <section v-if="showWelcomeGuide" class="ip-guide-panel" role="region" aria-label="IP 档案引导">
      <div class="guide-copy">
        <strong>4 步建好你的第一个 IP 档案</strong>
        <p>按「资料 → 定位 → 平台 → 内容规则」补齐后，生产中心生成内容时会自动参考这些设定。</p>
      </div>
      <div class="guide-actions">
        <button class="primary-pill" @click="createNewIp">创建第一个 IP</button>
        <button class="ghost-pill" @click="fillExampleAndStart">套用完整示例</button>
        <button class="ghost-pill" :disabled="Boolean(generatingSection)" @click="generateAllSections">一键生成完整档案</button>
      </div>
    </section>

    <section v-else-if="showListGuide" class="ip-guide-panel compact" role="region" aria-label="IP 档案引导">
      <div class="guide-copy">
        <strong>继续补齐档案，或新建另一个 IP</strong>
        <p v-if="nextMissingGroup">当前档案还缺「{{ nextMissingGroup.label }}」，补齐后生成质量更稳定。</p>
        <p v-else>档案已完整，可直接进入生产中心开始内容生产。</p>
      </div>
      <div class="guide-actions">
        <button v-if="nextMissingGroup" class="primary-pill" @click="goNextMissingStage">补齐{{ nextMissingGroup.label }}</button>
        <button class="ghost-pill" @click="createNewIp">新建 IP</button>
      </div>
    </section>

    <div v-if="isWizardActive" class="wizard-focus-bar" role="region" aria-label="当前建档步骤">
      <div class="focus-step">
        <small>当前步骤</small>
        <strong>{{ stages.find((item) => item.key === currentStage)?.label }}</strong>
        <span>{{ currentWizardHint }}</span>
      </div>
      <div class="focus-progress">
        <span>第 {{ currentWizardStepIndex + 1 }} / {{ wizardStageKeys.length }} 步</span>
        <strong>完整度 {{ ipCompleteness.percent }}%</strong>
      </div>
      <div class="focus-actions">
        <button class="ghost-pill" :disabled="Boolean(generatingSection)" @click="generateCurrentSection">
          {{ generatingSection ? '生成中...' : '一键生成本步' }}
        </button>
        <button class="ghost-pill" :disabled="Boolean(generatingSection)" @click="generateAllSections">生成完整档案</button>
        <button class="ghost-pill" @click="currentStage = 'home'">返回 IP 列表</button>
      </div>
    </div>

    <nav class="stage-nav" aria-label="IP 档案阶段">
      <button
        v-for="stage in stages"
        :key="stage.key"
        class="stage-tab"
        :class="{ active: currentStage === stage.key }"
        :aria-pressed="currentStage === stage.key"
        @click="setStage(stage.key)"
      >
        <span>{{ stage.label }}</span>
        <small>{{ getStagePercent(stage.key) }}%</small>
      </button>
    </nav>

    <div class="sprint-body" :class="{ 'wizard-layout': isWizardActive }">
    <main class="sprint-main">
      <section v-if="currentStage === 'home'" class="dashboard-grid">
        <button
          v-for="ip in availableIps"
          :key="ip.id"
          class="ip-list-row"
          :class="{ active: selectedIpId === ip.id }"
          type="button"
          :aria-current="selectedIpId === ip.id ? 'true' : undefined"
          @click="switchIp(ip.id)"
        >
          <strong>{{ ip.name }}</strong>
          <span>{{ ip.industry }}</span>
          <span class="status-pill" :class="ip.profileStatus === 'complete' ? 'complete' : 'incomplete'">
            {{ ip.profileStatus === 'complete' ? '完整' : '需优化' }}
          </span>
          <small>{{ ip.updatedAt?.slice(0, 10) }}</small>
        </button>
        <div v-if="!availableIps.length" class="empty-state">
          <strong>还没有 IP 档案</strong>
          <span>可使用上方引导创建，或点击「用示例开始」快速体验完整流程。</span>
        </div>
      </section>

      <section v-else-if="currentStage === 'ip'" class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>IP 资料</h3>
            <p class="panel-hint">{{ wizardStepHints.ip }}</p>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <IpSectionAssistPanel
          section="ip"
          section-label="IP 资料"
          :templates="ipSectionTemplates.ip"
          :selected-template-key="selectedTemplateKeys.ip"
          :is-generating="generatingSection === 'ip'"
          @update:selected-template-key="selectedTemplateKeys.ip = $event"
          @apply-template="applySectionTemplate('ip')"
          @generate-section="generateSectionContent('ip')"
        />
        <div class="form-grid">
          <label :class="{ invalid: isFieldMissing('name') }">
            名称 <span class="required-mark">*</span>
            <input v-model="ipForm.name" required :placeholder="ipFieldHints.name.placeholder" :aria-invalid="isFieldMissing('name')" />
            <small class="field-hint">{{ ipFieldHints.name.hint }}</small>
          </label>
          <label :class="{ invalid: isFieldMissing('type') }">
            类型 <span class="required-mark">*</span>
            <input v-model="ipForm.type" required :placeholder="ipFieldHints.type.placeholder" :aria-invalid="isFieldMissing('type')" />
            <small class="field-hint">{{ ipFieldHints.type.hint }}</small>
          </label>
          <label :class="{ invalid: isFieldMissing('businessGoal') }">
            商业目标 <span class="required-mark">*</span>
            <input v-model="ipForm.businessGoal" required :placeholder="ipFieldHints.businessGoal.placeholder" :aria-invalid="isFieldMissing('businessGoal')" />
            <small class="field-hint">{{ ipFieldHints.businessGoal.hint }}</small>
          </label>
        </div>
      </section>

      <section v-else-if="currentStage === 'strategy'" class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>人设定位</h3>
            <p class="panel-hint">{{ wizardStepHints.strategy }}</p>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <IpSectionAssistPanel
          section="strategy"
          section-label="人设定位"
          :templates="ipSectionTemplates.strategy"
          :selected-template-key="selectedTemplateKeys.strategy"
          :is-generating="generatingSection === 'strategy'"
          @update:selected-template-key="selectedTemplateKeys.strategy = $event"
          @apply-template="applySectionTemplate('strategy')"
          @generate-section="generateSectionContent('strategy')"
        />
        <div class="form-grid">
          <label :class="{ invalid: isFieldMissing('industry') }">
            行业 <span class="required-mark">*</span>
            <input v-model="ipForm.industry" required :placeholder="ipFieldHints.industry.placeholder" :aria-invalid="isFieldMissing('industry')" />
            <small class="field-hint">{{ ipFieldHints.industry.hint }}</small>
          </label>
          <label :class="{ invalid: isFieldMissing('targetAudience') }">
            目标用户 <span class="required-mark">*</span>
            <textarea v-model="ipForm.targetAudience" rows="3" required :placeholder="ipFieldHints.targetAudience.placeholder" :aria-invalid="isFieldMissing('targetAudience')"></textarea>
            <small class="field-hint">{{ ipFieldHints.targetAudience.hint }}</small>
          </label>
        </div>
      </section>

      <section v-else-if="currentStage === 'columns'" class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>平台配置</h3>
            <p class="panel-hint">{{ wizardStepHints.columns }}</p>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <IpSectionAssistPanel
          section="columns"
          section-label="平台配置"
          :templates="ipSectionTemplates.columns"
          :selected-template-key="selectedTemplateKeys.columns"
          :is-generating="generatingSection === 'columns'"
          @update:selected-template-key="selectedTemplateKeys.columns = $event"
          @apply-template="applySectionTemplate('columns')"
          @generate-section="generateSectionContent('columns')"
        />
        <div class="rule-grid">
          <div class="field-block" :class="{ invalid: isFieldMissing('mainPlatforms') }">
            <label for="main-platforms-input">主平台 <span class="required-mark">*</span></label>
            <div class="platform-chip-row" role="group" aria-label="阵地平台快捷按钮">
              <button
                v-for="item in platformOptions"
                :key="`main-${item.key}`"
                type="button"
                class="platform-chip"
                :class="{ active: isPlatformSelected('mainPlatforms', item.key) }"
                @click="togglePlatformField('mainPlatforms', item.key)"
              >{{ item.label }}</button>
            </div>
            <input
              id="main-platforms-input"
              v-model="ipForm.mainPlatforms"
              required
              :placeholder="ipFieldHints.mainPlatforms.placeholder"
              :aria-invalid="isFieldMissing('mainPlatforms')"
            />
            <small class="field-hint">{{ ipFieldHints.mainPlatforms.hint }}</small>
          </div>
          <div class="field-block">
            <label for="secondary-platforms-input">辅助平台</label>
            <div class="platform-chip-row" role="group" aria-label="分发平台快捷按钮">
              <button
                v-for="item in platformOptions"
                :key="`secondary-${item.key}`"
                type="button"
                class="platform-chip"
                :class="{ active: isPlatformSelected('secondaryPlatforms', item.key) }"
                @click="togglePlatformField('secondaryPlatforms', item.key)"
              >{{ item.label }}</button>
            </div>
            <input
              id="secondary-platforms-input"
              v-model="ipForm.secondaryPlatforms"
              :placeholder="ipFieldHints.secondaryPlatforms.placeholder"
            />
            <small class="field-hint">{{ ipFieldHints.secondaryPlatforms.hint }}</small>
          </div>
        </div>
      </section>

      <section v-else class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>内容规则</h3>
            <p class="panel-hint">{{ wizardStepHints.topics }}</p>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <IpSectionAssistPanel
          section="topics"
          section-label="内容规则"
          :templates="ipSectionTemplates.topics"
          :selected-template-key="selectedTemplateKeys.topics"
          :is-generating="generatingSection === 'topics'"
          @update:selected-template-key="selectedTemplateKeys.topics = $event"
          @apply-template="applySectionTemplate('topics')"
          @generate-section="generateSectionContent('topics')"
        />
        <div class="rule-grid">
          <label :class="{ invalid: isFieldMissing('tone') }">
            表达语气 <span class="required-mark">*</span>
            <input v-model="ipForm.tone" required :placeholder="ipFieldHints.tone.placeholder" :aria-invalid="isFieldMissing('tone')" />
            <small class="field-hint">{{ ipFieldHints.tone.hint }}</small>
          </label>
          <label :class="{ invalid: isFieldMissing('visualStyle') }">
            视觉风格 <span class="required-mark">*</span>
            <input v-model="ipForm.visualStyle" required :placeholder="ipFieldHints.visualStyle.placeholder" :aria-invalid="isFieldMissing('visualStyle')" />
            <small class="field-hint">{{ ipFieldHints.visualStyle.hint }}</small>
          </label>
          <label class="full" :class="{ invalid: isFieldMissing('conversionPath') }">
            转化路径 <span class="required-mark">*</span>
            <input v-model="ipForm.conversionPath" required :placeholder="ipFieldHints.conversionPath.placeholder" :aria-invalid="isFieldMissing('conversionPath')" />
            <small class="field-hint">{{ ipFieldHints.conversionPath.hint }}</small>
          </label>
          <label class="full">
            禁用表达
            <textarea v-model="ipForm.forbiddenExpressions" rows="4" :placeholder="ipFieldHints.forbiddenExpressions.placeholder"></textarea>
            <small class="field-hint">{{ ipFieldHints.forbiddenExpressions.hint }}</small>
          </label>
        </div>
      </section>

      <p class="state-line" role="status" aria-live="polite">{{ statusMessage || currentIpName }}</p>

      <footer v-if="isWizardActive && currentWizardStepIndex < wizardStageKeys.length - 1" class="wizard-footer">
        <button v-if="currentWizardStepIndex > 0" class="ghost-pill" @click="goPrevWizardStep">上一步</button>
        <button class="primary-pill" @click="goNextWizardStep">下一步</button>
      </footer>
    </main>

    <aside v-if="isWizardActive" class="wizard-sidebar" aria-label="建档进度">
      <strong>建档进度</strong>
      <ol class="wizard-checklist">
        <li
          v-for="step in workflowSteps"
          :key="step.key"
          :class="{ done: step.done, current: step.current }"
        >
          <button
            type="button"
            class="checklist-step"
            :aria-label="`进度：${step.label} ${step.percent}%`"
            @click="setStage(step.key)"
          >
            <span aria-hidden="true">{{ step.label }}</span>
            <small aria-hidden="true">{{ step.percent }}%</small>
          </button>
        </li>
      </ol>
      <div class="sidebar-tip">
        <small>提示</small>
        <p>每步都有行业模板和「一键生成」。可先自动生成，再按实际情况微调后保存。</p>
      </div>
    </aside>
    </div>
  </div>
</template>

<style scoped>
.sprint-shell {
  width: 100%;
  min-height: 100%;
  overflow: visible;
  padding: 28px;
  background: var(--color-bg-primary);
}

.guest-save-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 0 auto 18px;
  width: min(1240px, 100%);
  padding: 14px 18px;
  border: 1px solid rgba(36, 87, 255, 0.16);
  border-radius: 18px;
  background: rgba(239, 246, 255, 0.92);
}

.guest-save-banner strong {
  display: block;
  margin-bottom: 4px;
  color: #0f172a;
  font-size: 14px;
}

.guest-save-banner span {
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.sprint-hero,
.stage-nav,
.sprint-body,
.ip-guide-panel,
.wizard-focus-bar {
  width: min(1240px, 100%);
  margin: 0 auto;
}

.sprint-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  padding: 0 0 18px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.hero-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.ip-switcher {
  min-width: 220px;
}

.sprint-hero h2,
.form-panel h3 {
  margin: 0;
  color: #111827;
  font-size: clamp(26px, 3vw, 34px);
  font-weight: 900;
  letter-spacing: -0.05em;
}

.hero-lead {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
  max-width: 520px;
}

.ip-guide-panel {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  margin-top: 18px;
  padding: 18px 20px;
  border: 1px solid rgba(37, 99, 235, 0.14);
  border-radius: 20px;
  background: rgba(239, 246, 255, 0.72);
}

.ip-guide-panel.compact {
  background: #fff;
  border-color: rgba(15, 23, 42, 0.08);
}

.guide-copy {
  display: grid;
  gap: 6px;
}

.guide-copy strong {
  color: #0f172a;
  font-size: 16px;
}

.guide-copy p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
  max-width: 640px;
}

.guide-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.wizard-focus-bar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-top: 16px;
  padding: 14px 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.focus-step {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.focus-step small,
.focus-progress span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.focus-step strong,
.focus-progress strong {
  color: #0f172a;
  font-size: 15px;
}

.focus-step span {
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.focus-progress {
  display: grid;
  gap: 4px;
  text-align: right;
}

.focus-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.sprint-body.wizard-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 18px;
  align-items: start;
  margin-top: 18px;
}

.wizard-sidebar {
  position: sticky;
  top: 88px;
  display: grid;
  gap: 12px;
  padding: 16px;
  max-height: calc(100vh - 120px);
  overflow: auto;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.wizard-sidebar strong {
  color: #0f172a;
  font-size: 14px;
}

.wizard-checklist {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.wizard-checklist li.done .checklist-step {
  border-color: rgba(34, 197, 94, 0.28);
  background: rgba(240, 253, 244, 0.8);
  color: #15803d;
}

.wizard-checklist li.current .checklist-step {
  border-color: rgba(37, 99, 235, 0.35);
  background: rgba(239, 246, 255, 0.92);
  color: #1d4ed8;
}

.checklist-step {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 14px;
  background: #fff;
  color: #334155;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  text-align: left;
}

.checklist-step small {
  opacity: 0.72;
}

.sidebar-tip {
  display: grid;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

.sidebar-tip small {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.sidebar-tip p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.panel-hint {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
  max-width: 560px;
}

.wizard-footer {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

.ghost-pill {
  border: 1px solid rgba(17, 24, 39, 0.1);
  padding: 11px 18px;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-normal);
}

.ghost-pill:hover:not(:disabled) {
  border-color: rgba(37, 99, 235, 0.24);
  color: #1d4ed8;
}

.completeness-summary {
  display: grid;
  gap: 7px;
  max-width: 520px;
  margin-top: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.completeness-meter {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.2);
}

.completeness-meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #2457ff;
  transition: width var(--transition-normal);
}

.completeness-summary strong {
  color: #0f172a;
  font-size: 15px;
}

.completeness-summary small,
.next-action-link {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.next-action-link {
  width: fit-content;
  padding: 0;
  border: 0;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
}

.stage-nav {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.stage-tab {
  display: inline-flex;
  align-items: center;
  padding: 9px 14px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 999px;
  background: #fff;
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  font-family: inherit;
  transition: all var(--transition-normal);
  gap: 8px;
}

.stage-tab small {
  color: inherit;
  opacity: 0.72;
  font-size: 11px;
}

.stage-tab:hover {
  border-color: rgba(37, 99, 235, 0.22);
  background: rgba(37, 99, 235, 0.07);
  color: #1d4ed8;
}

.stage-tab.active {
  border-color: rgba(37, 99, 235, 0.35);
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.sprint-body {
  margin-top: 18px;
}

.sprint-main {
  margin-top: 0;
}

.stage-nav {
  margin-top: 18px;
}

.glass-panel {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.dashboard-grid {
  display: grid;
  gap: 10px;
}

.ip-list-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.5fr) minmax(120px, 1fr) 90px 100px;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 16px;
  background: #fff;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: all var(--transition-normal);
}

.ip-list-row:hover {
  border-color: rgba(37, 99, 235, 0.24);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
}

.ip-list-row.active {
  border-color: rgba(37, 99, 235, 0.4);
  background: rgba(239, 246, 255, 0.86);
}

.ip-list-row strong {
  color: #111827;
}

.ip-list-row span,
.ip-list-row small {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.status-pill {
  width: fit-content;
  padding: 4px 9px;
  border-radius: 999px;
}

.status-pill.complete {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.status-pill.incomplete {
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}

.form-panel {
  padding: 22px;
}

.panel-title-row {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.form-grid,
.rule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

label,
.field-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.field-block.invalid label {
  color: #dc2626;
}

.field-hint {
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.5;
}

.platform-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.platform-chip {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 999px;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
}

.platform-chip.active {
  border-color: rgba(36, 87, 255, 0.28);
  background: rgba(36, 87, 255, 0.08);
  color: #1d4ed8;
}

.required-mark {
  color: var(--color-warning);
}

label.invalid {
  color: var(--color-text-secondary);
}

label.invalid input,
label.invalid textarea,
label.invalid select {
  border-color: rgba(217, 119, 6, 0.55);
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.08);
}

input,
textarea,
select {
  width: 100%;
  padding: 11px 13px;
  border: 1px solid rgba(17, 24, 39, 0.1);
  border-radius: 16px;
  outline: none;
  background: #fff;
  color: #111827;
  font: inherit;
  font-weight: 500;
}

textarea {
  resize: vertical;
  line-height: 1.6;
}

input:focus,
textarea:focus,
select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

label.invalid input,
label.invalid textarea,
label.invalid select {
  border-color: rgba(220, 38, 38, 0.5);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.08);
}

.full {
  grid-column: 1 / -1;
}

.primary-pill {
  border: 0;
  padding: 11px 18px;
  border-radius: 999px;
  background: #2457ff;
  color: #fff;
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 14px 34px rgba(37, 99, 235, 0.2);
  transition: all var(--transition-normal);
}

.primary-pill:hover:not(:disabled) {
  background: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 18px 44px rgba(37, 99, 235, 0.26);
}

.primary-pill:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.state-line {
  margin: 16px 0 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
}

.empty-state {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 34px;
  border: 1px dashed rgba(100, 116, 139, 0.28);
  border-radius: 24px;
  background: rgba(248, 250, 252, 0.72);
  text-align: center;
  color: #64748b;
}

.empty-state strong {
  color: #0f172a;
  font-size: 16px;
}

.empty-state span {
  max-width: 420px;
  line-height: 1.7;
}

@media (max-width: 980px) {
  .sprint-shell {
    padding: 18px;
  }

  .sprint-hero,
  .panel-title-row,
  .ip-guide-panel,
  .wizard-focus-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .focus-progress {
    text-align: left;
  }

  .sprint-body.wizard-layout {
    grid-template-columns: 1fr;
  }

  .wizard-sidebar {
    position: static;
    max-height: none;
  }

  .ip-list-row,
  .form-grid,
  .rule-grid {
    grid-template-columns: 1fr;
  }

  .full {
    grid-column: auto;
  }
}
</style>

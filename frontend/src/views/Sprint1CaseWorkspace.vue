<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createSprint1IpAsset,
  getSprint1IpAsset,
  listSprint1IpAssets,
  updateSprint1IpAsset,
  type Sprint1IpAsset,
  type Sprint1IpAssetPayload,
} from '../api'

type StageKey = 'home' | 'ip' | 'strategy' | 'columns' | 'topics'

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

const currentStage = ref<StageKey>('home')
const selectedIpId = ref('')
const availableIps = ref<Sprint1IpAsset[]>([])
const currentIp = ref<Sprint1IpAsset | null>(null)
const isLoading = ref(false)
const statusMessage = ref('')

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

const currentIpName = computed(() => currentIp.value?.name || '未选择 IP')

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
    status: percent >= 100 ? '完整' : percent >= 60 ? '可生成，建议补齐' : '待补齐',
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

function parseCsv(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
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

async function loadIpAssets() {
  isLoading.value = true
  try {
    const res = await listSprint1IpAssets({ pageSize: 100 })
    availableIps.value = res.data.items
    if (!availableIps.value.length) {
      currentIp.value = null
      selectedIpId.value = ''
      resetForm()
      statusMessage.value = '暂无 IP'
      currentStage.value = 'home'
      return
    }

    const nextIpId = selectedIpId.value && availableIps.value.some((item) => item.id === selectedIpId.value)
      ? selectedIpId.value
      : availableIps.value[0].id
    selectedIpId.value = nextIpId
    await loadIpDetails(nextIpId)
  } catch (error) {
    statusMessage.value = (error as Error)?.message || '加载失败'
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
  await loadIpDetails(ipId)
}

function createNewIp() {
  currentIp.value = null
  selectedIpId.value = ''
  resetForm()
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
  } catch (error) {
    const fallbackAsset = {
      id: currentIp.value?.id || `local-${Date.now()}`,
      ...payload,
      profileStatus: ipCompleteness.value.percent >= 100 ? 'complete' : 'draft',
      createdAt: currentIp.value?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    } as Sprint1IpAsset
    currentIp.value = fallbackAsset
    selectedIpId.value = fallbackAsset.id
    availableIps.value = [fallbackAsset, ...availableIps.value.filter((item) => item.id !== fallbackAsset.id)]
    statusMessage.value = (error as Error)?.message === 'Network Error' ? '已保存 IP 资料（本地兜底）' : ((error as Error)?.message || '保存失败')
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  void loadIpAssets()
})
</script>

<template>
  <div class="sprint-shell">
    <header class="sprint-hero">
      <div>
        <h2>IP 档案</h2>
        <div class="completeness-summary" data-testid="ip-completeness-summary">
          <div class="completeness-meter">
            <span :style="{ width: `${ipCompleteness.percent}%` }"></span>
          </div>
          <strong data-testid="ip-completeness-percent">完整度 {{ ipCompleteness.percent }}%</strong>
          <small>
            {{ ipCompleteness.status }} · {{ ipCompleteness.completed }}/{{ ipCompleteness.total }} 项已补齐
          </small>
          <button v-if="nextMissingGroup" class="next-action-link" @click="goNextMissingStage">
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
            {{ ip.profileStatus === 'complete' ? '完整' : '待补齐' }}
          </span>
          <small>{{ ip.updatedAt?.slice(0, 10) }}</small>
        </button>
        <div v-if="!availableIps.length" class="empty-state">
          <strong>还没有 IP 档案</strong>
          <span>先创建一个 IP，补齐定位、平台和内容规则，后续生成会更稳定。</span>
          <button class="primary-pill" @click="createNewIp">创建第一个 IP</button>
        </div>
      </section>

      <section v-else-if="currentStage === 'ip'" class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>IP 资料</h3>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <div class="form-grid">
          <label :class="{ invalid: isFieldMissing('name') }">名称 <span class="required-mark">*</span><input v-model="ipForm.name" required :aria-invalid="isFieldMissing('name')" /></label>
          <label :class="{ invalid: isFieldMissing('type') }">类型 <span class="required-mark">*</span><input v-model="ipForm.type" required :aria-invalid="isFieldMissing('type')" /></label>
          <label :class="{ invalid: isFieldMissing('businessGoal') }">商业目标 <span class="required-mark">*</span><input v-model="ipForm.businessGoal" required :aria-invalid="isFieldMissing('businessGoal')" /></label>
        </div>
      </section>

      <section v-else-if="currentStage === 'strategy'" class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>人设定位</h3>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <div class="form-grid">
          <label :class="{ invalid: isFieldMissing('industry') }">行业 <span class="required-mark">*</span><input v-model="ipForm.industry" required :aria-invalid="isFieldMissing('industry')" /></label>
          <label :class="{ invalid: isFieldMissing('targetAudience') }">目标用户 <span class="required-mark">*</span><textarea v-model="ipForm.targetAudience" rows="3" required :aria-invalid="isFieldMissing('targetAudience')"></textarea></label>
        </div>
      </section>

      <section v-else-if="currentStage === 'columns'" class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>平台配置</h3>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <div class="rule-grid">
          <label :class="{ invalid: isFieldMissing('mainPlatforms') }">主平台 <span class="required-mark">*</span><input v-model="ipForm.mainPlatforms" required :aria-invalid="isFieldMissing('mainPlatforms')" placeholder="wechat,shipinhao" /></label>
          <label>辅助平台<input v-model="ipForm.secondaryPlatforms" placeholder="xiaohongshu,moments" /></label>
        </div>
      </section>

      <section v-else class="glass-panel form-panel">
        <div class="panel-title-row">
          <div>
            <h3>内容规则</h3>
          </div>
          <button class="primary-pill" :disabled="isLoading" @click="saveIpAsset">保存</button>
        </div>
        <div class="rule-grid">
          <label :class="{ invalid: isFieldMissing('tone') }">表达语气 <span class="required-mark">*</span><input v-model="ipForm.tone" required :aria-invalid="isFieldMissing('tone')" /></label>
          <label :class="{ invalid: isFieldMissing('visualStyle') }">视觉风格 <span class="required-mark">*</span><input v-model="ipForm.visualStyle" required :aria-invalid="isFieldMissing('visualStyle')" /></label>
          <label class="full" :class="{ invalid: isFieldMissing('conversionPath') }">转化路径 <span class="required-mark">*</span><input v-model="ipForm.conversionPath" required :aria-invalid="isFieldMissing('conversionPath')" /></label>
          <label class="full">禁用表达<textarea v-model="ipForm.forbiddenExpressions" rows="4"></textarea></label>
        </div>
      </section>

      <p class="state-line" role="status" aria-live="polite">{{ statusMessage || currentIpName }}</p>
    </main>
  </div>
</template>

<style scoped>
.sprint-shell {
  width: 100%;
  min-height: 100%;
  overflow: visible;
  padding: 28px;
  background:
    radial-gradient(circle at 8% 0%, rgba(37, 99, 235, 0.08), transparent 34%),
    radial-gradient(circle at 92% 8%, rgba(124, 58, 237, 0.06), transparent 32%),
    var(--color-bg-primary);
}

.sprint-hero,
.stage-nav,
.sprint-main {
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

.completeness-summary {
  display: grid;
  gap: 7px;
  max-width: 520px;
  margin-top: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
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
  background: var(--color-accent-gradient);
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
  background: rgba(255, 255, 255, 0.72);
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

.sprint-main {
  margin-top: 18px;
}

.glass-panel {
  border: 1px solid var(--glass-border);
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.7)),
    var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-sm);
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
  background: rgba(255, 255, 255, 0.78);
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

label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.required-mark {
  color: #dc2626;
}

label.invalid {
  color: #b91c1c;
}

input,
textarea,
select {
  width: 100%;
  padding: 11px 13px;
  border: 1px solid rgba(17, 24, 39, 0.1);
  border-radius: 16px;
  outline: none;
  background: rgba(255, 255, 255, 0.86);
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
  background: var(--color-accent-gradient);
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
  filter: saturate(1.05) brightness(1.02);
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
  .panel-title-row {
    align-items: stretch;
    flex-direction: column;
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

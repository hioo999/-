<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  buildShortVideoWorkflow,
  listShortVideoIntents,
  listShortVideoProjects,
  saveShortVideoProject,
  type ShortVideoIntentOption,
  type ShortVideoProjectSummary,
  type ShortVideoWorkflowResult,
} from '../api'
import {
  createVideoAipProjectFromShortVideo,
  getVideoAipProject,
  listVideoAipProjects,
  runAllVideoAipSteps,
  runNextVideoAipStep,
  retryVideoAipStep,
  type VideoAipProject,
  type VideoAipStepTask,
} from '../api/videoAip.api'
import { modePathMap } from '../stores/workspace'

type ProductionTrack = 'cinematic' | 'drama'

const props = defineProps<{
  initialProjectId?: number
  initialTopicId?: number
}>()

const router = useRouter()
const activeTrack = ref<ProductionTrack>('cinematic')
const isLoading = ref(false)
const isRunningAip = ref(false)
const feedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const intents = ref<ShortVideoIntentOption[]>([])
const workflow = ref<ShortVideoWorkflowResult | null>(null)
const savedProjects = ref<ShortVideoProjectSummary[]>([])
const savedProjectId = ref(0)
const aipProject = ref<VideoAipProject | null>(null)

const form = reactive({
  title: '未命名短视频项目',
  user_input: '',
  requested_intent: 'auto',
  subject_name: '主体',
  platform: '抖音/视频号',
  aspect_ratio: '9:16',
  duration: '15秒',
  model: '即梦2.0',
  style: '高级、真实、有记忆点',
  target_audience: '目标用户',
  core_message: '核心卖点或核心观点',
})

const trackMeta = computed(() => ({
  cinematic: {
    label: '短大片工厂',
    summary: '产品图、人物图或宠物图进入主体清理、多视图、九宫格分镜和视频任务。',
    placeholder: '例如：一款轻医美护肤精华，需要 15 秒竖屏产品 TVC，突出成分安全和前后对比。',
    suggestedIntents: ['product_tvc', 'pet_vlog', 'ip_character', 'lifestyle'],
  },
  drama: {
    label: '剧本短视频',
    summary: '从角色、痛点和反转剧情出发，拆分镜并进入视频 AIP 出片。',
    placeholder: '例如：客户不信任 AI 工具，最后被效率反转，适合视频号剧情短片。',
    suggestedIntents: ['ip_character', 'knowledge_talk'],
  },
}))

const filteredIntents = computed(() => {
  const keys = trackMeta.value[activeTrack.value].suggestedIntents
  return intents.value.filter((item) => keys.includes(item.key))
})

const workflowSteps = computed(() => workflow.value?.steps || [])
const aipSteps = computed(() => aipProject.value?.steps || [])
const completedAipSteps = computed(() => aipSteps.value.filter((step) => step.status === 'succeeded').length)

function setFeedback(type: 'success' | 'error' | 'info', message: string) {
  feedback.value = { type, message }
}

function getErrorMessage(error: unknown, fallback: string) {
  const payload = (error as { response?: { data?: { detail?: { message?: string } | string } } })?.response?.data?.detail
  if (typeof payload === 'string') return payload
  if (payload && typeof payload === 'object' && payload.message) return payload.message
  return (error as Error)?.message || fallback
}

function formatStepStatus(status: string) {
  const map: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    succeeded: '已完成',
    failed: '失败',
    planned: '已规划',
  }
  return map[status] || status
}

async function loadSupportData() {
  const [intentRes, projectRes, aipRes] = await Promise.all([
    listShortVideoIntents(),
    listShortVideoProjects(20),
    listVideoAipProjects({ limit: 10 }),
  ])
  intents.value = intentRes.data || []
  savedProjects.value = projectRes.data || []
  if (!aipProject.value && aipRes.data?.length) {
    const latest = aipRes.data[0]
    if (latest?.id) await refreshAipProject(latest.id)
  }
}

async function handleBuildWorkflow() {
  if (!form.user_input.trim()) {
    setFeedback('error', '请先描述你想做的短视频内容。')
    return
  }
  isLoading.value = true
  try {
    const res = await buildShortVideoWorkflow({
      user_input: form.user_input.trim(),
      requested_intent: form.requested_intent,
      subject_name: form.subject_name.trim(),
      platform: form.platform.trim(),
      aspect_ratio: form.aspect_ratio.trim(),
      duration: form.duration.trim(),
      model: form.model.trim(),
      style: form.style.trim(),
      target_audience: form.target_audience.trim(),
      core_message: form.core_message.trim(),
    })
    workflow.value = res.data
    if (res.data.intent?.label) {
      form.title = `${res.data.intent.label} · ${form.subject_name || '短视频项目'}`
    }
    setFeedback('success', `已识别为「${res.data.intent?.label || '通用工作流'}」，共 ${res.data.steps?.length || 0} 个步骤。`)
  } catch (error) {
    setFeedback('error', getErrorMessage(error, '生成工作流失败'))
  } finally {
    isLoading.value = false
  }
}

async function handleSaveProject() {
  if (!workflow.value) {
    setFeedback('error', '请先生成工作流。')
    return
  }
  isLoading.value = true
  try {
    const res = await saveShortVideoProject({
      title: form.title.trim() || '未命名短视频项目',
      subject_name: form.subject_name.trim(),
      intent_key: workflow.value.intent?.intent || '',
      intent_label: workflow.value.intent?.label || '',
      confidence: workflow.value.intent?.confidence || 0,
      platform: form.platform.trim(),
      aspect_ratio: form.aspect_ratio.trim(),
      duration: form.duration.trim(),
      model: form.model.trim(),
      style: form.style.trim(),
      target_audience: form.target_audience.trim(),
      core_message: form.core_message.trim(),
      user_input: form.user_input.trim(),
      workflow: workflow.value,
      archive_markdown: workflowSteps.value.map((step) => `## ${step.label}\n\n${step.prompt}`).join('\n\n'),
      notes: props.initialProjectId ? `关联 IP 项目 #${props.initialProjectId}` : '',
    })
    savedProjectId.value = res.data.id
    await loadSupportData()
    setFeedback('success', '短视频项目已归档，可进入视频 AIP 执行。')
  } catch (error) {
    setFeedback('error', getErrorMessage(error, '保存项目失败'))
  } finally {
    isLoading.value = false
  }
}

async function refreshAipProject(projectId: number) {
  const res = await getVideoAipProject(projectId)
  aipProject.value = res.data
}

async function handleCreateAipProject() {
  if (!savedProjectId.value) {
    setFeedback('error', '请先保存短视频项目归档。')
    return
  }
  isLoading.value = true
  try {
    const res = await createVideoAipProjectFromShortVideo(savedProjectId.value, {
      title: form.title.trim(),
      workflow_type: activeTrack.value === 'drama' ? 'drama' : 'product_tvc',
    })
    aipProject.value = res.data
    setFeedback('success', '视频 AIP 项目已创建，可以逐步执行媒体任务。')
  } catch (error) {
    setFeedback('error', getErrorMessage(error, '创建视频 AIP 项目失败'))
  } finally {
    isLoading.value = false
  }
}

async function handleRunNextStep() {
  if (!aipProject.value?.id) return
  isRunningAip.value = true
  try {
    await runNextVideoAipStep(aipProject.value.id)
    await refreshAipProject(aipProject.value.id)
    setFeedback('success', '已提交下一步媒体任务。')
  } catch (error) {
    setFeedback('error', getErrorMessage(error, '执行下一步失败'))
  } finally {
    isRunningAip.value = false
  }
}

async function handleRunAllSteps() {
  if (!aipProject.value?.id) return
  isRunningAip.value = true
  try {
    await runAllVideoAipSteps(aipProject.value.id)
    setFeedback('info', '已启动全流程执行，请稍后刷新查看步骤状态。')
    window.setTimeout(() => {
      if (aipProject.value?.id) void refreshAipProject(aipProject.value.id)
    }, 2500)
  } catch (error) {
    setFeedback('error', getErrorMessage(error, '启动全流程失败'))
  } finally {
    isRunningAip.value = false
  }
}

async function handleRetryStep(step: VideoAipStepTask) {
  if (!aipProject.value?.id) return
  isRunningAip.value = true
  try {
    await retryVideoAipStep(aipProject.value.id, step.id)
    await refreshAipProject(aipProject.value.id)
    setFeedback('success', `已重试步骤「${step.title}」。`)
  } catch (error) {
    setFeedback('error', getErrorMessage(error, '重试步骤失败'))
  } finally {
    isRunningAip.value = false
  }
}

function openReversalTool() {
  router.push(modePathMap.reversal)
}

function openPlatformStudio() {
  router.push(`${modePathMap.ip}?tab=platform`)
}

function applyIntent(intentKey: string) {
  form.requested_intent = intentKey
  const intent = intents.value.find((item) => item.key === intentKey)
  if (intent) form.title = `${intent.label} · ${form.subject_name || '短视频项目'}`
}

onMounted(() => {
  void loadSupportData()
})
</script>

<template>
  <div class="short-video-production">
    <header class="sv-hero">
      <div>
        <span class="section-eyebrow">短视频出片</span>
        <h2>短大片与剧本短视频</h2>
        <p>沿用当前 IP 项目与选题上下文，从工作流规划到视频 AIP 媒体任务一站式推进。</p>
        <p v-if="props.initialProjectId" class="context-line">关联 IP 项目 #{{ props.initialProjectId }}<span v-if="props.initialTopicId"> · 选题 #{{ props.initialTopicId }}</span></p>
      </div>
      <div class="hero-actions">
        <button class="btn btn-ghost" :disabled="isLoading" @click="loadSupportData">刷新</button>
        <button class="btn btn-ghost" @click="openPlatformStudio">去多平台工作台</button>
      </div>
    </header>

    <div v-if="feedback" class="sv-feedback" :class="feedback.type">{{ feedback.message }}</div>

    <section class="sv-card track-picker" aria-label="出片类型">
      <button class="track-card" :class="{ active: activeTrack === 'cinematic' }" type="button" @click="activeTrack = 'cinematic'">
        <span class="track-badge">短大片</span>
        <strong>{{ trackMeta.cinematic.label }}</strong>
        <span>{{ trackMeta.cinematic.summary }}</span>
      </button>
      <button class="track-card" :class="{ active: activeTrack === 'drama' }" type="button" @click="activeTrack = 'drama'">
        <span class="track-badge">剧本</span>
        <strong>{{ trackMeta.drama.label }}</strong>
        <span>{{ trackMeta.drama.summary }}</span>
      </button>
    </section>

    <section v-if="activeTrack === 'drama'" class="sv-card drama-bridge">
      <strong>剧本短视频可先写反转剧脚本</strong>
      <p>在反转剧工具里生成角色和剧情后，再回到这里归档并进入视频 AIP。</p>
      <button class="btn btn-ghost" @click="openReversalTool">打开反转剧编剧</button>
    </section>

    <section class="sv-card short-video-workflow">
      <div class="card-head">
        <div>
          <h3>1. 规划工作流</h3>
          <p>描述你的短视频需求，系统会识别场景并生成可执行步骤。</p>
        </div>
      </div>

      <div class="intent-row" v-if="filteredIntents.length">
        <button
          v-for="intent in filteredIntents"
          :key="intent.key"
          class="intent-chip"
          :class="{ active: form.requested_intent === intent.key }"
          type="button"
          @click="applyIntent(intent.key)"
        >{{ intent.label }}</button>
        <button class="intent-chip" :class="{ active: form.requested_intent === 'auto' }" type="button" @click="form.requested_intent = 'auto'">自动识别</button>
      </div>

      <div class="form-grid">
        <label>项目标题<input v-model="form.title" class="input" /></label>
        <label>主体名称<input v-model="form.subject_name" class="input" placeholder="产品名、IP 名或角色名" /></label>
        <label>目标平台<input v-model="form.platform" class="input" /></label>
        <label>画面比例<input v-model="form.aspect_ratio" class="input" /></label>
        <label>时长<input v-model="form.duration" class="input" /></label>
        <label>视频模型<input v-model="form.model" class="input" /></label>
        <label class="wide">核心表达<input v-model="form.core_message" class="input" /></label>
        <label class="wide">风格基调<input v-model="form.style" class="input" /></label>
        <label class="wide">目标受众<input v-model="form.target_audience" class="input" /></label>
        <label class="wide">需求描述<textarea v-model="form.user_input" class="input textarea" :placeholder="trackMeta[activeTrack].placeholder" rows="4" /></label>
      </div>

      <div class="action-row">
        <button class="btn btn-primary" :disabled="isLoading" @click="handleBuildWorkflow">{{ isLoading ? '生成中...' : '生成工作流' }}</button>
        <button class="btn btn-ghost" :disabled="isLoading || !workflow" @click="handleSaveProject">保存项目归档</button>
      </div>

      <div v-if="workflow" class="workflow-result">
        <div class="workflow-meta">
          <span class="intent-pill" :class="{ unknown: (workflow.intent?.confidence || 0) < 0.45 }">{{ workflow.intent?.label || '未识别' }} · 置信度 {{ Math.round((workflow.intent?.confidence || 0) * 100) }}%</span>
          <span v-if="workflow.workflow?.recommended_command">{{ workflow.workflow.recommended_command }}</span>
        </div>
        <article v-for="(step, index) in workflowSteps" :key="step.key" class="workflow-step-card">
          <div class="workflow-step-head">
            <div>
              <small>步骤 {{ index + 1 }}</small>
              <strong>{{ step.label }}</strong>
              <p>{{ step.description }}</p>
            </div>
          </div>
          <pre class="workflow-prompt">{{ step.prompt }}</pre>
        </article>
      </div>
    </section>

    <section class="sv-card">
      <div class="card-head">
        <div>
          <h3>2. 视频 AIP 执行</h3>
          <p>把归档项目接入视频 AIP，逐步跑主体清理、分镜、图片和视频任务。</p>
        </div>
        <div class="action-row">
          <button class="btn btn-primary" :disabled="isLoading || !savedProjectId" @click="handleCreateAipProject">创建 AIP 项目</button>
          <button class="btn btn-ghost" :disabled="isRunningAip || !aipProject" @click="handleRunNextStep">执行下一步</button>
          <button class="btn btn-ghost" :disabled="isRunningAip || !aipProject" @click="handleRunAllSteps">全流程执行</button>
        </div>
      </div>

      <div v-if="aipProject" class="aip-summary">
        <strong>{{ aipProject.title }}</strong>
        <span>{{ formatStepStatus(aipProject.status) }} · {{ completedAipSteps }}/{{ aipSteps.length }} 步完成</span>
      </div>

      <div v-if="aipSteps.length" class="aip-steps">
        <article v-for="step in aipSteps" :key="step.id" class="workflow-step-card">
          <div class="workflow-step-head">
            <div>
              <small>{{ step.step_key }}</small>
              <strong>{{ step.title }}</strong>
              <p>{{ step.goal }}</p>
              <span class="video-aip-task-meta">{{ formatStepStatus(step.status) }}</span>
            </div>
            <div class="workflow-step-actions">
              <button v-if="step.status === 'failed'" class="btn btn-ghost btn-sm" :disabled="isRunningAip" @click="handleRetryStep(step)">重试</button>
            </div>
          </div>
          <div v-if="step.output?.artifactUrl || step.output?.imageUrl || step.output?.videoUrl" class="video-aip-artifact">
            <img v-if="step.output?.imageUrl || (step.output?.artifactType === 'image' && step.output?.artifactUrl)" :src="step.output.imageUrl || step.output.artifactUrl" alt="步骤产出图" />
            <video v-else-if="step.output?.videoUrl || step.output?.artifactType === 'video'" :src="step.output.videoUrl || step.output.artifactUrl" controls />
            <a v-if="step.output?.artifactUrl" :href="step.output.artifactUrl" target="_blank" rel="noreferrer">查看产出</a>
          </div>
          <p v-if="step.error_message" class="step-error">{{ step.error_message }}</p>
        </article>
      </div>
      <p v-else class="empty-hint">保存项目并创建 AIP 后，步骤状态会显示在这里。</p>
    </section>

    <section v-if="savedProjects.length" class="sv-card">
      <div class="card-head"><div><h3>最近归档</h3><p>可继续从已有短视频项目创建 AIP。</p></div></div>
      <div class="archive-list">
        <button
          v-for="project in savedProjects.slice(0, 6)"
          :key="project.id"
          class="archive-item"
          type="button"
          @click="savedProjectId = project.id; form.title = project.title"
        >
          <strong>{{ project.title }}</strong>
          <span>{{ project.intent_label || project.intent_key }} · {{ project.updated_at?.slice(0, 10) || '未更新' }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.short-video-production {
  display: grid;
  gap: 16px;
}

.sv-hero,
.sv-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
  padding: 20px;
}

.section-eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sv-hero {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.sv-hero h2 {
  margin: 6px 0 8px;
  color: #0f172a;
  font-size: 28px;
  font-weight: 950;
}

.sv-hero p,
.context-line,
.empty-hint {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.context-line {
  margin-top: 8px;
  color: #1d4ed8;
  font-weight: 800;
}

.hero-actions,
.card-head,
.action-row,
.intent-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.card-head {
  justify-content: space-between;
  margin-bottom: 14px;
}

.card-head h3 {
  margin: 0 0 6px;
  color: #0f172a;
  font-size: 18px;
}

.track-picker {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.track-card {
  display: grid;
  gap: 8px;
  padding: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: linear-gradient(180deg, #fff, #f8fafc);
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.track-card.active {
  border-color: rgba(37, 99, 235, 0.42);
  box-shadow: 0 14px 32px rgba(37, 99, 235, 0.1);
  background: linear-gradient(180deg, #f8fbff, #eef4ff);
}

.track-badge {
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 900;
}

.track-card strong {
  font-size: 17px;
}

.track-card span {
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.drama-bridge {
  display: grid;
  gap: 8px;
  background: rgba(239, 246, 255, 0.72);
  border-color: rgba(37, 99, 235, 0.14);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.form-grid .wide {
  grid-column: 1 / -1;
}

label {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
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
}

.textarea {
  min-height: 96px;
  resize: vertical;
  line-height: 1.6;
}

.intent-chip {
  padding: 8px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 999px;
  background: #fff;
  color: #475569;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.intent-chip.active {
  border-color: rgba(37, 99, 235, 0.35);
  background: rgba(239, 246, 255, 0.92);
  color: #1d4ed8;
}

.workflow-result {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.workflow-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  color: #64748b;
  font-size: 13px;
}

.aip-summary {
  display: grid;
  gap: 4px;
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
}

.aip-summary strong {
  color: #0f172a;
}

.aip-summary span {
  color: #64748b;
  font-size: 13px;
}

.aip-steps,
.archive-list {
  display: grid;
  gap: 10px;
}

.archive-item {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  font: inherit;
}

.archive-item span {
  color: #64748b;
  font-size: 12px;
}

.step-error {
  margin: 8px 0 0;
  color: #b91c1c;
  font-size: 12px;
}

.sv-feedback {
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 800;
}

.sv-feedback.success { background: #dcfce7; color: #166534; }
.sv-feedback.error { background: #fee2e2; color: #991b1b; }
.sv-feedback.info { background: #dbeafe; color: #1e40af; }

.btn {
  min-height: 38px;
  padding: 8px 14px;
  border: 0;
  border-radius: 999px;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.btn-primary { background: #2457ff; color: #fff; }
.btn-ghost { border: 1px solid rgba(15, 23, 42, 0.08); background: #fff; color: #0f172a; }
.btn-sm { min-height: 32px; padding: 6px 10px; font-size: 12px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 900px) {
  .sv-hero,
  .card-head,
  .track-picker,
  .form-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

<style>
@import '../styles/copilot-workspace.css';
</style>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import PlatformContentStudio from './PlatformContentStudio.vue'
import TeleprompterPanel from './TeleprompterPanel.vue'
import WechatArticlePublisher from './WechatArticlePublisher.vue'
import {
  parseText,
  parseUrl,
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

type ProductionTab = 'overview' | 'wechat' | 'platform' | 'teleprompter' | 'advanced'
type MaterialInputMode = 'topic' | 'url' | 'text'

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

const activeTab = ref<ProductionTab>('overview')
const selectedProjectId = ref(0)
const selectedTopicId = ref(0)
const isLoading = ref(false)
const isCreatingProject = ref(false)
const isCreatingTopic = ref(false)
const isSavingMaterial = ref(false)
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
const runningTasks = computed(() => tasks.value.filter((task) => ['pending', 'running', 'retrying'].includes(String(task.status || ''))))
const failedTasks = computed(() => tasks.value.filter((task) => String(task.status || '') === 'failed'))
const contentInitialTitle = computed(() => selectedTopic.value?.title || materialForm.title || props.initialTitle || '未命名平台内容')
const contentInitialContent = computed(() => materialForm.extractedContent || materialForm.rawText || materialForm.topic || props.initialContent || '')
const hasActiveWork = computed(() => Boolean(selectedProjectId.value && selectedTopicId.value))

const tabItems: Array<{ key: ProductionTab; label: string; desc: string }> = [
  { key: 'overview', label: '选题总览', desc: '项目、选题、素材、任务、资产统一看板' },
  { key: 'wechat', label: '公众号闭环', desc: '文章生成、排版、封面、草稿箱' },
  { key: 'platform', label: '小红书/口播', desc: '小红书图文、抖音/视频号口播' },
  { key: 'teleprompter', label: '提词器', desc: '把口播稿带入录制或直播' },
  { key: 'advanced', label: '高级视频', desc: '短大片和剧本短视频入口预留' },
]

const statusCards = computed(() => [
  { label: '当前项目', value: selectedProject.value?.name || '未选择', hint: selectedProject.value?.ipType || '先选择或创建 IP 项目' },
  { label: '当前选题', value: selectedTopic.value?.title || '未选择', hint: selectedTopic.value?.status || '选题承载跨平台内容' },
  { label: '平台内容', value: String(platformContents.value.length), hint: '公众号、小红书、口播等内容' },
  { label: '任务状态', value: `${runningTasks.value.length} 运行 / ${failedTasks.value.length} 失败`, hint: '生成、图片、发布任务统一追踪' },
  { label: '资产沉淀', value: String(assets.value.length), hint: '素材、文案、图片、视频和发布记录' },
])

watch(selectedProjectId, async () => {
  selectedTopicId.value = 0
  await Promise.all([loadTopics(), refreshContextData()])
})

watch(selectedTopicId, async () => {
  await refreshContextData()
})

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
  } catch (err: any) {
    setFeedback('error', getErrorMessage(err, '生产上下文刷新失败'))
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

function activate(tab: ProductionTab) {
  activeTab.value = tab
  if (tab !== 'overview') void refreshContextData()
}
</script>

<template>
  <div class="production-center-shell">
    <header class="production-hero">
      <div class="hero-copy">
        <span class="section-eyebrow">Production Center</span>
        <h1>生产中心</h1>
        <p>围绕一个 IP 项目和一个内容选题，统一组织素材、平台内容、任务、资产和发布记录。</p>
      </div>
      <div class="hero-actions">
        <span v-if="runningTasks.length" class="production-chip active">{{ runningTasks.length }} 个任务运行中</span>
        <span v-if="failedTasks.length" class="production-chip danger">{{ failedTasks.length }} 个任务失败</span>
        <button class="btn btn-ghost" :disabled="isLoading" @click="loadInitialData">{{ isLoading ? '刷新中...' : '刷新生产上下文' }}</button>
      </div>
    </header>

    <div v-if="feedback" class="production-feedback" :class="feedback.type">{{ feedback.message }}</div>

    <section class="production-status-grid" aria-label="生产上下文概览">
      <article v-for="card in statusCards" :key="card.label" class="production-status-card">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </article>
    </section>

    <section class="production-context-grid">
      <article class="production-card context-card">
        <div class="card-head compact">
          <div>
            <h3>IP 项目</h3>
            <p>生产中心的第一层归属，所有选题、内容和资产都挂在项目下。</p>
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
            <p>选题是一次生产任务的业务容器，后续平台内容都归属到这里。</p>
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
            <p>主题、链接和原文先沉淀为当前选题素材，再供公众号、小红书和口播生成复用。</p>
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
              <span class="section-eyebrow">Topic Overview</span>
              <h2>{{ selectedTopic?.title || '等待选择内容选题' }}</h2>
              <p>{{ hasActiveWork ? '当前选题下的平台内容、任务、资产和发布记录会在这里汇总。' : '先选择或创建 IP 项目与内容选题，再开始生产。' }}</p>
            </div>
            <div class="card-actions">
              <button class="btn btn-primary" :disabled="!hasActiveWork" @click="activeTab = 'wechat'">进入公众号闭环</button>
              <button class="btn btn-ghost" :disabled="!hasActiveWork" @click="activeTab = 'platform'">生成小红书/口播</button>
            </div>
          </div>
          <div class="overview-columns">
            <article>
              <h3>平台内容</h3>
              <p v-if="!platformContents.length">当前选题暂无平台内容。</p>
              <button v-for="content in platformContents.slice(0, 8)" :key="content.contentId" class="overview-list-item" @click="activeTab = content.platform === 'wechat' ? 'wechat' : 'platform'">
                <strong>{{ content.title || '未命名内容' }}</strong>
                <span>{{ content.platform }} · {{ content.contentType }} · {{ content.status }}</span>
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
        />

        <TeleprompterPanel
          v-else-if="activeTab === 'teleprompter'"
          :initial-text="contentInitialContent"
          :current-user="teleprompterUser"
        />

        <section v-else class="production-card advanced-panel">
          <span class="section-eyebrow">Advanced Video</span>
          <h2>高级视频生产入口</h2>
          <p>短大片和剧本短视频后续会以当前项目和选题为上下文，统一写入任务中心和资产库。</p>
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
          <div class="side-head"><strong>任务中心</strong><button class="mini-link" @click="refreshContextData">刷新</button></div>
          <p v-if="!tasks.length">暂无任务。</p>
          <article v-for="task in tasks.slice(0, 8)" :key="task.taskId" class="compact-item task-item">
            <span>{{ task.taskType || 'task' }}</span>
            <strong>{{ task.status }} · {{ task.progress || 0 }}%</strong>
            <small>{{ task.errorMessage || task.error || '无错误' }}</small>
            <button v-if="task.status === 'failed'" class="mini-link danger" :disabled="isRetryingTaskId === task.taskId" @click="handleRetryTask(task)">重试</button>
          </article>
        </section>

        <section class="production-card side-card">
          <div class="side-head"><strong>资产库</strong><button class="mini-link" @click="refreshContextData">刷新</button></div>
          <p v-if="!assets.length">暂无资产。</p>
          <article v-for="asset in assets.slice(0, 8)" :key="asset.assetId" class="compact-item asset-item">
            <span>{{ asset.assetType }} · {{ asset.sourceType }}</span>
            <strong>{{ asset.title || asset.url || asset.assetId }}</strong>
            <button class="mini-link" @click="openAsset(asset)">查看</button>
          </article>
        </section>

        <section class="production-card side-card">
          <div class="side-head"><strong>生成记录</strong><button class="mini-link" @click="refreshContextData">刷新</button></div>
          <p v-if="!generationRecords.length">暂无生成记录。</p>
          <article v-for="record in generationRecords.slice(0, 6)" :key="record.recordId" class="compact-item">
            <span>{{ record.parseStatus || 'record' }} · {{ record.createdAt?.slice(0, 16) }}</span>
            <strong>{{ record.promptSnapshot?.templateKey || record.promptSnapshot?.name || record.modelSnapshot?.name || '生成记录' }}</strong>
            <small>{{ record.modelSnapshot?.provider || record.modelSnapshot?.model_id || record.modelSnapshot?.modelId || '模型快照待补充' }}</small>
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
  border: 1px solid rgba(29, 29, 31, 0.08);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: var(--shadow-sm);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
}

.production-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 24px;
  border-radius: 28px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(239, 246, 255, 0.82)),
    radial-gradient(circle at 90% 10%, rgba(124, 58, 237, 0.16), transparent 30%);
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
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.production-status-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 116px;
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
  color: #111827;
  font-size: 20px;
  letter-spacing: -0.5px;
}

.production-context-grid {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(320px, 1.15fr);
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
  background: #111827;
  color: #fff;
  box-shadow: var(--shadow-md);
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
  color: #111827;
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
  .card-head {
    flex-direction: column;
  }

  .mini-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

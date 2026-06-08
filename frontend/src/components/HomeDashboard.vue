<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDashboardOverview, type DashboardOverview } from '../api/dashboard.api'
import { useAuthStore } from '../stores/auth'
import { modePathMap } from '../stores/workspace'
import type { ToolKey } from '../stores/workspace'

const props = defineProps<{
  isGuestUser?: boolean
}>()

const emit = defineEmits<{
  navigate: [path: string]
  requestLogin: [path?: string | null]
}>()

const loading = ref(true)
const overview = ref<DashboardOverview | null>(null)
const loadError = ref('')

const productionPath = [
  { step: '1', label: '建立 IP 档案', desc: '定位、受众与平台策略' },
  { step: '2', label: '输入素材', desc: '主题、链接或原文' },
  { step: '3', label: '生成内容', desc: '口播、长文或直播话术' },
  { step: '4', label: '交付发布', desc: '提词、草稿箱或出片' },
]

const actionPathMap: Record<ToolKey, string> = {
  ip: modePathMap.ip,
  sprint1: modePathMap.sprint1,
  platform: `${modePathMap.ip}?tab=platform`,
  reversal: modePathMap.reversal,
  teleprompter: modePathMap.teleprompter,
  wechat: `${modePathMap.ip}?tab=wechat`,
  models: modePathMap.models,
  prompts: modePathMap.prompts,
}

const authStore = useAuthStore()

onMounted(async () => {
  if (props.isGuestUser || authStore.isGuestUser) {
    loading.value = false
    return
  }
  try {
    const res = await getDashboardOverview()
    overview.value = res.data
  } catch {
    loadError.value = '概览数据加载失败，你仍可开始生产。'
  } finally {
    loading.value = false
  }
})

function openAction(actionKey: ToolKey) {
  emit('navigate', actionPathMap[actionKey] || modePathMap.ip)
}

function openProtectedPath(path: string) {
  if (props.isGuestUser) {
    emit('requestLogin', path)
    return
  }
  emit('navigate', path)
}

function formatPercent(value: number) {
  return `${Math.round(value)}%`
}
</script>

<template>
  <section class="home-dashboard" data-testid="home-dashboard" aria-label="工作台概览">
    <div v-if="isGuestUser" class="guest-banner" role="note">
      <div>
        <strong>当前为试用模式</strong>
        <span>提词器可直接使用；新建 IP、生产中心、公众号等功能需登录后开启。</span>
      </div>
      <button class="btn btn-primary btn-sm" type="button" @click="emit('requestLogin', modePathMap.sprint1)">登录 / 注册</button>
    </div>

    <div class="home-hero-grid">
      <header class="home-hero">
        <span class="section-eyebrow">IP 全案工作台</span>
        <h1>今天要推进什么？</h1>
        <p>从生产中心选一项交付目标，系统会告诉你下一步该做什么。</p>
        <div class="hero-actions">
          <button class="btn btn-primary btn-lg" @click="openProtectedPath(modePathMap.ip)">开始生产</button>
          <button class="btn btn-ghost btn-lg" @click="openProtectedPath(modePathMap.sprint1)">新建 IP 档案</button>
        </div>
      </header>

      <aside class="home-side-panel" aria-label="今日概览">
        <article class="metric-card">
          <span>IP 完整度</span>
          <strong>{{ overview ? formatPercent(overview.ipCompleteness.value) : '—' }}</strong>
          <small v-if="overview?.ipCompleteness.missingItems.length">
            还可完善：{{ overview.ipCompleteness.missingItems.slice(0, 2).join('、') }}
          </small>
          <small v-else>档案信息较完整</small>
        </article>
        <article class="metric-card">
          <span>任务状态</span>
          <strong>{{ overview ? `${overview.taskSummary.running} 进行中` : '—' }}</strong>
          <small>{{ overview ? `${overview.taskSummary.failed} 需关注 / ${overview.taskSummary.pendingPublish} 待发布` : '加载中' }}</small>
        </article>
        <article class="metric-card">
          <span>内容资产</span>
          <strong>{{ overview?.assetSummary.total ?? '—' }}</strong>
          <small>{{ overview ? `${overview.assetSummary.scripts} 文稿 / ${overview.assetSummary.images} 图片` : '加载中' }}</small>
        </article>
      </aside>
    </div>

    <p v-if="loadError" class="home-hint error">{{ loadError }}</p>

    <section class="home-section" aria-label="继续推进">
      <div class="section-head">
        <h2>继续推进</h2>
        <span v-if="loading" class="section-meta">加载中...</span>
        <span v-else class="section-meta">最多显示 3 项优先事项</span>
      </div>
      <div v-if="overview?.todayActions.length" class="action-list">
        <article
          v-for="(action, index) in overview.todayActions.slice(0, 3)"
          :key="`${action.title}-${index}`"
          class="action-card"
        >
          <div>
            <span class="action-status">{{ action.status }}</span>
            <strong>{{ action.title }}</strong>
            <small>{{ action.owner }}</small>
          </div>
          <button class="btn btn-ghost btn-sm" @click="openAction(action.actionKey)">{{ action.action }}</button>
        </article>
      </div>
      <div v-else class="action-empty">
        <strong>还没有待办记录</strong>
        <span>点击「开始生产」，选择今天要交付的内容类型。</span>
      </div>
    </section>

    <section class="home-section" aria-label="标准生产路径">
      <div class="section-head">
        <h2>标准生产路径</h2>
        <span class="section-meta">四步完成一次内容交付</span>
      </div>
      <div class="path-grid">
        <article v-for="item in productionPath" :key="item.step" class="path-card">
          <i>{{ item.step }}</i>
          <strong>{{ item.label }}</strong>
          <span>{{ item.desc }}</span>
        </article>
      </div>
    </section>

    <section class="home-section" aria-label="常用工具">
      <div class="section-head">
        <h2>常用工具</h2>
        <span class="section-meta">需要直达时可从这里进入</span>
      </div>
      <div class="tool-grid">
        <button class="tool-card primary" @click="openProtectedPath(modePathMap.ip)">
          <strong>生产中心</strong>
          <span>任务化引导，统一组织项目与选题</span>
        </button>
        <button class="tool-card" @click="openProtectedPath(`${modePathMap.ip}?tab=wechat`)">
          <strong>写公众号文章</strong>
          <span>排版预览与草稿箱发布</span>
        </button>
        <button class="tool-card" @click="emit('navigate', modePathMap.teleprompter)">
          <strong>提词器</strong>
          <span>直播台本生成与在线播放</span>
        </button>
        <button class="tool-card" @click="openProtectedPath(modePathMap.sprint1)">
          <strong>IP 档案</strong>
          <span>人设定位与平台策略</span>
        </button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.home-dashboard {
  display: grid;
  gap: 28px;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
}

.home-hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.8fr);
  gap: 18px;
  align-items: stretch;
}

.home-hero {
  display: grid;
  gap: 14px;
  padding: 32px;
  border: 1px solid var(--color-border);
  border-radius: 28px;
  background:
    radial-gradient(circle at 92% 0%, rgba(36, 87, 255, 0.1), transparent 34%),
    linear-gradient(135deg, #fff 0%, #fff 58%, #f5f7ff 100%);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.045);
}

.home-hero h1 {
  margin: 0;
  color: #0b0f1a;
  font-family: var(--font-display);
  font-size: clamp(32px, 4.5vw, 48px);
  font-weight: 820;
  letter-spacing: -0.06em;
  line-height: 1.05;
}

.home-hero p {
  margin: 0;
  max-width: 560px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}

.home-side-panel {
  display: grid;
  gap: 12px;
}

.metric-card {
  display: grid;
  gap: 4px;
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.metric-card span,
.metric-card small,
.section-meta,
.action-card small,
.path-card span,
.tool-card span {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.metric-card strong {
  color: var(--color-text-primary);
  font-size: 22px;
  letter-spacing: -0.5px;
}

.home-section {
  display: grid;
  gap: 14px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.section-head h2 {
  margin: 0;
  font-size: 20px;
  letter-spacing: -0.4px;
}

.home-hint.error {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(217, 119, 6, 0.08);
  color: #b45309;
  font-weight: 700;
}

.guest-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid rgba(36, 87, 255, 0.16);
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.95), #fff);
}

.guest-banner strong {
  display: block;
  margin-bottom: 4px;
  color: var(--color-text-primary);
  font-size: 15px;
}

.guest-banner span {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.action-list,
.path-grid,
.tool-grid {
  display: grid;
  gap: 12px;
}

.action-list {
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.action-card,
.path-card,
.tool-card {
  border: 1px solid var(--color-border);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.action-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
}

.action-card strong,
.path-card strong,
.tool-card strong {
  display: block;
  margin-top: 4px;
  color: var(--color-text-primary);
  font-size: 16px;
}

.action-status {
  display: inline-flex;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 800;
}

.action-empty {
  display: grid;
  gap: 6px;
  padding: 22px;
  border: 1px dashed var(--color-border);
  border-radius: 22px;
  background: #fafbff;
  color: var(--color-text-secondary);
}

.path-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.path-card {
  display: grid;
  gap: 6px;
  padding: 18px;
}

.path-card i {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 999px;
  background: #eef3ff;
  color: #1d4ed8;
  font-style: normal;
  font-size: 12px;
  font-weight: 800;
}

.tool-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.tool-card {
  display: grid;
  gap: 6px;
  padding: 18px;
  text-align: left;
  cursor: pointer;
  font: inherit;
  transition: transform var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal);
}

.tool-card:hover {
  transform: translateY(-2px);
  border-color: #cbd8ff;
  box-shadow: 0 18px 40px rgba(36, 87, 255, 0.08);
}

.tool-card.primary {
  border-color: rgba(36, 87, 255, 0.22);
  background: linear-gradient(135deg, #2457ff, #1d4ed8);
  color: #fff;
}

.tool-card.primary span {
  color: rgba(255, 255, 255, 0.82);
}

@media (max-width: 960px) {
  .home-hero-grid,
  .path-grid,
  .tool-grid {
    grid-template-columns: 1fr;
  }

  .path-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tool-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .home-hero {
    padding: 22px;
  }

  .path-grid,
  .tool-grid {
    grid-template-columns: 1fr;
  }
}
</style>

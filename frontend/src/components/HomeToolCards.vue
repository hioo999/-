<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardOverview } from '../api/dashboard.api'

export type ToolKey = 'ip' | 'sprint1' | 'platform' | 'reversal' | 'teleprompter' | 'wechat' | 'models' | 'prompts'

interface DashboardMetric {
  label: string
  value: string
  hint: string
  state?: 'done' | 'active' | 'pending' | 'warning'
}

interface DashboardTask {
  title: string
  status: string
  owner: string
  action: string
  actionKey: ToolKey
}

interface QuickStartItem {
  label: string
  description: string
  key: ToolKey
  group: 'start' | 'produce' | 'publish' | 'system'
}

const emit = defineEmits<{
  select: [key: ToolKey]
}>()

const props = defineProps<{
  dashboard?: DashboardOverview | null
  loading?: boolean
  error?: string
}>()

const fallbackHeroStats = [
  { label: '生产闭环', value: '4 步' },
  { label: '可续写资产', value: '64 件' },
  { label: '今日优先级', value: '补档案' },
]

const fallbackMetrics: DashboardMetric[] = [
  { label: 'IP 档案完整度', value: '72%', hint: '还差平台策略、内容规则、转化路径', state: 'warning' },
  { label: '内容资产', value: '18', hint: '选题、脚本、提示词、发布包统一沉淀', state: 'active' },
  { label: '待发布包', value: '4', hint: '已生成，待质检和导出', state: 'pending' },
  { label: '今日继续', value: '3', hint: '最近 IP、短视频项目和提词稿', state: 'done' },
]

const fallbackTasks: DashboardTask[] = [
  { title: '补齐 IP 档案', status: '下一步', owner: '人设定位/平台配置', action: '去完善', actionKey: 'sprint1' },
  { title: '创建内容选题并输入素材', status: '可开始', owner: 'IP 项目/选题/素材', action: '去生产中心', actionKey: 'ip' },
  { title: '打通公众号草稿闭环', status: '本期主线', owner: '文章/封面/草稿箱', action: '去生产中心', actionKey: 'ip' },
  { title: '进入多平台兼容工作台', status: '兼容入口', owner: '小红书/抖音/视频号', action: '去工作台', actionKey: 'platform' },
  { title: '排版公众号草稿', status: '可发布', owner: 'Markdown 排版/草稿箱', action: '去排版', actionKey: 'wechat' },
]

const fallbackAssetStatuses = [
  { label: 'IP 档案', value: '6', hint: '2 个待补齐' },
  { label: '素材', value: '24', hint: '图片/视频/文档' },
  { label: '脚本', value: '11', hint: '3 个可发送提词器' },
  { label: '发布包', value: '5', hint: '2 个待质检' },
  { label: '公众号草稿', value: '0', hint: '待绑定公众号' },
]

const heroStats = computed(() => {
  if (!props.dashboard) return fallbackHeroStats
  return [
    { label: '生产闭环', value: '4 步' },
    { label: '可续写资产', value: `${props.dashboard.assetSummary.total} 件` },
    { label: '待处理任务', value: `${props.dashboard.taskSummary.failed} 个` },
  ]
})

const metrics = computed<DashboardMetric[]>(() => {
  if (!props.dashboard) return fallbackMetrics
  const missing = props.dashboard.ipCompleteness.missingItems
  return [
    {
      label: 'IP 档案完整度',
      value: `${props.dashboard.ipCompleteness.value}%`,
      hint: missing.length ? `还差${missing.join('、')}` : '已具备基础生产条件',
      state: props.dashboard.ipCompleteness.value >= 80 ? 'done' : 'warning',
    },
    { label: '内容资产', value: String(props.dashboard.assetSummary.total), hint: '脚本、图片、发布包统一沉淀', state: 'active' },
    { label: '待发布包', value: String(props.dashboard.taskSummary.pendingPublish), hint: '已生成，待质检和发布', state: 'pending' },
    { label: '今日继续', value: String(props.dashboard.todayActions.length), hint: '最近项目、任务和提词稿', state: 'done' },
  ]
})

const tasks = computed<DashboardTask[]>(() => {
  if (!props.dashboard?.todayActions.length) return fallbackTasks
  return props.dashboard.todayActions
})

const visibleTasks = computed(() => tasks.value.slice(0, 3))

const assetStatuses = computed(() => {
  if (!props.dashboard) return fallbackAssetStatuses
  return [
    { label: 'IP 档案', value: String(props.dashboard.ipCompleteness.value), hint: '完整度评分' },
    { label: '图片资产', value: String(props.dashboard.assetSummary.images), hint: '封面/插图/素材图' },
    { label: '脚本资产', value: String(props.dashboard.assetSummary.scripts), hint: '口播稿和平台文案' },
    { label: '发布包', value: String(props.dashboard.assetSummary.publishPackages), hint: '可导出或待质检' },
    { label: '任务失败', value: String(props.dashboard.taskSummary.failed), hint: '需要重试或处理' },
  ]
})

const pathSteps = [
  { title: '建 IP 档案', detail: '定位 / 受众 / 栏目' },
  { title: '输入素材', detail: '图片 / 链接 / 文档' },
  { title: '生成内容', detail: '脚本 / 分镜 / 提示词' },
  { title: '质检发布', detail: '排版 / 导出 / 归档' },
]

const quickStarts: QuickStartItem[] = [
  { label: '新建 IP', description: '先建立人设、平台和内容规则', key: 'sprint1', group: 'start' },
  { label: '生产中心', description: '按项目和选题组织素材、内容、任务和资产', key: 'ip', group: 'produce' },
  { label: '公众号闭环', description: '在生产中心生成文章、封面并发送草稿箱', key: 'ip', group: 'produce' },
  { label: '多平台工作台', description: '兼容入口：查看平台内容、任务和保留策略', key: 'platform', group: 'produce' },
  { label: '在线提词器', description: '把脚本带到直播和口播录制', key: 'teleprompter', group: 'publish' },
  { label: '公众号排版', description: '排版图文并发送到公众号草稿箱', key: 'wechat', group: 'publish' },
  { label: '模型中转', description: '配置 API Key、同步可用模型、设置默认模型', key: 'models', group: 'system' },
]

const coreActions = quickStarts.filter((item) => ['sprint1', 'ip', 'teleprompter', 'wechat'].includes(item.key))

const quickStartGroupLabel: Record<QuickStartItem['group'], string> = {
  start: '建档',
  produce: '生产',
  publish: '发布',
  system: '系统',
}
</script>

<template>
  <div class="home-tools">
    <section class="dashboard-hero" data-testid="home-dashboard">
      <div class="hero-copy">
        <span class="section-eyebrow">AI IP Studio / Today</span>
        <h1>今天的智能生产中枢</h1>
        <h2>把 IP 内容生产，变成一条可执行的智能流水线。</h2>
        <p>从人设定位、素材输入、脚本分镜到公众号草稿和发布包归档，用一个深色指挥舱串起完整生产链路。</p>
        <div class="hero-actions">
          <button class="cta-btn" @click="emit('select', 'sprint1')">新建 IP</button>
          <button class="secondary-btn" @click="emit('select', 'ip')">进入生产中心</button>
        </div>
      </div>

      <aside class="hero-brief" aria-label="今日生产建议">
        <span>下一步建议</span>
        <strong>{{ loading ? '正在同步今天的生产状态...' : '先补齐平台策略，再生成首条口播脚本。' }}</strong>
        <small v-if="error" class="dashboard-inline-error">使用本地默认看板，后端恢复后可刷新。</small>
        <div class="progress-track" aria-hidden="true"><i /></div>
        <div class="hero-stat-row">
          <article v-for="stat in heroStats" :key="stat.label">
            <small>{{ stat.label }}</small>
            <b>{{ stat.value }}</b>
          </article>
        </div>
      </aside>
    </section>

    <section class="sub-tabs" aria-label="首页信息分区">
      <span>当前视图</span>
      <b v-for="tab in tabs" :key="tab" :class="{ active: tab === '总览' }">{{ tab }}</b>
    </section>

    <section class="section-head">
      <div>
        <span class="section-kicker">Quick Start</span>
        <h3>四个核心动作优先展示，让生产路径一眼可执行。</h3>
      </div>
      <p>减少菜单感，把建档、生产、发布和系统配置变成清晰的工作流入口。</p>
    </section>

    <section class="quick-start-grid" aria-label="快捷开工入口">
      <button
        v-for="(item, index) in quickStarts"
        :key="item.label"
        class="quick-start-card"
        :class="`group-${item.group}`"
        :aria-label="item.key === 'teleprompter' ? '打开提词器功能' : undefined"
        @click="emit('select', item.key)"
      >
        <small>{{ quickStartGroupLabel[item.group] }}</small>
        <strong>{{ item.label }}</strong>
        <span>{{ item.description }}</span>
        <i aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</i>
      </button>
    </section>

    <section class="section-head compact">
      <div>
        <span class="section-kicker">Operating Signals</span>
        <h3>今天的生产健康度</h3>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card" :class="metric.state" :data-testid="metric.label === 'IP 档案完整度' ? 'home-ip-completeness' : undefined">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.hint }}</small>
      </article>
    </section>

    <section class="workbench-grid">
      <div class="task-panel glass-panel" data-testid="home-task-list">
        <header>
          <h3>今日继续</h3>
          <button @click="emit('select', 'ip')">进入工作台</button>
        </header>
        <div class="task-list">
          <article v-for="task in tasks" :key="task.title">
            <div>
              <strong>{{ task.title }}</strong>
              <small>{{ task.owner }}</small>
            </div>
            <span>{{ task.status }}</span>
            <button class="task-action" @click="emit('select', task.actionKey)">{{ task.action }}</button>
          </article>
        </div>
      </div>

      <div class="task-panel glass-panel asset-panel">
        <header>
          <h3>资产状态</h3>
          <button @click="emit('select', 'models')">模型中转</button>
        </header>
        <div class="asset-list">
          <article v-for="asset in assetStatuses" :key="asset.label">
            <span>{{ asset.label }}</span>
            <strong>{{ asset.value }}</strong>
            <small>{{ asset.hint }}</small>
          </article>
        </div>
      </div>
    </section>

    <section class="path-panel glass-panel">
      <header>
        <h3>标准生产路径</h3>
        <button @click="emit('select', 'ip')">开始执行</button>
      </header>
      <div class="path-steps">
        <article v-for="(step, index) in pathSteps" :key="step.title">
          <i>{{ index + 1 }}</i>
          <span>{{ step.title }}</span>
          <small>{{ step.detail }}</small>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-tools {
  --home-ink: #f8fafc;
  --home-muted: #cbd5e1;
  --home-soft: #94a3b8;
  --home-line: rgba(148, 163, 184, 0.16);
  --home-surface: rgba(15, 23, 42, 0.66);
  --home-surface-strong: rgba(15, 23, 42, 0.78);
  --home-accent: #7c3aed;
  --home-accent-dark: #22d3ee;
  --home-warm: #fbbf24;
  --home-green: #22c55e;
  display: grid;
  gap: 28px;
  width: 100%;
  max-width: 1380px;
  min-height: 100%;
  margin: 0 auto;
  overflow: visible;
  padding: 42px;
  background:
    radial-gradient(circle at 82% 0%, rgba(34, 211, 238, 0.16), transparent 28%),
    radial-gradient(circle at 16% 4%, rgba(124, 58, 237, 0.22), transparent 30%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.64), rgba(6, 10, 26, 0.92) 58%, rgba(11, 16, 38, 0.9));
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 36px;
}

.glass-panel {
  border: 1px solid var(--home-line);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(30, 41, 59, 0.78), rgba(15, 23, 42, 0.58)),
    var(--home-surface);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
}

.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-top: 2px;
}

.section-head.compact {
  margin-top: 4px;
}

.section-kicker {
  color: var(--home-accent-dark);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.section-head h3 {
  max-width: 720px;
  margin: 5px 0 0;
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: clamp(22px, 2.4vw, 32px);
  font-weight: 950;
  letter-spacing: -0.055em;
  line-height: 1.05;
}

.section-head p {
  max-width: 360px;
  margin: 0;
  color: var(--home-muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.65;
}

.dashboard-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.22fr) minmax(340px, 0.78fr);
  gap: 30px;
  align-items: stretch;
  min-height: 430px;
  padding: 42px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 36px;
  background:
    radial-gradient(circle at 74% 18%, rgba(34, 211, 238, 0.22), transparent 26%),
    radial-gradient(circle at 18% 12%, rgba(124, 58, 237, 0.38), transparent 34%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(6, 10, 26, 0.95) 56%, rgba(17, 24, 39, 0.98)),
    #060a1a;
  box-shadow: 0 34px 100px rgba(0, 0, 0, 0.34), 0 0 0 1px rgba(124, 58, 237, 0.08);
}

.dashboard-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(148, 163, 184, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.045) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.82), transparent 72%);
}

.dashboard-hero::after {
  content: '';
  position: absolute;
  inset: auto -14% -44% 30%;
  height: 300px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(124, 58, 237, 0.22), rgba(34, 211, 238, 0.16));
  filter: blur(2px);
  transform: rotate(-7deg);
}

.hero-copy,
.hero-brief {
  position: relative;
  z-index: 1;
}

.hero-copy {
  display: flex;
  max-width: 790px;
  flex-direction: column;
  justify-content: space-between;
  gap: 30px;
}

.section-eyebrow {
  color: rgba(165, 243, 252, 0.92);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.dashboard-hero h1 {
  margin: 0;
  color: rgba(203, 213, 225, 0.9);
  font-size: 18px;
  font-weight: 850;
  letter-spacing: -0.02em;
}

.dashboard-hero h2 {
  max-width: 18ch;
  margin: 10px 0 16px;
  color: #fff;
  font-family: var(--font-display);
  font-size: clamp(44px, 5.7vw, 78px);
  font-weight: 900;
  letter-spacing: -0.06em;
  line-height: 1;
}

.dashboard-hero p {
  max-width: 66ch;
  margin: 0;
  color: rgba(203, 213, 225, 0.84);
  font-size: 16px;
  line-height: 1.85;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.hero-brief {
  display: grid;
  align-content: space-between;
  gap: 22px;
  min-height: 100%;
  padding: 26px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 28px;
  background: rgba(15, 23, 42, 0.58);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 20px 70px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
}

.hero-brief > span {
  color: rgba(165, 243, 252, 0.78);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-brief > strong {
  color: #f8fafc;
  font-size: 26px;
  font-family: var(--font-display);
  font-weight: 900;
  letter-spacing: -0.04em;
  line-height: 1.18;
}

.dashboard-inline-error {
  color: #fde68a;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.5;
}

.progress-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.16);
}

.progress-track i {
  display: block;
  width: 72%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7c3aed, #6366f1 52%, #22d3ee);
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.32);
}

.hero-stat-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.hero-stat-row article {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.48);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.hero-stat-row small {
  color: rgba(226, 232, 240, 0.68);
  font-size: 11px;
  font-weight: 800;
}

.hero-stat-row b {
  color: #fff;
  font-size: 15px;
  font-weight: 950;
}

.cta-btn,
.task-panel button,
.quick-start-card,
.secondary-btn,
.path-panel button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.cta-btn,
.secondary-btn,
.task-panel button,
.path-panel button {
  min-height: 44px;
  padding: 12px 20px;
  border-radius: 999px;
  background: linear-gradient(135deg, #7c3aed, #6366f1 58%, #22d3ee);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  transition: transform var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal), border-color var(--transition-normal);
}

.secondary-btn {
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(15, 23, 42, 0.52);
  color: rgba(255, 255, 255, 0.92);
}

.cta-btn:hover,
.secondary-btn:hover,
.task-panel button:hover,
.path-panel button:hover {
  box-shadow: 0 16px 42px rgba(124, 58, 237, 0.28);
  transform: translateY(-1px);
}

.secondary-btn:hover {
  border-color: rgba(255, 255, 255, 0.36);
  background: rgba(30, 41, 59, 0.72);
  box-shadow: none;
}

.quick-start-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.quick-start-card {
  position: relative;
  display: grid;
  min-height: 176px;
  align-content: space-between;
  gap: 14px;
  padding: 24px;
  border: 1px solid var(--home-line);
  border-radius: 28px;
  background:
    radial-gradient(circle at 92% 6%, rgba(34, 211, 238, 0.12), transparent 30%),
    linear-gradient(180deg, rgba(30, 41, 59, 0.78), rgba(15, 23, 42, 0.68));
  color: inherit;
  text-align: left;
  box-shadow: 0 20px 54px rgba(0, 0, 0, 0.22);
  transition: transform var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal);
  overflow: hidden;
}

.quick-start-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.18), transparent 42%, rgba(34, 211, 238, 0.1));
  opacity: 0;
  transition: opacity var(--transition-normal);
  pointer-events: none;
}

.quick-start-card:first-child {
  grid-column: span 2;
  background:
    radial-gradient(circle at 88% 18%, rgba(34, 211, 238, 0.18), transparent 34%),
    linear-gradient(135deg, rgba(124, 58, 237, 0.22), rgba(15, 23, 42, 0.78));
}

.quick-start-card:nth-child(2) {
  grid-column: span 2;
}

.quick-start-card.group-publish::before {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.16), transparent 42%, rgba(34, 197, 94, 0.1));
}

.quick-start-card.group-system::before {
  background: linear-gradient(135deg, rgba(148, 163, 184, 0.14), transparent 46%, rgba(124, 58, 237, 0.12));
}

.quick-start-card:hover {
  border-color: rgba(34, 211, 238, 0.32);
  box-shadow: 0 24px 72px rgba(0, 0, 0, 0.3), 0 0 38px rgba(124, 58, 237, 0.12);
  transform: translateY(-2px);
}

.quick-start-card:hover::before {
  opacity: 1;
}

.quick-start-card strong {
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 20px;
  letter-spacing: -0.02em;
}

.quick-start-card small {
  width: fit-content;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(124, 58, 237, 0.18);
  color: #ddd6fe;
  font-size: 11px;
  font-weight: 900;
}

.quick-start-card.group-publish small {
  background: rgba(34, 211, 238, 0.13);
  color: #a5f3fc;
}

.quick-start-card.group-system small {
  background: rgba(148, 163, 184, 0.14);
  color: #cbd5e1;
}

.quick-start-card span {
  color: var(--home-muted);
  font-size: 14px;
  line-height: 1.7;
}

.quick-start-card i {
  position: absolute;
  right: 14px;
  bottom: 11px;
  color: rgba(148, 163, 184, 0.16);
  font-style: normal;
  font-size: 24px;
  font-weight: 950;
  letter-spacing: -0.06em;
}

.sub-tabs {
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
  padding: 8px;
  border: 1px solid var(--home-line);
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.62);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
}

.sub-tabs span,
.sub-tabs b {
  padding: 8px 12px;
  border-radius: 999px;
  color: var(--home-muted);
  font-size: 13px;
  font-weight: 800;
}

.sub-tabs span {
  color: var(--home-soft);
}

.sub-tabs b.active {
  background: rgba(124, 58, 237, 0.22);
  color: #ecfeff;
  box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.14);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.metric-card,
.task-panel {
  border: 1px solid var(--home-line);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.68)),
    var(--home-surface-strong);
  box-shadow: 0 20px 58px rgba(0, 0, 0, 0.24);
}

.metric-card {
  position: relative;
  display: grid;
  gap: 10px;
  min-height: 164px;
  padding: 24px;
  overflow: hidden;
}

.metric-card::after {
  content: '';
  position: absolute;
  right: 18px;
  bottom: 18px;
  width: 46px;
  height: 5px;
  border-radius: 999px;
  background: rgba(34, 211, 238, 0.28);
}

.metric-card.done {
  box-shadow: inset 0 4px 0 var(--home-green), 0 20px 58px rgba(0, 0, 0, 0.24);
}

.metric-card.active {
  box-shadow: inset 0 4px 0 var(--home-accent), 0 20px 58px rgba(0, 0, 0, 0.24);
}

.metric-card.warning {
  box-shadow: inset 0 4px 0 var(--home-warm), 0 20px 58px rgba(0, 0, 0, 0.24);
}

.metric-card span,
.task-list small {
  color: var(--home-muted);
  font-size: 13px;
  font-weight: 700;
}

.metric-card strong {
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 42px;
  font-weight: 950;
  letter-spacing: -0.055em;
}

.metric-card small {
  color: var(--home-soft);
  font-size: 12px;
  line-height: 1.6;
}

.task-panel {
  display: grid;
  gap: 18px;
  padding: 26px;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.28fr) minmax(300px, 0.72fr);
  gap: 22px;
}

.task-panel header,
.task-list article {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-list article > div {
  display: grid;
  gap: 4px;
}

.task-panel h3 {
  margin: 0;
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 21px;
  letter-spacing: -0.03em;
}

.task-list {
  display: grid;
  gap: 8px;
}

.task-list article {
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.48);
  transition: background var(--transition-normal), border-color var(--transition-normal);
}

.task-list article:hover {
  border-color: rgba(34, 211, 238, 0.22);
  background: rgba(30, 41, 59, 0.58);
}

.task-list strong {
  color: var(--home-ink);
}

.task-list span {
  color: var(--home-accent-dark);
  font-size: 13px;
  font-weight: 800;
}

.task-action {
  flex: 0 0 auto;
}

.asset-list {
  display: grid;
  gap: 10px;
}

.asset-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 5px 12px;
  align-items: center;
  padding: 15px 16px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.48);
}

.asset-list span,
.asset-list small {
  color: var(--home-muted);
  font-size: 12px;
  font-weight: 800;
}

.asset-list strong {
  color: var(--home-ink);
  font-size: 22px;
  font-weight: 950;
  grid-row: span 2;
}

.path-panel {
  display: grid;
  gap: 20px;
  padding: 26px;
}

.path-panel header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.path-panel h3 {
  margin: 0;
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 21px;
  letter-spacing: -0.03em;
}

.path-steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.path-steps article {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 4px 12px;
  align-items: center;
  padding: 18px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 22px;
  background: rgba(15, 23, 42, 0.48);
  color: #e2e8f0;
  font-weight: 900;
}

.path-steps i {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  grid-row: span 2;
  border-radius: 999px;
  background: rgba(124, 58, 237, 0.24);
  color: #ecfeff;
  font-style: normal;
  font-size: 12px;
}

.path-steps small {
  color: var(--home-muted);
  font-size: 12px;
  font-weight: 700;
}

.cta-btn:focus-visible,
.secondary-btn:focus-visible,
.quick-start-card:focus-visible,
.task-panel button:focus-visible,
.path-panel button:focus-visible {
  outline: 3px solid rgba(34, 211, 238, 0.34);
  outline-offset: 3px;
}

@media (max-width: 900px) {
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .dashboard-hero {
    grid-template-columns: 1fr;
  }

  .quick-start-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .quick-start-card,
  .quick-start-card:first-child,
  .quick-start-card:nth-child(2) {
    grid-column: span 1;
  }

  .quick-start-card:nth-child(6),
  .quick-start-card:nth-child(7) {
    grid-column: span 1;
  }

  .metric-grid,
  .path-steps,
  .workbench-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .home-tools {
    padding: 14px;
    gap: 16px;
    border-radius: 26px;
  }

  .section-head h3 {
    font-size: 24px;
  }

  .section-head p {
    max-width: 100%;
  }

  .dashboard-hero {
    min-height: auto;
    padding: 22px;
    border-radius: 26px;
  }

  .hero-copy {
    gap: 18px;
    justify-content: flex-start;
  }

  .dashboard-hero h2 {
    max-width: 100%;
    font-size: clamp(31px, 10.5vw, 40px);
    line-height: 1.02;
  }

  .dashboard-hero p {
    font-size: 14px;
    line-height: 1.75;
  }

  .hero-brief {
    gap: 14px;
    padding: 16px;
  }

  .hero-brief > strong {
    font-size: 20px;
  }

  .hero-stat-row {
    grid-template-columns: 1fr;
  }

  .quick-start-grid {
    grid-template-columns: 1fr;
  }

  .quick-start-card {
    min-height: 104px;
    padding: 20px;
  }

  .metric-grid,
  .path-steps,
  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .task-panel header,
  .task-list article {
    align-items: flex-start;
    flex-direction: column;
  }

  .sub-tabs {
    width: 100%;
    border-radius: 22px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cta-btn,
  .secondary-btn,
  .quick-start-card,
  .task-panel button,
  .path-panel button,
  .task-list article {
    transition: none;
  }
}
</style>

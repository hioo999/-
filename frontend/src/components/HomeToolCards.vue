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
  { label: 'IP 完整度', value: '72%', hint: '还差平台策略、内容规则、转化路径', state: 'warning' },
  { label: '内容资产', value: '18', hint: '选题、脚本、提示词、发布包', state: 'active' },
  { label: '待发布', value: '4', hint: '已生成，待质检和导出', state: 'pending' },
  { label: '失败任务', value: '0', hint: '今天没有阻塞任务', state: 'done' },
]

const fallbackTasks: DashboardTask[] = [
  { title: '补齐 IP 档案', status: '下一步', owner: '人设定位 / 平台配置', action: '去完善', actionKey: 'sprint1' },
  { title: '创建内容选题并输入素材', status: '可开始', owner: 'IP 项目 / 选题 / 素材', action: '去生产', actionKey: 'ip' },
  { title: '打通公众号草稿闭环', status: '本期主线', owner: '文章 / 封面 / 草稿箱', action: '去处理', actionKey: 'ip' },
]

const fallbackAssetStatuses = [
  { label: '最近文章', value: '6', hint: '2 篇待排版' },
  { label: '最近脚本', value: '11', hint: '3 篇可发送提词器' },
  { label: '最近封面', value: '24', hint: '图片/素材图' },
  { label: '发布包', value: '5', hint: '2 个待质检' },
]

const heroStats = computed(() => {
  if (!props.dashboard) return fallbackHeroStats
  return [
    { label: '生产闭环', value: '4 步' },
    { label: '可续写资产', value: `${props.dashboard.assetSummary.total} 件` },
    { label: '待处理任务', value: `${props.dashboard.taskSummary.total} 个` },
  ]
})

const metrics = computed<DashboardMetric[]>(() => {
  if (!props.dashboard) return fallbackMetrics
  const missing = props.dashboard.ipCompleteness.missingItems
  return [
    {
      label: 'IP 完整度',
      value: `${props.dashboard.ipCompleteness.value}%`,
      hint: missing.length ? `还差${missing.join('、')}` : '已具备基础生产条件',
      state: props.dashboard.ipCompleteness.value >= 80 ? 'done' : 'warning',
    },
    { label: '内容资产', value: String(props.dashboard.assetSummary.total), hint: '脚本、图片、发布包统一沉淀', state: 'active' },
    { label: '待发布', value: String(props.dashboard.taskSummary.pendingPublish), hint: '已生成，待质检和发布', state: 'pending' },
    { label: '失败任务', value: String(props.dashboard.taskSummary.failed), hint: '需要重试或人工处理', state: props.dashboard.taskSummary.failed ? 'warning' : 'done' },
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
    { label: '最近文章', value: String(props.dashboard.assetSummary.publishPackages), hint: '发布包与文章草稿' },
    { label: '最近脚本', value: String(props.dashboard.assetSummary.scripts), hint: '口播稿和平台文案' },
    { label: '最近封面', value: String(props.dashboard.assetSummary.images), hint: '封面/插图/素材图' },
    { label: '失败任务', value: String(props.dashboard.taskSummary.failed), hint: '需要重试或处理' },
  ]
})

const pathSteps = [
  { title: '建档', detail: '定位 / 受众 / 栏目' },
  { title: '输入素材', detail: '图片 / 链接 / 文档' },
  { title: '生成内容', detail: '脚本 / 分镜 / 提示词' },
  { title: '质检发布', detail: '排版 / 导出 / 归档' },
]

const quickStarts: QuickStartItem[] = [
  { label: '新建 IP', description: '建立人设、平台和内容规则', key: 'sprint1', group: 'start' },
  { label: '生产中心', description: '按项目和选题组织素材与内容', key: 'ip', group: 'produce' },
  { label: '在线提词器', description: '把脚本带到直播和口播录制', key: 'teleprompter', group: 'publish' },
  { label: '公众号排版', description: '排版图文并发送到草稿箱', key: 'wechat', group: 'publish' },
]

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
        <span class="section-eyebrow">Light Product Console</span>
        <h1>今天要推进什么？</h1>
        <p>围绕 IP 项目、内容选题和发布任务组织工作，先看到下一步，再进入具体工具。</p>
        <div class="hero-actions">
          <button class="cta-btn" @click="emit('select', 'ip')">开始生产</button>
          <button class="secondary-btn" @click="emit('select', 'sprint1')">新建 IP</button>
        </div>
      </div>

      <aside class="hero-brief" aria-label="今日生产建议">
        <span>今日待办摘要</span>
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

    <section class="workbench-grid">
      <div class="section-card task-panel" data-testid="home-task-list">
        <header>
          <div>
            <span class="section-kicker">Today</span>
            <h2>今日继续</h2>
          </div>
          <button @click="emit('select', 'ip')">进入工作台</button>
        </header>
        <div class="task-list">
          <article v-for="task in visibleTasks" :key="task.title">
            <div>
              <strong>{{ task.title }}</strong>
              <small>{{ task.owner }}</small>
            </div>
            <span>{{ task.status }}</span>
            <button class="task-action" @click="emit('select', task.actionKey)">{{ task.action }}</button>
          </article>
        </div>
      </div>

      <div class="section-card metric-panel">
        <header>
          <div>
            <span class="section-kicker">Signals</span>
            <h2>关键指标</h2>
          </div>
          <button @click="emit('select', 'models')">模型设置</button>
        </header>
        <div class="metric-grid">
          <article v-for="metric in metrics" :key="metric.label" class="metric-card" :class="metric.state" :data-testid="metric.label === 'IP 完整度' ? 'home-ip-completeness' : undefined">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.hint }}</small>
          </article>
        </div>
      </div>
    </section>

    <section class="section-head">
      <div>
        <span class="section-kicker">Workflow First</span>
        <h2>按生产路径组织入口，不再把所有功能堆在一屏。</h2>
      </div>
      <p>核心操作保留大卡片，系统配置和兼容入口降低视觉权重。</p>
    </section>

    <section class="path-panel section-card">
      <header>
        <h2>标准生产路径</h2>
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

    <section class="recent-panel section-card">
      <header>
        <h2>最近资产</h2>
        <span>文章 / 脚本 / 封面 / 发布包</span>
      </header>
      <div class="asset-list">
        <article v-for="asset in assetStatuses" :key="asset.label">
          <span>{{ asset.label }}</span>
          <strong>{{ asset.value }}</strong>
          <small>{{ asset.hint }}</small>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-tools {
  --home-ink: #0b0b0f;
  --home-text: #374151;
  --home-muted: #6b7280;
  --home-line: #e5e7eb;
  --home-line-strong: #d1d5db;
  --home-surface: #ffffff;
  --home-soft: #f1f3f8;
  --home-blue: #2457ff;
  --home-blue-soft: #eef3ff;
  --home-green: #16a34a;
  --home-orange: #d97706;
  display: grid;
  gap: 22px;
  width: 100%;
  max-width: 1360px;
  min-height: 100%;
  margin: 0 auto;
  color: var(--home-ink);
}

.section-card {
  border: 1px solid var(--home-line);
  border-radius: 28px;
  background: var(--home-surface);
  box-shadow: 0 18px 46px rgba(15, 23, 42, 0.05);
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 24px;
  align-items: stretch;
  min-height: 360px;
  padding: clamp(28px, 4vw, 54px);
  overflow: hidden;
  border: 1px solid var(--home-line);
  border-radius: 34px;
  background:
    radial-gradient(circle at 92% 0%, rgba(36, 87, 255, 0.12), transparent 34%),
    linear-gradient(135deg, #fff 0%, #fff 58%, #f5f7ff 100%);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.07);
}

.hero-copy {
  display: flex;
  max-width: 780px;
  flex-direction: column;
  justify-content: center;
  gap: 22px;
}

.section-eyebrow,
.section-kicker {
  color: var(--home-blue);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.dashboard-hero h1 {
  max-width: 12ch;
  margin: 0;
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: clamp(46px, 6vw, 82px);
  font-weight: 800;
  letter-spacing: -0.07em;
  line-height: 0.98;
}

.dashboard-hero p {
  max-width: 52ch;
  margin: 0;
  color: var(--home-text);
  font-size: 17px;
  line-height: 1.75;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.cta-btn,
.secondary-btn,
.task-panel button,
.metric-panel button,
.path-panel button,
.quick-start-card {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.cta-btn,
.secondary-btn,
.task-panel button,
.metric-panel button,
.path-panel button {
  min-height: 44px;
  padding: 12px 20px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 750;
  white-space: nowrap;
  transition: transform var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal), border-color var(--transition-normal), color var(--transition-normal);
}

.cta-btn,
.path-panel button {
  background: var(--home-blue);
  color: #fff;
  box-shadow: 0 12px 26px rgba(36, 87, 255, 0.18);
}

.secondary-btn,
.task-panel button,
.metric-panel button {
  border: 1px solid var(--home-line);
  background: #fff;
  color: var(--home-ink);
}

.cta-btn:hover,
.path-panel button:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}

.secondary-btn:hover,
.task-panel button:hover,
.metric-panel button:hover {
  border-color: #dbe6ff;
  background: var(--home-blue-soft);
  color: var(--home-blue);
  transform: translateY(-1px);
}

.hero-brief {
  display: grid;
  align-content: space-between;
  gap: 20px;
  min-height: 100%;
  padding: 24px;
  border: 1px solid var(--home-line);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.hero-brief > span {
  color: var(--home-muted);
  font-size: 12px;
  font-weight: 750;
}

.hero-brief > strong {
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 750;
  letter-spacing: -0.04em;
  line-height: 1.22;
}

.dashboard-inline-error {
  color: var(--home-orange);
  font-size: 12px;
  font-weight: 750;
  line-height: 1.5;
}

.progress-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e8edf8;
}

.progress-track i {
  display: block;
  width: 72%;
  height: 100%;
  border-radius: inherit;
  background: var(--home-blue);
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
  border: 1px solid var(--home-line);
  border-radius: 18px;
  background: #fff;
}

.hero-stat-row small,
.metric-card span,
.task-list small,
.asset-list span,
.asset-list small {
  color: var(--home-muted);
  font-size: 12px;
  font-weight: 700;
}

.hero-stat-row b {
  color: var(--home-ink);
  font-size: 15px;
  font-weight: 800;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.65fr) minmax(360px, 0.35fr);
  gap: 22px;
}

.task-panel,
.metric-panel,
.path-panel,
.recent-panel {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.task-panel header,
.metric-panel header,
.path-panel header,
.recent-panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.task-panel h2,
.metric-panel h2,
.path-panel h2,
.recent-panel h2,
.section-head h2 {
  margin: 0;
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 760;
  letter-spacing: -0.04em;
}

.task-list {
  display: grid;
  gap: 10px;
}

.task-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--home-line);
  border-radius: 18px;
  background: #fff;
}

.task-list article > div {
  display: grid;
  gap: 5px;
}

.task-list strong {
  color: var(--home-ink);
  font-size: 15px;
}

.task-list article > span {
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--home-blue-soft);
  color: var(--home-blue);
  font-size: 12px;
  font-weight: 750;
}

.task-action {
  min-height: 38px !important;
  padding: 8px 14px !important;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  display: grid;
  gap: 8px;
  min-height: 134px;
  padding: 18px;
  border: 1px solid var(--home-line);
  border-top: 3px solid var(--home-line-strong);
  border-radius: 20px;
  background: #fff;
}

.metric-card.done { border-top-color: var(--home-green); }
.metric-card.active { border-top-color: var(--home-blue); }
.metric-card.warning { border-top-color: var(--home-orange); }

.metric-card strong {
  color: var(--home-ink);
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.06em;
}

.metric-card small {
  color: var(--home-muted);
  font-size: 12px;
  line-height: 1.55;
}

.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  padding: 8px 2px 0;
}

.section-head h2 {
  max-width: 680px;
  margin-top: 6px;
  font-size: clamp(24px, 2.4vw, 34px);
}

.section-head p {
  max-width: 360px;
  margin: 0;
  color: var(--home-muted);
  font-size: 14px;
  font-weight: 650;
  line-height: 1.7;
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
  border: 1px solid var(--home-line);
  border-radius: 20px;
  background: #fbfcff;
  color: var(--home-ink);
  font-weight: 800;
}

.path-steps i {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  grid-row: span 2;
  border-radius: 999px;
  background: var(--home-blue-soft);
  color: var(--home-blue);
  font-style: normal;
  font-size: 12px;
}

.path-steps small {
  color: var(--home-muted);
  font-size: 12px;
  font-weight: 650;
}

.quick-start-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.quick-start-card {
  position: relative;
  display: grid;
  min-height: 156px;
  align-content: space-between;
  gap: 12px;
  padding: 22px;
  border: 1px solid var(--home-line);
  border-radius: 24px;
  background: #fff;
  color: inherit;
  text-align: left;
  box-shadow: 0 16px 38px rgba(15, 23, 42, 0.04);
  transition: transform var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal);
  overflow: hidden;
}

.quick-start-card:first-child,
.quick-start-card:nth-child(2) {
  background: linear-gradient(135deg, #fff, #f6f8ff);
}

.quick-start-card:hover {
  border-color: #dbe6ff;
  box-shadow: 0 20px 48px rgba(36, 87, 255, 0.1);
  transform: translateY(-2px);
}

.quick-start-card strong {
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 19px;
  letter-spacing: -0.03em;
}

.quick-start-card small {
  width: fit-content;
  padding: 5px 9px;
  border-radius: 999px;
  background: var(--home-blue-soft);
  color: var(--home-blue);
  font-size: 11px;
  font-weight: 800;
}

.quick-start-card.group-publish small {
  background: rgba(22, 163, 74, 0.1);
  color: var(--home-green);
}

.quick-start-card span {
  color: var(--home-muted);
  font-size: 14px;
  line-height: 1.65;
}

.quick-start-card i {
  position: absolute;
  right: 16px;
  bottom: 12px;
  color: #d8deea;
  font-style: normal;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.06em;
}

.recent-panel header > span {
  color: var(--home-muted);
  font-size: 13px;
  font-weight: 700;
}

.asset-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.asset-list article {
  display: grid;
  gap: 7px;
  padding: 17px;
  border: 1px solid var(--home-line);
  border-radius: 18px;
  background: #fbfcff;
}

.asset-list strong {
  color: var(--home-ink);
  font-size: 24px;
  font-weight: 800;
}

.cta-btn:focus-visible,
.secondary-btn:focus-visible,
.quick-start-card:focus-visible,
.task-panel button:focus-visible,
.metric-panel button:focus-visible,
.path-panel button:focus-visible {
  outline: 3px solid rgba(36, 87, 255, 0.22);
  outline-offset: 3px;
}

@media (max-width: 1100px) {
  .dashboard-hero,
  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .quick-start-grid,
  .path-steps,
  .asset-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .home-tools {
    gap: 16px;
  }

  .dashboard-hero,
  .section-card {
    border-radius: 22px;
  }

  .dashboard-hero {
    min-height: auto;
    padding: 22px;
  }

  .dashboard-hero h1 {
    max-width: 100%;
    font-size: clamp(34px, 11vw, 46px);
    line-height: 1.04;
  }

  .dashboard-hero p {
    font-size: 15px;
  }

  .hero-brief,
  .task-panel,
  .metric-panel,
  .path-panel,
  .recent-panel {
    padding: 18px;
  }

  .hero-stat-row,
  .metric-grid,
  .quick-start-grid,
  .path-steps,
  .asset-list {
    grid-template-columns: 1fr;
  }

  .task-panel header,
  .metric-panel header,
  .path-panel header,
  .recent-panel header,
  .section-head,
  .task-list article {
    align-items: flex-start;
    flex-direction: column;
  }

  .task-list article {
    display: flex;
  }

  .section-head p {
    max-width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cta-btn,
  .secondary-btn,
  .quick-start-card,
  .task-panel button,
  .metric-panel button,
  .path-panel button {
    transition: none;
  }
}
</style>

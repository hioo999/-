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

interface HomeModule {
  title: string
  label: string
  description: string
  key: ToolKey
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
  { label: '覆盖阶段', value: '定位到发布' },
  { label: '内容资产', value: '64 件示例' },
  { label: '发布闭环', value: '草稿箱可接入' },
]

const fallbackMetrics: DashboardMetric[] = [
  { label: 'IP 完整度', value: '72%', hint: '还差平台策略、内容规则、转化路径', state: 'warning' },
  { label: '内容资产', value: '18', hint: '选题、脚本、提示词、发布包', state: 'active' },
  { label: '待发布', value: '4', hint: '已生成，待质检和导出', state: 'pending' },
  { label: '失败任务', value: '0', hint: '当前没有阻塞任务', state: 'done' },
]

const fallbackAssetStatuses = [
  { label: '文章草稿', value: '6', hint: '适合公众号排版' },
  { label: '口播脚本', value: '11', hint: '可发送提词器' },
  { label: '封面素材', value: '24', hint: '沉淀为素材库' },
  { label: '发布包', value: '5', hint: '等待质检导出' },
]

const heroStats = computed(() => {
  if (!props.dashboard) return fallbackHeroStats
  return [
    { label: '覆盖阶段', value: '定位到发布' },
    { label: '内容资产', value: `${props.dashboard.assetSummary.total} 件` },
    { label: '待发布', value: `${props.dashboard.taskSummary.pendingPublish} 个` },
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

const assetStatuses = computed(() => {
  if (!props.dashboard) return fallbackAssetStatuses
  return [
    { label: '文章草稿', value: String(props.dashboard.assetSummary.publishPackages), hint: '发布包与文章草稿' },
    { label: '口播脚本', value: String(props.dashboard.assetSummary.scripts), hint: '脚本和平台文案' },
    { label: '封面素材', value: String(props.dashboard.assetSummary.images), hint: '封面、插图、素材图' },
    { label: '异常任务', value: String(props.dashboard.taskSummary.failed), hint: '需要重试或处理' },
  ]
})

const previewStages = [
  { title: '人设定位', detail: '明确受众、风格、栏目和转化路径' },
  { title: '内容工坊', detail: '把选题、素材、脚本和提示词放在同一条线里' },
  { title: '发布交付', detail: '输出口播、文章排版、封面和草稿箱内容' },
]

const moduleCards: HomeModule[] = [
  {
    title: 'IP 档案',
    label: '先定方向',
    description: '把人设定位、平台策略、内容边界和转化目标沉淀成可复用档案。',
    key: 'sprint1',
  },
  {
    title: '内容工坊',
    label: '持续生产',
    description: '围绕项目和选题收集素材，生成脚本、文案、封面提示词和发布包。',
    key: 'ip',
  },
  {
    title: '口播提词器',
    label: '录制可用',
    description: '把脚本直接带到录制现场，减少临场忘词和反复切换工具。',
    key: 'teleprompter',
  },
  {
    title: '公众号排版',
    label: '发布闭环',
    description: '把文章、封面和格式一起整理，推送到公众号草稿箱前完成质检。',
    key: 'wechat',
  },
]

const productFlow = [
  { title: '建立 IP 底座', detail: '定位、受众、价值主张、平台策略' },
  { title: '组织选题素材', detail: '主题、参考链接、图片、知识点' },
  { title: '生成内容资产', detail: '口播脚本、文章、提示词、封面方案' },
  { title: '发布并沉淀', detail: '质检、导出、草稿箱、资产归档' },
]

const quickStarts: QuickStartItem[] = [
  { label: '新建 IP', description: '从人设和平台策略开始', key: 'sprint1', group: 'start' },
  { label: '进入内容工坊', description: '创建选题并输入素材', key: 'ip', group: 'produce' },
  { label: '在线提词器', description: '把脚本带到录制现场', key: 'teleprompter', group: 'publish' },
  { label: '公众号排版', description: '整理文章并推送草稿', key: 'wechat', group: 'publish' },
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
        <span class="section-eyebrow">IP Growth System</span>
        <h1>把个人 IP 打造成可持续内容资产</h1>
        <p>从人设定位、选题素材到脚本、封面和公众号草稿，首页先说明产品能力，再进入具体工具。</p>
        <div class="hero-actions">
          <button class="cta-btn" @click="emit('select', 'ip')">开始生产</button>
          <button class="secondary-btn" @click="emit('select', 'sprint1')">新建 IP</button>
        </div>
        <div class="hero-stat-row" aria-label="产品覆盖范围">
          <article v-for="stat in heroStats" :key="stat.label">
            <small>{{ stat.label }}</small>
            <b>{{ stat.value }}</b>
          </article>
        </div>
      </div>

      <aside class="product-preview" aria-label="产品能力预览">
        <div class="preview-topline">
          <span>{{ loading ? '正在同步资产状态' : 'IP 打造全案' }}</span>
          <strong>定位 / 生产 / 发布</strong>
        </div>
        <div class="preview-stack">
          <article v-for="(stage, index) in previewStages" :key="stage.title" class="preview-card">
            <i>{{ String(index + 1).padStart(2, '0') }}</i>
            <div>
              <strong>{{ stage.title }}</strong>
              <small>{{ stage.detail }}</small>
            </div>
          </article>
        </div>
        <small v-if="error" class="dashboard-inline-error">实时数据暂未同步，当前展示产品导览内容。</small>
      </aside>
    </section>

    <section class="promise-grid">
      <article class="manifesto-card section-card">
        <span>首页应该先回答</span>
        <h2>这个系统能帮你把一个人设，稳定变成一批可发布内容。</h2>
        <p>它不是开发待办，也不是工具列表。首页保留产品主张、生产路径和关键入口，让创作者先理解闭环，再选择下一步。</p>
      </article>

      <aside class="status-panel section-card" aria-label="资产状态概览">
        <header>
          <h2>资产状态</h2>
          <span>{{ dashboard ? '实时数据' : '默认示例' }}</span>
        </header>
        <div class="metric-grid">
          <article
            v-for="metric in metrics"
            :key="metric.label"
            class="metric-card"
            :class="metric.state"
            :data-testid="metric.label === 'IP 完整度' ? 'home-ip-completeness' : undefined"
          >
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.hint }}</small>
          </article>
        </div>
      </aside>
    </section>

    <section class="module-section section-card">
      <header>
        <div>
          <span>核心能力</span>
          <h2>围绕 IP 成长，而不是围绕菜单堆叠。</h2>
        </div>
        <button @click="emit('select', 'ip')">进入内容工坊</button>
      </header>
      <div class="module-grid">
        <button
          v-for="(module, index) in moduleCards"
          :key="module.title"
          class="module-card"
          :class="{ featured: index === 0 }"
          @click="emit('select', module.key)"
        >
          <small>{{ module.label }}</small>
          <strong>{{ module.title }}</strong>
          <span>{{ module.description }}</span>
        </button>
      </div>
    </section>

    <section class="product-flow section-card">
      <header>
        <h2>标准生产路径</h2>
        <p>从第一次建档到一篇内容进入草稿箱，每一步都沉淀为下一次生产的上下文。</p>
      </header>
      <div class="flow-grid">
        <article v-for="(step, index) in productFlow" :key="step.title">
          <i>{{ index + 1 }}</i>
          <strong>{{ step.title }}</strong>
          <small>{{ step.detail }}</small>
        </article>
      </div>
    </section>

    <section class="quick-start-shell">
      <header>
        <h2>从这里开始</h2>
        <p>入口保持少而明确，把系统设置留给需要时再打开。</p>
      </header>
      <div class="quick-start-grid" aria-label="快捷开工入口">
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
      </div>
    </section>

    <section class="recent-panel section-card">
      <header>
        <h2>内容资产会被持续沉淀</h2>
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
  --home-muted: #667085;
  --home-line: #e4e7ec;
  --home-line-strong: #cfd7e6;
  --home-surface: #ffffff;
  --home-soft: #f4f7fb;
  --home-blue: #2457ff;
  --home-blue-soft: #edf3ff;
  --home-green: #148a53;
  --home-orange: #c76b12;
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
  border-radius: 30px;
  background: var(--home-surface);
  box-shadow: 0 20px 54px rgba(15, 23, 42, 0.055);
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
  gap: 28px;
  align-items: stretch;
  min-height: 470px;
  padding: clamp(28px, 4vw, 56px);
  overflow: hidden;
  border: 1px solid rgba(36, 87, 255, 0.12);
  border-radius: 36px;
  background:
    radial-gradient(circle at 88% 12%, rgba(36, 87, 255, 0.16), transparent 34%),
    radial-gradient(circle at 0% 100%, rgba(20, 138, 83, 0.12), transparent 32%),
    linear-gradient(135deg, #ffffff 0%, #f7f9ff 48%, #eef3ff 100%);
  box-shadow: 0 28px 78px rgba(15, 23, 42, 0.08);
}

.hero-copy {
  display: flex;
  max-width: 760px;
  flex-direction: column;
  justify-content: center;
  gap: 22px;
}

.section-eyebrow {
  width: fit-content;
  padding: 7px 11px;
  border: 1px solid rgba(36, 87, 255, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--home-blue);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.dashboard-hero h1 {
  max-width: 13ch;
  margin: 0;
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: clamp(42px, 5.4vw, 76px);
  font-weight: 820;
  letter-spacing: -0.072em;
  line-height: 1.02;
}

.dashboard-hero p,
.manifesto-card p,
.product-flow p,
.quick-start-shell p {
  margin: 0;
  color: var(--home-text);
  font-size: 16px;
  line-height: 1.78;
}

.dashboard-hero p {
  max-width: 50ch;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.cta-btn,
.secondary-btn,
.module-section button,
.module-card,
.quick-start-card {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.cta-btn,
.secondary-btn,
.module-section > header button {
  min-height: 46px;
  padding: 12px 22px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 780;
  white-space: nowrap;
  transition: transform var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal), border-color var(--transition-normal), color var(--transition-normal);
}

.cta-btn,
.module-section > header button {
  background: var(--home-blue);
  color: #fff;
  box-shadow: 0 14px 28px rgba(36, 87, 255, 0.2);
}

.secondary-btn {
  border: 1px solid var(--home-line-strong);
  background: rgba(255, 255, 255, 0.86);
  color: var(--home-ink);
}

.cta-btn:hover,
.module-section > header button:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}

.secondary-btn:hover {
  border-color: #c9d8ff;
  background: var(--home-blue-soft);
  color: var(--home-blue);
  transform: translateY(-1px);
}

.hero-stat-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  max-width: 660px;
}

.hero-stat-row article {
  display: grid;
  gap: 7px;
  padding: 15px;
  border: 1px solid rgba(36, 87, 255, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.68);
}

.hero-stat-row small,
.metric-card span,
.asset-list span,
.asset-list small,
.preview-card small,
.module-card span,
.quick-start-card span,
.flow-grid small {
  color: var(--home-muted);
  font-size: 12px;
  font-weight: 700;
}

.hero-stat-row b {
  color: var(--home-ink);
  font-size: 15px;
  font-weight: 820;
}

.product-preview {
  display: grid;
  align-content: space-between;
  gap: 18px;
  min-height: 100%;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.96), 0 18px 48px rgba(36, 87, 255, 0.08);
}

.preview-topline {
  display: grid;
  gap: 8px;
}

.preview-topline span,
.manifesto-card > span,
.module-section header span,
.quick-start-card small,
.status-panel header span {
  color: var(--home-blue);
  font-size: 12px;
  font-weight: 820;
}

.preview-topline strong {
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: clamp(28px, 3vw, 38px);
  font-weight: 790;
  letter-spacing: -0.055em;
}

.preview-stack {
  display: grid;
  gap: 12px;
}

.preview-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  padding: 17px;
  border: 1px solid var(--home-line);
  border-radius: 22px;
  background: #fff;
}

.preview-card i,
.flow-grid i {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 999px;
  background: var(--home-blue-soft);
  color: var(--home-blue);
  font-style: normal;
  font-size: 12px;
  font-weight: 820;
}

.preview-card div {
  display: grid;
  gap: 6px;
}

.preview-card strong {
  color: var(--home-ink);
  font-size: 15px;
  font-weight: 820;
}

.dashboard-inline-error {
  color: var(--home-orange);
  font-size: 12px;
  font-weight: 760;
  line-height: 1.5;
}

.promise-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(420px, 1.08fr);
  gap: 22px;
}

.manifesto-card,
.status-panel,
.module-section,
.product-flow,
.recent-panel {
  display: grid;
  gap: 20px;
  padding: 26px;
}

.manifesto-card {
  align-content: center;
  min-height: 300px;
  background:
    linear-gradient(135deg, #0b0b0f 0%, #18213a 100%);
  color: #fff;
}

.manifesto-card > span {
  color: #a8c1ff;
}

.manifesto-card h2,
.module-section h2,
.product-flow h2,
.quick-start-shell h2,
.recent-panel h2,
.status-panel h2 {
  margin: 0;
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: clamp(24px, 2.35vw, 34px);
  font-weight: 790;
  letter-spacing: -0.052em;
  line-height: 1.16;
}

.manifesto-card h2 {
  max-width: 16ch;
  color: #fff;
}

.manifesto-card p {
  max-width: 58ch;
  color: rgba(255, 255, 255, 0.78);
}

.status-panel header,
.module-section header,
.product-flow header,
.recent-panel header,
.quick-start-shell header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
}

.status-panel header span {
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--home-blue-soft);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  display: grid;
  gap: 8px;
  min-height: 138px;
  padding: 18px;
  border: 1px solid var(--home-line);
  border-top: 3px solid var(--home-line-strong);
  border-radius: 21px;
  background: #fff;
}

.metric-card.done { border-top-color: var(--home-green); }
.metric-card.active { border-top-color: var(--home-blue); }
.metric-card.warning { border-top-color: var(--home-orange); }

.metric-card strong {
  color: var(--home-ink);
  font-size: 30px;
  font-weight: 830;
  letter-spacing: -0.06em;
}

.metric-card small {
  color: var(--home-muted);
  font-size: 12px;
  line-height: 1.55;
}

.module-section header > div {
  display: grid;
  gap: 8px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.module-card {
  display: grid;
  min-height: 210px;
  align-content: end;
  gap: 10px;
  padding: 22px;
  border: 1px solid var(--home-line);
  border-radius: 24px;
  background: #fbfcff;
  color: inherit;
  text-align: left;
  transition: transform var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal);
}

.module-card.featured {
  grid-column: span 2;
  background:
    radial-gradient(circle at 88% 12%, rgba(36, 87, 255, 0.14), transparent 34%),
    linear-gradient(135deg, #f8fbff, #eef4ff);
}

.module-card:hover,
.quick-start-card:hover {
  border-color: #cbd8ff;
  box-shadow: 0 20px 48px rgba(36, 87, 255, 0.1);
  transform: translateY(-2px);
}

.module-card small {
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--home-blue-soft);
  color: var(--home-blue);
  font-size: 12px;
  font-weight: 820;
}

.module-card strong,
.quick-start-card strong {
  color: var(--home-ink);
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 790;
  letter-spacing: -0.04em;
}

.module-card span,
.quick-start-card span {
  font-size: 14px;
  line-height: 1.65;
}

.product-flow header {
  align-items: start;
}

.product-flow p {
  max-width: 520px;
  font-size: 14px;
}

.flow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.flow-grid article {
  display: grid;
  gap: 10px;
  min-height: 168px;
  padding: 20px;
  border: 1px solid var(--home-line);
  border-radius: 22px;
  background: #fbfcff;
}

.flow-grid strong {
  color: var(--home-ink);
  font-size: 16px;
  font-weight: 820;
}

.quick-start-shell {
  display: grid;
  gap: 16px;
  padding: 4px 2px 0;
}

.quick-start-shell header {
  padding: 0 2px;
}

.quick-start-shell p {
  max-width: 420px;
  color: var(--home-muted);
  font-size: 14px;
}

.quick-start-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.quick-start-card {
  position: relative;
  display: grid;
  min-height: 162px;
  align-content: space-between;
  gap: 12px;
  padding: 22px;
  overflow: hidden;
  border: 1px solid var(--home-line);
  border-radius: 25px;
  background: #fff;
  color: inherit;
  text-align: left;
  box-shadow: 0 16px 38px rgba(15, 23, 42, 0.04);
  transition: transform var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal);
}

.quick-start-card:first-child,
.quick-start-card:nth-child(2) {
  background: linear-gradient(135deg, #fff, #f5f8ff);
}

.quick-start-card small {
  width: fit-content;
  padding: 5px 9px;
  border-radius: 999px;
  background: var(--home-blue-soft);
}

.quick-start-card.group-publish small {
  background: rgba(20, 138, 83, 0.11);
  color: var(--home-green);
}

.quick-start-card i {
  position: absolute;
  right: 16px;
  bottom: 12px;
  color: #d8deea;
  font-style: normal;
  font-size: 24px;
  font-weight: 820;
  letter-spacing: -0.06em;
}

.recent-panel header > span {
  color: var(--home-muted);
  font-size: 13px;
  font-weight: 720;
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
  border-radius: 19px;
  background: #fbfcff;
}

.asset-list strong {
  color: var(--home-ink);
  font-size: 24px;
  font-weight: 830;
}

.cta-btn:focus-visible,
.secondary-btn:focus-visible,
.module-section button:focus-visible,
.module-card:focus-visible,
.quick-start-card:focus-visible {
  outline: 3px solid rgba(36, 87, 255, 0.22);
  outline-offset: 3px;
}

@media (max-width: 1180px) {
  .dashboard-hero,
  .promise-grid {
    grid-template-columns: 1fr;
  }

  .metric-grid,
  .module-grid,
  .flow-grid,
  .quick-start-grid,
  .asset-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .module-card.featured {
    grid-column: span 1;
  }
}

@media (max-width: 720px) {
  .home-tools {
    gap: 16px;
  }

  .dashboard-hero,
  .section-card {
    border-radius: 23px;
  }

  .dashboard-hero,
  .manifesto-card,
  .status-panel,
  .module-section,
  .product-flow,
  .recent-panel,
  .product-preview {
    padding: 20px;
  }

  .dashboard-hero {
    min-height: auto;
  }

  .dashboard-hero h1 {
    max-width: 100%;
    font-size: clamp(34px, 10.5vw, 46px);
    line-height: 1.06;
  }

  .dashboard-hero p {
    font-size: 15px;
  }

  .hero-stat-row,
  .metric-grid,
  .module-grid,
  .flow-grid,
  .quick-start-grid,
  .asset-list {
    grid-template-columns: 1fr;
  }

  .status-panel header,
  .module-section header,
  .product-flow header,
  .recent-panel header,
  .quick-start-shell header {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cta-btn,
  .secondary-btn,
  .module-section button,
  .module-card,
  .quick-start-card {
    transition: none;
  }
}
</style>

<script setup lang="ts">
export type ToolKey = 'ip' | 'sprint1' | 'reversal' | 'teleprompter' | 'prompts'

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

const emit = defineEmits<{
  select: [key: ToolKey]
}>()

const tabs = ['总览', '今日任务', '资产状态']

const metrics: DashboardMetric[] = [
  { label: 'IP 档案完整度', value: '72%', hint: '还差平台策略、内容规则、转化路径', state: 'warning' },
  { label: '内容资产', value: '18', hint: '选题、脚本、提示词、发布包统一沉淀', state: 'active' },
  { label: '待发布包', value: '4', hint: '已生成，待质检和导出', state: 'pending' },
  { label: '今日继续', value: '3', hint: '最近 IP、短视频项目和提词稿', state: 'done' },
]

const tasks: DashboardTask[] = [
  { title: '补齐 IP 档案', status: '下一步', owner: '人设定位/平台配置', action: '去完善', actionKey: 'sprint1' },
  { title: '生成第一版口播脚本', status: '可开始', owner: '主题或素材输入', action: '去生成', actionKey: 'ip' },
  { title: '整理短视频工作流', status: '待归档', owner: '分镜/提示词/发布包', action: '去工作台', actionKey: 'ip' },
]

const assetStatuses = [
  { label: 'IP 档案', value: '6', hint: '2 个待补齐' },
  { label: '素材', value: '24', hint: '图片/视频/文档' },
  { label: '脚本', value: '11', hint: '3 个可发送提词器' },
  { label: '发布包', value: '5', hint: '2 个待质检' },
]

const quickStarts: Array<{ label: string; description: string; key: ToolKey }> = [
  { label: '新建 IP', description: '先建立人设、平台和内容规则', key: 'sprint1' },
  { label: '上传/输入素材', description: '进入内容生产工作台生成脚本', key: 'ip' },
  { label: '短视频工作流', description: '生成分镜、动态脚本和最终提示词', key: 'ip' },
  { label: '在线提词器', description: '把脚本带到直播和口播录制', key: 'teleprompter' },
]
</script>

<template>
  <div class="home-tools">
    <section class="dashboard-hero glass-panel" data-testid="home-dashboard">
      <div>
        <span class="section-eyebrow">Dashboard</span>
        <h2>今天的工作台</h2>
        <p>围绕一个 IP 的内容生产链路推进：补档案、进工作台、生成脚本、质检发布、沉淀资产。</p>
      </div>
      <button class="cta-btn" @click="emit('select', 'sprint1')">新建 IP</button>
    </section>

    <nav class="sub-tabs glass-panel">
      <button v-for="tab in tabs" :key="tab" :class="{ active: tab === '总览' }">{{ tab }}</button>
    </nav>

    <section class="quick-start-grid">
      <button v-for="item in quickStarts" :key="item.label" class="quick-start-card" @click="emit('select', item.key)">
        <strong>{{ item.label }}</strong>
        <span>{{ item.description }}</span>
      </button>
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
          <button @click="emit('select', 'prompts')">提示词管理</button>
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
        <article v-for="(step, index) in ['建 IP 档案', '上传/输入素材', '生成内容', '质检发布']" :key="step">
          <i>{{ index + 1 }}</i>
          <span>{{ step }}</span>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-tools {
  display: grid;
  gap: 18px;
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 28px;
  background:
    radial-gradient(circle at 8% 0%, rgba(37, 99, 235, 0.08), transparent 34%),
    radial-gradient(circle at 92% 8%, rgba(124, 58, 237, 0.06), transparent 32%),
    var(--color-bg-primary);
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

.dashboard-hero {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 22px;
}

.section-eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.dashboard-hero h2 {
  margin: 6px 0 8px;
  color: #0f172a;
  font-size: 30px;
  font-weight: 900;
}

.dashboard-hero p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.cta-btn,
.sub-tabs button,
.task-panel button,
.quick-start-card,
.path-panel button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.cta-btn,
.task-panel button,
.path-panel button {
  padding: 10px 16px;
  border-radius: 999px;
  background: var(--color-accent-gradient);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  transition: all var(--transition-normal);
}

.cta-btn:hover,
.task-panel button:hover,
.path-panel button:hover {
  filter: saturate(1.05) brightness(1.02);
  box-shadow: 0 14px 34px rgba(37, 99, 235, 0.2);
  transform: translateY(-1px);
}

.quick-start-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.quick-start-card {
  display: grid;
  gap: 7px;
  padding: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.76);
  color: inherit;
  text-align: left;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
  transition: all var(--transition-normal);
}

.quick-start-card:hover {
  border-color: rgba(37, 99, 235, 0.24);
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}

.quick-start-card strong {
  color: #0f172a;
  font-size: 16px;
}

.quick-start-card span {
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.sub-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 18px;
}

.sub-tabs button {
  padding: 9px 14px;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
}

.sub-tabs button.active {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.1);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card,
.task-panel {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
}

.metric-card {
  display: grid;
  gap: 8px;
  padding: 18px;
}

.metric-card.done {
  box-shadow: inset 0 3px 0 #22c55e, 0 12px 32px rgba(15, 23, 42, 0.05);
}

.metric-card.active {
  box-shadow: inset 0 3px 0 #2563eb, 0 12px 32px rgba(15, 23, 42, 0.05);
}

.metric-card.warning {
  box-shadow: inset 0 3px 0 #f59e0b, 0 12px 32px rgba(15, 23, 42, 0.05);
}

.metric-card span,
.task-list small {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.metric-card strong {
  color: #0f172a;
  font-size: 32px;
  font-weight: 900;
}

.metric-card small {
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.6;
}

.task-panel {
  display: grid;
  gap: 14px;
  padding: 20px;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  gap: 18px;
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
  color: #0f172a;
  font-size: 20px;
}

.task-list {
  display: grid;
  gap: 10px;
}

.task-list article {
  padding: 14px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.86);
  border: 1px solid rgba(15, 23, 42, 0.05);
}

.task-list strong {
  color: #0f172a;
}

.task-list span {
  color: #2563eb;
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
  gap: 4px 12px;
  align-items: center;
  padding: 13px 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.84);
}

.asset-list span,
.asset-list small {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.asset-list strong {
  color: #0f172a;
  font-size: 22px;
  font-weight: 950;
  grid-row: span 2;
}

.path-panel {
  display: grid;
  gap: 16px;
  padding: 20px;
}

.path-panel header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.path-panel h3 {
  margin: 0;
  color: #0f172a;
  font-size: 20px;
}

.path-steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.path-steps article {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.86);
  color: #334155;
  font-weight: 900;
}

.path-steps i {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-style: normal;
  font-size: 12px;
}

@media (max-width: 900px) {
  .metric-grid,
  .quick-start-grid,
  .path-steps,
  .workbench-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-hero {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .home-tools {
    padding: 18px;
  }

  .metric-grid,
  .quick-start-grid,
  .path-steps,
  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .task-panel header,
  .task-list article {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

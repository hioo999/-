<script setup lang="ts">
import type { DashboardOverview } from '../api/dashboard.api'

export type ToolKey = 'ip' | 'sprint1' | 'platform' | 'reversal' | 'teleprompter' | 'wechat' | 'models' | 'prompts'

interface HomeNavItem {
  title: string
  key: ToolKey
  tone: 'primary' | 'plain'
}

defineProps<{
  dashboard?: DashboardOverview | null
  loading?: boolean
  error?: string
}>()

const emit = defineEmits<{
  select: [key: ToolKey]
}>()

const homeNavItems: HomeNavItem[] = [
  { title: '生产中心', key: 'ip', tone: 'primary' },
  { title: 'IP 档案', key: 'sprint1', tone: 'plain' },
  { title: '多平台工作台', key: 'platform', tone: 'plain' },
  { title: '公众号排版', key: 'wechat', tone: 'plain' },
  { title: '反转剧编剧', key: 'reversal', tone: 'plain' },
  { title: '模型设置', key: 'models', tone: 'plain' },
]
</script>

<template>
  <section class="home-nav" data-testid="home-dashboard" aria-label="首页导航">
    <header class="home-nav-head">
      <span>IP 全案工作台</span>
      <h1>选择入口</h1>
    </header>

    <div class="home-nav-grid">
      <button
        v-for="item in homeNavItems"
        :key="item.key"
        class="home-nav-card"
        :class="item.tone"
        @click="emit('select', item.key)"
      >
        <strong>{{ item.title }}</strong>
      </button>
    </div>
  </section>
</template>

<style scoped>
.home-nav {
  display: grid;
  gap: 28px;
  width: 100%;
  max-width: 1040px;
  min-height: calc(100vh - 180px);
  align-content: center;
  margin: 0 auto;
  color: #0f172a;
}

.home-nav-head {
  display: grid;
  gap: 8px;
  text-align: center;
}

.home-nav-head span {
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.home-nav-head h1 {
  margin: 0;
  color: #0b0f1a;
  font-family: var(--font-display);
  font-size: clamp(34px, 5vw, 54px);
  font-weight: 820;
  letter-spacing: -0.06em;
  line-height: 1;
}

.home-nav-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.home-nav-card {
  display: grid;
  min-height: 132px;
  place-items: center;
  padding: 24px;
  border: 1px solid #e2e8f0;
  border-radius: 26px;
  background: #fff;
  color: #0f172a;
  cursor: pointer;
  font: inherit;
  text-align: center;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.045);
  transition: transform var(--transition-normal), border-color var(--transition-normal), box-shadow var(--transition-normal), background var(--transition-normal), color var(--transition-normal);
}

.home-nav-card strong {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 780;
  letter-spacing: -0.04em;
}

.home-nav-card.primary {
  border-color: rgba(36, 87, 255, 0.22);
  background: linear-gradient(135deg, #2457ff, #1d4ed8);
  color: #fff;
  box-shadow: 0 24px 52px rgba(36, 87, 255, 0.18);
}

.home-nav-card:hover {
  border-color: #cbd8ff;
  box-shadow: 0 24px 54px rgba(36, 87, 255, 0.1);
  transform: translateY(-2px);
}

.home-nav-card.primary:hover {
  background: linear-gradient(135deg, #1d4ed8, #1e40af);
}

.home-nav-card:focus-visible {
  outline: 3px solid rgba(36, 87, 255, 0.22);
  outline-offset: 3px;
}

@media (max-width: 900px) {
  .home-nav {
    min-height: auto;
    align-content: start;
  }

  .home-nav-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .home-nav {
    gap: 20px;
  }

  .home-nav-grid {
    grid-template-columns: 1fr;
  }

  .home-nav-card {
    min-height: 96px;
    border-radius: 22px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-nav-card {
    transition: none;
  }
}
</style>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
import { modePathMap } from '../stores/workspace'
import type { ActiveUser } from '../stores/auth'

defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const router = useRouter()

const publishCards = [
  {
    title: '写公众号文章',
    desc: '从素材生成图文，排版预览后发送草稿箱。',
    path: `${modePathMap.ip}?tab=wechat`,
  },
  {
    title: '直播台本生成',
    desc: '把商品、活动或观点整理成可直接上场的 HTML 直播台本。',
    path: `${modePathMap.teleprompter}?tab=generator`,
  },
  {
    title: '在线提词播放',
    desc: '粘贴口播稿，进入全屏提词录制模式。',
    path: `${modePathMap.teleprompter}?tab=player`,
  },
]
</script>

<template>
  <WorkspaceLayout :current-user="currentUser" @logout="emit('logout')">
    <section class="publish-hub" data-testid="publish-hub">
      <header class="publish-hero">
        <span class="section-eyebrow">内容发布</span>
        <h1>选择发布方式</h1>
        <p>发布前建议先在生产中心完成素材与内容生成，这里提供直达入口。</p>
      </header>
      <div class="publish-grid">
        <button
          v-for="card in publishCards"
          :key="card.title"
          class="publish-card"
          @click="router.push(card.path)"
        >
          <strong>{{ card.title }}</strong>
          <span>{{ card.desc }}</span>
        </button>
      </div>
    </section>
  </WorkspaceLayout>
</template>

<style scoped>
.publish-hub {
  display: grid;
  gap: 24px;
  max-width: 960px;
  margin: 0 auto;
}

.publish-hero h1 {
  margin: 6px 0 8px;
  font-size: clamp(30px, 4vw, 42px);
  letter-spacing: -0.05em;
}

.publish-hero p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.publish-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.publish-card {
  display: grid;
  gap: 8px;
  padding: 22px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  font: inherit;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
  transition: transform var(--transition-normal), border-color var(--transition-normal);
}

.publish-card:hover {
  transform: translateY(-2px);
  border-color: #cbd8ff;
}

.publish-card strong {
  font-size: 18px;
}

.publish-card span {
  color: var(--color-text-secondary);
  line-height: 1.6;
}
</style>

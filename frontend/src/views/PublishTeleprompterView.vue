<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LiveTeleprompterGenerator from '../components/LiveTeleprompterGenerator.vue'
import TeleprompterPanel from '../components/TeleprompterPanel.vue'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
import type { ActiveUser } from '../stores/auth'

const props = defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const route = useRoute()
const router = useRouter()
const teleprompterTab = ref<'generator' | 'player'>('generator')
const teleprompterInitialText = ref('')

function normalizeTab(tab: unknown): 'generator' | 'player' {
  return tab === 'player' ? 'player' : 'generator'
}

teleprompterTab.value = normalizeTab(route.query.tab)

watch(
  () => route.query.tab,
  (tab) => {
    teleprompterTab.value = normalizeTab(tab)
  },
)

const teleprompterUser = computed(() => props.currentUser
  ? {
      name: props.currentUser.name || '用户',
      email: props.currentUser.email || '',
      token: props.currentUser.token,
      isGuest: props.currentUser.isGuest,
    }
  : undefined)

function switchTab(tab: 'generator' | 'player') {
  teleprompterTab.value = tab
  router.replace({ path: route.path, query: { ...route.query, tab } })
}

function handleLiveScriptToPlayer(text: string) {
  teleprompterInitialText.value = text
  switchTab('player')
}
</script>

<template>
  <WorkspaceLayout :current-user="currentUser" @logout="emit('logout')">
    <section class="teleprompter-page">
      <div class="teleprompter-workspace-tabs" aria-label="提词器模式切换">
        <button
          class="teleprompter-workspace-tab"
          :class="{ active: teleprompterTab === 'generator' }"
          @click="switchTab('generator')"
        >直播台本生成</button>
        <button
          class="teleprompter-workspace-tab"
          :class="{ active: teleprompterTab === 'player' }"
          @click="switchTab('player')"
        >在线提词播放</button>
      </div>
      <LiveTeleprompterGenerator
        v-if="teleprompterTab === 'generator'"
        :current-user="currentUser"
        @send-to-player="handleLiveScriptToPlayer"
      />
      <TeleprompterPanel
        v-else
        :initial-text="teleprompterInitialText"
        :current-user="teleprompterUser"
      />
    </section>
  </WorkspaceLayout>
</template>

<style scoped>
.teleprompter-page {
  display: grid;
  gap: 16px;
}

.teleprompter-workspace-tabs {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-tertiary);
  width: fit-content;
}

.teleprompter-workspace-tab {
  min-height: 38px;
  padding: 8px 14px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 650;
}

.teleprompter-workspace-tab.active {
  background: #eef3ff;
  color: var(--color-accent-primary);
}
</style>

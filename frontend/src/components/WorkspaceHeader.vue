<script setup lang="ts">
import { computed } from 'vue'
import { navModuleFromPath, navModulePathMap, modePathMap, type NavModule } from '../stores/workspace'

interface ActiveUser {
  name?: string
  email?: string
  token?: string
  isGuest?: boolean
  is_admin?: boolean
}

interface NavItem {
  id: NavModule
  label: string
  path: string
  title: string
  adminOnly?: boolean
}

const props = defineProps<{
  currentPath: string
  currentUser?: ActiveUser
  isGuestUser: boolean
  isAdminUser: boolean
  isGeneratingDrama?: boolean
  dramaGenerateReason?: string
}>()

const emit = defineEmits<{
  navigate: [path: string]
  logout: []
  generateDrama: []
  requestLogin: []
}>()

const primaryNav: NavItem[] = [
  { id: 'overview', label: '概览', path: navModulePathMap.overview, title: '工作台概览' },
  { id: 'production', label: '生产', path: navModulePathMap.production, title: '生产中心' },
  { id: 'publish', label: '发布', path: navModulePathMap.publish, title: '内容发布' },
  { id: 'settings', label: '设置', path: navModulePathMap.settings, title: '系统设置', adminOnly: true },
]

const activeModule = computed(() => navModuleFromPath(props.currentPath))

const productionShortcuts = [
  { label: 'IP 档案', path: modePathMap.sprint1 },
  { label: '反转剧编剧', path: modePathMap.reversal },
]

const publishShortcuts = [
  { label: '写公众号文章', path: `${modePathMap.ip}?tab=wechat` },
  { label: '小红书/口播', path: `${modePathMap.ip}?tab=platform` },
  { label: '直播台本生成', path: `${modePathMap.teleprompter}?tab=generator` },
  { label: '在线提词播放', path: `${modePathMap.teleprompter}?tab=player` },
]

const settingsShortcuts = [
  { label: '模型设置', path: modePathMap.models },
  { label: '提示词工具', path: modePathMap.prompts, adminOnly: true },
]

function isNavActive(item: NavItem) {
  return activeModule.value === item.id
}

function navigate(path: string) {
  emit('navigate', path)
}

function shortcutItems(module: NavModule) {
  if (module === 'production') return productionShortcuts
  if (module === 'publish') return publishShortcuts
  if (module === 'settings') return settingsShortcuts.filter((item) => !item.adminOnly || props.isAdminUser)
  return []
}
</script>

<template>
  <header class="workspace-header" role="banner">
    <div class="header-left">
      <button
        v-if="currentPath !== '/' && !isGuestUser"
        class="btn btn-ghost btn-sm btn-back-home"
        @click="navigate('/')"
      >返回概览</button>
      <div class="logo" aria-label="IP 全案工作台">
        <span class="logo-icon" aria-hidden="true">IP</span>
        <h1 class="logo-text">IP<span class="text-gradient">全案</span>工作台</h1>
      </div>
      <span class="badge badge-accent">v1.0</span>

      <nav class="mode-switcher app-mode-tabs" aria-label="工作台一级导航">
        <button
          v-for="item in primaryNav.filter((nav) => !nav.adminOnly || isAdminUser)"
          :key="item.id"
          class="tab-item"
          :class="{ active: isNavActive(item) }"
          :aria-current="isNavActive(item) ? 'page' : undefined"
          :title="item.title"
          @click="navigate(item.path)"
        >{{ item.label }}</button>
      </nav>
    </div>

    <div class="header-right">
      <details v-if="!isGuestUser && shortcutItems(activeModule).length" class="module-menu">
        <summary class="btn btn-ghost btn-sm">快捷入口</summary>
        <div class="module-menu-panel" role="menu">
          <button
            v-for="item in shortcutItems(activeModule)"
            :key="item.path"
            role="menuitem"
            :class="{ active: currentPath === item.path.split('?')[0] }"
            @click="navigate(item.path)"
          >{{ item.label }}</button>
        </div>
      </details>
      <div v-if="currentUser" class="user-chip" :title="currentUser.email">
        <span>{{ currentUser.isGuest ? '游客' : currentUser.name }}</span>
      </div>
      <button v-if="isGuestUser" class="guest-scope-chip" type="button" @click="emit('requestLogin')">
        登录解锁全部功能
      </button>
      <button v-if="currentUser" class="btn btn-ghost btn-sm" @click="emit('logout')">退出</button>
      <button
        v-if="currentPath === modePathMap.reversal"
        class="btn btn-primary"
        :title="dramaGenerateReason || '生成反转剧分镜脚本'"
        :disabled="isGeneratingDrama || Boolean(dramaGenerateReason)"
        @click="emit('generateDrama')"
      >
        <span v-if="isGeneratingDrama" class="typing-indicator" style="padding: 0;">
          <span></span><span></span><span></span>
        </span>
        <template v-else>生成反转剧</template>
      </button>
    </div>
  </header>
</template>

<style scoped>
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: nowrap;
  gap: 16px;
  min-height: 64px;
  padding: 10px 28px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.04);
  z-index: 10;
}

.header-left,
.header-right,
.logo,
.mode-switcher {
  display: flex;
  align-items: center;
}

.header-left {
  flex: 1 1 auto;
  gap: 14px;
  min-width: 0;
}

.header-right {
  flex: 0 0 auto;
  gap: 12px;
}

.logo {
  flex: 0 0 auto;
  gap: 8px;
}

.logo-icon {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 10px;
  background: var(--color-accent-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
}

.logo-text {
  color: var(--color-text-primary);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 750;
  letter-spacing: -0.04em;
  white-space: nowrap;
}

.mode-switcher {
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-tertiary);
}

.tab-item {
  position: relative;
  z-index: 1;
  flex: 0 0 auto;
  min-height: 38px;
  padding: 8px 14px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 650;
  transition: all var(--transition-normal);
  white-space: nowrap;
}

.tab-item:hover {
  background: #fff;
  color: var(--color-text-primary);
}

.tab-item.active {
  background: #eef3ff;
  color: var(--color-accent-primary);
  box-shadow: inset 0 0 0 1px #dbe6ff;
}

.module-menu {
  position: relative;
}

.module-menu summary {
  list-style: none;
}

.module-menu summary::-webkit-details-marker {
  display: none;
}

.module-menu-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 20;
  display: grid;
  gap: 6px;
  min-width: 190px;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: #fff;
  box-shadow: var(--shadow-md);
}

.module-menu-panel button {
  min-height: 40px;
  padding: 9px 12px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  text-align: left;
}

.module-menu-panel button:hover,
.module-menu-panel button.active {
  background: #eef3ff;
  color: var(--color-accent-primary);
}

.user-chip,
.guest-scope-chip {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.user-chip {
  max-width: 140px;
  padding: 7px 12px;
  border: 1px solid var(--color-border);
  background: #fff;
  color: var(--color-text-secondary);
}

.user-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guest-scope-chip {
  padding: 7px 11px;
  border: 1px solid rgba(36, 87, 255, 0.18);
  background: rgba(36, 87, 255, 0.08);
  color: var(--color-accent-primary);
  cursor: pointer;
  font: inherit;
}

@media (max-width: 1100px) {
  .workspace-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-left,
  .header-right {
    width: 100%;
    flex-wrap: wrap;
  }

  .mode-switcher {
    flex: 1 0 100%;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    overflow-x: auto;
    overflow-y: hidden;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
  }
}

@media (max-width: 720px) {
  .workspace-header {
    padding: 10px 14px;
  }

  .badge-accent,
  .user-chip {
    display: none;
  }

  .logo-text {
    overflow: hidden;
    max-width: 150px;
    text-overflow: ellipsis;
  }
}
</style>

<script setup lang="ts">
import type { ToolKey } from './HomeToolCards.vue'

type WorkspaceMode = 'home' | ToolKey

interface ActiveUser {
  name?: string
  email?: string
  token?: string
  isGuest?: boolean
  is_admin?: boolean
}

interface NavItem {
  label: string
  mode: WorkspaceMode
  group: 'overview' | 'produce' | 'publish' | 'system'
  title: string
  adminOnly?: boolean
}

const props = defineProps<{
  workspaceMode: WorkspaceMode
  currentUser?: ActiveUser
  isGuestUser: boolean
  isAdminUser: boolean
  isGeneratingDrama: boolean
  dramaGenerateReason: string
}>()

const emit = defineEmits<{
  select: [mode: WorkspaceMode]
  logout: []
  generateDrama: []
}>()

const primaryNav: NavItem[] = [
  { label: '总览', mode: 'home', group: 'overview', title: '首页总览与快捷开工' },
  { label: '生产中心', mode: 'ip', group: 'produce', title: '围绕 IP 项目和内容选题组织素材、平台内容、任务和资产' },
  { label: '发布工具', mode: 'platform', group: 'publish', title: '多平台内容、公众号排版和提词器兼容入口' },
  { label: '系统设置', mode: 'models', group: 'system', title: '模型中转与提示词配置' },
]

const groupedNav: NavItem[] = [
  { label: 'IP 档案库', mode: 'sprint1', group: 'produce', title: '全案底座 Sprint1' },
  { label: '多平台工作台', mode: 'platform', group: 'publish', title: '小红书、抖音、视频号内容生成与资产管理兼容入口' },
  { label: '反转剧编剧', mode: 'reversal', group: 'produce', title: '生成反转剧分镜脚本' },
  { label: '在线提词器', mode: 'teleprompter', group: 'publish', title: '录制和直播提词器' },
  { label: '公众号排版', mode: 'wechat', group: 'publish', title: '公众号排版与草稿箱发布兼容入口' },
  { label: '模型中转', mode: 'models', group: 'system', title: '模型中转与默认模型' },
  { label: '提示词管理', mode: 'prompts', group: 'system', title: '提示词分类与模板管理', adminOnly: true },
]

function isGroupActive(group: NavItem['group']) {
  if (props.workspaceMode === 'home') return group === 'overview'
  return groupedNav.some((item) => item.group === group && item.mode === props.workspaceMode)
}

function selectNav(item: NavItem) {
  if (props.isGuestUser && item.mode !== 'teleprompter') {
    emit('select', 'teleprompter')
    return
  }
  if (item.adminOnly && !props.isAdminUser) return
  emit('select', item.mode)
}
</script>

<template>
  <header class="workspace-header" role="banner">
    <div class="header-left">
      <button
        v-if="workspaceMode !== 'home' && workspaceMode !== 'ip' && !isGuestUser"
        class="btn btn-ghost btn-sm btn-back-home"
        @click="emit('select', 'home')"
      >返回首页</button>
      <div class="logo" aria-label="IP 全案工作台">
        <span class="logo-icon" aria-hidden="true">IP</span>
        <h1 class="logo-text">IP<span class="text-gradient">全案</span>工作台</h1>
      </div>
      <span class="badge badge-accent">v1.0</span>

      <nav v-if="!isGuestUser" class="mode-switcher app-mode-tabs" aria-label="工作台一级导航">
        <button
          v-for="item in primaryNav"
          :key="item.mode"
          class="tab-item"
          :class="{ active: item.mode === workspaceMode || isGroupActive(item.group) }"
          :aria-current="item.mode === workspaceMode || isGroupActive(item.group) ? 'page' : undefined"
          :title="item.title"
          @click="selectNav(item)"
        >{{ item.label }}</button>
      </nav>
    </div>

    <div v-if="workspaceMode !== 'ip'" class="header-right">
      <details v-if="!isGuestUser" class="module-menu">
        <summary class="btn btn-ghost btn-sm">模块</summary>
        <div class="module-menu-panel" role="menu">
          <button
            v-for="item in groupedNav.filter((nav) => !nav.adminOnly || isAdminUser)"
            :key="item.mode"
            role="menuitem"
            :class="{ active: workspaceMode === item.mode }"
            @click="selectNav(item)"
          >{{ item.label }}</button>
        </div>
      </details>
      <div v-if="!isGuestUser" class="global-search" title="快捷搜索和命令入口" aria-label="快捷搜索入口">
        <span>搜索功能 / 项目 / 任务</span>
        <kbd>⌘K</kbd>
      </div>
      <div v-if="currentUser" class="user-chip" :title="currentUser.email">
        <span>{{ currentUser.isGuest ? '游客' : currentUser.name }}</span>
      </div>
      <span v-if="isGuestUser" class="guest-scope-chip">仅提词器可用</span>
      <button class="btn btn-ghost btn-sm" @click="emit('select', 'teleprompter')">在线提词器</button>
      <button v-if="currentUser" class="btn btn-ghost btn-sm" @click="emit('logout')">退出</button>
      <button
        v-if="workspaceMode === 'reversal'"
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

.global-search {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
  padding: 9px 10px 9px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: #fff;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 800;
}

.global-search kbd {
  padding: 3px 7px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 900;
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
  border: 1px solid rgba(217, 119, 6, 0.22);
  background: rgba(217, 119, 6, 0.08);
  color: var(--color-warning);
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
    width: 100%;
    overflow-x: auto;
  }
}

@media (max-width: 720px) {
  .workspace-header {
    padding: 10px 14px;
  }

  .global-search,
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

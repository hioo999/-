import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

/** 工作台业务模块键 */
export type ToolKey = 'ip' | 'sprint1' | 'platform' | 'reversal' | 'teleprompter' | 'wechat' | 'models' | 'prompts'

/** 顶栏四模块 */
export type NavModule = 'overview' | 'production' | 'publish' | 'settings'

export type WorkspaceMode = 'home' | ToolKey

export const modePathMap: Record<WorkspaceMode, string> = {
  home: '/',
  ip: '/workspace/content',
  sprint1: '/workspace/ip-assets',
  platform: '/workspace/content',
  reversal: '/tools/reversal',
  teleprompter: '/publish/teleprompter',
  wechat: '/publish/wechat',
  models: '/settings/models',
  prompts: '/admin/prompts',
}

export const navModulePathMap: Record<NavModule, string> = {
  overview: '/',
  production: '/workspace/content',
  publish: '/publish',
  settings: '/settings/models',
}

export const pathModeMap: Record<string, WorkspaceMode> = {
  '/': 'home',
  '/workspace/content': 'ip',
  '/workspace/ip-assets': 'sprint1',
  '/tools/reversal': 'reversal',
  '/publish/teleprompter': 'teleprompter',
  '/publish/wechat': 'wechat',
  '/settings/models': 'models',
  '/admin/prompts': 'prompts',
}

export const legacyHashPathMap: Record<string, string> = {
  '#/ip': modePathMap.ip,
  '#/sprint1': modePathMap.sprint1,
  '#/platform': modePathMap.platform,
  '#/reversal': modePathMap.reversal,
  '#/teleprompter': modePathMap.teleprompter,
  '#/wechat': modePathMap.wechat,
  '#/models': modePathMap.models,
  '#/prompts': modePathMap.prompts,
}

export function modeFromPath(path: string): WorkspaceMode {
  if (path === '/workspace/platform') return 'ip'
  if (path === '/tools/teleprompter') return 'teleprompter'
  if (path === '/tools/wechat') return 'wechat'
  return pathModeMap[path] || 'home'
}

export function navModuleFromPath(path: string): NavModule {
  if (path === '/' ) return 'overview'
  if (path.startsWith('/workspace') || path === '/tools/reversal') return 'production'
  if (path.startsWith('/publish') || path === '/tools/teleprompter' || path === '/tools/wechat') return 'publish'
  if (path.startsWith('/settings') || path.startsWith('/admin')) return 'settings'
  return 'overview'
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const currentMode = ref<WorkspaceMode>('home')
  const currentPath = computed(() => modePathMap[currentMode.value])

  function setMode(mode: WorkspaceMode) {
    currentMode.value = mode
  }

  function setModeFromPath(path: string) {
    currentMode.value = modeFromPath(path)
  }

  return {
    currentMode,
    currentPath,
    setMode,
    setModeFromPath,
  }
})

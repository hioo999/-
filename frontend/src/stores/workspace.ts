import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { ToolKey } from '../components/HomeToolCards.vue'

export type WorkspaceMode = 'home' | ToolKey

export const modePathMap: Record<WorkspaceMode, string> = {
  home: '/',
  ip: '/workspace/content',
  sprint1: '/workspace/ip-assets',
  platform: '/workspace/platform',
  reversal: '/tools/reversal',
  teleprompter: '/tools/teleprompter',
  wechat: '/tools/wechat',
  models: '/settings/models',
  prompts: '/admin/prompts',
}

export const pathModeMap: Record<string, WorkspaceMode> = Object.fromEntries(
  Object.entries(modePathMap).map(([mode, path]) => [path, mode])
) as Record<string, WorkspaceMode>

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
  return pathModeMap[path] || 'home'
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

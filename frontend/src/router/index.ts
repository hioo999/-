import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { legacyHashPathMap, modePathMap, type WorkspaceMode } from '../stores/workspace'

declare module 'vue-router' {
  interface RouteMeta {
    initialMode?: WorkspaceMode
  }
}

const HomeView = () => import('../views/HomeView.vue')
const CopilotWorkspace = () => import('../views/CopilotWorkspace.vue')

function workspaceProps(mode: WorkspaceMode) {
  return { initialMode: mode }
}

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView },
  { path: modePathMap.ip, name: 'content-workspace', component: CopilotWorkspace, meta: workspaceProps('ip') },
  { path: modePathMap.sprint1, name: 'ip-assets', component: CopilotWorkspace, meta: workspaceProps('sprint1') },
  { path: modePathMap.platform, name: 'platform-workspace', component: CopilotWorkspace, meta: workspaceProps('platform') },
  { path: modePathMap.reversal, name: 'reversal-drama', component: CopilotWorkspace, meta: workspaceProps('reversal') },
  { path: modePathMap.teleprompter, name: 'teleprompter', component: CopilotWorkspace, meta: workspaceProps('teleprompter') },
  { path: modePathMap.wechat, name: 'wechat-publisher', component: CopilotWorkspace, meta: workspaceProps('wechat') },
  { path: modePathMap.models, name: 'model-settings', component: CopilotWorkspace, meta: workspaceProps('models') },
  { path: modePathMap.prompts, name: 'prompt-admin', component: CopilotWorkspace, meta: workspaceProps('prompts') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.path === '/' && to.hash && legacyHashPathMap[to.hash]) {
    return legacyHashPathMap[to.hash]
  }
  return true
})

export default router

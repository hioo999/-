import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { legacyHashPathMap, modePathMap, type WorkspaceMode } from '../stores/workspace'

declare module 'vue-router' {
  interface RouteMeta {
    initialMode?: WorkspaceMode
    guestAllowed?: boolean
  }
}

const HomeView = () => import('../views/HomeView.vue')
const ProductionView = () => import('../views/ProductionView.vue')
const IpAssetsView = () => import('../views/IpAssetsView.vue')
const PublishHubView = () => import('../views/PublishHubView.vue')
const PublishTeleprompterView = () => import('../views/PublishTeleprompterView.vue')
const ReversalView = () => import('../views/ReversalView.vue')
const SettingsView = () => import('../views/SettingsView.vue')
const PromptAdminView = () => import('../views/PromptAdminView.vue')

function workspaceProps(mode: WorkspaceMode) {
  return { initialMode: mode }
}

function isStoredAdminUser() {
  try {
    const raw = window.localStorage.getItem('ip-case-active-user')
    if (!raw) return false
    return JSON.parse(raw)?.is_admin === true
  } catch {
    return false
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView },
  { path: modePathMap.ip, name: 'production', component: ProductionView, meta: workspaceProps('ip') },
  { path: '/workspace/platform', redirect: (to) => ({ path: modePathMap.ip, query: { ...to.query, tab: 'platform' } }) },
  { path: modePathMap.sprint1, name: 'ip-assets', component: IpAssetsView, meta: workspaceProps('sprint1') },
  { path: '/publish', name: 'publish-hub', component: PublishHubView },
  { path: modePathMap.teleprompter, name: 'teleprompter', component: PublishTeleprompterView, meta: { ...workspaceProps('teleprompter'), guestAllowed: true } },
  { path: '/tools/teleprompter', redirect: (to) => ({ path: modePathMap.teleprompter, query: to.query }) },
  { path: modePathMap.wechat, redirect: (to) => ({ path: modePathMap.ip, query: { ...to.query, tab: 'wechat' } }) },
  { path: '/tools/wechat', redirect: (to) => ({ path: modePathMap.ip, query: { ...to.query, tab: 'wechat' } }) },
  { path: modePathMap.reversal, name: 'reversal-drama', component: ReversalView, meta: workspaceProps('reversal') },
  { path: modePathMap.models, name: 'model-settings', component: SettingsView, meta: workspaceProps('models') },
  { path: modePathMap.prompts, name: 'prompt-admin', component: PromptAdminView, meta: workspaceProps('prompts') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function isStoredGuestUser() {
  try {
    const raw = window.localStorage.getItem('ip-case-active-user')
    if (!raw) return true
    return !JSON.parse(raw)?.token
  } catch {
    return true
  }
}

const guestAllowedPaths = new Set([
  '/',
  modePathMap.teleprompter,
  '/tools/teleprompter',
  '/publish',
])

router.beforeEach((to) => {
  if (isStoredGuestUser() && !to.meta.guestAllowed && !guestAllowedPaths.has(to.path)) {
    return {
      path: modePathMap.home,
      query: {
        login: '1',
        redirect: to.fullPath,
      },
    }
  }
  if ((to.path === modePathMap.models || to.path === modePathMap.prompts) && !isStoredAdminUser()) {
    return modePathMap.home
  }
  if (to.path === '/' && to.hash && legacyHashPathMap[to.hash]) {
    const target = legacyHashPathMap[to.hash]
    if ((to.hash === '#/models' || to.hash === '#/prompts') && !isStoredAdminUser()) return modePathMap.home
    return target
  }
  return true
})

export default router

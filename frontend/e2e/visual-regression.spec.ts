import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test'

const apiBaseURL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8123'

async function signIn(page: Page, request: APIRequestContext, testInfo: TestInfo) {
  const email = `visual-${testInfo.project.name}-${testInfo.workerIndex}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`
  const password = process.env.E2E_TEST_PASSWORD || 'test-password-change-me'
  const registerResponse = await request.post(`${apiBaseURL}/api/auth/register`, {
    data: { name: 'Visual Tester', email, password },
  })
  expect(registerResponse.ok()).toBeTruthy()
  const session = await registerResponse.json()
  const activeUser = { name: 'Visual Tester', email, token: session.data.token }
  await page.addInitScript((user) => {
    window.localStorage.setItem('ip-case-active-user', JSON.stringify(user))
  }, activeUser)
}

test.describe('核心界面视觉截图', () => {
  test('首页工作台截图', async ({ page }, testInfo) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '今天要推进什么？' })).toBeVisible()
    await expect(page.getByTestId('home-dashboard')).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('home-dashboard.png'), fullPage: true })
  })

  test('IP 内容生产工作台截图', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/workspace/content')
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible()
    await expect(page.getByRole('region', { name: '生产任务引导' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('copilot-workbench.png'), fullPage: true })
  })

  test('IP 档案完整度页截图', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/#/sprint1')
    await expect(page.getByRole('heading', { name: 'IP 档案' })).toBeVisible()
    await expect(page.getByTestId('ip-completeness-summary')).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('ip-completeness.png'), fullPage: true })
  })

  test('生产中心任务引导区截图', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/workspace/content')
    await expect(page.getByRole('region', { name: '生产任务引导' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('production-center-guide.png'), fullPage: true })
  })

  test('公众号排版工具栏截图', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/tools/wechat')
    await expect(page.getByRole('heading', { name: '公众号排版与草稿箱发布' })).toBeVisible()
    await expect(page.getByRole('button', { name: '无序列表' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('wechat-editor-toolbar.png'), fullPage: true })
  })
})

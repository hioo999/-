import { expect, test } from '@playwright/test'

test.describe('核心界面视觉截图', () => {
  test('首页工作台截图', async ({ page }, testInfo) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '把个人 IP 打造成可持续内容资产' })).toBeVisible()
    await expect(page.getByTestId('home-dashboard')).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('home-dashboard.png'), fullPage: true })
  })

  test('IP 内容生产工作台截图', async ({ page }, testInfo) => {
    await page.goto('/#/ip')
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible()
    await expect(page.getByRole('navigation', { name: '生产中心模块' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('copilot-workbench.png'), fullPage: true })
  })

  test('IP 档案完整度页截图', async ({ page }, testInfo) => {
    await page.goto('/#/sprint1')
    await expect(page.getByRole('heading', { name: 'IP 档案' })).toBeVisible()
    await expect(page.getByTestId('ip-completeness-summary')).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('ip-completeness.png'), fullPage: true })
  })
})

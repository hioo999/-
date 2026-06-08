import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test'

const apiBaseURL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8123'

async function signIn(page: Page, request: APIRequestContext, testInfo: TestInfo, options: { isAdmin?: boolean } = {}) {
  const email = `buttons-${testInfo.project.name}-${testInfo.workerIndex}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`
  const password = process.env.E2E_TEST_PASSWORD || 'test-password-change-me'
  const registerResponse = await request.post(`${apiBaseURL}/api/auth/register`, {
    data: { name: 'Button Tester', email, password },
  })
  expect(registerResponse.ok()).toBeTruthy()
  const session = await registerResponse.json()
  const activeUser = { name: 'Button Tester', email, token: session.data.token, is_admin: options.isAdmin === true }
  await page.addInitScript((user) => {
    window.localStorage.setItem('ip-case-active-user', JSON.stringify(user))
  }, activeUser)
}

async function expectNoClientCrash(page: Page, action: () => Promise<void>) {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await action()
  expect(errors).toEqual([])
}

test.describe('全功能按钮冒烟', () => {
  test('首页卡片和顶部导航按钮可切换到对应功能', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/')

    const homeRoutes = [
      { name: '生产中心 任务化引导，统一组织项目与选题', heading: '生产中心', url: /\/workspace\/content/ },
      { name: '写公众号文章 排版预览与草稿箱发布', heading: '公众号排版与草稿箱发布', url: /\/workspace\/content\?tab=wechat/ },
      { name: '提词器 直播台本生成与在线播放', heading: '生成可直接上场的 HTML 直播台本', url: /\/publish\/teleprompter/ },
      { name: 'IP 档案 人设定位与平台策略', heading: 'IP 档案', url: /\/workspace\/ip-assets/ },
    ]

    for (const item of homeRoutes) {
      await page.goto('/')
      await page.getByTestId('home-dashboard').locator('.tool-grid').getByRole('button', { name: item.name }).click()
      await expect(page).toHaveURL(item.url)
      await expect(page.getByRole('heading', { name: item.heading })).toBeVisible()
    }

    await page.goto('/workspace/content')
    const topNav = page.getByRole('navigation', { name: '工作台一级导航' })
    await topNav.getByRole('button', { name: '概览' }).click()
    await expect(page.getByRole('heading', { name: '今天要推进什么？' })).toBeVisible()
    await topNav.getByRole('button', { name: '生产' }).click()
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible()
    await topNav.getByRole('button', { name: '发布' }).click()
    await expect(page.getByRole('heading', { name: '选择发布方式' })).toBeVisible()
  })

  test('生产中心主要按钮和模块切换可用', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/workspace/content')

    await expectNoClientCrash(page, async () => {
      await page.getByRole('button', { name: '刷新内容' }).click()
      const guide = page.getByRole('region', { name: '生产任务引导' })
      await guide.getByRole('button', { name: /做一篇公众号文章/ }).click()
      await expect(guide.getByLabel('当前任务目标平台').getByText('公众号')).toBeVisible()
      await guide.getByRole('button', { name: '用示例开始' }).click()
      await expect(page.getByRole('textbox', { name: '原文' })).toHaveValue(/企业想通过公众号建立专业信任/)
      await guide.getByRole('button', { name: /生成一条口播视频/ }).click()
      await guide.getByRole('button', { name: '用示例开始' }).click()
      await expect(page.getByRole('textbox', { name: '主题' })).toHaveValue(/个人 IP 内容创作者/)

      await page.getByRole('textbox', { name: '项目名称' }).fill(`按钮冒烟项目 ${Date.now()}`)
      await page.getByRole('textbox', { name: '账号定位' }).fill('用于按钮冒烟测试')
      await page.getByRole('button', { name: '创建项目' }).click()
      await expect(page.getByText('IP 项目已创建。')).toBeVisible()
      await page.getByRole('button', { name: '创建选题' }).click()
      await expect(page.getByText('内容选题已创建。')).toBeVisible()
      await page.getByTestId('production-save-material').click()
      await expect(page.getByText('素材已保存到当前选题资产库。')).toBeVisible()

      const moduleNav = page.getByRole('navigation', { name: '生产中心模块' })
      for (const label of ['写公众号文章', '小红书/口播', '提词器', '短视频出片', '选题总览']) {
        await moduleNav.getByRole('button', { name: new RegExp(label.replace('/', '\\/')) }).click()
      }
      await expect(page.getByRole('heading', { name: /按钮冒烟项目|等待选择内容选题|从一篇资料整理成企业 IP 长文|如何用 AI 提升个人 IP 内容生产效率/ }).first()).toBeVisible()
      const sidePanel = page.locator('.production-side-panel')
      await sidePanel.getByRole('button', { name: '提示词素材' }).click()
      await sidePanel.getByRole('button', { name: '全部' }).click()
    })
  })

  test('公众号排版工具栏按钮可写入正文并更新预览', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/tools/wechat')
    const body = page.getByRole('textbox', { name: '文章正文' })
    await body.fill('按钮冒烟正文')

    const toolbar = page.getByLabel('公众号排版工具栏')
    for (const label of ['二级标题', '小标题', '加粗', '斜体', '删除线', '高亮', '无序列表', '有序列表', '超链接', '引用卡片', '金句卡', '重点段落', '分割线', '关注引导', '推荐阅读']) {
      await toolbar.getByRole('button', { name: label }).click()
    }
    await expect(body).toHaveValue(/按钮冒烟正文|重点文字|推荐阅读|---/)
    await page.getByRole('button', { name: '发送前检查' }).click()
    await expect(page.getByText(/发送前检查|请填写|建议补充/).first()).toBeVisible()
    await page.getByRole('button', { name: '更新预览' }).click()
    await expect(page.getByTitle('公众号排版预览')).toBeVisible()
    await page.getByRole('button', { name: '复制正文' }).click()
  })

  test('提词器和直播台本按钮可完成核心交互', async ({ page }) => {
    await page.goto('/publish/teleprompter?tab=generator')
    await page.getByText('批量导入产品表').click()
    await page.getByPlaceholder('支持粘贴 Excel/CSV：产品名称,类别,直播价,原价,权益,卖点,痛点').fill('产品名称,类别,直播价,原价,权益,卖点,痛点\n测试产品,服务,99,199,限时权益,核心卖点,核心痛点')
    await page.getByRole('button', { name: '解析并替换排品' }).click()
    await expect(page.getByText('已导入 1 个产品。')).toBeVisible()
    await page.getByRole('button', { name: '开始检查' }).click()
    await expect(page.getByText('生成前检查通过。')).toBeVisible()

    await page.goto('/publish/teleprompter?tab=player')
    const editor = page.getByRole('textbox', { name: '粘贴你的口播文案...' })
    await editor.fill('第一段按钮测试\n第二段按钮测试')
    await page.getByRole('button', { name: 'Play' }).click()
    await expect(page.getByText(/倒计时|滚动中/).first()).toBeVisible()
    await page.keyboard.press('Space')
    await expect(page.getByText(/已暂停|待开始/).first()).toBeVisible()
    await page.getByRole('button', { name: '互动' }).click()
    await expect(page.getByText('互动暂停中', { exact: true })).toBeVisible()
    await page.keyboard.press('Enter')
    await page.getByRole('checkbox', { name: '镜像' }).check()
    await expect(page.getByRole('checkbox', { name: '镜像' })).toBeChecked()
    page.once('dialog', (dialog) => dialog.accept())
    await page.getByRole('button', { name: '清空' }).click()
    await expect(editor).toHaveValue('')
  })

  test('IP 档案和平台工作台核心按钮可用', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/workspace/ip-assets')
    await page.getByRole('button', { name: '新建 IP' }).click()
    await page.getByLabel('名称').fill(`按钮IP-${Date.now()}`)
    await page.getByLabel('类型').fill('专家IP')
    await page.getByLabel('商业目标').fill('验证按钮链路')
    await page.getByRole('button', { name: /^人设定位\s+\d+%$/ }).click()
    await page.getByLabel('行业').fill('AI 内容生产')
    await page.getByLabel('目标用户').fill('内容创作者')
    await page.getByRole('button', { name: /^平台配置\s+\d+%$/ }).click()
    await page.getByRole('textbox', { name: '主平台' }).fill('wechat')
    await page.getByRole('textbox', { name: '辅助平台' }).fill('xiaohongshu')
    await page.getByRole('button', { name: /^内容规则\s+\d+%$/ }).click()
    await page.getByLabel('表达语气').fill('专业直接')
    await page.getByLabel('视觉风格').fill('清爽科技')
    await page.getByLabel('转化路径').fill('内容种草 -> 私信咨询')
    for (const label of ['人设定位', '平台配置', '内容规则']) {
      await page.getByRole('button', { name: new RegExp(`^${label}\\s+\\d+%$`) }).click()
    }
    await page.getByRole('button', { name: '保存' }).click()
    await expect(page.getByText(/已创建 IP|已保存 IP 资料|已加载/)).toBeVisible()

    await page.goto('/workspace/content?tab=platform')
    const platformStudio = page.locator('.platform-studio')
    const platformTypes = platformStudio.getByLabel('平台类型')
    await platformTypes.getByRole('button', { name: '小红书创作' }).click()
    await platformTypes.getByRole('button', { name: '抖音口播' }).click()
    await platformTypes.getByRole('button', { name: '视频号口播' }).click()
    await platformStudio.getByRole('button', { name: '刷新资产' }).click()
    await platformStudio.getByRole('textbox', { name: '选题标题' }).fill('按钮平台选题')
    await platformStudio.getByRole('textbox', { name: '主题' }).fill('按钮平台主题')
    await expect(platformStudio.getByRole('button', { name: /生成视频号口播/ })).toBeEnabled()
  })
})

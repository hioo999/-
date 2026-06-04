import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test'

const apiBaseURL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8123'

async function signIn(page: Page, request: APIRequestContext, testInfo: TestInfo, options: { isAdmin?: boolean } = {}) {
  const email = `e2e-${testInfo.project.name}-${testInfo.workerIndex}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`
  const password = process.env.E2E_TEST_PASSWORD || 'test-password-change-me'
  const registerResponse = await request.post(`${apiBaseURL}/api/auth/register`, {
    data: { name: 'E2E Tester', email, password },
  })
  expect(registerResponse.ok()).toBeTruthy()
  const session = await registerResponse.json()
  const activeUser = { name: 'E2E Tester', email, token: session.data.token, is_admin: options.isAdmin === true }
  await page.addInitScript((user) => {
    window.localStorage.setItem('ip-case-active-user', JSON.stringify(user))
  }, activeUser)
  return activeUser
}

async function enterAsGuest(page: Page) {
  await page.goto('/')
}

async function enterLiveTool(page: Page) {
  await page.goto('/#/teleprompter')
  await expect(page.getByRole('textbox', { name: '粘贴你的口播文案...' })).toBeVisible()
}

test.describe('首页与内容生产冒烟', () => {
  test('游客进入首页后可见当前产品主导航', async ({ page }) => {
    await enterAsGuest(page)
    await expect(page.getByRole('heading', { name: '把个人 IP 打造成可持续内容资产' })).toBeVisible()
    await expect(page.getByTestId('home-dashboard')).toBeVisible()
    await expect(page.getByTestId('home-ip-completeness')).toBeVisible()
    await expect(page.getByTestId('home-dashboard').getByRole('button', { name: '新建 IP' })).toBeVisible()
    await expect(page.getByRole('button', { name: '在线提词器' })).toBeVisible()
  })

  test('hash 直达内容中心时展示新版生产中心模块', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/#/ip')

    await expect(page).toHaveURL(/\/workspace\/content$/)
    await expect(page.getByRole('heading', { name: '生产中心' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'IP 项目' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '内容选题', exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: '素材输入' })).toBeVisible()
    const productionGuide = page.getByRole('region', { name: '生产任务引导' })
    await expect(productionGuide.getByRole('heading', { name: '先选一个生产目标' })).toBeVisible()
    await expect(productionGuide.getByRole('button', { name: /生成一条口播视频/ })).toBeVisible()
    await expect(productionGuide.getByRole('button', { name: /做一篇公众号文章/ })).toBeVisible()
    await expect(productionGuide.getByText('当前该做：')).toBeVisible()
    const productionNav = page.getByRole('navigation', { name: '生产中心模块' })
    await expect(productionNav.getByRole('button')).toHaveCount(5)
    await expect(productionNav.getByRole('button', { name: /选题总览/ })).toBeVisible()
    await expect(productionNav.getByRole('button', { name: /公众号闭环/ })).toBeVisible()
    await expect(productionNav.getByRole('button', { name: /小红书\/口播/ })).toBeVisible()
    await expect(productionNav.getByRole('button', { name: /提词器/ })).toBeVisible()
    await expect(productionNav.getByRole('button', { name: /高级视频/ })).toBeVisible()
  })

  test('生产中心任务入口会切换推荐路径和素材输入方式', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/workspace/content')

    const productionGuide = page.getByRole('region', { name: '生产任务引导' })
    await productionGuide.getByRole('button', { name: /做一篇公众号文章/ }).click()
    await expect(productionGuide.getByLabel('推荐生产顺序').getByText('素材 -> 二创长文 -> 公众号排版 -> 草稿箱')).toBeVisible()
    await expect(productionGuide.getByLabel('当前任务目标平台').getByText('公众号')).toBeVisible()
    await expect(page.getByRole('textbox', { name: '原文' })).toBeVisible()
    await expect(productionGuide.getByRole('region', { name: '首单生产向导' })).toBeVisible()
    await productionGuide.getByRole('button', { name: '用示例开始' }).click()
    await expect(page.getByRole('textbox', { name: '选题名称' })).toHaveValue('从一篇资料整理成企业 IP 长文')
    await expect(page.getByRole('textbox', { name: '原文' })).toHaveValue(/企业想通过公众号建立专业信任/)
    await expect(productionGuide.getByText('当前该做：建立 IP 项目')).toBeVisible()

    await productionGuide.getByRole('button', { name: /准备一场直播话术/ }).click()
    await expect(productionGuide.getByLabel('推荐生产顺序').getByText('产品/活动 -> 直播脚本 -> 在线提词器')).toBeVisible()
    await expect(productionGuide.getByLabel('当前任务目标平台').getByText('抖音')).toBeVisible()
    await expect(page.getByRole('textbox', { name: '主题' })).toBeVisible()
    await productionGuide.getByRole('button', { name: '用示例开始' }).click()
    await expect(page.getByRole('textbox', { name: '选题名称' })).toHaveValue('618 活动直播开场和促单话术')
    await expect(page.getByRole('textbox', { name: '主题' })).toHaveValue(/直播主题是 618 限时活动/)
  })

  test('提示词管理页可创建分类和模板', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo, { isAdmin: true })

    const categories = [
      { id: 1, key: 'knowledge_talk', name: '知识口播', description: '干货分享', is_active: true, sort_order: 10 },
    ]
    const templates: any[] = []
    let nextTemplateId = 1

    await page.route('**/api/copilot/prompt-template-categories', async (route) => {
      const method = route.request().method()
      if (method === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: categories }) })
        return
      }
      if (method === 'POST') {
        const body = route.request().postDataJSON()
        const created = { id: categories.length + 1, is_active: true, ...body }
        categories.push(created)
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: created, message: '创建成功' }) })
      }
    })

    await page.route(/\/api\/copilot\/prompt-templates(\?.*)?$/, async (route) => {
      const method = route.request().method()
      const url = new URL(route.request().url())
      if (method === 'GET') {
        const categoryKey = url.searchParams.get('category_key') || ''
        const data = categoryKey ? templates.filter((item) => item.category_key === categoryKey && item.is_active !== false) : templates
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data }) })
        return
      }
      if (method === 'POST') {
        const body = route.request().postDataJSON()
        const created = { id: nextTemplateId++, is_active: true, ...body }
        templates.push(created)
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: created, message: '创建成功' }) })
      }
    })

    await page.route('**/api/copilot/prompt-templates/*', async (route) => {
      const id = Number(route.request().url().split('/').pop())
      const template = templates.find((item) => item.id === id)
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: template }) })
    })

    await page.goto('/admin/prompts')
    await expect(page.getByRole('heading', { name: '提示词分类与模板管理' })).toBeVisible()

    await page.getByPlaceholder('knowledge_talk').fill('qa_e2e')
    await page.getByPlaceholder('知识口播').fill('QA分类')
    await page.getByPlaceholder('说明该分类适合什么场景').fill('用于 E2E 验证')
    await page.getByRole('button', { name: '创建分类' }).click()
    await expect(page.getByText('提示词分类已创建。')).toBeVisible()
    await expect(page.getByRole('button', { name: /QA分类/ })).toBeVisible()

    await page.locator('.prompt-template-form select').selectOption('qa_e2e')
    await page.getByPlaceholder('three_part_knowledge').fill('qa_e2e_template')
    await page.getByPlaceholder('三段式干货').fill('QA口播模板')
    await page.getByPlaceholder('干货分享').fill('测试场景')
    await page.getByPlaceholder('黄金3秒钩子 -> 核心观点 -> 方法拆解 -> CTA').fill('开头 -> 内容 -> CTA')
    await page.getByPlaceholder(/开头必须有明确痛点/).fill('规则一\n规则二')
    await page.getByPlaceholder('可选。这里填写更完整的后台控制提示词正文，前端生成页不会直接展示。').fill('后台模板正文')
    await page.getByRole('button', { name: '创建模板' }).click()
    await expect(page.getByText('提示词模板已创建。')).toBeVisible()
    await page.getByRole('button', { name: '刷新' }).click()
    await expect(page.getByText('QA口播模板')).toBeVisible()
    await expect(page.getByText('结构：开头 -> 内容 -> CTA')).toBeVisible()
  })

  test('生产中心可创建项目、选题并保存素材', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.goto('/workspace/content')

    await page.getByRole('textbox', { name: '项目名称' }).fill(`E2E 内容中心项目 ${Date.now()}`)
    await page.getByRole('textbox', { name: '账号定位' }).fill('面向内容创作者的个人 IP 测试项目')
    await page.getByRole('button', { name: '创建项目' }).click()
    await expect(page.getByText('IP 项目已创建。')).toBeVisible()

    await page.getByRole('textbox', { name: '选题名称' }).fill('AI 内容中心全链路测试选题')
    await page.getByRole('button', { name: '创建选题' }).click()
    await expect(page.getByText('内容选题已创建。')).toBeVisible()

    await page.getByRole('textbox', { name: '素材标题' }).fill('E2E 主题素材')
    await page.getByRole('textbox', { name: '主题' }).fill('如何用 AI 内容中心提升个人 IP 内容生产效率')
    await page.getByRole('button', { name: '保存素材', exact: true }).click()
    await expect(page.getByText('素材已保存到当前选题资产库。')).toBeVisible()
    await expect(page.locator('.production-status-card').filter({ hasText: '资产沉淀' })).toContainText('1')
    await expect(page.locator('.asset-item').filter({ hasText: 'E2E 主题素材' })).toBeVisible()
  })

  test('多平台内容工作台可生成、编辑并进入资产沉淀视图', async ({ page, request }, testInfo) => {
    await signIn(page, request, testInfo)
    await page.route('**/api/xiaohongshu/notes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          message: '平台内容已生成',
          data: {
            content: {
              contentId: 9001,
              projectId: 1,
              topicId: 1,
              materialId: 1,
              platform: 'xiaohongshu',
              contentType: 'xiaohongshu_note',
              title: '测试小红书笔记',
              subtitle: '',
              author: '',
              summary: '测试摘要',
              coverPrompt: '蓝白科技感封面',
              coverAssetId: 0,
              imageSlots: [{ position: 'image_1', purpose: '首图', prompt: '内容中心首图' }],
              tags: ['qa', 'content-center'],
              complianceRisks: [],
              status: 'generated_with_fallback',
              version: 1,
              content: { export_text: '测试小红书正文：内容中心把素材、平台内容、任务和资产串成一条生产线。' },
              markdownSnapshot: '测试小红书正文：内容中心把素材、平台内容、任务和资产串成一条生产线。',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
            task: { taskId: 1, taskType: 'xiaohongshu_note_generate', status: 'succeeded', progress: 100 },
          },
        }),
      })
    })

    await page.goto('/workspace/content')
    await page.getByRole('navigation', { name: '生产中心模块' }).getByRole('button', { name: /小红书\/口播/ }).click()
    await expect(page.getByRole('heading', { name: '多平台内容工作台' })).toBeVisible()
    const platformStudio = page.locator('.platform-studio')
    await platformStudio.getByRole('textbox', { name: '选题标题' }).fill('测试小红书选题')
    await platformStudio.getByRole('textbox', { name: '主题' }).fill('内容中心如何提升生产效率')
    await platformStudio.getByRole('button', { name: '生成小红书创作' }).click()

    await expect(page.getByRole('heading', { name: '测试小红书笔记' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: '正文/复制内容' })).toHaveValue(/内容中心把素材、平台内容、任务和资产串成一条生产线/)
    await expect(page.getByText('xiaohongshu · xiaohongshu_note · generated_with_fallback')).toBeVisible()
  })
})

test.describe('提词器深度回归', () => {
  test('播放、暂停、互动、镜像、导入和清空可用', async ({ page }) => {
    await enterLiveTool(page)

    const editor = page.getByRole('textbox', { name: '粘贴你的口播文案...' })
    await editor.fill('第一段测试文案\n第二段测试文案')
    await expect(page.getByRole('button', { name: '第一段测试文案' })).toBeVisible()

    await page.getByRole('button', { name: 'Play' }).click()
    await expect(page.getByText(/倒计时|滚动中/).first()).toBeVisible()
    await page.keyboard.press('Space')
    await expect(page.getByText(/已暂停|待开始/).first()).toBeVisible()

    await page.getByRole('button', { name: '互动' }).click()
    await expect(page.getByText('互动暂停中', { exact: true })).toBeVisible()
    await page.keyboard.press('Enter')
    await expect(page.getByText('互动暂停中', { exact: true })).toHaveCount(0)

    const mirror = page.getByRole('checkbox', { name: '镜像' })
    await mirror.check()
    await expect(mirror).toBeChecked()
    await mirror.uncheck()
    await expect(mirror).not.toBeChecked()

    const fileChooserPromise = page.waitForEvent('filechooser')
    await page.getByRole('button', { name: '导入文件' }).click()
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles({
      name: 'teleprompter-import.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('导入文件第一段\n导入文件第二段'),
    })
    await expect(editor).toHaveValue(/导入文件第一段/)

    page.once('dialog', (dialog) => dialog.accept())
    await page.getByRole('button', { name: '清空' }).click()
    await expect(editor).toHaveValue('')
  })
})

test.describe('IP 档案主链路', () => {
  test('已登录状态下可进入 IP 档案并完成新建资料主流程', async ({ page, request }, testInfo) => {
    const email = `e2e-${testInfo.project.name}-${testInfo.workerIndex}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`
    const password = process.env.E2E_TEST_PASSWORD || 'test-password-change-me'
    const registerResponse = await request.post(`${apiBaseURL}/api/auth/register`, {
      data: { name: 'E2E Tester', email, password },
    })
    expect(registerResponse.ok()).toBeTruthy()
    const session = await registerResponse.json()

    await page.addInitScript((activeUser) => {
      window.localStorage.setItem('ip-case-active-user', JSON.stringify(activeUser))
    }, { name: 'E2E Tester', email, token: session.data.token })
    await page.goto('/#/sprint1')
    await expect(page.locator('.sprint-hero h2')).toHaveText('IP 档案')

    await page.getByRole('button', { name: '新建 IP' }).click()
    await page.getByLabel('名称').fill(`测试IP-${Date.now()}`)
    await page.getByLabel('类型').fill('专家IP')
    await page.getByLabel('商业目标').fill('建立信任并承接咨询')

    await page.getByRole('button', { name: /^人设定位\s+\d+%$/ }).click()
    await page.getByLabel('行业').fill('AI 内容生产')
    await page.getByLabel('目标用户').fill('内容创作者、运营团队和个人IP操盘手')

    await page.getByRole('button', { name: /^平台配置\s+\d+%$/ }).click()
    await page.getByLabel('主平台').fill('wechat,shipinhao')
    await page.getByLabel('辅助平台').fill('xiaohongshu,douyin')

    await page.getByRole('button', { name: /^内容规则\s+\d+%$/ }).click()
    await page.getByLabel('表达语气').fill('专业、直接、可信')
    await page.getByLabel('视觉风格').fill('清爽科技感')
    await page.getByLabel('转化路径').fill('内容种草 -> 私信咨询 -> 预约服务')
    await page.getByLabel('禁用表达').fill('绝对化承诺、夸大收益')
    await page.getByRole('button', { name: '保存' }).click()

    await expect(page.getByText(/已创建 IP|已保存 IP 资料|已加载/)).toBeVisible()
    await page.getByRole('button', { name: /^IP 列表\s+\d+%$/ }).click()
    await expect(page.getByText('AI 内容生产')).toBeVisible()

    const response = await request.get(`${apiBaseURL}/health`)
    expect(response.ok()).toBeTruthy()
  })
})

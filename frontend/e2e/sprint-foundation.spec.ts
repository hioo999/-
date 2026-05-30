import { expect, test, type Page } from '@playwright/test'

const apiBaseURL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8123'

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
    await expect(page.getByRole('heading', { name: '今天的工作台' })).toBeVisible()
    await expect(page.getByTestId('home-dashboard')).toBeVisible()
    await expect(page.getByTestId('home-ip-completeness')).toBeVisible()
    await expect(page.getByTestId('home-dashboard').getByRole('button', { name: '新建 IP' })).toBeVisible()
    await expect(page.getByRole('button', { name: '在线提词器' })).toBeVisible()
  })

  test('hash 直达 IP 内容工作台时隐藏根壳层并展示一级模块', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('ip-case-active-user', JSON.stringify({ name: 'E2E Tester', email: 'e2e@example.com', token: 'e2e-token' }))
    })
    await page.goto('/#/ip')

    await expect(page.getByRole('heading', { name: 'IP 全案内容生产工作台' })).toBeVisible()
    await expect(page.locator('.shell-topbar')).toHaveCount(0)
    await expect(page.locator('.top-nav')).toHaveCount(0)
    await expect(page.locator('.workspace-metrics')).toHaveCount(0)
    await expect(page.getByText('内容生产', { exact: true })).toHaveCount(0)
    await expect(page.getByText('账户', { exact: true })).toHaveCount(0)
    await expect(page.locator('.content-module-section')).toHaveCount(5)
    await expect(page.getByRole('heading', { name: '内容提取' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '短视频工作流' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '选题策略' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '口播文案' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '发布全案' })).toBeVisible()
  })

  test('提示词管理页可创建分类和模板', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('ip-case-active-user', JSON.stringify({ name: 'E2E Tester', email: 'e2e@example.com', token: 'e2e-token' }))
    })

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

    await page.goto('/#/prompts')
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

  test('内容生产页完成文本提取并生成全案主链路', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('ip-case-active-user', JSON.stringify({ name: 'E2E Tester', email: 'e2e@example.com', token: 'e2e-token' }))
    })
    await page.route('**/api/copilot/generate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            history_id: 1,
            script_content: '测试口播文案：AI 工具能把选题、脚本和发布计划串成一条稳定生产线。',
            video_prompts: '测试分镜提示词：竖屏 9:16，展示内容创作者使用 AI 工作台规划选题。',
            cover_prompt: '测试封面提示词：标题突出 AI 内容生产效率，科技感蓝白配色。',
          },
        }),
      })
    })

    const sourceText = 'AI 工具如何提升短视频选题效率。目标用户是内容创作者和运营团队，需要稳定产出选题、脚本和发布计划。'
    const longSourceText = Array.from({ length: 140 }, () => sourceText).join('\n')

    await page.goto('/#/ip')
    await page.getByRole('button', { name: '文本' }).click()
    await page.getByPlaceholder('直接粘贴文章内容...').fill(longSourceText)
    await page.getByRole('button', { name: '提取核心内容' }).click()

    await expect(page.locator('pre.content-text').first()).toContainText('AI 工具如何提升短视频选题效率')
    const generateButton = page.locator('.overview-actions').getByRole('button', { name: '生成全案' })
    await expect(generateButton).toBeEnabled()

    await generateButton.click()
    await expect(page.getByText('测试口播文案：AI 工具能把选题、脚本和发布计划串成一条稳定生产线。')).toBeVisible()
    await expect(page.getByText('发布辅助素材')).toBeVisible()
    await expect(page.getByText('内容输出状态：待输出')).toBeVisible()
    await expect(page.getByText('已生成')).toBeVisible()
  })

  test('内容生产页完成发布全案与发布质检闭环', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('ip-case-active-user', JSON.stringify({ name: 'E2E Tester', email: 'e2e@example.com', token: 'e2e-token' }))
    })
    await page.route('**/api/copilot/generate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            history_id: 1,
            script_content: '测试口播文案：AI 内容工作台帮助团队稳定生成选题、脚本和发布方案。',
            video_prompts: '测试分镜提示词：内容创作者在工作台中查看选题与发布计划。',
            cover_prompt: '测试封面提示词：AI 内容生产工作台，高效、稳定、可复用。',
          },
        }),
      })
    })
    await page.route('**/api/copilot/strategy/publish-package', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            short_titles: ['AI 内容生产效率翻倍', '选题脚本一条线搞定'],
            caption: '用 AI 工作台把选题、脚本、发布文案串起来，减少重复沟通。',
            comment_pin: '想要内容生产流程模板，评论区打“模板”。',
            private_message_reply: '已收到，发你一份内容生产流程模板。',
          },
        }),
      })
    })
    await page.route('**/api/copilot/strategy/quality-check', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            total_score: 92,
            optimized_opening: '别再手动拼选题、脚本和发布文案了。',
            issues: ['CTA 可再明确一点'],
            suggestions: ['首屏突出节省时间和复用流程'],
          },
        }),
      })
    })

    const sourceText = 'AI 内容工作台如何提升团队内容生产效率。目标用户是内容负责人和运营团队，需要稳定生成选题、脚本和发布方案。'
    const longSourceText = Array.from({ length: 140 }, () => sourceText).join('\n')

    await page.goto('/#/ip')
    await page.getByRole('button', { name: '文本' }).click()
    await page.getByPlaceholder('直接粘贴文章内容...').fill(longSourceText)
    await page.getByRole('button', { name: '提取核心内容' }).click()
    await expect(page.locator('pre.content-text').first()).toContainText('AI 内容工作台如何提升团队内容生产效率')
    await page.locator('.overview-actions').getByRole('button', { name: '生成全案' }).click()
    await expect(page.getByText('测试口播文案：AI 内容工作台帮助团队稳定生成选题、脚本和发布方案。')).toBeVisible()

    await page.getByRole('button', { name: '发布全案', exact: true }).click()
    await expect(page.getByText('AI 内容生产效率翻倍 / 选题脚本一条线搞定')).toBeVisible()
    await expect(page.getByText('用 AI 工作台把选题、脚本、发布文案串起来，减少重复沟通。')).toBeVisible()
    await expect(page.getByText('想要内容生产流程模板，评论区打“模板”。')).toBeVisible()
    await expect(page.getByText('已收到，发你一份内容生产流程模板。')).toBeVisible()
    await expect(page.getByText('内容输出状态：已输出')).toBeVisible()

    await page.getByRole('button', { name: '发布质检', exact: true }).click()
    await expect(page.getByText('总分：92')).toBeVisible()
    await expect(page.getByText('建议开头：别再手动拼选题、脚本和发布文案了。')).toBeVisible()
    await expect(page.getByText('问题：CTA 可再明确一点')).toBeVisible()
    await expect(page.getByText('建议：首屏突出节省时间和复用流程')).toBeVisible()
  })

  test('短视频工作流可识别、展示步骤并应用到内容模块', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('ip-case-active-user', JSON.stringify({ name: 'E2E Tester', email: 'e2e@example.com', token: 'e2e-token' }))
    })
    await page.route('**/api/short-video/workflow', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          data: {
            intent: {
              intent: 'product_tvc',
              label: '产品TVC',
              confidence: 0.93,
              matched_keywords: ['饮料', '15秒', '小红书'],
              source: 'mock',
            },
            workflow: {
              key: 'product_tvc',
              label: '产品TVC广告短视频',
              recommended_command: '/product-tvc-video',
              template_doc: 'product-tvc-video/SKILL.md',
            },
            variables: {
              主体名称: '无糖杏仁甘露',
              视频主题: '15秒清爽饮品种草',
            },
            steps: [
              {
                key: 'script',
                label: '口播脚本',
                description: '生成用于提词器跟读的口播脚本',
                prompt: '短视频工作流应用脚本：无糖杏仁甘露，0糖也能喝出高级清爽感。',
              },
              {
                key: 'storyboard',
                label: '九宫格分镜',
                description: '生成九宫格广告分镜提示词',
                prompt: '短视频工作流分镜：冰块、杏仁露、东方包装、清爽转场。',
              },
            ],
            questions: ['是否需要强调无糖卖点？'],
            next_actions: ['应用口播脚本到口播文案模块', '导出工作流归档'],
          },
        }),
      })
    })

    await page.goto('/#/ip')
    await page.getByPlaceholder('例：我上传的是一款无糖杏仁甘露饮料，做15秒小红书短视频，风格高级清爽').fill(
      '无糖杏仁甘露饮料，做 15 秒小红书产品 TVC，风格高级清爽。'
    )
    await page.getByPlaceholder('例：无糖杏仁甘露 / 布偶猫 / 张老师IP').fill('无糖杏仁甘露')
    await page.getByRole('button', { name: '自动识别并生成工作流' }).click()

    await expect(page.locator('.intent-pill').getByText('产品TVC', { exact: true })).toBeVisible()
    await expect(page.getByText('置信度 93%')).toBeVisible()
    await expect(page.getByText('产品TVC广告短视频')).toBeVisible()
    await expect(page.getByText('是否需要强调无糖卖点？')).toBeVisible()
    await expect(page.locator('.workflow-step-card strong').getByText('口播脚本', { exact: true })).toBeVisible()
    await expect(page.locator('.workflow-step-card strong').getByText('九宫格分镜', { exact: true })).toBeVisible()

    await page.locator('.workflow-step-card').filter({ hasText: '口播脚本' }).getByRole('button', { name: '应用' }).click()
    await expect(page.locator('pre.content-text').filter({ hasText: '短视频工作流应用脚本：无糖杏仁甘露，0糖也能喝出高级清爽感。' })).toBeVisible()
    await expect(page.locator('.overview-metrics article').filter({ hasText: '脚本文案' })).toContainText('已生成')
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

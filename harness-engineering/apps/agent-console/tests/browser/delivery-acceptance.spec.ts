import { expect, test } from '@playwright/test';

const requiredTexts = [
  '知识库工作台',
  '当前页面运行在本地 Agent',
  '平台不可见',
  '新建知识库'
];

const forbiddenTexts = [
  'sk-',
  'Secret Case Name',
  'secret-contract',
  '张三',
  '李四',
  '/Users/alice',
  'AGENT_SECRET_KEY=real-secret',
  'platform_password',
  'agent_password'
];

test('knowledge workspace opens without sensitive samples', async ({ page }) => {
  await page.route('**/api/agent/setup/status', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'ok', data: { setup_required: false, user_count: 1, default_admin_password: false } })
    });
  });
  await page.route('**/api/agent/auth/me', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'ok',
        data: { id: 'smoke-user', account: 'admin', name: '本地管理员', role: 'admin' }
      })
    });
  });
  await page.route('**/api/agent/knowledge-bases', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'ok', data: [] })
    });
  });
  await page.route('**/api/agent/users', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'ok', data: [{ id: 'smoke-user', account: 'admin', name: '本地管理员', role: 'admin', status: 'active' }] })
    });
  });
  await page.route('**/api/agent/data-sources', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'ok', data: [] })
    });
  });
  await page.route('**/api/agent/model-configs', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'ok', data: [] })
    });
  });

  await page.addInitScript(() => {
    window.localStorage.setItem('v41_agent_token', 'smoke-token');
  });

  await page.goto('/');
  await expect(page.getByText('知识库工作台').first()).toBeVisible();

  const body = page.locator('body');
  for (const text of requiredTexts) {
    await expect(body).toContainText(text);
  }

  await page.goto('/#/sources');
  await expect(body).toContainText('本地目录配置');
  await page.goto('/#/models');
  await expect(body).toContainText('API Key 仅本地保存');

  const bodyText = await body.innerText();
  for (const text of forbiddenTexts) {
    expect(bodyText).not.toContain(text);
  }
});

test('knowledge review controls show publish gates and logs', async ({ page }) => {
  const kb = {
    id: 'kb_smoke_review',
    type: 'team',
    name: '模板审核库',
    description: '交付 smoke 使用的审核库',
    owner_type: 'team',
    owner_id: 'smoke-user',
    knowledge_type: 'template',
    business_domain: null,
    legal_domain: null,
    jurisdiction: null,
    client_id: null,
    matter_id: null,
    department_id: null,
    project_team_id: null,
    ethical_wall_enabled: false,
    review_status: 'pending_review',
    confidentiality_level: 'internal',
    maintainer_id: null,
    expires_at: null,
    ai_usage_policy: 'search_only',
    citation_priority: 0,
    ai_enabled: true,
    default_permission_policy: 'private',
    status: 'active',
    current_user_role: 'admin',
    created_by: 'smoke-user',
    created_at: 1,
    updated_at: 1
  };

  await page.route('**/api/agent/setup/status', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, message: 'ok', data: { setup_required: false, user_count: 1, default_admin_password: false } }) });
  });
  await page.route('**/api/agent/auth/me', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, message: 'ok', data: { id: 'smoke-user', account: 'admin', name: '本地管理员', role: 'agent_admin' } }) });
  });
  await page.route('**/api/agent/users', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, message: 'ok', data: [{ id: 'smoke-user', account: 'admin', name: '本地管理员', role: 'agent_admin', status: 'active' }] }) });
  });
  await page.route('**/api/agent/knowledge-bases/kb_smoke_review/tree**', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, message: 'ok', data: { knowledge_base: kb, folders: [], files: [] } }) });
  });
  await page.route('**/api/agent/knowledge-bases/kb_smoke_review/review-logs', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, message: 'ok', data: [{ id: 'log_1', knowledge_base_id: kb.id, action: 'submit_review', from_status: 'draft', to_status: 'pending_review', operator_id: 'smoke-user', comment: null, created_at: 1 }] })
    });
  });
  await page.route('**/api/agent/knowledge-bases', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, message: 'ok', data: [kb] }) });
  });
  await page.route('**/api/agent/chats**', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, message: 'ok', data: [] }) });
  });

  await page.addInitScript(() => {
    window.localStorage.setItem('v41_agent_token', 'smoke-token');
  });

  await page.goto('/');
  const body = page.locator('body');
  await expect(body).toContainText('审核发布与治理');
  await expect(body).toContainText('高影响知识发布前仍有缺失项');
  await expect(body).toContainText('发布');
  await expect(body).toContainText('退回');
  await expect(body).toContainText('审核日志（1）');
});

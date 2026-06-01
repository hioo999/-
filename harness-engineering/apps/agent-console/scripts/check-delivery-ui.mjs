import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();

function read(path) {
  return readFileSync(join(root, path), 'utf8');
}

function assertIncludes(source, needle, message) {
  if (!source.includes(needle)) {
    throw new Error(message);
  }
}

function assertNotIncludes(source, needle, message) {
  if (source.includes(needle)) {
    throw new Error(message);
  }
}

const app = read('src/App.tsx');
const routes = read('src/routes/index.tsx');
const deliveryPage = read('src/pages/DeliveryAcceptancePage.tsx');

assertIncludes(app, "{ key: 'delivery', label: '交付验收' }", 'Agent menu must expose delivery acceptance entry');
assertIncludes(routes, "'delivery'", 'RouteKey must include delivery route');
assertIncludes(routes, '<DeliveryAcceptancePage />', 'delivery route must render DeliveryAcceptancePage');

const requiredDeliveryTexts = [
  'metadata-only',
  '平台不可见',
  '不展示案件',
  '一键导出交付 bundle',
  '复验完整 bundle',
  'bash scripts/verify-mvp.sh',
  'harness-engineering-delivery.tar.gz.sha256',
  'delivery-acceptance-report.json',
  'delivery-bundle-manifest.json'
];

for (const text of requiredDeliveryTexts) {
  assertIncludes(deliveryPage, text, `DeliveryAcceptancePage missing required UI copy: ${text}`);
}

const forbiddenSourceTexts = [
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

for (const text of forbiddenSourceTexts) {
  assertNotIncludes(deliveryPage, text, `DeliveryAcceptancePage must not include sensitive sample: ${text}`);
}

if (existsSync(join(root, 'dist'))) {
  const assetDir = join(root, 'dist', 'assets');
  const files = [join(root, 'dist', 'index.html')];
  if (existsSync(assetDir)) {
    for (const file of readdirSync(assetDir)) {
      if (file.endsWith('.js') || file.endsWith('.css')) {
        files.push(join(assetDir, file));
      }
    }
  }
  const bundleText = files.map((file) => readFileSync(file, 'utf8')).join('\n');
  for (const text of ['Secret Case Name', 'secret-contract', '/Users/alice', 'AGENT_SECRET_KEY=real-secret']) {
    assertNotIncludes(bundleText, text, `built assets must not include sensitive sample: ${text}`);
  }
  for (const text of ['交付验收', 'metadata-only', '平台不可见']) {
    assertIncludes(bundleText, text, `built assets missing delivery UI copy: ${text}`);
  }
}

console.log('agent-console delivery UI smoke check passed');

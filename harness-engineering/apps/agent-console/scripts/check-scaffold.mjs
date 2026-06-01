import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const requiredFiles = [
  'package.json',
  'index.html',
  'vite.config.ts',
  'src/main.tsx',
  'src/App.tsx',
  'src/services/agentClient.ts',
  'src/components/LocalOnlyBanner.tsx',
  'src/pages/LoginPage.tsx',
  'src/pages/AgentStatusPage.tsx',
  'src/pages/DataSourcesPage.tsx',
  'src/pages/ModelConfigPage.tsx',
  'src/pages/TasksPage.tsx',
  'src/pages/DeliveryAcceptancePage.tsx',
  'src/pages/CasesPage.tsx',
  'src/pages/RagChatPage.tsx'
];

for (const file of requiredFiles) {
  if (!existsSync(join(root, file))) {
    throw new Error(`missing required scaffold file: ${file}`);
  }
}

const client = readFileSync(join(root, 'src/services/agentClient.ts'), 'utf8');
if (client.includes('/api/platform')) {
  throw new Error('agent console client must not call platform APIs');
}

const banner = readFileSync(join(root, 'src/components/LocalOnlyBanner.tsx'), 'utf8');
if (!banner.includes('平台不可见')) {
  throw new Error('local-only banner must explain platform invisibility');
}

const deliveryPage = readFileSync(join(root, 'src/pages/DeliveryAcceptancePage.tsx'), 'utf8');
if (!deliveryPage.includes('metadata-only') || !deliveryPage.includes('不展示案件')) {
  throw new Error('delivery acceptance page must explain metadata-only and business-data invisibility');
}

console.log('agent-console scaffold check passed');

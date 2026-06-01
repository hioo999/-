import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const readme = readFileSync(join(root, 'README.md'), 'utf8');

const allowedPages = ['Login', 'Organizations', 'Licenses', 'Agents', 'Desensitized health', 'Platform audit logs'];
const allowedFallbacks = {
  Organizations: '组织',
  Licenses: '授权',
  Agents: 'Agent',
  'Desensitized health': '脱敏健康',
  'Platform audit logs': '平台审计'
};
for (const text of allowedPages) {
  const fallback = allowedFallbacks[text];
  if (!readme.includes(text) && (!fallback || !readme.includes(fallback))) {
    throw new Error(`platform console README missing allowed control-plane page: ${text}`);
  }
}

const forbiddenPages = ['Cases', 'Files', 'Document preview', 'RAG chat', 'Prompt viewer', 'Chat history', 'Evidence', 'Drafts', 'Vector search'];
for (const text of forbiddenPages) {
  if (!readme.includes(text)) {
    throw new Error(`platform console README must explicitly forbid: ${text}`);
  }
}

const forbiddenBusinessUi = ['案件工作台', '文件预览', '案件问答', '文书起草', '向量检索'];
for (const text of forbiddenBusinessUi) {
  if (readme.includes(`| ${text}`)) {
    throw new Error(`platform console must not list business UI page: ${text}`);
  }
}

console.log('platform-console invisibility UI smoke check passed');

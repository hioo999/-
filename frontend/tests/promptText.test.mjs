import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'

const source = readFileSync(new URL('../src/utils/promptText.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2020,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText
const modulePath = join(tmpdir(), `promptText-${Date.now()}.mjs`)
writeFileSync(modulePath, compiled)

const {
  hashPromptContent,
  looksLikePromptTitle,
  splitPromptTextBySpeechBoundary,
} = await import(pathToFileURL(modulePath).href)

assert.deepEqual(splitPromptTextBySpeechBoundary('模型用 opus4.8 生成。下一句开始。'), [
  '模型用 opus4.8 生成。',
  '下一句开始。',
])

assert.deepEqual(splitPromptTextBySpeechBoundary('调用 GPT-4.1，强度 1.5x。完成。'), [
  '调用 GPT-4.1，强度 1.5x。',
  '完成。',
])

assert.deepEqual(splitPromptTextBySpeechBoundary('参考 https://example.com/a.b/c.png。继续。'), [
  '参考 https://example.com/a.b/c.png。',
  '继续。',
])

assert.equal(looksLikePromptTitle('1. 主体清理'), true)
assert.equal(looksLikePromptTitle('1、主体清理'), true)
assert.equal(looksLikePromptTitle('第1步：主体清理'), true)
assert.equal(looksLikePromptTitle('1.5倍速度'), false)
assert.equal(looksLikePromptTitle('opus4.8'), false)
assert.equal(hashPromptContent('同一个提示词'), hashPromptContent('同一个提示词'))
assert.notEqual(hashPromptContent('提示词 A'), hashPromptContent('提示词 B'))

console.log('promptText tests passed')

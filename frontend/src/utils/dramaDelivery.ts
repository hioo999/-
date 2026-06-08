import type { ReversalDramaResult } from '../api'

/** 从分镜表提取适合提词器朗读的台词文本。 */
export function scenesToTeleprompterText(result: ReversalDramaResult): string {
  const title = result.overview?.title || '短剧脚本'
  const lines: string[] = [title, '']

  for (const scene of result.scenes || []) {
    const dialogue = String(scene.dialogue || '').trim()
    if (dialogue && dialogue !== '…' && dialogue !== '...') {
      lines.push(dialogue)
    }
  }

  if (result.ending_subtitle) {
    lines.push('', result.ending_subtitle)
  }

  return lines.join('\n').trim()
}

export function splitPromptTextBySpeechBoundary(text: string) {
  const segments: string[] = []
  let current = ''

  Array.from(text.replace(/\r\n?/g, '\n')).forEach((char, index, chars) => {
    if (char === '\n') {
      if (current.trim()) segments.push(current.trim())
      current = ''
      return
    }

    current += char
    if (isSpeechBoundary(chars, index)) {
      if (current.trim()) segments.push(current.trim())
      current = ''
    }
  })

  if (current.trim()) segments.push(current.trim())
  return segments
}

export function isSpeechBoundary(chars: string[], index: number) {
  const char = chars[index]
  if ('。！？!?；;'.includes(char)) return true
  if (char !== '.') return false

  const previous = chars[index - 1] || ''
  const next = chars[index + 1] || ''
  if (isAsciiDigit(previous) && isAsciiDigit(next)) return false
  return !next || isWhitespace(next)
}

export function looksLikePromptTitle(line: string) {
  const trimmed = line.trim()
  if (!trimmed) return false
  if (/^#{1,6}\s+/.test(trimmed) || /^【.+】$/.test(trimmed)) return true
  if (/^\d+、\s*\S+/.test(trimmed)) return true
  if (/^\d+\.\s+\S+/.test(trimmed)) return true
  if (/^第[\d一二三四五六七八九十]+(?:步|阶段|章|节)?[：:、]\s*\S+/.test(trimmed)) return true
  return trimmed.length <= 14 && !/[.。！？!?；;，,]/.test(trimmed)
}

export function hashPromptContent(content: string) {
  let hash = 5381
  for (const char of Array.from(content.trim())) {
    hash = ((hash << 5) + hash) ^ char.codePointAt(0)!
  }
  return (hash >>> 0).toString(36)
}

function isAsciiDigit(char: string) {
  return /^[0-9]$/.test(char)
}

function isWhitespace(char: string) {
  return /\s/.test(char)
}

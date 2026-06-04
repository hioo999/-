<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  createTeleprompterDraft,
  deleteTeleprompterDraft,
  getRecentTeleprompterDraft,
  getTeleprompterScript,
  getTeleprompterVideoPackageScript,
  getTeleprompterDraft,
  listTeleprompterDrafts,
  reportTeleprompterEvent,
  updateTeleprompterDraft,
  type TeleprompterCloudSettings,
  type TeleprompterDraft,
  type TeleprompterDraftPayload,
  type TeleprompterDraftSummary,
} from '../api/teleprompter.api'
import { looksLikePromptTitle, splitPromptTextBySpeechBoundary } from '../utils/promptText'

const STORAGE_KEY = 'ip-case-teleprompter-state'
const DOC_IMPORT_ACCEPT = '.txt,.md,.doc,.docx,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const SUPPORTED_IMPORT_EXTENSIONS = ['txt', 'md', 'doc', 'docx']
const MAX_SCRIPT_LENGTH = 30000
const SPOKEN_FILLERS = ['嗯', '啊', '呃', '额', '这个', '那个', '然后', '就是', '就是说', '其实', '大家', '那么', '所以', '呢', '吧', '哈']
const FINE_SCROLL_STEP = 60
const REMOTE_PAGE_RATIO = 0.58
const SPEED_STEP = 4
const MAX_PROMPT_LINE_LENGTH = 50
const REMOTE_SPEED_REPEAT_INTERVAL = 180
const REMOTE_PREVIOUS_KEYS = new Set(['PageUp', 'MediaTrackPrevious', 'BrowserBack'])
const REMOTE_NEXT_KEYS = new Set(['PageDown', 'MediaTrackNext', 'BrowserForward'])
const SPEED_DOWN_KEYS = new Set(['-', '_', 'AudioVolumeDown', 'VolumeDown'])
const SPEED_UP_KEYS = new Set(['+', '=', 'AudioVolumeUp', 'VolumeUp'])
const PLAY_TOGGLE_KEYS = new Set(['MediaPlayPause', 'Play', 'Pause'])

interface SpeechRecognitionResultLike {
  readonly isFinal: boolean
  readonly 0: { transcript: string }
}

interface SpeechRecognitionEventLike extends Event {
  readonly resultIndex: number
  readonly results: SpeechRecognitionResultLike[]
}

interface SpeechRecognitionErrorEventLike extends Event {
  readonly error: string
}

interface SpeechRecognitionLike extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

interface SpeechRecognitionConstructorLike {
  new (): SpeechRecognitionLike
}

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: SpeechRecognitionConstructorLike
  webkitSpeechRecognition?: SpeechRecognitionConstructorLike
}

type ThemeKey = 'dark' | 'warm' | 'contrast'

interface SavedTeleprompterState {
  title: string
  text: string
  speed: number
  fontSize: number
  lineHeight: number
  theme: ThemeKey
  mirror: boolean
  countdownEnabled: boolean
  currentScrollPosition: number
  updatedAt: string
}

interface TeleprompterUser {
  name: string
  email: string
  token?: string
  isGuest?: boolean
}

const props = defineProps<{
  initialText?: string
  currentUser?: TeleprompterUser
}>()

const defaultText = `欢迎使用在线提词器。

在左侧输入或上传你的口播文案，点击“开始”后，文案会按照设定速度自动滚动。

操作提示：
空格：播放 / 暂停
鼠标点击提词区域：播放 / 暂停
滚轮或方向键：上下微调文案位置
翻页笔上一页 / 下一页：上翻 / 下翻一屏
长按翻页笔上一页 / 下一页：减慢 / 加快滚动速度
+ / - 或音量键：调整滚动速度
Esc：退出全屏或暂停播放`

const scriptTitle = ref('未命名提词稿')
const scriptText = ref(defaultText)
const speed = ref(48)
const fontSize = ref(52)
const lineHeight = ref(1.65)
const theme = ref<ThemeKey>('dark')
const mirror = ref(false)
const countdownEnabled = ref(true)
const countdown = ref(0)
const isPlaying = ref(false)
const isFullscreen = ref(false)
const scrollProgress = ref(0)
const message = ref('')
const isVoiceFollowing = ref(false)
const isInteractionPaused = ref(false)
const temporaryInteractionNote = ref('')
const isFinishConfirmOpen = ref(false)
const finishSummary = ref<{ durationSeconds: number; completionRate: number; wordCount: number } | null>(null)
const sessionStartedAt = ref<number | null>(null)
const lastDraftSavedAt = ref('')
const cloudDraftId = ref<number | null>(null)
const isCloudDraftLoading = ref(false)
const isCloudDraftSaving = ref(false)
const isSourceScriptLoading = ref(false)
const cloudDraftError = ref('')
const cloudDrafts = ref<TeleprompterDraftSummary[]>([])
const isDraftListLoading = ref(false)
const draftListError = ref('')
const voiceSupported = ref(false)
const voiceStatus = ref('开启语音跟读前，请先允许麦克风权限。')
const currentSegmentIndex = ref(-1)
const lastTranscript = ref('')
const pendingVoiceMatchIndex = ref(-1)
const pendingVoiceMatchCount = ref(0)

const viewportRef = ref<HTMLElement | null>(null)
const editorRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const runtimeSpeedRef = ref<HTMLElement | null>(null)

const runtimeSpeedOffset = ref({ x: 0, y: 0 })
const isDraggingRuntimeSpeed = ref(false)
const isDraggingViewport = ref(false)

let frameId: number | null = null
let lastFrameTime = 0
let countdownTimer: number | null = null
let progressFrameId: number | null = null
let speechRecognition: SpeechRecognitionLike | null = null
let shouldRestartRecognition = false
let lastRemoteSpeedRepeatAt = 0
let draftSaveTimer: number | null = null
let cloudSaveTimer: number | null = null
let pendingRestoreScrollTop: number | null = null
let runtimeSpeedDragState: {
  pointerId: number
  startX: number
  startY: number
  originX: number
  originY: number
  minX: number
  maxX: number
  minY: number
  maxY: number
  moved: boolean
} | null = null
let viewportDragState: {
  pointerId: number
  startY: number
  startTop: number
  moved: boolean
} | null = null
let shouldSuppressViewportClick = false

interface PromptSegment {
  index: number
  text: string
  normalized: string
}

interface PromptSection {
  index: number
  title: string
  segmentIndex: number
}

const wordsCount = computed(() => {
  const englishWords = scriptText.value.match(/[A-Za-z0-9]+/g)?.length ?? 0
  const chineseChars = scriptText.value.match(/[\u4e00-\u9fa5]/g)?.length ?? 0
  return englishWords + chineseChars
})

const scriptLength = computed(() => Array.from(scriptText.value).length)

const isScriptTooLong = computed(() => scriptLength.value > MAX_SCRIPT_LENGTH)

const estimatedMinutes = computed(() => Math.max(1, Math.ceil(wordsCount.value / 320)))

const progressLabel = computed(() => `${Math.round(scrollProgress.value)}%`)

const isCloudDraftEnabled = computed(() => Boolean(props.currentUser?.token && !props.currentUser?.isGuest))

const saveStatusLabel = computed(() => {
  if (isSourceScriptLoading.value) return '正在加载来源脚本...'
  if (isCloudDraftLoading.value) return '正在加载云端草稿...'
  if (isCloudDraftSaving.value) return '正在保存云端草稿...'
  if (cloudDraftError.value) return `${isCloudDraftEnabled.value ? '云端保存失败' : '本地模式'}：${cloudDraftError.value}`
  if (isCloudDraftEnabled.value && cloudDraftId.value) return lastDraftSavedAt.value ? `已云端保存 ${lastDraftSavedAt.value}` : '云端草稿待保存'
  if (isCloudDraftEnabled.value) return lastDraftSavedAt.value ? `已云端保存 ${lastDraftSavedAt.value}` : '云端草稿待创建'
  return lastDraftSavedAt.value ? `已本地保存 ${lastDraftSavedAt.value}` : '游客模式：本地草稿待保存'
})

const promptSegments = computed<PromptSegment[]>(() => splitPromptSegments(scriptText.value))

const promptSections = computed<PromptSection[]>(() => getPromptSections(scriptText.value, promptSegments.value))

const currentSectionIndex = computed(() => {
  if (currentSegmentIndex.value < 0) return -1
  let activeSection = -1
  for (const section of promptSections.value) {
    if (section.segmentIndex <= currentSegmentIndex.value) activeSection = section.index
  }
  return activeSection
})

const finishDurationLabel = computed(() => {
  if (!finishSummary.value) return '0:00'
  const minutes = Math.floor(finishSummary.value.durationSeconds / 60)
  const seconds = finishSummary.value.durationSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
})

const themeClass = computed(() => `theme-${theme.value}`)

const displayStyle = computed(() => ({
  fontSize: `${fontSize.value}px`,
  lineHeight: String(lineHeight.value),
  transform: mirror.value ? 'scaleX(-1)' : 'none',
}))

const runtimeSpeedStyle = computed(() => ({
  transform: `translate(${runtimeSpeedOffset.value.x}px, ${runtimeSpeedOffset.value.y}px)`,
}))

watch(scriptText, () => {
  currentSegmentIndex.value = -1
  lastTranscript.value = ''
  pendingVoiceMatchIndex.value = -1
  pendingVoiceMatchCount.value = 0
})

watch(
  () => props.initialText,
  (initialText) => {
    if (!initialText?.trim() || initialText === scriptText.value) return
    scriptText.value = initialText
    resetContentPosition('viewport')
    message.value = '已载入当前内容，可开启语音跟读。'
  }
)

watch(
  [scriptTitle, scriptText, speed, fontSize, lineHeight, theme, mirror, countdownEnabled],
  () => scheduleDraftSave(),
  { deep: false }
)

watch(scriptLength, (length) => {
  if (length > MAX_SCRIPT_LENGTH) {
    message.value = `脚本已超过 ${MAX_SCRIPT_LENGTH} 字，请拆分后再开始提词。`
  }
})

function scheduleDraftSave() {
  if (draftSaveTimer !== null) window.clearTimeout(draftSaveTimer)
  draftSaveTimer = window.setTimeout(saveDraftState, 180)
}

function saveDraftState() {
  draftSaveTimer = null
  const viewport = viewportRef.value
  const state: SavedTeleprompterState = {
    title: scriptTitle.value.trim() || '未命名提词稿',
    text: scriptText.value,
    speed: speed.value,
    fontSize: fontSize.value,
    lineHeight: lineHeight.value,
    theme: theme.value,
    mirror: mirror.value,
    countdownEnabled: countdownEnabled.value,
    currentScrollPosition: viewport?.scrollTop ?? 0,
    updatedAt: new Date().toISOString(),
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    lastDraftSavedAt.value = formatTime(state.updatedAt)
  } catch {
    message.value = '本地保存失败，请复制文案备份。'
  }

  scheduleCloudDraftSave()
}

function scheduleCloudDraftSave() {
  if (!isCloudDraftEnabled.value || isCloudDraftLoading.value || !scriptText.value.trim() || isScriptTooLong.value) return
  if (cloudSaveTimer !== null) window.clearTimeout(cloudSaveTimer)
  cloudSaveTimer = window.setTimeout(() => {
    saveCloudDraft()
  }, 900)
}

async function saveCloudDraft() {
  if (!isCloudDraftEnabled.value || !scriptText.value.trim() || isScriptTooLong.value) return
  cloudSaveTimer = null
  isCloudDraftSaving.value = true
  cloudDraftError.value = ''
  try {
    const payload = buildCloudDraftPayload()
    const res = cloudDraftId.value
      ? await updateTeleprompterDraft(cloudDraftId.value, payload)
      : await createTeleprompterDraft(payload)
    cloudDraftId.value = res.data.draftId
    lastDraftSavedAt.value = res.data.updatedAt ? formatTime(res.data.updatedAt) : formatTime(new Date().toISOString())
    refreshCloudDrafts(false)
  } catch (err: any) {
    cloudDraftError.value = err?.response?.data?.detail || err?.message || '已回退到本地草稿'
  } finally {
    isCloudDraftSaving.value = false
  }
}

async function refreshCloudDrafts(showLoading = true) {
  if (!isCloudDraftEnabled.value) return
  if (showLoading) isDraftListLoading.value = true
  draftListError.value = ''
  try {
    const res = await listTeleprompterDrafts({ page: 1, pageSize: 8 })
    cloudDrafts.value = res.data.items || []
  } catch (err: any) {
    cloudDrafts.value = []
    draftListError.value = getCloudDraftErrorMessage(err, '草稿列表加载失败')
  } finally {
    if (showLoading) isDraftListLoading.value = false
  }
}

async function openCloudDraft(draftId: number) {
  if (!isCloudDraftEnabled.value) return
  if (cloudDraftId.value === draftId && !window.confirm('当前已打开该草稿，是否重新加载云端版本？')) return
  isCloudDraftLoading.value = true
  cloudDraftError.value = ''
  try {
    const detail = await getTeleprompterDraft(draftId)
    pause()
    finishSummary.value = null
    applyCloudDraft(detail.data)
    message.value = '已打开云端草稿。'
    nextTick(() => {
      if (pendingRestoreScrollTop !== null) {
        setViewportTop(pendingRestoreScrollTop)
        pendingRestoreScrollTop = null
      }
      updateProgress()
    })
  } catch (err: any) {
    cloudDraftError.value = err?.response?.data?.detail || err?.message || '草稿打开失败'
  } finally {
    isCloudDraftLoading.value = false
  }
}

async function removeCloudDraft(draftId: number) {
  if (!isCloudDraftEnabled.value) return
  if (!window.confirm('确认删除这个云端提词草稿吗？本地当前内容不会被清空。')) return
  try {
    await deleteTeleprompterDraft(draftId)
    if (cloudDraftId.value === draftId) cloudDraftId.value = null
    cloudDrafts.value = cloudDrafts.value.filter((draft) => draft.draftId !== draftId)
    message.value = '云端草稿已删除。'
  } catch (err: any) {
    draftListError.value = err?.response?.data?.detail || err?.message || '草稿删除失败'
  }
}

function buildCloudDraftPayload(): TeleprompterDraftPayload {
  return {
    title: scriptTitle.value.trim() || inferScriptTitle(scriptText.value),
    content: scriptText.value,
    settings: buildCloudSettings(),
    currentParagraphIndex: Math.max(0, currentSectionIndex.value),
    currentScrollPosition: Math.round(viewportRef.value?.scrollTop ?? 0),
    source: 'teleprompter',
    sourceId: cloudDraftId.value ? String(cloudDraftId.value) : '',
    status: isPlaying.value ? 'playing' : isInteractionPaused.value ? 'interaction_paused' : 'editing',
  }
}

function buildCloudSettings(): TeleprompterCloudSettings {
  return {
    fontSize: String(fontSize.value),
    lineHeight: String(lineHeight.value),
    scrollSpeed: speed.value,
    theme: theme.value,
    mirrorMode: mirror.value,
    countdownEnabled: countdownEnabled.value,
    countdownSeconds: 3,
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function loadSavedState() {
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) return

  try {
    const state = JSON.parse(raw) as Partial<SavedTeleprompterState>
    if (typeof state.title === 'string') scriptTitle.value = state.title
    if (typeof state.text === 'string') scriptText.value = state.text
    if (typeof state.speed === 'number') speed.value = clamp(state.speed, 1, 100)
    if (typeof state.fontSize === 'number') fontSize.value = clamp(state.fontSize, 24, 96)
    if (typeof state.lineHeight === 'number') lineHeight.value = clamp(state.lineHeight, 1.2, 2.4)
    if (state.theme === 'dark' || state.theme === 'warm' || state.theme === 'contrast') theme.value = state.theme
    if (typeof state.mirror === 'boolean') mirror.value = state.mirror
    if (typeof state.countdownEnabled === 'boolean') countdownEnabled.value = state.countdownEnabled
    if (typeof state.currentScrollPosition === 'number') pendingRestoreScrollTop = state.currentScrollPosition
    if (typeof state.updatedAt === 'string') lastDraftSavedAt.value = formatTime(state.updatedAt)
  } catch {
    message.value = '已忽略损坏的本地缓存。'
  }
}

function loadInitialText() {
  const initialText = props.initialText?.trim()
  if (!initialText) return false

  scriptText.value = props.initialText || ''
  scriptTitle.value = inferScriptTitle(props.initialText || '')
  resetContentPosition('viewport')
  message.value = '已载入当前内容，可开启语音跟读。'
  return true
}

async function loadCloudDraft() {
  if (!isCloudDraftEnabled.value || props.initialText?.trim()) return false
  isCloudDraftLoading.value = true
  cloudDraftError.value = ''
  try {
    const recent = await getRecentTeleprompterDraft()
    if (!recent.data?.draftId) return false
    const detail = await getTeleprompterDraft(recent.data.draftId)
    applyCloudDraft(detail.data)
    message.value = '已恢复最近云端提词草稿。'
    return true
  } catch (err: any) {
    cloudDraftError.value = getCloudDraftErrorMessage(err, '云端草稿加载失败，已回退本地草稿')
    return false
  } finally {
    isCloudDraftLoading.value = false
  }
}

function getCloudDraftErrorMessage(err: any, fallback: string) {
  const status = err?.response?.status
  const detail = err?.response?.data?.detail
  if (status === 500) return '云端草稿服务异常，已保留本地草稿；请重启后端后再刷新。'
  return detail || err?.message || fallback
}

async function loadSourceScriptFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const hashQuery = window.location.hash.includes('?') ? window.location.hash.split('?')[1] : ''
  const hashParams = new URLSearchParams(hashQuery)
  const source = params.get('source') || hashParams.get('source')
  const scriptId = Number(params.get('scriptId') || hashParams.get('scriptId') || 0)
  const packageId = Number(params.get('packageId') || hashParams.get('packageId') || 0)

  if (source === 'script' && scriptId > 0) {
    return loadSourceScript(() => getTeleprompterScript(scriptId), 'AI脚本')
  }

  if ((source === 'video-package' || source === 'video_package') && packageId > 0) {
    return loadSourceScript(() => getTeleprompterVideoPackageScript(packageId), '短视频发布包')
  }

  return false
}

async function loadSourceScript(loader: () => Promise<any>, sourceLabel: string) {
  isSourceScriptLoading.value = true
  cloudDraftError.value = ''
  try {
    const res = await loader()
    const data = res.data || {}
    scriptTitle.value = data.title || `${sourceLabel}提词稿`
    scriptText.value = data.content || ''
    pendingRestoreScrollTop = 0
    message.value = `已载入${sourceLabel}内容。`
    reportTeleprompterMetric('teleprompter_script_import')
    return Boolean(scriptText.value.trim())
  } catch (err: any) {
    cloudDraftError.value = err?.response?.data?.detail || err?.message || `${sourceLabel}加载失败`
    return false
  } finally {
    isSourceScriptLoading.value = false
  }
}

function applyCloudDraft(draft: TeleprompterDraft) {
  cloudDraftId.value = draft.draftId
  scriptTitle.value = draft.title || '未命名提词稿'
  scriptText.value = draft.content || ''
  applyCloudSettings(draft.settings)
  pendingRestoreScrollTop = draft.currentScrollPosition || 0
  if (draft.updatedAt) lastDraftSavedAt.value = formatTime(draft.updatedAt)
}

function applyCloudSettings(settings?: Partial<TeleprompterCloudSettings>) {
  if (!settings) return
  const fontSizePreset: Record<string, number> = { small: 32, medium: 44, large: 52, xlarge: 68 }
  const lineHeightPreset: Record<string, number> = { compact: 1.35, normal: 1.65, loose: 2 }
  const parsedFontSize = fontSizePreset[String(settings.fontSize)] ?? Number(settings.fontSize)
  const parsedLineHeight = lineHeightPreset[String(settings.lineHeight)] ?? Number(settings.lineHeight)
  if (Number.isFinite(parsedFontSize)) fontSize.value = clamp(parsedFontSize, 24, 96)
  if (Number.isFinite(parsedLineHeight)) lineHeight.value = clamp(parsedLineHeight, 1.2, 2.4)
  if (typeof settings.scrollSpeed === 'number') speed.value = clamp(settings.scrollSpeed, 1, 100)
  if (settings.theme === 'dark' || settings.theme === 'warm' || settings.theme === 'contrast') theme.value = settings.theme
  if (typeof settings.mirrorMode === 'boolean') mirror.value = settings.mirrorMode
  if (typeof settings.countdownEnabled === 'boolean') countdownEnabled.value = settings.countdownEnabled
}

function inferScriptTitle(text: string) {
  const firstLine = text.split('\n').map((line) => line.trim()).find(Boolean) || '未命名提词稿'
  return firstLine.replace(/^#{1,6}\s+/, '').slice(0, 24)
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function changeSpeed(delta: number, source = '速度') {
  speed.value = clamp(speed.value + delta, 1, 100)
  message.value = `${source}已调至 ${speed.value}`
  reportTeleprompterMetric('teleprompter_speed_change')
}

function startRuntimeSpeedDrag(event: PointerEvent) {
  if (event.button !== 0) return
  if (event.target instanceof HTMLElement && event.target.closest('button')) return

  const bar = runtimeSpeedRef.value
  const viewport = viewportRef.value
  if (!bar || !viewport) return

  event.stopPropagation()
  event.preventDefault()

  const barRect = bar.getBoundingClientRect()
  const viewportRect = viewport.getBoundingClientRect()
  const originX = runtimeSpeedOffset.value.x
  const originY = runtimeSpeedOffset.value.y
  const padding = 8

  runtimeSpeedDragState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX,
    originY,
    minX: originX + viewportRect.left + padding - barRect.left,
    maxX: originX + viewportRect.right - padding - barRect.right,
    minY: originY + viewportRect.top + padding - barRect.top,
    maxY: originY + viewportRect.bottom - padding - barRect.bottom,
    moved: false,
  }
  isDraggingRuntimeSpeed.value = true
  bar.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', handleRuntimeSpeedDrag)
  window.addEventListener('pointerup', stopRuntimeSpeedDrag)
  window.addEventListener('pointercancel', stopRuntimeSpeedDrag)
}

function handleRuntimeSpeedDrag(event: PointerEvent) {
  const state = runtimeSpeedDragState
  if (!state || event.pointerId !== state.pointerId) return

  event.preventDefault()
  const deltaX = event.clientX - state.startX
  const deltaY = event.clientY - state.startY
  if (Math.abs(deltaX) + Math.abs(deltaY) > 4) state.moved = true

  runtimeSpeedOffset.value = {
    x: clamp(state.originX + deltaX, state.minX, state.maxX),
    y: clamp(state.originY + deltaY, state.minY, state.maxY),
  }
}

function stopRuntimeSpeedDrag(event?: PointerEvent) {
  if (event && runtimeSpeedDragState && event.pointerId !== runtimeSpeedDragState.pointerId) return

  runtimeSpeedDragState = null
  isDraggingRuntimeSpeed.value = false
  window.removeEventListener('pointermove', handleRuntimeSpeedDrag)
  window.removeEventListener('pointerup', stopRuntimeSpeedDrag)
  window.removeEventListener('pointercancel', stopRuntimeSpeedDrag)
}

function startViewportDrag(event: PointerEvent) {
  if (event.button !== 0) return
  if (event.target instanceof HTMLElement && event.target.closest('button, input, textarea, select, label, .runtime-speed-bar')) return

  const viewport = viewportRef.value
  if (!viewport) return

  viewportDragState = {
    pointerId: event.pointerId,
    startY: event.clientY,
    startTop: viewport.scrollTop,
    moved: false,
  }
  isDraggingViewport.value = true
  viewport.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', handleViewportDrag)
  window.addEventListener('pointerup', stopViewportDrag)
  window.addEventListener('pointercancel', stopViewportDrag)
}

function handleViewportDrag(event: PointerEvent) {
  const state = viewportDragState
  const viewport = viewportRef.value
  if (!state || !viewport || event.pointerId !== state.pointerId) return

  const deltaY = event.clientY - state.startY
  if (Math.abs(deltaY) <= 4 && !state.moved) return

  event.preventDefault()
  state.moved = true
  if (isPlaying.value || countdown.value > 0) {
    pause()
    message.value = '已暂停，手动拖动调整位置。'
  }

  viewport.scrollTop = state.startTop - deltaY
  scheduleProgressUpdate()
}

function stopViewportDrag(event?: PointerEvent) {
  if (event && viewportDragState && event.pointerId !== viewportDragState.pointerId) return

  if (viewportDragState) viewportRef.value?.releasePointerCapture?.(viewportDragState.pointerId)
  shouldSuppressViewportClick = Boolean(viewportDragState?.moved)
  viewportDragState = null
  isDraggingViewport.value = false
  window.removeEventListener('pointermove', handleViewportDrag)
  window.removeEventListener('pointerup', stopViewportDrag)
  window.removeEventListener('pointercancel', stopViewportDrag)
  window.setTimeout(() => {
    shouldSuppressViewportClick = false
  }, 0)
}

function updateProgress() {
  const viewport = viewportRef.value
  if (!viewport) return

  const maxScroll = viewport.scrollHeight - viewport.clientHeight
  scrollProgress.value = maxScroll <= 0 ? 0 : clamp((viewport.scrollTop / maxScroll) * 100, 0, 100)
  scheduleDraftSave()
}

function scheduleProgressUpdate() {
  if (progressFrameId !== null) return
  progressFrameId = window.requestAnimationFrame(() => {
    progressFrameId = null
    updateProgress()
  })
}

function scrollByAmount(amount: number, takeover = true) {
  const viewport = viewportRef.value
  if (!viewport) return

  if (takeover && (isPlaying.value || countdown.value > 0)) {
    pause()
    message.value = '已暂停，手动调整位置。'
  }

  viewport.scrollBy({ top: amount, behavior: 'auto' })
  scheduleProgressUpdate()
}

function remotePage(direction: 1 | -1) {
  const viewport = viewportRef.value
  const amount = (viewport?.clientHeight ?? 500) * REMOTE_PAGE_RATIO * direction
  scrollByAmount(amount, false)
  message.value = direction > 0
    ? '翻页笔：已下翻一屏；长按下一页可加速。'
    : '翻页笔：已上翻一屏；长按上一页可减速。'
}

function changeSpeedFromRemoteHold(direction: 1 | -1, event: KeyboardEvent) {
  const now = event.timeStamp || performance.now()
  if (now - lastRemoteSpeedRepeatAt < REMOTE_SPEED_REPEAT_INTERVAL) return
  lastRemoteSpeedRepeatAt = now
  changeSpeed(direction * SPEED_STEP, '翻页笔长按速度')
}

function jumpToStart() {
  pause()
  setViewportTop(0)
  message.value = '已跳到开头。'
}

function jumpToEnd() {
  pause()
  const viewport = viewportRef.value
  if (viewport) setViewportTop(viewport.scrollHeight - viewport.clientHeight)
  message.value = '已跳到末尾。'
}

function animationStep(timestamp: number) {
  if (!isPlaying.value) return


  if (!lastFrameTime) lastFrameTime = timestamp
  const deltaSeconds = (timestamp - lastFrameTime) / 1000
  lastFrameTime = timestamp

  const viewport = viewportRef.value
  if (!viewport) return

  const maxScroll = viewport.scrollHeight - viewport.clientHeight
  viewport.scrollTop = clamp(viewport.scrollTop + speed.value * deltaSeconds, 0, maxScroll)
  updateProgress()

  if (viewport.scrollTop >= maxScroll && maxScroll > 0) {
    pause()
    message.value = '已滚动到文案末尾。'
    return
  }

  frameId = window.requestAnimationFrame(animationStep)
}

function startNow() {
  if (!scriptText.value.trim()) {
    message.value = '请先输入或上传提词文案。'
    return
  }
  if (isScriptTooLong.value) {
    message.value = `脚本已超过 ${MAX_SCRIPT_LENGTH} 字，请拆分后再开始提词。`
    return
  }
  isInteractionPaused.value = false
  isFinishConfirmOpen.value = false
  finishSummary.value = null
  if (!sessionStartedAt.value) sessionStartedAt.value = Date.now()
  reportTeleprompterMetric('teleprompter_start')
  clearCountdown()
  message.value = ''
  isPlaying.value = true
  lastFrameTime = 0
  if (frameId !== null) window.cancelAnimationFrame(frameId)
  frameId = window.requestAnimationFrame(animationStep)
}

function startWithCountdown() {
  if (!countdownEnabled.value) {
    startNow()
    return
  }

  clearCountdown()
  countdown.value = 3
  message.value = '倒计时后开始滚动。'
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearCountdown()
      startNow()
    }
  }, 1000)
}

function pause() {
  const wasPlaying = isPlaying.value || countdown.value > 0
  isPlaying.value = false
  lastFrameTime = 0
  clearCountdown()
  if (frameId !== null) {
    window.cancelAnimationFrame(frameId)
    frameId = null
  }
  if (wasPlaying) reportTeleprompterMetric('teleprompter_pause')
}

function toggleInteractionPause() {
  isInteractionPaused.value = !isInteractionPaused.value
  pause()
  message.value = isInteractionPaused.value ? '互动暂停中，正文位置已保留。' : '互动暂停已解除。'
  if (isInteractionPaused.value) reportTeleprompterMetric('teleprompter_interaction_pause')
}

function togglePlay() {
  if (isPlaying.value || countdown.value > 0) {
    pause()
    return
  }
  startWithCountdown()
}

function resetScroll() {
  pause()
  setViewportTop(0)
  message.value = '已回到开头。'
}

function setViewportTop(top: number) {
  const viewport = viewportRef.value
  if (!viewport) return

  viewport.scrollTop = Math.max(0, top)
  scheduleProgressUpdate()
}

function resetContentPosition(focusTarget: 'editor' | 'viewport' | 'none' = 'none') {
  pause()
  nextTick(() => {
    const editor = editorRef.value
    if (editor) {
      editor.scrollTop = 0
      try {
        editor.setSelectionRange(0, 0)
      } catch {
        // Some browsers may reject selection updates before the textarea is focused.
      }
    }

    setViewportTop(0)

    if (focusTarget === 'editor') {
      editor?.focus({ preventScroll: true })
    } else if (focusTarget === 'viewport') {
      viewportRef.value?.focus({ preventScroll: true })
    }
  })
}

function splitPromptSegments(text: string) {
  return splitPromptTextBySpeechBoundary(text)
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment, index) => ({
      index,
      text: segment,
      normalized: normalizeSpeechText(segment),
    }))
}

function formatTeleprompterText(text: string) {
  const normalized = text
    .replace(/\r\n?/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .trim()

  if (!normalized) return ''

  return normalized
    .split(/\n\s*\n+/)
    .map((paragraph) => formatTeleprompterParagraph(paragraph))
    .filter(Boolean)
    .join('\n\n')
}

function formatTeleprompterParagraph(paragraph: string) {
  const compactParagraph = paragraph
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .join(' ')
    .replace(/\s+([，。！？；：、,.!?;:])/g, '$1')

  const sentences = compactParagraph.match(/[^。！？!?；;]+[。！？!?；;]?/g) || [compactParagraph]
  return sentences
    .flatMap((sentence) => splitPromptLine(sentence.trim(), MAX_PROMPT_LINE_LENGTH))
    .filter(Boolean)
    .join('\n')
}

function splitPromptLine(text: string, maxLength: number) {
  if (getPromptTextLength(text) <= maxLength) return [text]

  const chunks: string[] = []
  let current = ''
  const parts = text.match(/[^，、,:：]+[，、,:：]?/g) || [text]

  for (const part of parts) {
    const trimmedPart = part.trim()
    if (!trimmedPart) continue

    if (getPromptTextLength(trimmedPart) > maxLength) {
      if (current) {
        chunks.push(current)
        current = ''
      }
      chunks.push(...splitByLength(trimmedPart, maxLength))
      continue
    }

    const next = current ? `${current}${trimmedPart}` : trimmedPart
    if (getPromptTextLength(next) > maxLength) {
      chunks.push(current)
      current = trimmedPart
    } else {
      current = next
    }
  }

  if (current) chunks.push(current)
  return chunks
}

function splitByLength(text: string, maxLength: number) {
  const chars = Array.from(text)
  const chunks: string[] = []
  for (let index = 0; index < chars.length; index += maxLength) {
    chunks.push(chars.slice(index, index + maxLength).join('').trim())
  }
  return chunks.filter(Boolean)
}

function getPromptTextLength(text: string) {
  return Array.from(text.replace(/\s/g, '')).length
}

function getPromptSections(text: string, segments: PromptSegment[]) {
  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean)
  const sections: PromptSection[] = []

  for (const line of lines) {
    const normalizedLine = normalizeSpeechText(line)
    if (!looksLikePromptTitle(line)) continue

    const segment = segments.find((item) => item.normalized.includes(normalizedLine) || normalizedLine.includes(item.normalized))
    if (!segment || sections.some((section) => section.segmentIndex === segment.index)) continue

    sections.push({
      index: sections.length,
      title: line.replace(/^#{1,6}\s+/, ''),
      segmentIndex: segment.index,
    })
  }

  if (!sections.length && segments.length) {
    sections.push({ index: 0, title: '开头', segmentIndex: 0 })
  }

  return sections.slice(0, 12)
}

function normalizeSpeechText(text: string) {
  let normalized = text
    .toLowerCase()
    .replace(/[\s\p{P}\p{S}]/gu, '')

  for (const filler of SPOKEN_FILLERS) {
    normalized = normalized.split(filler).join('')
  }

  return normalized
}

function goToSection(section: PromptSection) {
  pause()
  currentSegmentIndex.value = section.segmentIndex
  message.value = `已跳到段落：${section.title}`
  scrollToSegment(section.segmentIndex)
  reportTeleprompterMetric('teleprompter_paragraph_jump')
}

function goToRelativeSection(direction: 1 | -1) {
  const sections = promptSections.value
  if (!sections.length) {
    scrollByAmount(direction * (viewportRef.value?.clientHeight ?? 500) * 0.45)
    return
  }

  const currentIndex = currentSectionIndex.value >= 0 ? currentSectionIndex.value : 0
  const nextIndex = clamp(currentIndex + direction, 0, sections.length - 1)
  goToSection(sections[nextIndex])
}

function toggleVoiceFollow() {
  if (isVoiceFollowing.value) {
    stopVoiceFollow()
    return
  }
  startVoiceFollow()
}

function startVoiceFollow() {
  const SpeechRecognitionCtor = getSpeechRecognitionConstructor()
  if (!SpeechRecognitionCtor) {
    voiceSupported.value = false
    voiceStatus.value = '当前浏览器不支持语音识别。建议使用 Chrome。'
    return
  }

  if (!scriptText.value.trim()) {
    voiceStatus.value = '请先输入提词文案。'
    return
  }

  stopVoiceFollow(false)
  speechRecognition = new SpeechRecognitionCtor()
  speechRecognition.lang = 'zh-CN'
  speechRecognition.continuous = true
  speechRecognition.interimResults = true
  shouldRestartRecognition = true
  isVoiceFollowing.value = true
  voiceSupported.value = true
  voiceStatus.value = '正在监听，自动滚动不受影响。'

  speechRecognition.onresult = handleSpeechResult
  speechRecognition.onerror = (event) => {
    voiceStatus.value = `语音识别异常：${event.error}`
  }
  speechRecognition.onend = () => {
    if (shouldRestartRecognition) {
      try {
        speechRecognition?.start()
      } catch {
        voiceStatus.value = '语音识别已暂停，请重新开启。'
      }
    }
  }

  try {
    speechRecognition.start()
  } catch {
    voiceStatus.value = '语音识别启动失败，请检查麦克风权限。'
    isVoiceFollowing.value = false
  }
}

function stopVoiceFollow(updateStatus = true) {
  shouldRestartRecognition = false
  isVoiceFollowing.value = false
  if (speechRecognition) {
    speechRecognition.onresult = null
    speechRecognition.onerror = null
    speechRecognition.onend = null
    speechRecognition.stop()
    speechRecognition = null
  }
  if (updateStatus) voiceStatus.value = '语音跟读已关闭。'
}

function getSpeechRecognitionConstructor() {
  const speechWindow = window as SpeechRecognitionWindow
  return speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition || null
}

function handleSpeechResult(event: SpeechRecognitionEventLike) {
  let transcript = ''
  for (let index = event.resultIndex; index < event.results.length; index += 1) {
    transcript += event.results[index][0].transcript
  }

  const normalizedTranscript = normalizeSpeechText(transcript)
  if (!normalizedTranscript) return

  lastTranscript.value = transcript.trim()
  const matchedIndex = findBestSegmentIndex(normalizedTranscript)
  if (matchedIndex >= 0) {
    if (pendingVoiceMatchIndex.value === matchedIndex) {
      pendingVoiceMatchCount.value += 1
    } else {
      pendingVoiceMatchIndex.value = matchedIndex
      pendingVoiceMatchCount.value = 1
    }

    if (pendingVoiceMatchCount.value < 2 && Math.abs(matchedIndex - currentSegmentIndex.value) > 2) {
      voiceStatus.value = '已找到疑似位置，继续确认中。'
      return
    }

    currentSegmentIndex.value = matchedIndex
    voiceStatus.value = `已跟到：${promptSegments.value[matchedIndex]?.text.slice(0, 18) || ''}`
    if (!isPlaying.value && countdown.value <= 0) {
      isInteractionPaused.value = false
      scrollToSegment(matchedIndex)
    }
    return
  }

  if (isPlaying.value || countdown.value > 0) {
    voiceStatus.value = '未匹配到文案，继续按当前速度滚动。'
    return
  }

  voiceStatus.value = '未匹配到后续文案，请继续朗读或手动调整位置。'
}

function findBestSegmentIndex(normalizedTranscript: string) {
  const segments = promptSegments.value
  const minMatchLength = normalizedTranscript.length >= 6 ? 4 : 2
  const searchStart = Math.max(0, currentSegmentIndex.value)
  const orderedSegments = [
    ...segments.slice(searchStart, Math.min(searchStart + 16, segments.length)),
    ...segments.slice(0, searchStart),
    ...segments.slice(Math.min(searchStart + 16, segments.length)),
  ]

  let bestIndex = -1
  let bestScore = 0

  for (const segment of orderedSegments) {
    const score = getMatchScore(normalizedTranscript, segment.normalized)
    if (score > bestScore) {
      bestScore = score
      bestIndex = segment.index
    }
  }

  return bestScore >= minMatchLength ? bestIndex : -1
}

function getMatchScore(transcript: string, segment: string) {
  if (!transcript || !segment) return 0
  if (segment.includes(transcript)) return transcript.length
  if (transcript.includes(segment)) return segment.length

  let best = 0
  const maxWindow = Math.min(transcript.length, 18)
  for (let length = maxWindow; length >= 2; length -= 1) {
    for (let start = 0; start <= transcript.length - length; start += 1) {
      if (segment.includes(transcript.slice(start, start + length))) return length
    }
    if (best) return best
  }
  return best
}

function scrollToSegment(index: number) {
  nextTick(() => {
    const viewport = viewportRef.value
    const target = viewport?.querySelector(`[data-segment-index="${index}"]`) as HTMLElement | null
    if (!viewport || !target) return

    const offset = target.offsetTop - viewport.clientHeight * 0.36
    setViewportTop(offset)
  })
}

function getSegmentClass(index: number) {
  return {
    alternate: index % 2 === 1,
    active: index === currentSegmentIndex.value,
    read: currentSegmentIndex.value >= 0 && index < currentSegmentIndex.value,
    next: currentSegmentIndex.value >= 0 && index === currentSegmentIndex.value + 1,
  }
}

function clearCountdown() {
  countdown.value = 0
  if (countdownTimer !== null) {
    window.clearInterval(countdownTimer)
    countdownTimer = null
  }
}

async function toggleFullscreen() {
  const viewport = viewportRef.value
  if (!viewport) return

  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    } else {
      await viewport.requestFullscreen()
      reportTeleprompterMetric('teleprompter_fullscreen_enter')
    }
  } catch {
    message.value = '浏览器未允许进入全屏，请用按钮或快捷键重试。'
  }
}

function handleFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement)
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const extension = getFileExtension(file.name)
  if (!SUPPORTED_IMPORT_EXTENSIONS.includes(extension)) {
    message.value = '当前支持导入 TXT、MD、DOC、DOCX 文件。'
    input.value = ''
    return
  }

  try {
    const content = await readImportedFile(file, extension)
    scriptTitle.value = file.name.replace(/\.[^.]+$/, '').slice(0, 50) || inferScriptTitle(content)
    scriptText.value = content
    resetContentPosition('editor')
    message.value = `已导入：${file.name}`
    reportTeleprompterMetric('teleprompter_script_import')
    input.value = ''
  } catch {
    message.value = '文件读取失败，请确认文件未损坏。'
    input.value = ''
  }
}

function getFileExtension(fileName: string) {
  return fileName.split('.').pop()?.toLowerCase() || ''
}

async function readImportedFile(file: File, extension: string) {
  if (extension === 'docx') {
    return extractDocxText(await file.arrayBuffer())
  }

  if (extension === 'doc') {
    return decodeLegacyDoc(await file.arrayBuffer())
  }

  return file.text()
}

async function extractDocxText(buffer: ArrayBuffer) {
  const xml = await readZipEntry(buffer, 'word/document.xml')
  if (!xml) throw new Error('document.xml not found')
  return docxXmlToText(xml)
}

async function readZipEntry(buffer: ArrayBuffer, entryName: string) {
  const view = new DataView(buffer)
  const bytes = new Uint8Array(buffer)
  const eocdOffset = findEndOfCentralDirectory(view)
  if (eocdOffset < 0) return ''

  const centralDirectoryOffset = view.getUint32(eocdOffset + 16, true)
  const centralDirectorySize = view.getUint32(eocdOffset + 12, true)
  let offset = centralDirectoryOffset
  const endOffset = centralDirectoryOffset + centralDirectorySize

  while (offset < endOffset && view.getUint32(offset, true) === 0x02014b50) {
    const compressionMethod = view.getUint16(offset + 10, true)
    const compressedSize = view.getUint32(offset + 20, true)
    const fileNameLength = view.getUint16(offset + 28, true)
    const extraLength = view.getUint16(offset + 30, true)
    const commentLength = view.getUint16(offset + 32, true)
    const localHeaderOffset = view.getUint32(offset + 42, true)
    const fileName = new TextDecoder().decode(bytes.slice(offset + 46, offset + 46 + fileNameLength))

    if (fileName === entryName) {
      const localFileNameLength = view.getUint16(localHeaderOffset + 26, true)
      const localExtraLength = view.getUint16(localHeaderOffset + 28, true)
      const dataOffset = localHeaderOffset + 30 + localFileNameLength + localExtraLength
      const compressedData = bytes.slice(dataOffset, dataOffset + compressedSize)

      if (compressionMethod === 0) return new TextDecoder().decode(compressedData)
      if (compressionMethod === 8) return inflateRawToText(compressedData)
      return ''
    }

    offset += 46 + fileNameLength + extraLength + commentLength
  }

  return ''
}

function findEndOfCentralDirectory(view: DataView) {
  for (let offset = view.byteLength - 22; offset >= 0; offset -= 1) {
    if (view.getUint32(offset, true) === 0x06054b50) return offset
  }
  return -1
}

async function inflateRawToText(data: Uint8Array) {
  if (!('DecompressionStream' in window)) throw new Error('DecompressionStream unsupported')
  const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'))
  return new Response(stream).text()
}

function docxXmlToText(xml: string) {
  return xml
    .replace(/<w:tab\s*\/>/g, '\t')
    .replace(/<w:br\s*\/>/g, '\n')
    .replace(/<\/w:p>/g, '\n')
    .replace(/<w:t[^>]*>(.*?)<\/w:t>/g, (_, text: string) => decodeXmlEntities(text))
    .replace(/<[^>]+>/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function decodeXmlEntities(text: string) {
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
}

function decodeLegacyDoc(buffer: ArrayBuffer) {
  const utf8Text = new TextDecoder('utf-8', { fatal: false }).decode(buffer)
  const utf16Text = new TextDecoder('utf-16le', { fatal: false }).decode(buffer)
  const bestText = readableScore(utf16Text) > readableScore(utf8Text) ? utf16Text : utf8Text
  return bestText
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function readableScore(text: string) {
  const matches = text.match(/[\u4e00-\u9fa5A-Za-z0-9，。！？、,.!?]/g)
  return matches?.length ?? 0
}

function useGeneratedScript() {
  if (!props.initialText?.trim()) {
    message.value = '当前还没有可导入的口播文案。'
    return
  }
  scriptText.value = props.initialText
  scriptTitle.value = inferScriptTitle(props.initialText)
  resetContentPosition('editor')
  message.value = '已载入当前口播文案。'
}

function clearText() {
  if (scriptText.value.trim() && !window.confirm('确认清空当前提词文案吗？此操作不可撤销。')) return
  pause()
  scriptTitle.value = '未命名提词稿'
  scriptText.value = ''
  resetContentPosition('editor')
  message.value = '文案已清空。'
}

function handleEditorInput() {
  if (scriptTitle.value === '未命名提词稿' && scriptText.value.trim()) {
    scriptTitle.value = inferScriptTitle(scriptText.value)
  }
  scheduleProgressUpdate()
}

function handleEditorPaste(event: ClipboardEvent) {
  const pastedText = event.clipboardData?.getData('text/plain') || ''
  const formattedText = formatTeleprompterText(pastedText)
  if (!formattedText) {
    window.setTimeout(() => resetContentPosition('editor'), 0)
    return
  }

  event.preventDefault()
  const editor = editorRef.value
  const start = editor?.selectionStart ?? scriptText.value.length
  const end = editor?.selectionEnd ?? start
  const before = scriptText.value.slice(0, start)
  const after = scriptText.value.slice(end)
  const prefix = before && !before.endsWith('\n') ? '\n' : ''
  const suffix = after && !after.startsWith('\n') ? '\n' : ''
  const insertedText = `${prefix}${formattedText}${suffix}`

  scriptText.value = `${before}${insertedText}${after}`
  message.value = `已自动分句，每段不超过 ${MAX_PROMPT_LINE_LENGTH} 字。`
  nextTick(() => {
    const cursorPosition = before.length + insertedText.length
    editor?.setSelectionRange(cursorPosition, cursorPosition)
    resetContentPosition('editor')
  })
}

function handleViewportClick(event: MouseEvent) {
  if (shouldSuppressViewportClick) return
  const target = event.target as HTMLElement
  if (target.closest('button, input, textarea, select, label, .runtime-speed-bar')) return
  togglePlay()
}

function handleWheel() {
  if (isPlaying.value || countdown.value > 0) {
    pause()
    message.value = '已暂停，手动滚动调整位置。'
  }
  scheduleProgressUpdate()
}

function isTypingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable
}

function eventMatchesKeySet(event: KeyboardEvent, keys: Set<string>) {
  return keys.has(event.key) || keys.has(event.code)
}

function getRemotePageDirection(event: KeyboardEvent): 1 | -1 | 0 {
  if (eventMatchesKeySet(event, REMOTE_PREVIOUS_KEYS)) return -1
  if (eventMatchesKeySet(event, REMOTE_NEXT_KEYS)) return 1
  return 0
}

function handleRemotePageKey(event: KeyboardEvent, direction: 1 | -1) {
  event.preventDefault()
  viewportRef.value?.focus({ preventScroll: true })
  if (event.repeat) {
    changeSpeedFromRemoteHold(direction, event)
    return
  }
  lastRemoteSpeedRepeatAt = 0
  remotePage(direction)
}

function openFinishConfirm() {
  if (!scriptText.value.trim()) {
    message.value = '当前没有可结束的提词内容。'
    return
  }
  pause()
  isFinishConfirmOpen.value = true
}

function cancelFinish() {
  isFinishConfirmOpen.value = false
  message.value = '已取消结束，当前提词位置已保留。'
}

function confirmFinish() {
  pause()
  isInteractionPaused.value = false
  isFinishConfirmOpen.value = false
  const durationSeconds = sessionStartedAt.value ? Math.max(1, Math.round((Date.now() - sessionStartedAt.value) / 1000)) : 0
  finishSummary.value = {
    durationSeconds,
    completionRate: Math.round(scrollProgress.value),
    wordCount: wordsCount.value,
  }
  sessionStartedAt.value = null
  saveDraftState()
  saveCloudDraft()
  reportTeleprompterMetric('teleprompter_finish')
  message.value = '本次提词已结束，草稿和位置已保存。'
}

function reportTeleprompterMetric(eventName: string) {
  reportTeleprompterEvent({
    eventName,
    eventTime: new Date().toISOString(),
    sessionId: props.currentUser?.email || 'guest',
    properties: {
      source: cloudDraftId.value ? 'cloud_draft' : 'local_draft',
      draftId: cloudDraftId.value,
      wordCount: wordsCount.value,
      paragraphCount: promptSections.value.length,
      progress: Math.round(scrollProgress.value),
      speed: speed.value,
      fontSize: fontSize.value,
      theme: theme.value,
      userMode: isCloudDraftEnabled.value ? 'login' : 'guest',
    },
  }).catch(() => {
    // 埋点失败不影响提词主流程。
  })
}

async function copyScript() {
  if (!scriptText.value.trim()) {
    message.value = '暂无可复制的脚本。'
    return
  }

  try {
    await navigator.clipboard.writeText(scriptText.value)
    message.value = '脚本已复制。'
  } catch {
    message.value = '复制失败，请手动选择文本复制。'
  }
}

function replayFromStart() {
  finishSummary.value = null
  sessionStartedAt.value = null
  jumpToStart()
  startWithCountdown()
}

function handleKeydown(event: KeyboardEvent) {
  if (isTypingTarget(event.target)) return

  const remoteDirection = getRemotePageDirection(event)
  if (remoteDirection) {
    handleRemotePageKey(event, remoteDirection)
    return
  }

  if (eventMatchesKeySet(event, SPEED_DOWN_KEYS)) {
    event.preventDefault()
    changeSpeed(-SPEED_STEP, event.key.startsWith('Audio') || event.key.startsWith('Volume') ? '音量键速度' : '速度')
    return
  }

  if (eventMatchesKeySet(event, SPEED_UP_KEYS)) {
    event.preventDefault()
    changeSpeed(SPEED_STEP, event.key.startsWith('Audio') || event.key.startsWith('Volume') ? '音量键速度' : '速度')
    return
  }

  if (eventMatchesKeySet(event, PLAY_TOGGLE_KEYS)) {
    event.preventDefault()
    togglePlay()
    return
  }

  if (event.code === 'Space') {
    event.preventDefault()
    togglePlay()
  } else if (event.key.toLowerCase() === 'f') {
    event.preventDefault()
    toggleFullscreen()
  } else if (event.key.toLowerCase() === 'i') {
    event.preventDefault()
    toggleInteractionPause()
  } else if (event.key === 'Enter') {
    event.preventDefault()
    toggleInteractionPause()
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault()
    goToRelativeSection(-1)
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    goToRelativeSection(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (event.repeat) changeSpeedFromRemoteHold(-1, event)
    else scrollByAmount(-FINE_SCROLL_STEP)
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (event.repeat) changeSpeedFromRemoteHold(1, event)
    else scrollByAmount(FINE_SCROLL_STEP)
  } else if (event.key === 'Home') {
    event.preventDefault()
    jumpToStart()
  } else if (event.key === 'End') {
    event.preventDefault()
    jumpToEnd()
  } else if (event.key === 'Escape') {
    pause()
  }
}

onMounted(async () => {
  if (!loadInitialText()) {
    const sourceLoaded = await loadSourceScriptFromUrl()
    if (!sourceLoaded) {
      const cloudLoaded = await loadCloudDraft()
      if (!cloudLoaded) loadSavedState()
    }
  }
  voiceSupported.value = Boolean(getSpeechRecognitionConstructor())
  voiceStatus.value = voiceSupported.value
    ? '开启语音跟读前，请先允许麦克风权限。'
    : '当前浏览器不支持语音识别。建议使用 Chrome。'
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  refreshCloudDrafts(false)
  reportTeleprompterMetric('teleprompter_open')
  nextTick(() => {
    if (pendingRestoreScrollTop !== null) {
      setViewportTop(pendingRestoreScrollTop)
      pendingRestoreScrollTop = null
    }
    updateProgress()
  })
})

onUnmounted(() => {
  if (draftSaveTimer !== null) {
    window.clearTimeout(draftSaveTimer)
    draftSaveTimer = null
  }
  if (cloudSaveTimer !== null) {
    window.clearTimeout(cloudSaveTimer)
    cloudSaveTimer = null
  }
  saveDraftState()
  pause()
  stopVoiceFollow(false)
  stopRuntimeSpeedDrag()
  stopViewportDrag()
  if (progressFrameId !== null) {
    window.cancelAnimationFrame(progressFrameId)
    progressFrameId = null
  }
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})
</script>

<template>
  <div class="teleprompter-panel">
    <div class="permission-reminder glass-card" :class="{ unsupported: !voiceSupported }">
      <strong>{{ voiceSupported ? '先打开麦克风权限' : '当前浏览器不支持语音识别' }}</strong>
      <span>
        {{ voiceSupported
          ? '点击「语音跟读」后，在浏览器权限弹窗选择“允许”，系统才能根据讲话自动移动到对应文案。'
          : '请使用 Chrome 或 Edge 打开页面，再开启语音跟读。' }}
      </span>
    </div>

    <section class="teleprompter-commandbar glass-card">
      <div class="command-title">
        <span class="badge badge-accent">在线提词器</span>
        <strong>{{ scriptTitle }}</strong>
        <em>{{ isPlaying ? '滚动中' : countdown > 0 ? '倒计时' : '待开始' }}</em>
      </div>

      <div class="transport-controls" aria-label="提词器播放控制">
        <button class="transport-btn" title="回到开头" @click="jumpToStart">|‹</button>
        <button class="transport-btn" title="上一段" @click="goToRelativeSection(-1)">上一段</button>
        <button class="transport-btn play-btn" title="播放或暂停" @click="togglePlay">
          {{ isPlaying || countdown > 0 ? 'Pause' : 'Play' }}
        </button>
        <button class="transport-btn interact-btn" :class="{ active: isInteractionPaused }" title="互动暂停" @click="toggleInteractionPause">
          互动
        </button>
        <button class="transport-btn" title="下一段" @click="goToRelativeSection(1)">下一段</button>
        <button class="transport-btn" title="跳到末尾" @click="jumpToEnd">›|</button>
        <button class="transport-btn finish-btn" title="结束本次提词" @click="openFinishConfirm">结束</button>
      </div>

      <div class="voice-follow-card" :class="{ active: isVoiceFollowing }">
        <button class="voice-btn" :disabled="!voiceSupported" @click="toggleVoiceFollow">
          {{ isVoiceFollowing ? '关闭跟读' : '语音跟读' }}
        </button>
        <div class="voice-copy">
          <strong>{{ voiceStatus }}</strong>
          <span v-if="lastTranscript">识别：{{ lastTranscript }}</span>
          <span v-else>{{ voiceSupported ? '授权后朗读文案即可自动定位' : '浏览器不支持语音识别' }}</span>
        </div>
      </div>

      <div class="top-settings">
        <div class="setting-group compact wide speed-setting-card">
          <div class="speed-label-line">
            <span>速度</span>
            <strong>{{ speed }}</strong>
          </div>
          <div class="speed-stepper" aria-label="提词速度调节">
            <button type="button" class="speed-step-btn" title="减慢速度" @click="changeSpeed(-4)">-</button>
            <input v-model.number="speed" type="range" min="1" max="100" step="1" />
            <button type="button" class="speed-step-btn" title="加快速度" @click="changeSpeed(4)">+</button>
          </div>
        </div>
        <label class="setting-group compact">
          字号 <strong>{{ fontSize }}px</strong>
          <input v-model.number="fontSize" type="range" min="24" max="96" step="2" />
        </label>
        <label class="setting-group compact">
          行高 <strong>{{ lineHeight.toFixed(2) }}</strong>
          <input v-model.number="lineHeight" type="range" min="1.2" max="2.4" step="0.05" />
        </label>

        <div class="setting-row compact-row">
          <label class="switch-line">
            <input v-model="mirror" type="checkbox" />
            <span>镜像</span>
          </label>
          <label class="switch-line">
            <input v-model="countdownEnabled" type="checkbox" />
            <span>倒计时</span>
          </label>
        </div>

        <div class="theme-picker compact-theme">
          <button class="tab-item" :class="{ active: theme === 'dark' }" @click="theme = 'dark'">经典</button>
          <button class="tab-item" :class="{ active: theme === 'warm' }" @click="theme = 'warm'">暖色</button>
          <button class="tab-item" :class="{ active: theme === 'contrast' }" @click="theme = 'contrast'">高可读</button>
        </div>
      </div>
    </section>

    <div class="teleprompter-workbench">
      <aside class="teleprompter-sidebar glass-card">
        <div class="teleprompter-title-block">
          <h2>提词文案</h2>
          <p>开播中优先用上方播放器和互动暂停；字号、主题等属于开播前设置。</p>
        </div>

        <label class="script-title-field">
          脚本标题
          <input v-model="scriptTitle" class="input" maxlength="50" placeholder="输入脚本标题" />
        </label>

        <div v-if="promptSections.length" class="section-jump-list">
          <button
            v-for="section in promptSections"
            :key="section.index"
            class="section-jump"
            :class="{ active: section.index === currentSectionIndex }"
            @click="goToSection(section)"
          >{{ section.title }}</button>
        </div>

        <section v-if="isCloudDraftEnabled" class="cloud-draft-panel">
          <div class="cloud-draft-head">
            <div>
              <strong>云端草稿</strong>
              <span>{{ cloudDrafts.length ? `最近 ${cloudDrafts.length} 条` : '暂无草稿' }}</span>
            </div>
            <button class="btn btn-ghost btn-sm" :disabled="isDraftListLoading" @click="refreshCloudDrafts()">
              {{ isDraftListLoading ? '刷新中' : '刷新' }}
            </button>
          </div>

          <p v-if="draftListError" class="cloud-draft-error">{{ draftListError }}</p>

          <div v-if="cloudDrafts.length" class="cloud-draft-list">
            <article
              v-for="draft in cloudDrafts"
              :key="draft.draftId"
              class="cloud-draft-item"
              :class="{ active: draft.draftId === cloudDraftId }"
            >
              <button type="button" class="cloud-draft-main" @click="openCloudDraft(draft.draftId)">
                <strong>{{ draft.title }}</strong>
                <span>{{ draft.wordCount }} 字/词 · {{ draft.paragraphCount }} 段 · {{ draft.updatedAt ? formatTime(draft.updatedAt) : '未保存时间' }}</span>
              </button>
              <button type="button" class="cloud-draft-delete" title="删除云端草稿" @click="removeCloudDraft(draft.draftId)">删除</button>
            </article>
          </div>

          <p v-else-if="!draftListError" class="cloud-draft-empty">保存一次后，这里会显示云端提词稿。</p>
        </section>

        <div class="teleprompter-editor-actions">
          <button class="btn btn-ghost btn-sm" @click="fileInputRef?.click()">导入文件</button>
          <button class="btn btn-ghost btn-sm" :disabled="!props.initialText?.trim()" :title="props.initialText?.trim() ? '载入当前生成内容' : '暂无口播文案，请先生成全案'" @click="useGeneratedScript">载入口播文案</button>
          <button class="btn btn-ghost btn-sm" @click="copyScript">复制脚本</button>
          <button class="btn btn-ghost btn-sm" @click="clearText">清空</button>
          <input ref="fileInputRef" type="file" :accept="DOC_IMPORT_ACCEPT" hidden @change="handleFileChange" />
        </div>

        <textarea
          ref="editorRef"
          v-model="scriptText"
          class="input teleprompter-textarea"
          placeholder="粘贴你的口播文案..."
          @input="handleEditorInput"
          @paste="handleEditorPaste"
        ></textarea>

        <div class="teleprompter-stats">
          <span :class="{ warning: isScriptTooLong }">{{ scriptLength }} / {{ MAX_SCRIPT_LENGTH }} 字</span>
          <span>约 {{ estimatedMinutes }} 分钟</span>
          <span>进度 {{ progressLabel }}</span>
        </div>

        <p class="draft-save-line">{{ saveStatusLabel }}</p>
      </aside>

      <section class="teleprompter-stage glass-card" :class="themeClass">
        <div class="stage-toolbar">
          <div class="stage-status">
            <span class="status-dot" :class="{ playing: isPlaying }"></span>
            <strong>{{ isPlaying ? '滚动中' : countdown > 0 ? '倒计时' : '已暂停' }}</strong>
            <span v-if="message">{{ message }}</span>
          </div>
          <div class="remote-control-hint" title="支持常见 2.4G/蓝牙翻页笔：PageUp/PageDown、方向键、媒体上一首/下一首">
            <strong>翻页笔</strong>
            <span>上一页/下一页上下翻，长按调速</span>
          </div>
          <div class="stage-actions">
            <button class="btn btn-ghost btn-sm" @click="resetScroll">重置</button>
            <button class="btn btn-ghost btn-sm" @click="toggleFullscreen">
              {{ isFullscreen ? '退出全屏' : '全屏' }}
            </button>
            <button class="btn btn-ghost btn-sm" @click="openFinishConfirm">结束</button>
          </div>
        </div>

        <div class="progress-track">
          <div class="progress-fill" :style="{ width: progressLabel }"></div>
        </div>

        <div
          ref="viewportRef"
          class="teleprompter-viewport"
          :class="{ dragging: isDraggingViewport }"
          tabindex="0"
          @click="handleViewportClick"
          @pointerdown="startViewportDrag"
          @scroll="scheduleProgressUpdate"
          @wheel.passive="handleWheel"
        >
          <div v-if="countdown > 0" class="countdown-overlay">{{ countdown }}</div>
          <article class="prompt-content" :style="displayStyle">
            <template v-if="promptSegments.length">
              <span
                v-for="segment in promptSegments"
                :key="segment.index"
                class="prompt-segment"
                :class="getSegmentClass(segment.index)"
                :data-segment-index="segment.index"
              >{{ segment.text }}</span>
            </template>
            <template v-else>在左侧输入文案后开始提词。</template>
          </article>

          <div v-if="isInteractionPaused" class="interaction-pause-panel" @click.stop>
            <div>
              <strong>互动暂停中</strong>
              <span>正文位置已保留，临时话术不会写回原稿。</span>
            </div>
            <textarea v-model="temporaryInteractionNote" placeholder="输入临时互动话术，例如：先回答弹幕，再回到正文。"></textarea>
            <button type="button" @click="toggleInteractionPause">恢复正文</button>
          </div>

          <div
            v-if="promptSegments.length"
            ref="runtimeSpeedRef"
            class="runtime-speed-bar"
            :class="{ dragging: isDraggingRuntimeSpeed }"
            :style="runtimeSpeedStyle"
            @click.stop
          >
            <button type="button" class="runtime-speed-btn" @pointerdown.stop @click.stop="changeSpeed(-4)">-</button>
            <div class="runtime-speed-copy" title="按住这里拖动速度框" @pointerdown="startRuntimeSpeedDrag">
              <span>拖动调位置</span>
              <strong>{{ speed }}</strong>
            </div>
            <button type="button" class="runtime-speed-btn" @pointerdown.stop @click.stop="changeSpeed(4)">+</button>
          </div>
        </div>

        <div class="shortcut-strip">
          <span>点击画面：启停</span>
          <span>空格：暂停</span>
          <span>↑/↓：上下滚动</span>
          <span>←/→：上一段/下一段</span>
          <span>F：全屏</span>
          <span>I/Enter：互动暂停</span>
          <span>翻页笔/PageUp/PageDown：上下翻页</span>
          <span>长按翻页笔：调慢/调快速度</span>
          <span>+ / - / 音量键：调速</span>
          <span>Esc：暂停或退出全屏</span>
        </div>
      </section>
    </div>

    <div v-if="isFinishConfirmOpen" class="modal-backdrop" @click.self="cancelFinish">
      <section class="finish-modal glass-card">
        <span class="badge badge-accent">结束确认</span>
        <h3>确认结束本次提词？</h3>
        <p>当前脚本、显示设置和播放位置会自动保存，结束后可重新播放或复制脚本。</p>
        <div class="finish-actions">
          <button class="btn btn-ghost" @click="cancelFinish">继续提词</button>
          <button class="btn btn-primary" @click="confirmFinish">确认结束</button>
        </div>
      </section>
    </div>

    <section v-if="finishSummary" class="finish-summary glass-card">
      <div>
        <span class="badge badge-accent">本次统计</span>
        <h3>{{ scriptTitle }}</h3>
      </div>
      <div class="summary-grid">
        <span><strong>{{ finishDurationLabel }}</strong>提词时长</span>
        <span><strong>{{ finishSummary.completionRate }}%</strong>完成进度</span>
        <span><strong>{{ finishSummary.wordCount }}</strong>字/词</span>
      </div>
      <div class="finish-actions">
        <button class="btn btn-ghost" @click="copyScript">复制脚本</button>
        <button class="btn btn-primary" @click="replayFromStart">重新播放</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.teleprompter-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
  height: 100%;
  padding: 0;
  overflow-y: auto;
}

.permission-reminder {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(255, 251, 235, 0.96), rgba(254, 243, 199, 0.72));
  box-shadow: 0 12px 34px rgba(245, 158, 11, 0.1);
}

.permission-reminder.unsupported {
  border-color: rgba(239, 68, 68, 0.22);
  background: linear-gradient(135deg, rgba(254, 242, 242, 0.96), rgba(254, 226, 226, 0.72));
}

.permission-reminder strong {
  flex: 0 0 auto;
  color: #92400e;
  font-size: 14px;
  font-weight: 900;
}

.permission-reminder.unsupported strong {
  color: #991b1b;
}

.permission-reminder span {
  color: #78350f;
  font-size: 13px;
  line-height: 1.6;
}

.permission-reminder.unsupported span {
  color: #7f1d1d;
}

.teleprompter-commandbar {
  display: grid;
  grid-template-columns: minmax(130px, 0.55fr) auto minmax(240px, 0.9fr) minmax(360px, 1.8fr);
  gap: 14px;
  align-items: center;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 28px;
  box-shadow: 0 12px 34px rgba(29, 29, 31, 0.07);
}

.command-title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.command-title strong {
  overflow: hidden;
  color: #1d1d1f;
  font-size: 15px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-title em {
  flex: 0 0 auto;
  color: #6e6e73;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.transport-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 5px;
  border-radius: 999px;
  background: #f5f5f7;
}

.transport-btn {
  display: inline-flex;
  min-width: 42px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #1d1d1f;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.transport-btn:hover {
  background: #fff;
  transform: translateY(-1px);
}

.play-btn {
  min-width: 76px;
  background: #2457ff;
  color: #fff;
  box-shadow: 0 10px 24px rgba(36, 87, 255, 0.16);
}

.play-btn:hover {
  background: #1d4ed8;
}

.interact-btn {
  min-width: 54px;
  color: #b45309;
}

.interact-btn.active {
  background: #f59e0b;
  color: #fff;
}

.finish-btn {
  color: #b91c1c;
}

.voice-follow-card {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 6px 6px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 999px;
  background: #f7f7fa;
}

.voice-follow-card.active {
  border-color: rgba(16, 185, 129, 0.26);
  background: rgba(16, 185, 129, 0.08);
}

.voice-btn {
  flex: 0 0 auto;
  padding: 9px 13px;
  border: 0;
  border-radius: 999px;
  background: #2457ff;
  color: #fff;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.voice-btn:disabled {
  cursor: not-allowed;
  background: #d2d2d7;
}

.voice-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.voice-copy strong,
.voice-copy span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.voice-copy strong {
  color: #1d1d1f;
  font-size: 12px;
  font-weight: 850;
}

.voice-copy span {
  color: #6e6e73;
  font-size: 11px;
}

.top-settings {
  display: grid;
  grid-template-columns: minmax(160px, 1.1fr) minmax(130px, 0.8fr) minmax(130px, 0.8fr) auto minmax(210px, 1fr);
  gap: 10px;
  align-items: center;
  opacity: 0.92;
}

.teleprompter-workbench {
  display: grid;
  grid-template-columns: minmax(320px, 410px) minmax(0, 1fr);
  gap: 18px;
  min-height: 0;
  flex: 1;
}

.teleprompter-sidebar,
.teleprompter-stage {
  min-height: 0;
}

.teleprompter-sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 28px;
  box-shadow: 0 16px 42px rgba(29, 29, 31, 0.08);
}

.teleprompter-title-block h2 {
  margin: 0 0 8px;
  color: #1d1d1f;
  font-size: 30px;
  font-weight: 900;
  letter-spacing: -0.06em;
  line-height: 1.08;
}

.teleprompter-title-block p {
  margin: 0;
  color: #6e6e73;
  font-size: 14px;
  line-height: 1.75;
}

.teleprompter-editor-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.script-title-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #515154;
  font-size: 13px;
  font-weight: 800;
}

.teleprompter-editor-actions .btn {
  flex: 1;
  min-width: max-content;
}

.section-jump-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 20px;
  background: #f7f7fa;
}

.section-jump {
  max-width: 100%;
  overflow: hidden;
  padding: 7px 11px;
  border: 0;
  border-radius: 999px;
  background: #fff;
  color: #515154;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.section-jump.active {
  background: #eef3ff;
  color: #2457ff;
  box-shadow: inset 0 0 0 1px #dbe6ff;
}

.cloud-draft-panel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  background: #f8fafc;
}

.cloud-draft-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.cloud-draft-head div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.cloud-draft-head strong {
  color: #1d1d1f;
  font-size: 14px;
  font-weight: 900;
}

.cloud-draft-head span,
.cloud-draft-empty,
.cloud-draft-error {
  color: #6e6e73;
  font-size: 12px;
  font-weight: 700;
}

.cloud-draft-error {
  color: #b91c1c;
}

.cloud-draft-list {
  display: grid;
  gap: 8px;
  max-height: 210px;
  overflow-y: auto;
}

.cloud-draft-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 8px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
}

.cloud-draft-item.active {
  border-color: rgba(36, 87, 255, 0.28);
  background: #fff;
  box-shadow: 0 10px 26px rgba(36, 87, 255, 0.08);
}

.cloud-draft-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.cloud-draft-main strong,
.cloud-draft-main span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cloud-draft-main strong {
  color: #1d1d1f;
  font-size: 13px;
  font-weight: 900;
}

.cloud-draft-main span {
  color: #86868b;
  font-size: 11px;
  font-weight: 700;
}

.cloud-draft-delete {
  padding: 6px 9px;
  border: 0;
  border-radius: 999px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.teleprompter-textarea {
  min-height: 0;
  flex: 1;
  border-radius: 22px;
  background: #f7f7fa;
  color: #1d1d1f;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
  resize: vertical;
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #515154;
  font-size: 13px;
  font-weight: 700;
}

.setting-group strong {
  color: #1d1d1f;
}

.speed-setting-card {
  gap: 10px;
}

.speed-label-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.speed-stepper {
  display: grid;
  grid-template-columns: 34px minmax(90px, 1fr) 34px;
  gap: 8px;
  align-items: center;
}

.speed-step-btn {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 999px;
  background: #2457ff;
  color: #fff;
  font-size: 20px;
  font-weight: 900;
  line-height: 1;
  cursor: pointer;
}

.speed-step-btn:hover {
  background: #1d4ed8;
}

.setting-group input[type='range'] {
  width: 100%;
  accent-color: var(--color-accent-primary);
}

.setting-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.setting-group.compact {
  padding: 10px 12px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 18px;
  background: #fff;
}

.setting-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.compact-row {
  gap: 8px;
  justify-content: center;
}

.switch-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 999px;
  background: #fff;
  color: #515154;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.switch-line input {
  accent-color: var(--color-accent-primary);
}

.theme-picker {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px;
  padding: 4px;
  border-radius: 18px;
  background: #f5f5f7;
}

.compact-theme {
  min-width: 0;
}

.theme-picker .tab-item {
  padding: 8px 6px;
  font-size: 12px;
}

.teleprompter-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.teleprompter-stats span {
  padding: 12px 10px;
  border-radius: 18px;
  background: #f7f7fa;
  color: #515154;
  text-align: center;
  font-size: 12px;
  font-weight: 800;
}

.teleprompter-stats span.warning {
  background: #fef2f2;
  color: #b91c1c;
}

.draft-save-line {
  margin: -8px 0 0;
  color: #86868b;
  font-size: 12px;
  font-weight: 700;
}

.teleprompter-stage {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 28px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.stage-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
}

.stage-status {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 13px;
}

.stage-status span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remote-control-hint {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid rgba(36, 87, 255, 0.16);
  border-radius: 999px;
  background: rgba(36, 87, 255, 0.08);
  color: #475569;
  font-size: 12px;
}

.remote-control-hint strong {
  color: #2457ff;
  font-weight: 900;
}

.remote-control-hint span {
  color: #64748b;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-warning);
  box-shadow: none;
}

.status-dot.playing {
  background: var(--color-success);
  box-shadow: none;
}

.stage-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.stage-actions .btn-ghost {
  background: #fff;
  border-color: rgba(15, 23, 42, 0.08);
  color: #0f172a;
}

.stage-actions .btn-ghost:hover {
  background: #eef3ff;
  color: #2457ff;
}

.progress-track {
  height: 4px;
  background: #eef2f7;
}

.progress-fill {
  height: 100%;
  background: #2457ff;
  transition: width 0.15s linear;
}

.teleprompter-viewport {
  position: relative;
  flex: 1;
  overflow-y: auto;
  background: #050507;
  padding: clamp(56px, 9vw, 128px) clamp(32px, 8vw, 118px);
  outline: none;
  cursor: grab;
  scroll-behavior: auto;
  overscroll-behavior: contain;
  touch-action: none;
  -webkit-overflow-scrolling: touch;
}

.teleprompter-viewport.dragging {
  cursor: grabbing;
}

.runtime-speed-bar {
  position: fixed;
  right: max(28px, calc((100vw - 92%) / 2));
  bottom: 28px;
  z-index: 6;
  display: grid;
  grid-template-columns: 48px auto 48px;
  gap: 8px;
  align-items: center;
  width: fit-content;
  padding: 8px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 46px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.runtime-speed-bar.dragging {
  cursor: grabbing;
}

.teleprompter-viewport:fullscreen .runtime-speed-bar {
  right: 28px;
  bottom: 28px;
}

.runtime-speed-btn {
  display: inline-flex;
  width: 48px;
  height: 42px;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 999px;
  background: #fff;
  color: #1d1d1f;
  font-size: 24px;
  font-weight: 900;
  line-height: 1;
  cursor: pointer;
  touch-action: manipulation;
}

.runtime-speed-copy {
  display: flex;
  min-width: 82px;
  flex-direction: column;
  align-items: center;
  color: #0f172a;
  cursor: grab;
  touch-action: none;
}

.runtime-speed-copy span {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.runtime-speed-copy strong {
  color: #0f172a;
  font-size: 21px;
  font-weight: 900;
}

.runtime-speed-bar.dragging .runtime-speed-copy {
  cursor: grabbing;
}

.interaction-pause-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  z-index: 7;
  display: grid;
  width: min(520px, calc(100vw - 32px));
  gap: 14px;
  padding: 20px;
  border: 1px solid rgba(245, 158, 11, 0.42);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 26px 80px rgba(15, 23, 42, 0.16);
  transform: translate(-50%, -50%);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.interaction-pause-panel strong {
  display: block;
  margin-bottom: 4px;
  color: #92400e;
  font-size: 20px;
  font-weight: 900;
}

.interaction-pause-panel span {
  color: #78350f;
  font-size: 13px;
}

.interaction-pause-panel textarea {
  min-height: 96px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 16px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  line-height: 1.6;
  outline: none;
  resize: vertical;
}

.interaction-pause-panel button {
  justify-self: end;
  padding: 10px 16px;
  border: 0;
  border-radius: 999px;
  background: #f59e0b;
  color: #1d1d1f;
  font-weight: 900;
  cursor: pointer;
}

.teleprompter-viewport:fullscreen {
  background: #000;
}

.prompt-content {
  min-height: 140vh;
  padding-bottom: 48vh;
  color: #f7f7fb;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: pre-wrap;
  word-break: break-word;
  text-align: center;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.68);
  user-select: none;
}

.prompt-segment {
  display: inline;
  padding: 0 0.12em;
  border-radius: 0.18em;
  transition: background 0.18s ease, color 0.18s ease, text-shadow 0.18s ease;
}

.prompt-segment.alternate {
  color: #8fd3ff;
}

.prompt-segment::after {
  content: '\A\A';
  white-space: pre;
}

.prompt-segment.active {
  background: rgba(253, 203, 110, 0.28);
  color: #ffe08a;
  text-shadow: 0 0 24px rgba(253, 203, 110, 0.42);
}

.prompt-segment.read {
  color: rgba(255, 255, 255, 0.28);
  text-shadow: none;
}

.prompt-segment.next {
  color: rgba(255, 255, 255, 0.82);
  text-decoration: underline;
  text-decoration-color: rgba(116, 185, 255, 0.6);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.15em;
}

.theme-warm .teleprompter-viewport,
.theme-warm.teleprompter-stage {
  background: #14100b;
}

.theme-warm .prompt-content {
  color: #fff3d7;
}

.theme-contrast .teleprompter-viewport,
.theme-contrast.teleprompter-stage {
  background: #000;
}

.theme-contrast .prompt-content {
  color: #fff;
  text-shadow: none;
}

.countdown-overlay {
  position: fixed;
  inset: 0;
  z-index: 5;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.58);
  color: #fff;
  font-size: clamp(96px, 20vw, 220px);
  font-weight: 800;
  pointer-events: none;
}

.shortcut-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  color: #64748b;
  font-size: 12px;
}

.shortcut-strip span {
  padding: 4px 8px;
  border-radius: var(--radius-full);
  background: #f8fafc;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.38);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.finish-modal,
.finish-summary {
  width: min(520px, 100%);
  padding: 26px;
  background: rgba(255, 255, 255, 0.96);
}

.finish-modal h3,
.finish-summary h3 {
  margin: 12px 0 8px;
  color: #1d1d1f;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.04em;
}

.finish-modal p {
  margin: 0;
  color: #6e6e73;
  font-size: 14px;
  line-height: 1.7;
}

.finish-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.finish-summary {
  position: sticky;
  bottom: 0;
  z-index: 9;
  width: 100%;
  border-radius: 28px 28px 0 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.summary-grid span {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px;
  border-radius: 18px;
  background: #f5f5f7;
  color: #6e6e73;
  font-size: 12px;
  font-weight: 800;
}

.summary-grid strong {
  color: #1d1d1f;
  font-size: 24px;
  font-weight: 900;
}

@media (max-width: 1100px) {
  .teleprompter-commandbar,
  .top-settings,
  .teleprompter-workbench {
    grid-template-columns: 1fr;
  }

  .voice-follow-card {
    border-radius: 20px;
  }

  .teleprompter-panel,
  .teleprompter-workbench {
    overflow-y: auto;
  }

  .transport-controls {
    justify-content: flex-start;
    overflow-x: auto;
  }

  .teleprompter-stage {
    min-height: 72vh;
  }
}

@media (max-width: 640px) {
  .teleprompter-panel {
    gap: 12px;
  }

  .teleprompter-sidebar {
    padding: 14px;
  }

  .teleprompter-commandbar {
    padding: 12px;
    border-radius: 22px;
  }

  .transport-btn {
    min-width: 38px;
  }

  .play-btn {
    min-width: 68px;
  }

  .setting-grid,
  .teleprompter-stats,
  .top-settings {
    grid-template-columns: 1fr;
  }

  .stage-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .stage-actions,
  .stage-actions .btn {
    width: 100%;
  }

  .teleprompter-viewport {
    padding: 44px 20px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .finish-actions {
    flex-direction: column-reverse;
  }

  .finish-actions .btn {
    width: 100%;
  }
}

/* Layout refinement: keep existing themes/colors, improve hierarchy and rhythm. */
.teleprompter-panel {
  gap: 22px;
}

.teleprompter-commandbar {
  grid-template-columns: minmax(160px, 0.5fr) minmax(360px, 0.9fr) minmax(280px, 0.8fr);
  gap: 14px 18px;
  align-items: stretch;
  padding: 16px;
}

.command-title,
.transport-controls,
.voice-follow-card {
  align-self: center;
}

.transport-controls {
  justify-content: center;
}

.top-settings {
  grid-column: 1 / -1;
  grid-template-columns: minmax(220px, 1.2fr) minmax(180px, 0.9fr) minmax(180px, 0.9fr) minmax(150px, auto) minmax(240px, 1fr);
  gap: 12px;
}

.teleprompter-workbench {
  grid-template-columns: minmax(320px, 390px) minmax(0, 1fr);
  gap: 22px;
}

.teleprompter-sidebar,
.teleprompter-stage {
  border-radius: 32px;
}

.teleprompter-sidebar {
  padding: 26px;
}

.teleprompter-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-jump-list {
  max-height: 148px;
  overflow-y: auto;
}

.teleprompter-editor-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.teleprompter-editor-actions .btn {
  min-width: 0;
}

.teleprompter-textarea {
  min-height: 360px;
}

.teleprompter-stage {
  min-height: min(760px, calc(100vh - 180px));
}

.stage-toolbar {
  padding: 16px 18px;
}

.teleprompter-viewport {
  padding: clamp(72px, 9vw, 140px) clamp(44px, 8vw, 130px);
}

.shortcut-strip {
  justify-content: center;
  padding: 14px 18px 16px;
}

@media (max-width: 1280px) {
  .teleprompter-commandbar,
  .top-settings {
    grid-template-columns: 1fr 1fr;
  }

  .top-settings {
    grid-column: auto;
  }

  .voice-follow-card,
  .top-settings {
    grid-column: 1 / -1;
  }
}

@media (max-width: 1040px) {
  .teleprompter-commandbar,
  .top-settings,
  .teleprompter-workbench {
    grid-template-columns: 1fr;
  }

  .teleprompter-stage {
    min-height: 72vh;
  }
}

@media (max-width: 640px) {
  .teleprompter-panel {
    gap: 14px;
  }

  .teleprompter-commandbar,
  .teleprompter-sidebar,
  .teleprompter-stage {
    border-radius: 24px;
  }

  .teleprompter-editor-actions,
  .teleprompter-stats {
    grid-template-columns: 1fr;
  }

  .teleprompter-textarea {
    min-height: 260px;
  }
}
</style>

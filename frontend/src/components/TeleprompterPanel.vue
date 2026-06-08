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
type TeleprompterScriptStatus = 'todo' | 'recording' | 'done'
type ReadingWidthMode = 'narrow' | 'standard' | 'wide'
type EyeContactMode = 'natural' | 'camera' | 'distance'
type CameraFocusPosition = 'top' | 'center' | 'leftTop' | 'rightTop'
type RecordingMode = 'practice' | 'formal'

interface TeleprompterScriptItem {
  id: string
  title: string
  text: string
  status: TeleprompterScriptStatus
  scrollTop: number
  progress: number
  cloudDraftId?: number | null
  durationSeconds?: number
  updatedAt: string
}

interface SavedTeleprompterSettings {
  speed: number
  fontSize: number
  lineHeight: number
  theme: ThemeKey
  mirror: boolean
  countdownEnabled: boolean
  readingWidthMode?: ReadingWidthMode
  eyeContactMode?: EyeContactMode
  cameraFocusPosition?: CameraFocusPosition
  recordingMode?: RecordingMode
}

interface SavedTeleprompterState {
  version?: number
  activeScriptId?: string
  scripts?: TeleprompterScriptItem[]
  settings?: SavedTeleprompterSettings
  title?: string
  text?: string
  speed?: number
  fontSize?: number
  lineHeight?: number
  theme?: ThemeKey
  mirror?: boolean
  countdownEnabled?: boolean
  currentScrollPosition?: number
  updatedAt?: string
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

在左侧添加或导入几篇口播文案，点击文案卡片切换录制。录完一篇后，可标记完成并进入下一篇。`

const scriptTitle = ref('未命名提词稿')
const scriptText = ref(defaultText)
const scriptItems = ref<TeleprompterScriptItem[]>([
  createScriptItem({ title: scriptTitle.value, text: scriptText.value }),
])
const activeScriptId = ref(scriptItems.value[0]?.id || '')
const speed = ref(48)
const fontSize = ref(52)
const lineHeight = ref(1.65)
const theme = ref<ThemeKey>('dark')
const readingWidthMode = ref<ReadingWidthMode>('standard')
const eyeContactMode = ref<EyeContactMode>('natural')
const cameraFocusPosition = ref<CameraFocusPosition>('top')
const recordingMode = ref<RecordingMode>('formal')
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
const finishSummary = ref<{ title: string; durationSeconds: number; completionRate: number; wordCount: number } | null>(null)
const sessionStartedAt = ref<number | null>(null)
const lastDraftSavedAt = ref('')
const cloudDraftId = ref<number | null>(null)
const isCloudDraftLoading = ref(false)
const isCloudDraftSaving = ref(false)
const isSourceScriptLoading = ref(false)
const cloudDraftError = ref('')
const cloudDrafts = ref<TeleprompterDraftSummary[]>([])
const cloudDraftPage = ref(1)
const cloudDraftPageSize = 20
const cloudDraftTotal = ref(0)
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

function createScriptId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `script-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function createScriptItem(params: Partial<TeleprompterScriptItem> = {}): TeleprompterScriptItem {
  const text = params.text ?? ''
  return {
    id: params.id || createScriptId(),
    title: (params.title || inferScriptTitle(text) || '未命名提词稿').slice(0, 50),
    text,
    status: params.status === 'recording' || params.status === 'done' ? params.status : 'todo',
    scrollTop: typeof params.scrollTop === 'number' ? Math.max(0, params.scrollTop) : 0,
    progress: typeof params.progress === 'number' ? clamp(params.progress, 0, 100) : 0,
    cloudDraftId: typeof params.cloudDraftId === 'number' ? params.cloudDraftId : null,
    durationSeconds: typeof params.durationSeconds === 'number' ? Math.max(0, params.durationSeconds) : undefined,
    updatedAt: params.updatedAt || new Date().toISOString(),
  }
}

function persistActiveScriptItem(overrides: Partial<TeleprompterScriptItem> = {}) {
  const index = scriptItems.value.findIndex((item) => item.id === activeScriptId.value)
  if (index < 0) return

  const viewport = viewportRef.value
  const current = scriptItems.value[index]
  scriptItems.value[index] = {
    ...current,
    title: scriptTitle.value.trim() || '未命名提词稿',
    text: scriptText.value,
    scrollTop: Math.round(viewport?.scrollTop ?? current.scrollTop ?? 0),
    progress: Math.round(scrollProgress.value),
    cloudDraftId: cloudDraftId.value,
    updatedAt: new Date().toISOString(),
    ...overrides,
  }
}

function hydrateActiveScriptItem(restorePosition = true) {
  const item = activeScriptItem.value
  if (!item) return

  scriptTitle.value = item.title || '未命名提词稿'
  scriptText.value = item.text || ''
  cloudDraftId.value = item.cloudDraftId || null
  currentSegmentIndex.value = -1
  lastTranscript.value = ''
  pendingVoiceMatchIndex.value = -1
  pendingVoiceMatchCount.value = 0

  nextTick(() => {
    setViewportTop(restorePosition ? item.scrollTop || 0 : 0)
    updateProgress()
  })
}

function normalizeScriptItems(items: unknown): TeleprompterScriptItem[] {
  if (!Array.isArray(items)) return []
  return items
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const draft = item as Partial<TeleprompterScriptItem>
      return createScriptItem({
        ...draft,
        id: typeof draft.id === 'string' && draft.id ? draft.id : createScriptId(),
        title: typeof draft.title === 'string' ? draft.title : '未命名提词稿',
        text: typeof draft.text === 'string' ? draft.text : '',
      })
    })
    .filter((item): item is TeleprompterScriptItem => Boolean(item))
}

function replaceActiveScriptContent(title: string, text: string, restorePosition = false) {
  const index = scriptItems.value.findIndex((item) => item.id === activeScriptId.value)
  const nextItem = createScriptItem({
    ...(index >= 0 ? scriptItems.value[index] : {}),
    title: title || inferScriptTitle(text),
    text,
    status: 'todo',
    scrollTop: 0,
    progress: 0,
    durationSeconds: undefined,
    updatedAt: new Date().toISOString(),
  })

  if (index >= 0) {
    scriptItems.value[index] = nextItem
  } else {
    scriptItems.value.push(nextItem)
    activeScriptId.value = nextItem.id
  }

  hydrateActiveScriptItem(restorePosition)
}

function addScriptItem(text = '', title = '') {
  persistActiveScriptItem()
  const item = createScriptItem({
    title: title || (text.trim() ? inferScriptTitle(text) : `口播文案 ${scriptItems.value.length + 1}`),
    text,
  })
  scriptItems.value.push(item)
  activeScriptId.value = item.id
  finishSummary.value = null
  hydrateActiveScriptItem(false)
  message.value = text.trim() ? '已加入新的口播文案。' : '已新增空白口播文案。'
  scheduleDraftSave()
}

function switchScriptItem(targetId: string) {
  if (targetId === activeScriptId.value) return
  if (!scriptItems.value.some((item) => item.id === targetId)) return

  pause()
  stopVoiceFollow(false)
  persistActiveScriptItem()
  activeScriptId.value = targetId
  finishSummary.value = null
  hydrateActiveScriptItem(true)
  message.value = `已切换到：${activeScriptItem.value?.title || '未命名提词稿'}`
  scheduleDraftSave()
}

function removeScriptItem(targetId: string) {
  if (scriptItems.value.length <= 1) {
    message.value = '至少保留一篇口播文案。'
    return
  }

  const target = scriptItems.value.find((item) => item.id === targetId)
  if (!target) return
  if (!window.confirm(`确认删除「${target.title || '未命名提词稿'}」吗？`)) return

  pause()
  stopVoiceFollow(false)
  const targetIndex = scriptItems.value.findIndex((item) => item.id === targetId)
  scriptItems.value = scriptItems.value.filter((item) => item.id !== targetId)
  if (activeScriptId.value === targetId) {
    const nextItem = scriptItems.value[Math.min(targetIndex, scriptItems.value.length - 1)] || scriptItems.value[0]
    activeScriptId.value = nextItem.id
    hydrateActiveScriptItem(true)
  }
  message.value = '已删除口播文案。'
  scheduleDraftSave()
}

function goToRelativeScriptItem(direction: 1 | -1) {
  const nextIndex = clamp(activeScriptIndex.value + direction, 0, scriptItems.value.length - 1)
  const nextItem = scriptItems.value[nextIndex]
  if (!nextItem || nextItem.id === activeScriptId.value) return
  switchScriptItem(nextItem.id)
}

function goToNextPendingScriptItem() {
  const nextItem = scriptItems.value.slice(activeScriptIndex.value + 1).find((item) => item.status !== 'done')
    || scriptItems.value.find((item) => item.status !== 'done')
  if (!nextItem || nextItem.id === activeScriptId.value) return false
  switchScriptItem(nextItem.id)
  return true
}

function getScriptStatusLabel(status: TeleprompterScriptStatus) {
  if (status === 'done') return '已完成'
  if (status === 'recording') return '录制中'
  return '待录'
}

function applyEyeContactMode(mode: EyeContactMode) {
  eyeContactMode.value = mode
  if (mode === 'camera') {
    readingWidthMode.value = 'narrow'
    if (fontSize.value > 64) fontSize.value = 64
    if (lineHeight.value < 1.65) lineHeight.value = 1.65
  } else if (mode === 'distance') {
    readingWidthMode.value = 'wide'
    if (fontSize.value < 64) fontSize.value = 64
    if (lineHeight.value < 1.75) lineHeight.value = 1.75
  } else {
    readingWidthMode.value = 'standard'
  }
  message.value = `已切换到${eyeContactLabel.value}模式。`
}

function formatDuration(seconds?: number) {
  const safeSeconds = Math.max(0, Math.round(seconds || 0))
  const minutes = Math.floor(safeSeconds / 60)
  const restSeconds = safeSeconds % 60
  return `${minutes}:${String(restSeconds).padStart(2, '0')}`
}

function applyIncomingScriptText(text: string, messageText: string) {
  const normalizedText = text.trim()
  if (!normalizedText) return false

  const existing = scriptItems.value.find((item) => item.text.trim() === normalizedText)
  if (existing) {
    switchScriptItem(existing.id)
    message.value = messageText
    return true
  }

  const onlyDefaultScript = scriptItems.value.length === 1
    && (!scriptItems.value[0].text.trim() || scriptItems.value[0].text === defaultText)

  if (onlyDefaultScript) {
    replaceActiveScriptContent(inferScriptTitle(text), text, false)
    message.value = messageText
    return true
  }

  addScriptItem(text, inferScriptTitle(text))
  message.value = messageText
  return true
}

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

const activeScriptItem = computed(() => scriptItems.value.find((item) => item.id === activeScriptId.value) || scriptItems.value[0] || null)

const activeScriptIndex = computed(() => Math.max(0, scriptItems.value.findIndex((item) => item.id === activeScriptId.value)))

const hasNextScriptItem = computed(() => activeScriptIndex.value >= 0 && activeScriptIndex.value < scriptItems.value.length - 1)

const doneScriptCount = computed(() => scriptItems.value.filter((item) => item.status === 'done').length)

const scriptQueueLabel = computed(() => `${activeScriptIndex.value + 1}/${scriptItems.value.length}`)

const hasMoreCloudDrafts = computed(() => cloudDrafts.value.length < cloudDraftTotal.value)

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
  if (isCloudDraftLoading.value) return '正在加载历史口播...'
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
  return formatDuration(finishSummary.value.durationSeconds)
})

const themeClass = computed(() => `theme-${theme.value}`)

const readingWidthClass = computed(() => `reading-width-${readingWidthMode.value}`)

const cameraFocusClass = computed(() => `camera-focus-${cameraFocusPosition.value}`)

const eyeContactLabel = computed(() => {
  if (eyeContactMode.value === 'camera') return '看镜头'
  if (eyeContactMode.value === 'distance') return '远距离'
  return '自然'
})

const recordingModeLabel = computed(() => recordingMode.value === 'formal' ? '正式录制' : '练习模式')

const finishModalDescription = computed(() => recordingMode.value === 'formal'
  ? '当前脚本、显示设置和播放位置会自动保存，正式录制结束后可标记完成并进入下一篇。'
  : '当前脚本、显示设置和播放位置会自动保存，练习结束只保留进度，不会标记文案完成。')

const teleprompterReadinessChecks = computed(() => [
  { label: '文案已准备', passed: Boolean(scriptText.value.trim()) && !isScriptTooLong.value },
  { label: '阅读区已居中', passed: readingWidthMode.value !== 'wide' || fontSize.value >= 44 },
  { label: '字号适合录制', passed: fontSize.value >= 36 && fontSize.value <= 82 },
  { label: '倒计时已开启', passed: countdownEnabled.value },
  { label: '语音跟读可用', passed: voiceSupported.value },
])

const teleprompterRiskTips = computed(() => {
  const tips: string[] = []
  if (readingWidthMode.value === 'wide' && fontSize.value < 44) tips.push('当前阅读区偏宽且字号偏小，录制时眼神可能左右移动。')
  if (fontSize.value > 82) tips.push('字号偏大，长句可能换行频繁，建议切到“远距离”或调低字号。')
  if (!countdownEnabled.value && recordingMode.value === 'formal') tips.push('正式录制建议开启倒计时，避免开头手忙脚乱。')
  if (scriptLength.value > MAX_SCRIPT_LENGTH * 0.85) tips.push('当前文案接近长度上限，建议拆成多篇队列录制。')
  return tips
})

const allReadinessPassed = computed(() => teleprompterReadinessChecks.value.every((item) => item.passed))

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
    applyIncomingScriptText(initialText, '已加入当前口播文案，可点击左侧文案卡片切换录制。')
  }
)

watch(
  [scriptTitle, scriptText, speed, fontSize, lineHeight, theme, readingWidthMode, eyeContactMode, cameraFocusPosition, recordingMode, mirror, countdownEnabled],
  () => {
    persistActiveScriptItem()
    scheduleDraftSave()
  },
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
  persistActiveScriptItem()
  const updatedAt = new Date().toISOString()
  const state: SavedTeleprompterState = {
    version: 2,
    activeScriptId: activeScriptId.value,
    scripts: scriptItems.value,
    settings: {
      speed: speed.value,
      fontSize: fontSize.value,
      lineHeight: lineHeight.value,
      theme: theme.value,
      readingWidthMode: readingWidthMode.value,
      eyeContactMode: eyeContactMode.value,
      cameraFocusPosition: cameraFocusPosition.value,
      recordingMode: recordingMode.value,
      mirror: mirror.value,
      countdownEnabled: countdownEnabled.value,
    },
    updatedAt,
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    lastDraftSavedAt.value = formatTime(updatedAt)
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
    const targetScriptId = activeScriptId.value
    const targetCloudDraftId = cloudDraftId.value
    const payload = buildCloudDraftPayload()
    const res = targetCloudDraftId
      ? await updateTeleprompterDraft(targetCloudDraftId, payload)
      : await createTeleprompterDraft(payload)
    const savedScriptIndex = scriptItems.value.findIndex((item) => item.id === targetScriptId)
    if (savedScriptIndex >= 0) {
      scriptItems.value[savedScriptIndex] = {
        ...scriptItems.value[savedScriptIndex],
        cloudDraftId: res.data.draftId,
      }
    }
    if (activeScriptId.value === targetScriptId) cloudDraftId.value = res.data.draftId
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
  cloudDraftPage.value = 1
  try {
    const res = await listTeleprompterDrafts({ page: cloudDraftPage.value, pageSize: cloudDraftPageSize })
    cloudDrafts.value = res.data.items || []
    cloudDraftTotal.value = res.data.total || cloudDrafts.value.length
  } catch (err: any) {
    cloudDrafts.value = []
    cloudDraftTotal.value = 0
    draftListError.value = getCloudDraftErrorMessage(err, '草稿列表加载失败')
  } finally {
    if (showLoading) isDraftListLoading.value = false
  }
}

async function loadMoreCloudDrafts() {
  if (!isCloudDraftEnabled.value || isDraftListLoading.value || !hasMoreCloudDrafts.value) return
  isDraftListLoading.value = true
  draftListError.value = ''
  try {
    const nextPage = cloudDraftPage.value + 1
    const res = await listTeleprompterDrafts({ page: nextPage, pageSize: cloudDraftPageSize })
    const existingIds = new Set(cloudDrafts.value.map((draft) => draft.draftId))
    const nextItems = (res.data.items || []).filter((draft) => !existingIds.has(draft.draftId))
    cloudDrafts.value = [...cloudDrafts.value, ...nextItems]
    cloudDraftPage.value = nextPage
    cloudDraftTotal.value = res.data.total || cloudDrafts.value.length
  } catch (err: any) {
    draftListError.value = getCloudDraftErrorMessage(err, '更多历史口播加载失败')
  } finally {
    isDraftListLoading.value = false
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
    message.value = '已打开历史口播。'
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
    if (cloudDraftId.value === draftId) {
      cloudDraftId.value = null
      persistActiveScriptItem({ cloudDraftId: null })
    }
    cloudDrafts.value = cloudDrafts.value.filter((draft) => draft.draftId !== draftId)
    cloudDraftTotal.value = Math.max(0, cloudDraftTotal.value - 1)
    message.value = '历史口播已删除。'
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
    readingWidthMode: readingWidthMode.value,
    eyeContactMode: eyeContactMode.value,
    cameraFocusPosition: cameraFocusPosition.value,
    recordingMode: recordingMode.value,
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
    const restoredItems = normalizeScriptItems(state.scripts)
    if (restoredItems.length) {
      scriptItems.value = restoredItems
      activeScriptId.value = restoredItems.some((item) => item.id === state.activeScriptId)
        ? String(state.activeScriptId)
        : restoredItems[0].id
      const settings = (state.settings || {}) as Partial<SavedTeleprompterSettings>
      if (typeof settings.speed === 'number') speed.value = clamp(settings.speed, 1, 100)
      if (typeof settings.fontSize === 'number') fontSize.value = clamp(settings.fontSize, 24, 96)
      if (typeof settings.lineHeight === 'number') lineHeight.value = clamp(settings.lineHeight, 1.2, 2.4)
      if (settings.theme === 'dark' || settings.theme === 'warm' || settings.theme === 'contrast') theme.value = settings.theme
      if (settings.readingWidthMode === 'narrow' || settings.readingWidthMode === 'standard' || settings.readingWidthMode === 'wide') readingWidthMode.value = settings.readingWidthMode
      if (settings.eyeContactMode === 'natural' || settings.eyeContactMode === 'camera' || settings.eyeContactMode === 'distance') eyeContactMode.value = settings.eyeContactMode
      if (settings.cameraFocusPosition === 'top' || settings.cameraFocusPosition === 'center' || settings.cameraFocusPosition === 'leftTop' || settings.cameraFocusPosition === 'rightTop') cameraFocusPosition.value = settings.cameraFocusPosition
      if (settings.recordingMode === 'practice' || settings.recordingMode === 'formal') recordingMode.value = settings.recordingMode
      if (typeof settings.mirror === 'boolean') mirror.value = settings.mirror
      if (typeof settings.countdownEnabled === 'boolean') countdownEnabled.value = settings.countdownEnabled
      hydrateActiveScriptItem(true)
    } else {
      const legacyText = typeof state.text === 'string' ? state.text : ''
      const legacyItem = createScriptItem({
        title: typeof state.title === 'string' ? state.title : inferScriptTitle(legacyText),
        text: legacyText,
        scrollTop: typeof state.currentScrollPosition === 'number' ? state.currentScrollPosition : 0,
      })
      scriptItems.value = [legacyItem]
      activeScriptId.value = legacyItem.id
      hydrateActiveScriptItem(true)
    }
    if (typeof state.speed === 'number') speed.value = clamp(state.speed, 1, 100)
    if (typeof state.fontSize === 'number') fontSize.value = clamp(state.fontSize, 24, 96)
    if (typeof state.lineHeight === 'number') lineHeight.value = clamp(state.lineHeight, 1.2, 2.4)
    if (state.theme === 'dark' || state.theme === 'warm' || state.theme === 'contrast') theme.value = state.theme
    if (typeof state.mirror === 'boolean') mirror.value = state.mirror
    if (typeof state.countdownEnabled === 'boolean') countdownEnabled.value = state.countdownEnabled
    if (typeof state.updatedAt === 'string') lastDraftSavedAt.value = formatTime(state.updatedAt)
  } catch {
    message.value = '已忽略损坏的本地缓存。'
  }
}

function loadInitialText() {
  const initialText = props.initialText?.trim()
  if (!initialText) return false

  return applyIncomingScriptText(props.initialText || '', '已载入当前内容，可开启语音跟读。')
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
    replaceActiveScriptContent(data.title || `${sourceLabel}提词稿`, data.content || '', false)
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
  persistActiveScriptItem()
  const existingIndex = scriptItems.value.findIndex((item) => item.cloudDraftId === draft.draftId)
  const onlyDefaultScript = scriptItems.value.length === 1 && (scriptItems.value[0].text === defaultText || !scriptItems.value[0].text.trim())
  const item = createScriptItem({
    ...(existingIndex >= 0 ? scriptItems.value[existingIndex] : {}),
    title: draft.title || '未命名提词稿',
    text: draft.content || '',
    status: 'todo',
    scrollTop: draft.currentScrollPosition || 0,
    progress: 0,
    cloudDraftId: draft.draftId,
    updatedAt: draft.updatedAt || new Date().toISOString(),
  })

  if (existingIndex >= 0) {
    scriptItems.value[existingIndex] = item
  } else if (onlyDefaultScript) {
    scriptItems.value[0] = item
  } else {
    scriptItems.value.push(item)
  }

  activeScriptId.value = item.id
  applyCloudSettings(draft.settings)
  hydrateActiveScriptItem(true)
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
  if (settings.readingWidthMode === 'narrow' || settings.readingWidthMode === 'standard' || settings.readingWidthMode === 'wide') readingWidthMode.value = settings.readingWidthMode
  if (settings.eyeContactMode === 'natural' || settings.eyeContactMode === 'camera' || settings.eyeContactMode === 'distance') eyeContactMode.value = settings.eyeContactMode
  if (settings.cameraFocusPosition === 'top' || settings.cameraFocusPosition === 'center' || settings.cameraFocusPosition === 'leftTop' || settings.cameraFocusPosition === 'rightTop') cameraFocusPosition.value = settings.cameraFocusPosition
  if (settings.recordingMode === 'practice' || settings.recordingMode === 'formal') recordingMode.value = settings.recordingMode
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
  if (recordingMode.value === 'formal') persistActiveScriptItem({ status: 'recording' })
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
    .map((block) => formatTeleprompterBlock(block))
    .filter(Boolean)
    .join('\n\n')
}

function formatTeleprompterBlock(block: string) {
  return block
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => formatTeleprompterLine(line))
    .join('\n')
}

function formatTeleprompterLine(line: string) {
  const normalizedLine = line
    .replace(/\s+([，。！？；：、,.!?;:])/g, '$1')

  if (looksLikeSpeechStructureHeading(normalizedLine) || getPromptTextLength(normalizedLine) <= MAX_PROMPT_LINE_LENGTH) {
    return normalizedLine
  }

  const sentences = normalizedLine.match(/[^。！？!?；;]+[。！？!?；;]?/g) || [normalizedLine]
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
    if (!looksLikeSpeechStructureHeading(line)) continue

    const segment = segments.find((item) => item.normalized.includes(normalizedLine) || normalizedLine.includes(item.normalized))
    if (!segment || sections.some((section) => section.segmentIndex === segment.index)) continue

    sections.push({
      index: sections.length,
      title: line.replace(/^#{1,6}\s+/, ''),
      segmentIndex: segment.index,
    })
  }

  const blocks = text.split(/\n\s*\n+/).map((block) => block.trim()).filter(Boolean)
  for (const block of blocks) {
    const firstLine = block.split('\n').map((line) => line.trim()).find(Boolean) || ''
    const normalizedBlock = normalizeSpeechText(firstLine || block)
    if (!normalizedBlock) continue

    const segment = segments.find((item) => item.normalized.includes(normalizedBlock) || normalizedBlock.includes(item.normalized))
      || segments.find((item) => item.normalized && normalizedBlock.includes(item.normalized.slice(0, Math.min(12, item.normalized.length))))
    if (!segment || sections.some((section) => section.segmentIndex === segment.index)) continue

    sections.push({
      index: sections.length,
      title: getParagraphSectionTitle(firstLine || block, sections.length),
      segmentIndex: segment.index,
    })
  }

  if (!sections.length && segments.length) {
    sections.push({ index: 0, title: '第 1 段', segmentIndex: 0 })
  }

  return sections.slice(0, 12)
}

function getParagraphSectionTitle(text: string, index: number) {
  const cleaned = text.replace(/^#{1,6}\s+/, '').replace(/[:：]\s*$/, '').trim()
  if (looksLikeSpeechStructureHeading(cleaned)) return cleaned.slice(0, 18)
  const preview = Array.from(cleaned.replace(/\s+/g, '')).slice(0, 10).join('')
  return preview ? `第 ${index + 1} 段：${preview}` : `第 ${index + 1} 段`
}

function looksLikeSpeechStructureHeading(line: string) {
  const trimmed = line.trim()
  if (!trimmed) return false
  if (looksLikePromptTitle(trimmed)) return true
  if (getPromptTextLength(trimmed) > 28) return false
  return /^(开场|开头|引入|痛点|问题|观点|案例|故事|方法|步骤|重点|总结|结尾|收尾|引导|关注|转化|第一部分|第二部分|第三部分|第[一二三四五六七八九十0-9]+[部分章节段]?|[一二三四五六七八九十0-9]+[、.．)]).{0,24}[:：]?$/.test(trimmed)
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
    replaceActiveScriptContent(file.name.replace(/\.[^.]+$/, '').slice(0, 50) || inferScriptTitle(content), content, false)
    nextTick(() => editorRef.value?.focus({ preventScroll: true }))
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
  applyIncomingScriptText(props.initialText, '已将当前口播文案加入队列。')
}

function clearText() {
  if (scriptText.value.trim() && !window.confirm('确认清空当前提词文案吗？此操作不可撤销。')) return
  pause()
  replaceActiveScriptContent('未命名提词稿', '', false)
  nextTick(() => editorRef.value?.focus({ preventScroll: true }))
  message.value = '文案已清空。'
}

function handleEditorInput() {
  if (scriptTitle.value === '未命名提词稿' && scriptText.value.trim()) {
    scriptTitle.value = inferScriptTitle(scriptText.value)
  }
  if (activeScriptItem.value?.status === 'done') persistActiveScriptItem({ status: 'recording', durationSeconds: undefined })
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
  if (activeScriptItem.value?.status === 'done') persistActiveScriptItem({ status: 'recording', durationSeconds: undefined })
  message.value = `已保留原文分段，并优化超过 ${MAX_PROMPT_LINE_LENGTH} 字的长句。`
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

function confirmFinish(goNext = false) {
  pause()
  isInteractionPaused.value = false
  isFinishConfirmOpen.value = false
  const durationSeconds = sessionStartedAt.value ? Math.max(1, Math.round((Date.now() - sessionStartedAt.value) / 1000)) : 0
  const completedTitle = scriptTitle.value.trim() || '未命名提词稿'
  const completionRate = Math.round(scrollProgress.value)
  finishSummary.value = {
    title: completedTitle,
    durationSeconds,
    completionRate,
    wordCount: wordsCount.value,
  }
  persistActiveScriptItem(recordingMode.value === 'formal'
    ? {
        title: completedTitle,
        status: 'done',
        progress: completionRate,
        durationSeconds,
      }
    : {
        title: completedTitle,
        progress: completionRate,
      })
  sessionStartedAt.value = null
  saveDraftState()
  saveCloudDraft()
  reportTeleprompterMetric('teleprompter_finish')
  if (recordingMode.value === 'practice') {
    message.value = '练习已结束，位置已保存，未标记完成。'
  } else if (goNext && goToNextPendingScriptItem()) {
    message.value = `「${completedTitle}」已完成，已切换到下一篇。`
  } else {
    message.value = '本次提词已结束，草稿和位置已保存。'
  }
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
        <em>{{ scriptQueueLabel }} · {{ isPlaying ? '滚动中' : countdown > 0 ? '倒计时' : '待开始' }}</em>
      </div>

      <div class="transport-controls" aria-label="提词器播放控制">
        <button class="transport-btn" title="回到开头" @click="jumpToStart">|‹</button>
        <button class="transport-btn" title="上一篇" @click="goToRelativeScriptItem(-1)">上一篇</button>
        <button class="transport-btn" title="上一段" @click="goToRelativeSection(-1)">上一段</button>
        <button class="transport-btn play-btn" title="播放或暂停" @click="togglePlay">
          {{ isPlaying || countdown > 0 ? 'Pause' : 'Play' }}
        </button>
        <button class="transport-btn interact-btn" :class="{ active: isInteractionPaused }" title="互动暂停" @click="toggleInteractionPause">
          互动
        </button>
        <button class="transport-btn" title="下一段" @click="goToRelativeSection(1)">下一段</button>
        <button class="transport-btn" title="下一篇" @click="goToRelativeScriptItem(1)">下一篇</button>
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

        <div class="theme-picker compact-theme" aria-label="舞台配色">
          <button class="tab-item" :class="{ active: theme === 'dark' }" @click="theme = 'dark'">舞台暗色</button>
          <button class="tab-item" :class="{ active: theme === 'warm' }" @click="theme = 'warm'">暖色舞台</button>
          <button class="tab-item" :class="{ active: theme === 'contrast' }" @click="theme = 'contrast'">高对比舞台</button>
        </div>

        <div class="reading-width-picker setting-group compact">
          <span>阅读宽度</span>
          <div class="reading-width-tabs">
            <button type="button" :class="{ active: readingWidthMode === 'narrow' }" @click="readingWidthMode = 'narrow'">窄</button>
            <button type="button" :class="{ active: readingWidthMode === 'standard' }" @click="readingWidthMode = 'standard'">标准</button>
            <button type="button" :class="{ active: readingWidthMode === 'wide' }" @click="readingWidthMode = 'wide'">宽</button>
          </div>
        </div>
      </div>
    </section>

    <div class="teleprompter-workbench">
      <aside class="teleprompter-sidebar glass-card">
        <div class="teleprompter-title-block">
          <h2>提词文案</h2>
        </div>

        <section class="script-queue-panel">
          <div class="script-queue-head">
            <div>
              <strong>口播队列</strong>
              <span>{{ doneScriptCount }} / {{ scriptItems.length }} 已完成</span>
            </div>
            <button type="button" class="btn btn-ghost btn-sm" @click="addScriptItem()">新增文案</button>
          </div>

          <div class="script-queue-list">
            <article
              v-for="(item, index) in scriptItems"
              :key="item.id"
              class="script-queue-item"
              :class="{ active: item.id === activeScriptId, done: item.status === 'done' }"
            >
              <button type="button" class="script-queue-main" @click="switchScriptItem(item.id)">
                <span>第 {{ index + 1 }} 篇</span>
                <strong>{{ item.title || '未命名提词稿' }}</strong>
                <em>{{ getScriptStatusLabel(item.status) }} · {{ Math.round(item.progress) }}%{{ item.durationSeconds ? ` · ${formatDuration(item.durationSeconds)}` : '' }}</em>
              </button>
              <button type="button" class="script-queue-delete" title="删除口播文案" @click="removeScriptItem(item.id)">删除</button>
            </article>
          </div>
        </section>

        <section class="recording-preflight-panel">
          <div class="preflight-head">
            <div>
              <strong>{{ recordingModeLabel }}</strong>
              <span>{{ eyeContactLabel }} · {{ allReadinessPassed ? '准备就绪' : '建议检查' }}</span>
            </div>
            <div class="recording-mode-switch">
              <button type="button" :class="{ active: recordingMode === 'practice' }" @click="recordingMode = 'practice'">练习</button>
              <button type="button" :class="{ active: recordingMode === 'formal' }" @click="recordingMode = 'formal'">正式</button>
            </div>
          </div>

          <div class="eye-contact-modes">
            <button type="button" :class="{ active: eyeContactMode === 'natural' }" @click="applyEyeContactMode('natural')">自然</button>
            <button type="button" :class="{ active: eyeContactMode === 'camera' }" @click="applyEyeContactMode('camera')">看镜头</button>
            <button type="button" :class="{ active: eyeContactMode === 'distance' }" @click="applyEyeContactMode('distance')">远距离</button>
          </div>

          <div class="camera-focus-grid" aria-label="镜头安全区校准">
            <button type="button" :class="{ active: cameraFocusPosition === 'top' }" @click="cameraFocusPosition = 'top'">上方镜头</button>
            <button type="button" :class="{ active: cameraFocusPosition === 'center' }" @click="cameraFocusPosition = 'center'">中间镜头</button>
            <button type="button" :class="{ active: cameraFocusPosition === 'leftTop' }" @click="cameraFocusPosition = 'leftTop'">左上镜头</button>
            <button type="button" :class="{ active: cameraFocusPosition === 'rightTop' }" @click="cameraFocusPosition = 'rightTop'">右上镜头</button>
          </div>

          <div class="preflight-check-list">
            <span v-for="item in teleprompterReadinessChecks" :key="item.label" :class="{ passed: item.passed }">
              {{ item.passed ? '✓' : '!' }} {{ item.label }}
            </span>
          </div>

          <p v-for="tip in teleprompterRiskTips" :key="tip" class="preflight-risk">{{ tip }}</p>
        </section>

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
              <strong>历史口播</strong>
              <span>{{ cloudDraftTotal ? `已显示 ${cloudDrafts.length} / ${cloudDraftTotal} 条` : '暂无历史' }}</span>
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
              <button type="button" class="cloud-draft-delete" title="删除历史口播" @click="removeCloudDraft(draft.draftId)">删除</button>
            </article>
          </div>

          <button
            v-if="hasMoreCloudDrafts"
            type="button"
            class="cloud-draft-load-more"
            :disabled="isDraftListLoading"
            @click="loadMoreCloudDrafts"
          >{{ isDraftListLoading ? '加载中' : '加载更多历史口播' }}</button>

          <p v-else-if="!draftListError && !cloudDrafts.length" class="cloud-draft-empty">保存一次后，这里会显示你的历史口播文案。</p>
          <p v-else-if="!draftListError" class="cloud-draft-empty">已显示全部历史口播。</p>
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
            <button class="btn btn-ghost btn-sm" :disabled="!hasNextScriptItem" @click="goToRelativeScriptItem(1)">下一篇</button>
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
          :class="[readingWidthClass, cameraFocusClass, { dragging: isDraggingViewport }]"
          tabindex="0"
          @click="handleViewportClick"
          @pointerdown="startViewportDrag"
          @scroll="scheduleProgressUpdate"
          @wheel.passive="handleWheel"
        >
          <div v-if="countdown > 0" class="countdown-overlay">{{ countdown }}</div>
          <div class="reading-guide reading-guide-left" aria-hidden="true"></div>
          <div class="reading-guide reading-guide-right" aria-hidden="true"></div>
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

      </section>
    </div>

    <div v-if="isFinishConfirmOpen" class="modal-backdrop" @click.self="cancelFinish">
      <section class="finish-modal glass-card">
        <span class="badge badge-accent">结束确认</span>
        <h3>确认结束{{ recordingModeLabel }}？</h3>
        <p>{{ finishModalDescription }}</p>
        <div class="finish-actions">
          <button class="btn btn-ghost" @click="cancelFinish">继续提词</button>
          <button class="btn btn-ghost" @click="confirmFinish(false)">
            {{ recordingMode === 'formal' ? '仅标记完成' : '结束练习' }}
          </button>
          <button v-if="recordingMode === 'formal'" class="btn btn-primary" @click="confirmFinish(true)">完成并进入下一篇</button>
        </div>
      </section>
    </div>

    <section v-if="finishSummary" class="finish-summary glass-card">
      <div>
        <span class="badge badge-accent">本次统计</span>
        <h3>{{ finishSummary.title }}</h3>
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
  grid-template-columns: minmax(160px, 1.1fr) minmax(130px, 0.8fr) minmax(130px, 0.8fr) auto minmax(190px, 0.9fr) minmax(170px, 0.8fr);
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

.script-queue-panel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: #f8fafc;
}

.script-queue-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.script-queue-head div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.script-queue-head strong {
  color: #1d1d1f;
  font-size: 14px;
  font-weight: 900;
}

.script-queue-head span {
  color: #6e6e73;
  font-size: 12px;
  font-weight: 800;
}

.script-queue-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}

.script-queue-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 9px;
  border: 1px solid rgba(29, 29, 31, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
}

.script-queue-item.active {
  border-color: rgba(36, 87, 255, 0.3);
  background: #fff;
  box-shadow: 0 12px 28px rgba(36, 87, 255, 0.08);
}

.script-queue-item.done {
  border-color: rgba(16, 185, 129, 0.28);
}

.script-queue-main {
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

.script-queue-main span,
.script-queue-main em {
  color: #86868b;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

.script-queue-main strong {
  overflow: hidden;
  color: #1d1d1f;
  font-size: 13px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-queue-delete {
  padding: 7px 9px;
  border: 0;
  border-radius: 999px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.recording-preflight-panel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(36, 87, 255, 0.12);
  border-radius: 24px;
  background: linear-gradient(135deg, #f8fbff, #f5f7ff);
}

.preflight-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.preflight-head div:first-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.preflight-head strong {
  color: #1d1d1f;
  font-size: 14px;
  font-weight: 900;
}

.preflight-head span {
  color: #6e6e73;
  font-size: 12px;
  font-weight: 800;
}

.recording-mode-switch,
.eye-contact-modes,
.camera-focus-grid {
  display: grid;
  gap: 4px;
  padding: 4px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.recording-mode-switch {
  grid-template-columns: repeat(2, minmax(46px, 1fr));
}

.eye-contact-modes {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.camera-focus-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.recording-mode-switch button,
.eye-contact-modes button,
.camera-focus-grid button {
  min-width: 0;
  padding: 8px 6px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: #64748b;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.recording-mode-switch button.active,
.eye-contact-modes button.active,
.camera-focus-grid button.active {
  background: #2457ff;
  color: #fff;
  box-shadow: 0 8px 18px rgba(36, 87, 255, 0.16);
}

.preflight-check-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preflight-check-list span {
  padding: 5px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #b45309;
  font-size: 11px;
  font-weight: 900;
}

.preflight-check-list span.passed {
  background: #ecfdf5;
  color: #059669;
}

.preflight-risk {
  margin: 0;
  color: #b45309;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.55;
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

.cloud-draft-load-more {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(36, 87, 255, 0.16);
  border-radius: 16px;
  background: #eef3ff;
  color: #2457ff;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.cloud-draft-load-more:disabled {
  cursor: not-allowed;
  opacity: 0.62;
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

.reading-width-picker {
  min-width: 0;
}

.reading-width-picker > span {
  color: #515154;
  font-size: 12px;
  font-weight: 900;
}

.reading-width-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 3px;
  padding: 4px;
  border-radius: 16px;
  background: #f5f5f7;
}

.reading-width-tabs button {
  min-width: 0;
  padding: 8px 6px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: #6e6e73;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.reading-width-tabs button.active {
  background: #fff;
  color: #2457ff;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
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
  --reading-width: clamp(560px, 58vw, 920px);
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

.teleprompter-viewport.reading-width-narrow {
  --reading-width: clamp(460px, 46vw, 720px);
}

.teleprompter-viewport.reading-width-standard {
  --reading-width: clamp(560px, 58vw, 920px);
}

.teleprompter-viewport.reading-width-wide {
  --reading-width: clamp(680px, 68vw, 1100px);
}

.reading-guide {
  position: fixed;
  top: 10vh;
  bottom: 10vh;
  z-index: 2;
  width: 1px;
  background: linear-gradient(to bottom, transparent, rgba(147, 197, 253, 0.3), transparent);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}

.reading-guide-left {
  left: calc(50% - var(--reading-width) / 2);
}

.reading-guide-right {
  left: calc(50% + var(--reading-width) / 2);
}

.teleprompter-viewport:fullscreen .reading-guide {
  opacity: 1;
}

.teleprompter-viewport.camera-focus-top:fullscreen .prompt-content {
  transform-origin: center top;
}

.teleprompter-viewport.camera-focus-center:fullscreen {
  padding-top: clamp(96px, 14vh, 180px);
}

.teleprompter-viewport.camera-focus-leftTop:fullscreen .prompt-content {
  margin-left: calc(50% - var(--reading-width) / 2 - 4vw);
  margin-right: auto;
}

.teleprompter-viewport.camera-focus-rightTop:fullscreen .prompt-content {
  margin-left: auto;
  margin-right: calc(50% - var(--reading-width) / 2 - 4vw);
}

.teleprompter-viewport.camera-focus-leftTop:fullscreen .reading-guide-left {
  left: calc(50% - var(--reading-width) / 2 - 4vw);
}

.teleprompter-viewport.camera-focus-leftTop:fullscreen .reading-guide-right {
  left: calc(50% + var(--reading-width) / 2 - 4vw);
}

.teleprompter-viewport.camera-focus-rightTop:fullscreen .reading-guide-left {
  left: calc(50% - var(--reading-width) / 2 + 4vw);
}

.teleprompter-viewport.camera-focus-rightTop:fullscreen .reading-guide-right {
  left: calc(50% + var(--reading-width) / 2 + 4vw);
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
  width: min(100%, var(--reading-width));
  margin: 0 auto;
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
  background: rgba(253, 203, 110, 0.34);
  color: #ffe08a;
  text-shadow: 0 0 28px rgba(253, 203, 110, 0.5);
}

.prompt-segment.read {
  color: rgba(255, 255, 255, 0.28);
  text-shadow: none;
}

.prompt-segment.next {
  color: rgba(255, 255, 255, 0.92);
  text-decoration: underline;
  text-decoration-color: rgba(116, 185, 255, 0.6);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.15em;
}

.teleprompter-viewport:fullscreen .prompt-segment.active {
  box-shadow: 0 0 0 0.08em rgba(253, 203, 110, 0.12);
}

.teleprompter-viewport:fullscreen .prompt-segment.next {
  color: #c7e8ff;
}

.theme-dark .teleprompter-stage,
.theme-warm .teleprompter-stage,
.theme-contrast .teleprompter-stage {
  background: #fff;
}

.theme-dark .stage-toolbar,
.theme-warm .stage-toolbar,
.theme-contrast .stage-toolbar,
.theme-dark .progress-track,
.theme-warm .progress-track,
.theme-contrast .progress-track {
  background: #fff;
}

.theme-dark .teleprompter-viewport {
  background: #050507;
}

.theme-warm .teleprompter-viewport {
  background: #14100b;
}

.theme-warm .prompt-content {
  color: #fff3d7;
}

.theme-contrast .teleprompter-viewport {
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
  grid-template-columns: minmax(220px, 1.1fr) minmax(170px, 0.85fr) minmax(170px, 0.85fr) minmax(150px, auto) minmax(220px, 0.95fr) minmax(190px, 0.8fr);
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

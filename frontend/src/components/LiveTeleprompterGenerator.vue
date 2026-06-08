<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createLiveTeleprompterTemplate,
  deleteLiveTeleprompterHistory,
  deleteLiveTeleprompterTemplate,
  generateLiveTeleprompterScript,
  getLiveTeleprompterHistory,
  importLiveTeleprompterProducts,
  listLiveTeleprompterHistory,
  listLiveTeleprompterTemplates,
  listLiveTeleprompterThemes,
  preflightLiveTeleprompterScript,
  reviewLiveTeleprompterScript,
  saveLiveTeleprompterHistory,
  updateLiveTeleprompterTemplate,
  type LiveTeleprompterGeneratePayload,
  type LiveTeleprompterGenerateResult,
  type LiveTeleprompterHistorySummary,
  type LiveTeleprompterPreflightFinding,
  type LiveTeleprompterProduct,
  type LiveTeleprompterTemplate,
  type LiveTeleprompterTheme,
} from '../api/teleprompter.api'

interface ProductForm {
  name: string
  category: string
  positioning: string
  originalPrice: string
  livePrice: string
  offer: string
  sellingPointsText: string
  painPointsText: string
  suitableUsers: string
  faqText: string
  notes: string
  durationMinutes: number
}

const emit = defineEmits<{
  sendToPlayer: [text: string]
}>()

const props = defineProps<{
  currentUser?: { token?: string; isGuest?: boolean }
}>()

const feedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const isGenerating = ref(false)
const isHistoryLoading = ref(false)
const isSavingHistory = ref(false)
const isImportingProducts = ref(false)
const isChecking = ref(false)
const isReviewing = ref(false)
const isTemplateSaving = ref(false)
const isPreviewFullscreen = ref(false)
const isControlModeOpen = ref(false)
const isTemplateManagerOpen = ref(false)
const activeControlSectionIndex = ref(0)
const draggedProductIndex = ref(-1)
const result = ref<LiveTeleprompterGenerateResult | null>(null)
const lastPayload = ref<LiveTeleprompterGeneratePayload | null>(null)
const templates = ref<LiveTeleprompterTemplate[]>([])
const themes = ref<LiveTeleprompterTheme[]>([])
const historyItems = ref<LiveTeleprompterHistorySummary[]>([])
const preflightFindings = ref<LiveTeleprompterPreflightFinding[]>([])
const productImportText = ref('')
const reviewMarkdown = ref('')

const form = reactive({
  title: '直播专场台本',
  platform: '视频号',
  liveStart: '20:00',
  liveDurationMinutes: 60,
  gmvTarget: '',
  audience: '对产品感兴趣、需要被快速讲清楚价值和权益的用户',
  style: '专业强转化',
  hostCount: 2,
  hostAName: '主播A',
  hostARole: '主讲控场',
  hostBName: '主播B',
  hostBRole: '副播互动',
  benefits: '关注直播间，评论区互动，按直播间链接领取当场权益。',
  extraRequirements: '',
  complianceMode: true,
  templateKey: 'general_sales',
  themeKey: 'dark_live',
  aiEnhance: false,
  saveHistory: false,
})

const reviewForm = reactive({
  actualGmv: '',
  productResultsText: '',
  winningLines: '',
  weakProducts: '',
  audienceQuestions: '',
  notes: '',
})

const templateForm = reactive<LiveTeleprompterTemplate>({
  key: 'custom_live_template',
  name: '自定义直播模板',
  description: '',
  defaultStyle: '专业强转化',
  openingFocus: '福利和重点',
  productFocus: '痛点-卖点-价格-顾虑-倒计时',
  complianceTips: [],
  sectionBlueprint: [],
})
const templateComplianceText = ref('')
const templateBlueprintText = ref('')
const editingTemplateId = ref<number | null>(null)

const products = ref<ProductForm[]>([
  {
    name: '主推产品',
    category: '核心产品',
    positioning: 'main',
    originalPrice: '',
    livePrice: '',
    offer: '直播间限时权益',
    sellingPointsText: '解决核心痛点\n直播间权益清晰\n适合现场讲解转化',
    painPointsText: '用户不知道怎么选\n担心价格不划算\n担心买完不会用',
    suitableUsers: '首次了解、正在对比、希望先锁定权益的用户',
    faqText: '不确定适不适合怎么办？先拍下锁定权益，再由客服或专业人员确认。',
    notes: '',
    durationMinutes: 15,
  },
])

const positioningOptions = [
  { value: 'main', label: '主推冲单' },
  { value: 'premiere', label: '新品首发' },
  { value: 'traffic', label: '引流拉新' },
  { value: 'profit', label: '利润转化' },
  { value: 'return', label: '返场追单' },
  { value: 'normal', label: '普通产品' },
]

const canGenerate = computed(() => {
  if (isGenerating.value) return false
  return Boolean(form.title.trim() && products.value.some((item) => item.name.trim()))
})

const canUseCloudHistory = computed(() => Boolean(props.currentUser?.token && !props.currentUser?.isGuest))

const activeTemplate = computed(() => templates.value.find((item) => item.key === form.templateKey) || null)

const currentControlSection = computed(() => result.value?.sections[activeControlSectionIndex.value] || null)

const nextControlSection = computed(() => result.value?.sections[activeControlSectionIndex.value + 1] || null)

const resultStats = computed(() => {
  if (!result.value) return []
  return [
    { label: '阶段', value: String(result.value.sections.length) },
    { label: '必背', value: String(result.value.mustRemember.length) },
    { label: '字数', value: String(result.value.plainText.length) },
  ]
})

function splitText(value: string) {
  return value.split(/[\n；;]+/).map((item) => item.trim()).filter(Boolean)
}

function buildPayload(): LiveTeleprompterGeneratePayload {
  const mappedProducts: LiveTeleprompterProduct[] = products.value
    .filter((product) => product.name.trim())
    .map((product) => ({
      name: product.name.trim(),
      category: product.category.trim(),
      positioning: product.positioning,
      originalPrice: product.originalPrice.trim(),
      livePrice: product.livePrice.trim(),
      offer: product.offer.trim(),
      sellingPoints: splitText(product.sellingPointsText),
      painPoints: splitText(product.painPointsText),
      suitableUsers: product.suitableUsers.trim(),
      faq: splitText(product.faqText),
      notes: product.notes.trim(),
      durationMinutes: Number(product.durationMinutes) || 10,
    }))
  return {
    title: form.title.trim(),
    platform: form.platform.trim(),
    liveStart: form.liveStart.trim(),
    liveDurationMinutes: Number(form.liveDurationMinutes) || 60,
    gmvTarget: form.gmvTarget.trim(),
    audience: form.audience.trim(),
    style: form.style.trim(),
    hostCount: Number(form.hostCount) === 2 ? 2 : 1,
    hosts: [
      { name: form.hostAName.trim() || '主播A', role: form.hostARole.trim() || '主讲' },
      { name: form.hostBName.trim() || '主播B', role: form.hostBRole.trim() || '副播' },
    ],
    benefits: form.benefits.trim(),
    extraRequirements: form.extraRequirements.trim(),
    complianceMode: form.complianceMode,
    templateKey: form.templateKey,
    themeKey: form.themeKey,
    aiEnhance: form.aiEnhance,
    saveHistory: form.saveHistory && canUseCloudHistory.value,
    products: mappedProducts,
  }
}

async function generateScript() {
  if (!canGenerate.value) return
  isGenerating.value = true
  feedback.value = { type: 'info', message: '正在生成直播台本。' }
  try {
    const payload = buildPayload()
    lastPayload.value = payload
    const res = await generateLiveTeleprompterScript(payload)
    result.value = res.data
    activeControlSectionIndex.value = 0
    feedback.value = { type: 'success', message: '直播台本已生成，可预览、复制 HTML 或送入提词播放器。' }
    if (res.data.scriptId) await loadHistory()
  } catch (err: any) {
    feedback.value = { type: 'error', message: `生成失败：${err?.response?.data?.detail || err.message || '接口异常'}` }
  } finally {
    isGenerating.value = false
  }
}

async function loadTemplates() {
  try {
    const res = await listLiveTeleprompterTemplates()
    templates.value = res.data.items || []
    if (activeTemplate.value?.defaultStyle && form.style === '专业强转化') {
      form.style = activeTemplate.value.defaultStyle
    }
  } catch {
    templates.value = []
  }
}

async function loadThemes() {
  try {
    const res = await listLiveTeleprompterThemes()
    themes.value = res.data.items || []
  } catch {
    themes.value = []
  }
}

async function importProducts() {
  if (!productImportText.value.trim()) return
  isImportingProducts.value = true
  try {
    const res = await importLiveTeleprompterProducts({ rawText: productImportText.value })
    products.value = res.data.items.map((item) => ({
      name: item.name,
      category: item.category,
      positioning: item.positioning,
      originalPrice: item.originalPrice,
      livePrice: item.livePrice,
      offer: item.offer,
      sellingPointsText: item.sellingPoints.join('\n'),
      painPointsText: item.painPoints.join('\n'),
      suitableUsers: item.suitableUsers,
      faqText: item.faq.join('\n'),
      notes: item.notes,
      durationMinutes: item.durationMinutes,
    }))
    feedback.value = { type: 'success', message: `已导入 ${res.data.count} 个产品。` }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `导入失败：${err?.response?.data?.detail || err.message}` }
  } finally {
    isImportingProducts.value = false
  }
}

async function runPreflight() {
  isChecking.value = true
  try {
    const res = await preflightLiveTeleprompterScript({ request: buildPayload() })
    preflightFindings.value = res.data.items || []
    feedback.value = { type: res.data.passed ? 'success' : 'error', message: res.data.passed ? '生成前检查通过。' : '生成前检查发现必须修复项。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `检查失败：${err?.response?.data?.detail || err.message}` }
  } finally {
    isChecking.value = false
  }
}

function parseReviewProducts() {
  return reviewForm.productResultsText.split('\n').map((line) => {
    const [name, sales, conversion] = line.split(/[\t,，]/).map((item) => item?.trim() || '')
    return name ? { name, sales, conversion } : null
  }).filter(Boolean) as Array<Record<string, unknown>>
}

async function generateReview() {
  isReviewing.value = true
  try {
    const res = await reviewLiveTeleprompterScript({
      scriptId: result.value?.scriptId || null,
      title: `${result.value?.title || form.title} 直播复盘`,
      actualGmv: reviewForm.actualGmv,
      productResults: parseReviewProducts(),
      winningLines: reviewForm.winningLines,
      weakProducts: reviewForm.weakProducts,
      audienceQuestions: reviewForm.audienceQuestions,
      notes: reviewForm.notes,
    })
    reviewMarkdown.value = res.data.markdown
    feedback.value = { type: 'success', message: '直播复盘已生成。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `复盘失败：${err?.response?.data?.detail || err.message}` }
  } finally {
    isReviewing.value = false
  }
}

function editTemplate(item: LiveTeleprompterTemplate) {
  if (!item.isCustom || !item.templateId) return
  editingTemplateId.value = item.templateId
  templateForm.key = item.key
  templateForm.name = item.name
  templateForm.description = item.description
  templateForm.defaultStyle = item.defaultStyle
  templateForm.openingFocus = item.openingFocus
  templateForm.productFocus = item.productFocus
  templateComplianceText.value = (item.complianceTips || []).join('\n')
  templateBlueprintText.value = (item.sectionBlueprint || []).join('\n')
  isTemplateManagerOpen.value = true
}

function resetTemplateForm() {
  editingTemplateId.value = null
  templateForm.key = `custom_live_${Date.now()}`
  templateForm.name = '自定义直播模板'
  templateForm.description = ''
  templateForm.defaultStyle = '专业强转化'
  templateForm.openingFocus = '福利和重点'
  templateForm.productFocus = '痛点-卖点-价格-顾虑-倒计时'
  templateComplianceText.value = ''
  templateBlueprintText.value = ''
}

async function saveTemplate() {
  isTemplateSaving.value = true
  try {
    const payload = {
      ...templateForm,
      complianceTips: splitText(templateComplianceText.value),
      sectionBlueprint: splitText(templateBlueprintText.value),
    }
    if (editingTemplateId.value) {
      await updateLiveTeleprompterTemplate(editingTemplateId.value, payload)
    } else {
      await createLiveTeleprompterTemplate(payload)
    }
    await loadTemplates()
    resetTemplateForm()
    feedback.value = { type: 'success', message: '直播模板已保存。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `保存模板失败：${err?.response?.data?.detail || err.message}` }
  } finally {
    isTemplateSaving.value = false
  }
}

async function removeTemplate(item: LiveTeleprompterTemplate) {
  if (!item.templateId) return
  try {
    await deleteLiveTeleprompterTemplate(item.templateId)
    await loadTemplates()
    feedback.value = { type: 'success', message: '直播模板已删除。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `删除模板失败：${err?.response?.data?.detail || err.message}` }
  }
}

async function loadHistory() {
  if (!canUseCloudHistory.value) return
  isHistoryLoading.value = true
  try {
    const res = await listLiveTeleprompterHistory({ page: 1, pageSize: 12 })
    historyItems.value = res.data.items || []
  } catch {
    historyItems.value = []
  } finally {
    isHistoryLoading.value = false
  }
}

async function openHistoryItem(scriptId: number) {
  try {
    const res = await getLiveTeleprompterHistory(scriptId)
    result.value = {
      scriptId: res.data.scriptId,
      title: res.data.title,
      templateKey: res.data.templateKey,
      themeKey: String((res.data.result as any)?.themeKey || form.themeKey),
      plainText: res.data.plainText,
      html: res.data.html,
      sections: Array.isArray((res.data.result as any)?.sections) ? (res.data.result as any).sections : [],
      mustRemember: Array.isArray((res.data.result as any)?.mustRemember) ? (res.data.result as any).mustRemember : [],
      complianceTips: Array.isArray((res.data.result as any)?.complianceTips) ? (res.data.result as any).complianceTips : [],
      generatedBy: String((res.data.result as any)?.generatedBy || 'history'),
    }
    activeControlSectionIndex.value = 0
    feedback.value = { type: 'success', message: '历史直播台本已载入。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `载入历史失败：${err?.response?.data?.detail || err.message}` }
  }
}

async function removeHistoryItem(scriptId: number) {
  try {
    await deleteLiveTeleprompterHistory(scriptId)
    await loadHistory()
    feedback.value = { type: 'success', message: '历史记录已删除。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `删除失败：${err?.response?.data?.detail || err.message}` }
  }
}

async function saveCurrentHistory() {
  if (!result.value || !canUseCloudHistory.value) return
  isSavingHistory.value = true
  try {
    await saveLiveTeleprompterHistory({
      title: result.value.title,
      templateKey: result.value.templateKey || form.templateKey,
      request: (lastPayload.value || buildPayload()) as unknown as Record<string, unknown>,
      result: result.value as unknown as Record<string, unknown>,
      plainText: result.value.plainText,
      html: result.value.html,
    })
    await loadHistory()
    feedback.value = { type: 'success', message: '直播台本历史已保存。' }
  } catch (err: any) {
    feedback.value = { type: 'error', message: `保存历史失败：${err?.response?.data?.detail || err.message}` }
  } finally {
    isSavingHistory.value = false
  }
}

function addProduct() {
  products.value.push({
    name: `产品 ${products.value.length + 1}`,
    category: '',
    positioning: products.value.length === 0 ? 'main' : 'normal',
    originalPrice: '',
    livePrice: '',
    offer: '',
    sellingPointsText: '',
    painPointsText: '',
    suitableUsers: '',
    faqText: '',
    notes: '',
    durationMinutes: 10,
  })
}

function removeProduct(index: number) {
  if (products.value.length === 1) {
    feedback.value = { type: 'error', message: '至少保留一个产品。' }
    return
  }
  products.value.splice(index, 1)
}

function moveProduct(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= products.value.length) return
  const next = [...products.value]
  const [item] = next.splice(index, 1)
  next.splice(target, 0, item)
  products.value = next
}

function handleDragStart(index: number) {
  draggedProductIndex.value = index
}

function handleDrop(index: number) {
  const from = draggedProductIndex.value
  draggedProductIndex.value = -1
  if (from < 0 || from === index) return
  const next = [...products.value]
  const [item] = next.splice(from, 1)
  next.splice(index, 0, item)
  products.value = next
}

function applyTemplate() {
  if (activeTemplate.value?.defaultStyle) form.style = activeTemplate.value.defaultStyle
}

function prevControlSection() {
  activeControlSectionIndex.value = Math.max(0, activeControlSectionIndex.value - 1)
}

function nextControlSectionStep() {
  if (!result.value?.sections.length) return
  activeControlSectionIndex.value = Math.min(result.value.sections.length - 1, activeControlSectionIndex.value + 1)
}

async function copyText(value: string, label: string) {
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    feedback.value = { type: 'success', message: `${label}已复制。` }
  } catch {
    feedback.value = { type: 'error', message: '复制失败，请手动选择内容复制。' }
  }
}

function downloadHtml() {
  if (!result.value?.html) return
  const blob = new Blob([result.value.html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${result.value.title || '直播台本'}.html`
  link.click()
  URL.revokeObjectURL(url)
  feedback.value = { type: 'success', message: 'HTML 文件已生成下载。' }
}

function sendToPlayer() {
  if (!result.value?.plainText) return
  emit('sendToPlayer', result.value.plainText)
}

onMounted(() => {
  void loadTemplates()
  void loadThemes()
  void loadHistory()
})
</script>

<template>
  <div class="live-generator">
    <section class="generator-hero">
      <div>
        <span class="eyebrow">直播提词器</span>
        <h2>生成可直接上场的 HTML 直播台本</h2>
        <p>按直播主题、主播人数和排品顺序生成时间轴、双播话术、产品卡、返场、必背清单和合规提醒。</p>
      </div>
      <div class="hero-actions">
        <button class="btn btn-primary" :disabled="!canGenerate" @click="generateScript">
          {{ isGenerating ? '生成中...' : '生成直播台本' }}
        </button>
        <button class="btn btn-ghost" :disabled="!result" @click="sendToPlayer">送入提词播放器</button>
        <button class="btn btn-ghost" :disabled="!result" @click="isControlModeOpen = true">场控模式</button>
        <button class="btn btn-ghost" v-if="canUseCloudHistory" @click="isTemplateManagerOpen = true">模板管理</button>
      </div>
    </section>

    <div v-if="feedback" class="feedback" :class="feedback.type">{{ feedback.message }}</div>

    <div class="generator-layout">
      <section class="form-panel">
        <header class="panel-head">
          <h3>直播信息</h3>
          <small>支持行业模板、AI 润色、自动保存历史和场控预览。</small>
        </header>

        <div class="form-grid">
          <label>行业模板<select v-model="form.templateKey" class="input" @change="applyTemplate"><option v-for="item in templates" :key="item.key" :value="item.key">{{ item.name }}</option></select></label>
          <label>HTML 主题<select v-model="form.themeKey" class="input"><option v-for="item in themes" :key="item.key" :value="item.key">{{ item.name }}</option></select></label>
          <label>直播主题<input v-model="form.title" class="input" /></label>
          <label>平台<input v-model="form.platform" class="input" /></label>
          <label>开始时间<input v-model="form.liveStart" class="input" placeholder="20:00" /></label>
          <label>时长<input v-model.number="form.liveDurationMinutes" class="input" type="number" min="10" max="480" /></label>
          <label>GMV 目标<input v-model="form.gmvTarget" class="input" placeholder="例如 8W" /></label>
          <label>直播风格<input v-model="form.style" class="input" /></label>
          <label>主播人数<select v-model.number="form.hostCount" class="input"><option :value="1">1 人直播</option><option :value="2">2 人直播</option></select></label>
          <label>主播 A<input v-model="form.hostAName" class="input" /></label>
          <label v-if="form.hostCount === 2">主播 B<input v-model="form.hostBName" class="input" /></label>
          <label>主播 A 分工<input v-model="form.hostARole" class="input" /></label>
          <label v-if="form.hostCount === 2">主播 B 分工<input v-model="form.hostBRole" class="input" /></label>
          <label class="wide">目标人群<textarea v-model="form.audience" class="input textarea compact"></textarea></label>
          <label class="wide">本场福利<textarea v-model="form.benefits" class="input textarea compact"></textarea></label>
          <label class="wide">补充要求<textarea v-model="form.extraRequirements" class="input textarea compact" placeholder="例如：需要更强逼单、避免医疗绝对承诺、强调预约到店"></textarea></label>
          <label class="check-row"><input v-model="form.complianceMode" type="checkbox" />开启合规与场控提醒</label>
          <label class="check-row"><input v-model="form.aiEnhance" type="checkbox" />启用 AI 深度润色（不可用时自动规则兜底）</label>
          <label class="check-row" :class="{ disabled: !canUseCloudHistory }"><input v-model="form.saveHistory" type="checkbox" :disabled="!canUseCloudHistory" />生成后自动保存历史{{ canUseCloudHistory ? '' : '（登录后可用）' }}</label>
        </div>

        <div v-if="activeTemplate" class="template-hint">
          <strong>{{ activeTemplate.name }}</strong>
          <span>{{ activeTemplate.description }}</span>
          <small>结构：{{ activeTemplate.productFocus }}</small>
        </div>

        <div class="product-headline">
          <div>
            <h3>排品编辑器</h3>
            <small>按真实直播顺序添加产品，主推品建议放前面。</small>
          </div>
          <button class="btn btn-ghost btn-sm" @click="addProduct">添加产品</button>
        </div>

        <details class="import-box">
          <summary>批量导入产品表</summary>
          <textarea v-model="productImportText" class="input textarea" placeholder="支持粘贴 Excel/CSV：产品名称,类别,直播价,原价,权益,卖点,痛点"></textarea>
          <button class="btn btn-primary btn-sm" :disabled="!productImportText.trim() || isImportingProducts" @click="importProducts">{{ isImportingProducts ? '导入中...' : '解析并替换排品' }}</button>
        </details>

        <article
          v-for="(product, index) in products"
          :key="index"
          class="product-form"
          :class="{ dragging: draggedProductIndex === index }"
          draggable="true"
          @dragstart="handleDragStart(index)"
          @dragover.prevent
          @drop="handleDrop(index)"
        >
          <div class="product-form-top">
            <strong>产品 {{ index + 1 }}</strong>
            <div class="product-actions">
              <button class="btn btn-ghost btn-sm" :disabled="index === 0" @click="moveProduct(index, -1)">上移</button>
              <button class="btn btn-ghost btn-sm" :disabled="index === products.length - 1" @click="moveProduct(index, 1)">下移</button>
              <button class="btn btn-ghost btn-sm" @click="removeProduct(index)">删除</button>
            </div>
          </div>
          <div class="form-grid compact-grid">
            <label>名称<input v-model="product.name" class="input" /></label>
            <label>类别<input v-model="product.category" class="input" /></label>
            <label>定位<select v-model="product.positioning" class="input"><option v-for="item in positioningOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label>讲解分钟<input v-model.number="product.durationMinutes" class="input" type="number" min="1" max="120" /></label>
            <label>原价<input v-model="product.originalPrice" class="input" /></label>
            <label>直播价<input v-model="product.livePrice" class="input" /></label>
            <label class="wide">优惠/权益<textarea v-model="product.offer" class="input textarea compact"></textarea></label>
            <label class="wide">用户痛点<textarea v-model="product.painPointsText" class="input textarea compact" placeholder="一行一个痛点"></textarea></label>
            <label class="wide">核心卖点<textarea v-model="product.sellingPointsText" class="input textarea compact" placeholder="一行一个卖点"></textarea></label>
            <label class="wide">适合人群<textarea v-model="product.suitableUsers" class="input textarea compact"></textarea></label>
            <label class="wide">FAQ<textarea v-model="product.faqText" class="input textarea compact" placeholder="一行一个常见问题"></textarea></label>
            <label class="wide">备注<textarea v-model="product.notes" class="input textarea compact"></textarea></label>
          </div>
        </article>

        <section class="preflight-panel">
          <div class="history-head">
            <strong>直播前检查清单</strong>
            <button class="btn btn-ghost btn-sm" :disabled="isChecking" @click="runPreflight">{{ isChecking ? '检查中...' : '开始检查' }}</button>
          </div>
          <ul v-if="preflightFindings.length" class="preflight-list">
            <li v-for="item in preflightFindings" :key="item.label" :class="item.severity">
              <strong>{{ item.label }}</strong>
              <span>{{ item.suggestion }}</span>
            </li>
          </ul>
          <p v-else class="history-empty">生成前建议先检查价格、卖点、权益、返场和合规表达。</p>
        </section>
      </section>

      <section class="result-panel">
        <header class="panel-head result-head">
          <div>
            <h3>生成结果</h3>
            <small>HTML 可直接保存后在直播现场打开使用。</small>
          </div>
          <div class="result-actions">
            <button class="btn btn-ghost btn-sm" :disabled="!result" @click="copyText(result?.html || '', 'HTML')">复制 HTML</button>
            <button class="btn btn-ghost btn-sm" :disabled="!result" @click="copyText(result?.plainText || '', '纯文本')">复制纯文本</button>
            <button class="btn btn-ghost btn-sm" :disabled="!result || !canUseCloudHistory || isSavingHistory" @click="saveCurrentHistory">保存历史</button>
            <button class="btn btn-primary btn-sm" :disabled="!result" @click="downloadHtml">导出 HTML</button>
          </div>
        </header>

        <div v-if="canUseCloudHistory" class="history-panel">
          <div class="history-head">
            <strong>历史台本</strong>
            <button class="btn btn-ghost btn-sm" :disabled="isHistoryLoading" @click="loadHistory">刷新</button>
          </div>
          <div v-if="historyItems.length" class="history-list">
            <button v-for="item in historyItems" :key="item.scriptId" class="history-item" @click="openHistoryItem(item.scriptId)">
              <strong>{{ item.title }}</strong>
              <span>{{ item.sectionCount }} 阶段 · {{ item.wordCount }} 字</span>
            </button>
            <button v-for="item in historyItems" :key="`delete-${item.scriptId}`" class="history-delete" @click="removeHistoryItem(item.scriptId)">删除</button>
          </div>
          <p v-else class="history-empty">暂无历史台本。</p>
        </div>

        <div v-if="result" class="result-stats">
          <span v-for="item in resultStats" :key="item.label"><strong>{{ item.value }}</strong>{{ item.label }}</span>
        </div>

        <div v-if="result" class="preview-shell">
          <div class="preview-toolbar">
            <span>{{ result.title }}</span>
            <button class="btn btn-ghost btn-sm" @click="isPreviewFullscreen = true">全屏预览</button>
          </div>
          <iframe class="html-preview" :srcdoc="result.html" title="直播 HTML 台本预览"></iframe>
        </div>

        <div v-if="result" class="plain-output">
          <h4>主播必背清单</h4>
          <ul>
            <li v-for="item in result.mustRemember" :key="item">{{ item }}</li>
          </ul>
          <h4>纯文本台本</h4>
          <pre>{{ result.plainText }}</pre>
        </div>

        <div v-if="result" class="review-panel">
          <h4>直播复盘</h4>
          <div class="form-grid compact-grid">
            <label>实际 GMV<input v-model="reviewForm.actualGmv" class="input" placeholder="例如 12.6W" /></label>
            <label class="wide">产品结果<textarea v-model="reviewForm.productResultsText" class="input textarea compact" placeholder="一行一个：产品名,成交件数,表现"></textarea></label>
            <label class="wide">高转化话术<textarea v-model="reviewForm.winningLines" class="input textarea compact"></textarea></label>
            <label class="wide">弱项产品<textarea v-model="reviewForm.weakProducts" class="input textarea compact"></textarea></label>
            <label class="wide">用户高频问题<textarea v-model="reviewForm.audienceQuestions" class="input textarea compact"></textarea></label>
            <label class="wide">备注<textarea v-model="reviewForm.notes" class="input textarea compact"></textarea></label>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="isReviewing" @click="generateReview">{{ isReviewing ? '生成中...' : '生成复盘报告' }}</button>
          <pre v-if="reviewMarkdown" class="review-output">{{ reviewMarkdown }}</pre>
        </div>

        <div v-else class="empty-result">
          <strong>还没有生成台本</strong>
          <p>填好直播信息和至少一个产品后，点击“生成直播台本”。</p>
        </div>
      </section>
    </div>

    <div v-if="isPreviewFullscreen && result" class="preview-modal" role="dialog" aria-modal="true">
      <div class="preview-modal-head">
        <strong>{{ result.title }}</strong>
        <button class="btn btn-ghost btn-sm" @click="isPreviewFullscreen = false">关闭</button>
      </div>
      <iframe class="preview-modal-frame" :srcdoc="result.html" title="全屏直播 HTML 台本预览"></iframe>
    </div>

    <div v-if="isControlModeOpen && result" class="control-modal" role="dialog" aria-modal="true">
      <aside class="control-side">
        <div class="control-side-head">
          <strong>场控模式</strong>
          <button class="btn btn-ghost btn-sm" @click="isControlModeOpen = false">关闭</button>
        </div>
        <button
          v-for="(section, index) in result.sections"
          :key="section.sectionId"
          class="control-section-btn"
          :class="{ active: activeControlSectionIndex === index }"
          @click="activeControlSectionIndex = index"
        >
          <strong>{{ section.title }}</strong>
          <span>{{ section.timeRange }} · {{ section.goal }}</span>
        </button>
      </aside>
      <main class="control-stage">
        <div class="control-stage-head">
          <button class="btn btn-ghost" :disabled="activeControlSectionIndex === 0" @click="prevControlSection">上一段</button>
          <div>
            <strong>{{ currentControlSection?.title }}</strong>
            <span>{{ currentControlSection?.timeRange }} · {{ currentControlSection?.goal }}</span>
          </div>
          <button class="btn btn-primary" :disabled="!nextControlSection" @click="nextControlSectionStep">下一段</button>
        </div>
        <pre class="control-script">{{ currentControlSection?.plainText }}</pre>
        <div v-if="nextControlSection" class="control-next">
          <strong>下一段</strong>
          <span>{{ nextControlSection.title }}｜{{ nextControlSection.timeRange }}</span>
        </div>
      </main>
    </div>

    <div v-if="isTemplateManagerOpen" class="template-modal" role="dialog" aria-modal="true">
      <section class="template-manager">
        <div class="preview-modal-head">
          <strong>直播模板管理</strong>
          <button class="btn btn-ghost btn-sm" @click="isTemplateManagerOpen = false">关闭</button>
        </div>
        <div class="template-manager-grid">
          <aside class="template-list">
            <button v-for="item in templates.filter((t) => t.isCustom)" :key="item.key" class="history-item" @click="editTemplate(item)">
              <strong>{{ item.name }}</strong>
              <span>{{ item.key }}</span>
            </button>
            <p v-if="!templates.some((t) => t.isCustom)" class="history-empty">暂无自定义模板。</p>
          </aside>
          <main class="template-form">
            <div class="form-grid">
              <label>Key<input v-model="templateForm.key" class="input" /></label>
              <label>名称<input v-model="templateForm.name" class="input" /></label>
              <label class="wide">描述<textarea v-model="templateForm.description" class="input textarea compact"></textarea></label>
              <label class="wide">默认风格<input v-model="templateForm.defaultStyle" class="input" /></label>
              <label class="wide">开场重点<textarea v-model="templateForm.openingFocus" class="input textarea compact"></textarea></label>
              <label class="wide">产品结构<textarea v-model="templateForm.productFocus" class="input textarea compact"></textarea></label>
              <label class="wide">合规提示<textarea v-model="templateComplianceText" class="input textarea compact" placeholder="一行一条"></textarea></label>
              <label class="wide">阶段蓝图<textarea v-model="templateBlueprintText" class="input textarea compact" placeholder="一行一个阶段"></textarea></label>
            </div>
            <div class="hero-actions">
              <button class="btn btn-primary" :disabled="isTemplateSaving" @click="saveTemplate">{{ isTemplateSaving ? '保存中...' : '保存模板' }}</button>
              <button class="btn btn-ghost" @click="resetTemplateForm">新建</button>
              <button v-if="editingTemplateId" class="btn btn-ghost" @click="removeTemplate({ ...templateForm, templateId: editingTemplateId, isCustom: true })">删除</button>
            </div>
          </main>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.live-generator {
  display: grid;
  gap: 18px;
  width: 100%;
}

.generator-hero,
.form-panel,
.result-panel {
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: var(--shadow-sm);
}

.generator-hero {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 24px;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--color-accent-primary);
  font-size: 12px;
  font-weight: 850;
}

.generator-hero h2,
.panel-head h3,
.product-headline h3 {
  margin: 0;
  color: var(--color-text-primary);
  font-family: var(--font-display);
  letter-spacing: -0.04em;
}

.generator-hero h2 {
  font-size: clamp(26px, 3vw, 38px);
  line-height: 1.08;
}

.generator-hero p,
.panel-head small,
.product-headline small {
  color: var(--color-text-muted);
}

.generator-hero p {
  max-width: 720px;
  margin: 10px 0 0;
  line-height: 1.7;
}

.hero-actions,
.result-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.generator-layout {
  display: grid;
  grid-template-columns: minmax(360px, 0.95fr) minmax(420px, 1.05fr);
  gap: 18px;
  align-items: start;
}

.form-panel,
.result-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
}

.panel-head,
.product-headline,
.product-form-top,
.result-head,
.preview-toolbar,
.preview-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label,
.check-row {
  display: grid;
  gap: 7px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 750;
}

.wide {
  grid-column: 1 / -1;
}

.check-row {
  grid-column: 1 / -1;
  grid-template-columns: auto 1fr;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #f8fafc;
}

.check-row.disabled {
  opacity: 0.62;
}

.template-hint {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid #dbe6ff;
  border-radius: 16px;
  background: #f5f8ff;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.template-hint strong {
  color: var(--color-accent-primary);
}

.input {
  width: 100%;
  min-height: 40px;
  padding: 9px 11px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: #fff;
  color: var(--color-text-primary);
  font: inherit;
  font-size: 13px;
}

.textarea {
  min-height: 96px;
  resize: vertical;
}

.textarea.compact {
  min-height: 72px;
}

.product-form {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #f8fafc;
}

.import-box,
.preflight-panel,
.review-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: #fff;
}

.import-box summary {
  cursor: pointer;
  color: var(--color-text-primary);
  font-weight: 850;
}

.product-form.dragging {
  border-color: rgba(36, 87, 255, 0.45);
  background: #eef3ff;
}

.product-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.compact-grid {
  gap: 10px;
}

.feedback {
  padding: 12px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 760;
}

.feedback.info {
  background: #eff6ff;
  color: #1d4ed8;
}

.feedback.success {
  background: #ecfdf5;
  color: #047857;
}

.feedback.error {
  background: #fef2f2;
  color: #b91c1c;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.result-stats span {
  display: grid;
  gap: 2px;
  padding: 12px;
  border: 1px solid #dbe6ff;
  border-radius: 16px;
  background: #f5f8ff;
  color: var(--color-text-muted);
  font-size: 12px;
}

.result-stats strong {
  color: var(--color-accent-primary);
  font-size: 22px;
}

.history-panel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: #f8fafc;
}

.history-head,
.history-list {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-head {
  justify-content: space-between;
}

.history-list {
  flex-wrap: wrap;
}

.history-item,
.history-delete {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  font: inherit;
}

.preflight-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.preflight-list li {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border-radius: 14px;
  font-size: 13px;
}

.preflight-list li.success {
  background: #ecfdf5;
  color: #047857;
}

.preflight-list li.warning {
  background: #fffbeb;
  color: #b45309;
}

.preflight-list li.error {
  background: #fef2f2;
  color: #b91c1c;
}

.history-item {
  display: grid;
  gap: 3px;
  min-width: 190px;
  padding: 10px 12px;
  text-align: left;
}

.history-item strong {
  color: var(--color-text-primary);
  font-size: 13px;
}

.history-item span,
.history-empty {
  color: var(--color-text-muted);
  font-size: 12px;
}

.history-delete {
  padding: 9px 10px;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 800;
}

.preview-shell {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: #0f172a;
}

.preview-toolbar {
  min-height: 48px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 800;
}

.html-preview {
  display: block;
  width: 100%;
  height: 520px;
  border: 0;
  background: #0f172a;
}

.plain-output {
  display: grid;
  gap: 10px;
}

.plain-output h4 {
  margin: 0;
  color: var(--color-text-primary);
}

.plain-output ul {
  display: grid;
  gap: 7px;
  margin: 0;
  padding-left: 18px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.plain-output pre {
  max-height: 520px;
  overflow: auto;
  margin: 0;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #f8fafc;
  color: #0f172a;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}

.review-panel h4 {
  margin: 0;
  color: var(--color-text-primary);
}

.review-output {
  max-height: 420px;
  overflow: auto;
  margin: 0;
  padding: 14px;
  border-radius: 14px;
  background: #0f172a;
  color: #e2e8f0;
  white-space: pre-wrap;
  line-height: 1.7;
}

.empty-result {
  display: grid;
  place-items: center;
  min-height: 420px;
  padding: 28px;
  border: 1px dashed #cbd5e1;
  border-radius: 20px;
  color: var(--color-text-muted);
  text-align: center;
}

.empty-result strong {
  color: var(--color-text-primary);
  font-size: 18px;
}

.preview-modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  grid-template-rows: auto 1fr;
  background: #020617;
}

.preview-modal-head {
  min-height: 58px;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  color: #e2e8f0;
}

.preview-modal-frame {
  width: 100%;
  height: 100%;
  border: 0;
}

.control-modal {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  grid-template-columns: 320px 1fr;
  background: #020617;
  color: #e2e8f0;
}

.control-side {
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 16px;
  border-right: 1px solid rgba(255, 255, 255, 0.12);
  background: #0f172a;
  overflow: auto;
}

.control-side-head,
.control-stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.control-section-btn {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.72);
  color: #cbd5e1;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.control-section-btn.active {
  border-color: #38bdf8;
  background: rgba(14, 116, 144, 0.38);
  color: #f8fafc;
}

.control-section-btn span,
.control-stage-head span,
.control-next span {
  color: #94a3b8;
  font-size: 12px;
}

.control-stage {
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 16px;
  padding: 20px;
  min-width: 0;
}

.control-stage-head {
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.84);
}

.control-stage-head div {
  display: grid;
  gap: 3px;
  text-align: center;
}

.control-script {
  overflow: auto;
  margin: 0;
  padding: 28px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 24px;
  background: #08111f;
  color: #f8fafc;
  font-family: var(--font-sans);
  font-size: clamp(26px, 3vw, 46px);
  line-height: 1.72;
  white-space: pre-wrap;
}

.control-next {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(250, 204, 21, 0.28);
  border-radius: 16px;
  background: rgba(113, 63, 18, 0.34);
}

.template-modal {
  position: fixed;
  inset: 0;
  z-index: 95;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(2, 6, 23, 0.72);
}

.template-manager {
  width: min(1100px, 100%);
  max-height: min(860px, 92vh);
  overflow: hidden;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.32);
}

.template-manager .preview-modal-head {
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
}

.template-manager-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  padding: 18px;
  overflow: auto;
  max-height: calc(92vh - 64px);
}

.template-list,
.template-form {
  display: grid;
  align-content: start;
  gap: 12px;
}

@media (max-width: 1180px) {
  .generator-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .generator-hero,
  .panel-head,
  .product-headline,
  .result-head {
    align-items: stretch;
    flex-direction: column;
  }

  .form-grid,
  .result-stats {
    grid-template-columns: 1fr;
  }

  .hero-actions,
  .result-actions {
    width: 100%;
  }

  .control-modal {
    grid-template-columns: 1fr;
    grid-template-rows: 220px 1fr;
  }

  .template-manager-grid {
    grid-template-columns: 1fr;
  }
}
</style>

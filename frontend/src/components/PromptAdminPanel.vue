<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import ConfirmDialog from './ConfirmDialog.vue'
import { useConfirmDialog } from '../composables/useConfirmDialog'
import { modePathMap } from '../stores/workspace'
import {
  createPromptTemplate,
  createPromptTemplateCategory,
  deletePromptTemplate,
  deletePromptTemplateCategory,
  getPromptTemplate,
  listPromptTemplateMetrics,
  listPromptTemplateCategories,
  listPromptTemplates,
  listPromptTemplateVersions,
  updatePromptTemplate,
  updatePromptTemplateCategory,
  type PromptTemplateCategoryData,
  type PromptTemplateData,
  type PromptTemplateMetricData,
  type PromptTemplateVersionData,
} from '../api/promptTemplates.api'
import {
  createModelConfig,
  deleteModelConfig,
  listModelCatalog,
  listModelConfigs,
  type AIModelConfigData,
} from '../api/modelConfig.api'

interface WorkspaceUser {
  name: string
  email: string
  token?: string
  isGuest?: boolean
  is_admin?: boolean
}

const props = defineProps<{ currentUser?: WorkspaceUser }>()

const router = useRouter()
const { confirmState, requestConfirmation, resolveConfirmation } = useConfirmDialog()

const promptTemplateCategories = ref<PromptTemplateCategoryData[]>([])
const promptManagerTemplates = ref<PromptTemplateData[]>([])
const promptTemplateMetrics = ref<Record<string, PromptTemplateMetricData>>({})
const modelManagerConfigs = ref<AIModelConfigData[]>([])
const promptManagerCategoryKey = ref('')
const promptManagerFeedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const isSavingPromptCategory = ref(false)
const isSavingPromptTemplate = ref(false)
const isSavingModelConfig = ref(false)
const editingPromptCategoryKey = ref('')
const editingPromptTemplateId = ref(0)
const promptTemplateVersions = ref<PromptTemplateVersionData[]>([])

const promptCategoryForm = reactive<PromptTemplateCategoryData>({
  key: '',
  name: '',
  description: '',
  sort_order: 0,
  is_active: true,
})

const promptTemplateForm = reactive<PromptTemplateData>({
  id: 0,
  key: '',
  category_key: '',
  platform: '',
  scene: '',
  step: '',
  name: '',
  description: '',
  scenario: '',
  output_structure: '',
  writing_rules: [],
  prompt_body: '',
  version: '1.0.0',
  is_default: false,
  is_active: true,
  sort_order: 0,
  change_note: '',
})
const promptTemplateRulesText = ref('')

const promptTemplateRiskFindings = computed(() => {
  const text = [
    promptTemplateForm.name,
    promptTemplateForm.description,
    promptTemplateForm.output_structure,
    promptTemplateRulesText.value,
    promptTemplateForm.prompt_body || '',
  ].join('\n')
  const lower = text.toLowerCase()
  const findings: string[] = []
  if (/(api[_-]?key|secret|token|password)\s*[:=]\s*['"]?[A-Za-z0-9_./+=-]{24,}/i.test(text) || /sk-[A-Za-z0-9_-]{20,}/.test(text)) {
    findings.push('疑似包含密钥、令牌或密码')
  }
  const blocked = [
    ['ignore previous instructions', '要求模型忽略上文/系统指令'],
    ['ignore all previous instructions', '要求模型忽略上文/系统指令'],
    ['reveal system prompt', '要求泄露系统提示词'],
    ['print system prompt', '要求输出系统提示词'],
    ['bypass safety', '要求绕过安全策略'],
    ['jailbreak', '疑似越狱提示词'],
    ['忽略之前', '要求模型忽略上文/系统指令'],
    ['忽略以上', '要求模型忽略上文/系统指令'],
    ['泄露系统提示词', '要求泄露系统提示词'],
    ['输出系统提示词', '要求输出系统提示词'],
    ['绕过安全', '要求绕过安全策略'],
    ['越狱', '疑似越狱提示词'],
  ]
  blocked.forEach(([phrase, label]) => {
    if (lower.includes(phrase)) findings.push(label)
  })
  return Array.from(new Set(findings))
})

const modelConfigForm = reactive<AIModelConfigData>({
  name: '',
  model_type: 'text',
  provider: 'custom',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model_id: '',
  is_openai_compatible: true,
  is_default: false,
  is_active: true,
  timeout_seconds: 180,
  max_retries: 2,
  sort_order: 0,
  notes: '',
})

const liveStatusMessage = computed(() => promptManagerFeedback.value?.message || '')

async function loadPromptTemplateCategories() {
  try {
    const res = await listPromptTemplateCategories()
    promptTemplateCategories.value = res.data || []
    if (!promptManagerCategoryKey.value && promptTemplateCategories.value.length) {
      promptManagerCategoryKey.value = promptTemplateCategories.value[0].key
    }
  } catch {
    promptTemplateCategories.value = []
  }
}

async function loadPromptManagerTemplates() {
  try {
    const res = await listPromptTemplates(promptManagerCategoryKey.value)
    promptManagerTemplates.value = res.data || []
  } catch {
    promptManagerTemplates.value = []
  }
}

async function loadPromptTemplateMetrics() {
  try {
    const res = await listPromptTemplateMetrics()
    promptTemplateMetrics.value = Object.fromEntries(
      (res.data || []).map((item) => [`${item.templateType}:${item.templateId}`, item]),
    )
  } catch {
    promptTemplateMetrics.value = {}
  }
}

async function loadModelManagerConfigs() {
  try {
    const res = await listModelCatalog()
    modelManagerConfigs.value = res.data || []
  } catch {
    try {
      const res = await listModelConfigs()
      modelManagerConfigs.value = res.data || []
    } catch {
      modelManagerConfigs.value = []
    }
  }
}

async function refreshPromptData() {
  await loadPromptTemplateCategories()
  await loadPromptManagerTemplates()
  await loadPromptTemplateMetrics()
  await loadModelManagerConfigs()
}

watch(promptManagerCategoryKey, () => {
  resetPromptTemplateForm()
  loadPromptManagerTemplates()
})

function resetPromptCategoryForm() {
  editingPromptCategoryKey.value = ''
  Object.assign(promptCategoryForm, {
    key: '',
    name: '',
    description: '',
    sort_order: 0,
    is_active: true,
  })
}

function editPromptCategory(category: PromptTemplateCategoryData) {
  editingPromptCategoryKey.value = category.key
  Object.assign(promptCategoryForm, {
    key: category.key,
    name: category.name,
    description: category.description,
    sort_order: category.sort_order || 0,
    is_active: category.is_active !== false,
  })
}

function resetPromptTemplateForm() {
  editingPromptTemplateId.value = 0
  Object.assign(promptTemplateForm, {
    id: 0,
    key: '',
    category_key: promptManagerCategoryKey.value || 'knowledge_talk',
    platform: '',
    scene: '',
    step: '',
    name: '',
    description: '',
    scenario: '',
    output_structure: '',
    writing_rules: [],
    prompt_body: '',
    version: '1.0.0',
    is_default: false,
    is_active: true,
    sort_order: 0,
    change_note: '',
  })
  promptTemplateRulesText.value = ''
  promptTemplateVersions.value = []
}

function resetModelConfigForm() {
  Object.assign(modelConfigForm, {
    name: '',
    model_type: 'text',
    provider: 'custom',
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    model_id: '',
    is_openai_compatible: true,
    is_default: false,
    is_active: true,
    timeout_seconds: 180,
    max_retries: 2,
    sort_order: 0,
    notes: '',
  })
}

async function handleSavePromptCategory() {
  if (isSavingPromptCategory.value) return
  if (!promptCategoryForm.key.trim() || !promptCategoryForm.name.trim()) {
    promptManagerFeedback.value = { type: 'error', message: '请填写分类 Key 和分类名称。' }
    return
  }
  isSavingPromptCategory.value = true
  try {
    if (editingPromptCategoryKey.value) {
      await updatePromptTemplateCategory(editingPromptCategoryKey.value, promptCategoryForm)
      promptManagerFeedback.value = { type: 'success', message: '提示词分类已更新。' }
    } else {
      await createPromptTemplateCategory(promptCategoryForm)
      promptManagerFeedback.value = { type: 'success', message: '提示词分类已创建。' }
    }
    promptManagerCategoryKey.value = promptCategoryForm.key
    resetPromptCategoryForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '保存分类失败。' }
  } finally {
    isSavingPromptCategory.value = false
  }
}

async function handleDeletePromptCategory(category: PromptTemplateCategoryData) {
  const confirmed = await requestConfirmation({
    title: '停用提示词分类',
    message: `确认停用提示词分类「${category.name}」吗？该分类下模板也会停用。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deletePromptTemplateCategory(category.key)
    promptManagerFeedback.value = { type: 'success', message: `已停用分类「${category.name}」。` }
    if (promptManagerCategoryKey.value === category.key) promptManagerCategoryKey.value = ''
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用分类失败。' }
  }
}

async function editPromptTemplate(template: PromptTemplateData) {
  try {
    const res = await getPromptTemplate(template.id)
    const detail = res.data as PromptTemplateData
    editingPromptTemplateId.value = detail.id
    Object.assign(promptTemplateForm, {
      ...detail,
      platform: detail.platform || '',
      scene: detail.scene || '',
      step: detail.step || '',
      writing_rules: detail.writing_rules || [],
      prompt_body: detail.prompt_body || '',
      is_active: detail.is_active !== false,
      change_note: '',
    })
    promptTemplateRulesText.value = (detail.writing_rules || []).join('\n')
    const versions = await listPromptTemplateVersions(template.id)
    promptTemplateVersions.value = versions.data.items || []
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '读取模板详情失败。' }
  }
}

async function handleSavePromptTemplate() {
  if (isSavingPromptTemplate.value) return
  if (!promptTemplateForm.key.trim() || !promptTemplateForm.name.trim() || !promptTemplateForm.category_key.trim()) {
    promptManagerFeedback.value = { type: 'error', message: '请填写模板 Key、模板名称和所属分类。' }
    return
  }
  if (promptTemplateRiskFindings.value.length) {
    promptManagerFeedback.value = { type: 'error', message: `模板存在风险：${promptTemplateRiskFindings.value.join('；')}` }
    return
  }
  isSavingPromptTemplate.value = true
  try {
    const payload: PromptTemplateData = {
      ...promptTemplateForm,
      change_note: promptTemplateForm.change_note || (editingPromptTemplateId.value ? '后台更新模板' : '后台创建模板'),
      writing_rules: promptTemplateRulesText.value.split('\n').map((item) => item.trim()).filter(Boolean),
    }
    if (editingPromptTemplateId.value) {
      await updatePromptTemplate(editingPromptTemplateId.value, payload)
      promptManagerFeedback.value = { type: 'success', message: '提示词模板已更新。' }
    } else {
      await createPromptTemplate(payload)
      promptManagerFeedback.value = { type: 'success', message: '提示词模板已创建。' }
    }
    promptManagerCategoryKey.value = payload.category_key
    resetPromptTemplateForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '保存模板失败。' }
  } finally {
    isSavingPromptTemplate.value = false
  }
}

async function handleDeletePromptTemplate(template: PromptTemplateData) {
  const confirmed = await requestConfirmation({
    title: '停用提示词模板',
    message: `确认停用提示词模板「${template.name}」吗？停用后前端生成页不会继续选择它。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deletePromptTemplate(template.id)
    promptManagerFeedback.value = { type: 'success', message: `已停用模板「${template.name}」。` }
    if (editingPromptTemplateId.value === template.id) resetPromptTemplateForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用模板失败。' }
  }
}

function getPromptTemplateMetric(template: PromptTemplateData) {
  return promptTemplateMetrics.value[`${template.template_type || 'text_script'}:${template.id}`]
}

function formatMetricTime(value?: string | null) {
  if (!value) return '暂无生成记录'
  return value.slice(0, 16).replace('T', ' ')
}

function formatMetricRate(value?: number) {
  return `${Math.round((value || 0) * 100)}%`
}

async function handleSaveModelConfig() {
  if (isSavingModelConfig.value) return
  if (!modelConfigForm.name.trim()) {
    promptManagerFeedback.value = { type: 'error', message: '请填写模型名称。' }
    return
  }
  isSavingModelConfig.value = true
  try {
    await createModelConfig(modelConfigForm)
    promptManagerFeedback.value = { type: 'success', message: '模型配置已创建。' }
    resetModelConfigForm()
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '保存模型配置失败。' }
  } finally {
    isSavingModelConfig.value = false
  }
}

async function handleDeleteModelConfig(model: AIModelConfigData) {
  if (!model.id) return
  const confirmed = await requestConfirmation({
    title: '停用模型',
    message: `确认停用模型「${model.name}」吗？停用后它不会再出现在生成模型选择中。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deleteModelConfig(model.id)
    promptManagerFeedback.value = { type: 'success', message: `已停用模型「${model.name}」。` }
    await refreshPromptData()
  } catch (err: any) {
    promptManagerFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用模型失败。' }
  }
}

watch(() => props.currentUser?.token, (token) => {
  if (token) refreshPromptData()
}, { immediate: true })
</script>

<template>
  <div class="workspace workspace-embedded">
    <p class="sr-only" role="status" aria-live="polite" :aria-label="liveStatusMessage"></p>
    <main class="workspace-main workspace-main-embedded">
      <section class="panel panel-full glass-card prompt-manager-panel">
        <div class="prompt-manager-head">
          <div>
            <span class="section-eyebrow">Prompt Admin</span>
            <h1>提示词分类与模板管理</h1>
            <p>管理前端可选择的口播提示词分类和模板，生成时只注入已启用模板。</p>
          </div>
          <div class="prompt-manager-actions">
            <button class="btn btn-ghost btn-sm" @click="refreshPromptData">刷新</button>
            <button class="btn btn-primary btn-sm" @click="router.push(modePathMap.ip)">返回生产中心</button>
          </div>
        </div>

        <div v-if="promptManagerFeedback" class="prompt-feedback" :class="promptManagerFeedback.type">
          {{ promptManagerFeedback.message }}
        </div>

        <div class="prompt-manager-grid">
          <section class="prompt-admin-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>提示词分类</h3>
                <p>分类用于前端筛选模板，例如知识口播、带货种草、直播话术。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetPromptCategoryForm">新建分类</button>
            </div>

            <div class="prompt-category-list">
              <button
                v-for="category in promptTemplateCategories"
                :key="category.key"
                class="prompt-category-item"
                :class="{ active: promptManagerCategoryKey === category.key }"
                @click="promptManagerCategoryKey = category.key"
              >
                <strong>{{ category.name }}</strong>
                <span>{{ category.key }}</span>
              </button>

            </div>

            <div class="prompt-form compact-prompt-form">
              <div class="form-row">
                <label class="form-label">分类 Key</label>
                <input v-model="promptCategoryForm.key" class="input" placeholder="knowledge_talk" />
              </div>
              <div class="form-row">
                <label class="form-label">分类名称</label>
                <input v-model="promptCategoryForm.name" class="input" placeholder="知识口播" />
              </div>
              <div class="form-row">
                <label class="form-label">分类说明</label>
                <textarea v-model="promptCategoryForm.description" class="input" rows="2" placeholder="说明该分类适合什么场景"></textarea>
              </div>
              <div class="form-row-inline">
                <div class="form-row">
                  <label class="form-label">排序</label>
                  <input v-model.number="promptCategoryForm.sort_order" class="input" type="number" />
                </div>
                <label class="checkbox-row">
                  <input v-model="promptCategoryForm.is_active" type="checkbox" />
                  启用
                </label>
              </div>
              <div class="prompt-form-actions">
                <button class="btn btn-primary btn-sm" :disabled="isSavingPromptCategory" @click="handleSavePromptCategory">
                  {{ isSavingPromptCategory ? '保存中...' : editingPromptCategoryKey ? '更新分类' : '创建分类' }}
                </button>
                <button class="btn btn-ghost btn-sm" @click="resetPromptCategoryForm">清空</button>
              </div>
            </div>

            <div class="prompt-table-list">
              <article v-for="category in promptTemplateCategories" :key="category.key" class="prompt-table-item">
                <div>
                  <strong>{{ category.name }}</strong>
                  <span>{{ category.description || '暂无说明' }}</span>
                </div>
                <div class="prompt-table-actions">
                  <button class="btn btn-ghost btn-sm" @click="editPromptCategory(category)">编辑</button>
                  <button class="btn btn-ghost btn-sm" @click="handleDeletePromptCategory(category)">停用</button>
                </div>
              </article>
            </div>
          </section>

          <section class="prompt-admin-card prompt-template-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>提示词模板</h3>
                <p>模板正文由后台控制，前端生成页只展示名称、说明和结构。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetPromptTemplateForm">新建模板</button>
            </div>

            <div class="prompt-template-toolbar">
              <label class="selector-label">当前分类</label>
              <select v-model="promptManagerCategoryKey" class="select select-compact">
                <option v-for="category in promptTemplateCategories" :key="category.key" :value="category.key">
                  {{ category.name }}
                </option>
              </select>
              <span>{{ promptManagerTemplates.length }} 个已启用模板</span>
            </div>

            <div class="prompt-template-list">
              <article v-for="template in promptManagerTemplates" :key="template.id" class="prompt-template-item">
                <div>
                  <strong>{{ template.name }}</strong>
                  <span>{{ template.key }} · {{ template.platform || '全平台' }} / {{ template.scene || template.scenario || '未设置场景' }} / {{ template.step || '未设置步骤' }} · v{{ template.version }}</span>
                  <p>{{ template.description || '暂无说明' }}</p>
                  <small>结构：{{ template.output_structure || '未设置' }}</small>
                  <div class="prompt-template-metrics">
                    <span>生成 {{ getPromptTemplateMetric(template)?.generationCount || 0 }} 次</span>
                    <span>编辑率 {{ formatMetricRate(getPromptTemplateMetric(template)?.editRate) }}</span>
                    <span>定稿率 {{ formatMetricRate(getPromptTemplateMetric(template)?.saveRate) }}</span>
                    <span>提词转化 {{ formatMetricRate(getPromptTemplateMetric(template)?.teleprompterRate) }}</span>
                    <span>最近：{{ formatMetricTime(getPromptTemplateMetric(template)?.lastGeneratedAt) }}</span>
                  </div>
                </div>
                <div class="prompt-table-actions">
                  <span v-if="template.is_default" class="default-pill">默认</span>
                  <button class="btn btn-ghost btn-sm" @click="editPromptTemplate(template)">编辑</button>
                  <button class="btn btn-ghost btn-sm" @click="handleDeletePromptTemplate(template)">停用</button>
                </div>
              </article>
              <div v-if="!promptManagerTemplates.length" class="module-empty-state prompt-empty-state">
                <strong>当前分类暂无模板</strong>
                <span>创建一个模板后，IP 全案工作台即可选择使用。</span>
              </div>
            </div>

            <div class="prompt-form prompt-template-form">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">模板 Key</label>
                  <input v-model="promptTemplateForm.key" class="input" placeholder="three_part_knowledge" />
                </div>
                <div class="form-row">
                  <label class="form-label">模板名称</label>
                  <input v-model="promptTemplateForm.name" class="input" placeholder="三段式干货" />
                </div>
                <div class="form-row">
                  <label class="form-label">所属分类</label>
                  <select v-model="promptTemplateForm.category_key" class="input">
                    <option v-for="category in promptTemplateCategories" :key="category.key" :value="category.key">
                      {{ category.name }}
                    </option>
                  </select>
                </div>
                <div class="form-row">
                  <label class="form-label">适用场景</label>
                  <input v-model="promptTemplateForm.scenario" class="input" placeholder="干货分享" />
                </div>
                <div class="form-row">
                  <label class="form-label">平台</label>
                  <input v-model="promptTemplateForm.platform" class="input" placeholder="wechat / xiaohongshu / douyin" />
                </div>
                <div class="form-row">
                  <label class="form-label">业务场景</label>
                  <input v-model="promptTemplateForm.scene" class="input" placeholder="二创 / 口播 / 封面 / 分镜" />
                </div>
                <div class="form-row">
                  <label class="form-label">生成步骤</label>
                  <input v-model="promptTemplateForm.step" class="input" placeholder="正文生成 / 图片提示词 / 视频提示词" />
                </div>
                <div class="form-row">
                  <label class="form-label">版本</label>
                  <input v-model="promptTemplateForm.version" class="input" placeholder="1.0.0" />
                </div>
                <div class="form-row">
                  <label class="form-label">版本说明</label>
                  <input v-model="promptTemplateForm.change_note" class="input" placeholder="这次调整了什么" />
                </div>
                <div class="form-row">
                  <label class="form-label">排序</label>
                  <input v-model.number="promptTemplateForm.sort_order" class="input" type="number" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">模板说明</label>
                  <textarea v-model="promptTemplateForm.description" class="input" rows="2" placeholder="说明模板适合什么场景"></textarea>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">输出结构</label>
                  <textarea v-model="promptTemplateForm.output_structure" class="input" rows="2" placeholder="黄金3秒钩子 -> 核心观点 -> 方法拆解 -> CTA"></textarea>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">写作规则（一行一条）</label>
                  <textarea v-model="promptTemplateRulesText" class="input" rows="3" placeholder="开头必须有明确痛点\n不得做绝对效果承诺"></textarea>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">后台模板正文</label>
                  <textarea v-model="promptTemplateForm.prompt_body" class="input" rows="5" placeholder="可选。这里填写更完整的后台控制提示词正文，前端生成页不会直接展示。"></textarea>
                </div>
              </div>
              <div v-if="promptTemplateRiskFindings.length" class="prompt-risk-panel">
                <strong>模板风险提示</strong>
                <span v-for="finding in promptTemplateRiskFindings" :key="finding">{{ finding }}</span>
                <small>请移除高风险指令或密钥后再保存。后端会再次强校验。</small>
              </div>
              <div class="prompt-form-actions">
                <label class="checkbox-row">
                  <input v-model="promptTemplateForm.is_default" type="checkbox" />
                  设为分类默认
                </label>
                <label class="checkbox-row">
                  <input v-model="promptTemplateForm.is_active" type="checkbox" />
                  启用模板
                </label>
                <button class="btn btn-primary btn-sm" :disabled="isSavingPromptTemplate || promptTemplateRiskFindings.length > 0" @click="handleSavePromptTemplate">
                  {{ isSavingPromptTemplate ? '保存中...' : editingPromptTemplateId ? '更新模板' : '创建模板' }}
                </button>
                <button class="btn btn-ghost btn-sm" @click="resetPromptTemplateForm">清空</button>
              </div>
              <div v-if="promptTemplateVersions.length" class="prompt-version-list">
                <strong>版本历史</strong>
                <article v-for="version in promptTemplateVersions" :key="version.versionId" class="compact-item">
                  <span>v{{ version.version }} · {{ version.platform || '全平台' }} / {{ version.scene || '场景未填' }} / {{ version.step || '步骤未填' }}</span>
                  <small>{{ version.changeNote || '无变更说明' }} · {{ version.createdAt?.slice(0, 16) }}</small>
                </article>
              </div>
            </div>
          </section>

          <section class="prompt-admin-card model-config-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>大模型配置</h3>
                <p>快速添加模型：名称 + 类型 + API Key 即可；高级场景可补 Base URL 和模型 ID。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetModelConfigForm">清空表单</button>
            </div>

            <div class="prompt-template-list">
              <article v-for="model in modelManagerConfigs" :key="model.id" class="prompt-template-item">
                <div>
                  <strong>{{ model.name }}</strong>
                  <span>{{ model.model_type }} · {{ model.provider }} · {{ model.model_id || '默认模型' }}</span>
                  <p>{{ model.base_url }}</p>
                  <small>Key：{{ model.api_key_masked || '未填写' }} {{ model.is_default ? '· 默认' : '' }}</small>
                </div>
                <div class="prompt-table-actions">
                  <button class="btn btn-ghost btn-sm" @click="handleDeleteModelConfig(model)">停用</button>
                </div>
              </article>
              <div v-if="!modelManagerConfigs.length" class="module-empty-state prompt-empty-state">
                <strong>暂无模型配置</strong>
                <span>不配置也可以继续使用环境变量里的系统默认 AI 模型。</span>
              </div>
            </div>

            <div class="prompt-form model-config-form">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">模型名称</label>
                  <input v-model="modelConfigForm.name" class="input" placeholder="例：即梦图片 / GPT 文本" />
                </div>
                <div class="form-row">
                  <label class="form-label">模型类型</label>
                  <select v-model="modelConfigForm.model_type" class="input">
                    <option value="text">文本</option>
                    <option value="image">图片</option>
                    <option value="video">视频</option>
                    <option value="multimodal">多模态</option>
                  </select>
                </div>
                <div class="form-row">
                  <label class="form-label">供应商</label>
                  <input v-model="modelConfigForm.provider" class="input" placeholder="custom / openai / jimeng / kling" />
                </div>
                <div class="form-row">
                  <label class="form-label">API Key</label>
                  <input v-model="modelConfigForm.api_key" class="input" type="password" placeholder="后台保存，前端列表脱敏展示" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">Base URL</label>
                  <input v-model="modelConfigForm.base_url" class="input" placeholder="https://api.openai.com/v1" />
                </div>
                <div class="form-row">
                  <label class="form-label">模型 ID</label>
                  <input v-model="modelConfigForm.model_id" class="input" placeholder="gpt-4.1 / kling-v1 / jimeng-image" />
                </div>
                <div class="form-row">
                  <label class="form-label">排序</label>
                  <input v-model.number="modelConfigForm.sort_order" class="input" type="number" />
                </div>
              </div>
              <div class="prompt-form-actions">
                <label class="checkbox-row">
                  <input v-model="modelConfigForm.is_default" type="checkbox" />
                  设为类型默认
                </label>
                <label class="checkbox-row">
                  <input v-model="modelConfigForm.is_openai_compatible" type="checkbox" />
                  OpenAI 兼容
                </label>
                <button class="btn btn-primary btn-sm" :disabled="isSavingModelConfig" @click="handleSaveModelConfig">
                  {{ isSavingModelConfig ? '保存中...' : '创建模型' }}
                </button>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
    <ConfirmDialog
      :open="confirmState.open"
      :title="confirmState.title"
      :message="confirmState.message"
      :confirm-text="confirmState.confirmText"
      :cancel-text="confirmState.cancelText"
      :tone="confirmState.tone"
      @confirm="resolveConfirmation(true)"
      @cancel="resolveConfirmation(false)"
    />
  </div>
</template>

<style scoped src="../styles/copilot-workspace.css"></style>

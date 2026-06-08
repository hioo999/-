<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import ConfirmDialog from './ConfirmDialog.vue'
import { useConfirmDialog } from '../composables/useConfirmDialog'
import { modePathMap } from '../stores/workspace'
import {
  createModelGateway,
  deleteModelGateway,
  getModelDefaults,
  listModelCatalog,
  listModelConfigs,
  listModelGateways,
  setGlobalModelDefault,
  setModelDefault,
  syncModelGatewayModels,
  testModelGateway,
  updateModelCatalogItem,
  type AIModelConfigData,
  type ModelDefaultsData,
  type ModelGatewayData,
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
const isAdminUser = computed(() => props.currentUser?.is_admin === true)

const modelManagerConfigs = ref<AIModelConfigData[]>([])
const modelGateways = ref<ModelGatewayData[]>([])
const modelDefaults = ref<ModelDefaultsData>({})
const isSavingModelGateway = ref(false)
const modelGatewayFeedback = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
const modelGatewayBusy = reactive<Record<number, boolean>>({})

const modelGatewayForm = reactive<ModelGatewayData>({
  name: '',
  scope: 'user',
  provider_type: 'openai_compatible',
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  is_active: true,
})

const modelTypeLabels: Record<string, string> = {
  text: '文字',
  image: '图片',
  video: '视频',
  multimodal: '多模态',
  unknown: '待标注',
}

const modelResolutionLabels: Record<string, string> = {
  user_default: '个人默认',
  global_default: '全局默认',
  recommendation_fallback: '推荐兜底',
  none: '未配置',
}

const modelCapabilityGroups = computed(() => [
  { type: 'text', label: '生文字', models: modelManagerConfigs.value.filter((model) => ['text', 'multimodal'].includes(model.model_type)) },
  { type: 'image', label: '生图片', models: modelManagerConfigs.value.filter((model) => ['image', 'multimodal'].includes(model.model_type)) },
  { type: 'video', label: '生视频', models: modelManagerConfigs.value.filter((model) => ['video', 'multimodal'].includes(model.model_type)) },
])

const liveStatusMessage = computed(() => modelGatewayFeedback.value?.message || '')

function resolvedDefaultName(modelType: string) {
  const resolved = modelDefaults.value[modelType as keyof ModelDefaultsData]?.resolved
  return resolved?.name || '未配置'
}

function resolvedDefaultSource(modelType: string) {
  const entry = modelDefaults.value[modelType as keyof ModelDefaultsData]
  if (!entry?.resolved) return 'none'
  if (entry.personal?.id && entry.resolved.id === entry.personal.id) return 'user_default'
  if (entry.global?.id && entry.resolved.id === entry.global.id) return 'global_default'
  return 'recommendation_fallback'
}

function resolvedDefaultLabel(modelType: string) {
  return modelResolutionLabels[resolvedDefaultSource(modelType)] || '未配置'
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

async function loadModelGateways() {
  try {
    const res = await listModelGateways()
    modelGateways.value = res.data || []
  } catch {
    modelGateways.value = []
  }
}

async function loadModelDefaults() {
  try {
    const res = await getModelDefaults()
    modelDefaults.value = res.data || {}
  } catch {
    modelDefaults.value = {}
  }
}

async function refreshModelData() {
  await loadModelManagerConfigs()
  await loadModelGateways()
  await loadModelDefaults()
}

function resetModelGatewayForm() {
  Object.assign(modelGatewayForm, {
    name: '',
    scope: 'user',
    provider_type: 'openai_compatible',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    is_active: true,
  })
}

async function handleCreateModelGateway() {
  if (isSavingModelGateway.value) return
  if (!modelGatewayForm.name?.trim() || !modelGatewayForm.base_url?.trim() || !modelGatewayForm.api_key?.trim()) {
    modelGatewayFeedback.value = { type: 'error', message: '请填写配置名称、Base URL 和 API Key。' }
    return
  }
  isSavingModelGateway.value = true
  try {
    await createModelGateway(modelGatewayForm)
    modelGatewayFeedback.value = { type: 'success', message: '模型中转已创建，请点击“测试”或“同步模型”。' }
    resetModelGatewayForm()
    await refreshModelData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '创建模型中转失败。' }
  } finally {
    isSavingModelGateway.value = false
  }
}

async function handleTestModelGateway(gateway: ModelGatewayData) {
  if (!gateway.id) return
  modelGatewayBusy[gateway.id] = true
  try {
    const res = await testModelGateway(gateway.id)
    modelGatewayFeedback.value = { type: res.data?.ok ? 'success' : 'error', message: res.data?.message || res.message || '测试完成。' }
    await loadModelGateways()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '测试连接失败。' }
  } finally {
    modelGatewayBusy[gateway.id] = false
  }
}

async function handleSyncModelGateway(gateway: ModelGatewayData) {
  if (!gateway.id) return
  modelGatewayBusy[gateway.id] = true
  try {
    const res = await syncModelGatewayModels(gateway.id)
    modelGatewayFeedback.value = { type: 'success', message: res.message || `已同步 ${res.data?.length || 0} 个模型。` }
    await refreshModelData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '同步模型失败。' }
  } finally {
    modelGatewayBusy[gateway.id] = false
  }
}

async function handleDeleteModelGateway(gateway: ModelGatewayData) {
  if (!gateway.id) return
  const confirmed = await requestConfirmation({
    title: '停用模型中转',
    message: `确认停用中转「${gateway.name}」及其同步模型吗？停用后相关生成任务将不再使用该中转。`,
    confirmText: '停用',
  })
  if (!confirmed) return
  try {
    await deleteModelGateway(gateway.id)
    modelGatewayFeedback.value = { type: 'success', message: `已停用中转「${gateway.name}」。` }
    await refreshModelData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '停用中转失败。' }
  }
}

async function handleSetPersonalDefault(modelType: string, modelId: number) {
  try {
    await setModelDefault(modelType, modelId)
    modelGatewayFeedback.value = { type: 'success', message: `个人默认${modelTypeLabels[modelType] || modelType}模型已更新。` }
    await refreshModelData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '设置个人默认失败。' }
  }
}

async function handleSetGlobalDefault(modelType: string, modelId: number) {
  try {
    await setGlobalModelDefault(modelType, modelId)
    modelGatewayFeedback.value = { type: 'success', message: `全局默认${modelTypeLabels[modelType] || modelType}模型已更新。` }
    await refreshModelData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '设置全局默认失败。' }
  }
}

async function handleUpdateModelCapability(model: AIModelConfigData, modelType: string) {
  if (!model.id) return
  try {
    await updateModelCatalogItem(model.id, {
      model_type: modelType,
      recommendation_label: model.recommendation_label || '',
      recommendation_reason: model.recommendation_reason || '',
      risk_note: model.risk_note || '',
      sort_order: model.sort_order || 0,
      is_active: modelType !== 'unknown',
    })
    modelGatewayFeedback.value = { type: 'success', message: `模型「${model.name}」能力已更新。` }
    await refreshModelData()
  } catch (err: any) {
    modelGatewayFeedback.value = { type: 'error', message: err?.response?.data?.detail || err.message || '更新模型能力失败。' }
  }
}

function handleUpdateModelCapabilityFromEvent(model: AIModelConfigData, event: Event) {
  const target = event.target as HTMLSelectElement | null
  if (!target) return
  handleUpdateModelCapability(model, target.value)
}

watch(() => props.currentUser?.token, (token) => {
  if (token) refreshModelData()
  else modelDefaults.value = {}
}, { immediate: true })
</script>

<template>
  <div class="workspace workspace-embedded">
    <p class="sr-only" role="status" aria-live="polite" :aria-label="liveStatusMessage"></p>
    <main class="workspace-main workspace-main-embedded">
      <section class="panel panel-full glass-card prompt-manager-panel model-gateway-panel">
        <div class="prompt-manager-head">
          <div>
            <span class="section-eyebrow">Model Gateway</span>
            <h1>大模型中转与默认模型</h1>
            <p>填写兼容 OpenAI 的 Base URL 和 API Key 后，系统自动拉取该 Key 下的可用模型，并按文字、图片、视频任务设置默认模型。</p>
          </div>
          <div class="prompt-manager-actions">
            <button class="btn btn-ghost btn-sm" @click="refreshModelData">刷新</button>
            <button class="btn btn-primary btn-sm" @click="router.push(modePathMap.ip)">返回生产中心</button>
          </div>
        </div>

        <div v-if="modelGatewayFeedback" class="prompt-feedback" :class="modelGatewayFeedback.type">
          {{ modelGatewayFeedback.message }}
        </div>

        <div class="model-gateway-grid">
          <section class="prompt-admin-card model-gateway-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>添加大模型中转</h3>
                <p>先测试连接，再同步模型列表。普通用户创建个人中转，管理员可创建全局中转。</p>
              </div>
              <button class="btn btn-ghost btn-sm" @click="resetModelGatewayForm">清空表单</button>
            </div>

            <div class="prompt-form model-gateway-form">
              <div class="strategy-grid">
                <div class="form-row">
                  <label class="form-label">配置名称</label>
                  <input v-model="modelGatewayForm.name" class="input" placeholder="例：我的中转账号" />
                </div>
                <div class="form-row">
                  <label class="form-label">作用范围</label>
                  <select v-model="modelGatewayForm.scope" class="input">
                    <option value="user">个人可用</option>
                    <option v-if="isAdminUser" value="global">全局可用</option>
                  </select>
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">Base URL</label>
                  <input v-model="modelGatewayForm.base_url" class="input" placeholder="https://example.com/v1" />
                </div>
                <div class="form-row strategy-grid-wide">
                  <label class="form-label">API Key</label>
                  <input v-model="modelGatewayForm.api_key" class="input" type="password" autocomplete="off" placeholder="只加密保存，前端不回显明文" />
                </div>
              </div>
              <div class="prompt-form-actions">
                <label class="checkbox-row">
                  <input v-model="modelGatewayForm.is_active" type="checkbox" />
                  启用中转
                </label>
                <button class="btn btn-primary btn-sm" :disabled="isSavingModelGateway" @click="handleCreateModelGateway">
                  {{ isSavingModelGateway ? '保存中...' : '创建中转' }}
                </button>
              </div>
            </div>
          </section>

          <section class="prompt-admin-card model-gateway-card">
            <div class="prompt-admin-card-head">
              <div>
                <h3>默认模型策略</h3>
                <p>生成时优先使用个人默认；没有个人默认时使用后台全局默认；仍没有则按推荐排序兜底。</p>
              </div>
            </div>
            <div class="default-model-grid">
              <article v-for="group in modelCapabilityGroups" :key="group.type" class="default-model-card">
                <span>{{ group.label }}</span>
                <strong>{{ resolvedDefaultName(group.type) }}</strong>
                <small>{{ resolvedDefaultLabel(group.type) }}</small>
                <div class="default-model-actions">
                  <button
                    v-for="model in group.models.slice(0, 3)"
                    :key="model.id"
                    class="btn btn-ghost btn-sm"
                    @click="handleSetPersonalDefault(group.type, model.id || 0)"
                  >设个人默认：{{ model.name }}</button>
                </div>
              </article>
            </div>
          </section>
        </div>

        <section class="prompt-admin-card model-gateway-card">
          <div class="prompt-admin-card-head">
            <div>
              <h3>中转账号</h3>
              <p>测试连接会验证 Key 是否可用；同步模型会调用 `/models` 并写入模型目录。</p>
            </div>
          </div>
          <div class="model-gateway-list">
            <article v-for="gateway in modelGateways" :key="gateway.id" class="model-gateway-item">
              <div>
                <strong>{{ gateway.name }}</strong>
                <span>{{ gateway.scope === 'global' ? '全局' : '个人' }} · {{ gateway.provider_type || 'openai_compatible' }}</span>
                <p>{{ gateway.base_url }}</p>
                <small>Key：{{ gateway.api_key_masked || '未填写' }} · 状态：{{ gateway.last_test_status || 'untested' }} · 模型数：{{ gateway.last_model_count || 0 }}</small>
              </div>
              <div class="prompt-table-actions">
                <button v-if="gateway.scope !== 'global' || isAdminUser" class="btn btn-ghost btn-sm" :disabled="Boolean(gateway.id && modelGatewayBusy[gateway.id])" @click="handleTestModelGateway(gateway)">测试</button>
                <button v-if="gateway.scope !== 'global' || isAdminUser" class="btn btn-primary btn-sm" :disabled="Boolean(gateway.id && modelGatewayBusy[gateway.id])" @click="handleSyncModelGateway(gateway)">同步模型</button>
                <button v-if="gateway.scope !== 'global' || isAdminUser" class="btn btn-ghost btn-sm" @click="handleDeleteModelGateway(gateway)">停用</button>
              </div>
            </article>
            <div v-if="!modelGateways.length" class="module-empty-state prompt-empty-state">
              <strong>暂无模型中转</strong>
              <span>创建中转后点击同步，即可把该 API Key 下的模型加入选择列表。</span>
            </div>
          </div>
        </section>

        <section class="prompt-admin-card model-gateway-card">
          <div class="prompt-admin-card-head">
            <div>
              <h3>模型目录</h3>
              <p>系统会自动猜测模型能力；无法识别的模型请手动标注后再用于生成。</p>
            </div>
          </div>
          <div class="model-catalog-list">
            <article v-for="model in modelManagerConfigs" :key="model.id" class="model-catalog-item">
              <div class="model-catalog-main">
                <strong>{{ model.name }}</strong>
                <span>{{ model.provider }} · {{ model.model_id || '未设置模型 ID' }}</span>
                <p>{{ model.recommendation_label || '暂无推荐标签' }}{{ model.recommendation_reason ? `｜${model.recommendation_reason}` : '' }}</p>
                <small v-if="model.risk_note">风险提示：{{ model.risk_note }}</small>
              </div>
              <div class="model-catalog-controls">
                <select :value="model.model_type" class="input" @change="handleUpdateModelCapabilityFromEvent(model, $event)">
                  <option value="text">文字</option>
                  <option value="image">图片</option>
                  <option value="video">视频</option>
                  <option value="multimodal">多模态</option>
                  <option value="unknown">待标注</option>
                </select>
                <button class="btn btn-ghost btn-sm" @click="handleSetPersonalDefault(model.model_type, model.id || 0)">设个人默认</button>
                <button v-if="isAdminUser" class="btn btn-ghost btn-sm" @click="handleSetGlobalDefault(model.model_type, model.id || 0)">设全局默认</button>
              </div>
            </article>
            <div v-if="!modelManagerConfigs.length" class="module-empty-state prompt-empty-state">
              <strong>暂无可用模型</strong>
              <span>请先添加中转账号并同步模型，或由管理员配置全局模型。</span>
            </div>
          </div>
        </section>
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

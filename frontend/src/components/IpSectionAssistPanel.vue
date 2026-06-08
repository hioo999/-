<script setup lang="ts">
import type { IpSectionKey, IpSectionTemplate } from '../config/ipAssetTemplates'

defineProps<{
  section: IpSectionKey
  sectionLabel: string
  templates: IpSectionTemplate[]
  selectedTemplateKey: string
  isGenerating?: boolean
}>()

const emit = defineEmits<{
  'update:selectedTemplateKey': [value: string]
  applyTemplate: []
  generateSection: []
}>()
</script>

<template>
  <section class="section-assist" :aria-label="`${sectionLabel}辅助填写`">
    <div class="assist-head">
      <div>
        <strong>不知道怎么填？</strong>
        <span>先选行业模板快速套用，或一键生成当前步骤内容。</span>
      </div>
      <div class="assist-actions">
        <button class="ghost-pill" type="button" :disabled="isGenerating" @click="emit('applyTemplate')">套用模板</button>
        <button class="primary-pill assist-generate" type="button" :disabled="isGenerating" @click="emit('generateSection')">
          {{ isGenerating ? '生成中...' : '一键生成' }}
        </button>
      </div>
    </div>
    <div class="template-chip-row" role="listbox" :aria-label="`${sectionLabel}模板选择`">
      <button
        v-for="item in templates"
        :key="item.key"
        type="button"
        role="option"
        class="template-chip"
        :class="{ active: selectedTemplateKey === item.key }"
        :aria-selected="selectedTemplateKey === item.key"
        @click="emit('update:selectedTemplateKey', item.key)"
      >
        <strong>{{ item.label }}</strong>
        <small>{{ item.description }}</small>
      </button>
    </div>
  </section>
</template>

<style scoped>
.section-assist {
  display: grid;
  gap: 12px;
  margin-bottom: 18px;
  padding: 14px 16px;
  border: 1px solid rgba(36, 87, 255, 0.12);
  border-radius: 18px;
  background: rgba(239, 246, 255, 0.72);
}

.assist-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.assist-head strong {
  display: block;
  margin-bottom: 4px;
  color: #0f172a;
  font-size: 14px;
}

.assist-head span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.assist-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.template-chip-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
}

.template-chip {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  font: inherit;
  transition: border-color var(--transition-normal), box-shadow var(--transition-normal);
}

.template-chip strong {
  color: #0f172a;
  font-size: 13px;
}

.template-chip small {
  color: #64748b;
  font-size: 11px;
  line-height: 1.5;
}

.template-chip.active {
  border-color: rgba(36, 87, 255, 0.32);
  box-shadow: 0 8px 20px rgba(36, 87, 255, 0.08);
}

.assist-generate:disabled {
  opacity: 0.72;
  cursor: wait;
}
</style>

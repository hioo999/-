<script setup lang="ts">
defineProps<{
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  tone?: 'danger' | 'warning' | 'default'
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <div v-if="open" class="confirm-backdrop" role="presentation" @click.self="emit('cancel')">
    <section
      class="confirm-dialog"
      :class="tone || 'default'"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-message"
    >
      <div class="confirm-mark" aria-hidden="true">!</div>
      <div class="confirm-copy">
        <h2 id="confirm-title">{{ title }}</h2>
        <p id="confirm-message">{{ message }}</p>
      </div>
      <div class="confirm-actions">
        <button class="btn btn-ghost" @click="emit('cancel')">{{ cancelText || '取消' }}</button>
        <button class="btn btn-primary" @click="emit('confirm')">{{ confirmText || '确认' }}</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(8px);
}

.confirm-dialog {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 16px;
  width: min(440px, 100%);
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow-lg);
}

.confirm-mark {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 999px;
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
  font-size: 20px;
  font-weight: 900;
}

.confirm-dialog.warning .confirm-mark {
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}

.confirm-dialog.default .confirm-mark {
  background: rgba(37, 99, 235, 0.12);
  color: #2563eb;
}

.confirm-copy h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: 800;
}

.confirm-copy p {
  margin: 8px 0 0;
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.confirm-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

@media (max-width: 560px) {
  .confirm-dialog {
    grid-template-columns: 1fr;
  }

  .confirm-actions {
    flex-direction: column-reverse;
  }
}
</style>

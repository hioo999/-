import { reactive } from 'vue'

export function useConfirmDialog() {
  const confirmState = reactive({
    open: false,
    title: '',
    message: '',
    confirmText: '确认',
    cancelText: '取消',
    tone: 'danger' as 'danger' | 'warning' | 'default',
  })

  let confirmResolver: ((value: boolean) => void) | null = null

  function requestConfirmation(options: {
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    tone?: 'danger' | 'warning' | 'default'
  }) {
    confirmState.open = true
    confirmState.title = options.title
    confirmState.message = options.message
    confirmState.confirmText = options.confirmText || '确认'
    confirmState.cancelText = options.cancelText || '取消'
    confirmState.tone = options.tone || 'danger'
    return new Promise<boolean>((resolve) => {
      confirmResolver = resolve
    })
  }

  function resolveConfirmation(value: boolean) {
    confirmState.open = false
    confirmResolver?.(value)
    confirmResolver = null
  }

  return {
    confirmState,
    requestConfirmation,
    resolveConfirmation,
  }
}

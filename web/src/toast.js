// toast.js —— 轻量全局提示（跨三端演示面板复用）
import { reactive } from 'vue'

export const toasts = reactive([])
let seq = 0

export function toast(msg, type = 'info') {
  const id = ++seq
  toasts.push({ id, msg, type })
  setTimeout(() => {
    const i = toasts.findIndex(t => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, 2600)
}

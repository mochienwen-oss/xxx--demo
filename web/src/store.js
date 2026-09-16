// store.js —— 登录态（响应式 + localStorage 持久化）
import { reactive } from 'vue'

export const auth = reactive({
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),

  set(token, user) {
    this.token = token
    this.user = user
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
  },
  clear() {
    this.token = ''
    this.user = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }
})

// 简易事件总线：三端演示面板跨区域实时同步（任一角色变更工单时通知其余面板刷新）
export const bus = {
  map: new Map(),
  on(event, fn) {
    if (!this.map.has(event)) this.map.set(event, new Set())
    this.map.get(event).add(fn)
    return () => this.map.get(event).delete(fn)
  },
  emit(event, data) {
    ;(this.map.get(event) || []).forEach(fn => fn(data))
  }
}

export const ROLE_LABEL = { employee: '员工', worker: '维修工', admin: '管理员' }

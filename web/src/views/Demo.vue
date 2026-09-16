<script setup>
import { reactive, onMounted, onBeforeUnmount } from 'vue'
import { request } from '../api'
import { bus } from '../store'
import EmployeeHome from './EmployeeHome.vue'
import WorkerHome from './WorkerHome.vue'
import AdminHome from './AdminHome.vue'

const PANES = [
  { key: 'admin', label: '管理员', icon: '🛠️', username: 'admin', password: 'admin123', component: AdminHome },
  { key: 'worker', label: '维修工', icon: '🔧', username: 'zhangwei', password: '123456', component: WorkerHome },
  { key: 'employee', label: '员工', icon: '🙋', username: 'chenxiao', password: '123456', component: EmployeeHome }
]

// 每个角色一份独立会话（token + user），互不干扰
const sessions = reactive({
  admin: { token: '', user: null, loading: false },
  employee: { token: '', user: null, loading: false },
  worker: { token: '', user: null, loading: false }
})
// 每个角色一份独立登录表单
const forms = reactive({
  admin: { username: 'admin', password: 'admin123' },
  employee: { username: 'chenxiao', password: '123456' },
  worker: { username: 'zhangwei', password: '123456' }
})

async function login(key) {
  const s = sessions[key]
  s.loading = true
  try {
    // token:'' 避免误带上浏览器 localStorage 里的旧全局 token
    const data = await request('/auth/login', { method: 'POST', body: forms[key], token: '' })
    s.token = data.token
    s.user = data.user
  } catch (e) {
    alert(`[${key}] 登录失败：${e.message}`)
  } finally {
    s.loading = false
  }
}

function logout(key) {
  const s = sessions[key]
  s.token = ''
  s.user = null
}

function loginAll() {
  return Promise.all(PANES.map(p => login(p.key)))
}

let timer = null
onMounted(() => {
  timer = setInterval(() => bus.emit('tickets'), 5000)  // 兜底轮询，保证数据实时同步
})
onBeforeUnmount(() => { clearInterval(timer) })
</script>

<template>
  <div class="demo-wrap">
    <div class="demo-topbar">
      <div class="brand">🏢 智能报修系统</div>
      <button class="btn btn-sm" @click="loginAll">🔄 一键登录全部</button>
    </div>

    <div class="demo-grid">
      <section v-for="p in PANES" :key="p.key" class="demo-pane" :class="'pane-' + p.key">
        <header class="pane-head">
          <span class="pane-title">{{ p.icon }} {{ p.label }}</span>
          <span v-if="sessions[p.key].user" class="pane-user">{{ sessions[p.key].user.name }}</span>
          <span v-else class="pane-user muted">未登录</span>
          <button v-if="sessions[p.key].user" class="btn btn-sm btn-ghost" @click="logout(p.key)">退出</button>
        </header>

        <div class="pane-body">
          <!-- 已登录：渲染对应角色界面 -->
          <component v-if="sessions[p.key].user" :is="p.component" :session="sessions[p.key]" />

          <!-- 未登录：独立登录表单 -->
          <div v-else class="pane-login">
            <form @submit.prevent="login(p.key)">
              <div class="field">
                <label>用户名</label>
                <input v-model.trim="forms[p.key].username" autocomplete="username" />
              </div>
              <div class="field">
                <label>密码</label>
                <input v-model.trim="forms[p.key].password" type="password" autocomplete="current-password" />
              </div>
              <button class="btn" :disabled="sessions[p.key].loading">
                {{ sessions[p.key].loading ? '登录中…' : '登 录' }}
              </button>
            </form>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

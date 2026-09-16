<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { request } from '../api'
import { auth } from '../store'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)

function home() {
  const r = auth.user.role
  if (r === 'worker') return '/worker'
  if (r === 'admin') return '/admin'
  return '/employee'
}

async function submit() {
  loading.value = true
  try {
    const data = await request('/auth/login', {
      method: 'POST', body: { username: username.value, password: password.value }
    })
    auth.set(data.token, data.user)
    router.push(home())
  } catch (e) {
    alert(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <h1>🏢 xxx公司智能报修系统</h1>
      <p class="muted">请登录后使用</p>
      <form @submit.prevent="submit">
        <div class="field">
          <label>用户名</label>
          <input v-model.trim="username" placeholder="例如 admin" autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="密码" autocomplete="current-password" />
        </div>
        <button class="btn" :disabled="loading">{{ loading ? '登录中…' : '登 录' }}</button>
      </form>
      <div class="demo-accounts">
        <div class="muted">演示账号（用户名 / 密码）：</div>
        <div>管理员：admin / admin123</div>
        <div>员工：chenxiao / 123456</div>
        <div>维修工：zhangwei / 123456</div>
      </div>
    </div>
  </div>
</template>

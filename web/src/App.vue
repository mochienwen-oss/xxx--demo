<script setup>
import { auth, ROLE_LABEL } from './store'
import { useRoute, useRouter } from 'vue-router'
import Toast from './components/Toast.vue'
const router = useRouter()
const route = useRoute()
function logout() { auth.clear(); router.push('/login') }
</script>

<template>
  <!-- 三端演示页有自己的深色顶栏，这里不再重复渲染全局导航 -->
  <nav v-if="route.path !== '/demo'" class="navbar">
    <span class="brand">🏢 xxx公司智能报修系统</span>
    <span v-if="auth.token" class="who">{{ auth.user?.name }} · {{ ROLE_LABEL[auth.user?.role] }}</span>
    <div class="links">
      <template v-if="auth.token">
        <router-link v-if="auth.user?.role === 'employee'" to="/employee">员工端</router-link>
        <router-link v-if="auth.user?.role === 'worker'" to="/worker">维修工端</router-link>
        <router-link v-if="auth.user?.role === 'admin'" to="/admin">管理端</router-link>
        <a href="#" @click.prevent="logout">退出</a>
      </template>
    </div>
  </nav>
  <router-view />
  <Toast />
</template>

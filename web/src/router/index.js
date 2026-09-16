import { createRouter, createWebHashHistory } from 'vue-router'
import { auth } from '../store'
import Login from '../views/Login.vue'
import EmployeeHome from '../views/EmployeeHome.vue'
import WorkerHome from '../views/WorkerHome.vue'
import AdminHome from '../views/AdminHome.vue'
import Demo from '../views/Demo.vue'

function home() {
  const r = auth.user?.role
  if (r === 'worker') return '/worker'
  if (r === 'admin') return '/admin'
  return '/employee'
}

const routes = [
  { path: '/', redirect: '/demo' },
  { path: '/login', component: Login },
  { path: '/demo', component: Demo },
  { path: '/employee', component: EmployeeHome, meta: { role: 'employee' } },
  { path: '/worker', component: WorkerHome, meta: { role: 'worker' } },
  { path: '/admin', component: AdminHome, meta: { role: 'admin' } }
]

const router = createRouter({ history: createWebHashHistory(), routes })

// 路由守卫：未登录跳登录页，角色不符跳回自己的首页；/demo 无需全局登录态
router.beforeEach((to) => {
  if (to.path === '/login' || to.path === '/demo') return true
  if (!auth.token) return '/login'
  if (to.meta.role && auth.user?.role !== to.meta.role) return home()
  return true
})

export default router

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { request } from '../api'
import { bus } from '../store'
import { makeCtx } from '../ctx'

const props = defineProps({ session: Object })
const ctx = makeCtx(props.session)
const req = (p, o = {}) => request(p, { ...o, token: ctx.token })

const activeTab = ref('stats')   // 'stats' 数据看板 | 'tickets' 工单管理

const tickets = ref([])
const workers = ref([])
// 操作列下拉的受控选中值（ticketId -> worker_id）。
// 用 v-model 而非 :value：维修工选项是异步渲染的，v-model 会在选项就位后重新校准选中项，
// 避免「工单已是处理中、维修工列有人名、下拉却空白」的时序问题。
const assignSel = reactive({})
const stats = ref({ total: 0, completed: 0, rate: 0, byStatus: [], avgRating: null })

let offBus = null

function statusCls(s) {
  return ({ '待处理': 'pending', '处理中': 'progress', '已完成': 'done', '已驳回': 'rejected' })[s] || 'pending'
}
function countOf(s) { return stats.value.byStatus.find(x => x.status === s)?.c || 0 }
function pct(c) {
  const max = Math.max(1, ...stats.value.byStatus.map(x => x.c))
  return Math.round((c / max) * 100) + '%'
}
function color(s) {
  return ({ '待处理': '#f59e0b', '处理中': '#2563eb', '已完成': '#16a34a', '已驳回': '#9ca3af' })[s] || '#9ca3af'
}

// 6 个统计卡片（统一数据源，保证规格一致）
const statItems = computed(() => [
  { label: '总工单', value: stats.value.total },
  { label: '待处理', value: countOf('待处理') },
  { label: '处理中', value: countOf('处理中') },
  { label: '已完成', value: stats.value.completed },
  { label: '完成率', value: stats.value.rate + '%' },
  { label: '平均评分', value: stats.value.avgRating ?? '—' }
])

async function load() {
  const [s, t, w] = await Promise.all([req('/stats'), req('/tickets'), req('/workers')])
  stats.value = s; tickets.value = t; workers.value = w
  // 下拉选中值以服务端最新维修工为准（本地乐观更新会在下次 load 时被覆盖）
  for (const x of t) assignSel[x.id] = x.worker_id ?? ''
}

async function manualAssign(t, workerId) {
  const wid = Number(workerId)
  if (!wid) return
  const prev = assignSel[t.id] ?? ''
  assignSel[t.id] = wid                           // 立即回显，不等待请求与重渲染
  try { await req(`/tickets/${t.id}/claim`, { method: 'POST', body: { worker_id: wid } }); bus.emit('tickets') }
  catch (e) { assignSel[t.id] = prev; alert(e.message) }
}
async function autoAssign(t) {
  try { await req(`/tickets/${t.id}/claim`, { method: 'POST', body: {} }); bus.emit('tickets') } catch (e) { alert(e.message) }
}
async function reject(t) {
  try { await req(`/tickets/${t.id}/reject`, { method: 'POST' }); bus.emit('tickets') } catch (e) { alert(e.message) }
}
async function transfer(t, workerId) {
  const wid = Number(workerId)
  if (!wid) return
  const prev = t.worker_id ?? ''
  assignSel[t.id] = wid                           // 立即回显
  try { await req(`/tickets/${t.id}/transfer`, { method: 'POST', body: { worker_id: wid } }); bus.emit('tickets') }
  catch (e) { assignSel[t.id] = prev; alert(e.message) }
}

onMounted(() => { load(); offBus = bus.on('tickets', load) })
onBeforeUnmount(() => { offBus && offBus() })
</script>

<template>
  <div class="tab-wrap">
    <div class="tab-body">
      <!-- 统一外层容器 -->
      <div class="panel">
        <!-- 数据看板 -->
        <template v-if="activeTab === 'stats'">
          <div class="panel-title">📊 数据看板 <span class="sub">实时统计</span></div>
          <div class="stat-grid">
            <div class="stat" v-for="s in statItems" :key="s.label">
              <div class="num">{{ s.value }}</div>
              <div class="label">{{ s.label }}</div>
            </div>
          </div>
          <div class="panel-title" style="margin-top: 8px;">📈 状态分布</div>
          <div class="bar-row" v-for="s in stats.byStatus" :key="s.status">
            <span class="name">{{ s.status }}</span>
            <div class="track"><div class="fill" :style="{ width: pct(s.c), background: color(s.status) }"></div></div>
            <span class="val">{{ s.c }}</span>
          </div>
        </template>

        <!-- 工单管理 -->
        <template v-else>
          <div class="panel-title">📋 工单管理 <span class="sub">全部报修工单</span></div>
          <div class="table-scroll">
            <table>
              <thead>
                <tr><th>#</th><th>状态</th><th>类型</th><th>报修人</th><th>设备</th><th>描述</th><th>维修工</th><th>提交时间</th><th>催办</th><th>操作</th></tr>
              </thead>
              <tbody>
                <tr v-for="t in tickets" :key="t.id">
                  <td>{{ t.id }}</td>
                  <td><span class="badge" :class="statusCls(t.status)">{{ t.status }}</span></td>
                  <td>{{ t.fault_type || '—' }}</td>
                  <td>{{ t.employee_name }}</td>
                  <td>{{ t.device_name || '—' }}</td>
                  <td><span class="truncate" :title="t.description">{{ t.description }}</span></td>
                  <td>{{ t.worker_name || '—' }}</td>
                  <td class="muted">{{ t.created_at }}</td>
                  <td><span v-if="t.urge_count" class="badge urge">催办 {{ t.urge_count }} 次</span><span v-else class="muted">—</span></td>
                  <td>
                    <div class="actions" style="margin:0;">
                      <template v-if="t.status === '待处理'">
                        <select v-model="assignSel[t.id]" @change="manualAssign(t, $event.target.value)">
                          <option value="">手动派单…</option>
                          <option v-for="w in workers" :key="w.id" :value="w.id">{{ w.name }}</option>
                        </select>
                        <button class="btn btn-sm btn-green" @click="autoAssign(t)">智能派单</button>
                        <button class="btn btn-sm btn-ghost" @click="reject(t)">驳回</button>
                      </template>
                      <select v-else-if="t.status === '处理中'" v-model="assignSel[t.id]" @change="transfer(t, $event.target.value)">
                        <option value="">改派…</option>
                        <option v-for="w in workers" :key="w.id" :value="w.id">{{ w.name }}</option>
                      </select>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>

    <!-- 底部 tab -->
    <div class="tabbar">
      <div class="tab" :class="{ on: activeTab === 'stats' }" @click="activeTab = 'stats'">
        <span class="tab-icon">📊</span>
        <span class="tab-label">数据看板</span>
      </div>
      <div class="tab" :class="{ on: activeTab === 'tickets' }" @click="activeTab = 'tickets'">
        <span class="tab-icon">📋</span>
        <span class="tab-label">工单管理</span>
      </div>
    </div>
  </div>
</template>

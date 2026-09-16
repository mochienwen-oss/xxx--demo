<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { request } from '../api'
import { bus } from '../store'
import { makeCtx } from '../ctx'

const props = defineProps({ session: Object })
const ctx = makeCtx(props.session)
const req = (p, o = {}) => request(p, { ...o, token: ctx.token })

const activeTab = ref('hall')   // 'hall' 工单大厅 | 'mine' 我的工单

const hall = ref([])
const mine = ref([])
const dispatchMap = reactive({})   // ticketId -> 推荐维修工
const solutionMap = reactive({})   // ticketId -> 处理结果

let offBus = null

function statusCls(s) {
  return ({ '待处理': 'pending', '处理中': 'progress', '已完成': 'done', '已驳回': 'rejected' })[s] || 'pending'
}

async function load() {
  const list = await req('/tickets')
  hall.value = list.filter(t => t.status === '待处理')
  mine.value = list.filter(t => t.worker_id === ctx.user.id && t.status !== '待处理')
  // 只对新出现的待处理工单做一次智能推荐，避免轮询刷新时「依据」频繁跳动
  for (const t of hall.value) {
    if (dispatchMap[t.id] == null) {
      dispatchMap[t.id] = await req(`/smart/dispatch/${t.id}`).catch(() => null)
    }
  }
}

async function claim(id) {
  try { await req(`/tickets/${id}/claim`, { method: 'POST' }); bus.emit('tickets') } catch (e) { alert(e.message) }
}

async function complete(id) {
  const solution = solutionMap[id]
  if (!solution) { alert('请填写处理结果'); return }
  try { await req(`/tickets/${id}/complete`, { method: 'POST', body: { solution } }); bus.emit('tickets') } catch (e) { alert(e.message) }
}

async function transfer(id) {
  try { await req(`/tickets/${id}/transfer`, { method: 'POST', body: { worker_id: null } }); bus.emit('tickets') } catch (e) { alert(e.message) }
}

onMounted(() => { load(); offBus = bus.on('tickets', load) })
onBeforeUnmount(() => { offBus && offBus() })
</script>

<template>
  <div class="tab-wrap">
    <div class="tab-body">
      <!-- 工单大厅 -->
      <div v-if="activeTab === 'hall'" class="card">
        <h3>📥 工单大厅（待处理）</h3>
        <div v-if="!hall.length" class="empty">暂无待处理工单 🎉</div>
        <div class="ticket" v-for="t in hall" :key="t.id">
          <div class="top">
            <span class="badge pending">待处理</span>
            <strong>{{ t.fault_type || '未分类' }}</strong>
            <span class="muted">#{{ t.id }}</span>
          </div>
          <div class="desc">{{ t.description }}</div>
          <img v-if="t.image" class="thumb" :src="t.image" alt="现场照片" />
          <div class="meta">
            <span>报修人：{{ t.employee_name }}</span>
            <span>设备：{{ t.device_name || '—' }}</span>
            <span>提交：{{ t.created_at }}</span>
          </div>
          <div v-if="t.urge_count" class="urge-badge">⚠ 用户已催办 {{ t.urge_count }} 次，请尽快处理</div>
          <div class="ai-box mt8">
            🤖 智能推荐维修工：<span class="tag">{{ dispatchMap[t.id]?.name || '—' }}</span>
            <span v-if="dispatchMap[t.id]">（技能：{{ dispatchMap[t.id].skills }} · 在办 {{ dispatchMap[t.id].active }} 单）</span>
            <div v-if="dispatchMap[t.id]?.reason" class="mt8 muted">依据：{{ dispatchMap[t.id].reason }}</div>
          </div>
          <div class="actions">
            <button class="btn btn-sm" @click="claim(t.id)">接单</button>
          </div>
        </div>
      </div>

      <!-- 我的工单 -->
      <div v-else class="card">
        <h3>📌 我的工单</h3>
        <div v-if="!mine.length" class="empty">暂无工单</div>
        <div class="ticket" v-for="t in mine" :key="t.id">
          <div class="top">
            <span class="badge" :class="statusCls(t.status)">{{ t.status }}</span>
            <strong>{{ t.fault_type || '未分类' }}</strong>
            <span class="muted">#{{ t.id }}</span>
          </div>
          <div class="desc">{{ t.description }}</div>
          <div class="meta">
            <span>报修人：{{ t.employee_name }}</span>
            <span>设备：{{ t.device_name || '—' }}</span>
            <span v-if="t.resolved_at">完成：{{ t.resolved_at }}</span>
          </div>
          <div v-if="t.urge_count && t.status === '处理中'" class="urge-badge">⚠ 用户已催办 {{ t.urge_count }} 次，请尽快处理</div>
          <div v-if="t.status === '已完成' && t.solution" class="mt8 muted">处理结果：{{ t.solution }}</div>
          <div v-if="t.status === '已完成' && t.rating" class="mt8 muted">评分：{{ '★'.repeat(t.rating) }}</div>

          <div class="actions" v-if="t.status === '处理中'">
            <textarea v-model.trim="solutionMap[t.id]" placeholder="填写处理结果（将沉淀到知识库）"></textarea>
            <button class="btn btn-sm btn-green" @click="complete(t.id)">完成工单</button>
            <button class="btn btn-sm btn-ghost" @click="transfer(t.id)">转单</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部 tab -->
    <div class="tabbar">
      <div class="tab" :class="{ on: activeTab === 'hall' }" @click="activeTab = 'hall'">
        <span class="tab-icon">📥</span>
        <span class="tab-label">工单大厅</span>
      </div>
      <div class="tab" :class="{ on: activeTab === 'mine' }" @click="activeTab = 'mine'">
        <span class="tab-icon">📌</span>
        <span class="tab-label">我的工单</span>
      </div>
    </div>
  </div>
</template>

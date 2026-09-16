<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { request } from '../api'
import { bus } from '../store'
import { makeCtx } from '../ctx'
import { toast } from '../toast'

const props = defineProps({ session: Object })
const ctx = makeCtx(props.session)
const req = (p, o = {}) => request(p, { ...o, token: ctx.token })

const activeTab = ref('submit')   // 'submit' 提交报修 | 'mine' 我的报修

const tickets = ref([])
const recommends = ref([])
const faultTypes = ref([])        // 常见问题类型字典（来自后端，与智能分类同源）
const classifyResult = ref(null)
const submitting = ref(false)

const form = reactive({ device_name: '', fault_type: '', description: '', image: null })
const rateMap = reactive({})     // ticketId -> 评分
const commentMap = reactive({})  // ticketId -> 留言
const urging = reactive({})      // ticketId -> 催办中

let classifyTimer = null
let offBus = null

function statusCls(s) {
  return ({ '待处理': 'pending', '处理中': 'progress', '已完成': 'done', '已驳回': 'rejected' })[s] || 'pending'
}

// 实时智能分类（防抖）：综合「设备名 + 故障描述」判断故障类型
function classify() {
  clearTimeout(classifyTimer)
  classifyTimer = setTimeout(async () => {
    if (!form.device_name && !form.description) { classifyResult.value = null; return }
    classifyResult.value = await req('/smart/classify', {
      method: 'POST', body: { description: form.description, device: form.device_name }
    })
  }, 300)
}

function onImage(e) {
  const f = e.target.files[0]
  if (!f) return
  if (f.size > 2 * 1024 * 1024) { alert('图片请控制在 2MB 以内'); return }
  const r = new FileReader()
  r.onload = () => { form.image = r.result }
  r.readAsDataURL(f)
}

async function submit() {
  if (!form.description) { alert('请填写故障描述'); return }
  submitting.value = true
  try {
    // 手动选择的问题类型优先；未选则交由后端智能分类
    await req('/tickets', {
      method: 'POST',
      body: { device_name: form.device_name, fault_type: form.fault_type, description: form.description, image: form.image }
    })
    // 推荐方案按最终类型匹配：手选优先，否则用智能判断结果
    const finalType = form.fault_type || classifyResult.value?.type || ''
    recommends.value = await req('/smart/recommend', {
      method: 'POST', body: { description: form.description, faultType: finalType }
    })
    form.device_name = ''; form.fault_type = ''; form.description = ''; form.image = null
    classifyResult.value = null
    bus.emit('tickets')
  } catch (e) {
    alert(e.message)
  } finally {
    submitting.value = false
  }
}

async function urge(t) {
  if (urging[t.id]) return
  urging[t.id] = true
  try {
    await req(`/tickets/${t.id}/urge`, { method: 'POST' })
    toast('已催办，请耐心等待处理', 'success')
    bus.emit('tickets')
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    urging[t.id] = false
  }
}

async function rate(t) {
  const rating = rateMap[t.id]
  if (!rating) { alert('请先点击星星评分'); return }
  try {
    await req(`/tickets/${t.id}/rate`, { method: 'POST', body: { rating, comment: commentMap[t.id] || '' } })
    bus.emit('tickets')
  } catch (e) { alert(e.message) }
}

async function load() {
  tickets.value = await req('/tickets')
}

onMounted(() => {
  load()
  req('/fault-types').then(list => { faultTypes.value = list }).catch(() => {})
  offBus = bus.on('tickets', load)
})
onBeforeUnmount(() => { offBus && offBus() })
</script>

<template>
  <div class="tab-wrap">
    <div class="tab-body">
      <!-- 提交报修 -->
      <template v-if="activeTab === 'submit'">
        <div class="card">
          <h3>📝 提交报修</h3>
          <form @submit.prevent="submit">
            <div class="grid grid-2">
              <div class="field">
                <label>报修设备</label>
                <input v-model.trim="form.device_name" placeholder="例如：三楼会议室投影仪、研发部空调" @input="classify" />
              </div>
              <div class="field">
                <label>报修人</label>
                <input :value="ctx.user?.name" disabled />
              </div>
            </div>
            <div class="field">
              <label>问题类型</label>
              <select v-model="form.fault_type">
                <option value="">自动识别（按描述智能判断）</option>
                <option v-for="ft in faultTypes" :key="ft" :value="ft">{{ ft }}</option>
              </select>
            </div>
            <div class="field">
              <label>故障描述 <span class="req">*</span></label>
              <textarea v-model.trim="form.description" placeholder="请描述故障现象，例如：电脑无法开机、空调不制冷……" @input="classify"></textarea>
            </div>
            <div v-if="form.fault_type" class="ai-box">
              🤖 问题类型：<span class="tag">{{ form.fault_type }}</span>
              <span class="muted">· 已手动选择，提交后管理员端将按此类型显示工单</span>
            </div>
            <div v-else-if="classifyResult" class="ai-box">
              🤖 系统智能判断：<span class="tag">{{ classifyResult.type }}</span>（置信度：{{ classifyResult.confidence }}）
              <span class="muted">· 综合「设备名 + 故障描述」</span>
              <div v-if="classifyResult.reason" class="mt8 muted">依据：{{ classifyResult.reason }}</div>
            </div>
            <div class="field">
              <label>现场照片（可选，≤2MB）</label>
              <input type="file" accept="image/*" @change="onImage" />
            </div>
            <button class="btn" :disabled="submitting">{{ submitting ? '提交中…' : '提交报修' }}</button>
          </form>
        </div>

        <!-- 智能推荐 -->
        <div class="card" v-if="recommends.length">
          <h3>💡 智能推荐处理方案</h3>
          <div class="ticket" v-for="(r, i) in recommends" :key="i">
            <div class="top"><span class="badge progress">方案 {{ i + 1 }}</span><span class="muted">{{ r.fault_type }} · 匹配度 {{ r.score }}</span></div>
            <div class="desc">{{ r.solution }}</div>
          </div>
        </div>
      </template>

      <!-- 我的报修 -->
      <div v-else class="card">
        <h3>📋 我的报修</h3>
        <div v-if="!tickets.length" class="empty">暂无报修记录</div>
        <div class="ticket" v-for="t in tickets" :key="t.id">
          <div class="top">
            <span class="badge" :class="statusCls(t.status)">{{ t.status }}</span>
            <strong>{{ t.fault_type || '未分类' }}</strong>
            <span class="muted">#{{ t.id }}</span>
          </div>
          <div class="desc">{{ t.description }}</div>
          <img v-if="t.image" class="thumb" :src="t.image" alt="现场照片" />
          <div class="meta">
            <span>设备：{{ t.device_name || '—' }}</span>
            <span>维修工：{{ t.worker_name || '待分配' }}</span>
            <span>提交：{{ t.created_at }}</span>
            <span v-if="t.resolved_at">完成：{{ t.resolved_at }}</span>
          </div>
          <div v-if="t.solution" class="mt8 muted">处理结果：{{ t.solution }}</div>
          <div v-if="t.urge_count" class="mt8 muted">已催办 {{ t.urge_count }} 次</div>

          <div class="actions" v-if="t.status !== '已完成' && t.status !== '已驳回'">
            <button class="btn btn-sm btn-ghost" :disabled="urging[t.id]" @click="urge(t)">
              {{ urging[t.id] ? '催办中…' : '催办' }}
            </button>
          </div>

          <div class="rate-box" v-if="t.status === '已完成' && !t.rating">
            <div class="muted">请评价本次维修：</div>
            <div class="stars mt8">
              <span v-for="n in 5" :key="n" class="star" :class="{ on: n <= (rateMap[t.id] || 0) }" @click="rateMap[t.id] = n">★</span>
            </div>
            <input class="mt8" v-model.trim="commentMap[t.id]" placeholder="留言（可选）" />
            <button class="btn btn-sm mt8" @click="rate(t)">提交评价</button>
          </div>
          <div class="rate-box muted" v-else-if="t.status === '已完成' && t.rating">
            已评价：{{ '★'.repeat(t.rating) }}{{ '☆'.repeat(5 - t.rating) }}<span v-if="t.comment"> · {{ t.comment }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底端微信式 tab 切换 -->
    <div class="tabbar">
      <div class="tab" :class="{ on: activeTab === 'submit' }" @click="activeTab = 'submit'">
        <span class="tab-icon">📝</span>
        <span class="tab-label">提交报修</span>
      </div>
      <div class="tab" :class="{ on: activeTab === 'mine' }" @click="activeTab = 'mine'">
        <span class="tab-icon">📋</span>
        <span class="tab-label">我的报修</span>
      </div>
    </div>
  </div>
</template>

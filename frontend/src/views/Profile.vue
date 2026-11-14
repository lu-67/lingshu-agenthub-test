<template>
  <div class="pf">
    <!-- 顶部：头像 + 身份信息 + meta -->
    <section class="pf-header">
      <div class="pf-left">
        <div class="pf-avatar">{{ (me.username?.[0] || 'L').toUpperCase() }}</div>
        <div class="pf-title">
          <h1>{{ me.username }}</h1>
          <span class="pf-role" :class="me.role.toLowerCase()">{{ me.role === 'ADMIN' ? '管理员' : '普通用户' }}</span>
          <span class="pf-sep">·</span>
          <span class="pf-sub">ID {{ me.id }}</span>
          <span class="pf-sub">·</span>
          <span class="pf-sub">注册 {{ me.createdAt?.slice(0,10) || '-' }}</span>
        </div>
      </div>
      <dl class="pf-meta">
        <div><dt>Token</dt><dd class="mono">{{ tokenPreview }}</dd></div>
      </dl>
    </section>

    <!-- 4 格统计 -->
    <section class="pf-stats">
      <div class="stat">
        <span class="stat-icon">🧭</span>
        <div class="stat-body"><b>{{ me.stats?.agents ?? 0 }}</b><small>智能体</small></div>
      </div>
      <div class="stat">
        <span class="stat-icon">💬</span>
        <div class="stat-body"><b>{{ me.stats?.sessions ?? 0 }}</b><small>任务数</small></div>
      </div>
      <div class="stat">
        <span class="stat-icon">⚙️</span>
        <div class="stat-body"><b>{{ me.stats?.tasks ?? 0 }}</b><small>执行次数</small></div>
      </div>
      <div class="stat">
        <span class="stat-icon">🔗</span>
        <div class="stat-body"><b>{{ prefs.autoApprove ? '自动' : '手动' }}</b><small>审批模式</small></div>
      </div>
    </section>

    <!-- 下半：左偏好 + 右会话历史 -->
    <section class="pf-row2">
      <div class="pf-block wide">
        <h3>偏好设置</h3>
        <div class="pf-card2">
          <label v-for="opt in settings" :key="opt.key" class="pf-row">
            <div>
              <b>{{ opt.label }}</b>
              <small>{{ opt.desc }}</small>
            </div>
            <div class="toggle" :class="{on: prefs[opt.key]}" @click="prefs[opt.key] = !prefs[opt.key]; savePrefs()">
              <span class="dot"></span>
            </div>
          </label>
        </div>
      </div>

      <div class="pf-block wide">
        <h3>会话历史</h3>
        <div v-if="recent.length" class="sess-list">
          <div v-for="s in recent" :key="s.id" class="sess-row" @click="router.push(`/chat/${s.id}`)">
            <b>{{ trunc(s.title, 28) }}</b>
            <small>{{ fmtDate(s.createdAt) }}</small>
          </div>
        </div>
        <p v-else class="empty-note">暂无会话记录</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { auth, sessions as sessApi } from '../api'

const router = useRouter()
const me = reactive({ id: 0, username: '', role: 'USER', createdAt: '', stats: { agents: 0, sessions: 0, tasks: 0 } })
const recent = ref([])

const prefs = reactive({
  autoApprove: localStorage.getItem('nx_auto_approve') === 'true',
  showThinking: localStorage.getItem('nx_show_thinking') === 'true',
  markdown: localStorage.getItem('nx_markdown') !== 'false',
})

const settings = [
  { key: 'autoApprove',  label: '自动执行敏感动作', desc: '无需每次点击"批准"继续' },
  { key: 'showThinking', label: '思考过程默认展开', desc: 'AI 回答上方的 ▼ 折叠块' },
  { key: 'markdown',     label: 'Markdown 富文本', desc: '关闭后显示纯文本' },
]

function savePrefs() {
  localStorage.setItem('nx_auto_approve', prefs.autoApprove)
  localStorage.setItem('nx_show_thinking', prefs.showThinking)
  localStorage.setItem('nx_markdown', prefs.markdown)
}

const tokenPreview = computed(() => {
  const t = localStorage.getItem('nx_token') || ''
  return t.length > 0 ? `${t.slice(0, 12)}…${t.slice(-6)}` : '-'
})

function trunc(s, n) { return (s || '').length > n ? s.slice(0, n) + '…' : (s || '') }
function fmtDate(ts) {
  if (!ts) return '-'
  const d = new Date(ts)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return d.toTimeString().slice(0, 5)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

onMounted(async () => {
  try {
    const data = await auth.me()
    Object.assign(me, data)
  } catch (e) {
    console.warn('auth/me failed:', e)
    me.id = parseInt(localStorage.getItem('nx_uid')) || 0
    me.username = localStorage.getItem('nx_user') || ''
    me.role = localStorage.getItem('nx_role') || 'USER'
  }
  try {
    const r = await sessApi.list(null, 8)
    recent.value = (r.sessions || []).map(s => ({ id: s.id, title: s.title, createdAt: s.createdAt }))
  } catch {}
})
</script>

<style scoped>
.pf { padding: 28px 32px; max-width: 1080px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }

/* 顶部 header */
.pf-header {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  padding: 24px 28px; display: flex; align-items: center; justify-content: space-between; gap: 24px;
}
.pf-left { display: flex; align-items: center; gap: 18px; min-width: 0; }
.pf-avatar {
  width: 56px; height: 56px; border-radius: 14px;
  background: #111827; color: #fff; display: grid; place-items: center;
  font-size: 22px; font-weight: 700; flex: none;
}
.pf-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pf-title h1 { margin: 0; font-size: 20px; font-weight: 700; color: #111827; letter-spacing: -.01em; }
.pf-role { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.pf-role.admin { background: #FEF3C7; color: #92400E; }
.pf-role.user  { background: #DBEAFE; color: #1E40AF; }
.pf-sep { color: #D1D5DB; font-size: 12px; }
.pf-sub { font-size: 12px; color: #6B7280; }

.pf-meta { margin: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.pf-meta dt { font-size: 11px; color: #9CA3AF; }
.pf-meta dd { margin: 0; font-size: 12px; color: #374151; font-family: var(--mono); }

/* 统计行 */
.pf-stats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
}
.stat {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 12px;
  padding: 16px 18px; display: flex; align-items: center; gap: 14px;
}
.stat-icon { font-size: 22px; }
.stat-body { display: flex; flex-direction: column; gap: 2px; }
.stat b { font-size: 22px; font-weight: 700; color: #111827; letter-spacing: -.01em; line-height: 1; }
.stat small { font-size: 11.5px; color: #6B7280; }

/* 下半两列 */
.pf-row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.pf-block { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 20px; }
.pf-block h3 { margin: 0 0 14px; font-size: 13px; font-weight: 600; color: #374151; letter-spacing: .01em; }

.pf-card2 { /* 外层已经是 pf-block 的背景了 */ }
.pf-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #F3F4F6; }
.pf-row:last-child { border-bottom: none; }
.pf-row b { display: block; font-size: 13px; color: #111827; font-weight: 600; margin-bottom: 2px; }
.pf-row small { font-size: 11.5px; color: #9CA3AF; }
.toggle { width: 38px; height: 22px; border-radius: 999px; background: #E5E7EB; position: relative; cursor: pointer; flex: none; transition: background .15s; }
.toggle .dot { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: #fff; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,.15); transition: transform .15s; }
.toggle.on { background: #111827; }
.toggle.on .dot { transform: translateX(16px); }

.sess-list { max-height: 240px; overflow-y: auto; }
.sess-row { padding: 10px 2px; border-bottom: 1px solid #F3F4F6; display: flex; justify-content: space-between; gap: 10px; cursor: pointer; }
.sess-row:hover b { color: #111827; }
.sess-row:last-child { border-bottom: none; }
.sess-row b { font-size: 13px; color: #374151; font-weight: 500; }
.sess-row small { font-size: 11.5px; color: #9CA3AF; flex: none; }
.empty-note { margin: 0; padding: 20px; font-size: 12.5px; color: #9CA3AF; text-align: center; }

@media (max-width: 720px) {
  .pf { padding: 20px; }
  .pf-header { flex-direction: column; align-items: flex-start; }
  .pf-meta { align-items: flex-start; }
  .pf-stats { grid-template-columns: repeat(2, 1fr); }
  .pf-row2 { grid-template-columns: 1fr; }
}
</style>

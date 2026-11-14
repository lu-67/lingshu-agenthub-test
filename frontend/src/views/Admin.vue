<template>
  <div class="admin">
    <div class="hd">
      <h2>管理后台</h2>
      <nav class="tabs">
        <button v-for="t in tabs" :key="t.id" :class="{ active: tab === t.id }"
                @click="tab = t.id">{{ t.label }}</button>
      </nav>
    </div>

    <!-- ===== 概览 ===== -->
    <section v-if="tab === 'overview'" class="tab-body">
      <div class="stat-row">
        <div v-for="s in statsList" :key="s.key" class="stat">
          <span class="ico">{{ s.icon }}</span>
          <div>
            <b>{{ stats[s.key] ?? '-' }}</b>
            <small>{{ s.label }}</small>
          </div>
        </div>
      </div>
      <div class="grid-2">
        <div class="panel">
          <h4>数据库</h4>
          <div v-if="db" class="kv">
            <span>库名</span><b>{{ db.database }}</b>
            <span>引擎</span><b>{{ db.backend }}</b>
            <span>表数</span><b>{{ db.tables }}</b>
            <span>总行数</span><b>{{ db.rows?.toLocaleString() }}</b>
            <span>总大小</span><b>{{ db.size_mb ?? '-' }} MB</b>
          </div>
        </div>
        <div class="panel">
          <h4>调度器</h4>
          <div v-if="sch" class="kv">
            <span>运行中</span><b :class="{ good: sch.running, bad: !sch.running }">{{ sch.running ? '是' : '否' }}</b>
            <span>已注册 jobs</span><b>{{ sch.jobs?.length ?? 0 }}</b>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 用户管理 ===== -->
    <section v-if="tab === 'users'" class="tab-body">
      <div class="panel users-panel">
        <h4>用户列表（{{ users.length }}）</h4>
        <table class="tbl">
          <thead>
            <tr><th>ID</th><th>用户名</th><th>角色</th><th>注册时间</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id" :class="{ sel: uid === u.id }">
              <td class="mono">{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td><span class="role" :class="u.role.toLowerCase()">{{ u.role === 'ADMIN' ? '管理员' : '普通' }}</span></td>
              <td>{{ u.createdAt?.slice(0, 10) || '-' }}</td>
              <td>
                <button class="act" @click="openDetail(u.id)">查看详情</button>
                <button class="del" @click="del(u)" :disabled="u.id === myUid">删除</button>
              </td>
            </tr>
            <tr v-if="!users.length"><td colspan="5" class="empty">暂无用户</td></tr>
          </tbody>
        </table>
      </div>

      <div v-if="detail" class="panel detail-panel">
        <div class="detail-hd">
          <h4>{{ detail.username }}（id={{ detail.id }}）· {{ detail.role === 'ADMIN' ? '管理员' : '普通用户' }}</h4>
          <button class="close" @click="detail = null">✕</button>
        </div>
        <div class="count-row">
          <div v-for="(v, k) in detail.counts" :key="k" class="mini">
            <b>{{ v }}</b><small>{{ labelOf(k) }}</small>
          </div>
        </div>
        <div class="sub-block">
          <h5>最近智能体（{{ detail.recent_agents?.length || 0 }}）</h5>
          <table class="tbl">
            <thead><tr><th>ID</th><th>名称</th><th>模型</th><th>状态</th></tr></thead>
            <tbody>
              <tr v-for="a in detail.recent_agents" :key="a.id">
                <td class="mono">{{ a.id }}</td><td>{{ a.name }}</td>
                <td>{{ a.model }}</td>
                <td>{{ a.enabled ? '启用' : '停用' }}</td>
              </tr>
              <tr v-if="!detail.recent_agents?.length"><td colspan="4" class="empty">无</td></tr>
            </tbody>
          </table>
        </div>
        <div class="sub-block">
          <h5>最近定时任务（{{ detail.recent_automations?.length || 0 }}）</h5>
          <table class="tbl">
            <thead><tr><th>ID</th><th>名称</th><th>Cron</th><th>状态</th><th>上次</th><th>下次</th></tr></thead>
            <tbody>
              <tr v-for="a in detail.recent_automations" :key="a.id">
                <td class="mono">{{ a.id }}</td><td>{{ a.name }}</td>
                <td class="mono">{{ a.cron_expr }}</td>
                <td>{{ a.enabled ? '启用' : '停用' }}</td>
                <td class="mono small">{{ fmt(a.last_run_at) }}</td>
                <td class="mono small">{{ fmt(a.next_run_at) }}</td>
              </tr>
              <tr v-if="!detail.recent_automations?.length"><td colspan="6" class="empty">无</td></tr>
            </tbody>
          </table>
        </div>
        <div class="sub-block">
          <h5>最近任务（{{ detail.recent_tasks?.length || 0 }}）</h5>
          <table class="tbl">
            <thead><tr><th>ID</th><th>目标</th><th>状态</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="t in detail.recent_tasks" :key="t.id">
                <td class="mono">{{ t.id }}</td><td class="truncate" :title="t.goal">{{ t.goal }}</td>
                <td>{{ t.status }}</td>
                <td class="mono small">{{ fmt(t.created_at) }}</td>
              </tr>
              <tr v-if="!detail.recent_tasks?.length"><td colspan="4" class="empty">无</td></tr>
            </tbody>
          </table>
        </div>
        <div class="sub-block">
          <h5>最近会话（{{ detail.recent_sessions?.length || 0 }}）</h5>
          <table class="tbl">
            <thead><tr><th>ID</th><th>标题</th><th>最后消息</th><th>更新时间</th></tr></thead>
            <tbody>
              <tr v-for="s in detail.recent_sessions" :key="s.id">
                <td class="mono">{{ s.id }}</td><td>{{ s.title }}</td>
                <td class="truncate small" :title="s.last_message">{{ s.last_message }}</td>
                <td class="mono small">{{ fmt(s.updated_at) }}</td>
              </tr>
              <tr v-if="!detail.recent_sessions?.length"><td colspan="4" class="empty">无</td></tr>
            </tbody>
          </table>
        </div>
        <div class="sub-block">
          <h5>最近运行记录（{{ detail.recent_runs?.length || 0 }}）</h5>
          <table class="tbl">
            <thead><tr><th>ID</th><th>类型</th><th>状态</th><th>耗时(ms)</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="r in detail.recent_runs" :key="r.id">
                <td class="mono">{{ r.id }}</td><td>{{ r.kind }}</td>
                <td>{{ r.status }}</td><td>{{ r.elapsed_ms }}</td>
                <td class="mono small">{{ fmt(r.created_at) }}</td>
              </tr>
              <tr v-if="!detail.recent_runs?.length"><td colspan="5" class="empty">无</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- ===== 数据库 ===== -->
    <section v-if="tab === 'db'" class="tab-body">
      <div v-if="db" class="panel">
        <div class="panel-hd">
          <h4>数据表（{{ db.tables }}）</h4>
          <span class="muted">共 {{ db.rows?.toLocaleString() }} 行 · {{ db.size_mb ?? '-' }} MB</span>
        </div>
        <table class="tbl">
          <thead>
            <tr><th>表名</th><th>引擎</th><th>行数（约）</th><th>大小 MB</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in db.per_table" :key="t.table_name">
              <td class="mono">{{ t.table_name }}</td>
              <td>{{ t.engine }}</td>
              <td>{{ (t.table_rows || 0).toLocaleString() }}</td>
              <td>{{ t.mb ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ===== 定时任务 ===== -->
    <section v-if="tab === 'sch'" class="tab-body">
      <div v-if="sch" class="panel">
        <div class="panel-hd">
          <h4>调度器状态</h4>
          <span class="muted" :class="{ good: sch.running, bad: !sch.running }">
            {{ sch.running ? '● 运行中' : '○ 未启动' }}
          </span>
        </div>
        <table class="tbl">
          <thead><tr><th>Job ID</th><th>触发器</th><th>下次执行</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="j in sch.jobs" :key="j.job_id">
              <td class="mono">{{ j.job_id }}</td>
              <td class="mono small">{{ j.trigger }}</td>
              <td class="mono">{{ j.next_run || '—' }}</td>
              <td>{{ j.enabled ? '启用' : '停用' }}</td>
            </tr>
            <tr v-if="!sch.jobs?.length"><td colspan="4" class="empty">暂无注册的定时任务</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import http from '../api'

const tabs = [
  { id: 'overview', label: '概览' },
  { id: 'users',    label: '用户管理' },
  { id: 'db',       label: '数据库状态' },
  { id: 'sch',      label: '定时任务调度器' },
]
const tab = ref('overview')

const users = ref([])
const stats = reactive({})
const db = ref(null)
const sch = ref(null)
const detail = ref(null)
const myUid = parseInt(localStorage.getItem('nx_uid')) || 0

const statsList = [
  { icon: '👥', key: 'users',      label: '注册用户' },
  { icon: '🧭', key: 'agents',     label: '智能体' },
  { icon: '💬', key: 'sessions',   label: '会话' },
  { icon: '📨', key: 'messages',   label: '消息' },
  { icon: '⏰', key: 'automations', label: '定时任务' },
  { icon: '📋', key: 'tasks',      label: '任务' },
]

const LABELS = { agents:'智能体', sessions:'会话', messages:'消息', tasks:'任务',
                 automations:'定时任务', runs:'运行记录' }
const labelOf = (k) => LABELS[k] || k

function fmt(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return String(iso).slice(0, 19)
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function loadAll() {
  try {
    const [st, ur, ov, sc] = await Promise.allSettled([
      http.get('/admin/stats'),
      http.get('/admin/users', { params: { limit: 200 } }),
      http.get('/admin/db/overview'),
      http.get('/admin/scheduler/status'),
    ])
    if (st.status === 'fulfilled') Object.assign(stats, st.value)
    if (ur.status === 'fulfilled') users.value = ur.value.users || []
    if (ov.status === 'fulfilled') db.value = ov.value
    if (sc.status === 'fulfilled') sch.value = sc.value
  } catch (e) { console.warn(e) }
}

async function openDetail(uid) {
  try {
    detail.value = await http.get(`/admin/users/${uid}`)
  } catch (e) { alert(e?.response?.data?.detail || '加载失败') }
}

async function del(u) {
  if (!confirm(`确定删除 ${u.username}？其所有数据将一并删除，不可恢复。`)) return
  try {
    await http.delete(`/admin/users/${u.id}`)
    users.value = users.value.filter(x => x.id !== u.id)
    if (detail.value?.id === u.id) detail.value = null
    if (stats.users != null) stats.users = Math.max(0, stats.users - 1)
  } catch (e) { alert(e?.response?.data?.detail || '删除失败') }
}

onMounted(loadAll)
</script>

<style scoped>
.admin { padding: 20px 28px; max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.hd h2 { margin: 0; font-size: 17px; font-weight: 600; color: #111827; }
.tabs { display: flex; gap: 4px; }
.tabs button {
  padding: 6px 14px; border: 1px solid #E5E7EB; border-radius: 8px; background: #fff;
  color: #6B7280; font-size: 12.5px; cursor: pointer;
}
.tabs button:hover { color: #111827; border-color: #D1D5DB; }
.tabs button.active { background: #111827; color: #fff; border-color: #111827; }

.tab-body { display: flex; flex-direction: column; gap: 14px; }

.stat-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.stat {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 10px;
  padding: 12px 14px; display: flex; align-items: center; gap: 10px;
}
.ico { font-size: 20px; }
.stat b { font-size: 18px; font-weight: 700; color: #111827; display: block; line-height: 1; }
.stat small { font-size: 11px; color: #6B7280; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.panel { background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; padding: 16px 18px; }
.panel h4 { margin: 0 0 12px; font-size: 13px; font-weight: 600; color: #111827; }
.panel-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.kv { display: grid; grid-template-columns: 120px 1fr; gap: 6px 16px; font-size: 13px; }
.kv span { color: #6B7280; }
.kv b { color: #111827; font-weight: 600; }
.good { color: #059669; }
.bad  { color: #DC2626; }
.muted { color: #9CA3AF; font-size: 12px; }
.muted.good { color: #059669; } .muted.bad { color: #DC2626; }

.detail-panel { position: relative; }
.detail-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.detail-hd h4 { margin: 0; font-size: 14px; }
.close { border: none; background: none; cursor: pointer; color: #9CA3AF; font-size: 16px; padding: 2px 6px; }
.close:hover { color: #111827; }
.count-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin-bottom: 14px; }
.count-row .mini {
  text-align: center; border: 1px solid #E5E7EB; border-radius: 8px; padding: 10px 4px;
}
.count-row .mini b { display: block; font-size: 18px; font-weight: 700; color: #111827; }
.count-row .mini small { font-size: 11px; color: #6B7280; }
.sub-block { margin-top: 14px; }
.sub-block h5 { margin: 0 0 8px; font-size: 12px; color: #6B7280; font-weight: 600; }

.tbl { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.tbl th { text-align: left; padding: 8px 10px; font-size: 11px; color: #9CA3AF; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid #F3F4F6; }
.tbl td { padding: 9px 10px; color: #374151; border-bottom: 1px solid #F3F4F6; }
.tbl tr:last-child td { border-bottom: none; }
.tbl tr:hover td { background: #FAFBFC; }
.tbl tr.sel td { background: #F9FAFB; }
.tbl .mono { font-family: Consolas, Menlo, monospace; font-size: 12px; color: #6B7280; }
.tbl .small { font-size: 11.5px; }
.role { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.role.admin { background: #FEF3C7; color: #92400E; }
.role.user  { background: #DBEAFE; color: #1E40AF; }

.act { border: 1px solid #D1D5DB; background: #fff; color: #374151; padding: 3px 8px; border-radius: 6px; font-size: 11.5px; cursor: pointer; margin-right: 4px; }
.act:hover { border-color: #6B7280; color: #111827; }
.del { border: 1px solid #FECACA; background: #fff; color: #DC2626; padding: 3px 8px; border-radius: 6px; font-size: 11.5px; cursor: pointer; }
.del:hover:not(:disabled) { background: #FEF2F2; }
.del:disabled { opacity: .4; cursor: not-allowed; }

.empty { text-align: center; color: #9CA3AF; padding: 20px; font-size: 12px; }

@media (max-width: 860px) {
  .stat-row { grid-template-columns: repeat(3, 1fr); }
  .grid-2 { grid-template-columns: 1fr; }
  .count-row { grid-template-columns: repeat(3, 1fr); }
}
</style>

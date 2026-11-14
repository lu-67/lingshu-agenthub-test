<template>
  <div class="auto-page">
    <div class="head">
      <div>
        <h2>自动化</h2>
        <p class="sub">设定定时任务让智能体自动执行。错过运行会在下次启动时补偿。</p>
      </div>
      <button class="create-btn" @click="openEditor()"><Icon name="plus" :size="15" /> 新建定时任务</button>
    </div>

    <div v-if="!list.length" class="empty">还没有定时任务</div>

    <div v-for="a in list" :key="a.id" class="card">
      <div class="cl" :class="{ off: !a.enabled }">
        <span class="avatar">{{ a.agentAvatar }}</span>
        <div class="cinfo">
          <div class="cname">{{ a.name }} <span class="sub">· {{ a.agentName }}</span></div>
          <div class="cgoal">{{ a.goal }}</div>
        </div>
      </div>
      <div class="cron-row">
        <span class="cron">{{ a.cronExpr }}</span>
        <span class="cron-human">{{ cronToHuman(a.cronExpr) }}</span>
        <span v-if="a.lastRunAt" class="cron-info">上次：{{ fmt(a.lastRunAt) }}</span>
        <span v-if="a.nextRunAt" class="cron-info">下次：{{ fmt(a.nextRunAt) }}</span>
      </div>
      <div class="foot">
        <el-switch v-model="a.enabled" @change="toggle(a)" />
        <div class="actions">
          <button class="act" @click="openEditor(a)">编辑</button>
          <button class="act del" @click="remove(a)">删除</button>
        </div>
      </div>
    </div>

    <!-- 编辑 -->
    <el-dialog v-model="dialog" :title="editing ? '编辑定时任务' : '新建定时任务'" width="520px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" maxlength="64" placeholder="每日天气 / 每周报告" />
        </el-form-item>
        <el-form-item label="选择智能体">
          <el-select v-model="form.agentId" style="width:100%">
            <el-option v-for="a in agents" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行频率">
          <div class="cron-box">
            <div class="preset-row">
              <span class="preset-label">常用预设（点一下就行）</span>
              <div class="preset-list">
                <button v-for="p in presets" :key="p.expr" type="button"
                        class="preset" :class="{ active: form.cronExpr === p.expr }"
                        @click="form.cronExpr = p.expr">{{ p.label }}</button>
              </div>
            </div>
            <div class="cron-hint" :class="{ bad: !isValidCron(form.cronExpr) }">
              <span v-if="isValidCron(form.cronExpr)">✓ 已选：{{ cronToHuman(form.cronExpr) }}</span>
              <span v-else>⚠️ 格式不对，请点上方预设或手动填写</span>
            </div>
            <div class="cron-advanced">
              <button type="button" class="adv-toggle" @click="showAdv = !showAdv">
                {{ showAdv ? '▾' : '▸' }} 高级：自定义时间表达式
              </button>
              <div v-if="showAdv" class="adv-body">
                <el-input v-model="form.cronExpr" placeholder="例如 0 9 * * * 表示每天 9 点" />
                <div class="adv-help">
                  <div>5 个字段，空格分隔：<code>分 时 日 月 周</code></div>
                  <div>常用：<code>*</code>=任意  <code>*/5</code>=每 5   <code>1-5</code>=范围  <code>1,3,5</code>=列表</div>
                  <div>周：0=周日  1-6=周一到周六</div>
                </div>
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="目标">
          <el-input v-model="form.goal" type="textarea" :rows="3"
                    placeholder="每天早上 9 点帮我整理昨天市场动态和建议" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import Icon from '../components/Icon.vue'
import { automations as autoApi, agents as agentsApi } from '../api'

const list = ref([])
const agents = ref([])
const dialog = ref(false)
const editing = ref(null)
const showAdv = ref(false)
const form = reactive({ name: '', agentId: null, cronExpr: '', goal: '' })

// 常用预设：label = 人类可读, expr = cron
const presets = [
  { label: '每分钟', expr: '* * * * *' },
  { label: '每小时整点', expr: '0 * * * *' },
  { label: '每天早上 9:00', expr: '0 9 * * *' },
  { label: '每天上午 9:30', expr: '30 9 * * *' },
  { label: '每天中午 12:00', expr: '0 12 * * *' },
  { label: '每天晚上 20:00', expr: '0 20 * * *' },
  { label: '工作日早上 9:00', expr: '0 9 * * 1-5' },
  { label: '周一早上 9:00', expr: '0 9 * * 1' },
  { label: '每月 1 号早上 9:00', expr: '0 9 1 * *' },
]

// ---------- cron 解析 ----------
const _WEEKDAYS = ['周日','周一','周二','周三','周四','周五','周六']

function cronToHuman(expr) {
  const parts = (expr || '').trim().split(/\s+/)
  if (parts.length !== 5) return '—'
  const [m, h, dom, mon, dow] = parts
  // 时分
  let time = ''
  if (m !== '*' && h !== '*') {
    time = `${h.padStart(2,'0')}:${m.padStart(2,'0')}`
  } else if (h === '*' && m === '*') {
    // 每分钟
    return '每分钟'
  } else if (h === '*') {
    return `每小时的第 ${m} 分钟`
  } else {
    time = `每小时在 :${m.padStart(2,'0')}`
  }
  // 星期
  if (dow === '*' && dom === '*') {
    return `每天 ${time}`
  } else if (dow !== '*') {
    if (dow.includes('-')) {
      const [a, b] = dow.split('-').map(Number)
      return `每周${_WEEKDAYS[a]}到${_WEEKDAYS[b]} ${time}`
    } else if (dow.includes(',')) {
      return `每周 ${dow.split(',').map(x => _WEEKDAYS[Number(x)]).join('、')} ${time}`
    } else {
      return `每周${_WEEKDAYS[Number(dow)]} ${time}`
    }
  } else if (dom !== '*') {
    if (mon !== '*') {
      return `每月${dom}号 ${time}`
    }
    return `每月 ${dom} 号 ${time}`
  }
  return expr
}

function isValidCron(expr) {
  const parts = (expr || '').trim().split(/\s+/)
  return parts.length >= 5 && parts.every(p => /^[\d\s*,*\/\-]+$/.test(p))
}

function cronHint(expr) {
  if (!expr) return '选择上方预设，或手动输入 Cron 表达式（5 字段：分 时 日 月 周）'
  if (!isValidCron(expr)) return '⚠️ 表达式格式不对，应为 5 个字段（如 0 9 * * *）'
  return `✓ ${cronToHuman(expr)}`
}

// ---------- CRUD ----------
async function reload() {
  list.value = (await autoApi.list()).automations || []
  agents.value = (await agentsApi.list()).agents || []
}

function openEditor(a = null) {
  editing.value = a
  if (a) Object.assign(form, { name: a.name, agentId: a.agentId, cronExpr: a.cronExpr, goal: a.goal })
  else Object.assign(form, { name: '', agentId: agents.value[0]?.id, cronExpr: '0 9 * * *', goal: '' })
  dialog.value = true
}

async function save() {
  if (!form.name.trim() || !form.goal.trim() || !form.cronExpr.trim() || !form.agentId)
    return alert('请完整填写名称、智能体、执行频率和目标')
  if (!isValidCron(form.cronExpr))
    return alert('Cron 表达式格式不对，应为 5 个字段（如 0 9 * * *）')
  if (editing.value) await autoApi.update(editing.value.id, form)
  else await autoApi.create({ ...form })
  dialog.value = false
  await reload()
}

async function toggle(a) { await autoApi.update(a.id, { enabled: a.enabled }) }
async function remove(a) { if (!confirm(`删除「${a.name}」？`)) return; await autoApi.remove(a.id); await reload() }

function fmt(iso) { if (!iso) return '-'; const d = new Date(iso); return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}` }

onMounted(reload)
</script>

<style scoped>
.auto-page { padding: 24px 32px; height: 100%; overflow-y: auto; }
.head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; }
.head h2 { margin: 0 0 4px; font-size: 20px; }
.head .sub { margin: 0; color: var(--muted); font-size: 13px; }
.create-btn { display: flex; align-items: center; gap: 6px; height: 36px; padding: 0 16px;
              border-radius: 10px; border: none; background: var(--primary); color: #fff;
              font-size: 13px; cursor: pointer; }
.create-btn:hover { filter: brightness(1.1); }
.empty { padding: 60px; text-align: center; color: var(--muted); font-size: 13px;
         border: 1px dashed var(--border-strong); border-radius: 12px; }

.card {
  margin-bottom: 14px; padding: 16px 18px; border-radius: 14px; background: var(--surface-2);
  border: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px;
}
.cl { display: flex; gap: 12px; align-items: flex-start; }
.cl.off { opacity: .5; }
.avatar { width: 38px; height: 38px; border-radius: 10px; background: var(--surface);
          display: grid; place-items: center; font-size: 18px; flex: none; }
.cinfo { flex: 1; min-width: 0; }
.cname { font-size: 14px; font-weight: 600; }
.cname .sub { font-size: 11px; color: var(--muted); font-weight: 400; }
.cgoal { font-size: 12px; color: var(--text-2); margin-top: 3px; line-height: 1.5; }

.cron-row { display: flex; gap: 10px; align-items: center; padding: 6px 10px;
            background: var(--surface); border-radius: 8px; font-size: 11.5px; flex-wrap: wrap; }
.cron { font-family: var(--mono); color: var(--primary); font-weight: 600; }
.cron-human { color: var(--text-2); font-weight: 500; }
.cron-info { color: var(--muted); }
.foot { display: flex; justify-content: space-between; align-items: center; }
.actions { display: flex; gap: 6px; }
.act { padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border-strong);
       background: var(--surface); color: var(--text-2); font-size: 11.5px; cursor: pointer; }
.act:hover { border-color: var(--primary); color: var(--primary); }
.act.del:hover { border-color: #EF4444; color: #EF4444; }

/* --- cron editor --- */
.cron-box { border: 1px solid var(--border); border-radius: 10px; padding: 12px;
            background: var(--surface); display: flex; flex-direction: column; gap: 10px; }
.preset-row { display: flex; flex-direction: column; gap: 6px; }
.preset-label { font-size: 11px; color: var(--muted); }
.preset-list { display: flex; flex-wrap: wrap; gap: 6px; }
.preset {
  padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border-strong);
  background: var(--surface-2); color: var(--text-2); font-size: 12px; cursor: pointer;
  transition: all .15s;
}
.preset:hover { border-color: var(--primary); color: var(--primary); }
.preset.active { border-color: var(--primary); background: var(--primary); color: #fff; }
.cron-hint { font-size: 12.5px; color: var(--muted); padding: 2px 4px 0; }
.cron-hint.bad { color: #EF4444; }
.cron-advanced { margin-top: 8px; border-top: 1px dashed var(--border); padding-top: 10px; }
.adv-toggle {
  background: none; border: none; color: var(--primary); font-size: 12px;
  cursor: pointer; padding: 0; font-weight: 500;
}
.adv-toggle:hover { text-decoration: underline; }
.adv-body { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; }
.adv-help { font-size: 11.5px; color: var(--muted); line-height: 1.6; }
.adv-help code {
  background: var(--surface-2); padding: 1px 5px; border-radius: 4px;
  font-family: var(--mono); font-size: 11px; color: var(--text-2);
}
</style>

<template>
  <div v-if="session" class="chat">
    <section class="center">
      <div class="msgs" ref="msgBox">
        <!-- 开场白 -->
        <template v-if="messages.length === 0">
          <div class="intro">
            <span class="avatar">{{ agent.avatar }}</span>
            <div class="intro-bubble">
              <b>Hi，我是 {{ agent.name }}。</b>
              <small v-if="agent.description">{{ agent.description }}</small>
              <small>把目标告诉我，我会自己拆计划、多角色协作执行，把结果交付给你。</small>
            </div>
          </div>
          <div class="suggestions">
            <div v-for="q in SUGGESTIONS" :key="q" class="chip" @click="quick(q)">{{ q }}</div>
          </div>
        </template>

        <template v-for="m in messages" :key="m.id">
          <!-- 用户 -->
          <div v-if="m.role === 'user'" class="msg user">
            <div class="bubble user">{{ m.content }}</div>
          </div>

          <!-- 授权 -->
          <div v-else-if="m.status === 'waiting_approval'" class="msg assistant">
            <span class="avatar sm">{{ agent.avatar }}</span>
            <div class="a-body">
              <div class="ap-card">
                <div class="ap-title">需要你的授权</div>
                <div class="ap-desc">执行到「{{ m.data?.title }}」将触发敏感动作，请确认后继续。</div>
                <div class="ap-actions">
                  <button class="ap-cancel" @click="reload">取消</button>
                  <button class="ap-ok" @click="approve">同意并继续</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 错误 -->
          <div v-else-if="m.msgType === 'error'" class="msg assistant">
            <span class="avatar sm">{{ agent.avatar }}</span>
            <div class="a-body">
              <div class="err-card">{{ m.content }}</div>
            </div>
          </div>

          <!-- assistant 富文本回答（唯一正常分支） -->
          <div v-else class="msg assistant">
            <span class="avatar sm">{{ agent.avatar }}</span>
            <div class="a-body">
              <div class="a-meta">
                <b>{{ agent.name }}</b>
                <span>{{ fmtTime(m.createdAt) }}</span>
              </div>
              <!-- 可展开思考过程（Accio Work 风格） -->
              <details v-if="m.data?.thinking?.length" class="think">
                <summary>
                  <span class="tk-icon">▼</span>
                  <span>思考过程 · {{ m.data.thinking.length }} 步</span>
                </summary>
                <div class="tk-list">
                  <div v-for="(s, i) in m.data.thinking" :key="i" class="tk-row">
                    <span class="tk-dot">{{ s.status === 'success' ? '✓' : '…' }}</span>
                    <span class="tk-role">{{ s.role }}</span>
                    <span class="tk-title">{{ s.title }}</span>
                    <span class="tk-ms">{{ s.elapsedMs }}ms</span>
                  </div>
                </div>
              </details>
              <div class="bubble assistant markdown-body" v-html="renderMd(m.content || '')"></div>
              <div v-if="m.data?.artifacts?.length" class="a-files">
                <button v-for="a in m.data.artifacts" :key="a.id" class="f-chip"
                        @click="downloadArt(a)">
                  {{ kindLabel(a.kind) }} · {{ a.title }} ↓
                </button>
              </div>
            </div>
          </div>
        </template>

        <div v-if="running" class="msg assistant">
          <span class="avatar sm">{{ agent.avatar }}</span>
          <div class="a-body">
            <div class="typing"><span></span><span></span><span></span></div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <div class="input-bar">
          <textarea v-model="input" :disabled="running"
                    placeholder="输入问题… (@ 引用文件)"
                    @keydown.enter.exact.prevent="send" rows="1"></textarea>
          <button class="send" :disabled="running || !input.trim()" @click="send">
            <Icon name="send" :size="15" />
          </button>
        </div>
        <div class="input-row">
          <button class="it-btn"><Icon name="plus" :size="13" /> 添加</button>
          <button class="it-btn"><Icon name="bot" :size="13" /> 插件</button>
          <select class="it-select" v-model="perm">
            <option value="safe">权限：需授权</option>
            <option value="auto">自动执行</option>
          </select>
          <div class="spacer"></div>
          <button class="it-btn ghost">自动</button>
          <button class="it-btn ghost" title="语音"><Icon name="terminal" :size="13" /></button>
        </div>
      </div>
    </section>
  </div>

  <div v-else class="no-sess">
    <p>请先从「智能体市场」选择一个智能体开始任务。</p>
    <router-link to="/experts" class="go">去智能体市场</router-link>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import Icon from '../components/Icon.vue'
import { agents, sessions as sessApi, artifacts } from '../api'

const md = new MarkdownIt({ html: false, breaks: true })
const route = useRoute()
const router = useRouter()
const sid = computed(() => route.params.sid)

const SUGGESTIONS = [
  '调研 2026 年国内宠物智能硬件市场',
  '写 3 条小红书种草文案，主题是 AI 智能体工作台',
  '对比 DeepSeek / Kimi / 通义 在智能体方向的布局',
]

const session = ref(null)
const messages = ref([])
const agent = ref({})
const input = ref('')
const running = ref(false)
const perm = ref('safe')
const msgBox = ref(null)

function buildRunMd_deprecated() { /* legacy placeholder, kept for reference */ }

async function load() {
  try {
    session.value = await sessApi.get(sid.value)
    messages.value = session.value.messages || []
    const al = await agents.list()
    agent.value = al.agents.find(a => a.id === session.value.agentId) || {}
    await scrollBottom()
  } catch { router.replace('/experts') }
}
async function reload() { await load() }

function renderMd(t) { return t ? md.render(t) : '' }

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

function kindLabel(k) {
  return { report: '📝 报告', table: '📊 数据表', checklist: '✅ 清单' }[k] || k
}

async function send() {
  const content = input.value.trim()
  if (!content || running.value || !session.value) return
  input.value = ''; running.value = true; await nextTick(); await scrollBottom()
  try {
    const res = await sessApi.send(session.value.id, {
      content, autoApprove: perm.value === 'auto'
    })
    messages.value = res.messages || []
  } catch (e) {
    messages.value.push({
      role: 'assistant', msgType: 'error', content: e?.detail || '发送失败',
      createdAt: new Date().toISOString(),
    })
  } finally {
    running.value = false; await scrollBottom()
  }
}

async function approve() {
  running.value = true
  try {
    const res = await sessApi.approve(session.value.id)
    messages.value = res.messages || []
  } catch (e) { alert(e?.detail || '授权失败') }
  finally { running.value = false; await scrollBottom() }
}

async function downloadArt(a) {
  try {
    const blob = await artifacts.download(a.id)
    const url = URL.createObjectURL(blob)
    const el = document.createElement('a')
    el.href = url; el.download = `${a.title}.${a.format}`; el.click()
    URL.revokeObjectURL(url)
  } catch { alert('下载失败') }
}

async function scrollBottom() {
  await nextTick()
  msgBox.value?.scrollTo({ top: msgBox.value.scrollHeight, behavior: 'smooth' })
}
function quick(q) { input.value = q; send() }

watch(() => sid.value, () => load())
onMounted(load)
</script>

<style scoped>
.chat { height: 100%; display: flex; }
.center { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #FFFFFF; }

/* ======= 对话流 ======= */
.msgs { flex: 1; overflow-y: auto; padding: 20px 32px 12px; display: flex; flex-direction: column; gap: 18px; }

/* 开场白 */
.intro { display: flex; gap: 10px; align-items: flex-start; margin: 8px 0 2px; }
.intro .avatar { width: 28px; height: 28px; border-radius: 50%; font-size: 14px;
                 background: #F3F4F6; display: grid; place-items: center; flex: none; }
.intro-bubble { background: #F9FAFB; border-radius: 12px 12px 12px 2px;
                padding: 12px 16px; max-width: 600px; display: flex; flex-direction: column; gap: 3px; }
.intro-bubble b { font-size: 14px; color: #111827; font-weight: 600; }
.intro-bubble small { font-size: 12px; color: #6B7280; line-height: 1.55; }

.suggestions { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; padding-left: 38px; }
.chip { padding: 6px 12px; border-radius: 14px; background: #fff; border: 1px solid #E5E7EB;
        font-size: 12px; color: #111827; cursor: pointer; }
.chip:hover { border-color: #111827; }

/* 消息行 */
.msg { display: flex; gap: 10px; }
.msg.user { justify-content: flex-end; }
.msg.user .bubble { margin-left: auto; }

/* 头像 */
.avatar.sm {
  width: 28px; height: 28px; border-radius: 50%; font-size: 14px;
  background: #F3F4F6; display: grid; place-items: center; flex: none;
}

/* assistant body */
.a-body { flex: 1; min-width: 0; max-width: 720px; }
.a-meta { display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; }
.a-meta b { font-size: 13px; color: #111827; font-weight: 600; }
.a-meta span { font-size: 11px; color: #9CA3AF; font-family: var(--mono); }

/* ===== 思考过程折叠块（Accio Work 风格） ===== */
.think {
  margin-bottom: 8px; border: 1px solid #E5E7EB; border-radius: 6px;
  background: #FAFBFC; overflow: hidden;
}
.think > summary {
  cursor: pointer; padding: 6px 12px;
  font-size: 12px; color: #6B7280; user-select: none;
  display: flex; align-items: center; gap: 6px;
}
.think > summary:hover { color: #111827; background: #F3F4F6; }
.think[open] > summary { border-bottom: 1px solid #E5E7EB; color: #374151; }
.tk-icon { font-size: 9px; transition: transform .15s; display: inline-block; }
.think[open] .tk-icon { transform: rotate(180deg); }
.tk-list { padding: 6px 12px; display: flex; flex-direction: column; gap: 3px; }
.tk-row {
  display: flex; align-items: center; gap: 6px;
  font-size: 11.5px; color: #4B5563;
}
.tk-dot {
  width: 14px; text-align: center; font-size: 10px;
  color: #22C55E; flex: none;
}
.tk-row .tk-dot { color: #22C55E; }
.tk-role { color: #6B7280; min-width: 52px; flex: none; font-weight: 500; }
.tk-title { flex: 1; color: #374151; }
.tk-ms { color: #9CA3AF; font-family: var(--mono); font-size: 10.5px; }
.a-track {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; color: #6B7280; padding: 2px 8px; border-radius: 4px;
  background: #F3F4F6; margin-bottom: 6px;
}

/* 气泡 */
.bubble { padding: 10px 14px; max-width: 100%; line-height: 1.65; font-size: 14px; word-wrap: break-word; }
.bubble.user {
  background: #374151; color: #fff; border-radius: 14px 2px 14px 14px;
  max-width: 60%;
}
.bubble.assistant {
  background: transparent; border-radius: 2px; border: none; padding: 0;
}

/* markdown body */
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3),
.markdown-body :deep(h4), .markdown-body :deep(h5), .markdown-body :deep(h6) {
  margin: 14px 0 6px; font-weight: 650; color: #111827; line-height: 1.3;
}
.markdown-body :deep(h1) { font-size: 18px; }
.markdown-body :deep(h2) { font-size: 16px; }
.markdown-body :deep(h3) { font-size: 14px; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 4px 0; padding-left: 20px; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(strong) { font-weight: 650; color: #111827; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid #E5E7EB; margin: 12px 0; }
.markdown-body :deep(blockquote) {
  margin: 6px 0; padding: 4px 12px; border-left: 2px solid #E5E7EB;
  color: #6B7280; background: #F9FAFB; border-radius: 0 6px 6px 0;
}
.markdown-body :deep(code) {
  background: #F3F4F6; padding: 1px 5px; border-radius: 4px;
  font-family: var(--mono); font-size: 12.5px;
}
.markdown-body :deep(pre) {
  background: #111827; color: #E5E7EB; padding: 12px; border-radius: 8px;
  overflow-x: auto; margin: 8px 0; font-size: 12.5px;
}
.markdown-body :deep(pre code) { background: transparent; padding: 0; color: inherit; }
.markdown-body :deep(a) { color: #111827; text-decoration: underline; }
.markdown-body :deep(table) { border-collapse: collapse; margin: 10px 0; font-size: 12.5px; }
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #E5E7EB; padding: 6px 12px; text-align: left;
}
.markdown-body :deep(th) { background: #F9FAFB; font-weight: 600; }
.markdown-body :deep(details) {
  margin: 10px 0; border: 1px solid #E5E7EB; border-radius: 8px;
  padding: 6px 12px; background: #F9FAFB;
}
.markdown-body :deep(summary) {
  cursor: pointer; font-size: 12.5px; color: #374151; padding: 2px 0;
}
.markdown-body :deep(summary:hover) { color: #111827; }

/* 交付物下载按钮组 */
.a-files { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.f-chip {
  font-size: 12px; padding: 4px 10px; border-radius: 6px;
  border: 1px solid #E5E7EB; background: #F9FAFB; color: #374151;
  cursor: pointer;
}
.f-chip:hover { border-color: #111827; color: #111827; background: #fff; }

/* 授权 / 错误 */
.ap-card {
  max-width: 520px; background: #FFFBEB; border: 1px solid #FCD34D;
  border-radius: 10px; padding: 12px 16px;
}
.ap-title { font-weight: 600; color: #92400E; margin-bottom: 4px; font-size: 13px; }
.ap-desc { font-size: 12.5px; color: #78350F; line-height: 1.5; }
.ap-actions { display: flex; gap: 8px; margin-top: 10px; }
.ap-cancel, .ap-ok {
  padding: 6px 16px; border-radius: 7px; font-size: 12.5px; cursor: pointer;
  border: 1px solid #D1D5DB; background: #fff; color: #374151;
}
.ap-ok { background: #111827; color: #fff; border-color: #111827; }

.err-card {
  max-width: 520px; background: #FEF2F2; border: 1px solid #FCA5A5;
  border-radius: 10px; padding: 12px 16px; color: #991B1B; font-size: 13px;
}

/* typing */
.typing { display: flex; gap: 4px; padding: 4px 0; }
.typing span {
  width: 6px; height: 6px; border-radius: 50%; background: #9CA3AF;
  animation: bounce 1.2s infinite;
}
.typing span:nth-child(2) { animation-delay: .15s; }
.typing span:nth-child(3) { animation-delay: .3s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }

/* ======= 输入区 ======= */
.input-area { padding: 10px 32px 16px; background: #fff; border-top: 1px solid #E5E7EB; }
.input-bar {
  display: flex; align-items: flex-end; gap: 10px; padding: 10px 14px;
  border-radius: 12px; border: 1px solid #E5E7EB; background: #fff;
}
.input-bar:focus-within { border-color: #111827; }
.input-bar textarea {
  flex: 1; border: none; background: transparent; outline: none; color: #111827;
  font-size: 14px; resize: none; min-height: 22px; max-height: 160px; line-height: 1.5;
  font-family: inherit;
}
.send {
  width: 34px; height: 34px; border-radius: 9px; border: none; background: #22C55E;
  color: #fff; display: grid; place-items: center; cursor: pointer; flex: none;
}
.send:hover:not(:disabled) { background: #16A34A; }
.send:disabled { opacity: .4; cursor: not-allowed; }

.input-row {
  display: flex; align-items: center; gap: 6px; margin-top: 8px;
}
.it-btn {
  display: inline-flex; align-items: center; gap: 4px;
  height: 28px; padding: 0 10px; border-radius: 6px;
  border: 1px solid #E5E7EB; background: #fff; color: #374151;
  font-size: 12px; cursor: pointer;
}
.it-btn:hover { border-color: #111827; color: #111827; }
.it-btn.ghost { border-color: transparent; background: transparent; }
.it-select {
  height: 28px; padding: 0 8px; border-radius: 6px; border: 1px solid #E5E7EB;
  background: #fff; font-size: 12px; color: #374151; cursor: pointer;
}
.spacer { flex: 1; }

.no-sess { padding: 60px; text-align: center; color: #6B7280; }
.no-sess .go { color: #111827; text-decoration: underline; margin-left: 8px; }
</style>

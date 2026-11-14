<template>
  <div class="newtask">
    <!-- 头部欢迎区 -->
    <div class="welcome">
      <h1>你好，我是灵枢助手</h1>
      <p class="welcome-sub">说一句目标就开始干活——我会自己拆计划、多角色协作、把结果交付给你。</p>
    </div>

    <!-- 输入框 -->
    <div class="input-card">
      <textarea v-model="goal" :disabled="running"
                placeholder="例如：帮我调研 2026 年国内宠物智能硬件市场，输出 3 页报告 + 竞品对比表"
                rows="2"></textarea>
      <div class="input-foot">
        <span class="count">{{ goal.length }} / 500</span>
        <button class="send" :disabled="running || !goal.trim()" @click="quickRun">
          <Icon name="send" :size="15" /> 立即执行
        </button>
      </div>
    </div>

    <!-- 快捷入口：选智能体 -->
    <div class="panel">
      <div class="panel-head">
        <h3>1 · 选一个智能体</h3>
        <router-link to="/experts" class="panel-link">全部智能体 ›</router-link>
      </div>
      <div class="expert-row">
        <div v-for="a in experts" :key="a.id" class="expert-chip" :class="{on: pickedId === a.id}"
             @click="pickedId = a.id">
          <span class="eca" :style="bgFor(a.id)">{{ a.avatar }}</span>
          <div class="einfo">
            <b>{{ a.name }}</b>
            <small>{{ a.description }}</small>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷场景 -->
    <div class="panel">
      <div class="panel-head">
        <h3>2 · 或者，从常见场景开始</h3>
      </div>
      <div class="scene-grid">
        <div v-for="c in SCENES" :key="c.title" class="scene" @click="useScene(c)">
          <span class="sc-icon">{{ c.icon }}</span>
          <div class="sc-text">
            <b>{{ c.title }}</b>
            <small>{{ c.desc }}</small>
          </div>
          <Icon name="right" :size="13" class="sc-arrow" />
        </div>
      </div>
    </div>

    <!-- 最近任务 -->
    <div class="panel">
      <div class="panel-head">
        <h3>最近任务</h3>
      </div>
      <template v-if="sessions.length">
        <div class="recent">
          <router-link v-for="s in sessions" :key="s.id"
                       :to="`/chat/${s.id}`" class="recent-item">
            <span class="rca">{{ s.agentAvatar }}</span>
            <div class="rmeta">
              <b>{{ s.agentName }} · {{ trunc(s.title, 22) }}</b>
              <small>{{ trunc(stripMd(s.lastMessage), 40) || '（空）' }}</small>
            </div>
            <Icon name="right" :size="13" />
          </router-link>
        </div>
      </template>
      <div v-else class="recent-empty">还没有任务——说一句目标就开始吧</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { agents as agentsApi, sessions as sessApi } from '../api'

const router = useRouter()
const SCENES = [
  { icon: '📊', title: '市场调研', desc: '行业扫描 + 趋势 + 机会点',
    goal: '帮我调研 {topic} 市场，输出趋势、格局与机会点报告', skillHint: 'market_research' },
  { icon: '🔎', title: '竞品对比', desc: '3 个竞品的功能矩阵与差异化',
    goal: '对比 {A} / {B} / {C} 的功能与定价，输出对比表', skillHint: 'competitor_analysis' },
  { icon: '✍️', title: '文案创作', desc: '小红书 / 公众号 / 活动文案',
    goal: '写 3 条关于 {主题} 的小红书种草文案', skillHint: 'content_marketing' },
  { icon: '📈', title: '数据洞察', desc: '整理清洗 + 对比 + 建议',
    goal: '对比 {period1} vs {period2} 的 {指标}，给出结论和建议', skillHint: 'data_organize' },
  { icon: '💬', title: '知识问答', desc: '引用团队知识库回答',
    goal: '根据团队知识库，回答「{问题}」', skillHint: 'knowledge_qa' },
  { icon: '🧭', title: '通用任务', desc: '不确定用哪个技能时的兜底',
    goal: '帮我完成一个 {任务类型}：{描述}', skillHint: 'general' },
]

const goal = ref('')
const running = ref(false)
const experts = ref([])
const pickedId = ref(null)
const sessions = ref([])

function trunc(s, n) { return s ? (s.length > n ? s.slice(0, n) + '…' : s) : '' }
function stripMd(s) {
  if (!s) return ''
  return s
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\n+/g, ' ')
    .trim()
}

function bgFor(i) {
  const bgs = [
    '#F3F4F6', '#F9FAFB', '#F3F4F6', '#F9FAFB', '#F3F4F6', '#F9FAFB',
  ]
  return bgs[(i - 1) % bgs.length]
}

function useScene(c) {
  goal.value = c.goal.replace('{topic}', '某个领域').replace('{A} / {B} / {C}', '竞品 A / B / C')
                      .replace('{主题}', '你的产品').replace('{period1} vs {period2}', '上季度 vs 本季度')
                      .replace('{指标}', '核心指标').replace('{问题}', '你的问题')
                      .replace('{任务类型}', '任务').replace('{描述}', '具体描述')
}

async function quickRun() {
  if (!goal.value.trim()) return
  const agentId = pickedId.value || experts.value[0]?.id
  if (!agentId) { alert('请选一个智能体'); return }
  running.value = true
  try {
    // 先创建 session + 同步发送第一条消息（后端会执行 plan→steps→summarize）
    const sess = await sessApi.create({ agentId, title: trunc(goal.value, 24) })
    await sessApi.send(sess.id, { content: goal.value, autoApprove: true })
    router.push(`/chat/${sess.id}`)
  } catch (e) {
    console.error('quickRun failed:', e)
    alert('执行失败：' + (e?.detail || e?.message || '未知错误'))
  } finally { running.value = false }
}

onMounted(async () => {
  const ar = await agentsApi.list(); experts.value = ar.agents.slice(0, 6)
  if (experts.value.length) pickedId.value = experts.value[0].id
  const sr = await sessApi.list(null, 6); sessions.value = sr.sessions
})
</script>

<style scoped>
.newtask { padding: 36px 40px 60px; max-width: 940px; margin: 0 auto; }

/* 欢迎区 */
.welcome { text-align: center; margin-bottom: 20px; padding-top: 8px; }
.welcome h1 { margin: 0 0 6px; font-size: 24px; color: #111827; letter-spacing: -.01em; font-weight: 700; }
.welcome-sub { margin: 0; font-size: 13.5px; color: #6B7280; }

/* 输入卡片 */
.input-card {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 16px; padding: 18px 20px;
  box-shadow: 0 6px 22px rgba(17,24,39,.06);
  transition: border-color .15s, box-shadow .15s;
}
.input-card:focus-within { border-color: #111827; box-shadow: 0 10px 30px rgba(17,24,39,.1); }
.input-card textarea {
  width: 100%; box-sizing: border-box; border: none; outline: none; resize: none;
  font-size: 15px; color: #111827; background: transparent; font-family: inherit;
  line-height: 1.6; min-height: 56px;
}
.input-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.count { font-size: 11.5px; color: #9CA3AF; font-family: var(--mono); }
.send {
  height: 34px; padding: 0 16px; border-radius: 10px; border: none;
  background: #111827; color: #fff; font-size: 13px; font-weight: 600;
  display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
  transition: transform .1s;
}
.send:hover:not(:disabled) { transform: scale(1.03); }
.send:disabled { opacity: .4; cursor: not-allowed; }

/* 面板 */
.panel { margin-top: 24px; }
.panel-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
.panel-head h3 { margin: 0; font-size: 14px; color: #111827; font-weight: 600; }
.panel-link { font-size: 12px; color: #374151; text-decoration: none; }
.panel-link:hover { color: #111827; text-decoration: underline; }

/* 智能体行 */
.expert-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.expert-chip {
  display: flex; gap: 10px; align-items: center; padding: 10px 12px; border-radius: 12px;
  background: #fff; border: 1px solid #E5E7EB; cursor: pointer; transition: all .1s;
}
.expert-chip:hover { border-color: #111827; }
.expert-chip.on { border-color: #111827; background: #F9FAFB; box-shadow: 0 0 0 3px rgba(17,24,39,.05); }
.eca { width: 36px; height: 36px; border-radius: 8px; display: grid; place-items: center;
       font-size: 18px; color: #111827; flex: none; }
.einfo { flex: 1; min-width: 0; }
.einfo b { display: block; font-size: 12.5px; color: #111827; font-weight: 600; }
.einfo small { font-size: 11px; color: #6B7280; display: block; margin-top: 1px;
               overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 场景网格 */
.scene-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 10px; }
.scene {
  display: flex; gap: 12px; align-items: center; padding: 12px 14px; border-radius: 12px;
  background: #fff; border: 1px solid #E5E7EB; cursor: pointer; transition: all .1s;
}
.scene:hover { border-color: #111827; transform: translateY(-1px); box-shadow: 0 4px 14px rgba(17,24,39,.06); }
.sc-icon { width: 36px; height: 36px; border-radius: 10px; background: #F3F4F6; font-size: 18px;
           display: grid; place-items: center; flex: none; }
.sc-text { flex: 1; min-width: 0; }
.sc-text b { display: block; font-size: 13px; color: #111827; font-weight: 600; }
.sc-text small { font-size: 11.5px; color: #6B7280; display: block; margin-top: 1px; }
.sc-arrow { color: #9CA3AF; flex: none; }
.scene:hover .sc-arrow { color: #111827; }

/* 最近 */
.recent { display: flex; flex-direction: column; gap: 6px; }
.recent-empty { padding: 20px 12px; text-align: center; color: #9CA3AF; font-size: 12px; }
.recent-item {
  display: flex; gap: 10px; align-items: center; padding: 9px 12px; border-radius: 10px;
  background: #fff; border: 1px solid #E5E7EB; text-decoration: none; color: inherit;
}
.recent-item:hover { border-color: #111827; }
.rca { width: 28px; height: 28px; border-radius: 7px; background: #F3F4F6; font-size: 14px;
       display: grid; place-items: center; flex: none; }
.rmeta { flex: 1; min-width: 0; }
.rmeta b { display: block; font-size: 12.5px; color: #111827; font-weight: 600; }
.rmeta small { font-size: 11px; color: #6B7280; }
</style>

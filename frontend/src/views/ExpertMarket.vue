<template>
  <div class="expert-page">
    <div class="page-head">
      <div>
        <h1>智能体市场</h1>
        <p class="sub">内置 6 个领域智能体，也可以按业务自定义。选中后直接开聊，一键让 AI 团队帮你干活。</p>
      </div>
      <div class="head-tools">
        <input v-model="kw" class="search" placeholder="搜索智能体名称或专长" />
        <button class="btn primary" @click="openCreate"><Icon name="plus" :size="13" /> 新建智能体</button>
      </div>
    </div>

    <div class="grid-head">
      <div class="cards">
        <div v-for="a in filtered" :key="a.id" class="card">
          <div class="cavatar" :style="bgFor(a.id)">{{ a.avatar }}</div>
          <div class="cname">
            {{ a.name }}
            <span class="verified" v-if="a.isBuiltin">内置</span>
          </div>
          <div class="cdesc">{{ a.description || builtinDesc(a.name) }}</div>
          <button class="talk-btn" @click="startChat(a)">
            <Icon name="chat" :size="12" /> 开始任务
          </button>
        </div>
        <div class="card add" @click="openCreate">
          <div class="cavatar add-ga">+</div>
          <div class="cname muted">自定义智能体</div>
          <div class="cdesc">从 0 开始，绑定你需要的技能与系统指令</div>
          <button class="talk-btn ghost">新建</button>
        </div>
      </div>
    </div>

    <!-- ========== 新建 / 编辑 弹窗 ========== -->
    <el-dialog v-model="dialog" width="820px">
      <template #header>
        <div class="dhead">
          <span class="davatar">{{ form.avatar }}</span>
          <div class="dtitle">
            <b>{{ editing ? '编辑智能体' : '新建智能体' }}</b>
            <small v-if="editing && editing.isBuiltin">内置智能体可修改配置、不可删除</small>
          </div>
        </div>
      </template>

      <div class="body">
        <!-- 左侧 Tab -->
        <aside class="side">
          <div v-for="t in CTABS" :key="t.key" class="ctab"
               :class="{ on: tabKey === t.key }" @click="tabKey = t.key">
            <span>{{ t.icon }}</span> {{ t.label }}
            <em v-if="t.key === 'skills'" class="num">{{ form.skillIds.length }}</em>
          </div>
        </aside>

        <!-- 中间表单 -->
        <section class="form">
          <div v-if="tabKey === 'identity'">
            <label class="flabel required">名称</label>
            <input class="finput" v-model="form.name" maxlength="32" placeholder="例如：小红书文案写手" />

            <label class="flabel">头像</label>
            <div class="avatar-row">
              <div class="avatar-big" :style="bgFor(form.name.length || 1)">{{ form.avatar }}</div>
              <div class="avatar-picks">
                <button v-for="em in EMOJIS" :key="em" :class="{on: form.avatar === em}"
                        class="emo" @click="form.avatar = em">{{ em }}</button>
              </div>
            </div>

            <label class="flabel">描述 · 这个智能体擅长什么</label>
            <textarea class="ftextarea" v-model="form.description" :rows="3"
                      placeholder="由你设定角色与专长，执行时会按这里的描述调整语气与输出风格。" />

            <label class="flabel">系统指令（可选）</label>
            <textarea class="ftextarea" v-model="form.systemPrompt" :rows="3"
                      placeholder="进一步约束角色行为，例如：回答要引用来源、每段不超过 3 行、只用 Markdown 格式…" />

            <label class="flabel">模型</label>
            <select class="finput" v-model="form.model">
              <option value="mock">Mock（离线确定性，可直接断言）</option>
              <option value="deepseek">DeepSeek Live</option>
              <option value="kimi">Kimi Live</option>
            </select>
          </div>

          <div v-if="tabKey === 'skills'">
            <label class="flabel">勾选此智能体可调用的技能</label>
            <p class="fhint">技能是预定义的任务模板（角色 + 步骤 + 动作），决定了执行时会生成哪些步骤、
              由哪些角色协作、最终产出几份交付物。</p>
            <div class="skill-grid">
              <label v-for="s in SKILLS" :key="s.id" class="sk-row">
                <input type="checkbox" v-model="form.skillIds" :value="s.id" />
                <span class="skn">{{ s.name }}</span>
                <span class="skd">{{ s.desc }}</span>
              </label>
            </div>
          </div>

          <div v-if="tabKey === 'files'">
            <label class="flabel">知识库（可选）</label>
            <div class="files-area">
              <div class="empty">功能预留：后续可将 Markdown / PDF 上传到知识库，智能体会在执行时自动召回。</div>
            </div>
          </div>
        </section>

        <!-- 右侧实时预览 -->
        <aside class="preview">
          <div class="pv-title">预览效果</div>
          <div class="pv-card">
            <div class="pv-avatar" :style="bgFor((form.name.length || 1) + 3)">{{ form.avatar }}</div>
            <div class="pv-name">{{ form.name || '智能体名称' }}</div>
            <div class="pv-desc">{{ form.description || '由你设定角色与专长…' }}</div>
            <div class="pv-skills">
              <span v-for="sid in form.skillIds" :key="sid" class="s-tag">{{ skillName(sid) }}</span>
              <span v-if="!form.skillIds.length" class="s-tag empty">无</span>
            </div>
          </div>
        </aside>
      </div>

      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :disabled="!form.name.trim()" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { agents as agentsApi, sessions as sessApi } from '../api'

const router = useRouter()
const kw = ref('')
const agents = ref([])
const dialog = ref(false)
const tabKey = ref('identity')
const editing = ref(null)

const EMOJIS = ['🤖', '🎨', '📊', '🛍️', '✍️', '🔎', '💬', '📈', '🧭', '⚡', '🌐', '🔬']
const CTABS = [
  { key: 'identity', icon: '🧑', label: '身份' },
  { key: 'skills', icon: '🧩', label: '技能' },
  { key: 'files', icon: '📁', label: '知识库' },
]
const SKILLS = [
  { id: 'market_research', name: '市场调研', desc: '行业扫描 / 趋势洞察 / 机会点' },
  { id: 'competitor_analysis', name: '竞品分析', desc: '竞品拆解 / 功能矩阵 / 差异化策略' },
  { id: 'content_marketing', name: '内容营销', desc: '文案 / 种草 / 活动策划' },
  { id: 'data_organize', name: '数据整理', desc: '清洗 / 对比 / 洞察' },
  { id: 'knowledge_qa', name: '知识问答', desc: '引用知识库原文回答' },
  { id: 'general', name: '通用任务', desc: '不确定选哪个时的兜底' },
]

const BUILTIN_DESC = {
  '灵枢助手': '全能型 AI 助手。处理业务调研、写作、分析等各种任务，不确定选哪个时的首选。',
  '市场调研官': '行业扫描、消费者洞察、机会点输出',
  '电商主理人': '商品选品、主图文案、竞品对比',
  '内容创作手': '小红书 / 公众号文案、活动策划',
  '数据分析师': '数据整理、指标对比、趋势洞察',
  '知识问答官': '引用知识库原文回答问题',
}

const form = reactive({
  name: '', avatar: '🤖', description: '', systemPrompt: '', model: 'mock',
  skillIds: ['general'], sort: 80, enabled: true,
})

const filtered = computed(() =>
  agents.value.filter(a =>
    !kw.value ||
    (a.name + a.description + (a.skillIds || []).map(skillName).join(',')).includes(kw.value)
  )
)

function skillName(id) { return (SKILLS.find(s => s.id === id) || {}).name || id }

function bgFor(i) {
  const bgs = ['#F3F4F6', '#F9FAFB', '#F3F4F6', '#F9FAFB', '#F3F4F6', '#F9FAFB', '#F3F4F6', '#F9FAFB']
  return bgs[(Math.abs(i - 1)) % bgs.length]
}

function builtinDesc(n) { return BUILTIN_DESC[n] || '内置智能体' }

async function reload() {
  const res = await agentsApi.list(); agents.value = res.agents || []
}

function openCreate(a = null) {
  editing.value = a
  if (a) {
    Object.assign(form, {
      name: a.name, avatar: a.avatar, description: a.description,
      systemPrompt: a.systemPrompt, model: a.model || 'mock',
      skillIds: [...(a.skillIds || [])], sort: a.sort || 80, enabled: a.enabled,
    })
  } else {
    Object.assign(form, {
      name: '', avatar: '🤖', description: '', systemPrompt: '',
      model: 'mock', skillIds: ['general'], sort: 80, enabled: true,
    })
  }
  tabKey.value = 'identity'
  dialog.value = true
}

async function save() {
  if (!form.name.trim()) return alert('请填名称')
  const payload = {
    name: form.name, avatar: form.avatar, description: form.description,
    systemPrompt: form.systemPrompt, model: form.model, skillIds: form.skillIds,
    sort: form.sort, enabled: form.enabled,
  }
  if (editing.value) {
    await agentsApi.update(editing.value.id, payload)
  } else {
    await agentsApi.create(payload)
  }
  dialog.value = false; await reload()
}

async function startChat(a) {
  const r = await sessApi.create({ agentId: a.id, title: `与 ${a.name} 的任务` })
  router.push(`/chat/${r.id}`)
}

onMounted(reload)
</script>

<style scoped>
.expert-page { padding: 28px 32px 60px; }

.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; margin-bottom: 14px; }
.page-head h1 { margin: 0 0 4px; font-size: 22px; color: #111827; font-weight: 700; letter-spacing: -.01em; }
.page-head .sub { margin: 0; font-size: 13px; color: #6B7280; max-width: 520px; line-height: 1.55; }
.head-tools { display: flex; gap: 8px; align-items: center; }
.search {
  width: 260px; height: 34px; padding: 0 12px; border-radius: 8px; border: 1px solid #E5E7EB;
  background: #fff; font-size: 13px; outline: none;
}
.search:focus { border-color: #111827; }
.btn { height: 34px; padding: 0 14px; border-radius: 8px; font-size: 13px; cursor: pointer;
       border: 1px solid transparent; display: inline-flex; align-items: center; gap: 5px; }
.btn.primary { background: #111827; color: #fff; }
.btn.primary:hover { background: #000; }

.grid-head { margin-top: 14px; }
.cards {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px;
}

.card {
  background: #fff; border-radius: 14px; padding: 22px 18px 16px; border: 1px solid #E5E7EB;
  display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center;
  transition: transform .12s, box-shadow .12s;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(17,24,39,.08); }
.card.add { border-style: dashed; border-color: #D1D5DB; background: #FAFAFA; cursor: pointer; }
.card.add-ga {
  width: 64px; height: 64px; border-radius: 18px; background: #F3F4F6;
  display: grid; place-items: center; font-size: 28px; color: #9CA3AF;
}
.cavatar {
  width: 64px; height: 64px; border-radius: 16px; display: grid; place-items: center;
  font-size: 28px; color: #111827;
}
.cname { font-size: 15px; font-weight: 650; color: #111827; display: flex; align-items: center; gap: 6px; }
.cname.muted { color: #6B7280; }
.verified {
  font-size: 10px; padding: 1px 7px; border-radius: 6px;
  background: #F3F4F6; color: #374151; font-weight: 500; border: 1px solid #E5E7EB;
}
.cdesc { font-size: 12px; color: #6B7280; line-height: 1.55; min-height: 36px; }
.talk-btn {
  margin-top: 6px; height: 32px; width: 100%; border-radius: 8px; border: none; cursor: pointer;
  background: #22C55E; color: #fff; font-size: 13px; font-weight: 600;
  display: flex; align-items: center; justify-content: center; gap: 4px;
}
.talk-btn:hover { background: #16A34A; }
.talk-btn.ghost { background: #F3F4F6; color: #6B7280; }

/* ============ 弹窗 ============ */
.dhead { display: flex; gap: 10px; align-items: center; }
.davatar {
  width: 34px; height: 34px; border-radius: 10px;
  display: grid; place-items: center; font-size: 17px; background: #F3F4F6;
}
.dtitle b { font-size: 14px; color: #111827; display: block; }
.dtitle small { font-size: 11px; color: #9CA3AF; }

.body { display: flex; gap: 18px; min-height: 340px; }

.side { width: 110px; flex: none; display: flex; flex-direction: column; gap: 4px;
        border-right: 1px solid #E5E7EB; padding: 2px 0; }
.ctab {
  display: flex; align-items: center; gap: 8px; height: 34px; padding: 0 10px;
  border-radius: 8px; font-size: 13px; color: #374151; cursor: pointer; position: relative;
}
.ctab:hover { background: #F3F4F6; }
.ctab.on { background: #111827; color: #fff; font-weight: 600; }
.ctab em { margin-left: auto; font-style: normal; font-size: 10px;
           padding: 1px 6px; border-radius: 8px; background: rgba(0,0,0,.07); }
.ctab.on em { background: rgba(255,255,255,.25); }

.form { flex: 1; padding: 2px; overflow-y: auto; }
.flabel { font-size: 13px; font-weight: 600; color: #111827; display: block; margin: 4px 0 6px; }
.flabel.required::after { content: '*'; color: #EF4444; margin-left: 2px; }
.finput, .ftextarea {
  width: 100%; box-sizing: border-box; padding: 9px 12px; border: 1px solid #E5E7EB;
  border-radius: 8px; font-size: 13px; outline: none; background: #fff; font-family: inherit;
}
.finput:focus, .ftextarea:focus { border-color: #111827; }
.ftextarea { resize: vertical; min-height: 88px; }
.fhint { font-size: 11.5px; color: #6B7280; margin: -2px 0 10px; line-height: 1.55; }

.avatar-row { display: flex; gap: 14px; align-items: center; margin: 4px 0 14px; }
.avatar-big {
  width: 56px; height: 56px; border-radius: 14px; display: grid; place-items: center;
  font-size: 28px; color: #111827;
}
.avatar-picks { display: flex; flex-wrap: wrap; gap: 4px; max-width: 320px; }
.emo {
  width: 30px; height: 30px; border-radius: 7px; border: 1px solid #E5E7EB;
  background: #fff; cursor: pointer; font-size: 14px; display: grid; place-items: center;
}
.emo:hover { border-color: #111827; }
.emo.on { border-color: #111827; background: #111827; }

.skill-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.sk-row {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 8px;
  border: 1px solid #E5E7EB; cursor: pointer; font-size: 12.5px;
}
.sk-row:hover { background: #F3F4F6; }
.skn { font-weight: 600; min-width: 84px; }
.skd { color: #6B7280; font-size: 11px; }

.files-area { padding: 20px; border: 2px dashed #E5E7EB; border-radius: 10px;
              background: #FAFAFA; text-align: center; }
.files-area .empty { color: #9CA3AF; font-size: 12px; line-height: 1.6; }

/* 右侧预览 */
.preview { width: 180px; flex: none; border-left: 1px solid #E5E7EB; padding-left: 16px; }
.pv-title { font-size: 12px; font-weight: 600; color: #111827; margin-bottom: 10px; }
.pv-card {
  padding: 16px 14px; border-radius: 12px; background: #F9FAFB;
  border: 1px solid #E5E7EB; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 6px;
}
.pv-avatar {
  width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
  font-size: 22px; color: #111827;
}
.pv-name { font-size: 14px; font-weight: 600; color: #111827; }
.pv-desc { font-size: 11px; color: #6B7280; line-height: 1.5; min-height: 32px; }
.pv-skills { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; margin-top: 4px; }
.s-tag { font-size: 10.5px; padding: 1px 8px; border-radius: 6px;
         background: #F3F4F6; color: #374151; border: 1px solid #E5E7EB; }
.s-tag.empty { background: #F9FAFB; color: #9CA3AF; }
</style>

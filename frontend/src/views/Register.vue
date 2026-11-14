<template>
  <div class="auth">
    <!-- 左侧品牌区（和登录页完全对称） -->
    <div class="brand-side">
      <div class="bs-bg"></div>
      <div class="bs-inner">
        <div class="brand-mark">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect x="3" y="3" width="15" height="15" rx="3.5" stroke="#FFFFFF" stroke-width="1.5"/>
            <rect x="18" y="18" width="15" height="15" rx="3.5" stroke="#FFFFFF" stroke-width="1.5"/>
            <rect x="33" y="33" width="12" height="12" rx="3" stroke="#FFFFFF" stroke-width="1.5"/>
          </svg>
        </div>
        <h1>灵枢 AgentHub</h1>
        <p class="tagline">AI 智能体工作台 · 多角色协作 · 可展开思考</p>
      </div>
    </div>

    <!-- 右侧 -->
    <div class="form-side">
      <form class="card" @submit.prevent="submit" novalidate>
        <h2>创建账号</h2>
        <p class="sub">30 秒开始使用</p>

        <label class="field">
          <div class="fhd"><span>用户名</span><small :class="{ok: unameOk, warn: !unameOk && unameTouched}">3–20 字母/数字/_/-</small></div>
          <input v-model="form.username" @blur="unameTouched=true" placeholder="例如 zhangsan" spellcheck="false" maxlength="20" />
        </label>

        <label class="field">
          <div class="fhd"><span>密码</span><small :class="{err: form.password && form.password.length < 6}">至少 6 位</small></div>
          <input v-model="form.password" type="password" placeholder="至少 6 位" autocomplete="new-password" />
          <div class="strength">
            <div class="bars">
              <span v-for="i in 4" :key="i" class="bar" :class="[strengthColor, {on: i <= strengthLevel}]"></span>
            </div>
            <small :class="strengthColor">{{ strengthLabel }}</small>
          </div>
        </label>

        <label class="field">
          <div class="fhd"><span>确认密码</span><small v-if="form.confirm && !confirmOk" class="err">两次不一致</small></div>
          <input v-model="form.confirm" type="password" placeholder="再输入一次" autocomplete="new-password" />
        </label>

        <!-- 图形验证码 -->
        <label class="field">
          <div class="fhd"><span>验证码</span></div>
          <div class="captcha-row">
            <input v-model="form.captchaCode" placeholder="看图输入" maxlength="6" spellcheck="false" />
            <div class="captcha-img" @click="loadCaptcha" :title="'点击刷新'">
              <img v-if="captcha.image" :src="captcha.image" alt="验证码" />
              <span v-else-if="captcha.code" class="cap-fallback">{{ captcha.code }}</span>
              <span v-else class="cap-load">加载中…</span>
            </div>
          </div>
        </label>

        <p v-if="error" class="error">{{ error }}</p>

        <button class="submit" type="submit" :disabled="!canSubmit || loading">
          <span v-if="!loading">注册并登录</span>
          <span v-else class="loading-sp"></span>
        </button>

        <div class="switch">已有账号？<router-link to="/login">去登录</router-link></div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../api'
import http from '../api'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const unameTouched = ref(false)
const captcha = reactive({ id: '', image: '', code: '' })
const form = reactive({ username: '', password: '', confirm: '', captchaCode: '' })

const unameOk = computed(() => {
  const u = form.username.trim()
  return u.length >= 3 && u.length <= 20 && /^[a-zA-Z0-9_\-]+$/.test(u)
})
const strengthLevel = computed(() => {
  const p = form.password
  if (!p) return 0
  let s = 0
  if (p.length >= 6) s++
  if (p.length >= 10) s++
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++
  if (/\d/.test(p) && /[^A-Za-z0-9]/.test(p)) s++
  return s
})
const strengthColor = computed(() => ['', 'weak', 'ok', 'good', 'strong'][strengthLevel.value])
const strengthLabel = computed(() => ['', '弱', '一般', '良好', '强'][strengthLevel.value])
const confirmOk = computed(() => form.confirm === form.password)
const canSubmit = computed(() => unameOk.value && form.password.length >= 6 && confirmOk.value && form.captchaCode.trim().length > 0)

async function loadCaptcha() {
  try {
    const data = await http.get('/captcha')
    captcha.id = data.id
    captcha.image = data.image
    captcha.code = data.code || ''
    form.captchaCode = ''
  } catch (e) { console.warn('captcha fail', e) }
}

async function submit() {
  error.value = ''
  if (!canSubmit.value) { error.value = '请检查表单和验证码'; return }
  loading.value = true
  try {
    const r = await auth.register({
      username: form.username.trim(),
      password: form.password,
      captchaId: captcha.id,
      captchaCode: form.captchaCode.trim(),
    })
    localStorage.setItem('nx_token', r.token)
    localStorage.setItem('nx_user', r.username)
    localStorage.setItem('nx_role', r.role)
    if (r.id) localStorage.setItem('nx_uid', String(r.id))
    router.push('/new-task')
  } catch (e) {
    error.value = e?.detail || e?.message || '注册失败，请稍后重试'
    loadCaptcha()  // 失败了刷验证码
  } finally { loading.value = false }
}

onMounted(loadCaptcha)
</script>

<style scoped>
.auth { min-height: 100vh; display: flex; background: #FAFBFC; }
.brand-side {
  flex: 1; position: relative; overflow: hidden;
  background:
    radial-gradient(ellipse 90% 60% at 20% 15%, rgba(255,255,255,.07) 0%, transparent 55%),
    radial-gradient(ellipse 60% 80% at 85% 85%, rgba(34,197,94,.09) 0%, transparent 50%),
    linear-gradient(160deg, #0B1220 0%, #151F30 55%, #0F172A 100%);
  color: #fff; display: flex; align-items: center; padding: 48px; min-width: 500px;
}
.brand-side::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(circle 1px at 20% 30%, rgba(255,255,255,.5) 50%, transparent 100%),
    radial-gradient(circle 1px at 80% 70%, rgba(255,255,255,.4) 50%, transparent 100%),
    radial-gradient(circle 1px at 60% 10%, rgba(255,255,255,.3) 50%, transparent 100%),
    radial-gradient(circle 1px at 35% 85%, rgba(255,255,255,.3) 50%, transparent 100%),
    radial-gradient(circle 1px at 90% 40%, rgba(255,255,255,.4) 50%, transparent 100%);
  opacity: .35;
}
.bs-bg { position: absolute; inset: 0; pointer-events: none; opacity: .45; background: radial-gradient(circle at 20% 30%, rgba(34,197,94,.12) 0, transparent 40%), radial-gradient(circle at 80% 70%, rgba(99,102,241,.08) 0, transparent 50%), radial-gradient(circle at 60% 10%, rgba(255,255,255,.04) 0, transparent 30%); }
.bs-inner { position: relative; max-width: 420px; z-index: 1; }
.brand-mark { margin-bottom: 32px; }
.brand-side h1 { margin: 0 0 16px; font-size: 38px; font-weight: 700; letter-spacing: -.02em; line-height: 1.1; }
.tagline { margin: 0; font-size: 15px; color: #94A3B8; line-height: 1.6; }
.features { margin-top: 52px; display: flex; flex-direction: column; gap: 14px; }
.feat { display: flex; align-items: flex-start; gap: 12px; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #22C55E; flex: none; margin-top: 8px; box-shadow: 0 0 0 3px rgba(34,197,94,.2); }
.feat b { display: block; font-size: 13px; font-weight: 600; color: #fff; }
.feat small { font-size: 12px; color: #94A3B8; }
.bs-foot { margin-top: 48px; font-size: 11px; color: #64748B; letter-spacing: .05em; text-transform: uppercase; }

.form-side { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px; min-width: 400px; }
.card { width: 100%; max-width: 384px; background: #fff; border-radius: 16px; padding: 32px 28px; box-shadow: 0 1px 2px rgba(17,24,39,.04), 0 8px 24px rgba(17,24,39,.06); border: 1px solid rgba(229,231,235,.8); }
h2 { margin: 0 0 6px; font-size: 22px; font-weight: 700; color: #111827; letter-spacing: -.01em; text-align: center; }
.sub { margin: 0 0 20px; font-size: 12.5px; color: #9CA3AF; text-align: center; }

.field { display: block; margin-bottom: 14px; }
.fhd { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
.fhd > span { font-size: 12px; font-weight: 500; color: #374151; }
.fhd small { font-size: 11px; color: #9CA3AF; }
.fhd small.ok { color: #22C55E; }
.fhd small.warn, .fhd small.err { color: #DC2626; }
.field input {
  width: 100%; height: 40px; padding: 0 14px; font-size: 13.5px; color: #111827;
  background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; outline: none;
  transition: border-color .15s, box-shadow .15s; box-sizing: border-box;
}
.field input:focus { border-color: #111827; box-shadow: 0 0 0 4px rgba(17,24,39,.05); }
.field input::placeholder { color: #D1D5DB; }

/* 验证码 */
.captcha-row { display: flex; gap: 10px; align-items: stretch; }
.captcha-row input { flex: 1; }
.captcha-img {
  flex: none; width: 120px; height: 40px;
  border: 1px solid #E5E7EB; border-radius: 10px; background: #F8FAFC;
  cursor: pointer; display: grid; place-items: center; overflow: hidden;
  transition: border-color .15s;
}
.captcha-img:hover { border-color: #111827; }
.captcha-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
.cap-fallback { font-family: var(--mono); font-size: 18px; letter-spacing: 8px; font-weight: 700; color: #111827; }
.cap-load { font-size: 11px; color: #9CA3AF; }

.strength { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
.bars { display: flex; gap: 3px; flex: 1; }
.bar { height: 4px; flex: 1; background: #E5E7EB; border-radius: 2px; }
.bar.weak.on { background: #EF4444; }
.bar.ok.on { background: #F59E0B; }
.bar.good.on { background: #84CC16; }
.bar.strong.on { background: #22C55E; }
.strength small { font-size: 11px; min-width: 24px; }
.strength small.weak { color: #EF4444; }
.strength small.ok { color: #F59E0B; }
.strength small.good { color: #84CC16; }
.strength small.strong { color: #22C55E; }

.error { margin: 8px 0; padding: 8px 12px; font-size: 12px; color: #DC2626; background: #FEF2F2; border: 1px solid #FEE2E2; border-radius: 10px; }

.submit {
  width: 100%; height: 42px; margin-top: 6px; border: none; border-radius: 10px;
  background: linear-gradient(180deg, #1F2937 0%, #111827 100%);
  color: #fff; font-size: 13.5px; font-weight: 600; letter-spacing: .02em;
  cursor: pointer; transition: transform .1s, box-shadow .15s;
  box-shadow: 0 1px 0 rgba(255,255,255,.15) inset, 0 2px 4px rgba(17,24,39,.2);
  display: grid; place-items: center;
}
.submit:hover:not(:disabled) { box-shadow: 0 1px 0 rgba(255,255,255,.15) inset, 0 4px 12px rgba(17,24,39,.25); }
.submit:active:not(:disabled) { transform: translateY(1px); }
.submit:disabled { opacity: .5; cursor: not-allowed; }
.loading-sp { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.switch { margin: 16px 0 0; text-align: center; font-size: 12.5px; color: #6B7280; }
.switch a { color: #111827; text-decoration: none; font-weight: 500; margin-left: 2px; }
.switch a:hover { text-decoration: underline; }

@media (max-width: 720px) {
  .auth { flex-direction: column; }
  .brand-side { min-width: auto; padding: 36px 28px 28px; }
  .brand-side h1 { font-size: 28px; }
  .features { margin-top: 28px; }
  .bs-foot { display: none; }
  .form-side { padding: 24px; }
}
</style>

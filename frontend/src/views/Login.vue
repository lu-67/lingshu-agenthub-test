<template>
  <div class="auth">
    <!-- 左侧品牌区 -->
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
        <p class="tagline">一站式任务管理平台 · 统一入口 · 数据可视化 · 安全权限控制</p>
      </div>
    </div>

    <!-- 右侧表单 -->
    <div class="form-side">
      <form class="card" @submit.prevent="submit">
        <div class="hdr">
          <div class="hdr-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M12 2L4 6v6c0 5 3.5 9 8 10 4.5-1 8-5 8-10V6l-8-4z"/>
            </svg>
          </div>
          <h2>登录</h2>
          <p class="sub">请输入账号密码</p>
        </div>

        <div class="fields">
          <label class="field">
            <span>账号</span>
            <input ref="userInput" v-model="form.username" placeholder="请输入用户名" autocomplete="username" spellcheck="false" />
          </label>
          <label class="field">
            <span>密码</span>
            <div class="pass">
              <input v-model="form.password" :type="showPwd ? 'text' : 'password'" placeholder="请输入密码" autocomplete="current-password" />
              <button type="button" class="eyebtn" @click="showPwd = !showPwd" :title="showPwd ? '隐藏' : '显示'">
                <svg v-if="!showPwd" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </label>
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button class="submit" type="submit" :disabled="loading">
          <span v-if="!loading">登录</span>
          <span v-else class="loading-sp"></span>
        </button>

        <div class="demo">
          <span>演示账号</span>
          <div class="demo-chips">
            <button type="button" class="chip" @click="fill('tester', 'tester123')">tester</button>
            <button type="button" class="chip" @click="fill('admin', 'admin123')">admin</button>
          </div>
        </div>

        <p class="switch">还没有账号？<router-link to="/register">立即注册 →</router-link></p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../api'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const userInput = ref(null)
const showPwd = ref(false)
const form = reactive({ username: 'tester', password: 'tester123' })

function fill(username, password) { form.username = username; form.password = password; error.value = '' }

async function submit() {
  error.value = ''
  if (!form.username.trim() || !form.password) { error.value = '请输入账号和密码'; return }
  loading.value = true
  try {
    const r = await auth.login(form)
    localStorage.setItem('nx_token', r.token)
    localStorage.setItem('nx_user', r.username)
    localStorage.setItem('nx_role', r.role)
    if (r.id) localStorage.setItem('nx_uid', String(r.id))
    router.push('/new-task')
  } catch (e) { error.value = e?.detail || e?.message || '登录失败，请稍后重试' }
  finally { loading.value = false }
}

onMounted(() => userInput.value?.focus())
</script>

<style scoped>
.auth { min-height: 100vh; display: flex; background: #FAFBFC; }

/* 左侧 */
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
.bs-bg {
  position: absolute; inset: 0; pointer-events: none; opacity: .45;
  background:
    radial-gradient(circle at 20% 30%, rgba(34,197,94,.12) 0, transparent 40%),
    radial-gradient(circle at 80% 70%, rgba(99,102,241,.08) 0, transparent 50%),
    radial-gradient(circle at 60% 10%, rgba(255,255,255,.04) 0, transparent 30%);
}
.bs-inner { position: relative; max-width: 420px; z-index: 1; }
.brand-mark { margin-bottom: 32px; }
.brand-mark svg { opacity: .9; }
.brand-side h1 { margin: 0 0 16px; font-size: 38px; font-weight: 700; letter-spacing: -.02em; line-height: 1.1; }
.tagline { margin: 0; font-size: 15px; color: #94A3B8; line-height: 1.6; }
.features { margin-top: 52px; display: flex; flex-direction: column; gap: 14px; }
.feat { display: flex; align-items: flex-start; gap: 12px; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #22C55E; flex: none; margin-top: 8px; box-shadow: 0 0 0 3px rgba(34,197,94,.2); }
.feat b { display: block; font-size: 13px; font-weight: 600; color: #fff; letter-spacing: .01em; }
.feat small { font-size: 12px; color: #94A3B8; }
.bs-foot { margin-top: 48px; font-size: 11px; color: #64748B; letter-spacing: .05em; text-transform: uppercase; }

/* 右侧 */
.form-side { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px; min-width: 400px; }

.card {
  width: 100%; max-width: 384px;
  background: #fff; border-radius: 16px; padding: 36px 32px;
  box-shadow:
    0 1px 2px rgba(17,24,39,.04),
    0 8px 24px rgba(17,24,39,.06),
    0 24px 48px rgba(17,24,39,.04);
  border: 1px solid rgba(229,231,235,.8);
}
.hdr { text-align: center; margin-bottom: 28px; }
.hdr-icon {
  width: 44px; height: 44px; margin: 0 auto 16px;
  background: linear-gradient(135deg, #111827 0%, #374151 100%);
  border-radius: 12px; display: grid; place-items: center; color: #fff;
}
.hdr h2 { margin: 0 0 6px; font-size: 24px; font-weight: 700; color: #111827; letter-spacing: -.01em; }
.sub { margin: 0; font-size: 12.5px; color: #9CA3AF; }

.fields { display: flex; flex-direction: column; gap: 14px; margin-bottom: 4px; }
.field > span { display: block; margin-bottom: 6px; font-size: 12px; font-weight: 500; color: #374151; letter-spacing: .01em; }
.field input {
  width: 100%; height: 42px; padding: 0 14px; font-size: 14px; color: #111827;
  background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; outline: none;
  transition: border-color .15s, box-shadow .15s; box-sizing: border-box;
}
.field input:focus { border-color: #111827; box-shadow: 0 0 0 4px rgba(17,24,39,.05); }
.field input::placeholder { color: #D1D5DB; }

.pass { position: relative; }
.pass input { padding-right: 40px; }
.eyebtn {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  width: 28px; height: 28px; border: none; background: transparent; cursor: pointer;
  color: #9CA3AF; border-radius: 6px; display: grid; place-items: center;
}
.eyebtn:hover { background: #F3F4F6; color: #374151; }

.error {
  margin: 8px 0; padding: 8px 12px; font-size: 12px;
  color: #DC2626; background: #FEF2F2; border: 1px solid #FEE2E2; border-radius: 10px;
}

.submit {
  width: 100%; height: 44px; margin-top: 6px; border: none; border-radius: 10px;
  background: linear-gradient(180deg, #1F2937 0%, #111827 100%);
  color: #fff; font-size: 14px; font-weight: 600; letter-spacing: .02em;
  cursor: pointer; transition: transform .1s, box-shadow .15s;
  box-shadow: 0 1px 0 rgba(255,255,255,.15) inset, 0 2px 4px rgba(17,24,39,.2);
  display: grid; place-items: center;
}
.submit:hover:not(:disabled) { box-shadow: 0 1px 0 rgba(255,255,255,.15) inset, 0 4px 12px rgba(17,24,39,.25); }
.submit:active:not(:disabled) { transform: translateY(1px); }
.submit:disabled { opacity: .6; cursor: not-allowed; }
.loading-sp {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.demo { margin-top: 20px; padding-top: 18px; border-top: 1px solid #F3F4F6; display: flex; flex-direction: column; gap: 8px; align-items: center; }
.demo > span { font-size: 11px; color: #9CA3AF; letter-spacing: .02em; }
.demo-chips { display: flex; gap: 8px; }
.chip {
  border: 1px solid #E5E7EB; background: #fff; border-radius: 999px;
  padding: 6px 14px; font-size: 12px; color: #374151;
  cursor: pointer; transition: all .15s; font-family: var(--mono);
}
.chip:hover { border-color: #111827; color: #111827; background: #F9FAFB; }

.switch { margin: 18px 0 0; text-align: center; font-size: 12.5px; color: #6B7280; }
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

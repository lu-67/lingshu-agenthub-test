<template>
  <div class="shell">
    <!-- ============ 左侧竖栏 ============ -->
    <aside class="side" :style="{ width: sideW + 'px' }">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">
          <span class="bm-a"></span>
          <span class="bm-b"></span>
          <span class="bm-c"></span>
        </div>
        <div class="brand-text">
          <b>灵枢</b><span>AgentHub</span>
        </div>
      </div>

      <nav class="nav">
        <router-link to="/new-task" class="nav-item" :class="{ on: $route.path === '/new-task' }">
          <Icon name="spark" :size="16" /> 新任务
        </router-link>
        <router-link to="/experts" class="nav-item"
                     :class="{ on: $route.path.startsWith('/experts') || $route.path.startsWith('/chat') }">
          <Icon name="bot" :size="16" /> 智能体
        </router-link>
        <router-link to="/automations" class="nav-item" :class="{ on: $route.path === '/automations' }">
          <Icon name="timer" :size="16" /> 定时任务
        </router-link>
      </nav>

      <div class="side-section">
        <div class="sec-hd">
          <span>全部任务</span>
          <small>{{ sessions.length }}</small>
        </div>
        <div class="sess-wrap">
          <router-link v-for="s in sessions" :key="s.id" :to="`/chat/${s.id}`"
                       class="sess-item" :class="{on: $route.params.sid == s.id}">
            <span class="sa">{{ s.agentAvatar }}</span>
            <div class="sess-meta">
              <b>{{ trunc(s.title, 18) }}</b>
              <small>{{ trunc(stripMd(s.lastMessage), 28) || '（新任务）' }}</small>
            </div>
          </router-link>
          <div v-if="!sessions.length" class="empty">暂无任务，去「智能体」开始吧</div>
        </div>
      </div>

      <div class="side-foot">
        <div class="me" @click="meOpen = !meOpen">
          <div class="mavatar">{{ (username[0] || 'L').toUpperCase() }}</div>
          <div class="mmeta">
            <b>{{ username }}</b>
            <small>{{ role === 'ADMIN' ? '管理员' : '测试工程师' }}</small>
          </div>
          <Icon :name="meOpen ? 'chevron-up' : 'chevron-down'" :size="13" />
          <div v-if="meOpen" class="me-menu" @click.stop>
            <div class="mm-item" @click="meOpen = false; router.push('/profile')">
              <Icon name="user" :size="13" /> 个人设置
            </div>
            <div v-if="role === 'ADMIN'" class="mm-item" @click="meOpen = false; router.push('/admin')">
              <Icon name="shield" :size="13" /> 管理后台
            </div>
            <div class="mm-item" @click="meOpen = false; $refs.docsLink?.click()">
              <Icon name="terminal" :size="13" /> 接口文档
            </div>
            <div class="mm-divider"></div>
            <div class="mm-item danger" @click="meOpen = false; logout()">
              <Icon name="logout" :size="13" /> 退出登录
            </div>
          </div>
        </div>
        <a ref="docsLink" class="foot-link" :href="'http://localhost:8000/docs'" target="_blank" title="接口文档">
          <Icon name="terminal" :size="14" />
        </a>
        <button class="foot-link" @click="logout" title="退出登录">
          <Icon name="logout" :size="14" />
        </button>
      </div>
    </aside>

    <!-- 侧边栏拖拽条 -->
    <div class="side-resize" @mousedown="startResize"
         :class="{ resizing: isResizing }"
         @dblclick="sideW = 200; localStorage.setItem('nx_side_w', '200')"></div>

    <!-- ============ 右侧 ============ -->
    <div class="body">
      <header class="topbar">
        <div class="crumbs">
          <b>{{ pageTitle }}</b>
          <span v-if="!pageTitleHidden" class="sub">{{ pageSub }}</span>
        </div>
      </header>
      <main class="main"><router-view /></main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { sessions as sessApi } from '../api'

const route = useRoute()
const router = useRouter()
const sessions = ref([])
const meOpen = ref(false)
const docsLink = ref(null)
const username = ref(localStorage.getItem('nx_user') || '灵枢用户')
const role = ref(localStorage.getItem('nx_role') || 'USER')

// 侧边栏可拖拽
const sideW = ref(parseInt(localStorage.getItem('nx_side_w')) || 200)
const isResizing = ref(false)
function startResize(e) {
  isResizing.value = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}
function onResize(e) {
  const w = Math.min(360, Math.max(120, e.clientX))
  sideW.value = w
}
function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  localStorage.setItem('nx_side_w', String(sideW.value))
}

const pageTitle = computed(() => {
  if (route.path.startsWith('/chat')) {
    const a = sessions.value.find(s => s.id == route.params.sid)
    return a ? `${a.agentName} · ${trunc(a.title, 14)}` : '任务'
  }
  return route.meta?.title || '灵枢 AgentHub'
})
const pageTitleHidden = computed(() => route.path.startsWith('/chat'))
const pageSub = computed(() => {
  if (route.path === '/experts') return '选择一个智能体，开始任务'
  if (route.path === '/automations') return '设定定时任务让智能体自动执行'
  return ''
})

function trunc(s, n) { return s ? (s.length > n ? s.slice(0, n) + '…' : s) : '' }
function stripMd(s) {
  if (!s) return ''
  return s
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/#{1,6}\s+/g, '')
    .replace(/\[(.+?)\]\(.+?\)/g, '$1')
    .replace(/^[-*+]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    .replace(/^>\s+/gm, '')
    .replace(/^-{3,}$/gm, '')
    .replace(/^```[\s\S]*?```$/gm, '')
    .replace(/\n+/g, ' ')
    .trim()
}
async function reload() {
  try { sessions.value = (await sessApi.list(null, 100)).sessions || [] } catch {}
}
function logout() { localStorage.clear(); router.push('/login') }

onMounted(reload)
</script>

<style scoped>
.shell { display: flex; height: 100vh; overflow: hidden; background: #F7F8FA; }

/* ======== 左侧 ======== */
.side {
  flex: none; background: #FFFFFF; border-right: 1px solid #E5E7EB;
  display: flex; flex-direction: column; padding: 14px 0 14px; gap: 8px; overflow: hidden;
  transition: width .08s linear;
}
.side-resize {
  flex: none; width: 4px; margin-left: -2px; margin-right: -2px;
  cursor: col-resize; position: relative; z-index: 10;
  background: transparent; transition: background .15s;
}
.side-resize:hover, .side-resize.resizing { background: #111827; width: 3px; margin-left: -1px; margin-right: -1px; }

.brand { padding: 2px 14px 12px; display: flex; align-items: center; gap: 10px; }
/* 纯几何线 logo — 三层错方 */
.brand-mark {
  position: relative; width: 28px; height: 24px; flex: none;
}
.brand-mark span {
  position: absolute; box-sizing: border-box;
  border: 1.5px solid #111827; border-radius: 3px;
  background: transparent;
}
.brand-mark .bm-a { top: 0; left: 0;   width: 16px; height: 16px; }
.brand-mark .bm-b { top: 6px; left: 6px;  width: 16px; height: 16px; }
.brand-mark .bm-c { top: 12px; left: 12px; width: 16px; height: 16px; }
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.brand-text b { font-size: 15px; color: #111827; font-weight: 800; letter-spacing: .02em; }
.brand-text span { font-size: 10px; color: #9CA3AF; letter-spacing: .16em; }

.nav { padding: 0 8px; display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 10px; height: 34px; padding: 0 12px;
  border-radius: 8px; font-size: 13px; color: #374151; text-decoration: none;
  transition: all .12s; cursor: pointer;
}
.nav-item:hover { background: #F3F4F6; color: #111827; }
.nav-item.on { background: #111827; color: #FFFFFF; font-weight: 600; }

.side-section { flex: 1; display: flex; flex-direction: column; padding: 6px 8px 0; overflow: hidden; }
.sec-hd {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 10px 6px; font-size: 11px; font-weight: 600;
  color: #9CA3AF; letter-spacing: .06em; text-transform: uppercase;
}
.sec-hd small {
  background: #F3F4F6; color: #6B7280; font-size: 10px; font-weight: 600;
  padding: 1px 7px; border-radius: 999px; letter-spacing: 0; text-transform: none;
}

.sess-wrap { flex: 1; overflow-y: auto; padding: 0 4px; }
.sess-wrap .empty { padding: 20px 8px; text-align: center; color: #9CA3AF; font-size: 11.5px; line-height: 1.6; }
.sess-item {
  display: flex; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none;
  color: inherit; margin-bottom: 2px; transition: background .1s;
}
.sess-item:hover { background: #F3F4F6; }
.sess-item.on { background: #EFF6FF; }
.sa { width: 28px; height: 28px; border-radius: 7px; background: #F3F4F6;
       display: grid; place-items: center; font-size: 14px; flex: none; }
.sess-meta { flex: 1; min-width: 0; }
.sess-meta b { font-size: 12.5px; color: #111827; font-weight: 600;
               overflow: hidden; text-overflow: ellipsis; display: block; white-space: nowrap; }
.sess-meta small { font-size: 11px; color: #6B7280; display: block; white-space: nowrap;
                   overflow: hidden; text-overflow: ellipsis; margin-top: 1px; }

.side-foot {
  padding: 8px 10px 6px; border-top: 1px solid #E5E7EB;
  display: flex; align-items: center; gap: 6px;
}
.me { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; cursor: pointer; position: relative; padding: 4px 6px; margin: -4px -6px; border-radius: 8px; transition: background .1s; }
.me:hover { background: #F3F4F6; }
.mavatar {
  width: 28px; height: 28px; border-radius: 8px;
  background: #111827;
  color: #fff; display: grid; place-items: center; font-size: 12px; font-weight: 700; flex: none;
}
.mmeta { flex: 1; min-width: 0; display: flex; flex-direction: column; line-height: 1.2; }
.mmeta b { font-size: 12px; color: #111827; }
.mmeta small { font-size: 10.5px; color: #6B7280; }

/* 头像 dropdown 菜单 */
.me-menu {
  position: absolute; left: 0; bottom: calc(100% + 6px); z-index: 50;
  min-width: 160px; background: #fff; border: 1px solid #E5E7EB; border-radius: 10px;
  box-shadow: 0 10px 30px rgba(17,24,39,.1); padding: 4px;
}
.mm-item {
  display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 6px;
  font-size: 12.5px; color: #374151; cursor: pointer;
}
.mm-item:hover { background: #F3F4F6; color: #111827; }
.mm-item.danger { color: #DC2626; }
.mm-item.danger:hover { background: #FEF2F2; color: #DC2626; }
.mm-divider { height: 1px; background: #E5E7EB; margin: 4px 6px; }
.foot-link {
  width: 26px; height: 26px; border-radius: 7px; border: none; background: transparent;
  color: #6B7280; cursor: pointer; display: grid; place-items: center; text-decoration: none;
}
.foot-link:hover { background: #F3F4F6; color: #111827; }

/* ======== 右侧 ======== */
.body { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.topbar {
  height: 48px; flex: none; display: flex; align-items: center;
  padding: 0 24px; background: #FFFFFF; border-bottom: 1px solid #E5E7EB;
}
.crumbs { display: flex; align-items: baseline; gap: 10px; }
.crumbs b { font-size: 15px; color: #111827; font-weight: 600; }
.crumbs .sub { font-size: 12px; color: #9CA3AF; }
.main { flex: 1; overflow-y: auto; background: #F7F8FA; }
</style>

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/register', component: () => import('../views/Register.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/new-task',
    children: [
      { path: 'new-task', component: () => import('../views/NewTask.vue'),
        meta: { title: '新任务' } },
      { path: 'experts', component: () => import('../views/ExpertMarket.vue'),
        meta: { title: '智能体市场' } },
      { path: 'chat/:sid', component: () => import('../views/Chat.vue'),
        meta: { title: '任务' } },
      { path: 'automations', component: () => import('../views/Automations.vue'),
        meta: { title: '定时任务' } },
      { path: 'profile', component: () => import('../views/Profile.vue'),
        meta: { title: '个人设置' } },
      { path: 'admin', component: () => import('../views/Admin.vue'),
        meta: { title: '管理后台', adminOnly: true } },
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/new-task' }
]

const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach((to) => {
  if (!to.meta.public && !localStorage.getItem('nx_token')) return '/login'
})
export default router

import axios from 'axios'
import router from '../router'

const http = axios.create({ baseURL: '/api', timeout: 120000 })

http.interceptors.request.use(cfg => {
  const token = localStorage.getItem('nx_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

http.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('nx_token')
      router.push('/login')
    }
    return Promise.reject(err.response?.data || err)
  }
)

// ---------------- 认证 ----------------
export const auth = {
  login: d => http.post('/auth/login', d),
  register: d => http.post('/auth/register', d),
  me: () => http.get('/auth/me')
}

// ---------------- 智能体 ----------------
export const agents = {
  list: () => http.get('/agents'),
  create: d => http.post('/agents', d),
  update: (id, d) => http.put(`/agents/${id}`, d)
}

// ---------------- 会话 ----------------
export const sessions = {
  list: (agentId, limit = 50) => http.get('/sessions', { params: { agentId, limit } }),
  create: d => http.post('/sessions', d),
  get: id => http.get(`/sessions/${id}`),
  send: (id, d) => http.post(`/sessions/${id}/send`, d),
  approve: (id, note = '') => http.post(`/sessions/${id}/approve`, { note })
}

// ---------------- 定时任务 ----------------
export const automations = {
  list: () => http.get('/automations'),
  create: d => http.post('/automations', d),
  update: (id, d) => http.put(`/automations/${id}`, d),
  remove: id => http.delete(`/automations/${id}`)
}

// ---------------- 交付物 ----------------
export const artifacts = {
  download: id => http.get(`/artifacts/${id}/download`, { responseType: 'blob' })
}

// ---------------- 管理端 ----------------
export const admin = {
  users: () => http.get('/admin/users'),
  stats: () => http.get('/admin/stats')
}

export default http

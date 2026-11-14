import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端地址可通过环境变量覆盖（默认 8000，验证多实例时用 VITE_API_TARGET 指向别的端口）
const target = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'
const proxy = { '/api': { target, changeOrigin: true } }

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy }
})

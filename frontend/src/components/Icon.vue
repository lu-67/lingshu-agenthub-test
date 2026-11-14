<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       :stroke-width="stroke" stroke-linecap="round" stroke-linejoin="round" class="ic">
    <path v-for="(p, i) in paths" :key="i" :d="p" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, default: 'spark' },
  size: { type: [Number, String], default: 16 },
  stroke: { type: [Number, String], default: 1.7 }
})

// 手写 SVG 路径（Lucide 风格 24×24 线性图标），零图标库依赖、深浅色自动继承 currentColor
const MAP = {
  dashboard: ['M3 3h7v7H3z', 'M14 3h7v7h-7z', 'M14 14h7v7h-7z', 'M3 14h7v7H3z'],
  bot: ['M12 2v3', 'M5 8h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z', 'M9 13h.01', 'M15 13h.01', 'M9 17h6'],
  workflow: ['M6 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6z', 'M18 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z', 'M6 9v3a3 3 0 0 0 3 3h6'],
  plug: ['M9 2v6', 'M15 2v6', 'M6 8h12v4a6 6 0 0 1-12 0z', 'M12 18v4'],
  book: ['M3 5a2 2 0 0 1 2-2h6v18H5a2 2 0 0 1-2-2z', 'M13 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6'],
  flask: ['M9 3h6', 'M10 3v6L4.2 19.2A1 1 0 0 0 5.1 21h13.8a1 1 0 0 0 .9-1.8L14 9V3', 'M8 15h8'],
  activity: ['M3 12h4l3-8 4 16 3-8h4'],
  send: ['M22 2L11 13', 'M22 2l-7 20-4-9-9-4z'],
  history: ['M3 3v6h6', 'M3.5 9a9 9 0 1 0 2.1-3.4L3 9', 'M12 8v5l3 2'],
  shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'M9 12l2 2 4-4'],
  sun: ['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M12 2v2', 'M12 20v2', 'M4.9 4.9l1.4 1.4', 'M17.7 17.7l1.4 1.4', 'M2 12h2', 'M20 12h2', 'M4.9 19.1l1.4-1.4', 'M17.7 6.3l1.4-1.4'],
  moon: ['M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'],
  plus: ['M12 5v14', 'M5 12h14'],
  play: ['M6 3l14 9-14 9z'],
  search: ['M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'M21 21l-4.3-4.3'],
  settings: ['M4 21v-7', 'M4 10V3', 'M12 21v-9', 'M12 8V3', 'M20 21v-5', 'M20 12V3', 'M1 14h6', 'M9 8h6', 'M17 16h6'],
  key: ['M15 7a4 4 0 1 1-3.5 5.9L4 20.4V17h2v-2h2v-2l1.6-1.6A4 4 0 0 1 15 7z'],
  chart: ['M3 3v18h18', 'M7 15l3-4 3 3 5-7'],
  trash: ['M3 6h18', 'M8 6V4h8v2', 'M6 6l1 15h10l1-15', 'M10 11v6', 'M14 11v6'],
  edit: ['M11 4H4v16h16v-7', 'M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4z'],
  chevron: ['M6 9l6 6 6-6'],
  right: ['M9 6l6 6-6 6'],
  left: ['M15 6l-6 6 6 6'],
  close: ['M18 6L6 18', 'M6 6l12 12'],
  check: ['M20 6L9 17l-5-5'],
  copy: ['M9 9h11v11H9z', 'M5 15H4V4h11v1'],
  refresh: ['M23 4v6h-6', 'M1 20v-6h6', 'M3.5 9a9 9 0 0 1 14.8-3.4L23 10', 'M1 14l4.7 4.4A9 9 0 0 0 20.5 15'],
  spark: ['M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z', 'M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z'],
  database: ['M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3z', 'M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6', 'M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3'],
  layers: ['M12 2l9 5-9 5-9-5z', 'M3 12l9 5 9-5', 'M3 17l9 5 9-5'],
  terminal: ['M4 17l6-6-6-6', 'M12 19h8'],
  external: ['M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6', 'M15 3h6v6', 'M10 14L21 3'],
  user: ['M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M4 21v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2'],
  logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
  menu: ['M3 6h18', 'M3 12h18', 'M3 18h18'],
  info: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 11v5', 'M12 8h.01'],
  clock: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z', 'M12 7v5l3 2'],
  bolt: ['M13 2L3 14h7l-1 8 10-12h-7z'],
  filter: ['M3 4h18l-7 8v6l-4 2v-8z'],
  branch: ['M6 3v12', 'M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M18 9v3a3 3 0 0 1-3 3H9'],
  rocket: ['M5 13l-2 6 6-2', 'M14.5 4.5c3.5-2 6-2 6-2s0 2.5-2 6l-6 6-4-1-1-4z', 'M9 15l-3-3'],
  wand: ['M15 4V2', 'M15 10V8', 'M11.5 4.5l-1.4-1.4', 'M19.9 12.9l-1.4-1.4', 'M20 6h2', 'M2 20l9-9', 'M18 16h2'],
  card: ['M3 6h18v12H3z', 'M3 10h18'],
  brain: ['M9 4a3 3 0 0 0-3 3 3 3 0 0 0-1 5.8V15a3 3 0 0 0 4 2.8V20', 'M15 4a3 3 0 0 1 3 3 3 3 0 0 1 1 5.8V15a3 3 0 0 1-4 2.8V20', 'M12 4v16']
}
const paths = computed(() => MAP[props.name] || MAP.spark)
</script>

<style scoped>
.ic { display: block; flex: none; }
</style>

<template>
  <div class="chart" @mouseleave="hover = -1">
    <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" class="svg">
      <defs>
        <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#6366F1" stop-opacity=".34" />
          <stop offset="100%" stop-color="#6366F1" stop-opacity="0" />
        </linearGradient>
      </defs>
      <line v-for="g in 4" :key="g" :x1="0" :x2="W" :y1="(H / 4) * g" :y2="(H / 4) * g"
            stroke="currentColor" stroke-opacity=".08" stroke-dasharray="3 5" />
      <path v-if="area" :d="area" :fill="`url(#${gid})`" />
      <path :d="line" fill="none" stroke="#6366F1" stroke-width="2" stroke-linejoin="round" />
      <circle v-for="(p, i) in pts" :key="i" :cx="p.x" :cy="p.y" r="3.4"
              :fill="hover === i ? '#6366F1' : 'var(--surface)'" stroke="#6366F1" stroke-width="2" />
      <line v-if="hover >= 0" :x1="pts[hover]?.x" :x2="pts[hover]?.x" y1="0" :y2="H"
            stroke="#6366F1" stroke-opacity=".3" stroke-dasharray="3 4" />
    </svg>
    <div class="xaxis">
      <span v-for="(d, i) in data" :key="d.day" :class="{ on: hover === i }">{{ shortDay(d.day) }}</span>
    </div>
    <div v-for="(p, i) in pts" :key="'hit' + i" class="hit"
         :style="{ left: p.xpct + '%' }" @mouseenter="hover = i">
      <div v-if="hover === i" class="tip" :style="{ left: i < data.length / 2 ? '10px' : 'auto', right: i < data.length / 2 ? 'auto' : '10px' }">
        <b>{{ data[i].day }}</b>
        <div>运行 <em>{{ data[i].runs }}</em> 次 · 失败 <em>{{ data[i].errors }}</em></div>
        <div class="muted">平均 {{ data[i].avgMs || 0 }} ms</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 150 }
})
const W = 600
const H = computed(() => props.height)
const hover = ref(-1)
const gid = `g${Math.random().toString(36).slice(2, 8)}`

const max = computed(() => Math.max(1, ...props.data.map(d => d.runs)))
const pts = computed(() => {
  const n = props.data.length
  const pad = 8
  const innerW = W - pad * 2
  const innerH = H.value - pad * 2
  return props.data.map((d, i) => {
    const x = n <= 1 ? W / 2 : pad + (innerW * i) / (n - 1)
    const y = pad + innerH - (innerH * d.runs) / max.value
    return { x, y, xpct: (x / W) * 100 }
  })
})
const line = computed(() => pts.value.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' '))
const area = computed(() => {
  if (!pts.value.length) return ''
  const first = pts.value[0]
  const last = pts.value[pts.value.length - 1]
  return `${line.value} L${last.x},${H.value - 8} L${first.x},${H.value - 8} Z`
})
function shortDay(d) { return (d || '').slice(5) }
</script>

<style scoped>
.chart { position: relative; color: var(--text); }
.svg { width: 100%; height: v-bind('height + "px"'); display: block; overflow: visible; }
.xaxis { display: flex; justify-content: space-between; margin-top: 6px; font-size: 10.5px; color: var(--muted); }
.xaxis .on { color: var(--primary); font-weight: 600; }
.hit { position: absolute; top: 0; bottom: 18px; width: 14.28%; transform: translateX(-50%); }
.tip {
  position: absolute; top: 4px; background: var(--surface); border: 1px solid var(--border);
  box-shadow: var(--shadow); border-radius: 9px; padding: 7px 10px; font-size: 11px; color: var(--text-2);
  min-width: 130px; z-index: 5; pointer-events: none;
}
.tip b { color: var(--text); font-size: 11.5px; }
.tip em { font-style: normal; color: var(--primary); font-weight: 600; }
</style>

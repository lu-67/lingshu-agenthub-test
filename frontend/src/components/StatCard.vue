<template>
  <div class="stat card" :class="`tone-${tone}`">
    <div class="top">
      <span class="label">{{ label }}</span>
      <span class="ic"><Icon :name="icon" :size="15" /></span>
    </div>
    <div class="value">
      {{ display }}<em v-if="unit">{{ unit }}</em>
    </div>
    <div class="foot">
      <span v-if="hint" class="hint">{{ hint }}</span>
      <span v-if="delta !== null && delta !== undefined" class="delta" :class="delta >= 0 ? 'up' : 'down'">
        {{ delta >= 0 ? '+' : '' }}{{ delta }}%
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  label: String,
  value: [Number, String],
  unit: String,
  hint: String,
  icon: { type: String, default: 'chart' },
  tone: { type: String, default: 'primary' },
  delta: { type: Number, default: null }
})

const display = computed(() => {
  if (typeof props.value === 'number') return props.value.toLocaleString('zh-CN')
  return props.value ?? '—'
})
</script>

<style scoped>
.stat { padding: 15px 17px; position: relative; overflow: hidden; }
.stat::after {
  content: ""; position: absolute; right: -26px; top: -26px; width: 74px; height: 74px;
  border-radius: 50%; opacity: .12; background: currentColor;
}
.top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.label { font-size: 12px; color: var(--muted); }
.ic { width: 24px; height: 24px; border-radius: 7px; display: grid; place-items: center; background: var(--surface-2); }
.value { font-size: 25px; font-weight: 700; letter-spacing: -.03em; line-height: 1.1; color: var(--text); }
.value em { font-size: 12px; font-weight: 500; color: var(--muted); font-style: normal; margin-left: 3px; }
.foot { display: flex; align-items: center; gap: 8px; margin-top: 6px; min-height: 16px; }
.hint { font-size: 11px; color: var(--muted); }
.delta { font-size: 11px; padding: 0 6px; border-radius: 6px; }
.delta.up { color: #0EA97A; background: rgba(14, 169, 122, .1); }
.delta.down { color: #D93A3F; background: rgba(229, 72, 77, .1); }
.tone-primary { color: var(--primary); }
.tone-success { color: #0EA97A; }
.tone-warn { color: #B87700; }
.tone-info { color: #0E9BD4; }
.tone-danger { color: #D93A3F; }
</style>

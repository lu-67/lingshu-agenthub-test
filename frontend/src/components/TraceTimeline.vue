<template>
  <div class="trace">
    <div v-for="(s, i) in rows" :key="i" class="step" :class="{ open: expanded[i] }">
      <div class="rail">
        <span class="node" :style="{ background: color(s.type), boxShadow: `0 0 0 3px ${color(s.type)}22` }">
          {{ i + 1 }}
        </span>
        <i v-if="i < rows.length - 1" class="line"></i>
      </div>
      <div class="body">
        <div class="head" @click="toggle(i)">
          <span class="name">{{ s.name }}</span>
          <span class="type" :style="{ color: color(s.type), borderColor: color(s.type) + '44', background: color(s.type) + '14' }">
            {{ typeLabel(s.type) }}
          </span>
          <span v-if="s.branch" class="chip">分支 {{ s.branch }}</span>
          <span v-if="s.ms !== undefined && s.ms !== null" class="ms">{{ s.ms }} ms</span>
          <span v-if="s.status === 'failed'" class="chip bad">失败</span>
          <Icon :name="expanded[i] ? 'chevron' : 'right'" :size="13" class="chev" />
        </div>
        <div v-if="s.thought" class="thought">{{ s.thought }}</div>
        <div v-if="expanded[i]" class="detail">
          <div v-if="s.input && s.input !== '-'" class="block">
            <label>输入</label><pre>{{ s.input }}</pre>
          </div>
          <div v-if="s.output && s.output !== '-'" class="block">
            <label>输出</label><pre>{{ s.output }}</pre>
          </div>
        </div>
      </div>
    </div>
    <div v-if="!rows.length" class="empty"><div class="big">◎</div>还没有执行轨迹</div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  steps: { type: Array, default: () => [] },
  autoOpenFirst: { type: Boolean, default: false }
})

const COLORS = {
  start: '#0EA97A', knowledge: '#0E9BD4', tool: '#E08A00', llm: '#4F46E5',
  condition: '#DB2777', answer: '#7C3AED', final: '#7C3AED', default: '#7C87A0'
}
const LABELS = {
  start: '开始', knowledge: '知识检索', tool: '工具', llm: '大模型',
  condition: '条件', answer: '回答', final: '最终回答', agent: 'Agent'
}

const rows = computed(() => (props.steps || []).map((s, i) => {
  const action = s.action || ''
  let type = s.type
  if (!type) {
    if (action === 'final-answer') type = 'answer'
    else if (['calculator', 'weather', 'get_time', 'time', 'web_search', 'knowledge'].includes(action)) type = 'tool'
    else type = 'tool'
  }
  return {
    name: s.title || (action === 'final-answer' ? '最终回答' : action) || `步骤 ${i + 1}`,
    type, thought: s.thought || '', input: s.input,
    output: s.output || s.observation, status: s.status || 'success',
    ms: s.elapsedMs, branch: s.branch
  }
}))

const expanded = reactive({})
if (props.autoOpenFirst) expanded[0] = true

function toggle(i) { expanded[i] = !expanded[i] }
function color(t) { return COLORS[t] || COLORS.default }
function typeLabel(t) { return LABELS[t] || t || '步骤' }
</script>

<style scoped>
.trace { display: flex; flex-direction: column; }
.step { display: flex; gap: 11px; }
.rail { display: flex; flex-direction: column; align-items: center; }
.node {
  width: 22px; height: 22px; border-radius: 50%; color: #fff; font-size: 10.5px; font-weight: 600;
  display: grid; place-items: center; flex: none; margin-top: 3px;
}
.line { flex: 1; width: 1.5px; background: var(--border); margin: 4px 0; min-height: 14px; }
.body { flex: 1; padding-bottom: 12px; min-width: 0; }
.head { display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }
.name { font-size: 13px; font-weight: 580; color: var(--text); }
.type { font-size: 10px; padding: 0 6px; border-radius: 5px; border: 1px solid; line-height: 17px; }
.ms { font-size: 10.5px; color: var(--muted); font-family: var(--mono); }
.chev { margin-left: auto; color: var(--muted); }
.thought { font-size: 11.5px; color: var(--muted); margin-top: 2px; }
.detail { margin-top: 7px; display: flex; flex-direction: column; gap: 6px; }
.block label { font-size: 10px; color: var(--muted); letter-spacing: .04em; }
.block pre {
  margin: 2px 0 0; padding: 8px 10px; background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 8px; font-family: var(--mono); font-size: 11.5px; line-height: 1.6; color: var(--text-2);
  white-space: pre-wrap; word-break: break-word; max-height: 160px; overflow: auto;
}
</style>

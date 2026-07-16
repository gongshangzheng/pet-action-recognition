<template>
  <div class="task-node" :selectable="false">
    <div class="node-row-wrap" @mouseenter="onEnter" @mouseleave="onLeave">
      <div
        class="node-row"
        :class="{ selected: isSelected, clickable: isClickable, 'is-hidden': task.hidden || task.__hidden }"
        @click="onClick"
      >
        <!-- git 分支线 -->
        <div class="branch-lines" :style="{ width: depth * 20 + 20 + 'px' }">
          <div v-for="(show, i) in parentLines" :key="i" class="branch-cell">
            <div v-if="show" class="v-line" :style="{ background: color.line }"></div>
          </div>
          <div v-if="depth > 0" class="connector">
            <div class="conn-v" :style="{ background: color.line }"></div>
            <div class="conn-h" :style="{ background: color.line }"></div>
          </div>
        </div>

        <!-- 状态圆点 -->
        <div class="status-dot" :class="[statusCfg.dot, statusCfg.ring, { faded: task.status === 'completed' }]"></div>

        <!-- 内容 -->
        <div class="node-content">
          <span v-if="hasChildren" class="chevron" @click.stop="expanded = !expanded">
            <n-icon size="12">
              <chevron-down v-if="expanded" />
              <chevron-forward v-else />
            </n-icon>
          </span>
          <span v-else class="chevron-placeholder"></span>

          <span class="node-title" :class="{ done: task.status === 'completed', 'title-selected': isSelected }">
            <span class="task-id">{{ task.id }}</span>{{ task.title }}
          </span>

          <span v-if="task.priority" class="priority-tag" :class="'p-' + task.priority">
            {{ priorityLabel(task.priority) }}
          </span>

          <span v-if="hasChildren" class="progress-text">{{ count.completed }}/{{ count.total }}</span>

          <span v-if="task.assignee" class="assignee">
            <n-icon size="10"><person-outline /></n-icon>
            {{ task.assignee }}
          </span>

          <span v-if="task.startDate" class="date-text">{{ task.startDate.slice(5) }}</span>
        </div>
      </div>

      <!-- 悬浮提示 -->
      <div v-if="hovered && !isSelected" class="hover-card">
        <div class="hc-head">
          <div class="hc-title-row">
            <div class="status-dot sm" :class="[statusCfg.dot, statusCfg.ring]"></div>
            <strong>{{ task.title }}</strong>
          </div>
          <div class="hc-meta-row">
            <span class="hc-id">{{ task.id }}</span>
            <span class="hc-badge">{{ statusCfg.label }}</span>
            <span v-if="task.priority" class="hc-priority" :class="'p-' + task.priority">{{ priorityLabel(task.priority) }}</span>
          </div>
        </div>
        <div v-if="task.assignee" class="hc-line">执行人: {{ task.assignee }}</div>
        <div v-if="task.startDate" class="hc-line">
          {{ task.startDate }}{{ task.endDate ? ' → ' + task.endDate : '' }}
        </div>
        <div v-if="hasChildren" class="hc-progress">
          子任务: {{ count.completed }}/{{ count.total }} 已完成
        </div>
        <div v-if="recentProgress.length" class="hc-progress-section">
          <div class="hc-progress-title">进展记录</div>
          <div v-for="(p, i) in recentProgress" :key="i" class="hc-progress-entry"
               :class="{ 'is-done': p.note && p.note.startsWith('[完成]') }">
            <span class="hc-pdate">{{ p.date }}</span>
            <span class="hc-pnote">{{ p.note }}</span>
          </div>
        </div>
        <div v-if="task.description" class="hc-desc">{{ task.description }}</div>
      </div>
    </div>

    <!-- 子节点（递归） -->
    <div v-if="expanded && hasChildren">
      <project-task-node
        v-for="(child, i) in task.children"
        :key="child.id"
        :task="child"
        :depth="depth + 1"
        :is-last="i === task.children.length - 1"
        :parent-lines="[...parentLines, !isLast]"
        :color="color"
        :selected-id="selectedId"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { NIcon } from 'naive-ui'
import { ChevronDown, ChevronForward, PersonOutline } from '@vicons/ionicons5'

const props = defineProps({
  task: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  isLast: { type: Boolean, default: true },
  parentLines: { type: Array, default: () => [] },
  color: { type: Object, required: true },
  selectedId: { type: String, default: null },
})

const emit = defineEmits(['select'])

const TASK_STATUS = {
  active: { label: '进行中', dot: 'bg-green', ring: 'ring-green' },
  completed: { label: '已完成', dot: 'bg-blue', ring: 'ring-blue' },
  planned: { label: '规划中', dot: 'bg-gray', ring: 'ring-gray' },
  blocked: { label: '阻塞', dot: 'bg-red', ring: 'ring-red' },
  paused: { label: '已暂停', dot: 'bg-amber', ring: 'ring-amber' },
}

const PRIORITY_LABEL = { high: '高', medium: '中', low: '低' }
function priorityLabel(p) { return PRIORITY_LABEL[p] || p }

const expanded = ref(false)
const hovered = ref(false)
let hoverTimer = null

const hasChildren = computed(() => (props.task.children || []).length > 0)
const statusCfg = computed(() => TASK_STATUS[props.task.status] || TASK_STATUS.planned)
const isSelected = computed(() => props.selectedId === props.task.id)
const isClickable = computed(() => !!(props.task.notePath || props.task.description || (props.task.progress || []).length))

const count = computed(() => countTasks(props.task.children || []))
const recentProgress = computed(() => (props.task.progress || []).slice(0, 3))

function countTasks(tasks) {
  let total = 0
  let completed = 0
  for (const t of tasks) {
    total++
    if (t.status === 'completed') completed++
    if (t.children?.length) {
      const sub = countTasks(t.children)
      total += sub.total
      completed += sub.completed
    }
  }
  return { total, completed }
}

function onEnter() {
  hoverTimer = setTimeout(() => { hovered.value = true }, 400)
}
function onLeave() {
  if (hoverTimer) clearTimeout(hoverTimer)
  hovered.value = false
}
function onClick() {
  if (isClickable.value) emit('select', props.task)
}
</script>

<style scoped lang="scss">
.task-node { user-select: none; }
.node-row-wrap { position: relative; }

.node-row {
  display: flex;
  align-items: center;
  gap: 0;
  border-radius: 3px;
  transition: background 0.15s;
  padding: 2px 0;
  &.clickable { cursor: pointer; &:hover { background: var(--color-hover); } }
  &.clickable.selected { background: var(--color-selected); }
  &.is-hidden { opacity: 0.45; .node-title { font-style: italic; } }
}

.branch-lines {
  display: flex;
  flex-shrink: 0;
  align-items: stretch;
}
.branch-cell {
  position: relative;
  width: 20px;
  flex-shrink: 0;
  .v-line { position: absolute; left: 8px; top: 0; bottom: 0; width: 1px; }
}
.connector {
  position: relative;
  width: 20px;
  height: 28px;
  flex-shrink: 0;
  .conn-v { position: absolute; left: 8px; top: 0; height: 14px; width: 1px; }
  .conn-h { position: absolute; left: 8px; top: 14px; height: 1px; width: 10px; }
}

.status-dot {
  flex-shrink: 0;
  width: 10px; height: 10px;
  border-radius: 50%;
  margin: 0 6px;
  box-shadow: 0 0 0 2px rgba(0,0,0,0.15);
  &.sm { width: 8px; height: 8px; }
  &.faded { opacity: 0.6; }
}
.bg-green { background: #22c55e; } .ring-green { box-shadow: 0 0 0 2px rgba(34,197,94,0.3); }
.bg-blue { background: #3b82f6; } .ring-blue { box-shadow: 0 0 0 2px rgba(59,130,246,0.3); }
.bg-gray { background: #a1a1aa; } .ring-gray { box-shadow: 0 0 0 2px rgba(161,161,170,0.3); }
.bg-red { background: #ef4444; } .ring-red { box-shadow: 0 0 0 2px rgba(239,68,68,0.3); }
.bg-amber { background: #f59e0b; } .ring-amber { box-shadow: 0 0 0 2px rgba(245,158,11,0.3); }

.node-content {
  display: flex; align-items: center; gap: 6px;
  padding: 2px 4px; flex: 1; min-width: 0;
}
.chevron, .chevron-placeholder {
  flex-shrink: 0; width: 16px; height: 16px;
  display: inline-flex; align-items: center; justify-content: center;
}
.chevron { cursor: pointer; color: var(--color-text-dim); &:hover { color: var(--color-text); } }
.node-title {
  font-size: 13px; color: var(--color-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: inline-flex; align-items: center; gap: 4px;
  &.done { color: var(--color-text-dim); text-decoration: line-through; }
  &.title-selected { color: var(--color-text-heading); font-weight: 500; }
}
.task-id {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 10px; color: var(--color-text-dim);
  background: var(--color-elevated); border-radius: 3px;
  padding: 0 4px; line-height: 1.5;
  flex-shrink: 0;
}
.progress-text { flex-shrink: 0; font-size: 10px; color: var(--color-text-dim); }
.priority-tag {
  flex-shrink: 0; font-size: 9px; line-height: 1;
  padding: 1px 5px; border-radius: 3px; font-weight: 500;
  &.p-high { background: rgba(239,68,68,0.12); color: #dc2626; }
  &.p-medium { background: rgba(245,158,11,0.12); color: #d97706; }
  &.p-low { background: rgba(100,116,139,0.10); color: #64748b; }
}
.assignee {
  flex-shrink: 0; margin-left: auto;
  display: inline-flex; align-items: center; gap: 2px;
  background: var(--color-primary-soft); color: var(--color-primary);
  padding: 1px 6px; border-radius: 999px; font-size: 10px;
}
.date-text { flex-shrink: 0; font-size: 10px; color: var(--color-text-dim); }

.hover-card {
  position: absolute; left: 32px; top: 100%; z-index: 50;
  width: 240px; padding: 12px;
  background: var(--color-card); border: 1px solid var(--color-border);
  border-radius: 8px; box-shadow: 0 8px 24px var(--color-shadow);
      word-break: break-word; overflow-wrap: anywhere;
  .hc-head { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
  .hc-title-row { display: flex; align-items: center; gap: 6px; strong { font-size: 13px; color: var(--color-text-heading); } }
  .hc-meta-row { display: flex; align-items: center; gap: 6px; padding-left: 14px; }
  .hc-id { font-family: 'SF Mono', 'Menlo', monospace; font-size: 10px; color: var(--color-text-dim); background: var(--color-elevated); padding: 1px 5px; border-radius: 3px; }
  .hc-badge { font-size: 10px; min-width: 42px; text-align: center; background: var(--color-elevated); padding: 1px 6px; border-radius: 4px; color: var(--color-text-secondary); }
  .hc-priority {
    font-size: 9px; padding: 1px 5px; border-radius: 3px; font-weight: 500;
    &.p-high { background: rgba(239,68,68,0.12); color: #dc2626; }
    &.p-medium { background: rgba(245,158,11,0.12); color: #d97706; }
    &.p-low { background: rgba(100,116,139,0.10); color: #64748b; }
  }
  .hc-line { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }
  .hc-progress { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; }
  .hc-progress-section {
    margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--color-border);
    .hc-progress-title { font-size: 10px; color: var(--color-text-dim); margin-bottom: 3px; }
    .hc-progress-entry {
      font-size: 11px; line-height: 1.4; color: var(--color-text-secondary);
      display: flex; gap: 6px; margin-top: 2px;
      .hc-pdate { flex-shrink: 0; color: var(--color-text-dim); font-size: 10px; min-width: 70px; }
      .hc-pnote { white-space: pre-line; word-break: break-word; }
      &.is-done { color: #22c55e; .hc-pnote { font-weight: 500; } }
    }
  }
  .hc-desc { font-size: 12px; color: var(--color-text); margin-top: 6px; white-space: pre-line; line-height: 1.5; }
}
</style>

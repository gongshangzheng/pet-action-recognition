<template>
  <div class="projects-page" v-if="projects.length || loading">
    <!-- 标题 + 项目 Tab -->
    <header class="page-header">
      <div class="title-row">
        <n-icon size="20" color="#63b3ed"><git-branch-outline /></n-icon>
        <h2>项目树</h2>
      </div>
      <div class="project-tabs">
        <button
          v-for="(p, idx) in projects"
          :key="p.slug"
          class="tab"
          :class="{ active: activeSlug === p.slug }"
          :style="activeSlug === p.slug ? tabStyle(p, idx) : {}"
          @click="selectProject(p.slug)"
        >
          <span class="tab-dot" :style="{ background: activeSlug === p.slug ? projectColor(idx).dot : '#71717a' }"></span>
          <n-icon size="12" :style="{ color: projectColor(idx).text }">
            <component :is="statusIcon(p.status)" />
          </n-icon>
          {{ p.title }}
        </button>
      </div>
    </header>

    <div v-if="activeProject" class="content-grid">
      <!-- 左侧：任务树 -->
      <aside class="tree-sidebar">
        <div class="sidebar-head">
          <button class="back-btn" :class="{ active: !!selectedTask }" @click="backToReadme">
            <n-icon v-if="selectedTask" size="12"><arrow-back-outline /></n-icon>
            {{ activeProject.title }}
          </button>
          <div class="sidebar-meta">
            <span v-if="activeTree" class="meta-count">
              {{ treeCount.completed }}/{{ treeCount.total }}
            </span>
            <n-tooltip trigger="hover" placement="bottom-end">
              <template #trigger>
                <n-icon size="14" class="help-icon"><help-circle-outline /></n-icon>
              </template>
              <div class="legend">
                <div class="legend-title">任务状态说明</div>
                <div v-for="(cfg, key) in TASK_STATUS" :key="key" class="legend-item">
                  <span class="status-dot sm" :class="[cfg.dot, cfg.ring]"></span>
                  {{ cfg.label }}
                </div>
              </div>
            </n-tooltip>
          </div>
        </div>

        <div v-if="treeLoading" class="empty">加载中…</div>
        <div v-else-if="activeTree && activeTree.tasks.length" class="tree-list">
          <project-task-node
            v-for="(task, i) in activeTree.tasks"
            :key="task.id"
            :task="task"
            :depth="0"
            :is-last="i === activeTree.tasks.length - 1"
            :parent-lines="[]"
            :color="activeColor"
            :selected-id="selectedTask?.id"
            @select="selectTask"
          />
        </div>
        <div v-else class="empty">
          <n-icon size="32" color="#52525b"><git-branch-outline /></n-icon>
          <p>暂无任务树数据。</p>
        </div>
      </aside>

      <!-- 右侧：README 或 任务详情 -->
      <main class="detail-main">
        <div v-if="selectedTask" class="task-detail">
          <div class="detail-head">
            <span class="status-dot" :class="[taskStatus(selectedTask.status).dot, taskStatus(selectedTask.status).ring]"></span>
            <h3>{{ selectedTask.title }}</h3>
            <span class="detail-badge">{{ taskStatus(selectedTask.status).label }}</span>
            <span v-if="selectedTask.assignee" class="detail-assignee">
              <n-icon size="12"><person-outline /></n-icon>{{ selectedTask.assignee }}
            </span>
            <span v-if="selectedTask.startDate" class="detail-date">
              {{ selectedTask.startDate }}{{ selectedTask.endDate ? ' → ' + selectedTask.endDate : '' }}
            </span>
          </div>
          <div v-if="noteLoading" class="empty-inline">加载笔记中…</div>
          <markdown-renderer v-else-if="noteContent !== null" :content="noteContent" />
          <p v-else-if="selectedTask.description" class="desc-text">{{ selectedTask.description }}</p>
          <p v-else class="empty-inline">该任务暂无描述或笔记。</p>
        </div>

        <div v-else class="readme-view">
          <div class="readme-meta">
            <span class="status-dot lg" :style="{ background: activeColor.dot }"></span>
            <h3>{{ activeProject.title }}</h3>
            <span class="readme-status" :style="{ color: activeColor.text }">
              <n-icon size="14"><component :is="statusIcon(activeProject.status)" /></n-icon>
              {{ taskStatusLabel(activeProject.status) }}
            </span>
            <span v-if="activeProject.startDate" class="readme-date">
              {{ activeProject.startDate.slice(0, 10) }}{{ activeProject.endDate ? ' → ' + activeProject.endDate.slice(0, 10) : ' → 至今' }}
            </span>
            <span v-for="tag in (activeProject.tags || [])" :key="tag" class="readme-tag">{{ tag }}</span>
          </div>

          <div v-if="(activeProject.participants || []).length" class="participants">
            <n-icon size="14" color="#a1a1aa"><people-outline /></n-icon>
            <span v-for="(p, i) in activeProject.participants" :key="i" class="participant">
              <strong>{{ p.name }}</strong>
              <em>{{ p.role }}</em>
            </span>
          </div>

          <markdown-renderer :content="activeProject.body || '暂无 README 内容。'" />
        </div>
      </main>
    </div>

    <div v-else-if="!loading" class="empty-page">
      <n-icon size="40" color="#52525b"><git-branch-outline /></n-icon>
      <p>还没有项目。</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon, NTooltip } from 'naive-ui'
import {
  GitBranchOutline, ArrowBackOutline, HelpCircleOutline,
  PersonOutline, PeopleOutline, CheckmarkCircleOutline,
  PauseOutline, EllipseOutline,
} from '@vicons/ionicons5'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import ProjectTaskNode from './ProjectTaskNode.vue'
import { getProjects, getProjectDetail, getProjectTasks, getTaskNote } from '../../api/management'

const PROJECT_COLORS = [
  { dot: '#10b981', text: '#34d399', bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', line: 'rgba(16,185,129,0.5)' },
  { dot: '#3b82f6', text: '#60a5fa', bg: 'rgba(59,130,246,0.1)', border: 'rgba(59,130,246,0.3)', line: 'rgba(59,130,246,0.5)' },
  { dot: '#f59e0b', text: '#fbbf24', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', line: 'rgba(245,158,11,0.5)' },
  { dot: '#8b5cf6', text: '#a78bfa', bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.3)', line: 'rgba(139,92,246,0.5)' },
  { dot: '#ec4899', text: '#f472b6', bg: 'rgba(236,72,153,0.1)', border: 'rgba(236,72,153,0.3)', line: 'rgba(236,72,153,0.5)' },
  { dot: '#06b6d4', text: '#22d3ee', bg: 'rgba(6,182,212,0.1)', border: 'rgba(6,182,212,0.3)', line: 'rgba(6,182,212,0.5)' },
]

const TASK_STATUS = {
  active: { label: '进行中', dot: 'bg-green', ring: 'ring-green', icon: GitBranchOutline },
  completed: { label: '已完成', dot: 'bg-blue', ring: 'ring-blue', icon: CheckmarkCircleOutline },
  paused: { label: '已暂停', dot: 'bg-amber', ring: 'ring-amber', icon: PauseOutline },
  planned: { label: '规划中', dot: 'bg-gray', ring: 'ring-gray', icon: EllipseOutline },
}

const projects = ref([])
const activeSlug = ref(null)
const activeProject = ref(null)
const activeTree = ref(null)
const treeLoading = ref(false)
const selectedTask = ref(null)
const noteContent = ref(null)
const noteLoading = ref(false)
const pendingTaskId = ref(null) // 从 URL 恢复的任务 id，等任务树加载后定位

const route = useRoute()
const router = useRouter()

const activeColorIndex = computed(() => projects.value.findIndex(p => p.slug === activeSlug.value))
const activeColor = computed(() => projectColor(Math.max(0, activeColorIndex.value)))
const treeCount = computed(() => activeTree.value ? countAll(activeTree.value.tasks) : { total: 0, completed: 0 })

function projectColor(idx) {
  return PROJECT_COLORS[((idx % PROJECT_COLORS.length) + PROJECT_COLORS.length) % PROJECT_COLORS.length]
}
function statusIcon(status) {
  return (TASK_STATUS[status] || TASK_STATUS.planned).icon
}
function taskStatus(status) {
  return TASK_STATUS[status] || TASK_STATUS.planned
}
function taskStatusLabel(status) {
  return (TASK_STATUS[status] || TASK_STATUS.planned).label
}
function tabStyle(p, idx) {
  const c = projectColor(idx)
  return { background: c.bg, borderColor: c.border, color: c.text }
}

function countAll(tasks) {
  let total = 0, completed = 0
  for (const t of tasks) {
    total++
    if (t.status === 'completed') completed++
    if (t.children?.length) {
      const sub = countAll(t.children)
      total += sub.total
      completed += sub.completed
    }
  }
  return { total, completed }
}

// 递归查找任务节点
function findTaskById(tasks, id) {
  for (const t of tasks) {
    if (t.id === id) return t
    if (t.children?.length) {
      const found = findTaskById(t.children, id)
      if (found) return found
    }
  }
  return null
}

// 把当前状态写入 URL（replace，不污染历史）
function syncUrl(slug, taskId) {
  const query = { slug }
  if (taskId) query.task = taskId
  router.replace({ query })
}

async function loadProjects() {
  try {
    projects.value = await getProjects()
    if (!projects.value.length) return
    // 优先用 URL 中的 slug，否则取第一个
    const querySlug = route.query.slug
    const initialSlug = projects.value.some(p => p.slug === querySlug)
      ? querySlug
      : projects.value[0].slug
    pendingTaskId.value = route.query.task || null
    await selectProject(initialSlug, false)
    // 首次进入时补齐 URL（无 slug 或 slug 无效）
    if (route.query.slug !== initialSlug) syncUrl(initialSlug, pendingTaskId.value)
  } catch (e) {
    console.error('加载项目失败', e)
  }
}

// syncUrl=true 时把状态写回 URL（用户主动操作）；=false 时不写（URL 驱动时避免循环）
async function selectProject(slug, syncUrl = true) {
  if (activeSlug.value !== slug) {
    activeSlug.value = slug
    selectedTask.value = null
    noteContent.value = null
  }
  treeLoading.value = true
  try {
    const [detail, tree] = await Promise.all([
      getProjectDetail(slug),
      getProjectTasks(slug).catch(() => null),
    ])
    activeProject.value = detail
    activeTree.value = tree
    // 任务树加载完成后，恢复 URL 中指定的任务
    if (pendingTaskId.value && tree?.tasks?.length) {
      const found = findTaskById(tree.tasks, pendingTaskId.value)
      if (found) {
        selectedTask.value = found
        if (found.notePath) await loadNote(slug, found.notePath)
      }
      pendingTaskId.value = null
    }
  } catch (e) {
    console.error('加载项目详情失败', e)
  } finally {
    treeLoading.value = false
  }
  if (syncUrl) syncUrl(slug, null)
}

async function loadNote(slug, notePath) {
  noteContent.value = null
  noteLoading.value = true
  try {
    const res = await getTaskNote(slug, notePath)
    noteContent.value = res.content
  } catch (e) {
    noteContent.value = null
  } finally {
    noteLoading.value = false
  }
}

async function selectTask(task) {
  selectedTask.value = task
  noteContent.value = null
  if (task.notePath) await loadNote(activeSlug.value, task.notePath)
  syncUrl(activeSlug.value, task.id)
}

function backToReadme() {
  selectedTask.value = null
  noteContent.value = null
  syncUrl(activeSlug.value, null)
}

// 监听浏览器前进/后退导致的 URL 变化
watch(() => route.query, (q) => {
  const slug = q.slug
  // slug 变化 → 重新加载项目（不回写 URL）
  if (slug && slug !== activeSlug.value && projects.value.some(p => p.slug === slug)) {
    pendingTaskId.value = q.task || null
    selectProject(slug, false)
    return
  }
  // 同项目下 task 变化 → 切换任务
  if (slug === activeSlug.value && activeTree.value) {
    const taskId = q.task || null
    const currentId = selectedTask.value?.id
    if (taskId !== currentId) {
      if (!taskId) {
        selectedTask.value = null
        noteContent.value = null
      } else {
        const found = findTaskById(activeTree.value.tasks, taskId)
        if (found) {
          selectedTask.value = found
          if (found.notePath) loadNote(activeSlug.value, found.notePath)
          else noteContent.value = null
        }
      }
    }
  }
}, { deep: true })

onMounted(loadProjects)
</script>

<style scoped lang="scss">
.projects-page { padding: 4px 8px; }

.page-header { margin-bottom: 20px; }
.title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
  h2 { font-size: 18px; font-weight: 600; margin: 0; color: var(--color-text-heading); }
}
.project-tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.tab {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--color-border); background: var(--color-card);
  color: var(--color-text-secondary); padding: 5px 12px; border-radius: 999px;
  font-size: 12px; font-weight: 500; cursor: pointer;
  transition: all 0.15s;
  &:hover { background: var(--color-elevated); color: var(--color-text); }
}
.tab-dot { width: 8px; height: 8px; border-radius: 50%; }

.content-grid {
  display: grid; gap: 24px;
  grid-template-columns: 280px 1fr;
}
@media (max-width: 900px) { .content-grid { grid-template-columns: 1fr; } }

.tree-sidebar { min-height: 300px; }
.sidebar-head {
  display: flex; align-items: center; gap: 8px;
  border-bottom: 1px solid var(--color-border); padding-bottom: 8px; margin-bottom: 8px;
}
.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: var(--color-text-heading);
  background: none; border: none; cursor: pointer;
  &.active { color: var(--color-primary); }
}
.sidebar-meta { margin-left: auto; display: flex; align-items: center; gap: 6px;
  .meta-count { font-size: 10px; color: var(--color-text-dim); }
  .help-icon { color: var(--color-text-dim); cursor: help; &:hover { color: var(--color-text-secondary); } }
}
.tree-list { display: flex; flex-direction: column; gap: 2px; }

.empty { padding: 32px 0; text-align: center; color: var(--color-text-dim);
  p { margin-top: 8px; font-size: 12px; }
}

.detail-main { min-width: 0; }
.detail-head {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  border-bottom: 1px solid var(--color-border); padding-bottom: 16px; margin-bottom: 20px;
  h3 { font-size: 18px; font-weight: 700; margin: 0; color: var(--color-text-heading); }
}
.detail-badge { font-size: 10px; background: var(--color-elevated); padding: 2px 8px; border-radius: 4px; color: var(--color-text-secondary); }
.detail-assignee {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--color-primary-soft); color: var(--color-primary);
  padding: 2px 10px; border-radius: 999px; font-size: 11px;
}
.detail-date { font-family: monospace; font-size: 12px; color: var(--color-text-secondary); }
.desc-text { font-size: 14px; color: var(--color-text); line-height: 1.6; white-space: pre-line; }
.empty-inline { padding: 16px 0; text-align: center; color: var(--color-text-dim); font-size: 13px; }

.readme-meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: 12px;
  border-bottom: 1px solid var(--color-border); padding-bottom: 16px; margin-bottom: 24px;
  h3 { font-size: 20px; font-weight: 700; margin: 0; color: var(--color-text-heading); }
}
.readme-status { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; }
.readme-date { font-family: monospace; font-size: 12px; color: var(--color-text-secondary); }
.readme-tag { background: var(--color-elevated); padding: 2px 10px; border-radius: 999px; font-size: 10px; color: var(--color-text-secondary); }

.participants {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 24px;
}
.participant {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--color-border); background: var(--color-card);
  padding: 4px 10px; border-radius: 8px; font-size: 11px;
  strong { color: var(--color-text); font-weight: 500; }
  em { font-style: normal; background: var(--color-primary-soft); color: var(--color-primary); padding: 1px 6px; border-radius: 999px; font-size: 9px; }
}

.empty-page { padding: 64px 0; text-align: center; color: var(--color-text-dim);
  p { margin-top: 12px; font-size: 14px; }
}

.status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.status-dot.sm { width: 8px; height: 8px; }
.status-dot.lg { width: 12px; height: 12px; }
.bg-green { background: #22c55e; } .ring-green { box-shadow: 0 0 0 2px rgba(34,197,94,0.3); }
.bg-blue { background: #3b82f6; } .ring-blue { box-shadow: 0 0 0 2px rgba(59,130,246,0.3); }
.bg-gray { background: #a1a1aa; } .ring-gray { box-shadow: 0 0 0 2px rgba(161,161,170,0.3); }
.bg-amber { background: #f59e0b; } .ring-amber { box-shadow: 0 0 0 2px rgba(245,158,11,0.3); }
.bg-red { background: #ef4444; } .ring-red { box-shadow: 0 0 0 2px rgba(239,68,68,0.3); }

.legend { padding: 4px 0; .legend-title { font-size: 12px; font-weight: 600; margin-bottom: 8px; } }
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 11px; padding: 3px 0; }
</style>

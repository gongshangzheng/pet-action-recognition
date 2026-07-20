<template>
  <div class="wiki-page">
    <!-- Left sidebar -->
    <aside class="wiki-sidebar">
      <div class="wiki-sidebar-inner">
        <!-- Type tabs -->
        <div class="report-type-tabs">
          <button
            v-for="t in types"
            :key="t.key"
            class="report-type-tab"
            :class="{ active: activeType === t.key }"
            @click="switchType(t.key)"
          >
            {{ t.label }}
          </button>
        </div>

        <!-- Author filter -->
        <div class="sidebar-filter">
          <n-select
            v-model:value="authorFilter"
            :options="authorOptions"
            placeholder="全部成员"
            clearable
            size="tiny"
          />
        </div>

        <!-- Report list -->
        <n-spin :show="listLoading" size="small">
          <nav class="wiki-sidebar-nav">
            <a
              v-for="r in filteredReports"
              :key="r.id || r._key"
              class="wiki-sidebar-link"
              :class="{ active: isSelected(r) }"
              @click.prevent="selectReport(r)"
            >
              <span class="report-link-title">{{ r.title || '无标题' }}</span>
              <span class="report-link-meta">{{ reportSubLine(r) }}</span>
            </a>
          </nav>
          <div v-if="!filteredReports.length && !listLoading" class="wiki-sidebar-empty">
            {{ emptyText }}
          </div>
        </n-spin>
      </div>
    </aside>

    <!-- Mobile selector -->
    <div class="wiki-mobile-select">
      <div class="report-type-tabs" style="margin-bottom: 8px;">
        <button
          v-for="t in types"
          :key="t.key"
          class="report-type-tab"
          :class="{ active: activeType === t.key }"
          @click="switchType(t.key)"
        >
          {{ t.label }}
        </button>
      </div>
      <n-select
        :value="mobileSelected"
        :options="mobileOptions"
        placeholder="选择报告"
        size="small"
        @update:value="onMobileSelect"
      />
    </div>

    <!-- Center: article -->
    <article class="wiki-article">
      <n-spin :show="detailLoading">
        <div v-if="currentReport" class="wiki-content">
          <header class="wiki-header">
            <h1>{{ currentReport.title }}</h1>
            <div class="wiki-meta">{{ metaLine }}</div>
          </header>
          <div class="wiki-body">
            <MarkdownRenderer :content="currentReport.content" />
          </div>
        </div>
        <div v-else-if="!detailLoading" class="wiki-empty">
          <EmptyState :description="reports.length ? '请从左侧选择一份报告' : emptyText" />
        </div>
      </n-spin>
    </article>

    <!-- Right TOC -->
    <aside v-if="tocItems.length" class="wiki-toc">
      <div class="wiki-toc-inner">
        <div class="wiki-toc-title">目录</div>
        <nav>
          <a
            v-for="item in tocItems"
            :key="item.slug"
            class="wiki-toc-link"
            :class="{ 'level-3': item.level === 3 }"
            @click.prevent="scrollToHeading(item.slug)"
          >
            {{ item.text }}
          </a>
        </nav>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NSpin, NSelect } from 'naive-ui'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getDailyList, getDailyDetail, getWeeklyList, getWeeklyDetail, getMonthlyList, getMonthlyDetail } from '../../api/management'
import { extractToc } from '../../utils/markdown'

const route = useRoute()
const router = useRouter()

const types = [
  { key: 'daily', label: '日报' },
  { key: 'weekly', label: '周报' },
  { key: 'monthly', label: '月报' },
]

const activeType = computed(() => {
  return route.params.type || route.query.tab || 'daily'
})

const reports = ref([])
const listLoading = ref(false)
const currentReport = ref(null)
const detailLoading = ref(false)
const authorFilter = ref(null)

const authorOptions = computed(() =>
  [...new Set(reports.value.map(r => r.author))].map(a => ({ label: a, value: a }))
)

const filteredReports = computed(() => {
  let list = reports.value
  if (authorFilter.value) list = list.filter(r => r.author === authorFilter.value)
  return list
})

const emptyText = computed(() => {
  const labels = { daily: '日报', weekly: '周报', monthly: '月报' }
  return `暂无${labels[activeType.value] || '报告'}`
})

const tocItems = computed(() =>
  currentReport.value ? extractToc(currentReport.value.content) : []
)

const metaLine = computed(() => {
  if (!currentReport.value) return ''
  const r = currentReport.value
  if (activeType.value === 'daily') return `作者：${r.author} | 日期：${r.date}`
  if (activeType.value === 'weekly') return `作者：${r.author} | ${r.year} 年第 ${r.week} 周`
  if (activeType.value === 'monthly') return `作者：${r.author} | ${r.year} 年 ${r.month} 月`
  return ''
})

const mobileSelected = computed(() => {
  const p = route.params
  if (activeType.value === 'daily' && p.date) return `${p.date}|${p.author}`
  if (activeType.value === 'weekly' && p.year) return `${p.year}|${p.week}|${p.author}`
  if (activeType.value === 'monthly' && p.year) return `${p.year}|${p.month}|${p.author}`
  return null
})

const mobileOptions = computed(() =>
  filteredReports.value.map(r => ({
    label: `${reportSubLine(r)} ${r.author}`,
    value: r._key,
  }))
)

function reportSubLine(r) {
  if (activeType.value === 'daily') return r.date || ''
  if (activeType.value === 'weekly') return `${r.year} W${r.week}`
  if (activeType.value === 'monthly') return `${r.year}-${r.month}`
  return ''
}

function reportPath(r) {
  if (activeType.value === 'daily') return `/management/reports/daily/${r.date}/${r.author}`
  if (activeType.value === 'weekly') return `/management/reports/weekly/${r.year}/${r.week}/${r.author}`
  if (activeType.value === 'monthly') return `/management/reports/monthly/${r.year}/${r.month}/${r.author}`
  return '/management/reports'
}

function isSelected(r) {
  const p = route.params
  if (activeType.value === 'daily') return p.date === r.date && p.author === r.author
  if (activeType.value === 'weekly') return p.year == r.year && p.week == r.week && p.author === r.author
  if (activeType.value === 'monthly') return p.year == r.year && p.month == r.month && p.author === r.author
  return false
}

function switchType(type) {
  authorFilter.value = null
  currentReport.value = null
  router.push(`/management/reports?tab=${type}`)
}

function selectReport(r) {
  router.push(reportPath(r))
}

function onMobileSelect(key) {
  const r = filteredReports.value.find(x => x._key === key)
  if (r) selectReport(r)
}

function scrollToHeading(slug) {
  const el = document.getElementById(slug)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function fetchList() {
  listLoading.value = true
  reports.value = []
  try {
    if (activeType.value === 'daily') reports.value = (await getDailyList()) || []
    else if (activeType.value === 'weekly') reports.value = (await getWeeklyList()) || []
    else if (activeType.value === 'monthly') reports.value = (await getMonthlyList()) || []
    reports.value.forEach(r => {
      r._key = activeType.value === 'daily'
        ? `${r.date}|${r.author}`
        : activeType.value === 'weekly'
          ? `${r.year}|${r.week}|${r.author}`
          : `${r.year}|${r.month}|${r.author}`
    })
  } catch {
    reports.value = []
  }
  listLoading.value = false
}

async function fetchDetail() {
  const p = route.params
  if (!p.type) {
    currentReport.value = null
    return
  }
  detailLoading.value = true
  currentReport.value = null
  try {
    if (p.type === 'daily' && p.date && p.author) {
      currentReport.value = await getDailyDetail(p.date, p.author)
    } else if (p.type === 'weekly' && p.year && p.week && p.author) {
      currentReport.value = await getWeeklyDetail(p.year, p.week, p.author)
    } else if (p.type === 'monthly' && p.year && p.month && p.author) {
      currentReport.value = await getMonthlyDetail(p.year, p.month, p.author)
    }
    await nextTick()
  } catch {
    currentReport.value = null
  }
  detailLoading.value = false
}

onMounted(async () => {
  await fetchList()
  await fetchDetail()
})

watch(activeType, async () => {
  await fetchList()
  await fetchDetail()
})

watch(() => route.params, async () => {
  await fetchDetail()
})
</script>

<style scoped lang="scss">
.wiki-page {
  display: flex;
  gap: 24px;
  padding: 20px 24px;
  min-height: 100%;
}

.wiki-sidebar {
  display: none;
  width: 210px;
  flex-shrink: 0;
  @media (min-width: 1024px) { display: block; }
}

.wiki-sidebar-inner {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
  padding-right: 8px;
}

// Report type tabs
.report-type-tabs {
  display: flex;
  gap: 4px;
  padding: 0 4px 8px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 8px;
}

.report-type-tab {
  flex: 1;
  padding: 4px 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: var(--color-hover);
    color: var(--color-text);
  }
  &.active {
    background: var(--color-selected);
    color: var(--color-primary);
  }
}

.sidebar-filter {
  padding: 0 4px 8px;
}

.wiki-sidebar-nav {
  max-height: calc(100vh - 14rem);
  overflow-y: auto;
}

.wiki-sidebar-link {
  display: block;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  text-decoration: none;
  margin-bottom: 2px;

  &:hover {
    background: var(--color-hover);
    color: var(--color-text);
  }
  &.active {
    background: var(--color-selected);
    color: var(--color-primary);
    font-weight: 500;
  }
}

.report-link-title {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.report-link-meta {
  display: block;
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-dim);
  margin-top: 1px;
}

.wiki-sidebar-empty {
  font-size: 13px;
  color: var(--color-text-dim);
  padding: 8px 10px;
}

.wiki-mobile-select {
  display: block;
  margin-bottom: 12px;
  @media (min-width: 1024px) { display: none; }
}

.wiki-article {
  flex: 1;
  min-width: 0;
}

.wiki-content {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 24px;
}

.wiki-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
  h1 {
    font-size: 24px;
    font-weight: 700;
    margin: 0 0 8px;
    line-height: 1.3;
  }
}

.wiki-meta {
  font-size: 13px;
  color: var(--color-text-dim);
}

.wiki-body { line-height: 1.7; }

.wiki-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.wiki-toc {
  display: none;
  width: 180px;
  flex-shrink: 0;
  @media (min-width: 1280px) { display: block; }
}

.wiki-toc-inner {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
}

.wiki-toc-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
  padding: 8px 10px 4px;
}

.wiki-toc-link {
  display: block;
  padding: 3px 10px;
  border-left: 2px solid var(--color-border);
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text-dim);
  cursor: pointer;
  transition: all 0.15s;
  text-decoration: none;

  &:hover {
    color: var(--color-text);
    border-left-color: var(--color-primary);
  }
  &.level-3 { padding-left: 20px; }
}
</style>

<template>
  <div class="doc-page experiments-page">
    <h1 class="visually-hidden">实验报告</h1>

    <aside class="doc-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div v-if="!sidebarCollapsed" class="doc-sidebar-inner">
        <div class="panel-head">
          <span class="doc-sidebar-title">实验报告</span>
          <button class="panel-toggle" title="收起报告列表" @click="toggleSidebar">
            <n-icon size="14"><chevron-back-outline /></n-icon>
          </button>
        </div>

        <div class="filter-block">
          <n-select v-model:value="filters.topic" :options="topicOptions" placeholder="全部主题" clearable size="small" aria-label="按主题筛选" />
          <n-select v-model:value="filters.status" :options="statusOptions" placeholder="全部状态" clearable size="small" aria-label="按执行状态筛选" />
          <n-select v-model:value="filters.verdict" :options="verdictOptions" placeholder="全部结论" clearable size="small" aria-label="按结论筛选" />
          <n-checkbox v-model:checked="filters.completeOnly" size="small">仅完整</n-checkbox>
        </div>

        <n-spin :show="listLoading">
          <nav v-if="filteredReports.length" class="report-nav" aria-label="报告列表">
            <a
              v-for="r in filteredReports" :key="r.topic + '/' + r.slug"
              class="report-link" :class="{ active: isActive(r) }"
              :href="router.resolve(detailHref(r)).href"
              :aria-current="isActive(r) ? 'page' : undefined"
              v-clickable
              @click.prevent="open(r)"
            >
              <span class="report-link-title">{{ r.title || r.slug }}</span>
              <span class="report-link-meta">
                <n-tag size="small" :bordered="false" :type="statusTagType(r.status)">{{ statusLabel(r.status) }}</n-tag>
                <n-tag size="small" :bordered="false" :type="verdictTagType(r.verdict)">{{ verdictLabel(r.verdict) }}</n-tag>
                <span class="report-dim">{{ r.date }}</span>
              </span>
            </a>
          </nav>
          <div v-else-if="!listLoading" class="doc-sidebar-empty">当前筛选没有报告</div>
        </n-spin>
      </div>

      <div v-else class="panel-strip">
        <button class="panel-expand" title="展开报告列表" @click="toggleSidebar">
          <n-icon size="14"><chevron-forward-outline /></n-icon>
        </button>
        <span class="panel-strip-label">报告</span>
      </div>
    </aside>

    <div class="doc-mobile-select">
      <n-select
        :value="slug ? `${topic}/${slug}` : null"
        :options="mobileReportOptions" placeholder="选择报告" size="small" filterable
        @update:value="openByKey"
      />
    </div>

    <article class="doc-article">
      <n-spin :show="detailLoading">
        <div v-if="detail" class="doc-content">
          <header class="doc-header">
            <h1>{{ detail.metadata.title || `${topic}/${slug}` }}</h1>
            <div class="detail-meta">
              <n-tag size="small" :bordered="false" :type="statusTagType(detail.metadata.status)">{{ statusLabel(detail.metadata.status) }}</n-tag>
              <n-tag size="small" :bordered="false" :type="verdictTagType(detail.metadata.verdict)">{{ verdictLabel(detail.metadata.verdict) }}</n-tag>
              <n-tag v-if="detail.incomplete" size="small" :bordered="false" type="warning">不完整</n-tag>
              <span class="report-dim">run {{ detail.metadata.run_id }} · {{ detail.metadata.date }}</span>
              <span v-if="detail.metadata.change" class="report-dim">{{ detail.metadata.change }}</span>
              <n-button
                v-if="detail.metadata.run_id === 'gdino-crop-20261103a'"
                size="small" type="primary" secondary @click="openCropReview"
              >
                打开人工审阅
              </n-button>
            </div>
            <p v-if="detail.metadata.summary" class="detail-summary">{{ detail.metadata.summary }}</p>
            <n-alert v-if="detail.incomplete && detail.problems?.length" type="warning" :bordered="false" class="problems-alert">
              报告不完整（{{ detail.problems.length }} 项）：
              <ul class="problem-list">
                <li v-for="(p, i) in detail.problems.slice(0, 8)" :key="i">{{ p }}</li>
                <li v-if="detail.problems.length > 8">…共 {{ detail.problems.length }} 项</li>
              </ul>
            </n-alert>
          </header>

          <div class="detail-article">
          <!-- 正文：面向读者的文章；附录默认折叠 -->
          <MarkdownRenderer :content="reportParts.narrative" />

          <details v-if="reportParts.hasAppendix" class="foldable">
            <summary>附录：配置与完整数据<span class="fold-hint">精确配置 · 完整指标 · 来源与核查</span></summary>
            <MarkdownRenderer :content="reportParts.appendix" />
          </details>

          <!-- 结构化技术指标（manifest 指标含局限 / 趋势 / 表格）：默认折叠，不铺满正文 -->
          <details v-if="hasStructuredMetrics" class="foldable">
            <summary>指标与趋势（机器可读）<span class="fold-hint">evidence · metrics.json · cases</span></summary>

            <section v-if="metricTables.length" class="metrics-section">
              <div v-for="t in metricTables" :key="t.title" class="metric-table">
                <h3 v-if="t.title">{{ t.title }}</h3>
                <n-data-table
                  :columns="dynamicColumns(t.columns)" :data="tableRows(t.rows)"
                  :bordered="false" size="small" striped :scroll-x="560"
                />
              </div>
            </section>

            <section v-if="hasSeries" class="chart-section">
              <h3>趋势</h3>
              <v-chart class="trend-chart" :option="chartOption" autoresize aria-label="指标趋势图" role="img" />
            </section>

            <section v-if="manifestMetrics.length" class="manifest-metrics">
              <h3>指标说明（含局限）</h3>
              <n-data-table
                :columns="manifestColumns" :data="manifestMetrics"
                :bordered="false" size="small" striped :scroll-x="720"
              />
            </section>
          </details>

          <!-- 案例对比：正文已引用的不重复铺满；这里只补未引用的 -->
          <section v-if="additionalCases.length" class="cases-section">
            <h2>案例对比</h2>
            <div class="cases-toolbar">
              <n-radio-group v-model:value="compareMode" size="small" name="compare-mode">
                <n-radio-button value="side" label="并排" />
                <n-radio-button value="toggle" label="交替" />
              </n-radio-group>
              <n-radio-group v-if="compareMode === 'toggle' && additionalCases.length > 1" v-model:value="toggleIndex" size="small" name="case-pick">
                <n-radio-button v-for="(c, i) in additionalCases" :key="c.id" :value="i" :label="c.id" />
              </n-radio-group>
            </div>

            <div v-if="compareMode === 'side'" class="cases-grid">
              <figure v-for="c in additionalCases" :key="c.id" class="case-fig">
                <div class="case-img-wrap">
                  <video v-if="isVideoCase(c)" :src="assetUrl(c)" controls preload="metadata" playsinline class="case-video" />
                  <img v-else :src="assetUrl(c)" :alt="`${c.id}：${c.selection_reason}`" loading="lazy" />
                </div>
                <figcaption>
                  <strong>{{ c.id }}</strong> · {{ c.input }}
                  <span class="case-reason">（{{ c.selection_reason }}）</span>
                </figcaption>
              </figure>
            </div>

            <figure v-else class="case-fig case-toggle">
              <div class="case-img-wrap">
                <video v-if="isVideoCase(additionalCases[toggleIndex])" :src="assetUrl(additionalCases[toggleIndex])" controls preload="metadata" playsinline class="case-video" />
                <img v-else :src="assetUrl(additionalCases[toggleIndex])" :alt="`${additionalCases[toggleIndex].id}：${additionalCases[toggleIndex].selection_reason}`" />
              </div>
              <figcaption>
                <strong>{{ additionalCases[toggleIndex].id }}</strong> · {{ additionalCases[toggleIndex].input }}
                <span class="case-reason">（{{ additionalCases[toggleIndex].selection_reason }}）</span>
              </figcaption>
            </figure>
          </section>
        </div>
      
        </div>
        <div v-else-if="!detailLoading" class="doc-empty">
          <EmptyState description="请从左侧选择一篇报告" />
        </div>
      </n-spin>
    </article>

    <aside v-if="tocItems.length" class="doc-toc">
      <div class="doc-toc-inner">
        <div class="panel-head">
          <span class="doc-toc-title">目录</span>
        </div>
        <nav>
          <a
            v-for="item in tocItems" :key="item.text"
            class="doc-toc-link" :class="{ active: activeSection === item.text }"
            :href="`#${item.anchor}`"
            @click.prevent="scrollToSection(item)"
          >{{ item.text }}</a>
        </nav>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NIcon, NSpin, NSelect, NTag, NCheckbox, NDataTable,
  NAlert, NRadioGroup, NRadioButton, NButton,
} from 'naive-ui'
import { ChevronBackOutline, ChevronForwardOutline } from '@vicons/ionicons5'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getExperiments, getExperimentDetail, getExperimentAssetUrl, getExperimentMediaUrl } from '../../api/experiments'
import { vClickable } from '../../directives/clickable'
import { splitReportAppendix, narrativeEmbedsAsset } from './experimentReportContent'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const route = useRoute()
const router = useRouter()

const reports = ref([])
const invalidReports = ref([])
const listLoading = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const filters = ref({ topic: null, status: null, verdict: null, completeOnly: false })
const sidebarCollapsed = ref(false)
const activeSection = ref('')

function toggleSidebar() { sidebarCollapsed.value = !sidebarCollapsed.value }

const mobileReportOptions = computed(() => filteredReports.value.map(r => ({
  label: r.title || r.slug,
  value: `${r.topic}/${r.slug}`,
})))

function openByKey(key) {
  if (!key) return
  const [t, slugValue] = key.split('/')
  router.push({ query: { topic: t, slug: slugValue } })
}

const topic = computed(() => route.query.topic || '')
const slug = computed(() => route.query.slug || '')

const topicOptions = computed(() =>
  [...new Set(reports.value.map(r => r.topic))].map(t => ({ label: t, value: t })))
const statusOptions = [
  { label: '完成', value: 'complete' }, { label: '部分完成', value: 'partial' }, { label: '失败', value: 'failed' },
]
const verdictOptions = [
  { label: '有改善', value: 'improved' }, { label: '无收益', value: 'no-gain' },
  { label: '变差', value: 'worse' }, { label: '不确定', value: 'inconclusive' },
]
const STATUS_LABEL = { complete: '完成', partial: '部分完成', failed: '失败' }
const VERDICT_LABEL = { improved: '有改善', 'no-gain': '无收益', worse: '变差', inconclusive: '不确定' }
const statusLabel = s => STATUS_LABEL[s] || s || '—'
const verdictLabel = v => VERDICT_LABEL[v] || v || '—'
const statusTagType = s => ({ complete: 'success', partial: 'warning', failed: 'error' }[s] || 'default')
const verdictTagType = v => ({ improved: 'success', 'no-gain': 'default', worse: 'error', inconclusive: 'warning' }[v] || 'default')

const filteredReports = computed(() => reports.value.filter(r =>
  (!filters.value.topic || r.topic === filters.value.topic) &&
  (!filters.value.status || r.status === filters.value.status) &&
  (!filters.value.verdict || r.verdict === filters.value.verdict) &&
  (!filters.value.completeOnly || !r.incomplete)))

function isActive(r) { return r.topic === topic.value && r.slug === slug.value }
function detailHref(r) { return `/management/experiments?topic=${encodeURIComponent(r.topic)}&slug=${encodeURIComponent(r.slug)}` }

async function loadList() {
  listLoading.value = true
  try {
    const data = await getExperiments()
    reports.value = data.reports || []
    invalidReports.value = data.invalid || []
  } finally {
    listLoading.value = false
  }
}

async function loadDetail(t, s) {
  if (!t || !s) { detail.value = null; return }
  detailLoading.value = true
  try {
    detail.value = await getExperimentDetail(t, s)
    await nextTick()
    activeSection.value = ''
    observeSections()
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

function open(r) {
  router.push(detailHref(r))
}

function openCropReview() {
  router.push({
    name: 'CropReview',
    query: { set: 'cat-crop-gdino-20261103a-sample20-v1' },
  })
}

const metricTables = computed(() => (detail.value?.metrics?.tables || []).filter(t => (t.rows || []).length))
const hasSeries = computed(() => (detail.value?.metrics?.series || []).some(s => (s.points || []).length))
const manifestMetrics = computed(() => detail.value?.manifest?.metrics || [])
const evidenceEntries = computed(() => Object.entries(detail.value?.manifest?.evidence || {}).filter(([, v]) => v))
const cases = computed(() => (detail.value?.manifest?.cases || []).filter(c => (c.kind === 'image' || c.kind === 'video') && c.src))
const reportParts = computed(() => splitReportAppendix(detail.value?.content || ''))

const tocItems = computed(() => {
  const markdown = reportParts.value?.narrative || ''
  return markdown
    .split('\n')
    .filter(line => /^##\s+/.test(line))
    .map(line => {
      const text = line.replace(/^##\s+/, '').trim()
      return { text, anchor: text.replace(/\s+/g, '-') }
    })
})

function scrollToSection(item) {
  const nodes = document.querySelectorAll('.doc-content h2')
  const target = [...nodes].find(node => node.textContent.trim() === item.text)
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeSection.value = item.text
    history.replaceState(null, '', `#${item.anchor}`)
  }
}

let sectionObserver = null
function observeSections() {
  if (sectionObserver) sectionObserver.disconnect()
  const nodes = document.querySelectorAll('.doc-content h2')
  if (!nodes.length || typeof IntersectionObserver === 'undefined') return
  sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries.filter(entry => entry.isIntersecting)
    if (visible.length) activeSection.value = visible[0].target.textContent.trim()
  }, { rootMargin: '-20% 0px -70% 0px' })
  nodes.forEach(node => sectionObserver.observe(node))
}
const hasStructuredMetrics = computed(() => !!(manifestMetrics.value.length || hasSeries.value || metricTables.value.length || evidenceEntries.value.length))
// 正文已引用的案例图不重复铺满，只补未引用的
const additionalCases = computed(() => cases.value.filter(c => !narrativeEmbedsAsset(reportParts.value.narrative, c.src)))
const compareMode = ref('side')
const toggleIndex = ref(0)

function assetUrl(c) {
  const parts = String(c.src || '').split('/')
  const file = parts[parts.length - 1]
  if (parts[0] === 'media' || c.kind === 'video') return getExperimentMediaUrl(topic.value, slug.value, file)
  return getExperimentAssetUrl(topic.value, slug.value, file)
}

function isVideoCase(c) {
  return c?.kind === 'video'
}

const chartOption = computed(() => {
  const series = detail.value?.metrics?.series || []
  return {
    tooltip: { trigger: 'axis' },
    legend: series.length > 1 ? { bottom: 0 } : undefined,
    grid: { left: 48, right: 24, top: 24, bottom: series.length > 1 ? 40 : 28, containLabel: true },
    xAxis: { type: 'value', name: series[0]?.x_label || '' },
    yAxis: { type: 'value', name: series[0]?.y_label || '' },
    series: series.map(s => ({
      name: s.name, type: 'line', showSymbol: true,
      data: (s.points || []).map(p => [p.x, p.y]),
    })),
  }
})

function tableRows(rows) {
  return (rows || []).map(r => {
    const obj = {}
    ;(r || []).forEach((v, i) => { obj[`col${i}`] = String(v) })
    return obj
  })
}
// 行对象用动态 key col0..N，列按索引生成
function dynamicColumns(cols) {
  return (cols || []).map((c, i) => ({ title: c, key: `col${i}` }))
}

const manifestColumns = [
  { title: '指标', key: 'name', minWidth: 120 },
  { title: '单位', key: 'unit', width: 70 },
  { title: 'baseline', key: 'baseline', width: 90 },
  { title: '结果', key: 'result', width: 90 },
  { title: '变化', key: 'delta', width: 80 },
  { title: '样本量', key: 'sample_size', width: 80 },
  { title: '来源', key: 'source', minWidth: 140, ellipsis: { tooltip: true } },
  { title: '局限（不测量什么）', key: 'limitation', minWidth: 180, ellipsis: { tooltip: true } },
]

onMounted(() => {
  loadList()
  if (topic.value && slug.value) loadDetail(topic.value, slug.value)
})

watch(() => route.query, (q) => {
  if (q.topic && q.slug) loadDetail(q.topic, q.slug)
  else detail.value = null
})
</script>

<style scoped lang="scss">
// 版式参考 DocPage：侧栏选报告 + 正文阅读 + 右侧章节导航
.doc-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  min-height: 100%;

  @media (min-width: 1024px) {
    flex-direction: row;
    gap: 24px;
    padding: 20px 24px;
  }
}

.doc-sidebar { display: none; width: 240px; flex-shrink: 0;
  @media (min-width: 1024px) { display: block; }
}
.doc-sidebar.collapsed { width: 20px; }

.doc-sidebar-inner {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
  padding-right: 8px;
}

.doc-sidebar-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
}

.doc-sidebar-empty { padding: 8px 10px; font-size: 12px; color: var(--color-text-dim); }

.panel-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 4px; padding: 4px 2px 4px 10px; margin-bottom: 4px;
}

.panel-toggle, .panel-expand {
  display: inline-flex; align-items: center; justify-content: center;
  background: none; border: none; min-width: 24px; min-height: 24px;
  padding: 4px; cursor: pointer; color: var(--color-text-dim); border-radius: 4px;
  &:hover { background: var(--color-hover); color: var(--color-text); }
}

.panel-strip {
  position: sticky; top: 16px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.panel-expand { width: 100%; box-sizing: border-box; background: var(--color-card); border: 1px solid var(--color-border); border-radius: 6px; padding: 6px 0; }
.panel-strip-label { writing-mode: vertical-rl; font-size: 11px; color: var(--color-text-dim); letter-spacing: 0.08em; }

.filter-block {
  display: grid;
  gap: 6px;
  padding: 0 2px 10px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--color-border-light);

  :deep(.n-base-selection) { font-size: 12px; }
}

.report-nav { display: flex; flex-direction: column; gap: 2px; }

.report-link {
  display: flex; flex-direction: column; gap: 4px;
  padding: 8px 10px; border-radius: 6px;
  border-left: 2px solid transparent;
  text-decoration: none; color: var(--color-text);

  &:hover { background: var(--color-hover); }
  &:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -2px; }
  &.active { background: var(--color-selected); border-left-color: var(--color-primary); }
}

.report-link-title { font-size: 13px; font-weight: 500; line-height: 1.35; overflow-wrap: anywhere; }
.report-link-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.report-dim { color: var(--color-text-dim); font-size: 12px; }

.doc-mobile-select {
  display: block;
  @media (min-width: 1024px) { display: none; }
}

.doc-article { flex: 1; min-width: 0; }

.doc-content {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
  // 阅读列居中：宽屏下不让正文贴住侧栏
  max-width: 960px;
  margin-inline: auto;

  @media (min-width: 640px) { padding: 24px 32px; }
}

.doc-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);

  h1 { font-size: 24px; font-weight: 700; margin: 0 0 8px; line-height: 1.3; }
}

.doc-empty { display: flex; align-items: center; justify-content: center; min-height: 300px; }

.doc-toc { display: none; width: 180px; flex-shrink: 0;
  @media (min-width: 1280px) { display: block; }
}
.doc-toc-inner { position: sticky; top: 16px; max-height: calc(100vh - 5rem); overflow-y: auto; }
.doc-toc-title {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--color-text-dim);
}
.doc-toc-link {
  display: block; padding: 3px 10px;
  border-left: 2px solid var(--color-border);
  font-size: 12px; line-height: 1.4; color: var(--color-text-dim);
  cursor: pointer; text-decoration: none;
  transition: color 0.15s, border-color 0.15s;

  &:hover, &.active { color: var(--color-text); border-left-color: var(--color-primary); }
}

.visually-hidden {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

.invalid-block {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--color-elevated);
  font-size: 12px;
  color: var(--color-text-dim);
  overflow-wrap: anywhere;
}
.invalid-title { margin-right: 6px; }
.invalid-item { margin-right: 10px; }

.detail-card { overflow: visible; }

.detail-header { margin-bottom: 8px; }
.detail-title { margin: 0 0 8px; font-size: 20px; }
.visually-hidden {
  position: absolute; width: 1px; height: 1px; margin: -1px;
  clip-path: inset(50%); overflow: hidden; white-space: nowrap;
}
.detail-meta {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  color: var(--color-text-secondary); font-size: 13px;
}
.change-link { color: var(--color-text-dim); text-decoration: none; }
.detail-summary { margin: 10px 0 0; color: var(--color-text-secondary); }
.problems-alert { margin-top: 10px; }
.problem-list { margin: 6px 0 0; padding-left: 18px; }

.detail-article { margin-top: 8px; }

// 段落保持可读行宽；表格、代码、图占满正文区
.detail-article :deep(table),
.detail-article :deep(pre),
.detail-article :deep(.n-data-table),
.detail-article :deep(figure) {
  max-width: none;
  width: 100%;
}

.detail-article :deep(table) { display: block; overflow-x: auto; }
.foldable {
  margin-top: 18px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  background: var(--color-elevated);

  summary {
    cursor: pointer;
    padding: 10px 14px;
    font-weight: 600;
    list-style: none;
    &::-webkit-details-marker { display: none; }
    &::before { content: "▸"; margin-right: 8px; color: var(--color-text-dim); }
  }
  &[open] summary::before { content: "▾"; }
  summary:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -2px; border-radius: 8px; }

  .fold-hint { display: block; font-size: 12px; font-weight: normal; color: var(--color-text-dim); margin-top: 2px; }
  @media (min-width: 640px) { .fold-hint { display: inline; margin-left: 10px; margin-top: 0; } }

  > .markdown-body { padding: 0 14px 14px; }
  > section { padding: 0 14px 14px; }
}

.metrics-section, .chart-section, .manifest-metrics { margin-top: 12px; padding-top: 0; border-top: none;
  h3 { font-size: 13px; margin: 0 0 6px; color: var(--color-text-secondary); }
}

.cases-section {
  margin-top: 20px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
  h2 { font-size: 15px; margin: 0 0 10px; }
}

.metric-table { margin-bottom: 12px; }
.trend-chart { height: 260px; }

.cases-toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }

.cases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.case-fig { margin: 0; }
.case-img-wrap {
  overflow: auto;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  background: var(--color-elevated);

  img {
    display: block;
    // 原始像素纪律：不缩放、不平滑，容器滚动看细节
    image-rendering: pixelated;
    max-width: none;
  }

  // 视频需要看运动：按容器宽度缩放，不做像素化
  video.case-video {
    display: block;
    width: 100%;
    max-width: 720px;
    background: #000;
  }
}

.case-fig figcaption {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}
.case-reason { color: var(--color-text-dim); }
.case-toggle .case-img-wrap { max-width: 100%; }

@media (max-width: 720px) {
  .header-row { flex-direction: column; align-items: stretch; }
  .filter-select { width: 100%; }
}
</style>

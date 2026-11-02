<template>
  <div class="page-container experiments-page">
    <h1 class="visually-hidden">实验报告</h1>
    <n-card size="small">
      <template #header>
        <div class="flex-between header-row">
          <h2 class="card-title">实验报告</h2>
          <n-space align="center" :wrap="false">
            <n-select
              v-model:value="filters.topic" :options="topicOptions"
              placeholder="全部主题" clearable size="small" class="filter-select"
              aria-label="按主题筛选"
            />
            <n-select
              v-model:value="filters.status" :options="statusOptions"
              placeholder="全部状态" clearable size="small" class="filter-select"
              aria-label="按执行状态筛选"
            />
            <n-select
              v-model:value="filters.verdict" :options="verdictOptions"
              placeholder="全部结论" clearable size="small" class="filter-select"
              aria-label="按结论筛选"
            />
            <n-checkbox v-model:checked="filters.completeOnly" size="small">仅完整</n-checkbox>
          </n-space>
        </div>
      </template>

      <n-spin :show="listLoading">
        <template v-if="filteredReports.length || invalidReports.length">
          <ul class="report-list">
            <li v-for="r in filteredReports" :key="r.topic + '/' + r.slug">
              <a
                class="report-item"
                :class="{ active: isActive(r) }"
                :href="router.resolve(detailHref(r)).href"
                :aria-current="isActive(r) ? 'page' : undefined"
                v-clickable
                @click.prevent="open(r)"
              >
                <span class="report-title">{{ r.title || r.slug }}</span>
                <span class="report-meta">
                  <n-tag size="small" :bordered="false" :type="statusTagType(r.status)">{{ statusLabel(r.status) }}</n-tag>
                  <n-tag size="small" :bordered="false" :type="verdictTagType(r.verdict)">{{ verdictLabel(r.verdict) }}</n-tag>
                  <n-tag v-if="r.incomplete" size="small" :bordered="false" type="warning">不完整</n-tag>
                  <span class="report-dim">{{ r.topic }} · {{ r.date }}</span>
                </span>
              </a>
            </li>
          </ul>
          <div v-if="invalidReports.length" class="invalid-block">
            <span class="invalid-title">{{ invalidReports.length }} 个目录无法解析为报告：</span>
            <span v-for="inv in invalidReports" :key="inv.topic + '/' + inv.slug" class="invalid-item">
              {{ inv.topic }}/{{ inv.slug }}（{{ (inv.missing || []).join('、') }}）
            </span>
          </div>
        </template>
        <EmptyState v-else-if="!listLoading" description="暂无实验报告；用 experiment skill 的 build_report.py 生成" />
      </n-spin>
    </n-card>

    <n-card v-if="detail" size="small" class="detail-card">
      <n-spin :show="detailLoading">
        <header class="detail-header">
          <h2 class="detail-title">{{ detail.metadata.title || `${topic}/${slug}` }}</h2>
          <div class="detail-meta">
            <n-tag size="small" :bordered="false" :type="statusTagType(detail.metadata.status)">{{ statusLabel(detail.metadata.status) }}</n-tag>
            <n-tag size="small" :bordered="false" :type="verdictTagType(detail.metadata.verdict)">{{ verdictLabel(detail.metadata.verdict) }}</n-tag>
            <n-tag v-if="detail.incomplete" size="small" :bordered="false" type="warning">不完整</n-tag>
            <span class="report-dim">run {{ detail.metadata.run_id }} · {{ detail.metadata.date }}</span>
            <a v-if="detail.metadata.change" class="report-dim change-link" :href="`/api/management/experiments`" @click.prevent>{{ detail.metadata.change }}</a>
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
                  <img :src="assetUrl(c)" :alt="`${c.id}：${c.selection_reason}`" loading="lazy" />
                </div>
                <figcaption>
                  <strong>{{ c.id }}</strong> · {{ c.input }}
                  <span class="case-reason">（{{ c.selection_reason }}）</span>
                </figcaption>
              </figure>
            </div>

            <figure v-else class="case-fig case-toggle">
              <div class="case-img-wrap">
                <img :src="assetUrl(additionalCases[toggleIndex])" :alt="`${additionalCases[toggleIndex].id}：${additionalCases[toggleIndex].selection_reason}`" />
              </div>
              <figcaption>
                <strong>{{ additionalCases[toggleIndex].id }}</strong> · {{ additionalCases[toggleIndex].input }}
                <span class="case-reason">（{{ additionalCases[toggleIndex].selection_reason }}）</span>
              </figcaption>
            </figure>
          </section>
        </div>
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard, NSpin, NSpace, NSelect, NTag, NCheckbox, NDataTable,
  NAlert, NRadioGroup, NRadioButton,
} from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getExperiments, getExperimentDetail, getExperimentAssetUrl } from '../../api/experiments'
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
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

function open(r) {
  router.push(detailHref(r))
}

const metricTables = computed(() => (detail.value?.metrics?.tables || []).filter(t => (t.rows || []).length))
const hasSeries = computed(() => (detail.value?.metrics?.series || []).some(s => (s.points || []).length))
const manifestMetrics = computed(() => detail.value?.manifest?.metrics || [])
const evidenceEntries = computed(() => Object.entries(detail.value?.manifest?.evidence || {}).filter(([, v]) => v))
const cases = computed(() => (detail.value?.manifest?.cases || []).filter(c => c.kind === 'image' && c.src))
const reportParts = computed(() => splitReportAppendix(detail.value?.content || ''))
const hasStructuredMetrics = computed(() => !!(manifestMetrics.value.length || hasSeries.value || metricTables.value.length || evidenceEntries.value.length))
// 正文已引用的案例图不重复铺满，只补未引用的
const additionalCases = computed(() => cases.value.filter(c => !narrativeEmbedsAsset(reportParts.value.narrative, c.src)))
const compareMode = ref('side')
const toggleIndex = ref(0)

function assetUrl(c) {
  const parts = String(c.src || '').split('/')
  const file = parts[parts.length - 1]
  return getExperimentAssetUrl(topic.value, slug.value, file)
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
.experiments-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row { flex-wrap: wrap; gap: 8px; }
.filter-select { width: 132px; }

.report-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.report-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  color: var(--color-text);

  &:hover { background: var(--color-hover); }
  &:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -2px; }
  &.active { background: var(--color-selected); }
}

.report-title { font-weight: 500; min-width: 0; overflow-wrap: anywhere; }
.report-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.report-dim { color: var(--color-text-dim); font-size: 12px; }

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

.detail-article { margin-top: 8px; max-width: 76ch; }
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

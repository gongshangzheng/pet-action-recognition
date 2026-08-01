<template>
  <div class="page-container train-results">
    <!-- 筛选 -->
    <n-card size="small">
      <n-space align="center" size="small" wrap>
        <span class="lbl">模型</span>
        <n-select v-model:value="filters.model" :options="modelOptions" placeholder="全部" clearable size="small" style="width: 160px" />
        <span class="lbl">数据集</span>
        <n-select v-model:value="filters.dataset" :options="datasetOptions" placeholder="全部" clearable size="small" style="width: 140px" />
        <span class="lbl">状态</span>
        <n-select v-model:value="filters.status" :options="statusOptions" placeholder="全部" clearable size="small" style="width: 100px" />
        <n-button size="small" @click="load">刷新</n-button>
      </n-space>
    </n-card>

    <!-- 多模型曲线叠加区（所有 run 的同一指标叠在一张图对比） -->
    <n-card size="small" class="curve-card">
      <template #header>
        <div class="flex-between">
          <h3>训练曲线（多模型叠加）</h3>
          <n-space align="center" size="small">
            <span class="hint">指标</span>
            <n-select v-model:value="curveMetric" :options="metricOptions" size="small" style="width: 150px" />
          </n-space>
        </div>
      </template>
      <div v-if="compareOption" class="curve-wrap">
        <v-chart class="curve" :option="compareOption" autoresize />
      </div>
      <div v-else class="curve-placeholder">暂无曲线数据（训练跑出 epoch 后自动出现，下方筛选同步生效）</div>
    </n-card>

    <!-- 训练进程列表 -->
    <n-card size="small" title="训练进程列表" style="margin-top: 12px">
      <n-spin :show="loading">
        <n-data-table v-if="filteredRuns.length" :columns="runColumns" :data="filteredRuns" :bordered="false" size="small" striped />
        <EmptyState v-else description="暂无训练进程。在「训练运行」页启动训练后，进程列表 + loss 曲线在此。" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, h, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NSpin, NSpace, NSelect, NButton, NDataTable, useMessage } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTrainRuns, getTrainOutputUrl } from '../../api/training'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const runs = ref([])
const filters = ref({ model: null, dataset: null, status: null })
const currentRun = ref(null)
const currentRunId = ref(null)

// 跨浏览器刷新(F5)持久化筛选 + 选中 run（下拉框刷新不清空）
const STORE_KEY = 'projflow:train-results'
function persistState() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({ filters: filters.value, currentRunId: currentRunId.value }))
  } catch { /* localStorage 不可用时静默 */ }
}
function restoreState() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE_KEY) || '{}')
    if (s.filters) filters.value = { model: null, dataset: null, status: null, ...s.filters }
    if (s.currentRunId) currentRunId.value = s.currentRunId
  } catch { /* ignore */ }
}
watch([filters, () => currentRunId.value], persistState, { deep: true })
restoreState()

// 实时曲线：3s 轮询 getTrainRuns，同步选中 run 的 loss_series（曲线随 epoch 增长）
const RUNNING = new Set(['running', 'started'])
let pollTimer = null
const isRunning = (r) => !!r && RUNNING.has(r.status)

function sortRuns(list) {
  return [...list].sort((a, b) => (b.started_at || '').localeCompare(a.started_at || ''))
}

function syncCurrent() {
  if (!currentRunId.value) return
  const r = runs.value.find(x => x.id === currentRunId.value)
  if (r) {
    currentRun.value = r
  } else {
    // 持久化的 run 已不存在（被删）→ 清掉选中，交由 load() 回退到最新 run
    currentRunId.value = null
    currentRun.value = null
  }
}

async function refreshRuns() {
  loading.value = true
  try {
    const res = await getTrainRuns()
    runs.value = sortRuns(res.runs || [])
    syncCurrent()
  } catch { message.error('加载训练进程列表失败') }
  loading.value = false
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    const res = await getTrainRuns().catch(() => null)
    if (res?.runs) {
      runs.value = sortRuns(res.runs)
      syncCurrent()
    }
    // 全部 run 结束 → 停轮询
    if (!runs.value.some(isRunning)) {
      stopPolling()
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// 选项列表始终包含当前已选中值：即使 runs 变动导致该值暂时不在列表里，
// 下拉框也不会被清空（轮询/刷新不清空选中）。
const withSelected = (values, selected) => {
  if (selected && !values.includes(selected)) values.push(selected)
  return values.map(v => ({ label: v, value: v }))
}
const modelOptions = computed(() => withSelected([...new Set(runs.value.map(r => r.model))], filters.value.model))
const datasetOptions = computed(() => withSelected([...new Set(runs.value.map(r => r.dataset))], filters.value.dataset))
const statusOptions = computed(() => withSelected([...new Set(runs.value.map(r => r.status))], filters.value.status))

const filteredRuns = computed(() => {
  let list = runs.value
  if (filters.value.model) list = list.filter(r => r.model === filters.value.model)
  if (filters.value.dataset) list = list.filter(r => r.dataset === filters.value.dataset)
  if (filters.value.status) list = list.filter(r => r.status === filters.value.status)
  return list
})

// 多模型曲线叠加：所有 filteredRuns 的同一指标叠在一张图，逐 run 一条线
const curveMetric = ref('top1_acc')
const metricOptions = [
  { label: 'val top1 acc', value: 'top1_acc' },
  { label: 'val top5 acc', value: 'top5_acc' },
  { label: 'train loss', value: 'loss' },
  { label: 'learning rate', value: 'lr' },
]
const compareOption = computed(() => {
  const metric = curveMetric.value
  const runs = filteredRuns.value.filter(r => r.loss_series?.some(p => p[metric] != null))
  if (!runs.length) return null
  const series = runs.map(r => ({
    name: r.name || r.model || r.id,
    type: 'line',
    data: r.loss_series.filter(p => p[metric] != null).map(p => [p.epoch, p[metric]]),
    showSymbol: true,
    symbolSize: 4,
    smooth: true,
  }))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name), top: 0, type: 'scroll' },
    grid: { top: 40, left: 55, right: 20, bottom: 40 },
    xAxis: { type: 'value', name: 'epoch', minInterval: 1 },
    yAxis: { type: 'value', name: metric },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series,
  }
})

const runColumns = computed(() => [
  { title: '名称', key: 'name', width: 150, render: (r) => h('a', { style: 'color: #2563eb; cursor: pointer; text-decoration: none', onClick: () => router.push(`/training/runs/${r.id}`), title: r.description || r.id }, r.name || r.id) },
  { title: '模型', key: 'model' },
  { title: '数据集', key: 'dataset' },
  { title: 'epochs', key: 'epochs', width: 70 },
  { title: 'final_loss', key: 'final_loss', width: 90, render: (r) => fmt(r.final_loss) },
  { title: 'best_metric', key: 'best_metric', width: 100, render: (r) => fmt(r.best_metric) },
  { title: '状态', key: 'status', width: 80 },
  { title: '时间', key: 'started_at', render: (r) => r.started_at?.split('T')[0] || '-' },
  {
    title: 'Checkpoint', key: 'checkpoint', width: 140,
    render: (r) => {
      const links = []
      if (r.checkpoint_path) {
        links.push(h('a', { href: getTrainOutputUrl(r.checkpoint_path), style: 'color: #2563eb; text-decoration: none; margin-right: 8px', title: '下载 latest' }, 'latest'))
      }
      if (r.best_checkpoint_path) {
        links.push(h('a', { href: getTrainOutputUrl(r.best_checkpoint_path), style: 'color: #18a058; text-decoration: none', title: '下载 best' }, 'best'))
      }
      return links.length ? h('span', {}, links) : h('span', { style: 'color: #ccc' }, '—')
    },
  },
])

// cpColumns removed — checkpoint links now in run list directly

function fmt(v) { return (v == null || isNaN(v)) ? '-' : Number(v).toFixed(4) }
function fmtSize(b) {
  if (!b) return '-'
  const u = ['B', 'KB', 'MB', 'GB']; let i = 0, v = b
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${u[i]}`
}

function selectRun(r) {
  currentRunId.value = r?.id ?? null
  currentRun.value = r ?? null
  if (r && !r.loss_series?.length) message.info('该 run 暂无 loss_series（训练未开始或未记录）')
  // 选中一条还在跑的 run → 确保轮询开着，曲线会随 epoch 更新
  if (isRunning(r)) startPolling()
}

async function load() {
  loading.value = true
  try {
    const runsRes = await getTrainRuns().catch(() => ({ runs: [] }))
    runs.value = sortRuns(runsRes?.runs || [])
    // 选中：优先持久化的 currentRunId；若该 run 已被删（stale）→ 回退到最新一条
    if (currentRunId.value) syncCurrent()
    if (!currentRun.value && runs.value.length) {
      selectRun(runs.value[0])
    }
    if (runs.value.some(isRunning)) startPolling()
  } catch (e) { message.error('加载失败') }
  loading.value = false
}

onMounted(load)
onUnmounted(stopPolling)
</script>

<style scoped lang="scss">
.train-results { display: flex; flex-direction: column; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.lbl { font-size: 13px; color: var(--color-text-secondary); }
.hint { font-size: 12px; color: var(--color-text-dim); }
.curve-card .curve-wrap { background: var(--color-elevated); border-radius: 8px; padding: 8px; }
.curve { height: 320px; width: 100%; }
.curve-placeholder { color: var(--color-text-dim); padding: 48px; text-align: center; font-size: 14px; }
</style>

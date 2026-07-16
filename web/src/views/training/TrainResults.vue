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

    <!-- 常驻 loss 曲线区（选 run -> 显示其 loss_series） -->
    <n-card size="small" class="curve-card">
      <template #header>
        <div class="flex-between">
          <h3>训练曲线</h3>
          <span class="hint">{{ curveTitle || '选择下方一条 run 查看其 loss/指标曲线' }}</span>
        </div>
      </template>
      <div v-if="curveOption" class="curve-wrap">
        <v-chart class="curve" :option="curveOption" autoresize />
      </div>
      <div v-else class="curve-placeholder">选择下方任意一条训练 run，loss/指标曲线将在此处显示</div>
    </n-card>

    <!-- 训练 run 列表 -->
    <n-card size="small" title="训练 run 列表" style="margin-top: 12px">
      <n-spin :show="loading">
        <n-data-table v-if="filteredRuns.length" :columns="runColumns" :data="filteredRuns" :bordered="false" size="small" striped />
        <EmptyState v-else description="暂无训练 run。在「训练运行」页启动训练后，run 列表 + loss 曲线在此。" />
      </n-spin>
    </n-card>

    <!-- checkpoint 文件列表 -->
    <n-card size="small" title="checkpoint 文件（trained .pth）" style="margin-top: 12px">
      <n-spin :show="cpLoading">
        <n-data-table v-if="checkpoints.length" :columns="cpColumns" :data="checkpoints" :bordered="false" size="small" striped />
        <EmptyState v-else description="暂无 trained checkpoint。训练产物在 results/training/checkpoints/。" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, h, watch } from 'vue'
import { NCard, NSpin, NSpace, NSelect, NButton, NDataTable, useMessage } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTrainRuns, listCheckpoints, getTrainOutputUrl } from '../../api/training'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const message = useMessage()
const loading = ref(false)
const cpLoading = ref(false)
const runs = ref([])
const checkpoints = ref([])
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
  if (r) currentRun.value = r
}

async function refreshCheckpoints() {
  cpLoading.value = true
  try {
    const cps = await listCheckpoints().catch(() => ({ checkpoints: [] }))
    checkpoints.value = cps?.checkpoints || []
  } finally { cpLoading.value = false }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    const res = await getTrainRuns().catch(() => null)
    if (res?.runs) {
      runs.value = sortRuns(res.runs)
      syncCurrent()
    }
    // 全部 run 结束：补刷一次 checkpoints（拿新 .pth），停轮询
    if (!runs.value.some(isRunning)) {
      stopPolling()
      refreshCheckpoints()
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

const curveTitle = computed(() => {
  const r = currentRun.value
  if (!r) return ''
  const tail = isRunning(r) ? ' · 训练中，实时刷新…' : ''
  return `${r.model} · ${r.dataset} · ${r.id}${tail}`
})

// 曲线 series 数据驱动：loss_series 里含哪个指标就画哪条
// （通用训练可能只有 loss；率失真等下游可能含 psnr/bpp）。
const curveOption = computed(() => {
  const r = currentRun.value
  if (!r || !r.loss_series?.length) return null
  const epochs = r.loss_series.map(p => p.epoch)
  const build = (key) => r.loss_series.map(p => p[key])
  const series = []
  if (r.loss_series.some(p => p.loss != null)) series.push({ name: 'loss', type: 'line', data: build('loss'), smooth: true })
  if (r.loss_series.some(p => p.psnr != null)) series.push({ name: 'PSNR(dB)', type: 'line', data: build('psnr'), smooth: true, yAxisIndex: 1 })
  if (r.loss_series.some(p => p.bpp != null)) series.push({ name: 'bpp', type: 'line', data: build('bpp'), smooth: true, yAxisIndex: 1 })
  if (!series.length) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name) },
    xAxis: { type: 'category', data: epochs, name: 'epoch' },
    yAxis: [{ type: 'value', name: 'loss' }, { type: 'value', name: '指标' }],
    series,
  }
})

const runColumns = computed(() => [
  { title: 'ID', key: 'id', width: 150 },
  { title: '模型', key: 'model' },
  { title: '数据集', key: 'dataset' },
  { title: 'epochs', key: 'epochs', width: 70 },
  { title: 'final_loss', key: 'final_loss', width: 90, render: (r) => fmt(r.final_loss) },
  { title: 'best_metric', key: 'best_metric', width: 100, render: (r) => fmt(r.best_metric) },
  { title: '状态', key: 'status', width: 80 },
  { title: '时间', key: 'started_at', render: (r) => r.started_at?.split('T')[0] || '-' },
  {
    title: '操作', key: 'actions', width: 110,
    render: (r) => h(NButton, { size: 'small', type: 'primary', secondary: true, onClick: () => selectRun(r) }, { default: () => '看曲线' }),
  },
])

const cpColumns = [
  { title: 'checkpoint', key: 'name' },
  { title: '大小', key: 'size_bytes', width: 100, render: (r) => fmtSize(r.size_bytes) },
  {
    title: '操作', key: 'actions', width: 160,
    render: (r) => h('div', { style: 'display:flex;gap:6px' }, [
      h(NButton, { size: 'small', secondary: true, onClick: () => copyUrl(r) }, { default: () => '复制路径' }),
      h(NButton, { size: 'small', type: 'primary', secondary: true, onClick: () => download(r) }, { default: () => '下载' }),
    ]),
  },
]

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

function copyUrl(cp) {
  const url = getTrainOutputUrl(cp.path)
  navigator.clipboard?.writeText(url)
  message.success(`已复制 checkpoint 服务路径: ${url}`)
}

function download(cp) {
  const a = document.createElement('a')
  a.href = getTrainOutputUrl(cp.path)
  a.download = cp.name
  a.click()
}

async function load() {
  loading.value = true
  cpLoading.value = true
  try {
    const [runsRes, cps] = await Promise.all([
      getTrainRuns().catch(() => ({ runs: [] })),
      listCheckpoints().catch(() => ({ checkpoints: [] })),
    ])
    runs.value = sortRuns(runsRes?.runs || [])
    checkpoints.value = cps?.checkpoints || []
    // 自动选中最新一条 run（开页面即可看到正在跑的曲线）
    if (!currentRunId.value && runs.value.length) {
      selectRun(runs.value[0])
    } else {
      syncCurrent()
    }
    if (runs.value.some(isRunning)) startPolling()
  } catch (e) { message.error('加载失败') }
  loading.value = false
  cpLoading.value = false
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

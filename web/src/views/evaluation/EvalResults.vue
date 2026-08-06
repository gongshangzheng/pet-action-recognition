<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>评测结果</h3>
          <n-space align="center">
            <n-select v-model:value="filters.model" :options="modelOptions" placeholder="全部模型" clearable size="small" style="width: 200px" />
            <n-select v-model:value="filters.dataset" :options="datasetOptions" placeholder="全部数据集" clearable size="small" style="width: 160px" />
            <n-button size="small" @click="load" :loading="loading">刷新</n-button>
          </n-space>
        </div>
      </template>
      <n-spin :show="loading">
        <template v-if="rawResults.length">
          <!-- 图表放最上方 -->
          <n-space vertical :size="12" style="margin-bottom: 16px">
            <n-space align="center">
              <span style="font-size: 13px; color: #666">对比指标：</span>
              <n-select v-model:value="chartMetric" :options="metricOptions" size="small" style="width: 160px" />
              <span style="font-size: 12px; color: #999">（每个模型仅取最新一次评测）</span>
            </n-space>
            <v-chart v-if="chartOption" class="result-chart" :option="chartOption" autoresize />
          </n-space>

          <n-divider />

          <n-data-table :columns="columns" :data="filteredResults" :bordered="false" size="small" striped />
        </template>
        <EmptyState v-else description="暂无评测数值结果；在「训练运行」页跑 POST /api/training/run_test 后这里显示 top1/top5 准确率" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { NCard, NSpin, NSpace, NSelect, NDataTable, NDivider, NButton } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTrainTestResults } from '../../api/training'
import { getModels } from '../../api/evaluation'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const rawResults = ref([])          // 原始全部结果（含历史重复）
const modelRegistry = ref([])        // 模型注册表
const filters = ref({ model: null, dataset: null })
const chartMetric = ref('top1_acc')

// 可切换的指标
const metricOptions = [
  { label: 'Top-1 Acc', value: 'top1_acc', unit: '%', max: 100, isPct: true },
  { label: 'Top-5 Acc', value: 'top5_acc', unit: '%', max: 100, isPct: true },
  { label: 'Mean-1 Acc', value: 'mean1_acc', unit: '%', max: 100, isPct: true },
  { label: '延迟 (ms)', value: 'latency_ms', unit: 'ms', max: null, isPct: false },
  { label: 'FPS', value: 'fps', unit: '', max: null, isPct: false },
  { label: 'RTF', value: 'rtf', unit: '', max: null, isPct: false },
  { label: 'GPU 显存 (MB)', value: 'gpu_mem_mb', unit: 'MB', max: null, isPct: false },
  { label: '参数量 (M)', value: 'param_count_m', unit: 'M', max: null, isPct: false },
  { label: '模型大小 (MB)', value: 'ckpt_size_mb', unit: 'MB', max: null, isPct: false },
]

// config 文件名 → 注册模型名；注册表没有则过滤掉训练参数 token，得到模型族名
const getModelDisplayName = (modelConfig) => {
  if (!modelConfig) return '-'
  const lower = modelConfig.toLowerCase()
  for (const reg of modelRegistry.value) {
    if (reg.id && lower.includes(reg.id.toLowerCase())) return reg.name
  }
  // fallback：按 -_ 切成 token，丢掉训练参数（8xb32 / 1x1x3 / 100e / kinetics400 / rgb / imagenet / r50 / pre / k400 ...）
  const tokens = modelConfig.replace(/\.py$/, '').split(/[-_]+/).filter(t => {
    if (!t) return false
    if (/^\d+e$/i.test(t)) return false                 // 100e / 256e
    if (/^\d+xb\d+/i.test(t)) return false              // 8xb32
    if (/^\d+x\d+x\d+$/.test(t)) return false           // 1x1x3
    if (/^\d+x\d+$/.test(t)) return false               // 8x8
    if (/^\d+$/.test(t)) return false                   // 纯数字 400
    if (/^(kinetics\w*|rgb|imagenet\w*|in1k\w*|ig65m|pretrained|pre|facebook|divst|dense|amp|k\w*)$/i.test(t)) return false
    if (/^r\d{2,3}$/i.test(t)) return false             // r50 / r152
    return true
  })
  return tokens.join('-') || modelConfig.replace(/\.py$/, '')
}

// 关键：每个 (模型, 数据集, split) 只保留最新一条
const dedupedResults = computed(() => {
  const map = new Map()
  for (const r of rawResults.value) {
    const key = `${getModelDisplayName(r.model)}|${r.dataset}|${r.split}`
    const prev = map.get(key)
    if (!prev || (r.finished_at || '') > (prev.finished_at || '')) {
      map.set(key, r)
    }
  }
  return [...map.values()]
})

const modelOptions = computed(() =>
  [...new Set(dedupedResults.value.map(r => getModelDisplayName(r.model)))]
    .map(m => ({ label: m, value: m }))
)
const datasetOptions = computed(() =>
  [...new Set(dedupedResults.value.map(r => r.dataset))].map(d => ({ label: d, value: d }))
)

const filteredResults = computed(() => {
  let list = dedupedResults.value
  if (filters.value.model) list = list.filter(r => getModelDisplayName(r.model) === filters.value.model)
  if (filters.value.dataset) list = list.filter(r => r.dataset === filters.value.dataset)
  return list
})

const pct = (v) => (v == null ? '-' : (v * 100).toFixed(2) + '%')
const fmtNum = (v, d = 1) => (v == null ? '-' : Number(v).toFixed(d))

const getMetricValue = (r, metric) => {
  const m = r.metrics || {}
  if (metric === 'top1_acc') return m.top1_acc
  if (metric === 'top5_acc') return m.top5_acc
  if (metric === 'mean1_acc') return m.mean1_acc
  return m.speed?.[metric]
}

const columns = computed(() => [
  {
    title: '模型', key: 'model', minWidth: 280,
    render: (r) => h('span', { title: r.model }, getModelDisplayName(r.model)),
    ellipsis: { tooltip: true },
  },
  { title: '数据集', key: 'dataset', width: 120 },
  { title: 'Split', key: 'split', width: 70 },
  { title: 'Top-1', key: 'top1', width: 75, render: (r) => pct(r.metrics?.top1_acc) },
  { title: 'Top-5', key: 'top5', width: 75, render: (r) => pct(r.metrics?.top5_acc) },
  { title: 'Mean-1', key: 'mean1', width: 80, render: (r) => pct(r.metrics?.mean1_acc) },
  { title: '延迟(ms)', key: 'lat', width: 80, render: (r) => fmtNum(r.metrics?.speed?.latency_ms) },
  { title: 'FPS', key: 'fps', width: 65, render: (r) => fmtNum(r.metrics?.speed?.fps) },
  { title: 'RTF', key: 'rtf', width: 60, render: (r) => fmtNum(r.metrics?.speed?.rtf, 3) },
  { title: 'GPU(MB)', key: 'gpumem', width: 80, render: (r) => fmtNum(r.metrics?.speed?.gpu_mem_mb) },
  { title: '参数(M)', key: 'params', width: 75, render: (r) => fmtNum(r.metrics?.speed?.param_count_m) },
  { title: 'ckpt(MB)', key: 'ckpt', width: 80, render: (r) => fmtNum(r.metrics?.speed?.ckpt_size_mb) },
  {
    title: '状态', key: 'status', width: 90,
    render: (r) => {
      if (r.status === 'completed') return h('span', { style: 'color: #18a058' }, '✓ 完成')
      if (r.status === 'error') {
        const tail = (r.stdout_tail || '无日志').slice(-500)
        return h('span', {
          style: 'color: #d03050; cursor: help; border-bottom: 1px dotted #d03050',
          title: tail,
        }, '✗ 错误')
      }
      return r.status
    },
  },
  { title: '时间', key: 'finished_at', width: 150, render: (r) => r.finished_at?.replace('T', ' ').slice(0, 19) || '-' },
])

const chartOption = computed(() => {
  if (!filteredResults.value.length) return null
  const models = [...new Set(filteredResults.value.map(r => getModelDisplayName(r.model)))]
  const datasets = [...new Set(filteredResults.value.map(r => r.dataset))]
  const opt = metricOptions.find(o => o.value === chartMetric.value)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: models, type: 'scroll', left: 10, right: 10, top: 0 },
    grid: { top: 40, left: 50, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: datasets },
    yAxis: {
      type: 'value',
      name: opt?.label || '',
      max: opt?.max || undefined,
    },
    series: models.map(m => ({
      name: m,
      type: 'bar',
      data: datasets.map(d => {
        const r = filteredResults.value.find(x => getModelDisplayName(x.model) === m && x.dataset === d)
        const v = r ? getMetricValue(r, chartMetric.value) : null
        if (v == null) return 0
        return opt?.isPct ? +(v * 100).toFixed(2) : +Number(v).toFixed(2)
      }),
    })),
  }
})

async function load() {
  loading.value = true
  try {
    const [testData, modelsData] = await Promise.all([
      getTrainTestResults(),
      getModels(),
    ])
    rawResults.value = testData.results || []
    modelRegistry.value = modelsData || []
  } catch {
    rawResults.value = []
  }
  loading.value = false
}
onMounted(load)
</script>

<style scoped>
.result-chart { height: 350px; width: 100%; }
</style>

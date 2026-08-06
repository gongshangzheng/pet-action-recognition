<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>评测结果</h3>
          <n-space align="center">
            <n-select v-model:value="filters.model" :options="modelOptions" placeholder="全部模型" clearable size="small" style="width: 180px" />
            <n-select v-model:value="filters.dataset" :options="datasetOptions" placeholder="全部数据集" clearable size="small" style="width: 160px" />
            <n-button size="small" @click="load" :loading="loading">刷新</n-button>
          </n-space>
        </div>
      </template>
      <n-spin :show="loading">
        <template v-if="results.length">
          <!-- 图表放最上方 -->
          <n-space vertical :size="12" style="margin-bottom: 16px">
            <n-space align="center">
              <span style="font-size: 13px; color: #666">对比指标：</span>
              <n-select v-model:value="chartMetric" :options="metricOptions" size="small" style="width: 140px" />
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

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const results = ref([])
const filters = ref({ model: null, dataset: null })
const chartMetric = ref('top1_acc')

// 可切换的指标
const metricOptions = [
  { label: 'Top-1 Acc', value: 'top1_acc', unit: '%', max: 100 },
  { label: 'Top-5 Acc', value: 'top5_acc', unit: '%', max: 100 },
  { label: 'Mean-1 Acc', value: 'mean1_acc', unit: '%', max: 100 },
  { label: '延迟 (ms)', value: 'latency_ms', unit: 'ms', max: null },
  { label: 'FPS', value: 'fps', unit: '', max: null },
  { label: 'RTF', value: 'rtf', unit: '', max: null },
  { label: 'GPU 显存 (MB)', value: 'gpu_mem_mb', unit: 'MB', max: null },
  { label: '参数量 (M)', value: 'param_count_m', unit: 'M', max: null },
  { label: '模型大小 (MB)', value: 'ckpt_size_mb', unit: 'MB', max: null },
]

const modelOptions = computed(() => [...new Set(results.value.map(r => r.model))].map(m => ({ label: m, value: m })))
const datasetOptions = computed(() => [...new Set(results.value.map(r => r.dataset))].map(d => ({ label: d, value: d })))

const filteredResults = computed(() => {
  let list = results.value
  if (filters.value.model) list = list.filter(r => r.model === filters.value.model)
  if (filters.value.dataset) list = list.filter(r => r.dataset === filters.value.dataset)
  return list
})

const pct = (v) => (v == null ? '-' : (v * 100).toFixed(2) + '%')
const fmtNum = (v, d = 1) => (v == null ? '-' : Number(v).toFixed(d))

const getMetricValue = (r, metric) => {
  const m = r.metrics || {}
  switch (metric) {
    case 'top1_acc': return m.top1_acc
    case 'top5_acc': return m.top5_acc
    case 'mean1_acc': return m.mean1_acc
    case 'latency_ms': return m.speed?.latency_ms
    case 'fps': return m.speed?.fps
    case 'rtf': return m.speed?.rtf
    case 'gpu_mem_mb': return m.speed?.gpu_mem_mb
    case 'param_count_m': return m.speed?.param_count_m
    case 'ckpt_size_mb': return m.speed?.ckpt_size_mb
    default: return null
  }
}

const fmtMetric = (v, metric) => {
  if (v == null) return '-'
  const opt = metricOptions.find(o => o.value === metric)
  if (['top1_acc', 'top5_acc', 'mean1_acc'].includes(metric)) {
    return (v * 100).toFixed(2) + '%'
  }
  return Number(v).toFixed(opt?.value.includes('rtf') ? 3 : 1)
}

const columns = computed(() => [
  { title: '模型', key: 'model', minWidth: 280, ellipsis: { tooltip: true } },
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
    title: '状态', key: 'status', width: 120,
    render: (r) => {
      if (r.status === 'completed') return h('span', { style: 'color: #18a058' }, '✓ 完成')
      if (r.status === 'error') return h('span', { style: 'color: #d03050' }, [
        '✗ 错误',
        r.error ? h('n-tooltip', { style: 'max-width: 300px' }, {
          default: () => '?',
          trigger: () => h('n-tag', { size: 'small', type: 'error', style: 'margin-left: 4px' }, { default: () => '详情' })
        })
      ])
      return r.status
    }
  },
  { title: '时间', key: 'finished_at', width: 150, render: (r) => r.finished_at?.replace('T', ' ').slice(0, 19) || '-' },
])

const chartOption = computed(() => {
  if (!filteredResults.value.length) return null
  const models = [...new Set(filteredResults.value.map(r => r.model))]
  const datasets = [...new Set(filteredResults.value.map(r => r.dataset))]
  const opt = metricOptions.find(o => o.value === chartMetric.value)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: models, type: 'scroll', left: 10, right: 10 },
    xAxis: { type: 'category', data: datasets },
    yAxis: {
      type: 'value',
      name: opt?.label || '',
      max: opt?.max || undefined,
      axisLabel: { formatter: (v) => opt?.unit ? v + opt.unit : v }
    },
    series: models.map(m => ({
      name: m,
      type: 'bar',
      data: datasets.map(d => {
        const r = filteredResults.value.find(x => x.model === m && x.dataset === d)
        const v = r ? getMetricValue(r, chartMetric.value) : null
        return v != null ? (['top1_acc', 'top5_acc', 'mean1_acc'].includes(chartMetric.value) ? +(v * 100).toFixed(2) : +v.toFixed(2)) : 0
      }),
    })),
  }
})

async function load() {
  loading.value = true
  try {
    const d = await getTrainTestResults()
    results.value = d.results || []
  } catch { results.value = [] }
  loading.value = false
}
onMounted(load)
</script>

<style scoped>
.result-chart { height: 350px; width: 100%; }
</style>

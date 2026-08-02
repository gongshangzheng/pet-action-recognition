<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>评测结果（数值）</h3>
          <n-space align="center">
            <n-select v-model:value="filters.model" :options="modelOptions" placeholder="全部模型" clearable size="small" style="width: 180px" />
            <n-select v-model:value="filters.dataset" :options="datasetOptions" placeholder="全部数据集" clearable size="small" style="width: 160px" />
            <n-button size="small" @click="load" :loading="loading">刷新</n-button>
          </n-space>
        </div>
      </template>
      <n-spin :show="loading">
        <template v-if="results.length">
          <n-data-table :columns="columns" :data="filteredResults" :bordered="false" size="small" striped />

          <n-divider />

          <h4>模型对比（Top-1 Acc）</h4>
          <v-chart v-if="chartOption" class="result-chart" :option="chartOption" autoresize />
        </template>
        <EmptyState v-else description="暂无评测数值结果；在「训练运行」页跑 POST /api/training/run_test 后这里显示 top1/top5 准确率" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
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

const columns = computed(() => [
  { title: '模型', key: 'model', minWidth: 220, ellipsis: { tooltip: true } },
  { title: '数据集', key: 'dataset', width: 140 },
  { title: 'Split', key: 'split', width: 80 },
  { title: 'Top-1', key: 'top1', width: 80, render: (r) => pct(r.metrics?.top1_acc) },
  { title: 'Top-5', key: 'top5', width: 80, render: (r) => pct(r.metrics?.top5_acc) },
  { title: 'Mean-1', key: 'mean1', width: 85, render: (r) => pct(r.metrics?.mean1_acc), title: 'per-class 平均 top1' },
  { title: '延迟(ms)', key: 'lat', width: 85, render: (r) => fmtNum(r.metrics?.speed?.latency_ms) },
  { title: 'FPS', key: 'fps', width: 70, render: (r) => fmtNum(r.metrics?.speed?.fps) },
  { title: 'RTF', key: 'rtf', width: 65, render: (r) => fmtNum(r.metrics?.speed?.rtf, 3) },
  { title: 'GPU(MB)', key: 'gpumem', width: 85, render: (r) => fmtNum(r.metrics?.speed?.gpu_mem_mb) },
  { title: '参数(M)', key: 'params', width: 80, render: (r) => fmtNum(r.metrics?.speed?.param_count_m) },
  { title: 'ckpt(MB)', key: 'ckpt', width: 85, render: (r) => fmtNum(r.metrics?.speed?.ckpt_size_mb) },
  {
    title: '状态', key: 'status', width: 100,
    render: (r) => r.status === 'completed' ? '✓ 完成' : r.status === 'error' ? '✗ 错误' : r.status,
  },
  { title: '时间', key: 'finished_at', width: 160, render: (r) => r.finished_at?.replace('T', ' ').slice(0, 19) || '-' },
])

const chartOption = computed(() => {
  if (!filteredResults.value.length) return null
  const models = [...new Set(filteredResults.value.map(r => r.model))]
  const datasets = [...new Set(filteredResults.value.map(r => r.dataset))]
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: models },
    xAxis: { type: 'category', data: datasets },
    yAxis: { type: 'value', name: 'Top-1 Acc (%)', max: 100 },
    series: models.map(m => ({
      name: m,
      type: 'bar',
      data: datasets.map(d => {
        const r = filteredResults.value.find(x => x.model === m && x.dataset === d)
        return r?.metrics?.top1_acc != null ? +(r.metrics.top1_acc * 100).toFixed(2) : 0
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
.result-chart { height: 400px; width: 100%; }
</style>

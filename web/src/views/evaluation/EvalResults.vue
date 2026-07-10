<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>评测结果</h3>
          <n-space align="center">
            <n-select v-model:value="filters.model" :options="modelOptions" placeholder="全部模型" clearable size="small" style="width: 160px" />
            <n-select v-model:value="filters.dataset" :options="datasetOptions" placeholder="全部数据集" clearable size="small" style="width: 160px" />
          </n-space>
        </div>
      </template>
      <n-spin :show="loading">
        <template v-if="results.length">
          <n-data-table :columns="columns" :data="filteredResults" :bordered="false" size="small" striped />

          <n-divider />

          <h4>模型对比图表</h4>
          <v-chart v-if="chartOption" class="result-chart" :option="chartOption" autoresize />
        </template>
        <EmptyState v-else description="暂无评测结果，可在评测运行页面启动评测" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { NCard, NSpin, NSpace, NSelect, NDataTable, NDivider } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import EmptyState from '../../components/common/EmptyState.vue'
import { getEvalResults } from '../../api/evaluation'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(false)
const results = ref([])
const filters = ref({ model: null, dataset: null })

const modelOptions = computed(() => [...new Set(results.value.map(r => r.model_name))].map(m => ({ label: m, value: m })))
const datasetOptions = computed(() => [...new Set(results.value.map(r => r.dataset_name))].map(d => ({ label: d, value: d })))

const filteredResults = computed(() => {
  let list = results.value
  if (filters.value.model) list = list.filter(r => r.model_name === filters.value.model)
  if (filters.value.dataset) list = list.filter(r => r.dataset_name === filters.value.dataset)
  return list
})

const columns = computed(() => {
  if (!results.value.length) return []
  const metricKeys = Object.keys(results.value[0].metrics || {})
  return [
    { title: '模型', key: 'model_name' },
    { title: '数据集', key: 'dataset_name' },
    ...metricKeys.map(k => ({
      title: k,
      key: `metrics.${k}`,
      render: (row) => row.metrics?.[k]?.toFixed(2) ?? '-',
    })),
    { title: '时间', key: 'timestamp', render: (row) => row.timestamp?.split('T')[0] || '-' },
  ]
})

const chartOption = computed(() => {
  if (!filteredResults.value.length) return null
  const modelNames = [...new Set(filteredResults.value.map(r => r.model_name))]
  const metricKey = Object.keys(filteredResults.value[0].metrics || {})[0]
  if (!metricKey) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: modelNames },
    xAxis: { type: 'category', data: [...new Set(filteredResults.value.map(r => r.dataset_name))] },
    yAxis: { type: 'value', name: metricKey },
    series: modelNames.map(mn => ({
      name: mn,
      type: 'bar',
      data: filteredResults.value.filter(r => r.model_name === mn).map(r => r.metrics?.[metricKey] || 0),
    })),
  }
})

onMounted(async () => {
  loading.value = true
  try { results.value = await getEvalResults() } catch { results.value = [] }
  loading.value = false
})
</script>

<style scoped>
.result-chart { height: 400px; width: 100%; }
</style>

<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <n-space align="center" size="small">
            <n-button size="small" quaternary @click="$router.push('/training/results')">← 返回</n-button>
            <h3>{{ run?.id || 'Run 详情' }}</h3>
            <n-tag v-if="run" :type="statusType" size="small">{{ run.status }}</n-tag>
            <n-tag v-if="isRunning" type="info" size="small">实时刷新中…</n-tag>
          </n-space>
          <n-button size="small" @click="load" :loading="loading">刷新</n-button>
        </div>
      </template>

      <n-spin :show="loading">
        <div v-if="run">
          <!-- 元信息 -->
          <n-descriptions :column="4" size="small" label-placement="left" bordered>
            <n-descriptions-item label="模型">{{ run.model }}</n-descriptions-item>
            <n-descriptions-item label="数据集">{{ run.dataset }}</n-descriptions-item>
            <n-descriptions-item label="Epochs">{{ run.epochs }}</n-descriptions-item>
            <n-descriptions-item label="LR">{{ fmt(run.lr) }}</n-descriptions-item>
            <n-descriptions-item label="Batch Size">{{ run.batch_size }}</n-descriptions-item>
            <n-descriptions-item label="Device">{{ run.device }}</n-descriptions-item>
            <n-descriptions-item label="开始">{{ fmtTime(run.started_at) }}</n-descriptions-item>
            <n-descriptions-item label="模式">
              <span v-if="run.pretrained">pretrained finetune</span>
              <span v-else-if="run.load_from">load_from {{ run.load_from }}</span>
              <span v-else-if="run.resumed_at">resume</span>
              <span v-else-if="run.from_scratch">from scratch</span>
              <span v-else>default</span>
            </n-descriptions-item>
            <n-descriptions-item v-if="run.final_loss != null" label="Final Loss">{{ fmt(run.final_loss) }}</n-descriptions-item>
            <n-descriptions-item v-if="run.best_metric != null" label="Best Metric">{{ fmt(run.best_metric) }}</n-descriptions-item>
          </n-descriptions>

          <!-- Checkpoint 链接 -->
          <div v-if="run.checkpoint_path || run.best_checkpoint_path" style="margin-top: 12px">
            <h4>Checkpoint</h4>
            <n-space size="small">
              <n-tag v-if="run.checkpoint_path" size="small" :bordered="false">
                latest: {{ run.checkpoint_path }}
              </n-tag>
              <n-tag v-if="run.best_checkpoint_path" size="small" type="success" :bordered="false">
                best: {{ run.best_checkpoint_path }}
              </n-tag>
            </n-space>
          </div>
        </div>
        <EmptyState v-else description="Run 不存在或尚未加载" />
      </n-spin>
    </n-card>

    <!-- TensorBoard 风格曲线 -->
    <n-card v-if="lossChart || accChart || lrChart" size="small" style="margin-top: 12px" title="训练曲线">
      <div v-if="lossChart" class="chart-block">
        <div class="chart-title">Loss</div>
        <v-chart class="chart" :option="lossChart" autoresize />
      </div>
      <div v-if="accChart" class="chart-block">
        <div class="chart-title">Accuracy</div>
        <v-chart class="chart" :option="accChart" autoresize />
      </div>
      <div v-if="lrChart" class="chart-block">
        <div class="chart-title">Learning Rate</div>
        <v-chart class="chart" :option="lrChart" autoresize />
      </div>
    </n-card>

    <!-- 可视化样本 -->
    <n-card v-if="visSamples.length" size="small" style="margin-top: 12px" title="可视化样本（val 预测）">
      <div class="vis-grid">
        <div v-for="s in visSamples" :key="s.idx" class="vis-item" @click="previewVis(s)">
          <img :src="getVisSampleUrl('work_dirs/' + runId + '/vis_samples/' + s.file)" class="vis-img" loading="lazy" />
          <div class="vis-meta">
            <span :class="s.correct ? 'vis-ok' : 'vis-err'">{{ s.correct ? '✓' : '✗' }}</span>
            <span class="vis-gt">GT: {{ s.gt_label }}</span>
            <span class="vis-pred">pred: {{ s.pred_label }} ({{ s.score }})</span>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 大图预览 -->
    <n-modal v-model:show="visPreviewShow" preset="card" :title="visPreviewTitle" style="max-width: 600px">
      <img :src="visPreviewSrc" style="width: 100%" />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { NCard, NSpin, NSpace, NButton, NTag, NDescriptions, NDescriptionsItem, NModal } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTrainRunDetail, listVisSamples, getVisSampleUrl } from '../../api/training'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

const route = useRoute()
const runId = route.params.run_id
const loading = ref(false)
const run = ref(null)
const visSamples = ref([])
let pollTimer = null

const visPreviewShow = ref(false)
const visPreviewSrc = ref('')
const visPreviewTitle = ref('')

function previewVis(s) {
  visPreviewSrc.value = getVisSampleUrl('work_dirs/' + runId + '/vis_samples/' + s.file)
  visPreviewTitle.value = `${s.correct ? '✓' : '✗'} GT: ${s.gt_label} → pred: ${s.pred_label} (${s.score})`
  visPreviewShow.value = true
}

const isRunning = computed(() => ['running', 'started'].includes(run.value?.status))
const statusType = computed(() => {
  const s = run.value?.status
  if (s === 'completed') return 'success'
  if (s === 'error') return 'error'
  return 'info'
})

function fmt(v) { return (v == null || isNaN(v)) ? '-' : Number(v).toFixed(4) }
function fmtTime(t) { return t ? t.replace('T', ' ').slice(0, 19) : '-' }

// 从 loss_series 构建 ECharts option
function buildChart(seriesData, seriesNames, yName) {
  if (!seriesData.length) return null
  const epochs = seriesData.map(p => p.epoch)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: seriesNames, top: 0 },
    grid: { top: 30, left: 50, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: epochs, name: 'epoch' },
    yAxis: { type: 'value', name: yName },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: seriesNames.map((name, i) => ({
      name, type: 'line', data: seriesData.map(p => p[name] ?? p[Object.keys(p).find(k => k.toLowerCase().includes(name.toLowerCase().replace('_acc', '').replace('top', '')))] ?? null),
      smooth: true, showSymbol: true, symbolSize: 5,
    })),
  }
}

const lossChart = computed(() => {
  const s = run.value?.loss_series
  if (!s?.length || !s.some(p => p.loss != null)) return null
  return buildChart(s, ['loss'], 'loss')
})

const accChart = computed(() => {
  const s = run.value?.loss_series
  if (!s?.length) return null
  const names = []
  if (s.some(p => p.top1_acc != null)) names.push('top1_acc')
  if (s.some(p => p.top5_acc != null)) names.push('top5_acc')
  if (!names.length) return null
  const epochs = s.map(p => p.epoch)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: names, top: 0 },
    grid: { top: 30, left: 50, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: epochs, name: 'epoch' },
    yAxis: { type: 'value', name: 'accuracy', max: 1 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: names.map(name => ({
      name, type: 'line', data: s.map(p => p[name] ?? null),
      smooth: true, showSymbol: true, symbolSize: 5,
    })),
  }
})

const lrChart = computed(() => {
  const s = run.value?.loss_series
  if (!s?.length || !s.some(p => p.lr != null)) return null
  const epochs = s.map(p => p.epoch)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 10, left: 50, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: epochs, name: 'epoch' },
    yAxis: { type: 'value', name: 'lr' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: [{ name: 'lr', type: 'line', data: s.map(p => p.lr), smooth: true, showSymbol: false }],
  }
})

async function load() {
  loading.value = true
  try { run.value = await getTrainRunDetail(runId) } catch { run.value = null }
  loading.value = false
  loadVis()
  if (isRunning.value) startPoll()
  else stopPoll()
}

async function loadVis() {
  try {
    const d = await listVisSamples(runId)
    visSamples.value = d.samples || []
  } catch { visSamples.value = [] }
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    try { run.value = await getTrainRunDetail(runId) } catch {}
    if (!isRunning.value) { stopPoll(); loadVis() }
    else loadVis()
  }, 3000)
}
function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

onMounted(load)
onUnmounted(stopPoll)
</script>

<style scoped>
.page-container { padding: 16px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.chart-block { margin-bottom: 16px; }
.chart-block:last-child { margin-bottom: 0; }
.chart-title { font-weight: 600; font-size: 13px; color: #6b7280; margin-bottom: 4px; }
.chart { height: 200px; width: 100%; }
.vis-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.vis-item { border: 1px solid rgba(128,128,128,0.2); border-radius: 6px; overflow: hidden; cursor: pointer; }
.vis-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.vis-img { width: 100%; height: 140px; object-fit: cover; display: block; }
.vis-meta { padding: 4px 6px; font-size: 11px; display: flex; flex-direction: column; gap: 1px; }
.vis-ok { color: #18a058; font-weight: bold; }
.vis-err { color: #d03050; font-weight: bold; }
.vis-gt { color: #6b7280; }
.vis-pred { color: #9ca3af; }
</style>

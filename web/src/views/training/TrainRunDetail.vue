<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <n-space align="center" size="small">
            <n-button size="small" quaternary @click="$router.push('/training/results')">← 返回</n-button>
            <h3>{{ run?.name || run?.id || '进程详情' }}</h3>
            <span v-if="run?.description" style="font-size: 12px; color: #9ca3af">{{ run.description }}</span>
            <n-tag v-if="run" :type="statusType" size="small">{{ run.status }}</n-tag>
            <n-tag v-if="isRunning" type="info" size="small">实时刷新中…</n-tag>
          </n-space>
          <n-button size="small" @click="load" :loading="loading">刷新</n-button>
        </div>
      </template>

      <n-spin :show="loading">
        <div v-if="run">
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
            <n-descriptions-item v-if="run.advanced" label="高级超参">
              <span style="font-size: 12px; color: #9ca3af">{{ JSON.stringify(run.advanced) }}</span>
            </n-descriptions-item>
          </n-descriptions>

          <div v-if="run.checkpoint_path || run.best_checkpoint_path" style="margin-top: 12px">
            <h4>Checkpoint</h4>
            <n-space size="small">
              <n-tag v-if="run.checkpoint_path" size="small" :bordered="false">latest: {{ run.checkpoint_path }}</n-tag>
              <n-tag v-if="run.best_checkpoint_path" size="small" type="success" :bordered="false">best: {{ run.best_checkpoint_path }}</n-tag>
            </n-space>
          </div>
        </div>
        <EmptyState v-else description="Run 不存在或尚未加载" />
      </n-spin>
    </n-card>

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

    <!-- 可视化样本：epoch 网格 + 点击展开详情 -->
    <n-card v-if="visGroups.length" size="small" style="margin-top: 12px" title="可视化样本">
      <div class="epoch-grid">
        <div
          v-for="group in visGroups"
          :key="group.epoch"
          :class="['epoch-cell', { active: selectedEpoch === group.epoch }]"
          @click="selectedEpoch = group.epoch"
        >
          <div class="epoch-cell-thumb">
            <img v-if="group.samples[0]" :src="group.samples[0].url" loading="lazy" />
          </div>
          <div class="epoch-cell-meta">
            <span class="epoch-num">Ep {{ group.epoch }}</span>
            <span :class="visGroupCorrect(group) === group.samples.length ? 'vis-all-ok' : ''">{{ visGroupCorrect(group) }}/{{ group.samples.length }}</span>
          </div>
        </div>
      </div>

      <!-- 选中 epoch 的详情（左右切换） -->
      <n-card v-if="selectedEpoch !== null && selectedGroup" size="small" :bordered="true" style="margin-top: 12px">
        <template #header>
          Epoch {{ selectedEpoch }}
          ({{ visGroupCorrect(selectedGroup) }}/{{ selectedGroup.samples.length }} correct)
        </template>
        <div class="vis-card-inner">
          <button class="vis-nav vis-prev" :disabled="visIndex[selectedEpoch] === 0" @click="switchVis(selectedEpoch, -1)">◀</button>
          <div class="vis-main" v-if="selectedGroup.samples[visIndex[selectedEpoch]]">
            <img :src="selectedGroup.samples[visIndex[selectedEpoch]].url" class="vis-big-img" loading="lazy" />
            <div class="vis-info">
              <span :class="selectedGroup.samples[visIndex[selectedEpoch]].correct ? 'vis-ok' : 'vis-err'">{{ selectedGroup.samples[visIndex[selectedEpoch]].correct ? 'OK' : 'WRONG' }}</span>
              <span class="vis-gt">GT: {{ selectedGroup.samples[visIndex[selectedEpoch]].gt_label }}</span>
              <span class="vis-pred">pred: {{ selectedGroup.samples[visIndex[selectedEpoch]].pred_label }} ({{ selectedGroup.samples[visIndex[selectedEpoch]].score }})</span>
              <span class="vis-idx">{{ visIndex[selectedEpoch] + 1 }}/{{ selectedGroup.samples.length }}</span>
            </div>
          </div>
          <button class="vis-nav vis-next" :disabled="visIndex[selectedEpoch] >= selectedGroup.samples.length - 1" @click="switchVis(selectedEpoch, 1)">▶</button>
        </div>
        <div class="vis-thumbs">
          <div
            v-for="(s, i) in selectedGroup.samples"
            :key="s.idx"
            :class="['vis-thumb', { active: i === visIndex[selectedEpoch] }]"
            @click="visIndex[selectedEpoch] = i"
          >
            <img :src="s.url" loading="lazy" />
          </div>
        </div>
      </n-card>
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { NCard, NSpin, NSpace, NButton, NTag, NDescriptions, NDescriptionsItem } from 'naive-ui'
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
const visGroups = ref([])
const visIndex = reactive({})
const selectedEpoch = ref(null)
let pollTimer = null

const selectedGroup = computed(() => visGroups.value.find(g => g.epoch === selectedEpoch.value) || null)

const isRunning = computed(() => ['running', 'started'].includes(run.value?.status))
const statusType = computed(() => {
  const s = run.value?.status
  if (s === 'completed') return 'success'
  if (s === 'error') return 'error'
  return 'info'
})

function fmt(v) { return (v == null || isNaN(v)) ? '-' : Number(v).toFixed(4) }
function fmtTime(t) { return t ? t.replace('T', ' ').slice(0, 19) : '-' }

function visGroupCorrect(group) {
  return group.samples.filter(s => s.correct).length
}
function switchVis(epoch, dir) {
  const i = visIndex[epoch] ?? 0
  visIndex[epoch] = Math.max(0, Math.min((visGroups.value.find(g => g.epoch === epoch)?.samples.length || 1) - 1, i + dir))
}

const lossChart = computed(() => {
  const s = run.value?.loss_series
  if (!s?.length || !s.some(p => p.loss != null)) return null
  const epochs = s.map(p => p.epoch)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['loss'], top: 0 },
    grid: { top: 30, left: 50, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: epochs, name: 'epoch' },
    yAxis: { type: 'value', name: 'loss' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: [{ name: 'loss', type: 'line', data: s.map(p => p.loss), smooth: true, showSymbol: true, symbolSize: 5 }],
  }
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
    series: names.map(name => ({ name, type: 'line', data: s.map(p => p[name] ?? null), smooth: true, showSymbol: true, symbolSize: 5 })),
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
  try {
    const d = await getTrainRunDetail(runId)
    lastRunJson = JSON.stringify(d)
    run.value = d
  } catch { run.value = null }
  loading.value = false
  loadVis()
  if (isRunning.value) startPoll()
  else stopPoll()
}

async function loadVis() {
  try {
    const d = await listVisSamples(runId)
    visGroups.value = d.groups || []
    visGroups.value.forEach(g => { if (visIndex[g.epoch] == null) visIndex[g.epoch] = 0 })
    if (selectedEpoch.value === null && visGroups.value.length) {
      selectedEpoch.value = visGroups.value[0].epoch
    }
  } catch { visGroups.value = [] }
}

let lastRunJson = ''
function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    try {
      const d = await getTrainRunDetail(runId)
      // 数据没变 → 跳过响应式更新，避免详情面板/曲线每 3s 重渲染
      const json = JSON.stringify(d)
      if (json !== lastRunJson) {
        lastRunJson = json
        run.value = d
      }
    } catch {}
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
.vis-card-inner { display: flex; align-items: center; gap: 12px; }
.vis-nav { border: none; background: rgba(128,128,128,0.1); border-radius: 6px; width: 36px; height: 36px; cursor: pointer; font-size: 14px; color: #6b7280; flex-shrink: 0; }
.vis-nav:hover:not(:disabled) { background: rgba(128,128,128,0.2); }
.vis-nav:disabled { opacity: 0.3; cursor: default; }
.vis-main { flex: 1; text-align: center; }
.vis-big-img { max-width: 100%; max-height: 300px; border-radius: 6px; display: block; margin: 0 auto 8px; }
.vis-info { font-size: 12px; display: flex; justify-content: center; gap: 12px; align-items: center; }
.vis-ok { color: #18a058; font-weight: bold; }
.vis-err { color: #d03050; font-weight: bold; }
.vis-gt { color: #6b7280; }
.vis-pred { color: #9ca3af; }
.vis-idx { color: #9ca3af; margin-left: auto; }
.vis-all-ok { color: #18a058; }
.vis-thumbs { display: flex; gap: 6px; margin-top: 10px; overflow-x: auto; }
.vis-thumb { width: 60px; height: 45px; border: 2px solid transparent; border-radius: 4px; overflow: hidden; cursor: pointer; flex-shrink: 0; }
.vis-thumb.active { border-color: #2563eb; }
.vis-thumb img { width: 100%; height: 100%; object-fit: cover; }
.epoch-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); gap: 8px; }
.epoch-cell { border: 2px solid transparent; border-radius: 6px; overflow: hidden; cursor: pointer; background: rgba(128,128,128,0.06); }
.epoch-cell:hover { background: rgba(128,128,128,0.12); }
.epoch-cell.active { border-color: #2563eb; }
.epoch-cell-thumb { height: 60px; overflow: hidden; }
.epoch-cell-thumb img { width: 100%; height: 100%; object-fit: cover; }
.epoch-cell-meta { padding: 3px 4px; font-size: 11px; display: flex; justify-content: space-between; color: #6b7280; }
.epoch-num { font-weight: 600; }
</style>

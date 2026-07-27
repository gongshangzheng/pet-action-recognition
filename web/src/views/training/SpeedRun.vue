<template>
  <div class="page-container">
    <n-card title="Speed Run — 视频×模型 → 标注视频" size="small">
      <n-spin :show="loading">
        <n-form :model="form" label-placement="left" :label-width="90" style="max-width: 760px">
          <n-form-item label="视频路径" required>
            <n-input
              v-model:value="form.videosText"
              type="textarea"
              :rows="3"
              placeholder="每行一个视频路径（相对仓库根或绝对），如&#10;models/mmaction2/demo/demo.mp4&#10;datasets/ucf101/videos/PlayingGuitar/xxx.avi"
            />
          </n-form-item>
          <n-form-item label="模型">
            <n-space align="center" style="width: 100%">
              <n-select
                v-model:value="form.models"
                multiple
                :options="modelOptions"
                placeholder="选择模型（留空=全部）"
                style="flex: 1; min-width: 360px"
                filterable
              />
              <n-checkbox v-model:checked="allModels">全部</n-checkbox>
            </n-space>
          </n-form-item>
          <n-form-item label="设备">
            <n-radio-group v-model:value="form.device">
              <n-radio value="cuda:0">GPU (cuda:0)</n-radio>
              <n-radio value="cpu">CPU</n-radio>
            </n-radio-group>
          </n-form-item>
          <n-form-item label="选项">
            <n-checkbox v-model:checked="form.force">强制重跑（覆盖已有）</n-checkbox>
          </n-form-item>
          <n-form-item label=" ">
            <n-button type="primary" :loading="running" :disabled="!videos.length" @click="handleRun">
              启动 Speed Run
            </n-button>
            <n-tag v-if="status.running" type="info" style="margin-left: 12px">运行中 · 已出 {{ status.results_count }} 条</n-tag>
            <n-tag v-else-if="lastRunId" type="success" style="margin-left: 12px">已完成 · {{ status.results_count }} 条</n-tag>
          </n-form-item>
        </n-form>
      </n-spin>
    </n-card>

    <n-card title="结果" size="small" style="margin-top: 16px">
      <n-space style="margin-bottom: 8px">
        <n-button size="small" @click="refreshResults" :loading="loading">刷新</n-button>
        <n-text depth="3">{{ results.length }} 条结果 · {{ generatedAt }}</n-text>
      </n-space>
      <n-data-table
        :columns="resultColumns"
        :data="results"
        :pagination="{ pageSize: 20 }"
        size="small"
        :row-key="row => row.id"
      />
    </n-card>

    <VideoModal v-model:show="videoShow" :src="videoSrc" :title="videoTitle" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { h } from 'vue'
import { NButton, NTag } from 'naive-ui'
import {
  getTrainModels,
  speedRun,
  getSpeedrunStatus,
  getSpeedrunResults,
  getSpeedrunOutputUrl,
} from '@/api/training'
import VideoModal from '@/components/common/VideoModal.vue'

const loading = ref(false)
const running = ref(false)
const lastRunId = ref('')
const results = ref([])
const generatedAt = ref('')
const status = reactive({ running: false, results_count: 0 })
const modelOptions = ref([])

const form = reactive({
  videosText: 'models/mmaction2/demo/demo.mp4',
  models: [],
  device: 'cuda:0',
  force: false,
})
const allModels = ref(true)

const videos = computed(() =>
  form.videosText.split('\n').map(s => s.trim()).filter(Boolean)
)

watch(allModels, (v) => {
  form.models = v ? [] : form.models
})

const videoShow = ref(false)
const videoSrc = ref('')
const videoTitle = ref('')

function playVideo(path, title) {
  videoSrc.value = getSpeedrunOutputUrl(path)
  videoTitle.value = title
  videoShow.value = true
}

const resultColumns = [
  { title: '模型', key: 'model_id', width: 180 },
  { title: '视频', key: 'video', ellipsis: { tooltip: true }, minWidth: 220 },
  {
    title: 'Top-1',
    key: 'metrics',
    width: 200,
    render: (row) => {
      const m = row.metrics || {}
      return m.top1_label ? `${m.top1_label} (${(m.top1_score ?? 0).toFixed(2)})` : '—'
    },
  },
  {
    title: 'Top-5',
    key: 'top5',
    render: (row) => {
      const top5 = row.metrics?.top5 || []
      return top5.map(([label, score], i) =>
        h(NTag, { size: 'small', type: i === 0 ? 'success' : 'default', style: 'margin: 2px' },
          () => `${label} ${score.toFixed(2)}`)
      )
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) =>
      h(NTag, { size: 'small', type: row.status === 'completed' ? 'success' : row.status === 'error' ? 'error' : 'warning' },
        () => row.status),
  },
  {
    title: '视频',
    key: 'output_video',
    width: 90,
    render: (row) =>
      row.output_video
        ? h(NButton, { size: 'small', onClick: () => playVideo(row.output_video, `${row.model_id} · ${row.video}`) }, () => '播放')
        : '—',
  },
]

async function loadModels() {
  loading.value = true
  try {
    const models = await getTrainModels()
    modelOptions.value = (models || [])
      .filter(m => !m.id.endsWith('-quadruped'))
      .map(m => ({ label: `${m.id} · ${m.name}`, value: m.id }))
  } finally {
    loading.value = false
  }
}

async function handleRun() {
  if (!videos.value.length) return
  loading.value = true
  try {
    const body = {
      videos: videos.value,
      models: allModels.value ? 'all' : form.models,
      device: form.device,
      force: form.force,
    }
    const res = await speedRun(body)
    lastRunId.value = res.run_id || ''
    running.value = true
    status.running = true
    status.results_count = 0
    startPolling()
  } finally {
    loading.value = false
  }
}

let pollTimer = null
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    await Promise.all([refreshStatus(), refreshResults()])
    if (!status.running && status.results_count > 0) {
      running.value = false
      stopPolling()
    }
  }, 3000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function refreshStatus() {
  try {
    const s = await getSpeedrunStatus()
    status.running = !!s.running
    status.results_count = s.results_count ?? 0
  } catch { /* ignore */ }
}
async function refreshResults() {
  try {
    const d = await getSpeedrunResults()
    results.value = d.results || []
    generatedAt.value = d.generated_at || ''
  } catch { /* ignore */ }
}

onMounted(() => {
  loadModels()
  refreshResults()
  refreshStatus()
})
onUnmounted(stopPolling)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>

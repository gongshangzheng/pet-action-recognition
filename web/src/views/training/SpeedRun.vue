<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>Speed Run 结果视频</h3>
          <n-space align="center" size="small" wrap>
            <n-select
              v-model:value="filterModel"
              :options="modelOptions"
              placeholder="全部模型"
              clearable
              size="small"
              style="width: 180px"
              filterable
            />
            <n-select
              v-model:value="filterVideo"
              :options="videoOptions"
              placeholder="全部视频"
              clearable
              size="small"
              style="width: 200px"
              filterable
            />
            <n-tag size="small" :type="accuracy.pct >= 50 ? 'success' : 'warning'">
              准确率 {{ accuracy.correct }}/{{ accuracy.total }} ({{ accuracy.pct }}%)
            </n-tag>
            <n-button size="small" @click="refreshResults" :loading="loading">刷新</n-button>
            <n-tag v-if="status.running" type="info" size="small">运行中 · 已出 {{ status.results_count }} 条</n-tag>
            <n-tag v-else type="success" size="small">共 {{ results.length }} 条</n-tag>
          </n-space>
        </div>
      </template>

      <n-spin :show="loading">
        <n-grid v-if="filteredResults.length" cols="3 600:2 900:3 1200:4" :x-gap="12" :y-gap="12" responsive="screen">
          <n-gi v-for="r in pagedResults" :key="r.id">
            <div class="video-card" @click="playVideo(r)">
              <div class="thumb">
                <img v-if="r.cover_image" :src="getSpeedrunOutputUrl(r.cover_image)" class="cover-img" loading="lazy" />
                <n-icon v-else size="36"><PlayCircleOutline /></n-icon>
                <span class="play-overlay">▶</span>
                <span class="ext">MP4</span>
                <span v-if="r.correct === true" class="badge correct">✓</span>
                <span v-else-if="r.correct === false" class="badge wrong">✗</span>
                <span v-else class="badge na">—</span>
              </div>
              <div class="info">
                <div class="model" :title="r.model_id">{{ r.model_id }}</div>
                <div class="info-row">
                  <div class="pred">
                    <span class="pred-label">{{ r.metrics?.top1_label || '—' }}</span>
                    <span v-if="r.metrics?.top1_score != null" class="pred-score">{{ r.metrics.top1_score.toFixed(2) }}</span>
                  </div>
                  <div class="meta">
                    <span class="meta-gpu" :title="r.gpu_mem_mb != null ? `${r.gpu_mem_mb}MB GPU 显存` : 'GPU 显存未知'">
                      <span v-if="r.gpu_mem_mb != null">{{ r.gpu_mem_mb }}MB</span>
                      <span v-else class="dim">—MB</span>
                    </span>
                    <span class="meta-sep">·</span>
                    <span class="meta-elapsed" :title="r.elapsed_s != null ? `${r.elapsed_s}s 推理耗时` : '推理耗时未知'">
                      {{ r.elapsed_s != null ? r.elapsed_s + 's' : '—' }}
                    </span>
                    <n-tag
                      class="meta-status"
                      size="tiny"
                      :type="r.status === 'completed' ? 'success' : r.status === 'error' ? 'error' : 'warning'"
                    >{{ r.status === 'completed' ? '✓' : r.status === 'error' ? '✗' : '…' }}</n-tag>
                  </div>
                </div>
                <div class="video-name" :title="r.video">{{ videoStem(r.video) }}</div>
              </div>
            </div>
          </n-gi>
        </n-grid>
        <n-pagination
          v-if="filteredResults.length > pageSize"
          v-model:page="page"
          :page-count="pageCount"
          :page-size="pageSize"
          size="small"
          style="margin-top: 12px; justify-content: center"
        />
        <EmptyState v-else-if="!filteredResults.length" description="暂无结果视频。展开下方「运行设置」启动一次 speed run。" />
      </n-spin>
    </n-card>

    <n-card size="small" style="margin-top: 16px">
      <n-collapse>
        <n-collapse-item title="运行设置（新建 / 重跑 speed run）" name="run">
          <n-form :model="form" label-placement="left" :label-width="90" style="max-width: 760px">
            <n-form-item label="视频路径" required>
              <n-input
                v-model:value="form.videosText"
                type="textarea"
                :rows="3"
                placeholder="每行一个视频路径，如&#10;datasets/ucf101/PlayingGuitar/v_PlayingGuitar_g01_c01.avi"
              />
            </n-form-item>
            <n-form-item label="模型">
              <n-space align="center" style="width: 100%">
                <n-select
                  v-model:value="form.models"
                  multiple
                  :options="modelOptionsAll"
                  placeholder="选择模型（留空=全部）"
                  style="flex: 1; min-width: 360px"
                  filterable
                />
                <n-checkbox v-model:checked="allModels">全部</n-checkbox>
              </n-space>
            </n-form-item>
            <n-form-item label="设备">
              <n-radio-group v-model:value="form.device">
                <n-radio value="cuda:0">cuda:0</n-radio>
                <n-radio value="cuda:1">cuda:1</n-radio>
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
            </n-form-item>
          </n-form>
        </n-collapse-item>
      </n-collapse>
    </n-card>

    <VideoModal v-model:show="videoShow" :src="videoSrc" :title="videoTitle" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  NCard, NSpin, NSpace, NSelect, NButton, NTag, NGrid, NGi, NIcon, NPagination,
  NForm, NFormItem, NInput, NRadioGroup, NRadio, NCheckbox, NCollapse, NCollapseItem,
} from 'naive-ui'
import { PlayCircleOutline } from '@vicons/ionicons5'
import EmptyState from '../../components/common/EmptyState.vue'
import VideoModal from '../../components/common/VideoModal.vue'
import {
  getTrainModels,
  speedRun,
  getSpeedrunStatus,
  getSpeedrunResults,
  getSpeedrunOutputUrl,
} from '../../api/training'

const loading = ref(false)
const running = ref(false)
const results = ref([])
const status = reactive({ running: false, results_count: 0 })
const modelOptionsAll = ref([])
const filterModel = ref(null)
const filterVideo = ref(null)

const form = reactive({
  videosText: 'datasets/ucf101/PlayingGuitar/v_PlayingGuitar_g01_c01.avi\ndatasets/ucf101/Archery/v_Archery_g01_c01.avi\ndatasets/ucf101/BabyCrawling/v_BabyCrawling_g01_c01.avi',
  models: [],
  device: 'cuda:0',
  force: false,
})
const allModels = ref(true)

const videos = computed(() => form.videosText.split('\n').map(s => s.trim()).filter(Boolean))

watch(allModels, (v) => { form.models = v ? [] : form.models })

const modelOptions = computed(() => {
  const ids = [...new Set(results.value.map(r => r.model_id))].sort()
  return ids.map(id => ({ label: id, value: id }))
})

const videoOptions = computed(() => {
  const vids = [...new Set(results.value.map(r => r.video))].sort()
  return vids.map(v => ({ label: videoStem(v), value: v }))
})

const filteredResults = computed(() => {
  let list = results.value
  if (filterModel.value) list = list.filter(r => r.model_id === filterModel.value)
  if (filterVideo.value) list = list.filter(r => r.video === filterVideo.value)
  return list
})

const accuracy = computed(() => {
  const withGT = filteredResults.value.filter(r => r.correct === true || r.correct === false)
  const correct = withGT.filter(r => r.correct).length
  const total = withGT.length
  const pct = total > 0 ? Math.round((correct / total) * 100) : 0
  return { correct, total, pct }
})

const page = ref(1)
const pageSize = 20
const pageCount = computed(() => Math.ceil(filteredResults.value.length / pageSize))
const pagedResults = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredResults.value.slice(start, start + pageSize)
})
watch([filterModel, filterVideo], () => { page.value = 1 })

function videoStem(path) {
  return path.split('/').pop()
}

const videoShow = ref(false)
const videoSrc = ref('')
const videoTitle = ref('')

function playVideo(r) {
  if (!r.output_video) return
  videoSrc.value = getSpeedrunOutputUrl(r.output_video)
  videoTitle.value = `${r.model_id} · ${videoStem(r.video)}`
  videoShow.value = true
}

async function loadModels() {
  loading.value = true
  try {
    const models = await getTrainModels()
    modelOptionsAll.value = (models || [])
      .filter(m => !m.id.endsWith('-quadruped'))
      .map(m => ({ label: `${m.id} · ${m.name}`, value: m.id }))
  } finally { loading.value = false }
}

async function handleRun() {
  if (!videos.value.length) return
  loading.value = true
  try {
    const res = await speedRun({
      videos: videos.value,
      models: allModels.value ? 'all' : form.models,
      device: form.device,
      force: form.force,
    })
    running.value = true
    status.running = true
    status.results_count = 0
    startPolling()
  } finally { loading.value = false }
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
function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

async function refreshStatus() {
  try {
    const s = await getSpeedrunStatus()
    status.running = !!s.running
    status.results_count = s.results_count ?? 0
  } catch {}
}
async function refreshResults() {
  try {
    const d = await getSpeedrunResults()
    results.value = d.results || []
  } catch {}
}

onMounted(() => { loadModels(); refreshResults(); refreshStatus() })
onUnmounted(stopPolling)
</script>

<style scoped>
.page-container { padding: 16px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.video-card {
  border: 1px solid var(--n-border-color, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow .15s, transform .15s;
  background: var(--n-color, #fff);
}
.video-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.12); transform: translateY(-1px); }
.thumb {
  position: relative;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  color: rgba(255,255,255,.9);
  overflow: hidden;
}
.thumb .cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb .play-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 28px;
  color: rgba(255,255,255,.8);
  text-shadow: 0 2px 8px rgba(0,0,0,.6);
  pointer-events: none;
}
.thumb .ext {
  position: absolute;
  top: 6px;
  right: 8px;
  font-size: 11px;
  color: rgba(255,255,255,.7);
}
.thumb .badge {
  position: absolute;
  top: 6px;
  left: 8px;
  font-size: 14px;
  font-weight: bold;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.thumb .badge.correct { background: #18a058; }
.thumb .badge.wrong { background: #d03050; }
.thumb .badge.na { background: #909399; }
.info {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.model {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--n-text-color, #1f2329);
}
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 18px;
}
.pred {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}
.pred-label {
  font-size: 12px;
  font-weight: 500;
  line-height: 1.3;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--n-color-target-bg, rgba(37, 99, 235, 0.08));
  color: var(--n-color-target, #2563eb);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.pred-score {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-2, #6b7280);
}
.meta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-dim, #9ca3af);
  white-space: nowrap;
}
.meta-sep { opacity: .55; }
.meta-status { margin-left: 2px; }
.video-name {
  margin-top: 1px;
  font-size: 10px;
  font-style: italic;
  line-height: 1.3;
  color: var(--color-text-dim, #9ca3af);
  opacity: .85;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dim { color: var(--color-text-dim, #9ca3af); }
</style>

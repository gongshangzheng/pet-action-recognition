<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>实时视频流 + 实时推理（Live）</h3>
          <n-space :size="8">
            <n-button size="small" @click="loadSources" :loading="loadingSources">刷新源</n-button>
            <n-button size="small" type="primary" @click="openAddSource">+ 添加源</n-button>
          </n-space>
        </div>
      </template>

      <!-- 推理控制条 -->
      <div class="infer-bar">
        <n-space align="center" :wrap="false">
          <span class="lbl">模型：</span>
          <n-select
            v-model:value="selectedModel"
            :options="modelOptions"
            placeholder="选模型"
            size="small"
            style="width: 260px"
            :disabled="inferring"
          />
          <n-select v-model:value="device" :options="deviceOptions" size="small" style="width: 110px" :disabled="inferring" />
          <n-input-number v-model:value="strideSec" :min="0.5" :max="10" :step="0.5" size="small" style="width: 110px">
            <template #prefix>步长s</template>
          </n-input-number>
          <n-button v-if="!inferring" type="primary" size="small" :disabled="!canInfer" @click="startInfer">
            开始推理
          </n-button>
          <n-button v-else type="error" size="small" @click="stopInfer">停止</n-button>
          <n-text v-if="inferStatus" :type="inferStatusType" style="font-size: 12px">{{ inferStatus }}</n-text>
        </n-space>
      </div>

      <div class="live-layout">
        <!-- 左：源 + 文件 -->
        <div class="live-left">
          <n-spin :show="loadingSources">
            <div class="section-title">摄像头源</div>
            <n-list v-if="sources.length" hoverable clickable bordered>
              <n-list-item
                v-for="s in sources"
                :key="s.id"
                :class="{ active: s.id === selectedSourceId }"
                @click="selectSource(s)"
              >
                <n-thing>
                  <template #header>
                    <span class="src-name">{{ s.name }}</span>
                    <n-tag size="tiny" :type="s.is_active ? 'success' : 'default'" style="margin-left: 6px">
                      {{ s.is_active ? '启用' : '停用' }}
                    </n-tag>
                  </template>
                  <template #description>
                    <n-ellipsis style="font-size: 11px; color: #888">{{ s.alias }} · {{ s.stream_url }}</n-ellipsis>
                  </template>
                  <template #header-extra>
                    <n-space :size="4" @click.stop>
                      <n-button size="tiny" quaternary @click="openEditSource(s)">编辑</n-button>
                      <n-popconfirm @positive-click="onDeleteSource(s)">
                        <template #trigger><n-button size="tiny" quaternary type="error">删除</n-button></template>
                        确认删除源 "{{ s.name }}"？
                      </n-popconfirm>
                    </n-space>
                  </template>
                </n-thing>
              </n-list-item>
            </n-list>
            <n-empty v-else description="无源；先 POST /api/live/sources 添加（源管理 UI 见 t11-5）" style="padding: 20px 0" />

            <div v-if="files.length" class="section-title" style="margin-top: 12px">视频文件</div>
            <n-spin :show="loadingFiles">
              <n-list v-if="files.length" hoverable clickable bordered size="small">
                <n-list-item
                  v-for="f in files"
                  :key="f.name"
                  :class="{ active: f.name === selectedFile }"
                  @click="selectFile(f)"
                >
                  <n-thing>
                    <template #header>{{ f.name }}</template>
                    <template #description>{{ (f.size / 1024 / 1024).toFixed(2) }} MB</template>
                  </n-thing>
                </n-list-item>
              </n-list>
            </n-spin>
          </n-spin>
        </div>

        <!-- 中：播放器 -->
        <div class="live-right">
          <VideoPlayer :src="playUrl" :overlay="currentOverlay" @timeupdate="onTime" @screenshot="onScreenshot" />
          <div v-if="currentSource" class="meta">
            <n-tag size="small" type="info">{{ currentSource.alias }}</n-tag>
            <span v-if="selectedFile" style="margin-left: 8px; font-size: 13px; color: #666">{{ selectedFile }}</span>
            <n-text v-if="playUrl" depth="3" style="font-size: 12px; margin-left: 8px">
              stream_token 已签名（借鉴 pet-videos 安全方案）
            </n-text>
          </div>
        </div>

        <!-- 右：推理段列表 -->
        <div class="live-segs">
          <div class="section-title">识别段（{{ segments.length }}）</div>
          <n-scrollbar style="max-height: 60vh">
            <n-list v-if="segments.length" bordered size="small">
              <n-list-item
                v-for="(s, i) in segments"
                :key="i"
                :class="{ active: currentSegIndex === i }"
              >
                <n-thing>
                  <template #header>
                    <n-tag :type="segColor(s.label)" size="tiny" style="margin-right: 6px">{{ s.label }}</n-tag>
                    <span style="font-size: 12px">{{ (s.score * 100).toFixed(0) }}%</span>
                  </template>
                  <template #description style="font-size: 11px">
                    {{ s.t_start }}s – {{ s.t_end }}s · {{ s.model }}
                  </template>
                </n-thing>
              </n-list-item>
            </n-list>
            <n-empty v-else description="点「开始推理」逐段识别" style="padding: 30px 0" />
          </n-scrollbar>
        </div>
      </div>
    </n-card>
    <SourceManageModal v-model:visible="showSourceModal" :source="editingSource" @saved="loadSources" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { NCard, NSpin, NList, NListItem, NThing, NTag, NEmpty, NEllipsis, NText, NButton, NSpace, NSelect, NInputNumber, NScrollbar, NPopconfirm, useMessage } from 'naive-ui'
import VideoPlayer from '../components/live/VideoPlayer.vue'
import SourceManageModal from '../components/live/SourceManageModal.vue'
import { getSources, getSourceFiles, getPlayUrl, createScreenshot, deleteSource } from '../api/live'
import { getTrainModels } from '../api/training'

const sources = ref([])
const files = ref([])
const selectedSourceId = ref(null)
const selectedFile = ref('')
const playUrl = ref('')
const currentSource = ref(null)
const loadingSources = ref(false)
const loadingFiles = ref(false)

// 推理
const trainModels = ref([])
const selectedModel = ref(null)
const device = ref('cpu')
const strideSec = ref(2)
const inferring = ref(false)
const inferStatus = ref('')
const inferStatusType = ref('info')
const segments = ref([])
const currentTime = ref(0)
let es = null

const deviceOptions = [
  { label: 'CPU', value: 'cpu' },
  { label: 'CUDA:0', value: 'cuda:0' },
  { label: 'CUDA:1', value: 'cuda:1' },
]

const modelOptions = computed(() => {
  const mm = trainModels.value.map(m => ({ label: `${m.name} (${m.id})`, value: `mmaction2:${m.id}` }))
  return [...mm, { label: 'Qwen3-VL-Plus (VLM)', value: 'vlm:qwen3-vl-plus' }]
})

const canInfer = computed(() => currentSource.value && selectedFile.value && selectedModel.value)

const currentSegIndex = computed(() => {
  const t = currentTime.value
  return segments.value.findIndex(s => t >= s.t_start && t < s.t_end)
})

const currentOverlay = computed(() => {
  const i = currentSegIndex.value
  if (i < 0) return ''
  const s = segments.value[i]
  return `${s.label}  ${(s.score * 100).toFixed(0)}%`
})

// 按 label 哈希取色
const COLOR_TYPES = ['success', 'info', 'warning', 'error', 'default']
function segColor(label) {
  let h = 0
  for (const c of label) h = (h * 31 + c.charCodeAt(0)) % 1000
  return COLOR_TYPES[h % COLOR_TYPES.length]
}

async function loadSources() {
  loadingSources.value = true
  try {
    const d = await getSources()
    sources.value = d.sources || []
    if (sources.value.length && !currentSource.value) selectSource(sources.value[0])
  } finally {
    loadingSources.value = false
  }
}

async function loadModels() {
  try {
    const d = await getTrainModels()
    trainModels.value = d.models || d || []
    if (trainModels.value.length && !selectedModel.value) {
      selectedModel.value = `mmaction2:${trainModels.value[0].id}`
    }
  } catch (e) { trainModels.value = [] }
}

async function selectSource(s) {
  currentSource.value = s
  selectedSourceId.value = s.id
  selectedFile.value = ''
  playUrl.value = ''
  files.value = []
  loadingFiles.value = true
  try {
    const d = await getSourceFiles(s.id)
    files.value = d.files || []
    if (files.value.length) selectFile(files.value[0])
  } finally {
    loadingFiles.value = false
  }
}

async function selectFile(f) {
  selectedFile.value = f.name
  playUrl.value = ''
  if (!currentSource.value) return
  try {
    const d = await getPlayUrl(currentSource.value.alias, f.name)
    playUrl.value = d.url
  } catch (e) {
    playUrl.value = ''
  }
}

function startInfer() {
  if (!canInfer.value || !selectedModel.value) return
  const [modelType, modelId] = selectedModel.value.split(':')
  const alias = currentSource.value.alias
  const filename = selectedFile.value
  const url = `/api/live/analyze/stream?alias=${encodeURIComponent(alias)}&filename=${encodeURIComponent(filename)}&model_id=${encodeURIComponent(modelId)}&model_type=${modelType}&clip_sec=1&stride_sec=${strideSec.value}&device=${device.value}`
  segments.value = []
  inferring.value = true
  inferStatus.value = '启动推理…'
  inferStatusType.value = 'info'
  es = new EventSource(url)
  es.onmessage = (e) => {
    const d = JSON.parse(e.data)
    if (d.status === 'loading_model') { inferStatus.value = `加载模型 ${d.model}…`; return }
    if (d.status === 'model_loaded') { inferStatus.value = `推理中（模型 ${d.model} ${d.took_sec}s）`; return }
    if (d.status === 'done') { inferStatus.value = `完成（${segments.value.length} 段）`; inferStatusType.value = 'success'; stopInfer(); return }
    if (d.error) { inferStatus.value = `错误：${d.error}`; inferStatusType.value = 'error'; stopInfer(); return }
    if (d.t_start !== undefined) {
      segments.value.push(d)
      inferStatus.value = `推理中…已 ${segments.value.length} 段`
    }
  }
  es.onerror = () => {
    if (inferring.value) { inferStatus.value = '连接中断'; inferStatusType.value = 'error' }
    stopInfer()
  }
}

function stopInfer() {
  inferring.value = false
  if (es) { es.close(); es = null }
}

function onTime(t) {
  currentTime.value = t
}

// 源管理 + 截屏
const showSourceModal = ref(false)
const editingSource = ref(null)
const msg = useMessage()

function openAddSource() { editingSource.value = null; showSourceModal.value = true }
function openEditSource(s) { editingSource.value = s; showSourceModal.value = true }
async function onDeleteSource(s) {
  try {
    await deleteSource(s.id)
    msg.success('已删除')
    if (currentSource.value?.id === s.id) { currentSource.value = null; files.value = []; playUrl.value = '' }
    await loadSources()
  } catch (e) { msg.error('删除失败') }
}
async function onScreenshot(dataUrl) {
  // 下载到本地
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = `shot-${Date.now()}.png`
  a.click()
  // 上传到后端（关联当前源）
  if (currentSource.value) {
    try {
      await createScreenshot({ source_id: currentSource.value.id, filename: `shot-${Date.now()}`, data_url: dataUrl })
      msg.success('截图已入库')
    } catch (e) { msg.warning('截图上传失败，本地已保存') }
  } else {
    msg.info('截图已下载（无关联源，未入库）')
  }
}

onMounted(() => {
  loadSources()
  loadModels()
})
onUnmounted(stopInfer)
</script>

<style scoped>
.live-layout { display: grid; grid-template-columns: 280px 1fr 280px; gap: 16px; }
.live-left { border-right: 1px solid #eee; padding-right: 12px; max-height: 70vh; overflow-y: auto; }
.live-right { display: flex; flex-direction: column; gap: 10px; }
.live-segs { border-left: 1px solid #eee; padding-left: 12px; max-height: 70vh; }
.infer-bar { padding: 8px 12px; margin-bottom: 12px; background: #fafafa; border-radius: 6px; }
.section-title { font-size: 13px; color: #888; margin: 8px 0 6px; }
.lbl { font-size: 13px; color: #666; white-space: nowrap; }
.n-list-item.active { background: var(--n-color, #f0f7ff); }
.src-name { font-weight: 500; }
.meta { display: flex; align-items: center; }
</style>

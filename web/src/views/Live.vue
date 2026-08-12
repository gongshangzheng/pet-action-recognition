<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>示例视频演示</h3>
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
          <button v-if="!inferring" class="n-button n-button--primary-type n-button--small-type" :disabled="!canInfer" @click="startInfer">
            开始推理
          </button>
          <button v-else class="n-button n-button--error-type n-button--small-type" @click="stopInfer">停止</button>
          <n-text v-if="inferStatus" :type="inferStatusType" style="font-size: 12px">{{ inferStatus }}</n-text>
        </n-space>
      </div>

      <div class="live-layout">
        <!-- 左：示例视频列表 -->
        <div class="live-left">
          <div class="section-title flex-between">
            <span>视频源</span>
            <n-button size="tiny" @click="editingSource = null; showSourceModal = true">+ 管理摄像头</n-button>
          </div>
          <n-tabs v-model:active="leftTab" type="line" size="small">
            <n-tab-pane name="demo" title="示例视频">
              <n-spin :show="loadingDemo">
                <n-list v-if="demoVideos.length" hoverable clickable bordered size="small">
                  <n-list-item
                    v-for="v in demoVideos"
                    :key="v.name"
                    :class="{ active: demoSelected === v.name }"
                    @click="selectDemo(v)"
                  >
                    <n-thing>
                      <template #header>
                        <n-tag size="tiny" :type="labelTagType(v.label)">{{ v.label }}</n-tag>
                        <span style="margin-left: 6px">{{ v.name }}</span>
                      </template>
                      <template #description>{{ (v.size / 1024 / 1024).toFixed(1) }} MB</template>
                    </n-thing>
                  </n-list-item>
                </n-list>
                <n-empty v-if="!demoVideos.length && !loadingDemo" description="无演示视频" style="padding: 20px 0" />
              </n-spin>
            </n-tab-pane>
            <n-tab-pane name="source" title="摄像头源">
              <n-spin :show="loadingSources">
                <n-list v-if="sources.length" hoverable clickable bordered size="small">
                  <n-list-item
                    v-for="s in sources"
                    :key="s.id"
                    :class="{ active: currentSource?.id === s.id }"
                    @click="selectSource(s)"
                  >
                    <n-thing>
                      <template #header>
                        <n-tag size="tiny" :type="s.is_active ? 'success' : 'default'">
                          {{ s.is_active ? '在线' : '离线' }}
                        </n-tag>
                        <span class="src-name" style="margin-left: 6px">{{ s.alias || s.name }}</span>
                      </template>
                      <template #description style="font-size: 11px">{{ s.stream_url }}</template>
                    </n-thing>
                  </n-list-item>
                </n-list>
                <n-empty v-if="!sources.length && !loadingSources" description="无摄像头源" style="padding: 20px 0" />
              </n-spin>
            </n-tab-pane>
          </n-tabs>
        </div>

        <!-- 中：播放器 -->
        <div class="live-right">
          <!-- 真直播模式（帧级同步） -->
          <CanvasPlayer
            v-if="isDemoMode && liveStreamUrl"
            :src="liveStreamUrl"
            @result="onCanvasResult"
            @done="onCanvasDone"
            @status="onCanvasStatus"
          />
          <!-- 静态视频播放 -->
          <VideoPlayer v-else :src="playUrl" :overlay="currentOverlay" @timeupdate="onTime" @screenshot="onScreenshot" />
          <div class="meta">
            <n-tag v-if="isDemoMode" size="small" type="warning">🎬 直播</n-tag>
            <span v-if="selectedFile" style="margin-left: 8px; font-size: 13px; color: #666">{{ selectedFile }}</span>
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
import { ref, onMounted, computed, onUnmounted, watch, nextTick } from 'vue'
import { NCard, NSpin, NList, NListItem, NThing, NTag, NEmpty, NText, NButton, NSpace, NSelect, NInputNumber, NScrollbar, NTabs, NTabPane, useMessage } from 'naive-ui'
import VideoPlayer from '../components/live/VideoPlayer.vue'
import CanvasPlayer from '../components/live/CanvasPlayer.vue'
import { createScreenshot, getDemoVideos, getDemoVideoUrl } from '../api/live'
import { getTrainModels } from '../api/training'

const selectedFile = ref('')
const playUrl = ref('')
const demoVideos = ref([])
const demoSelected = ref('')
const loadingDemo = ref(false)
const leftTab = ref('demo')  // 'demo' | 'source'
const isDemoMode = ref(false)
const liveStreamUrl = ref('')
const currentSource = ref(null)  // for source mode

// 摄像头源
const sources = ref([])
const loadingSources = ref(false)
const showSourceModal = ref(false)
const editingSource = ref(null)

// 推理
const trainModels = ref([])
const selectedModel = ref('mmaction2:tsn-resnet50')  // 默认值，避免等待模型加载
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

const canInfer = computed(() => {
  const hasSource = leftTab.value === 'demo' && demoSelected.value || leftTab.value === 'source' && currentSource.value
  return hasSource && selectedModel.value
})

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

function labelTagType(label) {
  return segColor(label)  // 复用同一套颜色逻辑
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

async function loadSources() {
  loadingSources.value = true
  try {
    const { getStreamSources } = await import('../api/live')
    sources.value = await getStreamSources()
  } catch (e) { sources.value = [] }
  finally { loadingSources.value = false }
}

function selectSource(s) {
  leftTab.value = 'source'
  currentSource.value = s
  demoSelected.value = ''
  selectedFile.value = s.name
  playUrl.value = ''
}

async function loadDemoVideos() {
  loadingDemo.value = true
  try {
    const d = await getDemoVideos()
    demoVideos.value = d.videos || []
  } catch (e) { demoVideos.value = [] }
  finally { loadingDemo.value = false }
}

function selectDemo(v) {
  leftTab.value = 'demo'
  demoSelected.value = v.name
  selectedFile.value = v.name
  currentSource.value = null
  playUrl.value = getDemoVideoUrl(v.name)
}

function startInfer() {
  if (!selectedModel.value) selectedModel.value = 'mmaction2:tsn-resnet50'
  if (!canInfer.value) return
  // demo 模式走 CanvasPlayer（帧级同步）
  if (leftTab.value === 'demo') { playDemo(); return }
  const [modelType, modelId] = selectedModel.value.split(':')
  const filename = selectedFile.value
  const url = `/api/live/demo/analyze/stream?video_name=${encodeURIComponent(filename)}&model_id=${encodeURIComponent(modelId)}&model_type=${modelType}&clip_sec=1&stride_sec=${strideSec.value}&device=${device.value}`
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
  liveStreamUrl.value = ''
  isDemoMode.value = false
  es = null
}

async function playDemo() {
  const v = demoVideos.value.find(x => x.name === demoSelected.value)
  if (v) selectDemo(v)
  segments.value = []
  const [modelType, modelId] = (selectedModel.value || 'mmaction2:tsn-resnet50').split(':')
  const url = `/api/live/demo/live_stream?video_name=${encodeURIComponent(selectedFile.value)}&model_id=${encodeURIComponent(modelId)}&stride_sec=${strideSec.value}&clip_sec=1&device=${device.value}`
  isDemoMode.value = true
  liveStreamUrl.value = url
  inferring.value = true
  inferStatus.value = '加载模型…'
}

function onTime(t) {
  currentTime.value = t
}

function onCanvasResult(seg) {
  segments.value.push(seg)
  inferStatus.value = `推理中…已 ${segments.value.length} 段`
}

function onCanvasDone() {
  inferStatus.value = `完成（${segments.value.length} 段）`
  inferStatusType.value = 'success'
  inferring.value = false
}

function onCanvasStatus(msg) {
  inferStatus.value = msg
}

const msg = useMessage()

async function onScreenshot(dataUrl) {
  // 下载到本地
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = `shot-${Date.now()}.png`
  a.click()
  // 上传到后端
  try {
    await createScreenshot({ filename: `shot-${Date.now()}`, data_url: dataUrl })
    msg.success('截图已入库')
  } catch (e) { msg.warning('截图上传失败，本地已保存') }
}

onMounted(() => {
  loadModels()
  loadDemoVideos()
  loadSources()
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

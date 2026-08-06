<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>实时视频流（Live）</h3>
          <n-button size="small" @click="loadSources" :loading="loadingSources">刷新源</n-button>
        </div>
      </template>

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
                </n-thing>
              </n-list-item>
            </n-list>
            <n-empty v-else description="无源；先在后端 POST /api/live/sources 添加（源管理 UI 见 t11-5）" style="padding: 20px 0" />

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

        <!-- 右：播放器 -->
        <div class="live-right">
          <VideoPlayer :src="playUrl" />
          <div v-if="currentSource" class="meta">
            <n-tag size="small" type="info">{{ currentSource.alias }}</n-tag>
            <span v-if="selectedFile" style="margin-left: 8px; font-size: 13px; color: #666">{{ selectedFile }}</span>
            <n-text v-if="playUrl" depth="3" style="font-size: 12px; margin-left: 8px">
              stream_token 已签名（借鉴 pet-videos 安全方案）
            </n-text>
          </div>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NList, NListItem, NThing, NTag, NEmpty, NEllipsis, NText, NButton } from 'naive-ui'
import VideoPlayer from '../components/live/VideoPlayer.vue'
import { getSources, getSourceFiles, getPlayUrl } from '../api/live'

const sources = ref([])
const files = ref([])
const selectedSourceId = ref(null)
const selectedFile = ref('')
const playUrl = ref('')
const currentSource = ref(null)
const loadingSources = ref(false)
const loadingFiles = ref(false)

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

onMounted(loadSources)
</script>

<style scoped>
.live-layout { display: grid; grid-template-columns: 320px 1fr; gap: 16px; }
.live-left { border-right: 1px solid #eee; padding-right: 12px; max-height: 70vh; overflow-y: auto; }
.live-right { display: flex; flex-direction: column; gap: 10px; }
.section-title { font-size: 13px; color: #888; margin: 8px 0 6px; }
.n-list-item.active { background: var(--n-color, #f5f5f5); }
.src-name { font-weight: 500; }
.meta { display: flex; align-items: center; }
</style>

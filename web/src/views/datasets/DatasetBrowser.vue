<template>
  <div class="page-container">
    <!-- 数据集列表 -->
    <n-card v-if="!currentDataset" size="small">
      <template #header><h3>数据集管理</h3></template>
      <n-spin :show="loading">
        <div v-if="datasets.length" class="ds-grid">
          <div v-for="d in datasets" :key="d.id" class="ds-card" @click="enterDataset(d)">
            <div class="ds-card-icon">
              <n-icon size="28"><FolderOpenOutline /></n-icon>
            </div>
            <div class="ds-card-name">{{ d.name }}</div>
            <div class="ds-card-meta">
              <span v-if="d.subdirs">{{ d.subdirs }} 子目录</span>
              <span v-if="d.files">{{ d.files }} 文件</span>
              <span v-if="d.is_symlink" class="ds-link">→ 软链</span>
            </div>
          </div>
        </div>
        <EmptyState v-else description="datasets/ 为空" />
      </n-spin>
    </n-card>

    <!-- 浏览视图 -->
    <n-card v-else size="small">
      <template #header>
        <div class="flex-between">
          <div class="breadcrumb">
            <span class="crumb-link" @click="backToDatasets">数据集</span>
            <template v-for="(seg, i) in pathSegments" :key="i">
              <span class="crumb-sep">/</span>
              <span class="crumb-link" @click="navigateTo(i)">{{ seg }}</span>
            </template>
          </div>
          <n-space align="center" size="small">
            <span class="item-count">共 {{ browseData.total }} 项</span>
            <n-button size="small" @click="loadBrowse" :loading="loading">刷新</n-button>
          </n-space>
        </div>
      </template>
      <n-spin :show="loading">
        <div v-if="browseData.items.length" class="browse-grid">
          <div v-for="item in browseData.items" :key="item.name" class="browse-item" @click="onItemClick(item)">
            <!-- 目录 -->
            <div v-if="item.type === 'dir'" class="item-thumb dir-thumb">
              <n-icon size="24"><FolderOutline /></n-icon>
            </div>
            <!-- 图片 -->
            <div v-else-if="item.is_image" class="item-thumb">
              <img :src="getFileUrl(item.name)" class="item-cover" loading="lazy" />
            </div>
            <!-- 视频（封面图） -->
            <div v-else-if="item.is_video" class="item-thumb">
              <img :src="getThumbUrl(item.name)" class="item-cover" loading="lazy" />
              <span class="play-overlay">▶</span>
            </div>
            <!-- 其他文件 -->
            <div v-else class="item-thumb file-thumb">
              <n-icon size="24"><DocumentOutline /></n-icon>
            </div>
            <div class="item-name" :title="item.name">{{ item.name }}</div>
          </div>
        </div>
        <EmptyState v-else description="此目录为空" />
        <n-pagination
          v-if="browseData.pages > 1"
          v-model:page="page"
          :page-count="browseData.pages"
          :page-size="pageSize"
          size="small"
          style="margin-top: 12px; justify-content: center"
          @update:page="loadBrowse"
        />
      </n-spin>
    </n-card>

    <!-- 文件预览 -->
    <n-modal v-model:show="previewShow" preset="card" :title="previewTitle" style="max-width: 800px">
      <div v-if="previewType === 'image'" style="text-align: center">
        <img :src="previewSrc" style="max-width: 100%; max-height: 70vh" />
      </div>
      <video v-else-if="previewType === 'video'" :src="previewSrc" controls preload="none" playsinline
        style="width: 100%; max-height: 70vh; background: #000" />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { NCard, NSpin, NSpace, NButton, NIcon, NPagination, NModal } from 'naive-ui'
import { FolderOpenOutline, FolderOutline, DocumentOutline } from '@vicons/ionicons5'
import EmptyState from '../../components/common/EmptyState.vue'
import { listDatasets, browseDataset, getDatasetFileUrl, getDatasetThumbUrl } from '../../api/datasets'

defineOptions({ name: 'DatasetBrowser' })

const loading = ref(false)
const datasets = ref([])
const currentDataset = ref(null)
const currentPath = ref('')
const page = ref(1)
const pageSize = 20
const browseData = reactive({ items: [], total: 0, pages: 0 })

const pathSegments = computed(() => currentPath.value ? currentPath.value.split('/') : [])

const previewShow = ref(false)
const previewSrc = ref('')
const previewTitle = ref('')
const previewType = ref('')

function getFileUrl(name) {
  const p = currentPath.value ? `${currentPath.value}/${name}` : name
  return getDatasetFileUrl(currentDataset.value.id, p)
}
function getThumbUrl(name) {
  const p = currentPath.value ? `${currentPath.value}/${name}` : name
  return getDatasetThumbUrl(currentDataset.value.id, p)
}

async function loadDatasets() {
  loading.value = true
  try {
    const d = await listDatasets()
    datasets.value = d.datasets || []
  } catch { datasets.value = [] }
  loading.value = false
}

async function loadBrowse() {
  if (!currentDataset.value) return
  loading.value = true
  try {
    const d = await browseDataset(currentDataset.value.id, {
      path: currentPath.value, page: page.value, size: pageSize,
    })
    Object.assign(browseData, d)
  } catch { browseData.items = [] }
  loading.value = false
}

function enterDataset(d) {
  currentDataset.value = d
  currentPath.value = ''
  page.value = 1
  loadBrowse()
}

function backToDatasets() {
  currentDataset.value = null
  currentPath.value = ''
}

function navigateTo(segmentIndex) {
  const segs = pathSegments.value.slice(0, segmentIndex + 1)
  currentPath.value = segs.join('/')
  page.value = 1
  loadBrowse()
}

function onItemClick(item) {
  if (item.type === 'dir') {
    currentPath.value = currentPath.value ? `${currentPath.value}/${item.name}` : item.name
    page.value = 1
    loadBrowse()
  } else if (item.is_image || item.is_video) {
    previewType.value = item.is_image ? 'image' : 'video'
    previewSrc.value = getFileUrl(item.name)
    previewTitle.value = item.name
    previewShow.value = true
  }
}

onMounted(loadDatasets)
</script>

<style scoped>
.page-container { padding: 16px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.breadcrumb { display: flex; align-items: center; gap: 2px; flex-wrap: wrap; }
.crumb-link { cursor: pointer; color: #6b7280; }
.crumb-link:hover { color: #333; text-decoration: underline; }
.crumb-sep { color: #ccc; margin: 0 2px; }
.item-count { font-size: 12px; color: #9ca3af; }
.ds-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.ds-card {
  border: 1px solid rgba(128,128,128,0.2);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  text-align: center;
  transition: box-shadow .15s;
}
.ds-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.ds-card-icon { margin-bottom: 8px; color: #6b7280; }
.ds-card-name { font-weight: 600; font-size: 14px; }
.ds-card-meta { font-size: 11px; color: #9ca3af; margin-top: 4px; }
.ds-link { color: #6b7280; font-style: italic; }
.browse-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.browse-item {
  border: 1px solid rgba(128,128,128,0.15);
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow .15s;
}
.browse-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.item-thumb {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  position: relative;
  overflow: hidden;
}
.item-cover { width: 100%; height: 100%; object-fit: cover; }
.dir-thumb { background: rgba(128,128,128,0.08); color: #6b7280; }
.file-thumb { background: rgba(128,128,128,0.08); color: #9ca3af; }
.play-overlay {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  font-size: 24px; color: rgba(255,255,255,.8); text-shadow: 0 2px 6px rgba(0,0,0,.5);
  pointer-events: none;
}
.item-name {
  padding: 4px 6px; font-size: 11px; color: #6b7280;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
</style>

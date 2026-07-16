<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>查看输出</h3>
          <n-button size="small" @click="load">刷新</n-button>
        </div>
      </template>
      <n-spin :show="loading">
        <n-data-table :columns="columns" :data="outputs" :bordered="false" size="small" striped />
        <EmptyState v-if="!loading && !outputs.length" description="暂无输出文件。运行评测后，压缩码流/重建视频会出现在这里。" />
      </n-spin>
    </n-card>

    <VideoModal v-model:show="videoShow" :src="videoSrc" :title="videoTitle" />
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { NCard, NSpin, NDataTable, NButton, useMessage } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import VideoModal from '../../components/common/VideoModal.vue'
import { listOutputs, getOutputUrl } from '../../api/evaluation'

const message = useMessage()
const loading = ref(false)
const outputs = ref([])
const videoShow = ref(false)
const videoSrc = ref('')
const videoTitle = ref('')

const columns = [
  { title: '文件', key: 'name', render: (r) => r.path },
  { title: '类型', key: 'ext', width: 80 },
  { title: '大小', key: 'size_bytes', width: 100, render: (r) => fmtSize(r.size_bytes) },
  {
    title: '操作', key: 'actions', width: 120,
    render: (r) => r.is_video
      ? h(NButton, { size: 'small', type: 'primary', secondary: true, onClick: () => play(r) }, { default: () => '播放' })
      : h('span', { class: 'dim' }, '—'),
  },
]

function fmtSize(b) {
  if (!b) return '-'
  const u = ['B', 'KB', 'MB', 'GB']
  let i = 0, v = b
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${u[i]}`
}

function play(r) {
  // 按需：仅点击时赋值 src，VideoModal 内 <video v-if=show preload=none> 才请求字节
  videoSrc.value = getOutputUrl(r.path)
  videoTitle.value = r.name
  videoShow.value = true
}

async function load() {
  loading.value = true
  try {
    const res = await listOutputs()
    outputs.value = res?.outputs || []
  } catch (e) {
    message.error('加载输出列表失败')
    outputs.value = []
  }
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.dim { color: var(--color-text-dim, #9ca3af); }
</style>

<template>
  <div class="video-player">
    <video
      v-if="src"
      ref="videoEl"
      :src="src"
      controls
      autoplay
      playsinline
      @error="onError"
    />
    <div v-else class="empty">
      <n-empty description="选择左侧源与文件后开始播放" />
    </div>
    <div v-if="error" class="error">视频加载失败：{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { NEmpty } from 'naive-ui'

const props = defineProps({
  src: { type: String, default: '' },
})

const videoEl = ref(null)
const error = ref('')

watch(() => props.src, (v) => {
  error.value = ''
  if (v && videoEl.value) videoEl.value.load()
})

function onError(e) {
  error.value = e?.target?.error?.message || '未知错误'
}
</script>

<style scoped>
.video-player {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: 6px;
  overflow: hidden;
  aspect-ratio: 16 / 9;
}
.video-player video { width: 100%; height: 100%; object-fit: contain; }
.video-player .empty {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: #999; background: #1f1f1f;
}
.video-player .error {
  position: absolute; bottom: 8px; left: 8px;
  background: rgba(208, 48, 80, 0.9); color: #fff;
  padding: 4px 10px; border-radius: 4px; font-size: 12px;
}
</style>

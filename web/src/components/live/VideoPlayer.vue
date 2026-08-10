<template>
  <div class="video-player">
    <video
      v-if="src"
      ref="videoEl"
      :src="src"
      :style="{ transform: `translate(${pan.x}px, ${pan.y}px)` }"
      controls
      autoplay
      playsinline
      @timeupdate="onTime"
      @error="onError"
    />
    <div v-else class="empty">
      <n-empty description="选择左侧源与文件后开始播放" />
    </div>
    <div v-if="overlay && src" class="overlay">{{ overlay }}</div>
    <button v-if="src" class="shot-btn" @click="screenshot" title="截屏（截图到后端 + 下载）">📷 截屏</button>
    <PtzJoystick v-if="src" @pan="onPan" @reset="onReset" />
    <div v-if="error" class="error">视频加载失败：{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { NEmpty } from 'naive-ui'
import PtzJoystick from './PtzJoystick.vue'

const props = defineProps({
  src: { type: String, default: '' },
  overlay: { type: String, default: '' },
})

const emit = defineEmits(['timeupdate', 'screenshot'])

const videoEl = ref(null)
const error = ref('')
const pan = ref({ x: 0, y: 0 })

watch(() => props.src, (v) => {
  error.value = ''
  pan.value = { x: 0, y: 0 }
  if (v && videoEl.value) videoEl.value.load()
})

function onTime(e) { emit('timeupdate', e.target.currentTime) }
function onError(e) { error.value = e?.target?.error?.message || '未知错误' }
function onPan(dx, dy) { pan.value = { x: pan.value.x + dx, y: pan.value.y + dy } }
function onReset() { pan.value = { x: 0, y: 0 } }

function screenshot() {
  const v = videoEl.value
  if (!v || !v.videoWidth) return
  const c = document.createElement('canvas')
  c.width = v.videoWidth
  c.height = v.videoHeight
  c.getContext('2d').drawImage(v, 0, 0)
  emit('screenshot', c.toDataURL('image/png'))
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
.video-player video { width: 100%; height: 100%; object-fit: contain; transition: transform 0.15s; }
.video-player .empty {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: #999; background: #1f1f1f;
}
.video-player .overlay {
  position: absolute; top: 10px; left: 10px;
  background: rgba(0, 0, 0, 0.65); color: #fff;
  padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: 500;
  pointer-events: none;
}
.video-player .shot-btn {
  position: absolute; top: 10px; right: 10px;
  background: rgba(0, 0, 0, 0.6); color: #fff; border: none;
  padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
.video-player .shot-btn:hover { background: rgba(0, 0, 0, 0.8); }
.video-player .error {
  position: absolute; bottom: 8px; left: 8px;
  background: rgba(208, 48, 80, 0.9); color: #fff;
  padding: 4px 10px; border-radius: 4px; font-size: 12px;
}
</style>

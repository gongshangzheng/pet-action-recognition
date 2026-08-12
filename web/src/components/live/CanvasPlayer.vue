<template>
  <div class="canvas-player" ref="containerRef">
    <canvas ref="canvasRef" :width="canvasWidth" :height="canvasHeight" />
    <div v-if="currentLabel" class="osd-overlay">
      <span class="osd-label" :style="{ background: labelBg }">
        {{ currentLabel }} {{ (currentScore * 100).toFixed(0) }}%
      </span>
    </div>
    <div v-if="loading" class="loading-mask">
      <n-spin size="large" />
      <span style="margin-top: 8px; color: #fff">{{ loadingText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { NSpin } from 'naive-ui'

const props = defineProps<{
  src?: string   // SSE URL
}>()

const emit = defineEmits<{
  (e: 'result', seg: any): void
  (e: 'done'): void
  (e: 'status', msg: string): void
}>()

const canvasRef = ref<HTMLCanvasElement>()
const containerRef = ref<HTMLDivElement>()
const canvasWidth = ref(640)
const canvasHeight = ref(360)
const loading = ref(true)
const loadingText = ref('加载模型…')
const currentLabel = ref('')
const currentScore = ref(0)
const currentTime = ref(0)
let es: EventSource | null = null

const labelBg = computed(() => {
  const colors: Record<string, string> = {
    locomotion: '#4caf50', jump: '#2196f3', eating: '#ff9800',
    drinking: '#9c27b0', grooming: '#e91e63', still_rest: '#607d8b',
    social_interaction: '#ff5722', other_unknown: '#9e9e9e',
  }
  return colors[currentLabel.value] || '#333'
})

function drawFrame(dataUrl: string) {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const img = new Image()
  img.onload = () => {
    canvas.width = img.width
    canvas.height = img.height
    canvasWidth.value = img.width
    canvasHeight.value = img.height
    ctx.drawImage(img, 0, 0)
    img.remove()
  }
  img.src = dataUrl
}

function connect() {
  if (!props.src) return
  disconnect()

  console.log('[CanvasPlayer] connecting to:', props.src)
  es = new EventSource(props.src)
  loading.value = true
  loadingText.value = '加载模型…'
  emit('status', '加载模型…')

  es.onmessage = (e) => {
    let d
    try {
      d = JSON.parse(e.data)
    } catch (err) {
      console.error('[CanvasPlayer] parse error:', err)
      return
    }

    if (d.type === 'status') {
      if (d.status === 'loading_model') {
        loadingText.value = `加载模型 ${d.model || ''}…`
        emit('status', `加载模型 ${d.model || ''}…`)
      } else if (d.status === 'model_loaded') {
        loading.value = false
        loadingText.value = ''
        emit('status', '推理中…')
      }
    } else if (d.type === 'frame') {
      loading.value = false
      currentTime.value = d.t
      drawFrame(d.data_url)
    } else if (d.type === 'result') {
      currentLabel.value = d.label
      currentScore.value = d.score
      emit('result', {
        t_start: d.t,
        t_end: d.t + 1,
        label: d.label,
        score: d.score,
        top5: d.top5,
        model: d.model,
      })
    } else if (d.type === 'done') {
      currentLabel.value = '完成'
      emit('done')
    } else if (d.type === 'error') {
      console.error('[CanvasPlayer] error:', d.error)
      loadingText.value = `错误：${d.error}`
      emit('status', `错误：${d.error}`)
    }
  }

  es.onerror = () => {
    console.error('[CanvasPlayer] EventSource error')
    loadingText.value = '连接中断'
    emit('status', '连接中断')
  }
}

function disconnect() {
  if (es) { es.close(); es = null }
}

onUnmounted(disconnect)

// src 变化时自动重连（immediate: true 首次也触发）
watch(() => props.src, (newSrc, oldSrc) => {
  if (newSrc && newSrc !== oldSrc) {
    connect()
  }
}, { immediate: true })

defineExpose({ connect, disconnect })
</script>

<style scoped>
.canvas-player { position: relative; width: 100%; background: #000; border-radius: 6px; overflow: hidden; }
.canvas-player canvas { display: block; width: 100%; height: auto; }
.osd-overlay { position: absolute; top: 12px; left: 12px; pointer-events: none; }
.osd-label {
  color: #fff; font-size: 16px; font-weight: bold; padding: 4px 12px;
  border-radius: 4px; background: #333; text-shadow: 0 1px 3px rgba(0,0,0,0.5);
}
.loading-mask {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; background: rgba(0,0,0,0.7);
}
</style>

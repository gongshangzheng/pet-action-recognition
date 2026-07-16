<template>
  <n-modal v-model:show="show" preset="card" :title="title" style="max-width: 760px">
    <div class="video-wrap">
      <!-- 仅在弹窗打开时挂载 <video>，且 preload="none" -> 不预加载，点开才请求字节 -->
      <video
        v-if="show && src"
        :src="src"
        controls
        preload="none"
        playsinline
        style="width: 100%; max-height: 70vh; background: #000"
      />
      <div v-if="!src" class="no-src">无可播放的输出视频</div>
    </div>
    <template #footer>
      <span class="hint">按需加载：仅在打开此弹窗时请求视频流。</span>
    </template>
  </n-modal>
</template>

<script setup>
import { NModal } from 'naive-ui'

defineProps({
  title: { type: String, default: '输出视频' },
  src: { type: String, default: '' },
})
const show = defineModel('show', { type: Boolean, default: false })
</script>

<style scoped>
.video-wrap { display: flex; justify-content: center; align-items: center; }
.no-src { color: var(--color-text-dim, #9ca3af); padding: 24px; }
.hint { font-size: 12px; color: var(--color-text-dim, #9ca3af); }
</style>

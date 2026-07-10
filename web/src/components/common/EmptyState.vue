<template>
  <div class="empty-state">
    <n-empty :description="description">
      <template #icon>
        <slot name="icon"></slot>
      </template>
      <template #extra>
        <slot name="extra"></slot>
      </template>
    </n-empty>
  </div>
</template>

<script setup>
import { NEmpty } from 'naive-ui'

defineProps({
  description: { type: String, default: '暂无数据' },
})
</script>

<style scoped>
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}
</style>

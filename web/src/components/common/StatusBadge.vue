<template>
  <n-tag :type="tagType" size="small" round :bordered="false">
    {{ label }}
  </n-tag>
</template>

<script setup>
import { computed } from 'vue'
import { NTag } from 'naive-ui'

const props = defineProps({
  status: { type: String, default: 'pending' },
})

const statusMap = {
  normal: { type: 'success', label: '正常推进' },
  in_progress: { type: 'success', label: '正常推进' },
  risk: { type: 'warning', label: '需关注' },
  blocked: { type: 'error', label: '阻塞中' },
  done: { type: 'success', label: '已完成' },
  completed: { type: 'success', label: '已完成' },
  pending: { type: 'default', label: '待开始' },
  not_started: { type: 'default', label: '未开始' },
  delayed: { type: 'error', label: '延期' },
}

const tagType = computed(() => (statusMap[props.status] || statusMap.pending).type)
const label = computed(() => (statusMap[props.status] || statusMap.pending).label)
</script>

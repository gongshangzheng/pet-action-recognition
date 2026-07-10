<template>
  <div class="page-container">
    <n-card title="项目里程碑" size="small">
      <n-spin :show="loading">
        <n-timeline v-if="milestones.length">
          <n-timeline-item
            v-for="m in milestones"
            :key="m.name"
            :type="timelineType(m.status)"
            :title="m.name"
            :time="m.target_date || '未定'"
          >
            <div class="milestone-detail">
              <StatusBadge :status="m.status" />
              <span v-if="m.owner" class="text-secondary">负责人：{{ m.owner }}</span>
              <span v-if="m.actual_date" class="text-secondary">完成日期：{{ m.actual_date }}</span>
            </div>
            <p v-if="m.description" class="milestone-desc">{{ m.description }}</p>
          </n-timeline-item>
        </n-timeline>
        <EmptyState v-else description="暂无里程碑数据" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NTimeline, NTimelineItem, NSpin } from 'naive-ui'
import StatusBadge from '../../components/common/StatusBadge.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getMilestones } from '../../api/management'

const loading = ref(false)
const milestones = ref([])

function timelineType(status) {
  const map = { done: 'success', completed: 'success', in_progress: 'info', pending: 'default', not_started: 'default', delayed: 'error', risk: 'warning' }
  return map[status] || 'default'
}

onMounted(async () => {
  loading.value = true
  try { milestones.value = await getMilestones() } catch { milestones.value = [] }
  loading.value = false
})
</script>

<style scoped>
.milestone-detail { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.milestone-desc { font-size: 13px; color: #6b7280; }
</style>

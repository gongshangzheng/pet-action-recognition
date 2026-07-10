<template>
  <div class="page-container">
    <n-spin :show="loading">
      <n-grid v-if="hasData" :cols="3" :x-gap="16" :y-gap="16">
        <n-gi>
          <n-card title="待开始" size="small">
            <template #header-extra><n-tag size="small" round>{{ tasks.pending.length }}</n-tag></template>
            <div class="task-list">
              <div v-for="t in tasks.pending" :key="t.name" class="task-card">
                <div class="task-name">{{ t.name }}</div>
                <div class="task-meta">
                  <span>{{ t.owner }}</span>
                  <span v-if="t.end_date">{{ t.end_date }}</span>
                </div>
              </div>
              <p v-if="!tasks.pending.length" class="text-light">暂无</p>
            </div>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card title="进行中" size="small">
            <template #header-extra><n-tag size="small" type="info" round>{{ tasks.in_progress.length }}</n-tag></template>
            <div class="task-list">
              <div v-for="t in tasks.in_progress" :key="t.name" class="task-card">
                <div class="task-name">{{ t.name }}</div>
                <div class="task-meta">
                  <StatusBadge :status="t.status" />
                  <span>{{ t.owner }}</span>
                </div>
                <div v-if="t.note" class="task-note">{{ t.note }}</div>
              </div>
              <p v-if="!tasks.in_progress.length" class="text-light">暂无</p>
            </div>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card title="已完成" size="small">
            <template #header-extra><n-tag size="small" type="success" round>{{ tasks.completed.length }}</n-tag></template>
            <div class="task-list">
              <div v-for="t in tasks.completed" :key="t.name" class="task-card">
                <div class="task-name">{{ t.name }}</div>
                <div class="task-meta">
                  <span>{{ t.owner }}</span>
                  <span v-if="t.end_date">{{ t.end_date }}</span>
                </div>
              </div>
              <p v-if="!tasks.completed.length" class="text-light">暂无</p>
            </div>
          </n-card>
        </n-gi>
      </n-grid>
      <EmptyState v-else description="暂无任务数据，可在 management/docs/tasks.md 中添加" />
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { NGrid, NGi, NCard, NTag, NSpin } from 'naive-ui'
import StatusBadge from '../../components/common/StatusBadge.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTasks } from '../../api/management'

const loading = ref(false)
const tasks = ref({ pending: [], in_progress: [], completed: [] })
const hasData = computed(() => tasks.value.pending.length || tasks.value.in_progress.length || tasks.value.completed.length)

onMounted(async () => {
  loading.value = true
  try { tasks.value = await getTasks() } catch {}
  loading.value = false
})
</script>

<style scoped lang="scss">
.task-list { display: flex; flex-direction: column; gap: 8px; }
.task-card {
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border-left: 3px solid #e5e7eb;

  .task-name { font-weight: 500; margin-bottom: 6px; }
  .task-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #6b7280; }
  .task-note { font-size: 12px; color: #9ca3af; margin-top: 4px; }
}
</style>

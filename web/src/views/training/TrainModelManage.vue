<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between"><h3>模型配置（可训练 DL 模型）</h3><n-button size="small" @click="load">刷新</n-button></div>
      </template>
      <n-spin :show="loading">
        <n-data-table :columns="columns" :data="models" :bordered="false" size="small" striped />
        <EmptyState v-if="!loading && !models.length" description="暂无可训练模型。下游接 CompressAI 架构 + ELIC 后此处列出。" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NDataTable, NButton } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTrainModels } from '../../api/training'

const loading = ref(false)
const models = ref([])
const columns = [
  { title: 'ID', key: 'id', width: 160 },
  { title: '名称', key: 'name', render: (r) => r.name || r.id },
  { title: '架构', key: '架构', render: (r) => r.架构 || r.type || '-' },
  { title: 'quality 级', key: 'quality', width: 90 },
  { title: 'pretrained 来源', key: 'pretrained' },
  { title: '已训练 checkpoint', key: 'trained_checkpoint', render: (r) => r.trained_checkpoint || '—' },
]

async function load() {
  loading.value = true
  try { models.value = (await getTrainModels()) || [] } catch { models.value = [] }
  loading.value = false
}
onMounted(load)
</script>

<style scoped>
.flex-between { display: flex; justify-content: space-between; align-items: center; }
</style>

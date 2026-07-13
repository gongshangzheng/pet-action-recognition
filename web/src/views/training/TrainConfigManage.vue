<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between"><h3>训练配置（超参 preset）</h3><n-button size="small" @click="load">刷新</n-button></div>
      </template>
      <n-spin :show="loading">
        <n-data-table :columns="columns" :data="configs" :bordered="false" size="small" striped />
        <EmptyState v-if="!loading && !configs.length" description="暂无超参 preset。" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NDataTable, NButton } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTrainConfigs } from '../../api/training'

const loading = ref(false)
const configs = ref([])
const columns = [
  { title: 'ID', key: 'id', width: 120 },
  { title: '名称', key: 'name', render: (r) => r.name || r.id },
  { title: 'epochs', key: 'epochs', width: 80 },
  { title: 'lr', key: 'lr', width: 90 },
  { title: 'batch', key: 'batch_size', width: 70 },
  { title: 'optimizer', key: 'optimizer', width: 100 },
  { title: 'λ(RD)', key: 'lambda', width: 80 },
  { title: 'quality', key: 'quality', width: 80 },
  { title: '描述', key: 'description' },
]

async function load() {
  loading.value = true
  try { configs.value = (await getTrainConfigs()) || [] } catch { configs.value = [] }
  loading.value = false
}
onMounted(load)
</script>

<style scoped>
.flex-between { display: flex; justify-content: space-between; align-items: center; }
</style>

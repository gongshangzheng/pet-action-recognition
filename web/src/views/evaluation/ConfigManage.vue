<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <h3>评测配置</h3>
          <n-button size="small" @click="load">刷新</n-button>
        </div>
      </template>
      <n-spin :show="loading">
        <n-data-table :columns="columns" :data="configs" :bordered="false" size="small" striped />
        <EmptyState v-if="!loading && !configs.length" description="暂无评测配置。在 evaluation/configs/configs.json 添加。" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NDataTable, NButton } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getEvalConfigs } from '../../api/evaluation'

const loading = ref(false)
const configs = ref([])

const columns = [
  { title: 'ID', key: 'id', width: 140 },
  { title: '名称', key: 'name', render: (r) => r.name || r.id },
  { title: '描述', key: 'description' },
  { title: '参数', key: 'params', render: (r) => r.params ? JSON.stringify(r.params) : '-' },
]

async function load() {
  loading.value = true
  try { configs.value = (await getEvalConfigs()) || [] } catch { configs.value = [] }
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.flex-between { display: flex; justify-content: space-between; align-items: center; }
</style>

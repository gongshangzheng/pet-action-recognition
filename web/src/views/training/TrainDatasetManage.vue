<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between"><h3>数据集配置（训练数据集）</h3><n-button size="small" @click="load">刷新</n-button></div>
      </template>
      <n-spin :show="loading">
        <n-data-table :columns="columns" :data="datasets" :bordered="false" size="small" striped />
        <EmptyState v-if="!loading && !datasets.length" description="暂无训练数据集。下游接 FLIR thermal train split / OSU 帧 / 自定义后此处列出。" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NDataTable, NButton } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTrainDatasets } from '../../api/training'

const loading = ref(false)
const datasets = ref([])
const columns = [
  { title: 'ID', key: 'id', width: 180 },
  { title: '名称', key: 'name', render: (r) => r.name || r.id },
  { title: 'split', key: 'split', width: 100 },
  { title: '样本数', key: 'num_samples', width: 90 },
  { title: '模态', key: 'modalities', render: (r) => (r.modalities || []).join(',') },
  { title: '描述', key: 'description' },
]

async function load() {
  loading.value = true
  try { datasets.value = (await getTrainDatasets()) || [] } catch { datasets.value = [] }
  loading.value = false
}
onMounted(load)
</script>

<style scoped>
.flex-between { display: flex; justify-content: space-between; align-items: center; }
</style>

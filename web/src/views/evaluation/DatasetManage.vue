<template>
  <div class="page-container">
    <n-card title="数据集管理" size="small">
      <n-spin :show="loading">
        <n-table v-if="datasets.length" :bordered="false" :single-line="false" size="small" striped>
          <thead>
            <tr><th>名称</th><th>类别数</th><th>样本数</th><th>模态</th><th>说明</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in datasets" :key="d.id">
              <td>{{ d.name }}</td>
              <td>{{ d.num_classes ?? '-' }}</td>
              <td>{{ d.num_samples ?? '-' }}</td>
              <td>
                <n-space :size="4">
                  <n-tag v-for="m in (d.modalities || [])" :key="m" size="small">{{ m }}</n-tag>
                </n-space>
              </td>
              <td>{{ d.description || '-' }}</td>
            </tr>
          </tbody>
        </n-table>
        <EmptyState v-else description="暂无数据集数据，可在 evaluation/datasets/ 目录添加数据集配置" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NTable, NTag, NSpace } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getDatasets } from '../../api/evaluation'

const loading = ref(false)
const datasets = ref([])

onMounted(async () => {
  loading.value = true
  try { datasets.value = await getDatasets() } catch { datasets.value = [] }
  loading.value = false
})
</script>

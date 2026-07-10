<template>
  <div class="page-container">
    <n-card title="模型管理" size="small">
      <n-spin :show="loading">
        <n-grid v-if="models.length" :cols="3" :x-gap="16" :y-gap="16">
          <n-gi v-for="m in models" :key="m.id">
            <n-card size="small" hoverable>
              <template #header>
                <div class="flex-between">
                  <h4>{{ m.name }}</h4>
                  <n-tag size="small" type="info">{{ m.type }}</n-tag>
                </div>
              </template>
              <n-descriptions :column="1" size="small">
                <n-descriptions-item label="参数量">{{ m.params || '-' }}</n-descriptions-item>
                <n-descriptions-item label="说明">{{ m.description || '-' }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-gi>
        </n-grid>
        <EmptyState v-else description="暂无模型数据，可在 evaluation/models/ 目录添加模型配置" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NGrid, NGi, NTag, NDescriptions, NDescriptionsItem } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getModels } from '../../api/evaluation'

const loading = ref(false)
const models = ref([])

onMounted(async () => {
  loading.value = true
  try { models.value = await getModels() } catch { models.value = [] }
  loading.value = false
})
</script>

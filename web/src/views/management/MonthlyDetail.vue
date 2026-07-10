<template>
  <div class="page-container">
    <n-spin :show="loading">
      <n-card v-if="report">
        <template #header>
          <div class="flex-between">
            <div>
              <h2>{{ report.title }}</h2>
              <p class="text-secondary">作者：{{ report.author }} | {{ report.year }} 年 {{ report.month }} 月</p>
            </div>
            <n-button @click="router.back()">返回</n-button>
          </div>
        </template>
        <MarkdownRenderer :content="report.content" />
      </n-card>
      <EmptyState v-else description="未找到该月报" />
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NCard, NButton, NSpin } from 'naive-ui'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getMonthlyDetail } from '../../api/management'

const route = useRoute()
const router = useRouter()
const report = ref(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    report.value = await getMonthlyDetail(route.params.year, route.params.month, route.params.author)
  } catch { report.value = null }
  loading.value = false
})
</script>

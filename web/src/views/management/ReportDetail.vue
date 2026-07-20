<template>
  <div class="page-container">
    <n-spin :show="loading">
      <n-card v-if="report">
        <template #header>
          <div class="flex-between">
            <div>
              <h2>{{ report.title }}</h2>
              <p class="text-secondary">{{ metaLine }}</p>
            </div>
            <n-button @click="goBack">返回</n-button>
          </div>
        </template>
        <div v-if="report.tags && report.tags.length" class="detail-tags" style="margin-bottom: 12px;">
          <n-tag v-for="tag in report.tags" :key="tag" size="small" :bordered="false">{{ tag }}</n-tag>
        </div>
        <MarkdownRenderer :content="report.content" />
      </n-card>
      <EmptyState v-else :description="notFoundText" />
    </n-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NCard, NButton, NSpin, NTag } from 'naive-ui'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getDailyDetail, getWeeklyDetail, getMonthlyDetail } from '../../api/management'

const route = useRoute()
const router = useRouter()
const report = ref(null)
const loading = ref(false)

const type = computed(() => route.params.type)

const TYPE_LABELS = { daily: '日报', weekly: '周报', monthly: '月报' }

const metaLine = computed(() => {
  if (!report.value) return ''
  const r = report.value
  if (type.value === 'daily') return `作者：${r.author} | 日期：${r.date}`
  if (type.value === 'weekly') return `作者：${r.author} | ${r.year} 年第 ${r.week} 周`
  if (type.value === 'monthly') return `作者：${r.author} | ${r.year} 年 ${r.month} 月`
  return ''
})

const notFoundText = computed(() => `未找到该${TYPE_LABELS[type.value] || '报告'}`)

function goBack() {
  router.push(`/management/reports?tab=${type.value}`)
}

async function fetchReport() {
  loading.value = true
  report.value = null
  try {
    const p = route.params
    if (type.value === 'daily') {
      report.value = await getDailyDetail(p.date, p.author)
    } else if (type.value === 'weekly') {
      report.value = await getWeeklyDetail(p.year, p.week, p.author)
    } else if (type.value === 'monthly') {
      report.value = await getMonthlyDetail(p.year, p.month, p.author)
    }
  } catch {
    report.value = null
  }
  loading.value = false
}

onMounted(fetchReport)
</script>

<style scoped>
.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>

<template>
  <div class="page-container">
    <n-card title="日报" size="small">
      <template #header-extra>
        <n-space align="center">
          <n-select v-model:value="filters.author" :options="authorOptions" placeholder="全部成员" clearable size="small" style="width: 140px" />
          <n-date-picker v-model:value="filters.dateRange" type="month" size="small" clearable placeholder="选择月份" />
        </n-space>
      </template>
      <n-spin :show="loading">
        <n-table v-if="reports.length" :bordered="false" :single-line="false" size="small" striped>
          <thead>
            <tr>
              <th>日期</th>
              <th>作者</th>
              <th>标题</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredReports" :key="r.id">
              <td>{{ r.date }}</td>
              <td>{{ r.author }}</td>
              <td>{{ r.title }}</td>
              <td>
                <n-button text type="primary" @click="router.push(`/management/daily/${r.date}/${r.author}`)">查看</n-button>
              </td>
            </tr>
          </tbody>
        </n-table>
        <EmptyState v-else description="暂无日报，可在 management/daily/ 目录创建日报文件" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NSpin, NTable, NButton, NSpace, NSelect, NDatePicker } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getDailyList } from '../../api/management'

const router = useRouter()
const reports = ref([])
const loading = ref(false)
const filters = ref({ author: null, dateRange: null })

const authorOptions = computed(() => {
  const authors = [...new Set(reports.value.map(r => r.author))]
  return authors.map(a => ({ label: a, value: a }))
})

const filteredReports = computed(() => {
  let list = reports.value
  if (filters.value.author) list = list.filter(r => r.author === filters.value.author)
  if (filters.value.dateRange) {
    const d = new Date(filters.value.dateRange)
    const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    list = list.filter(r => r.date?.startsWith(ym))
  }
  return list
})

onMounted(async () => {
  loading.value = true
  try { reports.value = await getDailyList() } catch { reports.value = [] }
  loading.value = false
})
</script>

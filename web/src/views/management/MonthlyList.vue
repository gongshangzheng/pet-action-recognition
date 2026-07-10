<template>
  <div class="page-container">
    <n-card title="月报" size="small">
      <template #header-extra>
        <n-select v-model:value="filters.author" :options="authorOptions" placeholder="全部成员" clearable size="small" style="width: 140px" />
      </template>
      <n-spin :show="loading">
        <n-table v-if="reports.length" :bordered="false" :single-line="false" size="small" striped>
          <thead>
            <tr><th>年月</th><th>作者</th><th>标题</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredReports" :key="r.id">
              <td>{{ r.year }}-{{ r.month }}</td>
              <td>{{ r.author }}</td>
              <td>{{ r.title }}</td>
              <td><n-button text type="primary" @click="router.push(`/management/monthly/${r.year}/${r.month}/${r.author}`)">查看</n-button></td>
            </tr>
          </tbody>
        </n-table>
        <EmptyState v-else description="暂无月报" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NSpin, NTable, NButton, NSelect } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getMonthlyList } from '../../api/management'

const router = useRouter()
const reports = ref([])
const loading = ref(false)
const filters = ref({ author: null })

const authorOptions = computed(() => [...new Set(reports.value.map(r => r.author))].map(a => ({ label: a, value: a })))
const filteredReports = computed(() => filters.value.author ? reports.value.filter(r => r.author === filters.value.author) : reports.value)

onMounted(async () => {
  loading.value = true
  try { reports.value = await getMonthlyList() } catch { reports.value = [] }
  loading.value = false
})
</script>

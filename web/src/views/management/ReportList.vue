<template>
  <div class="page-container">
    <n-card size="small">
      <n-tabs :value="activeTab" type="line" @update:value="onTabChange">
        <!-- 日报 -->
        <n-tab-pane name="daily" tab="日报">
          <div class="tab-toolbar">
            <n-select v-model:value="dailyFilters.author" :options="dailyAuthorOptions" placeholder="全部成员" clearable size="small" style="width: 140px" />
            <n-date-picker v-model:value="dailyFilters.dateRange" type="month" size="small" clearable placeholder="选择月份" />
          </div>
          <n-spin :show="dailyLoading">
            <n-table v-if="dailyReports.length" :bordered="false" :single-line="false" size="small" striped>
              <thead><tr><th>日期</th><th>作者</th><th>标题</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="r in filteredDaily" :key="r.id">
                  <td>{{ r.date }}</td>
                  <td>{{ r.author }}</td>
                  <td>{{ r.title }}</td>
                  <td><n-button text type="primary" @click="router.push(`/management/reports/daily/${r.date}/${r.author}`)">查看</n-button></td>
                </tr>
              </tbody>
            </n-table>
            <EmptyState v-else description="暂无日报，可在 management/daily/ 目录创建日报文件" />
          </n-spin>
        </n-tab-pane>

        <!-- 周报 -->
        <n-tab-pane name="weekly" tab="周报">
          <div class="tab-toolbar">
            <n-select v-model:value="weeklyFilters.author" :options="weeklyAuthorOptions" placeholder="全部成员" clearable size="small" style="width: 140px" />
          </div>
          <n-spin :show="weeklyLoading">
            <n-table v-if="weeklyReports.length" :bordered="false" :single-line="false" size="small" striped>
              <thead><tr><th>年份</th><th>周次</th><th>作者</th><th>标题</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="r in filteredWeekly" :key="r.id">
                  <td>{{ r.year }}</td>
                  <td>第 {{ r.week }} 周</td>
                  <td>{{ r.author }}</td>
                  <td>{{ r.title }}</td>
                  <td><n-button text type="primary" @click="router.push(`/management/reports/weekly/${r.year}/${r.week}/${r.author}`)">查看</n-button></td>
                </tr>
              </tbody>
            </n-table>
            <EmptyState v-else description="暂无周报" />
          </n-spin>
        </n-tab-pane>

        <!-- 月报 -->
        <n-tab-pane name="monthly" tab="月报">
          <div class="tab-toolbar">
            <n-select v-model:value="monthlyFilters.author" :options="monthlyAuthorOptions" placeholder="全部成员" clearable size="small" style="width: 140px" />
          </div>
          <n-spin :show="monthlyLoading">
            <n-table v-if="monthlyReports.length" :bordered="false" :single-line="false" size="small" striped>
              <thead><tr><th>年月</th><th>作者</th><th>标题</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="r in filteredMonthly" :key="r.id">
                  <td>{{ r.year }}-{{ r.month }}</td>
                  <td>{{ r.author }}</td>
                  <td>{{ r.title }}</td>
                  <td><n-button text type="primary" @click="router.push(`/management/reports/monthly/${r.year}/${r.month}/${r.author}`)">查看</n-button></td>
                </tr>
              </tbody>
            </n-table>
            <EmptyState v-else description="暂无月报" />
          </n-spin>
        </n-tab-pane>

      </n-tabs>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NCard, NTabs, NTabPane, NSpin, NTable, NButton, NSelect, NDatePicker } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getDailyList, getWeeklyList, getMonthlyList } from '../../api/management'

const route = useRoute()
const router = useRouter()

const VALID_TABS = ['daily', 'weekly', 'monthly']
const activeTab = ref(VALID_TABS.includes(route.query.tab) ? route.query.tab : 'daily')

function onTabChange(name) {
  activeTab.value = name
  router.replace({ query: { ...route.query, tab: name } })
}

// ── 日报 ──
const dailyReports = ref([])
const dailyLoading = ref(false)
const dailyFilters = ref({ author: null, dateRange: null })
const dailyAuthorOptions = computed(() => [...new Set(dailyReports.value.map(r => r.author))].map(a => ({ label: a, value: a })))
const filteredDaily = computed(() => {
  let list = dailyReports.value
  if (dailyFilters.value.author) list = list.filter(r => r.author === dailyFilters.value.author)
  if (dailyFilters.value.dateRange) {
    const d = new Date(dailyFilters.value.dateRange)
    const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    list = list.filter(r => r.date?.startsWith(ym))
  }
  return list
})

// ── 周报 ──
const weeklyReports = ref([])
const weeklyLoading = ref(false)
const weeklyFilters = ref({ author: null })
const weeklyAuthorOptions = computed(() => [...new Set(weeklyReports.value.map(r => r.author))].map(a => ({ label: a, value: a })))
const filteredWeekly = computed(() => weeklyFilters.value.author ? weeklyReports.value.filter(r => r.author === weeklyFilters.value.author) : weeklyReports.value)

// ── 月报 ──
const monthlyReports = ref([])
const monthlyLoading = ref(false)
const monthlyFilters = ref({ author: null })
const monthlyAuthorOptions = computed(() => [...new Set(monthlyReports.value.map(r => r.author))].map(a => ({ label: a, value: a })))
const filteredMonthly = computed(() => monthlyFilters.value.author ? monthlyReports.value.filter(r => r.author === monthlyFilters.value.author) : monthlyReports.value)

// ── Lazy-load per tab ──
const loaded = ref({ daily: false, weekly: false, monthly: false })

async function loadTab(tab) {
  if (loaded.value[tab]) return
  loaded.value[tab] = true
  if (tab === 'daily') {
    dailyLoading.value = true
    try { dailyReports.value = await getDailyList() } catch { dailyReports.value = [] }
    dailyLoading.value = false
  } else if (tab === 'weekly') {
    weeklyLoading.value = true
    try { weeklyReports.value = await getWeeklyList() } catch { weeklyReports.value = [] }
    weeklyLoading.value = false
  } else if (tab === 'monthly') {
    monthlyLoading.value = true
    try { monthlyReports.value = await getMonthlyList() } catch { monthlyReports.value = [] }
    monthlyLoading.value = false
  }
}

onMounted(() => loadTab(activeTab.value))
watch(activeTab, (tab) => loadTab(tab))
</script>

<style scoped>
.tab-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>

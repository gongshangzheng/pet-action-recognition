<template>
  <div class="page-container">
    <n-card title="会议纪要" size="small">
      <n-spin :show="loading">
        <n-table v-if="meetings.length" :bordered="false" :single-line="false" size="small" striped>
          <thead>
            <tr><th>日期</th><th>参会人</th><th>记录人</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="m in meetings" :key="m.date">
              <td>{{ m.date }}</td>
              <td>{{ m.participants }}</td>
              <td>{{ m.recorder }}</td>
              <td><n-button text type="primary" @click="viewDetail(m)">查看</n-button></td>
            </tr>
          </tbody>
        </n-table>
        <EmptyState v-else description="暂无会议纪要" />
      </n-spin>
    </n-card>

    <n-modal v-model:show="showModal" preset="card" :title="`会议纪要 — ${current?.date || ''}`" style="width: 800px">
      <MarkdownRenderer v-if="current" :content="current.content" />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NTable, NButton, NModal } from 'naive-ui'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getMeetings, getMeetingDetail } from '../../api/management'

const loading = ref(false)
const meetings = ref([])
const showModal = ref(false)
const current = ref(null)

async function viewDetail(m) {
  try {
    current.value = await getMeetingDetail(m.date)
    showModal.value = true
  } catch {}
}

onMounted(async () => {
  loading.value = true
  try { meetings.value = await getMeetings() } catch { meetings.value = [] }
  loading.value = false
})
</script>

<template>
  <div class="page-container">
    <n-spin :show="loading">
      <n-grid v-if="members.length" :cols="3" :x-gap="16" :y-gap="16">
        <n-gi v-for="m in members" :key="m.id">
          <n-card hoverable @click="router.push(`/management/team/${m.id}`)">
            <div class="member-card">
              <n-avatar round size="large" :style="{ backgroundColor: avatarColor(m.id) }">
                {{ m.name.charAt(0) }}
              </n-avatar>
              <div class="member-info">
                <h3>{{ m.name }}</h3>
                <p class="member-role">{{ m.role }}</p>
                <p class="member-date">入职：{{ m.join_date }}</p>
              </div>
            </div>
            <template #footer>
              <n-ellipsis :line-clamp="1">
                <span class="text-secondary">研究方向：{{ m.research_direction || '待补充' }}</span>
              </n-ellipsis>
            </template>
          </n-card>
        </n-gi>
      </n-grid>
      <EmptyState v-else description="暂无团队成员" />
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NGrid, NGi, NCard, NAvatar, NSpin, NEllipsis } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTeamList } from '../../api/management'

const router = useRouter()
const members = ref([])
const loading = ref(false)

const colors = ['#4f46e5', '#0ea5e9', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6']
function avatarColor(id) {
  const idx = (id || '').charCodeAt(0) % colors.length
  return colors[idx]
}

onMounted(async () => {
  loading.value = true
  try {
    members.value = await getTeamList()
  } catch { members.value = [] }
  loading.value = false
})
</script>

<style scoped>
.member-card {
  display: flex;
  align-items: center;
  gap: 16px;
}
.member-info h3 { margin-bottom: 4px; }
.member-role { font-size: 13px; color: #6b7280; margin-bottom: 2px; }
.member-date { font-size: 12px; color: #9ca3af; }
</style>

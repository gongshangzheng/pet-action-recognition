<template>
  <div class="page-container">
    <n-spin :show="loading">
      <n-grid v-if="members.length" cols="1 640:2 900:3" responsive="screen" :x-gap="16" :y-gap="16">
        <n-gi v-for="m in members" :key="m.id">
          <n-card hoverable @click="router.push(`/management/team/${m.id}`)">
            <div class="member-card">
              <n-avatar round size="large" :style="{ backgroundColor: avatarColor(m.id) }">
                {{ m.name.charAt(0) }}
              </n-avatar>
              <div class="member-info">
                <h2 class="member-name">{{ m.name }}</h2>
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

// 头像底色的白字需 ≥4.5:1（原 #0ea5e9 2.77 / #f59e0b 2.15 / #10b981 2.54 均不达标）
const colors = ['#4f46e5', '#0369a1', '#b45309', '#047857', '#b91c1c', '#6d28d9']
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
.member-info h2 { margin-bottom: 4px; font-size: 17px; font-weight: 600; }
.member-role { font-size: 13px; color: var(--color-text-secondary); margin-bottom: 2px; }
.member-date { font-size: 12px; color: var(--color-text-dim); }
</style>

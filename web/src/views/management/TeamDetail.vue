<template>
  <div class="page-container">
    <n-spin :show="loading">
      <n-card v-if="member">
        <template #header>
          <div class="flex-between">
            <div class="flex" style="align-items: center; gap: 16px">
              <n-avatar round size="large" :style="{ backgroundColor: '#4f46e5' }">
                {{ member.name?.charAt(0) }}
              </n-avatar>
              <div>
                <h2>{{ member.name }}</h2>
                <p class="text-secondary">{{ member.role }}</p>
              </div>
            </div>
            <n-button @click="router.back()">返回</n-button>
          </div>
        </template>
        <n-descriptions :column="2" bordered>
          <n-descriptions-item label="姓名">{{ member.name }}</n-descriptions-item>
          <n-descriptions-item label="英文标识">{{ member.id }}</n-descriptions-item>
          <n-descriptions-item label="角色">{{ member.role }}</n-descriptions-item>
          <n-descriptions-item label="入职日期">{{ member.join_date }}</n-descriptions-item>
          <n-descriptions-item label="研究方向" :span="2">{{ member.research_direction || '待补充' }}</n-descriptions-item>
        </n-descriptions>

        <n-divider />

        <h3>技术栈</h3>
        <n-space v-if="member.tech_stack?.length">
          <n-tag v-for="t in member.tech_stack" :key="t" type="info" size="small">{{ t }}</n-tag>
        </n-space>
        <p v-else class="text-light">待补充</p>

        <n-divider />

        <h3>负责模块</h3>
        <ul v-if="member.responsible_modules?.length">
          <li v-for="m in member.responsible_modules" :key="m">{{ m }}</li>
        </ul>
        <p v-else class="text-light">待补充</p>
      </n-card>
      <EmptyState v-else description="未找到该成员" />
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard, NAvatar, NButton, NSpin, NDescriptions, NDescriptionsItem,
  NDivider, NSpace, NTag,
} from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getTeamMember } from '../../api/management'

const route = useRoute()
const router = useRouter()
const member = ref(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    member.value = await getTeamMember(route.params.id)
  } catch { member.value = null }
  loading.value = false
})
</script>

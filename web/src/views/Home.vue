<template>
  <div class="page-container home-page">
    <n-grid :cols="3" :x-gap="16" :y-gap="16">
      <n-gi>
        <n-card class="module-card management" hoverable @click="router.push('/management/team')">
          <div class="module-icon">PM</div>
          <h3>项目管理</h3>
          <p class="module-desc">团队档案、日报/周报/月报、任务看板、里程碑</p>
          <div class="module-stats">
            <n-statistic label="团队成员" :value="stats.teamCount" />
          </div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="module-card papers" hoverable @click="router.push('/papers/list')">
          <div class="module-icon">PP</div>
          <h3>论文搜集</h3>
          <p class="module-desc">多源聚合、智能分类、精读笔记</p>
          <div class="module-stats">
            <n-statistic label="论文数量" :value="stats.paperCount" />
          </div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="module-card evaluation" hoverable @click="router.push('/evaluation/results')">
          <div class="module-icon">EV</div>
          <h3>评测体系</h3>
          <p class="module-desc">模型管理、评测运行、结果对比</p>
          <div class="module-stats">
            <n-statistic label="评测模型" :value="stats.modelCount" />
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-grid :cols="2" :x-gap="16" :y-gap="16" style="margin-top: 16px">
      <n-gi>
        <n-card title="项目里程碑" size="small">
          <n-spin :show="loadingMilestones">
            <div v-if="milestones.length" class="milestone-preview">
              <div v-for="m in milestones.slice(0, 4)" :key="m.name" class="milestone-item">
                <StatusBadge :status="m.status" />
                <span class="milestone-name">{{ m.name }}</span>
                <span class="milestone-date">{{ m.target_date || '未定' }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无里程碑数据" />
          </n-spin>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="技术路线" size="small">
          <n-space direction="vertical" :size="8">
            <n-tag v-for="route in techRoutes" :key="route" type="info" size="small" round>
              {{ route }}
            </n-tag>
          </n-space>
        </n-card>
      </n-gi>
    </n-grid>

    <n-card title="评测模型概览" size="small" style="margin-top: 16px">
      <n-spin :show="loadingModels">
        <n-table v-if="models.length" :bordered="false" :single-line="false" size="small">
          <thead>
            <tr>
              <th>模型</th>
              <th>类型</th>
              <th>参数量</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in models" :key="m.id">
              <td>{{ m.name }}</td>
              <td>{{ m.type }}</td>
              <td>{{ m.params || '-' }}</td>
              <td>{{ m.description || '-' }}</td>
            </tr>
          </tbody>
        </n-table>
        <EmptyState v-else description="暂无模型数据" />
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NGrid, NGi, NCard, NStatistic, NSpin, NTable, NTag, NSpace,
} from 'naive-ui'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { getMilestones, getTeamList } from '../api/management'
import { getModels } from '../api/evaluation'
import { getPaperStats } from '../api/papers'

const router = useRouter()

const stats = ref({ teamCount: 0, paperCount: 0, modelCount: 0 })
const milestones = ref([])
const models = ref([])
const loadingMilestones = ref(false)
const loadingModels = ref(false)

const techRoutes = [
  '2D CNN', '3D CNN', 'Transformer', 'Skeleton',
  '多模态', '视频基础模型', 'Stitching-Retargeting', 'PMTNet',
]

onMounted(async () => {
  loadingMilestones.value = true
  loadingModels.value = true
  try {
    const team = await getTeamList().catch(() => [])
    stats.value.teamCount = team?.length || 0
  } catch {}
  try {
    const paperStats = await getPaperStats().catch(() => ({ total: 0 }))
    stats.value.paperCount = paperStats?.total || 0
  } catch {}
  try {
    const ms = await getMilestones().catch(() => [])
    milestones.value = ms || []
  } catch {} finally { loadingMilestones.value = false }
  try {
    const mdls = await getModels().catch(() => [])
    models.value = mdls || []
    stats.value.modelCount = mdls?.length || 0
  } catch {} finally { loadingModels.value = false }
})
</script>

<style scoped lang="scss">
.module-card {
  cursor: pointer;
  text-align: center;
  transition: transform 0.2s;

  &:hover { transform: translateY(-4px); }

  .module-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    margin: 0 auto 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 700;
    color: #fff;
  }

  &.management .module-icon { background: #4f46e5; }
  &.papers .module-icon { background: #0ea5e9; }
  &.evaluation .module-icon { background: #f59e0b; }

  h3 { margin-bottom: 8px; }
  .module-desc { font-size: 13px; color: #6b7280; margin-bottom: 12px; }
}

.milestone-preview {
  .milestone-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #f3f4f6;

    .milestone-name { flex: 1; font-size: 14px; }
    .milestone-date { font-size: 13px; color: #9ca3af; }
  }
}
</style>

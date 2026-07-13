<template>
  <n-layout has-sider style="height: 100vh">
    <!-- 侧边栏 -->
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="sidebar-logo">
        <span v-if="!collapsed" class="logo-text">宠物动作识别</span>
        <span v-else class="logo-icon">PAR</span>
      </div>
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        :expanded-keys="expandedKeys"
        @update:value="handleMenuSelect"
        @update:expanded-keys="handleExpandUpdate"
      />
    </n-layout-sider>

    <!-- 主内容区 -->
    <n-layout>
      <!-- 顶部 -->
      <n-layout-header bordered class="app-header">
        <div class="header-left">
          <n-breadcrumb>
            <n-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </n-breadcrumb-item>
          </n-breadcrumb>
        </div>
        <div class="header-right">
          <span class="header-date">{{ today }}</span>
          <n-button quaternary circle class="theme-toggle" @click="themeStore.toggle">
            <template #icon>
              <n-icon size="18">
                <sunny-outline v-if="themeStore.isDark" />
                <moon-outline v-else />
              </n-icon>
            </template>
          </n-button>
        </div>
      </n-layout-header>

      <!-- 内容区 -->
      <n-layout-content class="app-content" :native-scrollbar="false">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { ref, computed, h, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NLayout, NLayoutSider, NLayoutHeader, NLayoutContent,
  NMenu, NBreadcrumb, NBreadcrumbItem, NButton, NIcon,
} from 'naive-ui'
import {
  HomeOutline, PeopleOutline, GitBranchOutline, CalendarOutline,
  DocumentTextOutline, GridOutline, FlagOutline, ChatbubblesOutline,
  SearchOutline, SettingsOutline, FlaskOutline, BarChartOutline,
  CubeOutline, LayersOutline, SunnyOutline, MoonOutline,
} from '@vicons/ionicons5'
import { useThemeStore } from '../stores/theme'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const collapsed = ref(false)
const manualExpanded = ref(null)

const expandedKeys = computed(() => {
  if (manualExpanded.value) return manualExpanded.value
  const path = route.path
  if (path.startsWith('/management')) return ['management']
  if (path.startsWith('/papers')) return ['papers']
  if (path.startsWith('/evaluation')) return ['evaluation']
  return []
})

function handleExpandUpdate(keys) {
  manualExpanded.value = keys
}

function renderIcon(icon) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = [
  {
    label: '首页',
    key: '/',
    icon: renderIcon(HomeOutline),
  },
  {
    label: '项目管理',
    key: 'management',
    icon: renderIcon(PeopleOutline),
    children: [
      { label: '项目树', key: '/management/projects', icon: renderIcon(GitBranchOutline) },
      { label: '团队成员', key: '/management/team', icon: renderIcon(PeopleOutline) },
      { label: '日报', key: '/management/daily', icon: renderIcon(CalendarOutline) },
      { label: '周报', key: '/management/weekly', icon: renderIcon(DocumentTextOutline) },
      { label: '月报', key: '/management/monthly', icon: renderIcon(DocumentTextOutline) },
      { label: '任务看板', key: '/management/tasks', icon: renderIcon(GridOutline) },
      { label: '里程碑', key: '/management/milestones', icon: renderIcon(FlagOutline) },
      { label: '会议纪要', key: '/management/meetings', icon: renderIcon(ChatbubblesOutline) },
    ],
  },
  {
    label: '论文搜集',
    key: 'papers',
    icon: renderIcon(SearchOutline),
    children: [
      { label: '论文列表', key: '/papers/list', icon: renderIcon(DocumentTextOutline) },
      { label: '数据源配置', key: '/papers/config', icon: renderIcon(SettingsOutline) },
    ],
  },
  {
    label: '评测体系',
    key: 'evaluation',
    icon: renderIcon(FlaskOutline),
    children: [
      { label: '评测运行', key: '/evaluation/run', icon: renderIcon(FlaskOutline) },
      { label: '评测结果', key: '/evaluation/results', icon: renderIcon(BarChartOutline) },
      { label: '模型管理', key: '/evaluation/models', icon: renderIcon(CubeOutline) },
      { label: '数据集管理', key: '/evaluation/datasets', icon: renderIcon(LayersOutline) },
    ],
  },
]

const activeKey = computed(() => {
  const path = route.path
  // 匹配最长前缀
  const allKeys = [
    '/', '/management/projects', '/management/team', '/management/daily', '/management/weekly',
    '/management/monthly', '/management/tasks', '/management/milestones',
    '/management/meetings', '/papers/list', '/papers/config',
    '/evaluation/run', '/evaluation/results', '/evaluation/models', '/evaluation/datasets',
  ]
  let best = '/'
  for (const k of allKeys) {
    if (path.startsWith(k) && k.length > best.length) best = k
  }
  return best
})

watch(() => route.path, () => { manualExpanded.value = null })

function handleMenuSelect(key) {
  router.push(key)
}

const breadcrumbs = computed(() => {
  const items = [{ title: '首页', path: '/' }]
  const moduleMap = {
    management: '项目管理',
    papers: '论文搜集',
    evaluation: '评测体系',
  }
  if (route.meta.module && moduleMap[route.meta.module]) {
    items.push({ title: moduleMap[route.meta.module], path: '' })
  }
  if (route.meta.title) {
    items.push({ title: route.meta.title, path: route.path })
  }
  return items
})

const today = computed(() => {
  const d = new Date()
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 星期${weekdays[d.getDay()]}`
})
</script>

<style scoped lang="scss">
.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #2a2a3e;
  color: #fff;
  font-weight: 700;

  .logo-text {
    font-size: 16px;
    white-space: nowrap;
  }
  .logo-icon {
    font-size: 14px;
  }
}

.app-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-date {
  font-size: 13px;
  color: var(--color-text-dim);
}

.theme-toggle {
  color: var(--color-text-secondary);
}

.app-content {
  height: calc(100vh - 56px);
  padding: 0;
}
</style>

<template>
  <n-layout has-sider style="height: 100vh">
    <!-- 侧边栏 -->
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="56"
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
        :collapsed-width="56"
        :collapsed-icon-size="18"
        :options="visibleMenuOptions"
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
            <n-breadcrumb-item
              v-for="item in breadcrumbs"
              :key="item.path || item.title"
              :to="item.path || undefined"
              :clickable="!!item.path"
              @click="onBreadcrumbClick(item)"
            >
              {{ item.title }}
            </n-breadcrumb-item>
          </n-breadcrumb>
        </div>
        <div class="header-right">
          <span class="header-date">{{ today }}</span>
          <n-popover trigger="click" placement="bottom-end" :show-arrow="false">
            <template #trigger>
              <n-button quaternary circle class="theme-toggle" title="主题与图标">
                <template #icon>
                  <n-icon size="18">
                    <color-palette-outline />
                  </n-icon>
                </template>
              </n-button>
            </template>
            <div class="theme-panel">
              <div class="theme-panel-title">主题色</div>
              <div class="accent-grid">
                <button
                  v-for="a in ACCENTS"
                  :key="a.key"
                  class="accent-swatch"
                  :class="{ active: themeStore.accent === a.key }"
                  :title="a.label"
                  :style="{ backgroundColor: swatchColor(a), color: readableOn(swatchColor(a)) }"
                  @click="themeStore.setAccent(a.key)"
                >
                  <n-icon v-if="themeStore.accent === a.key" size="14"><checkmark-outline /></n-icon>
                </button>
              </div>
              <div class="theme-panel-title">图标</div>
              <div class="favicon-grid">
                <button
                  v-for="f in FAVICONS"
                  :key="f.key"
                  class="favicon-option"
                  :class="{ active: themeStore.favicon === f.key }"
                  :title="f.label"
                  @click="themeStore.setFavicon(f.key)"
                  v-html="faviconSvg(f.key, themeStore.accentPrimary)"
                ></button>
              </div>
            </div>
          </n-popover>
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
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <keep-alive :include="['PaperList', 'TrainResults', 'DatasetBrowser', 'ReportPage']">
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { ref, computed, h, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NLayout, NLayoutSider, NLayoutHeader, NLayoutContent,
  NMenu, NBreadcrumb, NBreadcrumbItem, NButton, NIcon, NPopover,
} from 'naive-ui'
import {
  HomeOutline, PeopleOutline, GitBranchOutline,
  DocumentTextOutline, GridOutline, FlagOutline, ChatbubblesOutline,
  SearchOutline, SettingsOutline, FlaskOutline, BarChartOutline,
  CubeOutline, LayersOutline, SchoolOutline, FilmOutline, BookOutline,
  SunnyOutline, MoonOutline, VideocamOutline,
  ColorPaletteOutline, CheckmarkOutline,
} from '@vicons/ionicons5'
import { useThemeStore } from '../stores/theme'
import { SIDEBAR_DEFAULT_COLLAPSED } from '../config/layout'
import { ACCENTS, readableOn } from '../config/theme'
import { FAVICONS, faviconSvg } from '../config/favicon'
import { HIDDEN_KEYS, filterHidden } from '../config/hidden'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()

const SIDEBAR_COLLAPSED_KEY = 'app.sidebar-collapsed'
// 旧 key 兼容读取：迁移到通用 key 后仍能恢复用户此前折叠偏好
const LEGACY_SIDEBAR_COLLAPSED_KEY = 'pet-action-recognition-sidebar-collapsed'

function readCollapsed() {
  try {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY) ??
      localStorage.getItem(LEGACY_SIDEBAR_COLLAPSED_KEY)
    if (stored === null) return SIDEBAR_DEFAULT_COLLAPSED
    return stored === '1'
  } catch {
    return SIDEBAR_DEFAULT_COLLAPSED
  }
}

const collapsed = ref(readCollapsed())

// 持久化用户偏好（不设 immediate：避免初始化时把默认值写进存储，
// 否则用户永远无法通过删除该 key 回到默认值）
watch(collapsed, (value) => {
  try { localStorage.setItem(SIDEBAR_COLLAPSED_KEY, value ? '1' : '0') } catch { /* ignore */ }
})

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

// 调色盘色块取当前模式下的色值
function swatchColor(accent) {
  return themeStore.isDark ? accent.dark : accent.light
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
      { label: '团队成员', key: '/management/team', icon: renderIcon(PeopleOutline), show: false },
      { label: '报告', key: '/management/reports', icon: renderIcon(DocumentTextOutline), show: false },
      { label: '任务看板', key: '/management/tasks', icon: renderIcon(GridOutline), show: false },
      { label: '里程碑', key: '/management/milestones', icon: renderIcon(FlagOutline), show: false },
      { label: '会议纪要', key: '/management/meetings', icon: renderIcon(ChatbubblesOutline), show: false },
      { label: '文档', key: '/management/docs', icon: renderIcon(BookOutline) },
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
      { label: 'Speed Run', key: '/evaluation/speedrun', icon: renderIcon(FilmOutline) },
      { label: '评测结果', key: '/evaluation/results', icon: renderIcon(BarChartOutline) },
      { label: '模型管理', key: '/evaluation/models', icon: renderIcon(CubeOutline) },
      { label: '评测配置', key: '/evaluation/configs', icon: renderIcon(SettingsOutline) },
    ],
  },
  {
    label: '数据集',
    key: 'datasets',
    icon: renderIcon(LayersOutline),
    children: [
      { label: '数据集浏览', key: '/datasets', icon: renderIcon(LayersOutline) },
    ],
  },
  {
    label: '实时视频流',
    key: '/live',
    icon: renderIcon(VideocamOutline),
  },
  {
    label: '训练体系',
    key: 'training',
    icon: renderIcon(SchoolOutline),
    children: [
      { label: '训练运行', key: '/training/run', icon: renderIcon(SchoolOutline) },
      { label: '训练结果', key: '/training/results', icon: renderIcon(BarChartOutline) },
      { label: '模型配置', key: '/training/models', icon: renderIcon(CubeOutline) },
      { label: '训练配置', key: '/training/configs', icon: renderIcon(SettingsOutline) },
    ],
  },
]

// 按 HIDDEN_KEYS 过滤后的菜单（叶子命中 path 摘除；分组命中摘整组；组内叶子全部隐藏时整组摘除）
const visibleMenuOptions = computed(() => filterHidden(menuOptions, HIDDEN_KEYS))

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/management/reports')) return '/management/reports'
  if (path.startsWith('/management/docs')) return '/management/docs'
  // 匹配最长前缀
  const allKeys = [
    '/', '/management/projects', '/management/team',
    '/management/tasks', '/management/milestones',
    '/management/meetings', '/management/docs', '/papers/list', '/papers/config',
    '/evaluation/run', '/evaluation/speedrun', '/evaluation/results', '/evaluation/outputs', '/evaluation/models', '/evaluation/configs',
    '/datasets',
    '/live',
    '/training/run', '/training/results', '/training/models', '/training/configs',
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

function onBreadcrumbClick(item) {
  if (item.path && item.path !== route.path) router.push(item.path)
}

// 模块 -> 模块首页路径（让 breadcrumb 的模块项可点回退）
const MODULE_PATH = {
  management: '/management/projects',
  papers: '/papers/list',
  evaluation: '/evaluation/run',
  training: '/training/run',
}

const breadcrumbs = computed(() => {
  const items = [{ title: '首页', path: '/' }]
  const moduleMap = {
    management: '项目管理',
    papers: '论文搜集',
    evaluation: '评测体系',
    training: '训练体系',
  }
  if (route.meta.module && moduleMap[route.meta.module]) {
    items.push({ title: moduleMap[route.meta.module], path: MODULE_PATH[route.meta.module] || '' })
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
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-heading);
  font-weight: 700;

  .logo-text {
    font-size: 16px;
    white-space: nowrap;
  }
  .logo-icon {
    font-size: 13px;
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

.theme-panel {
  width: 172px;
}

.theme-panel-title {
  font-size: 12px;
  color: var(--color-text-dim);
  margin-bottom: 8px;

  & + .accent-grid,
  & + .favicon-grid {
    margin-bottom: 14px;
  }
}

.accent-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.accent-swatch {
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 50%;
  border: 2px solid transparent;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s, border-color 0.15s;

  &:hover {
    transform: scale(1.08);
  }

  &.active {
    border-color: var(--color-text);
  }
}

.favicon-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.favicon-option {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  border: 2px solid transparent;
  background: none;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.15s, border-color 0.15s;

  :deep(svg) {
    display: block;
    width: 100%;
    height: 100%;
  }

  &:hover {
    transform: scale(1.08);
  }

  &.active {
    border-color: var(--color-text);
  }
}

.app-content {
  height: calc(100vh - 56px);
  padding: 0;

  :deep(.n-scrollbar-content) {
    height: 100%;
  }

  :deep(.n-scrollbar-content > *) {
    min-height: 100%;
  }
}
</style>

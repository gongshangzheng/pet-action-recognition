<template>
  <div class="wiki-page">
    <!-- Left sidebar: meeting list -->
    <aside class="wiki-sidebar">
      <div class="wiki-sidebar-inner">
        <div class="wiki-sidebar-title">会议纪要</div>
        <nav class="wiki-sidebar-nav">
          <a
            v-for="m in meetings"
            :key="m.date"
            class="wiki-sidebar-link"
            :class="{ active: currentDate === m.date }"
            @click.prevent="navigateTo(m.date)"
          >
            {{ m.date }}
            <span v-if="m.participants" class="wiki-sidebar-sub">{{ m.participants }}</span>
          </a>
        </nav>
        <div v-if="!meetings.length && !listLoading" class="wiki-sidebar-empty">暂无会议纪要</div>
      </div>
    </aside>

    <!-- Mobile selector -->
    <div class="wiki-mobile-select">
      <n-select
        :value="currentDate"
        :options="mobileOptions"
        placeholder="选择会议"
        size="small"
        @update:value="navigateTo"
      />
    </div>

    <!-- Center: article -->
    <article class="wiki-article">
      <n-spin :show="loading">
        <div v-if="current" class="wiki-content">
          <header class="wiki-header">
            <h1>会议纪要 — {{ current.date }}</h1>
            <div class="wiki-meta">
              <span v-if="current.participants">参会人：{{ current.participants }}</span>
              <span v-if="current.recorder">记录人：{{ current.recorder }}</span>
            </div>
          </header>
          <div class="wiki-body">
            <MarkdownRenderer :content="current.content" />
          </div>
        </div>
        <div v-else-if="!loading" class="wiki-empty">
          <EmptyState :description="meetings.length ? '请从左侧选择一次会议' : '暂无会议纪要，可在 management/meetings/ 目录创建会议文件'" />
        </div>
      </n-spin>
    </article>

    <!-- Right TOC -->
    <aside v-if="tocItems.length" class="wiki-toc">
      <div class="wiki-toc-inner">
        <div class="wiki-toc-title">目录</div>
        <nav>
          <a
            v-for="item in tocItems"
            :key="item.slug"
            class="wiki-toc-link"
            :class="{ 'level-3': item.level === 3 }"
            @click.prevent="scrollToHeading(item.slug)"
          >
            {{ item.text }}
          </a>
        </nav>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NSpin, NSelect } from 'naive-ui'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getMeetings, getMeetingDetail } from '../../api/management'
import { extractToc } from '../../utils/markdown'

const route = useRoute()
const router = useRouter()

const meetings = ref([])
const current = ref(null)
const loading = ref(false)
const listLoading = ref(false)

const currentDate = computed(() => route.params.date || '')
const tocItems = computed(() => current.value ? extractToc(current.value.content) : [])

const mobileOptions = computed(() =>
  meetings.value.map(m => ({ label: `${m.date}${m.participants ? ` — ${m.participants}` : ''}`, value: m.date }))
)

function navigateTo(date) {
  if (date === currentDate.value) return
  router.push(`/management/meetings/${date}`)
}

function scrollToHeading(slug) {
  const el = document.getElementById(slug)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function fetchMeeting(date) {
  if (!date) {
    current.value = null
    return
  }
  loading.value = true
  current.value = null
  try {
    current.value = await getMeetingDetail(date)
    await nextTick()
  } catch {
    current.value = null
  }
  loading.value = false
}

async function fetchMeetingList() {
  listLoading.value = true
  try {
    meetings.value = await getMeetings()
  } catch {
    meetings.value = []
  }
  listLoading.value = false
}

onMounted(async () => {
  await fetchMeetingList()
  if (currentDate.value) {
    await fetchMeeting(currentDate.value)
  } else if (meetings.value.length) {
    router.replace(`/management/meetings/${meetings.value[0].date}`)
  }
})

watch(currentDate, (date) => {
  if (date) fetchMeeting(date)
})
</script>

<style scoped lang="scss">
.wiki-page {
  display: flex;
  gap: 24px;
  padding: 20px 24px;
  min-height: 100%;

  // 窄屏：左侧导航收起为顶部下拉，三栏变单栏（否则下拉作为 flex 项会把正文挤没）
  @media (max-width: 1023px) {
    flex-direction: column;
    gap: 12px;
    padding: 16px;
  }
}

.wiki-sidebar {
  display: none;
  width: 210px;
  flex-shrink: 0;
  @media (min-width: 1024px) { display: block; }
}

.wiki-sidebar-inner {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
  padding-right: 8px;
}

.wiki-sidebar-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
  padding: 8px 10px 4px;
}

.wiki-sidebar-empty {
  font-size: 13px;
  color: var(--color-text-dim);
  padding: 8px 10px;
}

.wiki-sidebar-link {
  display: block;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
  text-decoration: none;
  margin-bottom: 2px;

  &:hover {
    background: var(--color-hover);
    color: var(--color-text);
  }
  &.active {
    background: var(--color-selected);
    color: var(--color-primary);
    font-weight: 500;
  }
}

.wiki-sidebar-sub {
  display: block;
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-dim);
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wiki-mobile-select {
  display: block;
  width: 100%;
  margin-bottom: 12px;
  @media (min-width: 1024px) { display: none; }
}

.wiki-article {
  flex: 1;
  min-width: 0;
}

.wiki-content {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 24px;
}

.wiki-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
  h1 {
    font-size: 24px;
    font-weight: 700;
    margin: 0 0 8px;
    line-height: 1.3;
  }
}

.wiki-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--color-text-dim);
  flex-wrap: wrap;
}

.wiki-body { line-height: 1.7; }

.wiki-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.wiki-toc {
  display: none;
  width: 180px;
  flex-shrink: 0;
  @media (min-width: 1280px) { display: block; }
}

.wiki-toc-inner {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
}

.wiki-toc-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
  padding: 8px 10px 4px;
}

.wiki-toc-link {
  display: block;
  padding: 3px 10px;
  border-left: 2px solid var(--color-border);
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text-dim);
  cursor: pointer;
  transition: background-color 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
  text-decoration: none;

  &:hover {
    color: var(--color-text);
    border-left-color: var(--color-primary);
  }
  &.level-3 { padding-left: 20px; }
}
</style>

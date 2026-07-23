<template>
  <div class="doc-page">
    <!-- Left sidebar: doc list -->
    <aside class="doc-sidebar">
      <div class="doc-sidebar-inner">
        <div class="doc-sidebar-title">文档</div>
        <nav class="doc-sidebar-nav">
          <a
            v-for="doc in docsList"
            :key="doc.slug"
            class="doc-sidebar-link"
            :class="{ active: currentSlug === doc.slug }"
            @click.prevent="navigateTo(doc.slug)"
          >
            {{ doc.title || doc.slug }}
          </a>
        </nav>
        <div v-if="!docsList.length && !listLoading" class="doc-sidebar-empty">暂无文档</div>
      </div>
    </aside>

    <!-- Mobile doc selector -->
    <div class="doc-mobile-select">
      <n-select
        :value="currentSlug"
        :options="mobileOptions"
        placeholder="选择文档"
        size="small"
        @update:value="navigateTo"
      />
    </div>

    <!-- Center: article -->
    <article class="doc-article">
      <n-spin :show="loading">
        <div v-if="currentDoc" class="doc-content">
          <header class="doc-header">
            <h1>{{ currentDoc.title }}</h1>
            <div class="doc-meta">
              <span v-if="currentDoc.author">{{ currentDoc.author }}</span>
              <span v-if="currentDoc.date">{{ currentDoc.date }}</span>
              <n-tag
                v-for="tag in (currentDoc.tags || [])"
                :key="tag"
                size="small"
                :bordered="false"
              >{{ tag }}</n-tag>
            </div>
            <p v-if="currentDoc.summary" class="doc-summary">{{ currentDoc.summary }}</p>
          </header>
          <div class="doc-body">
            <MarkdownRenderer :content="bodyContent" />
          </div>
        </div>
        <div v-else-if="!loading" class="doc-empty">
          <EmptyState description="请从左侧选择一篇文档" />
        </div>
      </n-spin>
    </article>

    <!-- Right TOC -->
    <aside v-if="tocItems.length" class="doc-toc">
      <div class="doc-toc-inner">
        <div class="doc-toc-title">目录</div>
        <nav>
          <a
            v-for="item in tocItems"
            :key="item.slug"
            class="doc-toc-link"
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
import { NSpin, NTag, NSelect } from 'naive-ui'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getDocList, getDocDetail } from '../../api/management'
import { extractToc, slugify } from '../../utils/markdown'

const route = useRoute()
const router = useRouter()

const docsList = ref([])
const currentDoc = ref(null)
const loading = ref(false)
const listLoading = ref(false)

const currentSlug = computed(() => route.params.slug || '')
const tocItems = computed(() => currentDoc.value ? extractToc(currentDoc.value.content) : [])
const bodyContent = computed(() =>
  currentDoc.value ? currentDoc.value.content.replace(/^# .+\n*/gm, '') : ''
)

const mobileOptions = computed(() =>
  docsList.value.map(d => ({ label: d.title || d.slug, value: d.slug }))
)

function navigateTo(slug) {
  if (slug === currentSlug.value) return
  router.push(`/management/docs/${slug}`)
}

function scrollToHeading(slug) {
  const el = document.getElementById(slug)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function fetchDoc(slug) {
  if (!slug) {
    currentDoc.value = null
    return
  }
  loading.value = true
  currentDoc.value = null
  try {
    currentDoc.value = await getDocDetail(slug)
    await nextTick()
  } catch {
    currentDoc.value = null
  }
  loading.value = false
}

async function fetchDocList() {
  listLoading.value = true
  try {
    docsList.value = await getDocList()
  } catch {
    docsList.value = []
  }
  listLoading.value = false
}

onMounted(async () => {
  await fetchDocList()
  if (currentSlug.value) {
    await fetchDoc(currentSlug.value)
  } else if (docsList.value.length) {
    router.replace(`/management/docs/${docsList.value[0].slug}`)
  }
})

watch(currentSlug, (slug) => {
  if (slug) fetchDoc(slug)
})
</script>

<style scoped lang="scss">
.doc-page {
  display: flex;
  gap: 24px;
  padding: 20px 24px;
  min-height: 100%;
}

// Left sidebar
.doc-sidebar {
  display: none;
  width: 210px;
  flex-shrink: 0;

  @media (min-width: 1024px) {
    display: block;
  }
}

.doc-sidebar-inner {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
  padding-right: 8px;
}

.doc-sidebar-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
  padding: 8px 10px 4px;
}

.doc-sidebar-empty {
  font-size: 13px;
  color: var(--color-text-dim);
  padding: 8px 10px;
}

.doc-sidebar-link {
  display: block;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s;
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

// Mobile selector
.doc-mobile-select {
  display: block;
  margin-bottom: 12px;

  @media (min-width: 1024px) {
    display: none;
  }
}

// Center article
.doc-article {
  flex: 1;
  min-width: 0;
}

.doc-content {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 24px;
}

.doc-header {
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

.doc-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-dim);
  flex-wrap: wrap;
}

.doc-summary {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.doc-body {
  line-height: 1.7;
}

.doc-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

// Right TOC
.doc-toc {
  display: none;
  width: 180px;
  flex-shrink: 0;

  @media (min-width: 1280px) {
    display: block;
  }
}

.doc-toc-inner {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
}

.doc-toc-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
  padding: 8px 10px 4px;
}

.doc-toc-link {
  display: block;
  padding: 3px 10px;
  border-left: 2px solid var(--color-border);
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text-dim);
  cursor: pointer;
  transition: all 0.15s;
  text-decoration: none;

  &:hover {
    color: var(--color-text);
    border-left-color: var(--color-primary);
  }

  &.level-3 {
    padding-left: 20px;
  }
}
</style>

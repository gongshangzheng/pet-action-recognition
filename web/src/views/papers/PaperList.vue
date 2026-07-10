<template>
  <div class="page-container">
    <n-card size="small">
      <template #header>
        <div class="flex-between">
          <div class="header-left">
            <h3>论文列表</h3>
            <n-tag v-if="stats.total" size="small" type="info" round>共 {{ stats.total }} 篇</n-tag>
          </div>
          <n-button size="small" type="primary" circle @click="showFetchModal = true" title="添加论文">
            <template #icon><n-icon><AddOutline /></n-icon></template>
          </n-button>
        </div>
      </template>

      <!-- 统计栏 -->
      <div v-if="stats.total" class="stats-bar">
        <div class="stat-item">
          <span class="stat-num">{{ stats.total }}</span>
          <span class="stat-label">论文总数</span>
        </div>
        <div class="stat-divider" />
        <template v-for="(count, source) in (stats.by_source || {})" :key="source">
          <div class="stat-item">
            <span class="stat-num">{{ count }}</span>
            <span class="stat-label">{{ source }}</span>
          </div>
          <div class="stat-divider" />
        </template>
        <div class="stat-item">
          <span class="stat-num">{{ starCount }}</span>
          <span class="stat-label">⭐ 收藏</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-num">{{ pinCount }}</span>
          <span class="stat-label">📌 置顶</span>
        </div>
      </div>

      <!-- 筛选工具栏 -->
      <div class="filter-toolbar">
        <n-space align="center">
          <n-input v-model:value="searchQuery" placeholder="搜索标题/摘要" clearable size="small" style="width: 200px" @update:value="debouncedSearch" />
          <n-select v-model:value="dateRange" :options="dateOptions" size="small" style="width: 120px" />
          <n-select v-model:value="filters.category" :options="categoryOptions" placeholder="分类" clearable size="small" style="width: 200px" />
        </n-space>
        <n-space align="center">
          <n-button
            size="small"
            :type="starredOnly ? 'warning' : 'default'"
            :secondary="!starredOnly"
            @click="starredOnly = !starredOnly"
          >⭐ 收藏</n-button>
          <n-button-group size="small">
            <n-button :type="sortBy === 'newest' ? 'primary' : 'default'" @click="sortBy = 'newest'" title="最新优先">↓</n-button>
            <n-button :type="sortBy === 'oldest' ? 'primary' : 'default'" @click="sortBy = 'oldest'" title="最早优先">↑</n-button>
            <n-button :type="sortBy === 'title' ? 'primary' : 'default'" @click="sortBy = 'title'" title="标题排序">Aa</n-button>
          </n-button-group>
        </n-space>
      </div>

      <n-spin :show="loading">
        <div v-if="papers.length" class="papers-grid">
          <div v-for="p in paginatedPapers" :key="p.id" class="paper-card" :class="{ pinned: p.pinned }" @click="openDetail(p.id)">
            <!-- 缩略图 -->
            <div class="paper-thumb">
              <img
                v-if="p.external_ids?.arxiv && !failedThumbs.has(p.external_ids.arxiv)"
                :src="thumbnailUrl(p.external_ids.arxiv)"
                :alt="p.title"
                @error="onThumbError(p.external_ids.arxiv)"
                loading="lazy"
              />
              <div v-else class="placeholder">
                <span class="icon">📄</span>
                <span>无预览</span>
              </div>
            </div>
            <!-- 内容 -->
            <div class="paper-content">
              <h4 class="paper-title">{{ p.title_zh || p.title }}</h4>
              <div v-if="p.title_zh" class="paper-title-en">{{ p.title }}</div>
              <div class="paper-meta">
                <n-tag v-for="cat in (p.categories || [])" :key="cat" size="tiny" :type="categoryColor(cat)" round>{{ cat }}</n-tag>
                <n-tag v-if="p.source" size="tiny" type="warning" round>{{ p.source }}</n-tag>
                <span v-if="p.published_at" class="paper-date">{{ formatDate(p.published_at) }}</span>
              </div>
              <p class="paper-authors">{{ formatAuthors(p.authors) }}</p>
              <p class="paper-abstract">{{ p.abstract_zh || p.abstract }}</p>
              <div class="paper-footer">
                <div class="paper-links">
                  <a v-if="p.url" :href="p.url" target="_blank" class="paper-link" @click.stop>arXiv</a>
                  <a v-if="p.pdf_url" :href="p.pdf_url" target="_blank" class="paper-link" @click.stop>PDF</a>
                  <a v-if="p.blog_url" :href="p.blog_url" target="_blank" class="paper-link blog" @click.stop>Blog</a>
                </div>
                <div class="paper-actions">
                  <span v-if="p.has_note" class="badge-icon" title="有笔记">📝</span>
                  <span v-if="p.summary_zh" class="badge-icon" title="有摘要">✨</span>
                  <button class="action-btn" :class="{ active: p.pinned }" @click.stop="handlePin(p)" title="置顶">📌</button>
                  <button class="action-btn" :class="{ active: p.starred }" @click.stop="handleStar(p)" title="收藏">⭐</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <EmptyState v-else description="暂无论文数据" />
      </n-spin>

      <!-- 分页 -->
      <div v-if="filteredPapers.length > pageSize" class="pagination-wrap">
        <n-pagination
          v-model:page="currentPage"
          :page-count="Math.ceil(filteredPapers.length / pageSize)"
          :page-size="pageSize"
        />
      </div>
    </n-card>

    <!-- 添加论文弹窗 -->
    <n-modal v-model:show="showFetchModal" preset="dialog" title="通过 URL 添加论文">
      <n-space vertical>
        <n-input v-model:value="fetchUrl" placeholder="粘贴 arXiv / DOI / Semantic Scholar 链接" />
        <n-checkbox v-model:checked="fetchForce">已存在时强制重新添加</n-checkbox>
      </n-space>
      <template #action>
        <n-space>
          <n-button secondary @click="showFetchModal = false">取消</n-button>
          <n-button type="primary" :loading="fetching" @click="handleFetch">添加</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 论文详情浮窗 -->
    <n-modal v-model:show="showDetailModal" :mask-closable="true" @update:show="onDetailModalUpdate" class="detail-modal-wrap">
      <div class="detail-modal-body">
        <n-spin :show="detailLoading">
          <div v-if="detailPaper" class="detail-inner">
            <!-- 头部 -->
            <div class="dm-header">
              <div class="dm-header-info">
                <h2>{{ detailPaper.title_zh || detailPaper.title }}
                  <span v-if="detailPaper.summary_zh" class="dm-ai-badge" title="已生成 AI 概述">✨</span>
                </h2>
                <p v-if="detailPaper.title_zh" class="dm-title-en">{{ detailPaper.title }}</p>
                <p class="dm-authors">{{ formatAllAuthors(detailPaper.authors) }}</p>
                <div class="dm-tags">
                  <n-tag v-for="cat in (detailPaper.categories || [])" :key="cat" size="tiny" :type="categoryColor(cat)" round>{{ cat }}</n-tag>
                  <n-tag v-if="detailPaper.source" size="tiny" type="warning" round>{{ detailPaper.source }}</n-tag>
                  <span v-if="detailPaper.published_at" class="dm-date">{{ formatDate(detailPaper.published_at) }}</span>
                </div>
              </div>
              <div class="dm-actions">
                <n-button :type="detailPaper.starred ? 'warning' : 'default'" :secondary="!detailPaper.starred" @click="handleDetailStar">
                  {{ detailPaper.starred ? '⭐ 已收藏' : '☆ 收藏' }}
                </n-button>
                <n-button :type="detailPaper.pinned ? 'info' : 'default'" :secondary="!detailPaper.pinned" @click="handleDetailPin">
                  {{ detailPaper.pinned ? '📌 已置顶' : '置顶' }}
                </n-button>
                <n-button v-if="detailPaper.url" tag="a" :href="detailPaper.url" target="_blank" secondary>arXiv</n-button>
                <n-button v-if="detailPaper.pdf_url" tag="a" :href="detailPaper.pdf_url" target="_blank" secondary>PDF</n-button>
                <n-button v-if="detailPaper.blog_url" tag="a" :href="detailPaper.blog_url" target="_blank" type="warning" secondary>Blog</n-button>
              </div>
            </div>
            <!-- 摘要 + 缩略图 -->
            <div class="dm-body">
              <div v-if="detailPaper.external_ids?.arxiv" class="dm-thumb">
                <img :src="thumbnailUrl(detailPaper.external_ids.arxiv)" :alt="detailPaper.title" @error="e => e.target.style.display = 'none'" />
              </div>
              <div class="dm-text">
                <h3>摘要</h3>
                <p v-if="detailPaper.abstract_zh" class="dm-abstract-zh">{{ detailPaper.abstract_zh }}</p>
                <p class="dm-abstract-en">{{ detailPaper.abstract }}</p>
                <template v-if="detailPaper.summary_zh">
                  <n-divider />
                  <h3>AI 概述</h3>
                  <p class="dm-summary">{{ detailPaper.summary_zh }}</p>
                </template>
              </div>
            </div>
            <!-- 笔记 -->
            <div class="dm-notes">
              <div class="dm-notes-header">
                <h3>精读笔记</h3>
                <n-space>
                  <n-button v-if="!editingNote" secondary @click="startEditNote">编辑笔记</n-button>
                  <template v-else>
                    <n-button secondary @click="cancelEditNote">取消</n-button>
                    <n-button type="primary" :loading="savingNote" @click="saveNote">保存</n-button>
                  </template>
                </n-space>
              </div>
              <MarkdownRenderer v-if="!editingNote && detailNote" :content="detailNote" />
              <n-input v-else-if="editingNote" v-model:value="noteDraft" type="textarea" :rows="8" placeholder="支持 Markdown 格式..." />
              <p v-else class="dm-no-note">暂无笔记，点击「编辑」开始记录</p>
            </div>
            <!-- 操作 -->
            <div class="dm-footer">
              <n-button type="primary" secondary :loading="summarizing" @click="handleSummarize">生成 AI 概述</n-button>
              <n-button secondary @click="showBlogModal = true">设置 Blog 链接</n-button>
            </div>
          </div>
        </n-spin>
      </div>
    </n-modal>

    <!-- Blog 链接弹窗 -->
    <n-modal v-model:show="showBlogModal" preset="dialog" title="设置精读 Blog 链接">
      <n-input v-model:value="blogUrlDraft" placeholder="Blog URL（留空清除）" />
      <template #action>
        <n-space>
          <n-button secondary @click="showBlogModal = false">取消</n-button>
          <n-button type="primary" @click="saveBlog">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NSpin, NSpace, NInput, NSelect, NTag, NButton, NButtonGroup, NIcon, NDivider,
  NPagination, NModal, NCheckbox, useMessage,
} from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import EmptyState from '../../components/common/EmptyState.vue'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import { getPaperList, getPaperStats, getThumbnailUrl, fetchPaper, starPaper, pinPaper, getPaperDetail, getPaperNote, savePaperNote, setPaperBlog, summarizePaper } from '../../api/papers'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const papers = ref([])
const total = ref(0)
const stats = ref({ total: 0, by_category: {}, by_source: {} })
const searchQuery = ref('')
const filters = ref({ category: null })
const sortBy = ref('newest')
const dateRange = ref('all')
const starredOnly = ref(false)
const currentPage = ref(1)
const pageSize = 20
const showFetchModal = ref(false)
const fetchUrl = ref('')
const fetchForce = ref(false)
const fetching = ref(false)
const failedThumbs = ref(new Set())

// ---- 详情浮窗状态 ----
const showDetailModal = ref(false)
const detailPaper = ref(null)
const detailLoading = ref(false)
const detailNote = ref('')
const editingNote = ref(false)
const noteDraft = ref('')
const savingNote = ref(false)
const summarizing = ref(false)
const showBlogModal = ref(false)
const blogUrlDraft = ref('')
const detailPaperId = ref(null)

const noteCount = computed(() => papers.value.filter(p => p.has_note).length)
const starCount = computed(() => papers.value.filter(p => p.starred).length)
const pinCount = computed(() => papers.value.filter(p => p.pinned).length)

const dateOptions = [
  { label: '全部时间', value: 'all' },
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本年', value: 'year' },
]

function isInDateRange(dateStr, range) {
  if (!dateStr || range === 'all') return true
  const date = new Date(dateStr)
  const now = new Date()
  if (range === 'today') return date.toDateString() === now.toDateString()
  if (range === 'week') {
    const weekAgo = new Date(now); weekAgo.setDate(weekAgo.getDate() - 7)
    return date >= weekAgo
  }
  if (range === 'month') return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear()
  if (range === 'year') return date.getFullYear() === now.getFullYear()
  return true
}

let searchTimer = null

const categoryOptions = computed(() => {
  const cats = stats.value.by_category || {}
  return Object.entries(cats).map(([k, v]) => ({ label: `${k.replace(/_/g, ' ')} (${v})`, value: k }))
})

const filteredPapers = computed(() => {
  let result = papers.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      (p.title || '').toLowerCase().includes(q) ||
      (p.title_zh || '').toLowerCase().includes(q) ||
      (p.abstract || '').toLowerCase().includes(q) ||
      (p.abstract_zh || '').toLowerCase().includes(q)
    )
  }
  if (dateRange.value !== 'all') {
    result = result.filter(p => isInDateRange(p.published_at, dateRange.value))
  }
  if (starredOnly.value) result = result.filter(p => p.starred)
  // 排序：置顶优先，再按选定方式
  return [...result].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1
    if (!a.pinned && b.pinned) return 1
    if (sortBy.value === 'newest') return new Date(b.published_at || 0) - new Date(a.published_at || 0)
    if (sortBy.value === 'oldest') return new Date(a.published_at || 0) - new Date(b.published_at || 0)
    if (sortBy.value === 'title') return (a.title_zh || a.title || '').localeCompare(b.title_zh || b.title || '')
    return 0
  })
})

const paginatedPapers = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredPapers.value.slice(start, start + pageSize)
})

function thumbnailUrl(arxivId) {
  return getThumbnailUrl(arxivId)
}

function onThumbError(arxivId) {
  failedThumbs.value.add(arxivId)
  failedThumbs.value = new Set(failedThumbs.value)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return dateStr.split('T')[0]
}

function formatAuthors(authors) {
  if (!authors || !authors.length) return ''
  const list = Array.isArray(authors) ? authors : [authors]
  return list.slice(0, 3).join(', ') + (list.length > 3 ? ` 等 ${list.length} 人` : '')
}

function formatAllAuthors(authors) {
  if (!authors || !authors.length) return ''
  const list = Array.isArray(authors) ? authors : [authors]
  return list.join(', ')
}

function categoryColor(cat) {
  const map = { diffusion: 'info', autoregressive: 'success', image_compression: 'warning', visual_tokenizer: 'error' }
  return map[cat] || 'default'
}

function debouncedSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { currentPage.value = 1 }, 300)
}

watch(() => filters.value.category, () => { currentPage.value = 1 })
watch(() => starredOnly.value, () => { currentPage.value = 1 })
watch(() => dateRange.value, () => { currentPage.value = 1 })

async function loadPapers() {
  loading.value = true
  try {
    // 全量加载（140篇不多，客户端分页+筛选）
    const params = { limit: 500, offset: 0 }
    if (filters.value.category) params.category = filters.value.category
    const data = await getPaperList(params)
    papers.value = data.papers || []
    total.value = data.total || 0
  } catch { papers.value = [] }
  loading.value = false
}

async function loadStats() {
  try { stats.value = await getPaperStats() } catch {}
}

async function handleStar(p) {
  const newVal = !p.starred
  p.starred = newVal
  try {
    await starPaper(p.id, newVal)
    message.success(newVal ? '已收藏' : '已取消收藏')
  } catch {
    p.starred = !newVal
    message.error('操作失败')
  }
}

async function handlePin(p) {
  const newVal = !p.pinned
  p.pinned = newVal
  try {
    await pinPaper(p.id, newVal)
    message.success(newVal ? '已置顶' : '已取消置顶')
  } catch {
    p.pinned = !newVal
    message.error('操作失败')
  }
}

async function handleFetch() {
  if (!fetchUrl.value.trim()) { message.warning('请输入论文链接'); return }
  fetching.value = true
  try {
    const result = await fetchPaper(fetchUrl.value.trim(), fetchForce.value)
    if (result.status === 'exists') {
      message.info('该论文已存在')
    } else if (result.status === 'new') {
      message.success('论文添加成功')
    } else if (result.error) {
      message.error(result.message || '添加失败')
    }
    showFetchModal.value = false
    fetchUrl.value = ''
    fetchForce.value = false
    loadPapers()
    loadStats()
  } catch { message.error('网络错误') }
  fetching.value = false
}

onMounted(() => {
  loadPapers()
  loadStats()
  // 恢复滚动位置
  const scrollContainer = document.querySelector('.app-content .n-scrollbar-container')
  const savedScroll = sessionStorage.getItem('paperList:scrollY')
  // 恢复浮窗状态
  const hash = window.location.hash
  if (hash.startsWith('#paper=')) {
    const id = hash.substring(7)
    if (id) {
      detailPaperId.value = id
      showDetailModal.value = true
      loadDetail(id)
    }
  }
  // 滚动恢复需要等数据加载完
  if (savedScroll && scrollContainer) {
    nextTick(() => {
      setTimeout(() => { scrollContainer.scrollTop = parseInt(savedScroll) }, 100)
    })
  }
})

// 滚动位置保存（Naive UI scrollbar 容器）
let scrollTimer = null
let _scrollEl = null
function onScroll() {
  if (scrollTimer) clearTimeout(scrollTimer)
  scrollTimer = setTimeout(() => {
    if (_scrollEl) sessionStorage.setItem('paperList:scrollY', String(_scrollEl.scrollTop))
  }, 200)
}
nextTick(() => {
  _scrollEl = document.querySelector('.app-content .n-scrollbar-container')
  if (_scrollEl) _scrollEl.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  if (_scrollEl) _scrollEl.removeEventListener('scroll', onScroll)
})

// ---- 详情浮窗功能 ----
function openDetail(id) {
  detailPaperId.value = id
  showDetailModal.value = true
  loadDetail(id)
  history.replaceState(null, '', `#paper=${id}`)
}

function onDetailModalUpdate(show) {
  if (!show) {
    detailPaper.value = null
    detailNote.value = ''
    editingNote.value = false
    detailPaperId.value = null
    history.replaceState(null, '', window.location.pathname + window.location.search)
  }
}

async function loadDetail(id) {
  detailLoading.value = true
  try {
    const [p, n] = await Promise.all([
      getPaperDetail(id).catch(() => null),
      getPaperNote(id).catch(() => ({ content: '' })),
    ])
    detailPaper.value = p
    detailNote.value = n?.content || ''
    blogUrlDraft.value = p?.blog_url || ''
  } catch {}
  detailLoading.value = false
}

function startEditNote() { noteDraft.value = detailNote.value; editingNote.value = true }
function cancelEditNote() { editingNote.value = false }

async function saveNote() {
  savingNote.value = true
  try {
    await savePaperNote(detailPaperId.value, noteDraft.value)
    detailNote.value = noteDraft.value
    editingNote.value = false
    message.success('笔记已保存')
  } catch { message.error('保存失败') }
  savingNote.value = false
}

async function handleSummarize() {
  summarizing.value = true
  try {
    const result = await summarizePaper(detailPaperId.value)
    if (result.error) {
      message.warning(result.message || '摘要生成失败')
    } else {
      message.success('摘要生成成功')
      if (result.result?.title_zh) detailPaper.value.title_zh = result.result.title_zh
      if (result.result?.abstract_zh) detailPaper.value.abstract_zh = result.result.abstract_zh
      if (result.result?.summary_zh) detailPaper.value.summary_zh = result.result.summary_zh
    }
  } catch { message.error('请求失败') }
  summarizing.value = false
}

async function saveBlog() {
  try {
    await setPaperBlog(detailPaperId.value, blogUrlDraft.value)
    detailPaper.value.blog_url = blogUrlDraft.value
    showBlogModal.value = false
    message.success('Blog 链接已保存')
  } catch { message.error('保存失败') }
}

async function handleDetailStar() {
  const newVal = !detailPaper.value.starred
  detailPaper.value.starred = newVal
  // 同步到列表
  const p = papers.value.find(p => p.id === detailPaperId.value)
  if (p) p.starred = newVal
  try {
    await starPaper(detailPaperId.value, newVal)
    message.success(newVal ? '已收藏' : '已取消收藏')
  } catch {
    detailPaper.value.starred = !newVal
    if (p) p.starred = !newVal
    message.error('操作失败')
  }
}

async function handleDetailPin() {
  const newVal = !detailPaper.value.pinned
  detailPaper.value.pinned = newVal
  const p = papers.value.find(p => p.id === detailPaperId.value)
  if (p) p.pinned = newVal
  try {
    await pinPaper(detailPaperId.value, newVal)
    message.success(newVal ? '已置顶' : '已取消置顶')
  } catch {
    detailPaper.value.pinned = !newVal
    if (p) p.pinned = !newVal
    message.error('操作失败')
  }
}
</script>

<style scoped lang="scss">
.flex-between { flex-wrap: wrap; gap: 8px; }
.header-left { display: flex; align-items: center; gap: 10px; }

.filter-toolbar {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;
  flex-wrap: wrap; gap: 10px;
}

.stats-bar {
  display: flex; gap: 16px; align-items: center; margin-bottom: 14px; padding: 10px 16px;
  background: #f8fafc; border-radius: 8px; flex-wrap: wrap;
}
.stat-item { display: flex; align-items: baseline; gap: 5px; }
.stat-num { font-size: 20px; font-weight: bold; color: #4f46e5; }
.stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-divider { width: 1px; height: 20px; background: #e2e8f0; }

.papers-grid { display: flex; flex-direction: column; gap: 14px; }

.paper-card {
  display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 14px;
  padding: 14px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
  transition: all 0.2s; cursor: pointer;
  &:hover { border-color: #4f46e544; box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
  &.pinned { border-left: 3px solid #4f46e5; background: #fafaff; }
  @media (max-width: 640px) {
    grid-template-columns: 1fr;
    .paper-thumb { min-height: 120px; max-height: 160px; img { object-fit: contain; } }
  }
}

.paper-thumb {
  border-radius: 8px; overflow: hidden; background: #f1f5f9;
  display: flex; align-items: center; justify-content: center; min-height: 200px;
  img { width: 100%; height: auto; display: block; object-fit: cover; }
  .placeholder { color: #94a3b8; font-size: 12px; text-align: center; padding: 20px; .icon { font-size: 28px; display: block; margin-bottom: 6px; opacity: 0.5; } }
}

.paper-content { display: flex; flex-direction: column; min-width: 0; }
.paper-title { font-size: 14px; font-weight: 600; line-height: 1.5; margin-bottom: 4px; color: #1e293b; }
.paper-title-en { font-size: 12px; color: #94a3b8; margin-bottom: 6px; font-style: italic; }
.paper-meta { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; align-items: center; }
.paper-date { font-size: 11px; color: #94a3b8; margin-left: 4px; }
.paper-authors { font-size: 12px; color: #64748b; margin-bottom: 8px; }
.paper-abstract {
  font-size: 13px; color: #475569; line-height: 1.6;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.paper-footer { display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 8px; }
.paper-links { display: flex; gap: 6px; }
.paper-link {
  display: inline-flex; padding: 3px 10px; border-radius: 999px;
  border: 1px solid #e2e8f0; font-size: 12px; color: #4f46e5;
  text-decoration: none; transition: all 0.15s;
  &:hover { background: #4f46e5; color: #fff; border-color: #4f46e5; }
  &.blog { color: #f59e0b; &:hover { background: #f59e0b; border-color: #f59e0b; } }
}
.paper-actions { display: flex; gap: 4px; align-items: center; }
.badge-icon { font-size: 14px; opacity: 0.7; }
.action-btn {
  background: none; border: none; cursor: pointer; font-size: 16px;
  padding: 2px 4px; border-radius: 4px; opacity: 0.25;
  transition: all 0.15s; line-height: 1;
  &:hover { opacity: 0.6; background: #f1f5f9; }
  &.active { opacity: 1; }
}

.pagination-wrap { display: flex; justify-content: center; margin-top: 16px; }

// ---- 详情浮窗 ----
.detail-modal-body {
  background: #fff; border-radius: 12px; width: 80vw; max-width: 800px;
  max-height: 85vh; overflow-y: auto; padding: 24px;
}
.detail-inner { display: flex; flex-direction: column; gap: 16px; }
.dm-header {
  display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  h2 { font-size: 18px; line-height: 1.4; margin-bottom: 4px; }
}
.dm-header-info { flex: 1; min-width: 0; }
.dm-title-en { font-size: 13px; color: #94a3b8; font-style: italic; margin-bottom: 4px; }
.dm-authors { font-size: 13px; color: #64748b; margin-bottom: 8px; }
.dm-tags { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.dm-date { font-size: 12px; color: #94a3b8; margin-left: 6px; }
.dm-actions { display: flex; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }

.dm-body { display: flex; gap: 20px; flex-wrap: wrap; }
.dm-thumb { width: 200px; flex-shrink: 0; img { width: 100%; border-radius: 8px; border: 1px solid #e2e8f0; } }
.dm-text { flex: 1; min-width: 200px; h3 { font-size: 15px; margin-bottom: 8px; } }
.dm-abstract-zh { font-size: 14px; color: #1e293b; line-height: 1.7; margin-bottom: 12px; }
.dm-abstract-en { font-size: 13px; color: #64748b; line-height: 1.6; }
.dm-summary { font-size: 14px; color: #334155; line-height: 1.7; background: #f8fafc; padding: 12px; border-radius: 8px; }

.dm-notes { border-top: 1px solid #e2e8f0; padding-top: 16px; }
.dm-notes-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; h3 { font-size: 15px; } }
.dm-no-note { color: #94a3b8; font-size: 13px; }

.dm-footer { display: flex; gap: 8px; border-top: 1px solid #e2e8f0; padding-top: 16px; }

.dm-ai-badge { font-size: 16px; cursor: default; vertical-align: middle; margin-left: 6px; }
</style>

<template>
  <div class="page-container">
    <n-spin :show="loading">
      <div v-if="paper" class="paper-detail">
        <!-- 顶部信息区 -->
        <n-card>
          <template #header>
            <div class="detail-header">
              <div class="header-info">
                <h2>{{ paper.title_zh || paper.title }}</h2>
                <p v-if="paper.title_zh" class="title-en">{{ paper.title }}</p>
                <p class="authors">{{ formatAuthors(paper.authors) }}</p>
                <div class="meta-tags">
                  <n-tag v-for="cat in (paper.categories || [])" :key="cat" size="small" type="info" round>{{ cat }}</n-tag>
                  <n-tag v-for="ac in (paper.arxiv_categories || []).slice(0,3)" :key="ac" size="tiny" round>{{ ac }}</n-tag>
                  <n-tag v-if="paper.source" size="small" type="warning" round>{{ paper.source }}</n-tag>
                  <span v-if="paper.published_at" class="date">{{ formatDate(paper.published_at) }}</span>
                </div>
              </div>
            </div>
          </template>

          <div class="detail-body">
            <!-- 缩略图 -->
            <div v-if="paper.external_ids?.arxiv" class="detail-thumb">
              <img :src="thumbnailUrl(paper.external_ids.arxiv)" :alt="paper.title" @error="onThumbError" />
            </div>

            <!-- 摘要 -->
            <div class="detail-content">
              <h3>摘要</h3>
              <p v-if="paper.abstract_zh" class="abstract-zh">{{ paper.abstract_zh }}</p>
              <p class="abstract-en">{{ paper.abstract }}</p>

              <!-- LLM 摘要 -->
              <div v-if="paper.summary_zh" class="summary-section">
                <n-divider />
                <h3>AI 概述</h3>
                <p class="summary-text">{{ paper.summary_zh }}</p>
              </div>
            </div>
          </div>
        </n-card>

        <!-- 笔记区 -->
        <n-card title="精读笔记" size="small" style="margin-top: 16px">
          <template #header-extra>
            <n-space>
              <n-button v-if="!editingNote" size="small" @click="startEditNote">编辑笔记</n-button>
              <template v-else>
                <n-button size="small" @click="cancelEditNote">取消</n-button>
                <n-button size="small" type="primary" :loading="savingNote" @click="saveNote">保存</n-button>
              </template>
            </n-space>
          </template>
          <MarkdownRenderer v-if="!editingNote && noteContent" :content="noteContent" />
          <n-input v-else-if="editingNote" v-model:value="noteDraft" type="textarea" :rows="12" placeholder="支持 Markdown 格式..." />
          <EmptyState v-else description="暂无笔记，点击「编辑笔记」开始记录" />
        </n-card>

        <!-- 操作区 -->
        <n-card title="操作" size="small" style="margin-top: 16px">
          <n-space>
            <n-button size="small" :loading="summarizing" @click="handleSummarize">
              ✨ 生成 AI 摘要
            </n-button>
            <n-button size="small" @click="showBlogModal = true">
              设置 Blog 链接
            </n-button>
          </n-space>
        </n-card>
      </div>
      <EmptyState v-else description="未找到该论文" />
    </n-spin>

    <!-- Blog 链接弹窗 -->
    <n-modal v-model:show="showBlogModal" preset="dialog" title="设置精读 Blog 链接">
      <n-input v-model:value="blogUrlDraft" placeholder="Blog URL（留空清除）" />
      <template #action>
        <n-space>
          <n-button @click="showBlogModal = false">取消</n-button>
          <n-button type="primary" @click="saveBlog">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 底部悬浮动作栏：收藏/置顶/arXiv/PDF（图标按钮，不占内容区） -->
    <div v-if="paper" class="action-fab">
      <n-tooltip>
        <template #trigger>
          <n-button quaternary circle :type="paper.starred ? 'warning' : 'default'" @click="handleStar">
            <template #icon><n-icon size="20"><star v-if="paper.starred" /><star-outline v-else /></n-icon></template>
          </n-button>
        </template>
        {{ paper.starred ? '已收藏' : '收藏' }}
      </n-tooltip>
      <n-tooltip>
        <template #trigger>
          <n-button quaternary circle :type="paper.pinned ? 'info' : 'default'" @click="handlePin">
            <template #icon><n-icon size="20"><bookmarks v-if="paper.pinned" /><bookmarks-outline v-else /></n-icon></template>
          </n-button>
        </template>
        {{ paper.pinned ? '已置顶' : '置顶' }}
      </n-tooltip>
      <n-tooltip v-if="paper.url">
        <template #trigger>
          <n-button quaternary circle tag="a" :href="paper.url" target="_blank">
            <template #icon><n-icon size="20"><document-text-outline /></n-icon></template>
          </n-button>
        </template>
        arXiv
      </n-tooltip>
      <n-tooltip v-if="paper.pdf_url">
        <template #trigger>
          <n-button quaternary circle tag="a" :href="paper.pdf_url" target="_blank">
            <template #icon><n-icon size="20"><document-outline /></n-icon></template>
          </n-button>
        </template>
        PDF
      </n-tooltip>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { NCard, NSpin, NButton, NTag, NSpace, NDivider, NInput, NModal, NIcon, NTooltip, useMessage } from 'naive-ui'
import { Star, StarOutline, Bookmarks, BookmarksOutline, DocumentTextOutline, DocumentOutline } from '@vicons/ionicons5'
import MarkdownRenderer from '../../components/common/MarkdownRenderer.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getPaperDetail, getPaperNote, savePaperNote, setPaperBlog, summarizePaper, getThumbnailUrl, starPaper, pinPaper } from '../../api/papers'

const route = useRoute()
const message = useMessage()

const loading = ref(false)
const paper = ref(null)
const noteContent = ref('')
const editingNote = ref(false)
const noteDraft = ref('')
const savingNote = ref(false)
const summarizing = ref(false)
const showBlogModal = ref(false)
const blogUrlDraft = ref('')

function thumbnailUrl(arxivId) { return getThumbnailUrl(arxivId) }
function onThumbError(e) { e.target.style.display = 'none' }
function formatDate(d) { return d ? d.split('T')[0] : '' }
function formatAuthors(authors) {
  if (!authors || !authors.length) return ''
  const list = Array.isArray(authors) ? authors : [authors]
  return list.join(', ')
}

function startEditNote() { noteDraft.value = noteContent.value; editingNote.value = true }
function cancelEditNote() { editingNote.value = false }

async function handleStar() {
  const newVal = !paper.value.starred
  paper.value.starred = newVal
  try {
    await starPaper(route.params.id, newVal)
    message.success(newVal ? '已收藏' : '已取消收藏')
  } catch {
    paper.value.starred = !newVal
    message.error('操作失败')
  }
}

async function handlePin() {
  const newVal = !paper.value.pinned
  paper.value.pinned = newVal
  try {
    await pinPaper(route.params.id, newVal)
    message.success(newVal ? '已置顶' : '已取消置顶')
  } catch {
    paper.value.pinned = !newVal
    message.error('操作失败')
  }
}

async function saveNote() {
  savingNote.value = true
  try {
    await savePaperNote(route.params.id, noteDraft.value)
    noteContent.value = noteDraft.value
    editingNote.value = false
    message.success('笔记已保存')
  } catch { message.error('保存失败') }
  savingNote.value = false
}

async function handleSummarize() {
  summarizing.value = true
  try {
    const result = await summarizePaper(route.params.id)
    if (result.error) {
      message.warning(result.message || '摘要生成失败')
    } else {
      message.success('摘要生成成功')
      if (result.result?.title_zh) paper.value.title_zh = result.result.title_zh
      if (result.result?.abstract_zh) paper.value.abstract_zh = result.result.abstract_zh
      if (result.result?.summary_zh) paper.value.summary_zh = result.result.summary_zh
    }
  } catch { message.error('请求失败') }
  summarizing.value = false
}

async function saveBlog() {
  try {
    await setPaperBlog(route.params.id, blogUrlDraft.value)
    paper.value.blog_url = blogUrlDraft.value
    showBlogModal.value = false
    message.success('Blog 链接已保存')
  } catch { message.error('保存失败') }
}

onMounted(async () => {
  loading.value = true
  try {
    const [p, n] = await Promise.all([
      getPaperDetail(route.params.id).catch(() => null),
      getPaperNote(route.params.id).catch(() => ({ content: '' })),
    ])
    paper.value = p
    noteContent.value = n?.content || ''
    blogUrlDraft.value = p?.blog_url || ''
  } catch {}
  loading.value = false
})
</script>

<style scoped lang="scss">
.detail-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.header-info { flex: 1; min-width: 0; h2 { margin-bottom: 4px; } }
.title-en { font-size: 13px; color: #94a3b8; font-style: italic; margin-bottom: 4px; }
.authors { font-size: 13px; color: #64748b; margin-bottom: 8px; }
.meta-tags { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; .date { font-size: 12px; color: #94a3b8; margin-left: 6px; } }

.action-fab {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 8px; padding: 8px 16px;
  background: var(--color-card); border: 1px solid var(--color-border);
  border-radius: 999px; box-shadow: 0 4px 16px var(--color-shadow);
  z-index: 100;
}

.detail-body { display: flex; gap: 20px; }
.detail-thumb { width: 200px; flex-shrink: 0; img { width: 100%; border-radius: 8px; border: 1px solid #e2e8f0; } }
.detail-content { flex: 1; min-width: 0; h3 { font-size: 15px; margin-bottom: 8px; } }
.abstract-zh { font-size: 14px; color: #1e293b; line-height: 1.7; margin-bottom: 12px; }
.abstract-en { font-size: 13px; color: #64748b; line-height: 1.6; }
.summary-section { margin-top: 16px; }
.summary-text { font-size: 14px; color: #334155; line-height: 1.7; background: #f8fafc; padding: 12px; border-radius: 8px; }
</style>

<template>
  <div class="markdown-body" ref="containerRef" v-html="rendered" @click="handleClick"></div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import checkbox from 'markdown-it-task-checkbox'
import { slugify } from '../../utils/markdown'
import mermaid from 'mermaid'
import { useThemeStore } from '../../stores/theme'

const props = defineProps({
  content: { type: String, default: '' },
})

const containerRef = ref(null)
const themeStore = useThemeStore()
const router = useRouter()

function handleClick(e) {
  const anchor = e.target.closest('a')
  if (!anchor) return
  const href = anchor.getAttribute('href')
  if (href && href.startsWith('/management/')) {
    e.preventDefault()
    router.push(href)
  }
}

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
})
  // 渲染 - [ ] / - [x] 为 checkbox
  .use(checkbox, {
    disabled: true,
    divWrap: false,
    liClass: 'task-list-item',
  })

// Heading auto-ID
const defaultHeadingRender = md.renderer.rules.heading_open ||
  function (tokens, idx, options, env, self) { return self.renderToken(tokens, idx, options) }

md.renderer.rules.heading_open = function (tokens, idx, options, env, self) {
  const token = tokens[idx]
  if (token.tag === 'h2' || token.tag === 'h3') {
    const nextToken = tokens[idx + 1]
    if (nextToken && nextToken.type === 'inline') {
      const text = nextToken.content || ''
      token.attrSet('id', slugify(text))
    }
  }
  return defaultHeadingRender(tokens, idx, options, env, self)
}

// Mermaid code block: render as <pre class="mermaid"> instead of <pre><code>
const defaultFence = md.renderer.rules.fence ||
  function (tokens, idx, options, env, self) { return self.renderToken(tokens, idx, options) }

md.renderer.rules.fence = function (tokens, idx, options, env, self) {
  const token = tokens[idx]
  const info = token.info ? token.info.trim() : ''
  if (info === 'mermaid') {
    const escaped = md.utils.escapeHtml(token.content)
    return `<pre class="mermaid">${escaped}</pre>\n`
  }
  return defaultFence(tokens, idx, options, env, self)
}

const rendered = computed(() => {
  if (!props.content) return '<p class="text-light">暂无内容</p>'
  let src = props.content
  // Task links: [[proj#t2-3]] or [[proj#t2-3|display]] → project tree with task selected
  src = src.replace(/\[\[([^#|\]]+)#([^|\]]+)\|([^\]]+)\]\]/g, (_, proj, task, text) =>
    `[${text.trim()}](/management/projects?slug=${proj.trim()}&task=${task.trim()})`)
  src = src.replace(/\[\[([^#|\]]+)#([^|\]]+)\]\]/g, (_, proj, task) =>
    `[${proj.trim()}/${task.trim()}](/management/projects?slug=${proj.trim()}&task=${task.trim()})`)
  // Doc links: [[slug]] or [[slug|display]] → doc detail page
  src = src.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (_, slug, text) => `[${text.trim()}](/management/docs/${slug.trim()})`)
  src = src.replace(/\[\[([^\]]+)\]\]/g, (_, slug) => `[${slug.trim()}](/management/docs/${slug.trim()})`)
  return md.render(src)
})

async function renderMermaid() {
  if (!containerRef.value) return
  const nodes = containerRef.value.querySelectorAll('pre.mermaid')
  if (!nodes.length) return

  for (const node of nodes) {
    if (!node.dataset.source) {
      node.dataset.source = node.textContent
    } else {
      node.textContent = node.dataset.source
      node.removeAttribute('data-processed')
    }
    const svgEl = node.querySelector('svg')
    if (svgEl) svgEl.remove()
  }

  try {
    mermaid.initialize({
      startOnLoad: false,
      theme: themeStore.isDark ? 'dark' : 'default',
      securityLevel: 'loose',
      fontFamily: 'system-ui, sans-serif',
    })
    await mermaid.run({ nodes: Array.from(nodes) })
  } catch (e) {
    console.warn('Mermaid render error:', e)
  }
}

watch(
  [rendered, () => themeStore.isDark],
  async () => {
    await nextTick()
    await renderMermaid()
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.markdown-body {
  :deep(.task-list-item) {
    list-style: none;
    margin-left: -20px;
  }
  :deep(.task-list-item input[type='checkbox']) {
    margin-right: 8px;
    transform: translateY(1px);
    accent-color: var(--color-primary);
    width: 14px;
    height: 14px;
    cursor: default;
  }

  :deep(pre.mermaid) {
    background: transparent;
    padding: 16px;
    margin: 16px 0;
    text-align: center;
    overflow-x: auto;

    svg {
      max-width: 100%;
      height: auto;
    }
  }

  :deep(.d-error) {
    display: none;
  }

  :deep(a) {
    color: var(--color-primary);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>

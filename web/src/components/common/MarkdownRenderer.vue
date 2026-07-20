<template>
  <div class="markdown-body" v-html="rendered"></div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import checkbox from 'markdown-it-task-checkbox'
import { slugify } from '../../utils/markdown'

const props = defineProps({
  content: { type: String, default: '' },
})

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

// 为 h2/h3 添加 id 锚点（用于 TOC 跳转）
const defaultRender = md.renderer.rules.heading_open || function(tokens, idx, options, env, self) {
  return self.renderToken(tokens, idx, options)
}
md.renderer.rules.heading_open = function(tokens, idx, options, env, self) {
  const token = tokens[idx]
  if (token.tag === 'h2' || token.tag === 'h3') {
    const nextToken = tokens[idx + 1]
    if (nextToken && nextToken.type === 'inline') {
      const text = nextToken.content || ''
      token.attrSet('id', slugify(text))
    }
  }
  return defaultRender(tokens, idx, options, env, self)
}

const rendered = computed(() => {
  if (!props.content) return '<p class="text-light">暂无内容</p>'
  return md.render(props.content)
})
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
}
</style>

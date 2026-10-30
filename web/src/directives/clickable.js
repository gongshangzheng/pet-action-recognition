// ============================================================
// v-clickable —— 给「用 div 当卡片/列表项」的元素补键盘语义
//
// 这些元素本身没有 href，也不在 tab 序列里，鼠标能点但键盘到不了。
// 指令只补语义，不改样式：
//   role="button" + tabindex="0" + Enter/Space 触发原生 click
//
// 用法：<div class="paper-card" v-clickable @click="open(p)">
// 若元素已有 aria-label / role，指令不覆盖。
// ============================================================

const HANDLER = Symbol('clickableHandler')

export const vClickable = {
  mounted(el) {
    if (!el.hasAttribute('role')) el.setAttribute('role', 'button')
    if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '0')

    el[HANDLER] = (event) => {
      if (event.key !== 'Enter' && event.key !== ' ' && event.key !== 'Spacebar') return
      // Space 默认会滚动页面，Enter 在部分容器里会触发默认提交
      event.preventDefault()
      el.click()
    }
    el.addEventListener('keydown', el[HANDLER])
  },
  unmounted(el) {
    if (el[HANDLER]) {
      el.removeEventListener('keydown', el[HANDLER])
      delete el[HANDLER]
    }
  },
}

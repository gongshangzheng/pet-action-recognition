// 主内容滚动位置记忆（用于长文页刷新后回到原阅读位置）。
// Naive UI 的滚动容器不在 window，因此在 app-content 内定位并对 sessionStorage 降级处理。

const KEY_PREFIX = 'doc-scroll:'

function getStorage() {
  try {
    return typeof window === 'undefined' ? null : window.sessionStorage
  } catch {
    return null
  }
}

export function findScrollContainer() {
  if (typeof document === 'undefined') return null
  return document.querySelector('.app-content .n-scrollbar-container') || document.querySelector('.n-scrollbar-container')
}

export function readScrollPosition(key) {
  const storage = getStorage()
  if (!storage || !key) return null
  try {
    const value = Number.parseInt(storage.getItem(KEY_PREFIX + key), 10)
    return Number.isFinite(value) ? value : null
  } catch {
    return null
  }
}

function saveScrollPosition(key, top) {
  const storage = getStorage()
  if (!storage || !key) return
  try {
    storage.setItem(KEY_PREFIX + key, String(Math.max(0, Math.round(top))))
  } catch {
    // Storage 禁用或配额不足时不影响阅读。
  }
}

export function attachScrollMemory(element, getKey, { delay = 150 } = {}) {
  let key = typeof getKey === 'function' ? getKey() : ''
  let lastTop = element?.scrollTop || 0
  let timer = null

  function commit() {
    if (timer) clearTimeout(timer)
    timer = null
    saveScrollPosition(key, lastTop)
  }

  function onScroll() {
    if (!element) return
    lastTop = element.scrollTop
    if (timer) return
    timer = setTimeout(commit, delay)
  }

  element?.addEventListener('scroll', onScroll, { passive: true })
  return {
    noteRouteChange(nextKey) {
      commit()
      key = nextKey || ''
      lastTop = 0
    },
    dispose() {
      element?.removeEventListener('scroll', onScroll)
      commit()
    },
  }
}

export function restoreOrReset(key, isReady, { tries = 16, interval = 60, settleDelay = 150 } = {}) {
  const target = readScrollPosition(key)
  const apply = () => {
    const element = findScrollContainer()
    if (!element) return
    element.scrollTop = target && target > 0 ? target : 0
    if (target && target > 0) {
      setTimeout(() => {
        const current = findScrollContainer()
        if (current) current.scrollTop = target
      }, settleDelay)
    }
  }

  let attempt = 0
  const restore = () => {
    if (typeof isReady !== 'function' || isReady()) return apply()
    if (++attempt < tries) setTimeout(restore, interval)
  }
  restore()
}

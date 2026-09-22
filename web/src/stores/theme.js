import { defineStore } from 'pinia'
import { ACCENTS, DEFAULT_ACCENT, accentFor, toRgba } from '../config/theme'
import { DEFAULT_FAVICON, faviconDataUrl, isFaviconKey } from '../config/favicon'

const STORAGE_KEY = 'pet-action-recognition-theme'
const ACCENT_KEY = 'pet-action-recognition-accent'
const FAVICON_KEY = 'pet-action-recognition-favicon'

function detectInitial() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* ignore */ }
  // 默认跟随系统偏好
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

function readAccent() {
  try {
    const saved = localStorage.getItem(ACCENT_KEY)
    if (ACCENTS.some((a) => a.key === saved)) return saved
  } catch { /* ignore */ }
  return DEFAULT_ACCENT
}

function readFavicon() {
  try {
    const saved = localStorage.getItem(FAVICON_KEY)
    if (isFaviconKey(saved)) return saved
  } catch { /* ignore */ }
  return DEFAULT_FAVICON
}

function apply(mode) {
  document.documentElement.setAttribute('data-theme', mode)
}

/** 把强调色写入 <html> 的 CSS 变量（inline 优先级高于样式表里的 :root 默认值）。 */
function applyAccent(accent, mode) {
  const a = accentFor(accent, mode === 'dark')
  const root = document.documentElement
  root.style.setProperty('--color-primary', a.primary)
  root.style.setProperty('--color-primary-soft', toRgba(a.primary, a.softAlpha))
  root.style.setProperty('--color-selected', toRgba(a.primary, a.selectedAlpha))
  root.style.setProperty('--color-primary-border', toRgba(a.primary, a.borderAlpha))
  root.setAttribute('data-accent', a.key)
}

/** 按当前强调色 + 明暗模式生成站点图标，写入 <link rel="icon">。 */
function applyFavicon(favicon, accent, mode) {
  const bg = accentFor(accent, mode === 'dark').primary
  let link = document.querySelector('link[rel="icon"]')
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.setAttribute('type', 'image/svg+xml')
  link.setAttribute('href', faviconDataUrl(favicon, bg))
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: detectInitial(),
    accent: readAccent(),
    favicon: readFavicon(),
  }),
  getters: {
    isDark: (state) => state.mode === 'dark',
    accentPrimary: (state) => accentFor(state.accent, state.mode === 'dark').primary,
  },
  actions: {
    init() {
      apply(this.mode)
      applyAccent(this.accent, this.mode)
      applyFavicon(this.favicon, this.accent, this.mode)
    },
    toggle() {
      this.mode = this.mode === 'dark' ? 'light' : 'dark'
      try { localStorage.setItem(STORAGE_KEY, this.mode) } catch { /* ignore */ }
      apply(this.mode)
      // 明暗切换后强调色与图标都需换用对应模式色值
      applyAccent(this.accent, this.mode)
      applyFavicon(this.favicon, this.accent, this.mode)
    },
    setAccent(key) {
      if (!ACCENTS.some((a) => a.key === key)) return
      this.accent = key
      try { localStorage.setItem(ACCENT_KEY, key) } catch { /* ignore */ }
      applyAccent(key, this.mode)
      applyFavicon(this.favicon, key, this.mode)
    },
    setFavicon(key) {
      if (!isFaviconKey(key)) return
      this.favicon = key
      try { localStorage.setItem(FAVICON_KEY, key) } catch { /* ignore */ }
      applyFavicon(key, this.accent, this.mode)
    },
  },
})

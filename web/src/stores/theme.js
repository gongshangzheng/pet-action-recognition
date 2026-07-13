import { defineStore } from 'pinia'

const STORAGE_KEY = 'pet-action-recognition-theme'

function detectInitial() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  // 默认跟随系统偏好
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

function apply(mode) {
  document.documentElement.setAttribute('data-theme', mode)
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: detectInitial(),
  }),
  getters: {
    isDark: (state) => state.mode === 'dark',
  },
  actions: {
    init() {
      apply(this.mode)
    },
    toggle() {
      this.mode = this.mode === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, this.mode)
      apply(this.mode)
    },
  },
})

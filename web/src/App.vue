<template>
  <n-config-provider :theme="naiveTheme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-loading-bar-provider>
          <router-view />
        </n-loading-bar-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed, watch } from 'vue'
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NLoadingBarProvider,
  darkTheme,
} from 'naive-ui'
import { useThemeStore } from './stores/theme'
import { accentThemeOverrides } from './config/theme'

const themeStore = useThemeStore()
themeStore.init()

// Naive UI 跟随主题 store：dark 模式用 darkTheme，light 模式用 null
const naiveTheme = computed(() => (themeStore.isDark ? darkTheme : null))

// Naive UI 主题覆盖：主色随强调色 + 明暗模式变化，与 CSS 变量同源（config/theme.js）
// textColor3 / placeholderColor 必须显式给值：Naive 默认值（#c2c2c2 / 38% 白）对比度只有 1.8–3.3:1。
const themeOverrides = computed(() => ({
  common: {
    ...accentThemeOverrides(themeStore.accent, themeStore.isDark),
    borderRadius: '8px',
    textColor3: themeStore.isDark ? '#9d9da7' : '#5f6672',
    placeholderColor: themeStore.isDark ? '#9d9da7' : '#5f6672',
    placeholderColorDisabled: themeStore.isDark ? '#6b6b74' : '#8b919b',
  },
  // 浅色下 Naive 的语义标签文字色（#18a058 / #2080f0 / #f0a020 / #d03050）压同色浅底只有 3.0–3.4:1。
  // 深色主题的默认值已达标，不覆盖。
  Tag: themeStore.isDark
    ? {}
    : {
      textColorSuccess: '#0f7a41', // 4.74:1
      textColorInfo: '#1554ad', //    6.41:1
      textColorWarning: '#8a5a06', //  5.52:1
      textColorError: '#b91c1c', //    5.67:1
    },
}))

// 主题切换时同步 <html data-theme>（store.toggle 已处理，这里做兜底）
watch(() => themeStore.mode, (mode) => {
  document.documentElement.setAttribute('data-theme', mode)
})
</script>

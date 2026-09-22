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
const themeOverrides = computed(() => ({
  common: {
    ...accentThemeOverrides(themeStore.accent, themeStore.isDark),
    borderRadius: '8px',
  },
}))

// 主题切换时同步 <html data-theme>（store.toggle 已处理，这里做兜底）
watch(() => themeStore.mode, (mode) => {
  document.documentElement.setAttribute('data-theme', mode)
})
</script>

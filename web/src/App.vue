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

const themeStore = useThemeStore()
themeStore.init()

// Naive UI 跟随主题 store：dark 模式用 darkTheme，light 模式用 null
const naiveTheme = computed(() => (themeStore.isDark ? darkTheme : null))

const themeOverrides = {
  common: {
    primaryColor: '#4f46e5',
    primaryColorHover: '#6366f1',
    primaryColorPressed: '#4338ca',
    borderRadius: '8px',
  },
}

// 主题切换时同步 <html data-theme>（store.toggle 已处理，这里做兜底）
watch(() => themeStore.mode, (mode) => {
  document.documentElement.setAttribute('data-theme', mode)
})
</script>

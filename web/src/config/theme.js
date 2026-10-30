// ============================================================
// 主题强调色（主色）配置 —— 唯一数据源
//
// 全站主色由这里驱动，同时注入两条渲染路径：
//   1) Naive UI 组件的 themeOverrides（App.vue 用 accentThemeOverrides 计算）
//   2) 自定义元素的 CSS 变量（stores/theme.js 用 accentFor + toRgba 写入 <html>）
// 两处取同一份值，因此不会出现「Naive 组件一个色、自定义元素另一个色」。
//
// 每个色只维护 light / dark 两个主色值，其余派生：
//   hover / pressed 由 mix() 得到；--color-primary-soft / --color-selected 由 toRgba() 得到。
// 新增一个颜色只需在 ACCENTS 里加一行。
// ============================================================

// 默认强调色：无本地偏好时使用（枪灰）
export const DEFAULT_ACCENT = 'gray'

// 浅色模式用较深的色值，深色模式用较亮的变体。
// 主色同时用于「白底上的文字/链接」与「白字按钮的底色」，所以 light 值必须两头都 ≥4.5:1：
// 白底对比度 / 自身 16% 浅底（secondary 按钮、soft 底色）上的对比度 都达标。
// （cyan/teal/green/amber/rose/blue 原值只在按钮底色一项达标，作文字色时 3.0–4.4:1。）
export const ACCENTS = [
  { key: 'indigo', label: '靛蓝', light: '#4f46e5', dark: '#a5b4fc' }, // 6.29 / 5.26
  { key: 'blue', label: '蓝色', light: '#1d4ed8', dark: '#60a5fa' }, //  6.70 / 5.57
  { key: 'cyan', label: '青色', light: '#155e75', dark: '#22d3ee' }, //  7.27 / 5.66
  { key: 'teal', label: '青绿', light: '#115e59', dark: '#2dd4bf' }, //  7.58 / 5.88
  { key: 'green', label: '绿色', light: '#166534', dark: '#4ade80' }, //  7.13 / 5.95
  { key: 'amber', label: '琥珀', light: '#92400e', dark: '#fbbf24' }, //  7.09 / 5.88
  { key: 'rose', label: '玫红', light: '#be123c', dark: '#fda4af' }, //  6.29 / 5.12
  { key: 'violet', label: '紫罗兰', light: '#6d28d9', dark: '#c4b5fd' }, // 6.62 / 5.20
  { key: 'gray', label: '枪灰', light: '#4a4f57', dark: '#a8aeb6' }, //  8.24 / 6.84
]

// soft / selected 变量在明暗模式下的透明度（沿用改造前的取值）
const SOFT_ALPHA = { light: 0.12, dark: 0.15 }
const SELECTED_ALPHA = { light: 0.08, dark: 0.12 }
// 中透明度变体：卡片 hover 边框等需要比 soft 更实、比实色更轻的场合
const BORDER_ALPHA = { light: 0.27, dark: 0.30 }

function hexToRgb(hex) {
  const raw = String(hex).replace('#', '')
  const full = raw.length === 3 ? raw.split('').map((c) => c + c).join('') : raw
  const num = parseInt(full, 16)
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 }
}

function rgbToHex({ r, g, b }) {
  const to = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')
  return `#${to(r)}${to(g)}${to(b)}`
}

/** 把 hex 颜色按比例混合到 target（'#ffffff' / '#000000'）。 */
export function mix(hex, target, ratio) {
  const a = hexToRgb(hex)
  const b = hexToRgb(target)
  return rgbToHex({
    r: a.r + (b.r - a.r) * ratio,
    g: a.g + (b.g - a.g) * ratio,
    b: a.b + (b.b - a.b) * ratio,
  })
}

/** hex → rgba() 字符串，用于带透明度的 soft / selected 变量。 */
export function toRgba(hex, alpha) {
  const { r, g, b } = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/** 取某强调色在指定模式下的完整取值。 */
export function accentFor(key, isDark) {
  const mode = isDark ? 'dark' : 'light'
  const accent = ACCENTS.find((a) => a.key === key) || ACCENTS.find((a) => a.key === DEFAULT_ACCENT)
  return {
    key: accent.key,
    label: accent.label,
    primary: accent[mode],
    softAlpha: SOFT_ALPHA[mode],
    selectedAlpha: SELECTED_ALPHA[mode],
    borderAlpha: BORDER_ALPHA[mode],
  }
}

/** 返回在该底色上可读的文字颜色（用于色块上的对勾）。 */
export function readableOn(hex) {
  const { r, g, b } = hexToRgb(hex)
  const lum = 0.299 * r + 0.587 * g + 0.114 * b
  return lum > 150 ? '#1f2937' : '#ffffff'
}

/** Naive UI 的 common 主题覆盖（primary 系列），供 App.vue 使用。 */
export function accentThemeOverrides(key, isDark) {
  const primary = accentFor(key, isDark).primary
  const hover = mix(primary, '#ffffff', isDark ? 0.1 : 0.12)
  const pressed = mix(primary, '#000000', 0.12)
  return {
    primaryColor: primary,
    primaryColorHover: hover,
    primaryColorPressed: pressed,
    primaryColorSuppl: hover,
  }
}

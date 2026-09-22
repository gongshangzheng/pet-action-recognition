#!/usr/bin/env node
// GitHub Pages 是纯静态托管，直接访问 history 路由的深链接（如
// /<repo>/management/docs/architecture）会命中平台 404。把 index.html 复制成
// 404.html 后，平台在未知路径上返回它，Vue Router 即可接管并渲染正确页面。

import { copyFileSync, existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const indexFile = join(webDir, 'dist', 'index.html')
const fallbackFile = join(webDir, 'dist', '404.html')

if (!existsSync(indexFile)) {
  console.error(`[copy-404] 未找到 ${indexFile}，请先执行 vite build（npm run build 会自动串联）`)
  process.exit(1)
}

copyFileSync(indexFile, fallbackFile)
console.log('[copy-404] dist/index.html → dist/404.html')

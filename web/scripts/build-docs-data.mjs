#!/usr/bin/env node
// 构建期把 management/docs/ 编译为 GitHub Pages 可读取的静态文档数据与图片资产。

import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const WEB_DIR = resolve(__dirname, '..')
const REPO_ROOT = resolve(WEB_DIR, '..')
const DOCS_DIR = join(REPO_ROOT, 'management', 'docs')
const ASSETS_DIR = join(DOCS_DIR, '_assets')
const OUT_FILE = join(WEB_DIR, 'public', 'docs-data.json')
const OUT_ASSETS_DIR = join(WEB_DIR, 'public', 'docs-assets')
// 下游可在此指定顶层文件夹优先级；未列目录仍以名字稳定排序。
const FOLDER_ORDER = []

function fail(message) {
  console.error(`[build-docs-data] ${message}`)
  process.exit(1)
}

function walkMarkdown(dir) {
  const found = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('_')) continue
    const full = join(dir, entry.name)
    if (entry.isDirectory()) found.push(...walkMarkdown(full))
    else if (entry.isFile() && entry.name.endsWith('.md')) found.push(full)
  }
  return found
}

function unquote(value) {
  const text = value.trim()
  if (text.length >= 2 && ((text[0] === '"' && text.at(-1) === '"') || (text[0] === "'" && text.at(-1) === "'"))) {
    return text.slice(1, -1)
  }
  return text
}

function parseScalar(raw) {
  const value = raw.trim()
  if (!value) return ''
  if (value.startsWith('[') && value.endsWith(']')) {
    const inner = value.slice(1, -1).trim()
    return inner ? inner.split(',').map((item) => unquote(item)) : []
  }
  if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value)
  return unquote(value)
}

function parseFrontmatter(content, file) {
  if (!content.startsWith('---')) return [{}, content]
  const end = content.indexOf('---', 3)
  if (end < 0) fail(`${file}: frontmatter 起始 --- 之后没有结束 ---`)
  const meta = {}
  content.slice(3, end).split(/\r?\n/).forEach((line, index) => {
    if (!line.trim() || /^\s*#/.test(line)) return
    if (/^\s/.test(line)) fail(`${file}:${index + 2} frontmatter 不支持缩进或多行：${line}`)
    const match = /^([A-Za-z0-9_-]+):\s?(.*)$/.exec(line)
    if (!match) fail(`${file}:${index + 2} 无法解析的 frontmatter 行：${line}`)
    meta[match[1]] = parseScalar(match[2])
  })
  return [meta, content.slice(end + 3).trim()]
}

function numberOrInfinity(value) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return Infinity
  const number = Number(value)
  return Number.isFinite(number) ? number : Infinity
}

function dateOrdinal(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ''))
  if (!match) return 0
  return Math.floor(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])) / 86400000)
}

function documentFolder(meta, slug) {
  if (meta.folder === undefined || meta.folder === null || meta.folder === '') {
    return slug.includes('/') ? slug.split('/', 1)[0] : ''
  }
  return String(meta.folder)
}

function compareDocs(a, b) {
  const compare = (left, right) => (left < right ? -1 : left > right ? 1 : 0)
  const aRank = FOLDER_ORDER.indexOf(a.folder)
  const bRank = FOLDER_ORDER.indexOf(b.folder)
  return compare(aRank < 0 ? FOLDER_ORDER.length : aRank, bRank < 0 ? FOLDER_ORDER.length : bRank)
    || compare(numberOrInfinity(a.order), numberOrInfinity(b.order))
    || compare(numberOrInfinity(a.id), numberOrInfinity(b.id))
    || compare(dateOrdinal(b.date), dateOrdinal(a.date))
    || compare(a.slug, b.slug)
}

function copyAssets() {
  rmSync(OUT_ASSETS_DIR, { recursive: true, force: true })
  if (!existsSync(ASSETS_DIR)) return
  mkdirSync(dirname(OUT_ASSETS_DIR), { recursive: true })
  cpSync(ASSETS_DIR, OUT_ASSETS_DIR, { recursive: true })
}

function main() {
  if (!existsSync(DOCS_DIR)) fail(`找不到文档目录：${DOCS_DIR}`)
  const files = walkMarkdown(DOCS_DIR).sort()
  if (!files.length) fail(`文档目录中没有 .md 文件：${DOCS_DIR}`)

  const docs = []
  const details = {}
  for (const file of files) {
    const displayPath = relative(REPO_ROOT, file)
    const [meta, content] = parseFrontmatter(readFileSync(file, 'utf8'), displayPath)
    const slug = relative(DOCS_DIR, file).split(sep).join('/').replace(/\.md$/, '')
    const folder = documentFolder(meta, slug)
    const base = {
      slug,
      title: meta.title ?? slug,
      author: meta.author ?? '',
      date: meta.date === undefined || meta.date === null ? '' : String(meta.date),
      tags: Array.isArray(meta.tags) ? meta.tags : [],
      summary: meta.summary ?? '',
      id: meta.id ?? null,
      order: meta.order ?? null,
      folder,
    }
    const sidecarFile = file.replace(/\.md$/, '.json')
    let sidecar = {}
    if (existsSync(sidecarFile)) {
      try {
        sidecar = JSON.parse(readFileSync(sidecarFile, 'utf8') || '{}')
      } catch (error) {
        fail(`${relative(REPO_ROOT, sidecarFile)} 不是合法 JSON：${error.message}`)
      }
    }
    docs.push(base)
    details[slug] = { ...base, content, sidecar }
  }

  docs.sort(compareDocs)
  const orderedDetails = Object.fromEntries(docs.map((doc) => [doc.slug, details[doc.slug]]))
  mkdirSync(dirname(OUT_FILE), { recursive: true })
  copyAssets()
  writeFileSync(OUT_FILE, `${JSON.stringify({ generatedAt: new Date().toISOString(), docs, details: orderedDetails }, null, 2)}\n`)
  console.log(`[build-docs-data] ${docs.length} 篇文档 → ${relative(REPO_ROOT, OUT_FILE)}`)
}

main()

/**
 * 论文 API 封装
 *
 * 开发环境：通过 /api 代理到后端 FastAPI
 * 生产环境（GitHub Pages）：从静态 JSON 加载，收藏/置顶/笔记用 localStorage
 */
import request from './request'

const isProd = import.meta.env.PROD

// ========== localStorage 工具 ==========

const LS_KEY = 'par_favorites'
const LS_NOTE_KEY = 'par_notes'

function loadFavs() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '{}')
  } catch {
    return {}
  }
}

function saveFavs(favs) {
  localStorage.setItem(LS_KEY, JSON.stringify(favs))
}

function loadNotes() {
  try {
    return JSON.parse(localStorage.getItem(LS_NOTE_KEY) || '{}')
  } catch {
    return {}
  }
}

function saveNotes(notes) {
  localStorage.setItem(LS_NOTE_KEY, JSON.stringify(notes))
}

// ========== 静态数据加载 ==========

let _staticPapers = null

async function loadStaticPapers() {
  if (_staticPapers) return _staticPapers
  const base = import.meta.env.BASE_URL || '/'
  const resp = await fetch(`${base}data/papers.json`)
  const data = await resp.json()

  // 注入 localStorage 中的收藏/置顶状态
  const favs = loadFavs()
  const notes = loadNotes()
  data.papers.forEach(p => {
    const fav = favs[p.id] || {}
    p.starred = fav.starred || false
    p.pinned = fav.pinned || false
    p.note = notes[p.id] || ''
    p.has_note = !!p.note
  })

  _staticPapers = data
  return data
}

// ========== API 导出 ==========

// 论文列表
export const getPaperList = async (params = {}) => {
  if (isProd) {
    const data = await loadStaticPapers()
    let papers = data.papers

    // 客户端筛选
    if (params.category) {
      papers = papers.filter(p => (p.categories || []).includes(params.category))
    }
    if (params.source) {
      papers = papers.filter(p => p.source === params.source)
    }

    const limit = params.limit || 100
    const offset = params.offset || 0
    return {
      total: papers.length,
      papers: papers.slice(offset, offset + limit),
    }
  }
  return request.get('/papers', { params })
}

// 论文统计
export const getPaperStats = async () => {
  if (isProd) {
    const data = await loadStaticPapers()
    const by_source = {}
    const by_category = {}
    data.papers.forEach(p => {
      by_source[p.source] = (by_source[p.source] || 0) + 1
      ;(p.categories || []).forEach(c => {
        by_category[c] = (by_category[c] || 0) + 1
      })
    })
    return { total: data.papers.length, by_source, by_category }
  }
  return request.get('/papers/stats/summary')
}

// 论文详情
export const getPaperDetail = async (id) => {
  if (isProd) {
    const data = await loadStaticPapers()
    return data.papers.find(p => p.id === id) || { error: 'not found' }
  }
  return request.get(`/papers/${id}`)
}

// 论文笔记
export const getPaperNote = async (id) => {
  if (isProd) {
    const notes = loadNotes()
    return { content: notes[id] || '' }
  }
  return request.get(`/papers/${id}/note`)
}

export const savePaperNote = async (id, content) => {
  if (isProd) {
    const notes = loadNotes()
    notes[id] = content
    saveNotes(notes)
    // 更新缓存
    if (_staticPapers) {
      const p = _staticPapers.papers.find(p => p.id === id)
      if (p) { p.note = content; p.has_note = !!content }
    }
    return { status: 'ok' }
  }
  return request.put(`/papers/${id}/note`, { content })
}

// Blog 链接
export const setPaperBlog = async (id, blogUrl) => {
  if (isProd) {
    if (_staticPapers) {
      const p = _staticPapers.papers.find(p => p.id === id)
      if (p) p.blog_url = blogUrl
    }
    return { status: 'ok' }
  }
  return request.put(`/papers/${id}/blog`, { blog_url: blogUrl })
}

// 通过 URL 拉取论文（静态部署不支持）
export const fetchPaper = async (url, force = false) => {
  if (isProd) return { error: '静态部署不支持添加论文' }
  return request.post('/papers/fetch', { url, force })
}

// 触发摘要生成（静态部署不支持）
export const summarizePaper = async (id) => {
  if (isProd) return { status: 'not_implemented' }
  return request.post(`/papers/${id}/summarize`)
}

// 收藏 / 取消收藏
export const starPaper = async (id, starred) => {
  if (isProd) {
    const favs = loadFavs()
    if (!favs[id]) favs[id] = {}
    favs[id].starred = starred
    saveFavs(favs)
    if (_staticPapers) {
      const p = _staticPapers.papers.find(p => p.id === id)
      if (p) p.starred = starred
    }
    return { status: 'ok', starred }
  }
  return request.put(`/papers/${id}/star`, { starred })
}

// 置顶 / 取消置顶
export const pinPaper = async (id, pinned) => {
  if (isProd) {
    const favs = loadFavs()
    if (!favs[id]) favs[id] = {}
    favs[id].pinned = pinned
    saveFavs(favs)
    if (_staticPapers) {
      const p = _staticPapers.papers.find(p => p.id === id)
      if (p) p.pinned = pinned
    }
    return { status: 'ok', pinned }
  }
  return request.put(`/papers/${id}/pin`, { pinned })
}

// 缩略图 URL
export const getThumbnailUrl = (arxivId) => {
  if (isProd) return null  // 静态部署无缩略图
  return `/api/papers/thumbnails/${arxivId}`
}

// 论文 digest（静态部署不支持）
export const getDailyDigest = async () => {
  if (isProd) return { digest: null }
  return request.get('/papers/digests/daily')
}

export const generateDigest = async (period = '今日', limit = 100) => {
  if (isProd) return { error: '静态部署不支持' }
  return request.post('/papers/digests/generate', null, { params: { period, limit } })
}

// 保留旧接口兼容
export const getPaperCategories = () => Promise.resolve(['action_recognition', 'pet_action_recognition', 'pose_estimation', 'skeleton_action_recognition', 'survey', 'temporal_action_detection', 'video_foundation_model'])
export const getPaperSources = async () => {
  if (isProd) return { sources: ['arxiv', 'manual'] }
  return request.get('/papers/sources')
}
export const updatePaperSource = async (id, data) => {
  if (isProd) return { status: 'ok' }
  return request.put(`/papers/sources/${id}`, data)
}
import request from './request'

// 论文列表（代理 SeekVerse）
export const getPaperList = (params) => request.get('/papers', { params })

// 论文统计
export const getPaperStats = () => request.get('/papers/stats/summary')

// 论文详情
export const getPaperDetail = (id) => request.get(`/papers/${id}`)

// 论文笔记
export const getPaperNote = (id) => request.get(`/papers/${id}/note`)
export const savePaperNote = (id, content) => request.put(`/papers/${id}/note`, { content })

// Blog 链接
export const setPaperBlog = (id, blogUrl) => request.put(`/papers/${id}/blog`, { blog_url: blogUrl })

// 通过 URL 拉取论文
export const fetchPaper = (url, force = false) => request.post('/papers/fetch', { url, force })

// 触发摘要生成
export const summarizePaper = (id) => request.post(`/papers/${id}/summarize`)

// 收藏 / 取消收藏
export const starPaper = (id, starred) => request.put(`/papers/${id}/star`, { starred })

// 置顶 / 取消置顶
export const pinPaper = (id, pinned) => request.put(`/papers/${id}/pin`, { pinned })

// 缩略图 URL
export const getThumbnailUrl = (arxivId) => `/api/papers/thumbnails/${arxivId}`

// 论文 digest
export const getDailyDigest = () => request.get('/papers/digests/daily')
export const generateDigest = (period = '今日', limit = 100) => request.post('/papers/digests/generate', null, { params: { period, limit } })

// 保留旧接口兼容
export const getPaperCategories = () => Promise.resolve(['autoregressive', 'diffusion', 'image_compression', 'visual_tokenizer'])
export const getPaperSources = () => request.get('/papers/sources')
export const updatePaperSource = (id, data) => request.put(`/papers/sources/${id}`, data)

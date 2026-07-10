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

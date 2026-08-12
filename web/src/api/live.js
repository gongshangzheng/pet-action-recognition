import request from './request'

// 摄像头源 CRUD
export const getSources = () => request.get('/live/sources')
export const createSource = (data) => request.post('/live/sources', data)
export const updateSource = (id, data) => request.put(`/live/sources/${id}`, data)
export const deleteSource = (id) => request.delete(`/live/sources/${id}`)

// 源下视频文件
export const getSourceFiles = (id) => request.get(`/live/sources/${id}/files`)

// 生成带 stream_token 的播放 url
export const getPlayUrl = (alias, filename) =>
  request.get('/live/play_url', { params: { alias, filename } })

// 截屏
export const getScreenshots = (sourceId) =>
  request.get('/live/screenshots', sourceId ? { params: { source_id: sourceId } } : {})
export const createScreenshot = (data) => request.post('/live/screenshots', data)

// 演示模式
export const getDemoVideos = () => request.get('/live/demo/videos')
export const getDemoVideoUrl = (videoName) => `/api/live/demo/video/${videoName}`

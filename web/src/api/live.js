import request from './request'

// 截屏
export const getScreenshots = () => request.get('/live/screenshots')
export const createScreenshot = (data) => request.post('/live/screenshots', data)

// 摄像头源
export const getStreamSources = () => request.get('/live/sources').then(d => d.sources)
export const createStreamSource = (data) => request.post('/live/sources', data).then(d => d.source)
export const updateStreamSource = (id, data) => request.put(`/live/sources/${id}`, data).then(d => d.source)
export const deleteStreamSource = (id) => request.delete(`/live/sources/${id}`)
// 别名（SourceManageModal 使用的名字）
export const createSource = createStreamSource
export const updateSource = updateStreamSource

// 演示模式
export const getDemoVideos = () => request.get('/live/demo/videos')
export const getDemoVideoUrl = (videoName) => `/api/live/demo/video/${videoName}`

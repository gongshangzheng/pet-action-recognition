import request from './request'

// speed run（N 视频 × M 模型 → 标注视频 + 聚合结果）
export const speedRun = (data) => request.post('/speedrun/run', data)
export const getSpeedrunStatus = () => request.get('/speedrun/status')
export const getSpeedrunResults = (runName = null) =>
  request.get('/speedrun/results', { params: runName ? { run_name: runName } : {} })
export const listSpeedrunOutputs = () => request.get('/speedrun/outputs')
export const getSpeedrunOutputUrl = (path) => `/api/speedrun/outputs/${path}`

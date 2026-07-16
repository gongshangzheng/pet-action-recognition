import request from './request'

// 模型
export const getModels = () => request.get('/evaluation/models')
export const getModelDetail = (id) => request.get(`/evaluation/models/${id}`)

// 数据集
export const getDatasets = () => request.get('/evaluation/datasets')
export const getDatasetDetail = (id) => request.get(`/evaluation/datasets/${id}`)

// 评测配置
export const getEvalConfigs = () => request.get('/evaluation/configs')
export const getEvalConfig = (id) => request.get(`/evaluation/configs/${id}`)

// 评测运行
export const runEvaluation = (data) => request.post('/evaluation/run', data)

// 评测结果
export const getEvalResults = (params) => request.get('/evaluation/results', { params })
export const getEvalResultDetail = (id) => request.get(`/evaluation/results/${id}`)
export const compareResults = (params) => request.get('/evaluation/results/compare', { params })

// 输出视频/码流（按需服务）
export const listOutputs = () => request.get('/evaluation/outputs')
// 拼接按需播放 URL（<video preload="none"> 仅在挂载时才请求字节）
export const getOutputUrl = (path) => `/api/evaluation/outputs/${path}`

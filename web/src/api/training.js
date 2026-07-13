import request from './request'

// 可训练模型
export const getTrainModels = () => request.get('/training/models')
export const getTrainModelDetail = (id) => request.get(`/training/models/${id}`)

// 训练数据集
export const getTrainDatasets = () => request.get('/training/datasets')
export const getTrainDatasetDetail = (id) => request.get(`/training/datasets/${id}`)

// 训练超参配置
export const getTrainConfigs = () => request.get('/training/configs')
export const getTrainConfig = (id) => request.get(`/training/configs/${id}`)

// 训练运行
export const runTraining = (data) => request.post('/training/run', data)

// 训练 run 列表/详情
export const getTrainRuns = (params) => request.get('/training/runs', { params })
export const getTrainRunDetail = (id) => request.get(`/training/runs/${id}`)

// checkpoint
export const listCheckpoints = () => request.get('/training/checkpoints')
export const getCheckpointDetail = (id) => request.get(`/training/checkpoints/${id}`)

// 训练产物（checkpoint/log 文件，按需下载/查看）
export const listTrainOutputs = () => request.get('/training/outputs')
export const getTrainOutputUrl = (path) => `/api/training/outputs/${path}`

import request from './request'

export const listDatasets = () => request.get('/datasets')
export const browseDataset = (datasetId, params) => request.get(`/datasets/${datasetId}/browse`, { params })
export const getDatasetFileUrl = (datasetId, path) => `/api/datasets/${datasetId}/file?path=${encodeURIComponent(path)}`
export const getDatasetThumbUrl = (datasetId, path) => `/api/datasets/${datasetId}/thumb?path=${encodeURIComponent(path)}`

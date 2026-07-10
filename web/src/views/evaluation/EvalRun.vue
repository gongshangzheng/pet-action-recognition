<template>
  <div class="page-container">
    <n-card title="评测配置与运行" size="small">
      <n-spin :show="loading">
        <n-form ref="formRef" :model="form" label-placement="left" :label-width="100" style="max-width: 600px">
          <n-form-item label="选择模型" required>
            <n-select v-model:value="form.model_id" :options="modelOptions" placeholder="请选择模型" />
          </n-form-item>
          <n-form-item label="选择数据集" required>
            <n-select v-model:value="form.dataset_id" :options="datasetOptions" placeholder="请选择数据集" />
          </n-form-item>
          <n-form-item label="评测配置">
            <n-select v-model:value="form.config_id" :options="configOptions" placeholder="选择配置（可选）" clearable />
          </n-form-item>
          <n-form-item label="Batch Size">
            <n-input-number v-model:value="form.batch_size" :min="1" :max="256" />
          </n-form-item>
          <n-form-item label="设备">
            <n-radio-group v-model:value="form.device">
              <n-radio value="cuda">GPU (CUDA)</n-radio>
              <n-radio value="cpu">CPU</n-radio>
            </n-radio-group>
          </n-form-item>
          <n-form-item label="额外参数">
            <n-input v-model:value="form.extra_args" type="textarea" :rows="2" placeholder="--clip_len 16 --num_workers 4" />
          </n-form-item>
          <n-form-item label=" ">
            <n-button type="primary" :loading="running" @click="handleRun">启动评测</n-button>
          </n-form-item>
        </n-form>
      </n-spin>
    </n-card>

    <n-card v-if="runResult" title="运行结果" size="small" style="margin-top: 16px">
      <n-alert :type="runResult.success ? 'success' : 'error'" :title="runResult.success ? '评测完成' : '评测失败'">
        <pre>{{ runResult.output }}</pre>
      </n-alert>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { NCard, NSpin, NForm, NFormItem, NSelect, NInputNumber, NRadioGroup, NRadio, NInput, NButton, NAlert, useMessage } from 'naive-ui'
import { getModels, getDatasets, getEvalConfigs, runEvaluation } from '../../api/evaluation'

const message = useMessage()
const loading = ref(false)
const running = ref(false)
const models = ref([])
const datasets = ref([])
const configs = ref([])
const runResult = ref(null)
const form = ref({ model_id: null, dataset_id: null, config_id: null, batch_size: 8, device: 'cuda', extra_args: '' })

const modelOptions = computed(() => models.value.map(m => ({ label: `${m.name} (${m.type})`, value: m.id })))
const datasetOptions = computed(() => datasets.value.map(d => ({ label: d.name, value: d.id })))
const configOptions = computed(() => configs.value.map(c => ({ label: c.name || c.id, value: c.id })))

async function handleRun() {
  if (!form.value.model_id || !form.value.dataset_id) {
    message.warning('请选择模型和数据集')
    return
  }
  running.value = true
  runResult.value = null
  try {
    const res = await runEvaluation(form.value)
    runResult.value = { success: true, output: JSON.stringify(res, null, 2) }
    message.success('评测已完成')
  } catch (e) {
    runResult.value = { success: false, output: e.message || '评测执行失败' }
    message.error('评测执行失败')
  }
  running.value = false
}

onMounted(async () => {
  loading.value = true
  try {
    const [m, d, c] = await Promise.all([
      getModels().catch(() => []),
      getDatasets().catch(() => []),
      getEvalConfigs().catch(() => []),
    ])
    models.value = m || []
    datasets.value = d || []
    configs.value = c || []
  } catch {}
  loading.value = false
})
</script>

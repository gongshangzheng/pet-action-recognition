<template>
  <div class="page-container">
    <n-card title="训练配置与运行" size="small">
      <n-spin :show="loading">
        <n-form ref="formRef" :model="form" label-placement="left" :label-width="100" style="max-width: 600px">
          <n-form-item label="选择模型" required>
            <n-select v-model:value="form.model_id" :options="modelOptions" placeholder="可训练 DL 模型" />
          </n-form-item>
          <n-form-item label="选择数据集" required>
            <n-select v-model:value="form.dataset_id" :options="datasetOptions" placeholder="训练数据集" />
          </n-form-item>
          <n-form-item label="训练配置">
            <n-select v-model:value="form.config_id" :options="configOptions" placeholder="超参 preset（可选）" clearable />
          </n-form-item>
          <n-form-item label="Epochs">
            <n-input-number v-model:value="form.epochs" :min="1" :max="1000" />
          </n-form-item>
          <n-form-item label="学习率 lr">
            <n-input-number v-model:value="form.lr" :step="0.0001" :min="0" />
          </n-form-item>
          <n-form-item label="Batch Size">
            <n-input-number v-model:value="form.batch_size" :min="1" :max="512" />
          </n-form-item>
          <n-form-item label="设备">
            <n-radio-group v-model:value="form.device">
              <n-radio value="cuda">GPU (CUDA)</n-radio>
              <n-radio value="cpu">CPU</n-radio>
            </n-radio-group>
          </n-form-item>
          <n-form-item label=" ">
            <n-collapse :default-expanded-names="[]" style="width: 100%">
              <n-collapse-item title="高级超参（可选，覆盖 config）" name="adv">
                <div class="adv-grid">
                  <n-form-item label="weight_decay" label-placement="top" :show-feedback="false">
                    <n-input-number v-model:value="form.weight_decay" :step="0.01" :min="0" placeholder="config 默认" />
                  </n-form-item>
                  <n-form-item label="backbone_lr_mult" label-placement="top" :show-feedback="false">
                    <n-input-number v-model:value="form.backbone_lr_mult" :step="0.05" :min="0" :max="1" placeholder="config 默认" />
                  </n-form-item>
                  <n-form-item label="label_smoothing" label-placement="top" :show-feedback="false">
                    <n-input-number v-model:value="form.label_smoothing" :step="0.05" :min="0" :max="1" placeholder="0=关" />
                  </n-form-item>
                  <n-form-item label="num_clips_val" label-placement="top" :show-feedback="false">
                    <n-input-number v-model:value="form.num_clips_val" :step="1" :min="1" :max="10" placeholder="config 默认" />
                  </n-form-item>
                </div>
                <n-form-item label="override 片段（Python）" label-placement="top" :show-feedback="false">
                  <n-input v-model:value="form.override_snippet" type="textarea" :rows="3" placeholder="param_scheduler = [dict(type='LinearLR', start_factor=0.1, by_epoch=True, begin=0, end=5)]&#10;model.cls_head.dropout = 0.5&#10;每行 verbatim 追加到 override config（可写任意 dict 值）" />
                </n-form-item>
                <p class="hint">weight_decay/backbone_lr_mult/label_smoothing/片段走 override 文件（mmengine cfg-options 不支持 {} 字典）；num_clips_val 走 cfg-options。最终命令见训练日志 [cmd] 行。</p>
              </n-collapse-item>
            </n-collapse>
          </n-form-item>
          <n-form-item label="额外参数">
            <n-input v-model:value="form.extra_args" type="textarea" :rows="2" placeholder="--scheduler cosine --num_workers 4" />
          </n-form-item>
          <n-form-item label=" ">
            <n-button type="primary" :loading="running" @click="handleRun">启动训练</n-button>
          </n-form-item>
        </n-form>
      </n-spin>
    </n-card>

    <n-card v-if="runResult" title="训练结果" size="small" style="margin-top: 16px">
      <n-alert :type="runResult.success ? 'success' : 'error'" :title="runResult.success ? '训练已启动/完成' : '训练失败'">
        <pre>{{ runResult.output }}</pre>
      </n-alert>
      <div v-if="runResult.checkpoint" style="margin-top: 12px">
        <h4>训练 checkpoint</h4>
        <n-code>{{ runResult.checkpoint }}</n-code>
        <p class="hint">该 checkpoint 可在「评测运行」页选 DL 模型时引用（checkpoint→eval 打通）。</p>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { NCard, NSpin, NForm, NFormItem, NSelect, NInputNumber, NRadioGroup, NRadio, NInput, NButton, NAlert, NCode, NCollapse, NCollapseItem, useMessage } from 'naive-ui'
import { getTrainModels, getTrainDatasets, getTrainConfigs, runTraining } from '../../api/training'

const message = useMessage()
const loading = ref(false)
const running = ref(false)
const models = ref([])
const datasets = ref([])
const configs = ref([])
const runResult = ref(null)
const form = ref({ model_id: null, dataset_id: null, config_id: null, epochs: 100, lr: 1e-4, batch_size: 16, device: 'cuda', extra_args: '', weight_decay: null, backbone_lr_mult: null, label_smoothing: 0, num_clips_val: null, override_snippet: '' })

// 下拉框跨浏览器刷新(F5)持久化（不清空）
const FORM_STORE_KEY = 'projflow:train-run'
const PERSIST_FIELDS = ['model_id', 'dataset_id', 'config_id']
function persistForm() {
  try {
    const snap = {}
    for (const k of PERSIST_FIELDS) snap[k] = form.value[k]
    localStorage.setItem(FORM_STORE_KEY, JSON.stringify(snap))
  } catch { /* localStorage 不可用静默 */ }
}
function restoreForm() {
  try {
    const snap = JSON.parse(localStorage.getItem(FORM_STORE_KEY) || '{}')
    for (const k of PERSIST_FIELDS) if (snap[k] != null) form.value[k] = snap[k]
  } catch { /* ignore */ }
}
watch(() => [form.value.model_id, form.value.dataset_id, form.value.config_id], persistForm)
restoreForm()

const modelOptions = computed(() => models.value.map(m => ({ label: `${m.name || m.id} (${m.架构 || m.type || '?'})`, value: m.id })))
const datasetOptions = computed(() => datasets.value.map(d => ({ label: d.name || d.id, value: d.id })))
const configOptions = computed(() => configs.value.map(c => ({ label: c.name || c.id, value: c.id })))

// 选中「训练配置」preset 时把其超参回填到表单（仅覆盖 preset 含的字段）。
watch(() => form.value.config_id, (cfgId) => {
  if (!cfgId) return
  const cfg = configs.value.find(c => c.id === cfgId)
  if (!cfg) return
  const fields = ['epochs', 'lr', 'batch_size']
  for (const f of fields) {
    if (cfg[f] != null) form.value[f] = cfg[f]
  }
})

async function handleRun() {
  if (!form.value.model_id || !form.value.dataset_id) {
    message.warning('请选择模型和数据集')
    return
  }
  running.value = true
  runResult.value = null
  try {
    const res = await runTraining(form.value)
    runResult.value = {
      success: true,
      output: JSON.stringify(res, null, 2),
      checkpoint: res?.checkpoint || null,
    }
    message.success('训练任务已提交')
  } catch (e) {
    runResult.value = { success: false, output: e.message || '训练执行失败' }
    message.error('训练执行失败')
  }
  running.value = false
}

onMounted(async () => {
  loading.value = true
  try {
    const [m, d, c] = await Promise.all([
      getTrainModels().catch(() => []),
      getTrainDatasets().catch(() => []),
      getTrainConfigs().catch(() => []),
    ])
    models.value = m || []
    datasets.value = d || []
    configs.value = c || []
  } catch {}
  loading.value = false
})
</script>

<style scoped>
.hint { font-size: 12px; color: var(--color-text-dim); margin-top: 4px; }
.adv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
</style>

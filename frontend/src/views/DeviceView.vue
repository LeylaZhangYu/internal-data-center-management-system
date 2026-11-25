<template>
  <div class="page-card">
    <div class="toolbar">
      <el-select v-model="filters.data_center_id" clearable filterable placeholder="全部机房" aria-label="按机房筛选" style="width:220px" @change="searchDevices">
        <el-option v-for="item in datacenters" :key="item.id" :label="`${item.name}（${item.id}）`" :value="item.id" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索资产编号/名称/IP/型号" style="width:240px" @keyup.enter="searchDevices" />
      <el-select v-model="filters.device_type" clearable placeholder="设备类型" style="width:200px" @change="searchDevices">
        <el-option label="通用服务器 (server)" value="server" />
        <el-option label="GPU服务器 (gpu_server)" value="gpu_server" />
        <el-option label="CPU服务器 (cpu_server)" value="cpu_server" />
        <el-option label="管理节点 (management_node)" value="management_node" />
        <el-option label="交换机 (switch)" value="switch" />
        <el-option label="存储 (storage)" value="storage" />
        <el-option label="配电单元 (pdu)" value="pdu" />
        <el-option label="防火墙 (firewall)" value="firewall" />
        <el-option label="其他 (other)" value="other" />
      </el-select>
      <el-select v-model="filters.status" clearable placeholder="状态" style="width:220px" @change="searchDevices">
        <el-option label="计划中 (planned)" value="planned" />
        <el-option label="运行中 (active)" value="active" />
        <el-option label="待机 (standby)" value="standby" />
        <el-option label="维护中 (maintenance)" value="maintenance" />
        <el-option label="已退役 (retired)" value="retired" />
        <el-option label="已下架 (off_shelf)" value="off_shelf" />
      </el-select>
      <el-button @click="searchDevices">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
      <el-button type="primary" @click="openDialog()" :disabled="!canEdit">新增设备</el-button>
      <el-button type="danger" plain :disabled="!canEdit || listLoading || !selectedRows.length" :loading="deleting" @click="deleteSelected">批量删除{{ selectedRows.length ? `（${selectedRows.length}）` : '' }}</el-button>
      <el-upload :show-file-list="false" :before-upload="beforeUpload" accept=".csv,.xlsx" :disabled="!canEdit">
        <el-button :disabled="!canEdit">导入CSV/XLSX</el-button>
      </el-upload>
      <el-button @click="download('/devices/export/csv', '设备清单.csv')">导出CSV</el-button>
      <el-button @click="download('/devices/export/xlsx', '设备清单.xlsx')">导出XLSX</el-button>
      <el-dropdown @command="downloadTemplate">
        <el-button>下载导入模板 ▾</el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="xlsx">Excel 模板（含填写说明）</el-dropdown-item>
            <el-dropdown-item command="csv">CSV 模板</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <p class="import-help">导入支持中英文表头。必填：设备名称、设备类型；资产编号、型号、IP地址可留空；类型和状态使用英文代码，具体见 Excel 模板说明。</p>

    <p v-if="selectedRows.length" class="import-help">已选 {{ selectedRows.length }} 台设备，仅删除本页勾选项；切换分页或查询条件将清空选择。</p>
    <div v-loading="listLoading || deleting" class="device-table-layout">
      <div class="device-info-scroll">
    <el-table ref="tableRef" class="device-table" :data="rows" row-key="id" @selection-change="setSelection" table-layout="fixed" style="min-width:1350px">
      <el-table-column type="selection" width="48" :selectable="() => canEdit && !listLoading && !deleting" />
      <el-table-column prop="asset_number" label="资产编号" width="140" show-overflow-tooltip>
        <template #default="scope">{{ scope.row.asset_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="name" label="设备名称" width="160" show-overflow-tooltip />
      <el-table-column prop="device_type" label="类型" width="190" show-overflow-tooltip>
          <template #default="scope">{{ deviceTypeLabel(scope.row.device_type) }}</template>
        </el-table-column>
      <el-table-column prop="model" label="型号" width="140" show-overflow-tooltip>
        <template #default="scope">{{ scope.row.model || '-' }}</template>
      </el-table-column>
      <el-table-column label="所属机房" width="160" show-overflow-tooltip>
        <template #default="scope">{{ dataCenterName(scope.row) }}</template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP" width="140" show-overflow-tooltip>
        <template #default="scope">{{ scope.row.ip_address || '-' }}</template>
      </el-table-column>
      <el-table-column label="安装位置" width="190">
        <template #default="scope">{{ formatInstallLocation(scope.row) }}</template>
      </el-table-column>
      <el-table-column prop="u_height" label="占用U" width="90" />
      <el-table-column prop="status" label="状态" width="190" show-overflow-tooltip>
          <template #default="scope">{{ deviceStatusLabel(scope.row.status) }}</template>
        </el-table-column>
      <el-table-column label="管理员" width="180" show-overflow-tooltip>
        <template #default="scope">{{ (scope.row.administrators || []).map((a:any) => a.name).join('、') }}</template>
      </el-table-column>
    </el-table>
      </div>
      <el-table class="device-actions-table" :data="rows" table-layout="fixed">
        <el-table-column label="操作" min-width="140">
          <template #default="scope">
            <el-button size="small" @click="openDialog(scope.row)" :disabled="!canEdit">编辑</el-button>
            <el-button size="small" type="primary" plain @click="openMove(scope.row)" :disabled="!canEdit">移动</el-button>
            <el-button size="small" type="warning" plain @click="unmount(scope.row)" :disabled="!canEdit || scope.row.status === 'off_shelf'">下架</el-button>
            <el-button size="small" @click="openDetail(scope.row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div style="margin-top:16px; display:flex; justify-content:flex-end">
      <el-pagination background layout="prev, pager, next, total" :total="total" v-model:current-page="page" :page-size="pageSize" @current-change="load" />
    </div>

    <el-dialog v-model="visible" :title="form.id ? '编辑设备' : '新增设备'" width="840px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="24"><el-form-item label="资产编号" prop="asset_number">
            <el-input v-model="form.asset_number" placeholder="选填；新编号只需填写末尾部分，如001" />
            <p class="asset-code-help">{{ assetCodePreview ? `保存编号：${assetCodePreview}` : '选好机房和机柜后，自动补充机房ID_区域ID_前缀；留空则不生成编号。' }}</p>
            <p v-if="form.id" class="asset-code-help">修改编号时按所选机柜生成前缀；编辑其他字段或移动设备时保留原编号。</p>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="设备名称" prop="name" required><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="机房" prop="data_center_id" required><el-select v-model="form.data_center_id" clearable style="width:100%" @change="onDataCenterChange"><el-option v-for="item in datacenters" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="设备类型" prop="device_type" required><el-select v-model="form.device_type" style="width:100%"><el-option label="通用服务器 (server)" value="server" />
        <el-option label="GPU服务器 (gpu_server)" value="gpu_server" />
        <el-option label="CPU服务器 (cpu_server)" value="cpu_server" />
        <el-option label="管理节点 (management_node)" value="management_node" /><el-option label="交换机 (switch)" value="switch" /><el-option label="存储 (storage)" value="storage" /><el-option label="配电单元 (pdu)" value="pdu" /><el-option label="防火墙 (firewall)" value="firewall" /><el-option label="其他 (other)" value="other" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="型号" prop="model"><el-input v-model="form.model" placeholder="选填" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="序列号"><el-input v-model="form.serial_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="用途" prop="purpose" required><el-input v-model="form.purpose" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态" prop="status" required><el-select v-model="form.status" style="width:100%"><el-option label="计划中 (planned)" value="planned" /><el-option label="运行中 (active)" value="active" /><el-option label="待机 (standby)" value="standby" /><el-option label="维护中 (maintenance)" value="maintenance" /><el-option label="已退役 (retired)" value="retired" /><el-option label="已下架 (off_shelf)" value="off_shelf" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="IP地址" prop="ip_address"><el-input v-model="form.ip_address" placeholder="选填" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="机柜" prop="rack_id" required><el-select v-model="form.rack_id" clearable style="width:100%"><el-option v-for="item in filteredRacks" :key="item.id" :label="item.code" :value="item.id" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="起始U位" required><el-input-number v-model="form.start_u" :min="1" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="占用U数"><el-input-number v-model="form.u_height" :min="1" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="CPU"><el-input v-model="form.cpu" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="内存GB"><el-input-number v-model="form.memory_gb" :min="0" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="GPU"><el-input v-model="form.gpu" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="硬盘"><el-input v-model="form.storage_desc" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="操作系统"><el-input v-model="form.operating_system" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="管理员" prop="administrator_ids" required><el-select v-model="form.administrator_ids" multiple style="width:100%"><el-option v-for="item in administrators" :key="item.id" :label="`${item.name}(${item.department})`" :value="item.id" /></el-select></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="端口"><el-input v-model="portsText" placeholder="使用英文逗号分隔，如 eth0,eth1" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="备注"><el-input v-model="form.notes" type="textarea" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="moveVisible" title="移动设备" width="420px">
      <el-form :model="moveForm" label-width="90px">
        <el-form-item label="目标机柜" required><el-select v-model="moveForm.rack_id" style="width:100%"><el-option v-for="item in racks" :key="item.id" :label="item.code" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="起始U位" required><el-input-number v-model="moveForm.start_u" :min="1" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="moveForm.comment" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmMove">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="设备详情" size="560px">
      <el-descriptions v-if="currentDetail" :column="2" border>
        <el-descriptions-item label="资产编号">{{ currentDetail.asset_number || '-' }}</el-descriptions-item>
        <el-descriptions-item label="名称">{{ currentDetail.name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ deviceTypeLabel(currentDetail.device_type) }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ currentDetail.model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentDetail.ip_address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ deviceStatusLabel(currentDetail.status) }}</el-descriptions-item>
        <el-descriptions-item label="安装位置">{{ formatInstallLocation(currentDetail) }}</el-descriptions-item>
        <el-descriptions-item label="管理员">{{ (currentDetail.administrators || []).map((a:any) => a.name).join('、') }}</el-descriptions-item>
        <el-descriptions-item label="端口" :span="2">{{ (currentDetail.ports || []).map((p:any) => p.name).join('、') }}</el-descriptions-item>
        <el-descriptions-item label="CPU">{{ currentDetail.cpu || '-' }}</el-descriptions-item>
        <el-descriptions-item label="内存">{{ currentDetail.memory_gb || '-' }} GB</el-descriptions-item>
        <el-descriptions-item label="GPU">{{ currentDetail.gpu || '-' }}</el-descriptions-item>
        <el-descriptions-item label="硬盘">{{ currentDetail.storage_desc || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'
import { deviceStatusLabel, deviceTypeLabel } from '../utils/labels'
import { deviceCodePreview } from '../utils/deviceCode'
import { useBatchDelete } from '../composables/useBatchDelete'

const auth = useAuthStore()
const canEdit = computed(() => auth.user?.role === 'admin')
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const listLoading = ref(false)
let listRequest: AbortController | undefined
const visible = ref(false)
const moveVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref<any>(null)
const movingId = ref<number | null>(null)
const racks = ref<any[]>([])
const datacenters = ref<any[]>([])
const filteredRacks = computed(() => racks.value.filter((rack) => !form.data_center_id || rack.data_center_id === form.data_center_id))
const administrators = ref<any[]>([])
const filters = reactive<any>({ keyword: '', device_type: '', status: '', data_center_id: undefined })
const form = reactive<any>({})
const originalAssetNumber = ref<string | null>(null)
const assetCodePreview = computed(() => deviceCodePreview(form.asset_number, racks.value.find(rack => rack.id === form.rack_id), originalAssetNumber.value))
const moveForm = reactive<any>({ rack_id: undefined, start_u: 1, comment: '' })
const portsText = ref('')
const formRef = ref<any>()
const formRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  device_type: [{ required: true, message: '请选择设备类型', trigger: 'change' }],
  purpose: [{ required: true, message: '请输入用途', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  rack_id: [{ required: true, message: '请选择机柜', trigger: 'change' }],
  administrator_ids: [{ type: 'array', required: true, min: 1, message: '请选择至少一名管理员', trigger: 'change' }],
  data_center_id: [{ required: true, message: '请选择机房', trigger: 'change' }],
}

const resetForm = () => Object.assign(form, { id: undefined, data_center_id: filters.data_center_id || undefined, asset_number: '', name: '', device_type: 'server', model: '', serial_number: '', purpose: '', status: 'planned', ip_address: '', rack_id: undefined, start_u: undefined, u_height: 1, cpu: '', memory_gb: undefined, gpu: '', storage_desc: '', operating_system: '', notes: '', administrator_ids: [] })
const parsePorts = () => portsText.value.split(',').map((x) => x.trim()).filter(Boolean).map((name) => ({ name }))
const dataCenterName = (device: any) => {
  const rack = racks.value.find((item) => item.id === device?.rack_id)
  return datacenters.value.find((item) => item.id === rack?.data_center_id)?.name || '未指定'
}
const rackCode = (rackId: number) => racks.value.find((rack) => rack.id === rackId)?.code || `机柜${rackId}`
const formatInstallLocation = (device: any) => {
  if (!device?.rack_id || !device?.start_u) return '未上架'
  const endU = device.start_u + Math.max(Number(device.u_height || 1), 1) - 1
  return `${rackCode(device.rack_id)} / U${device.start_u}–U${endU}`
}

const onDataCenterChange = () => {
  if (!filteredRacks.value.some((rack) => rack.id === form.rack_id)) form.rack_id = undefined
}
const loadRacks = async () => {
  const items: any[] = []
  for (let rackPage = 1; ; rackPage++) {
    const { data } = await client.get('/racks', { params: { page: rackPage, page_size: 100 } })
    items.push(...data.items)
    if (!data.items.length || items.length >= data.total) return items
  }
}
const loadAux = async () => {
  const [rackResult, dcResult, adminResult] = await Promise.allSettled([
    loadRacks(),
    client.get('/datacenters'),
    client.get('/administrators'),
  ])
  if (rackResult.status === 'fulfilled') racks.value = rackResult.value
  if (dcResult.status === 'fulfilled') datacenters.value = dcResult.value.data || []
  if (adminResult.status === 'fulfilled') administrators.value = adminResult.value.data || []
  if ([rackResult, dcResult, adminResult].some(result => result.status === 'rejected')) ElMessage.warning('部分机房、机柜或管理员信息加载失败，请刷新重试')
}
const load = async () => {
  clearSelection()
  listRequest?.abort()
  const controller = new AbortController()
  listRequest = controller
  listLoading.value = true
  try {
    const { data } = await client.get('/devices', { signal: controller.signal, params: {
      page: page.value, page_size: pageSize, ...filters, data_center_id: filters.data_center_id || undefined,
    } })
    if (!controller.signal.aborted) {
      rows.value = data.items
      total.value = data.total
      const lastPage = Math.max(1, Math.ceil(data.total / pageSize))
      if (page.value > lastPage) { page.value = lastPage; await load() }
    }
  } catch (error: any) {
    if (!controller.signal.aborted) { rows.value = []; total.value = 0; ElMessage.error(error?.response?.data?.detail || '设备列表加载失败') }
  } finally { if (!controller.signal.aborted) listLoading.value = false }
}
const { tableRef, selectedRows, deleting, setSelection, clearSelection, deleteSelected } = useBatchDelete({
  resource: 'devices', canDelete: () => canEdit.value && !listLoading.value, reload: load,
  onDeleted: (ids) => { if (ids.includes(currentDetail.value?.id)) { detailVisible.value = false; currentDetail.value = null } },
})
const searchDevices = () => { page.value = 1; load() }
const resetFilters = () => {
  Object.assign(filters, { keyword: '', device_type: '', status: '', data_center_id: undefined })
  searchDevices()
}
onBeforeUnmount(() => listRequest?.abort())
const openDialog = (row?: any) => {
  resetForm()
  originalAssetNumber.value = row?.asset_number || null
  portsText.value = ''
  if (row) {
    Object.assign(form, row)
    form.data_center_id = racks.value.find((rack) => rack.id === row.rack_id)?.data_center_id
    form.administrator_ids = (row.administrators || []).map((item:any) => item.id)
    portsText.value = (row.ports || []).map((p:any) => p.name).join(',')
  }
  visible.value = true
}
const save = async () => {
  try {
    await formRef.value?.validate()
    if (assetCodePreview.value.length > 100) { ElMessage.warning('完整资产编号（含前缀）不能超过100个字符'); return }
    const { data_center_id, ...deviceForm } = form
    const payload = { ...deviceForm, ports: parsePorts() }
    if (form.id) await client.put(`/devices/${form.id}`, payload)
    else await client.post('/devices', payload)
    ElMessage.success('保存成功')
    visible.value = false
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  }
}
const openMove = (row: any) => {
  movingId.value = row.id
  Object.assign(moveForm, { rack_id: row.rack_id, start_u: row.start_u || 1, comment: '' })
  moveVisible.value = true
}
const confirmMove = async () => {
  try {
    await client.post(`/devices/${movingId.value}/move`, moveForm)
    ElMessage.success('移动成功')
    moveVisible.value = false
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '移动失败')
  }
}
const unmount = async (row: any) => {
  await client.post(`/devices/${row.id}/unmount`, { comment: '前端执行下架' })
  ElMessage.success('设备已下架')
  load()
}
const openDetail = async (row: any) => {
  const { data } = await client.get(`/devices/${row.id}`)
  currentDetail.value = data
  detailVisible.value = true
}
const beforeUpload = async (file: any) => {
  const formData = new FormData()
  formData.append('file', file)
  try {
    const { data } = await client.post('/devices/import', formData)
    ElMessage.success(data.message)
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '导入失败')
  }
  return false
}
const downloadTemplate = (format: string) => download(`/devices/template/${format}`, `设备导入模板.${format}`)
const download = async (url: string, filename: string) => {
  try {
  const response = await client.get(url, { responseType: 'blob' })
  const blobUrl = window.URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(blobUrl)
  } catch {
    ElMessage.error('下载失败，请检查登录状态或稍后重试')
  }
}

onMounted(async () => {
  await loadAux()
  resetForm()
  await load()
})
</script>

<style scoped>
.asset-code-help { color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.6; margin: 5px 0 0; overflow-wrap: anywhere; }
.import-help { color: #64748b; font-size: 12px; margin: 0 0 16px; }
.device-table-layout { display: grid; grid-template-columns: minmax(0, 1fr) 280px; align-items: start; }
.device-info-scroll { min-width: 0; overflow-x: auto; }
.device-table { width: 100%; }
.device-table :deep(.el-checkbox) { height: 24px; }
.device-actions-table { width: 280px; }
/* Narrow screens keep the information pane usable without overlaying actions. */
@media (max-width: 700px) {
  .device-table-layout { grid-template-columns: minmax(0, 1fr) 150px; }
  .device-actions-table { width: 150px; }
  .device-actions-table :deep(.el-table__body .cell) { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
  .device-actions-table :deep(.el-button) { margin: 0; padding: 4px; }
  .device-table-layout :deep(.el-table__body td.el-table__cell) { height: 72px; }
}
</style>

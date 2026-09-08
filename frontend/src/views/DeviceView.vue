<template>
  <div class="page-card">
    <div class="toolbar">
      <el-input v-model="filters.keyword" placeholder="搜索资产编号/名称/IP/型号" style="width:240px" @keyup.enter="load" />
      <el-select v-model="filters.device_type" clearable placeholder="设备类型" style="width:140px">
        <el-option label="server" value="server" />
        <el-option label="switch" value="switch" />
        <el-option label="storage" value="storage" />
        <el-option label="pdu" value="pdu" />
        <el-option label="firewall" value="firewall" />
        <el-option label="other" value="other" />
      </el-select>
      <el-select v-model="filters.status" clearable placeholder="状态" style="width:140px">
        <el-option label="planned" value="planned" />
        <el-option label="active" value="active" />
        <el-option label="standby" value="standby" />
        <el-option label="maintenance" value="maintenance" />
        <el-option label="retired" value="retired" />
        <el-option label="off_shelf" value="off_shelf" />
      </el-select>
      <el-button @click="load">查询</el-button>
      <el-button type="primary" @click="openDialog()" :disabled="!canEdit">新增设备</el-button>
      <el-upload :show-file-list="false" :before-upload="beforeUpload" accept=".csv,.xlsx" :disabled="!canEdit">
        <el-button :disabled="!canEdit">导入CSV/XLSX</el-button>
      </el-upload>
      <el-button @click="download('/devices/export/csv', 'devices.csv')">导出CSV</el-button>
      <el-button @click="download('/devices/export/xlsx', 'devices.xlsx')">导出XLSX</el-button>
    </div>

    <div class="device-table-wrap">
    <el-table class="device-table" :data="rows" table-layout="fixed" style="min-width: 1480px">
      <el-table-column prop="asset_number" label="资产编号" width="140" show-overflow-tooltip />
      <el-table-column prop="name" label="设备名称" width="160" show-overflow-tooltip />
      <el-table-column prop="device_type" label="类型" width="100" />
      <el-table-column prop="model" label="型号" width="140" show-overflow-tooltip />
      <el-table-column prop="ip_address" label="IP" width="140" show-overflow-tooltip />
      <el-table-column label="位置" width="140">
        <template #default="scope">{{ scope.row.rack_id ? `Rack ${scope.row.rack_id} / U${scope.row.start_u}` : '未上架' }}</template>
      </el-table-column>
      <el-table-column prop="u_height" label="占用U" width="90" />
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column label="管理员" width="180" show-overflow-tooltip>
        <template #default="scope">{{ (scope.row.administrators || []).map((a:any) => a.name).join('、') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
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
          <el-col :span="12"><el-form-item label="资产编号" prop="asset_number" required><el-input v-model="form.asset_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="设备名称" prop="name" required><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="设备类型" prop="device_type" required><el-select v-model="form.device_type" style="width:100%"><el-option label="server" value="server" /><el-option label="switch" value="switch" /><el-option label="storage" value="storage" /><el-option label="pdu" value="pdu" /><el-option label="firewall" value="firewall" /><el-option label="other" value="other" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="型号" prop="model" required><el-input v-model="form.model" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="序列号"><el-input v-model="form.serial_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="用途"><el-input v-model="form.purpose" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="planned" value="planned" /><el-option label="active" value="active" /><el-option label="standby" value="standby" /><el-option label="maintenance" value="maintenance" /><el-option label="retired" value="retired" /><el-option label="off_shelf" value="off_shelf" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="IP地址"><el-input v-model="form.ip_address" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="机柜"><el-select v-model="form.rack_id" clearable style="width:100%"><el-option v-for="item in racks" :key="item.id" :label="item.code" :value="item.id" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="起始U位"><el-input-number v-model="form.start_u" :min="1" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="占用U数"><el-input-number v-model="form.u_height" :min="1" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="CPU"><el-input v-model="form.cpu" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="内存GB"><el-input-number v-model="form.memory_gb" :min="0" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="GPU"><el-input v-model="form.gpu" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="硬盘"><el-input v-model="form.storage_desc" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="操作系统"><el-input v-model="form.operating_system" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="管理员"><el-select v-model="form.administrator_ids" multiple style="width:100%"><el-option v-for="item in administrators" :key="item.id" :label="`${item.name}(${item.department})`" :value="item.id" /></el-select></el-form-item></el-col>
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
        <el-form-item label="目标机柜"><el-select v-model="moveForm.rack_id" style="width:100%"><el-option v-for="item in racks" :key="item.id" :label="item.code" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="起始U位"><el-input-number v-model="moveForm.start_u" :min="1" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="moveForm.comment" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmMove">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="设备详情" size="560px">
      <el-descriptions v-if="currentDetail" :column="2" border>
        <el-descriptions-item label="资产编号">{{ currentDetail.asset_number }}</el-descriptions-item>
        <el-descriptions-item label="名称">{{ currentDetail.name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ currentDetail.device_type }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ currentDetail.model }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentDetail.ip_address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentDetail.status }}</el-descriptions-item>
        <el-descriptions-item label="位置">{{ currentDetail.rack_id ? `Rack ${currentDetail.rack_id} / U${currentDetail.start_u}` : '未上架' }}</el-descriptions-item>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const canEdit = computed(() => auth.user?.role === 'admin')
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const visible = ref(false)
const moveVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref<any>(null)
const movingId = ref<number | null>(null)
const racks = ref<any[]>([])
const administrators = ref<any[]>([])
const filters = reactive<any>({ keyword: '', device_type: '', status: '' })
const form = reactive<any>({})
const moveForm = reactive<any>({ rack_id: undefined, start_u: 1, comment: '' })
const portsText = ref('')
const formRef = ref<any>()
const formRules = {
  asset_number: [{ required: true, message: '请输入资产编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  device_type: [{ required: true, message: '请选择设备类型', trigger: 'change' }],
  model: [{ required: true, message: '请输入型号', trigger: 'blur' }],
}

const resetForm = () => Object.assign(form, { id: undefined, asset_number: '', name: '', device_type: 'server', model: '', serial_number: '', purpose: '', status: 'planned', ip_address: '', rack_id: undefined, start_u: undefined, u_height: 1, cpu: '', memory_gb: undefined, gpu: '', storage_desc: '', operating_system: '', notes: '', administrator_ids: [] })
const parsePorts = () => portsText.value.split(',').map((x) => x.trim()).filter(Boolean).map((name) => ({ name }))
const loadAux = async () => {
  const [rackResult, adminResult] = await Promise.allSettled([
    client.get('/racks', { params: { page: 1, page_size: 100 } }),
    client.get('/administrators'),
  ])
  if (rackResult.status === 'fulfilled') racks.value = rackResult.value.data.items || []
  if (adminResult.status === 'fulfilled') administrators.value = adminResult.value.data || []
}
const load = async () => {
  const { data } = await client.get('/devices', { params: { page: page.value, page_size: pageSize, ...filters } })
  rows.value = data.items
  total.value = data.total
}
const openDialog = (row?: any) => {
  resetForm()
  portsText.value = ''
  if (row) {
    Object.assign(form, row)
    form.administrator_ids = (row.administrators || []).map((item:any) => item.id)
    portsText.value = (row.ports || []).map((p:any) => p.name).join(',')
  }
  visible.value = true
}
const save = async () => {
  try {
    await formRef.value?.validate()
    const payload = { ...form, ports: parsePorts() }
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
const download = async (url: string, filename: string) => {
  const response = await client.get(url, { responseType: 'blob' })
  const blobUrl = window.URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(blobUrl)
}

onMounted(async () => {
  await loadAux()
  resetForm()
  await load()
})
</script>

<style scoped>
.device-table-wrap{width:100%;overflow-x:auto;overflow-y:hidden}.device-table{width:100%}.device-table :deep(.el-table__fixed-right){box-shadow:-6px 0 10px rgba(15,23,42,.08)}.device-table :deep(.el-table__fixed-right::before){background:#fff}.device-table :deep(.el-table__cell){white-space:nowrap}
</style>

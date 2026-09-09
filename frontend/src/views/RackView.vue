<template>
  <div class="page-card">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索机柜编号/备注" style="width:240px" @keyup.enter="load" />
      <el-button @click="load">查询</el-button>
      <el-button type="primary" @click="openDialog()" :disabled="!canEdit">新增机柜</el-button>
    </div>
    <el-table class="rack-table" :data="rows" @row-click="showDetail" table-layout="fixed" style="width:100%">
      <el-table-column prop="code" label="机柜编号" show-overflow-tooltip />
      <el-table-column prop="data_center_id" label="机房ID" />
      <el-table-column prop="area_id" label="区域ID" />
      <el-table-column prop="row_position" label="行" />
      <el-table-column prop="column_position" label="列" />
      <el-table-column prop="orientation" label="朝向" show-overflow-tooltip>
          <template #default="scope">{{ orientationLabel(scope.row.orientation) }}</template>
        </el-table-column>
      <el-table-column prop="total_u" label="总U数" />
      <el-table-column label="状态">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="scope">
          <el-button size="small" @click.stop="showDetail(scope.row)">详情</el-button>
          <el-button size="small" @click.stop="openDialog(scope.row)" :disabled="!canEdit">编辑</el-button>
          <el-button v-if="scope.row.is_active" size="small" type="warning" plain @click.stop="deactivate(scope.row.id)" :disabled="!canEdit">停用</el-button>
          <el-button v-else size="small" type="success" plain @click.stop="activate(scope.row.id)" :disabled="!canEdit">启用</el-button>
          <el-button size="small" type="danger" link @click.stop="removeRack(scope.row)" :disabled="!canEdit">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:16px; display:flex; justify-content:flex-end">
      <el-pagination background layout="prev, pager, next, total" :total="total" v-model:current-page="page" :page-size="pageSize" @current-change="load" />
    </div>

    <el-dialog v-model="visible" :title="form.id ? '编辑机柜' : '新增机柜'" width="640px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="所属机房" required><el-select v-model="form.data_center_id" style="width:100%"><el-option v-for="item in datacenters" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="所属区域" required><el-select v-model="form.area_id" style="width:100%"><el-option v-for="item in currentAreas" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="机柜编号" required><el-input v-model="form.code" /></el-form-item>
        <el-form-item label="机柜行列">
          <el-space>
            <el-input-number v-model="form.row_position" :min="1" controls-position="right" />
            <span class="field-unit">行</span>
            <el-input-number v-model="form.column_position" :min="1" controls-position="right" />
            <span class="field-unit">列</span>
          </el-space>
          <div class="field-help">记录机柜在机房平面中的第几行、第几列，便于查找和管理。</div>
        </el-form-item>

        <el-form-item label="朝向"><el-select v-model="form.orientation" style="width:100%"><el-option label="北向 (north)" value="north" /><el-option label="南向 (south)" value="south" /><el-option label="东向 (east)" value="east" /><el-option label="西向 (west)" value="west" /></el-select></el-form-item>
        <el-form-item label="总U数"><el-input-number v-model="form.total_u" :min="1" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="机柜详情" size="520px">
      <div v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="机柜编号">{{ detail.code }}</el-descriptions-item>
          <el-descriptions-item label="设备数">{{ detail.device_count }}</el-descriptions-item>
          <el-descriptions-item label="已占用U">{{ detail.utilization.occupied_u }}</el-descriptions-item>
          <el-descriptions-item label="剩余U">{{ detail.utilization.remaining_u }}</el-descriptions-item>
          <el-descriptions-item label="利用率">{{ detail.utilization.utilization_rate }}%</el-descriptions-item>
          <el-descriptions-item label="朝向">{{ orientationLabel(detail.orientation) }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-table :data="detail.occupancy" size="small">
          <el-table-column prop="name" label="设备" />
          <el-table-column prop="asset_number" label="资产编号" />
          <el-table-column prop="start_u" label="起始U" width="80" />
          <el-table-column prop="end_u" label="结束U" width="80" />
          <el-table-column prop="u_height" label="占用U" width="80" />
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'
import { orientationLabel } from '../utils/labels'

const auth = useAuthStore()
const canEdit = computed(() => auth.user?.role === 'admin')
const keyword = ref('')
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const visible = ref(false)
const detailVisible = ref(false)
const detail = ref<any>(null)
const datacenters = ref<any[]>([])
const form = reactive<any>({})
const currentAreas = computed(() => datacenters.value.find((item) => item.id === form.data_center_id)?.areas || [])

const resetForm = () => Object.assign(form, { id: undefined, data_center_id: undefined, area_id: undefined, code: '', row_position: 1, column_position: 1, x_position: 0, y_position: 0, orientation: 'north', total_u: 42, is_active: true, remark: '' })
const loadDatacenters = async () => {
  const { data } = await client.get('/datacenters')
  datacenters.value = data
}
const load = async () => {
  const { data } = await client.get('/racks', { params: { page: page.value, page_size: pageSize, keyword: keyword.value || undefined } })
  rows.value = data.items
  total.value = data.total
}
const openDialog = (row?: any) => {
  resetForm()
  if (row) Object.assign(form, row)
  else if (datacenters.value[0]) {
    form.data_center_id = datacenters.value[0].id
    form.area_id = datacenters.value[0].areas?.[0]?.id
  }
  visible.value = true
}
const save = async () => {
  try {
    const payload = { ...form, x_position: (Number(form.column_position || 1) - 1) * 2.2, y_position: (Number(form.row_position || 1) - 1) * 4 }
    if (form.id) await client.put(`/racks/${form.id}`, payload)
    else await client.post('/racks', payload)
    ElMessage.success('保存成功')
    visible.value = false
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  }
}
const showDetail = async (row: any) => {
  const { data } = await client.get(`/racks/${row.id}`)
  detail.value = data
  detailVisible.value = true
}
const activate = async (id: number) => {
  try {
    await client.post(`/racks/${id}/activate`)
    ElMessage.success('机柜已启用')
    await load()
  } catch (error: any) { ElMessage.error(error?.response?.data?.detail || '启用失败') }
}
const removeRack = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除机柜“${row.code}”吗？机柜下的服务器和设备也会一并删除，且不可恢复。`, '删除确认', { type: 'warning' })
    await client.delete(`/racks/${row.id}`)
    ElMessage.success('机柜已删除')
    await load()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error?.response?.data?.detail || '删除失败')
  }
}
const deactivate = async (id: number) => {
  await client.post(`/racks/${id}/deactivate`)
  ElMessage.success('已停用')
  load()
}

onMounted(async () => {
  await loadDatacenters()
  resetForm()
  load()
})
</script>

<style scoped>
.field-help{width:100%;margin-top:4px;color:#64748b;font-size:12px;line-height:1.5}.field-unit{color:#64748b;font-size:12px;white-space:nowrap}
.rack-table :deep(.el-table__cell){padding:10px 8px;white-space:nowrap}.rack-table :deep(.el-table__header th){background:#f5f8fc!important;color:#475569;font-weight:600}.rack-table :deep(.el-table__fixed-right){box-shadow:-5px 0 10px rgba(15,23,42,.06);background:#fff}.rack-table :deep(.el-table__fixed-right .el-table__cell){background:#fff!important}.rack-table :deep(.el-table__row:hover>td){background:#eff6ff!important}@media(max-width:900px){.rack-table{min-width:980px}}
</style>

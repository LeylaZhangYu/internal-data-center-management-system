<template>
  <div class="page-card">
    <div class="toolbar">
      <el-button type="primary" @click="openDcDialog()" :disabled="!canEdit">新增机房</el-button>
      <el-button @click="openAreaDialog()" :disabled="!canEdit || !datacenters.length">新增区域</el-button>
    </div>
    <el-table :data="datacenters" row-key="id" default-expand-all>
      <el-table-column type="expand">
        <template #default="scope">
          <el-table :data="scope.row.areas || []" size="small">
            <el-table-column prop="name" label="区域" />
            <el-table-column prop="row_count" label="行数" width="100" />
            <el-table-column prop="column_count" label="列数" width="100" />
            <el-table-column prop="description" label="说明" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="areaScope">
                <el-button size="small" @click="openAreaDialog(areaScope.row, scope.row.id)" :disabled="!canEdit">编辑</el-button>
                <el-button size="small" type="danger" link @click="removeArea(areaScope.row)" :disabled="!canEdit">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="机房名称" />
      <el-table-column prop="location" label="位置" />
      <el-table-column prop="owner" label="负责人" />
      <el-table-column prop="contact" label="联系信息" />
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="scope">
          <el-button size="small" @click="openDcDialog(scope.row)" :disabled="!canEdit">编辑</el-button>
          <el-button size="small" type="danger" plain @click="deactivate(scope.row.id)" :disabled="!isAdmin">停用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dcVisible" :title="dcForm.id ? '编辑机房' : '新增机房'" width="560px">
      <el-form :model="dcForm" label-width="90px">
        <el-form-item label="名称" required><el-input v-model="dcForm.name" /></el-form-item>
        <el-form-item label="位置" required><el-input v-model="dcForm.location" /></el-form-item>
        <el-form-item label="负责人" required><el-input v-model="dcForm.owner" /></el-form-item>
        <el-form-item label="联系方式"><el-input v-model="dcForm.contact" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="dcForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dcVisible = false">取消</el-button>
        <el-button type="primary" @click="saveDc">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="areaVisible" :title="areaForm.id ? '编辑区域' : '新增区域'" width="560px">
      <el-form :model="areaForm" label-width="90px">
        <el-form-item label="所属机房" required>
          <el-select v-model="areaForm.data_center_id" style="width:100%">
            <el-option v-for="item in datacenters" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域名称" required><el-input v-model="areaForm.name" /></el-form-item>
        <el-form-item label="行数"><el-input-number v-model="areaForm.row_count" :min="1" /></el-form-item>
        <el-form-item label="列数"><el-input-number v-model="areaForm.column_count" :min="1" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="areaForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="areaVisible = false">取消</el-button>
        <el-button type="primary" @click="saveArea">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const canEdit = computed(() => auth.user?.role === 'admin')
const isAdmin = computed(() => auth.user?.role === 'admin')
const datacenters = ref<any[]>([])
const dcVisible = ref(false)
const areaVisible = ref(false)
const dcForm = reactive<any>({})
const areaForm = reactive<any>({ data_center_id: undefined, name: '', row_count: 1, column_count: 1, description: '' })

const resetDc = () => Object.assign(dcForm, { id: undefined, name: '', location: '', owner: '', contact: '', description: '', is_active: true })
const openDcDialog = (row?: any) => {
  resetDc()
  if (row) Object.assign(dcForm, row)
  dcVisible.value = true
}
const openAreaDialog = (row?: any, dataCenterId?: number) => {
  Object.assign(areaForm, { id: undefined, data_center_id: dataCenterId || datacenters.value[0]?.id, name: '', row_count: 1, column_count: 1, description: '' })
  if (row) Object.assign(areaForm, row)
  areaVisible.value = true
}
const load = async () => {
  const { data } = await client.get('/datacenters')
  datacenters.value = data
}
const saveDc = async () => {
  try {
    if (dcForm.id) await client.put(`/datacenters/${dcForm.id}`, dcForm)
    else await client.post('/datacenters', dcForm)
    ElMessage.success('保存成功')
    dcVisible.value = false
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  }
}
const saveArea = async () => {
  try {
    if (!areaForm.data_center_id) {
      ElMessage.warning('请选择所属机房')
      return
    }
    const { id, data_center_id, ...payload } = areaForm
    if (id) await client.put(`/datacenters/areas/${id}`, payload)
    else await client.post(`/datacenters/${data_center_id}/areas`, payload)
    ElMessage.success(id ? '区域已更新' : '区域已新增')
    areaVisible.value = false
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '操作失败')
  }
}
const removeArea = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除区域“${row.name}”吗？删除后不可恢复。`, '删除确认', { type: 'warning' })
    await client.delete(`/datacenters/areas/${row.id}`)
    ElMessage.success('区域已删除')
    await load()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error?.response?.data?.detail || '删除失败')
  }
}
const deactivate = async (id: number) => {
  await client.post(`/datacenters/${id}/deactivate`)
  ElMessage.success('已停用')
  load()
}

onMounted(load)
</script>

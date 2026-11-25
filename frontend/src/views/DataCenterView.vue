<template>
  <div class="page-card">
    <div class="toolbar">
      <el-button type="primary" @click="openDcDialog()" :disabled="!canEdit">新增机房</el-button>
      <el-button @click="openAreaDialog()" :disabled="!canEdit || !datacenters.length">新增区域</el-button>
    </div>
    <p class="id-help">机房ID、区域ID为系统生成的固定编号，与机柜管理及 Excel 导入模板中的对应字段一致。</p>
    <el-table class="datacenter-table" :data="datacenters" row-key="id" default-expand-all table-layout="fixed">
      <el-table-column type="expand">
        <template #default="scope">
          <section class="area-section" :aria-label="`${scope.row.name}的区域`">
            <header class="area-section-header">
              <div class="area-section-heading"><el-icon><Grid /></el-icon><h3>所属区域</h3><span class="area-count">{{ (scope.row.areas || []).length }}</span></div>
              <el-button text type="primary" size="small" :disabled="!canEdit" @click="openAreaDialog(undefined, scope.row.id)"><el-icon><Plus /></el-icon><span>添加区域</span></el-button>
            </header>
            <ul v-if="scope.row.areas?.length" class="area-list">
              <li v-for="area in scope.row.areas" :key="area.id" class="area-item">
                <div class="area-identity"><span class="area-symbol" aria-hidden="true"><el-icon><Grid /></el-icon></span><div><strong>{{ area.name }}</strong><small>区域ID：{{ area.id }}</small></div></div>
                <div class="area-dimensions" :aria-label="`${area.row_count}行${area.column_count}列`"><span><b>{{ area.row_count }}</b> 行</span><i aria-hidden="true">×</i><span><b>{{ area.column_count }}</b> 列</span></div>
                <p class="area-description" :class="{ 'is-empty': !area.description }" :title="area.description || undefined">{{ area.description || '暂无说明' }}</p>
                <div class="area-actions" :aria-label="`${area.name}的操作`"><el-button size="small" text :disabled="!canEdit" :aria-label="`编辑区域${area.name}`" @click="openAreaDialog(area, scope.row.id)">编辑</el-button><span aria-hidden="true"></span><el-button size="small" text type="danger" :disabled="!canEdit" :aria-label="`删除区域${area.name}`" @click="removeArea(area)">删除</el-button></div>
              </li>
            </ul>
            <div v-else class="area-empty"><span class="area-symbol" aria-hidden="true"><el-icon><Grid /></el-icon></span><div><strong>还没有区域</strong><p>为当前机房添加区域，方便组织机柜布局。</p></div></div>
          </section>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="机房ID" width="100" />
      <el-table-column prop="name" label="机房名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="location" label="位置" min-width="220" show-overflow-tooltip />
      <el-table-column prop="owner" label="负责人" min-width="140" />
      <el-table-column prop="contact" label="联系信息" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="scope">
          <el-button size="small" @click="openDcDialog(scope.row)" :disabled="!canEdit">编辑</el-button>
          <el-button v-if="scope.row.is_active" size="small" type="warning" plain @click="deactivate(scope.row.id)" :disabled="!isAdmin">停用</el-button>
          <el-button v-else size="small" type="success" plain @click="activate(scope.row.id)" :disabled="!isAdmin">启用</el-button>
          <el-button size="small" type="danger" link @click="removeDc(scope.row)" :disabled="!isAdmin">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dcVisible" :title="dcForm.id ? '编辑机房' : '新增机房'" width="560px">
      <el-form :model="dcForm" label-width="90px">
        <el-form-item v-if="dcForm.id" label="机房ID"><span>{{ dcForm.id }}</span></el-form-item>
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
        <el-form-item v-if="areaForm.id" label="区域ID"><span>{{ areaForm.id }}</span></el-form-item>
        <el-form-item label="所属机房" required>
          <el-select v-model="areaForm.data_center_id" style="width:100%">
            <el-option v-for="item in datacenters" :key="item.id" :label="`${item.name}（机房ID：${item.id}）`" :value="item.id" />
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
import { Grid, Plus } from '@element-plus/icons-vue'
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
const activate = async (id: number) => {
  try {
    await client.post(`/datacenters/${id}/activate`)
    ElMessage.success('机房已启用')
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '启用失败')
  }
}
const removeDc = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除机房“${row.name}”吗？该机房下的区域、机柜和设备也会一并删除，且不可恢复。`, '删除确认', { type: 'warning' })
    await client.delete(`/datacenters/${row.id}`)
    ElMessage.success('机房已删除')
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

<style scoped src="../styles/datacenters.css"></style>

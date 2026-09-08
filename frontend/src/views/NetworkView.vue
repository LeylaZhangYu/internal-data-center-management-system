<template>
  <div style="display:flex; flex-direction:column; gap:16px">
    <div class="page-card">
      <div class="toolbar">
        <el-button type="primary" @click="openDialog()" :disabled="!canEdit">新增链路</el-button>
      </div>
      <el-table :data="links">
        <el-table-column prop="local_device_name" label="本端设备" />
        <el-table-column prop="local_port_name" label="本端端口" />
        <el-table-column prop="remote_device_name" label="对端设备" />
        <el-table-column prop="remote_port_name" label="对端端口" />
        <el-table-column prop="bandwidth" label="带宽" width="100" />
        <el-table-column prop="vlan" label="VLAN" width="100" />
        <el-table-column prop="status" label="状态" width="190" show-overflow-tooltip>
          <template #default="scope">{{ linkStatusLabel(scope.row.status) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="openDialog(scope.row)" :disabled="!canEdit">编辑</el-button>
            <el-button size="small" type="danger" plain @click="remove(scope.row.id)" :disabled="!canEdit">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="page-card">
      <h3 style="margin-top:0">简单拓扑视图</h3>
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px;">
        <div v-for="node in topology.nodes" :key="node.id" style="padding: 12px; border: 1px solid #dcdfe6; border-radius: 8px; background:#fafafa">
          <div style="font-weight:600; white-space:pre-line">{{ node.label }}</div>
          <el-tag size="small">{{ node.type }}</el-tag>
        </div>
      </div>
      <el-table :data="topology.edges" size="small">
        <el-table-column prop="source" label="源" />
        <el-table-column prop="target" label="目标" />
        <el-table-column prop="label" label="链路信息" />
        <el-table-column prop="status" label="状态" width="190" show-overflow-tooltip>
          <template #default="scope">{{ linkStatusLabel(scope.row.status) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="visible" :title="form.id ? '编辑链路' : '新增链路'" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="本端端口" required>
          <el-select v-model="form.local_port_id" filterable style="width:100%">
            <el-option v-for="item in ports" :key="item.id" :label="`${item.device_name} / ${item.name}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="对端端口" required>
          <el-select v-model="form.remote_port_id" filterable style="width:100%">
            <el-option v-for="item in ports" :key="item.id" :label="`${item.device_name} / ${item.name}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="带宽"><el-input v-model="form.bandwidth" /></el-form-item>
        <el-form-item label="VLAN"><el-input v-model="form.vlan" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="正常 (up)" value="up" /><el-option label="断开 (down)" value="down" /><el-option label="计划中 (planned)" value="planned" /></el-select></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'
import { linkStatusLabel } from '../utils/labels'

const auth = useAuthStore()
const canEdit = computed(() => auth.user?.role === 'admin')
const links = ref<any[]>([])
const ports = ref<any[]>([])
const topology = reactive<any>({ nodes: [], edges: [] })
const visible = ref(false)
const form = reactive<any>({})
const resetForm = () => Object.assign(form, { id: undefined, local_port_id: undefined, remote_port_id: undefined, bandwidth: '', vlan: '', status: 'up', description: '' })
const load = async () => {
  const [linkRes, portRes, topologyRes] = await Promise.all([client.get('/network/links'), client.get('/network/ports'), client.get('/network/topology')])
  links.value = linkRes.data
  ports.value = portRes.data
  Object.assign(topology, topologyRes.data)
}
const openDialog = (row?: any) => {
  resetForm()
  if (row) Object.assign(form, row)
  visible.value = true
}
const save = async () => {
  try {
    if (form.id) await client.put(`/network/links/${form.id}`, form)
    else await client.post('/network/links', form)
    ElMessage.success('保存成功')
    visible.value = false
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  }
}
const remove = async (id: number) => {
  await client.delete(`/network/links/${id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(() => {
  resetForm()
  load()
})
</script>

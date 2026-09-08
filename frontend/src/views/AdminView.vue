<template>
  <div class="page-card">
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()" :disabled="!canEdit">新增管理员</el-button>
    </div>
    <el-table :data="rows">
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="department" label="部门" />
      <el-table-column prop="phone" label="电话" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column label="状态" width="100"><template #default="scope"><el-tag>{{ scope.row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="120"><template #default="scope"><el-button size="small" @click="openDialog(scope.row)" :disabled="!canEdit">编辑</el-button></template></el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑管理员' : '新增管理员'" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="姓名" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="部门" required><el-input v-model="form.department" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
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

const auth = useAuthStore()
const canEdit = computed(() => auth.user?.role === 'admin')
const rows = ref<any[]>([])
const visible = ref(false)
const form = reactive<any>({})
const resetForm = () => Object.assign(form, { id: undefined, name: '', department: '', phone: '', email: '', is_active: true })
const load = async () => {
  const { data } = await client.get('/administrators')
  rows.value = data
}
const openDialog = (row?: any) => {
  resetForm()
  if (row) Object.assign(form, row)
  visible.value = true
}
const save = async () => {
  try {
    if (form.id) await client.put(`/administrators/${form.id}`, form)
    else await client.post('/administrators', form)
    ElMessage.success('保存成功')
    visible.value = false
    load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  }
}

onMounted(() => {
  resetForm()
  load()
})
</script>

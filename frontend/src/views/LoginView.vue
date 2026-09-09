<template>
  <div style="min-height:100vh; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#e0ecff,#f5f7fa)">
    <el-card style="width: 420px">
      <template #header>
        <div style="font-size:20px; font-weight:700">机房管理系统登录</div>
      </template>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" style="width:100%" @click="submit" :loading="loading">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const submit = async () => {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/dashboard')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

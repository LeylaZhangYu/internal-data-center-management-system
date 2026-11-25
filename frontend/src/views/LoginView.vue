<template>
  <div class="login-page">
    <section class="login-story" aria-label="平台介绍">
      <div class="login-brand"><span class="brand-mark"><el-icon><Cpu /></el-icon></span><strong>机房管理<span>DATA CENTER</span></strong></div>
      <div class="login-story-copy"><span class="login-kicker">INFRASTRUCTURE, ORGANIZED.</span><h1>看清每一处空间，<br />管理每一份资产。</h1><p>连接机房、机柜与设备，<br />让基础设施管理更清晰、更从容。</p></div>
      <div class="login-racks" aria-hidden="true"><div v-for="rack in 3" :key="rack" class="login-rack"><span v-for="slot in 6" :key="slot"><i /><b /></span></div><div class="rack-floor" /></div>
      <div class="login-story-footer"><span>空间管理 / 设备资产 / 网络连接</span><span>DC — 01</span></div>
    </section>
    <section class="login-entry">
      <div class="login-form-wrap"><span class="login-kicker">WELCOME BACK</span><h2>登录工作空间</h2><p class="login-subtitle">使用管理员账号访问数据中心管理平台。</p>
        <el-form :model="form" label-position="top" size="large" @submit.prevent="submit">
          <el-form-item label="用户名" required><el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" /></el-form-item>
          <el-form-item label="密码" required><el-input v-model="form.password" placeholder="请输入密码" type="password" show-password autocomplete="current-password" /></el-form-item>
          <el-button class="login-submit" type="primary" native-type="submit" :loading="loading">登录 <span aria-hidden="true">→</span></el-button>
        </el-form>
        <p class="login-note"><el-icon><Lock /></el-icon>仅限已授权人员访问</p>
      </div>
      <div class="login-entry-footer">数据中心 · 基础设施管理平台</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, Lock } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const submit = async () => {
  if (loading.value) return
  if (!form.username.trim() || !form.password) { ElMessage.warning('请输入用户名和密码'); return }
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

<template>
  <el-container class="app-shell">
    <el-aside width="220px" class="app-aside">
      <div class="brand"><span class="brand-dot"></span><div><strong>机房管理</strong><small>DATA CENTER OS</small></div></div>
      <el-menu
        router
        background-color="transparent"
        text-color="#d9d9d9"
        active-text-color="#fff"
        :default-active="$route.path"
      >
        <el-menu-item index="/dashboard">首页概览</el-menu-item>
        <el-menu-item index="/datacenters">机房与区域</el-menu-item>
        <el-menu-item index="/racks">机柜管理</el-menu-item>
        <el-menu-item index="/devices">设备管理</el-menu-item>
        <el-menu-item index="/administrators">管理员</el-menu-item>
        <el-menu-item index="/network">网络上联</el-menu-item>
        <el-menu-item index="/visualization">3D可视化</el-menu-item>
        <el-menu-item index="/logs">操作日志</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div class="header-title"><span>控制台</span><small>部门内部数据中心管理系统</small></div>
        <div style="display:flex; align-items:center; gap:16px">
          <el-tag>{{ auth.user?.full_name }} / {{ auth.user?.role }}</el-tag>
          <el-button type="danger" plain @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const logout = () => {
  auth.logout()
  router.push('/login')
}
</script>

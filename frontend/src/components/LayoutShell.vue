<template>
  <el-container class="app-shell" :class="{ 'nav-compact': compact }">
    <aside class="app-aside" aria-label="主导航">
      <router-link to="/dashboard" class="brand"><span class="brand-mark"><el-icon><Cpu /></el-icon></span><span class="brand-copy"><strong>机房管理</strong><small>DATA CENTER</small></span></router-link>
      <nav class="app-navigation">
        <section v-for="group in navigation" :key="group.label" class="nav-group">
          <div class="nav-group-label">{{ group.label }}</div>
          <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="nav-link" :class="{ active: route.path === item.path }" :aria-current="route.path === item.path ? 'page' : undefined" :title="item.title">
            <el-icon><component :is="item.icon" /></el-icon><span>{{ item.title }}</span><i v-if="route.path === item.path" class="nav-indicator" />
          </router-link>
        </section>
      </nav>
      <div class="sidebar-foot"><span class="sidebar-foot-mark">DC</span><span>基础设施管理平台<small>空间 · 资产 · 连接</small></span></div>
    </aside>
    <el-container class="app-workspace">
      <el-header class="app-header">
        <div class="header-location"><el-button text circle :aria-label="compact ? '展开导航' : '收起导航'" :aria-expanded="!compact" @click="compact = !compact"><el-icon><Expand v-if="compact" /><Fold v-else /></el-icon></el-button><span class="header-product">工作空间</span><span class="breadcrumb-divider">/</span><strong>{{ current.title }}</strong></div>
        <div class="header-user"><span class="user-avatar">{{ (auth.user?.full_name || 'A').slice(0, 1) }}</span><span class="user-copy"><strong>{{ auth.user?.full_name || '管理员' }}</strong><small>{{ roleLabel(auth.user?.role) }}</small></span><el-button text class="logout-button" @click="logout">退出登录</el-button></div>
      </el-header>
      <el-main class="app-main">
        <div v-if="!isScene" class="page-heading"><div><span class="page-eyebrow">{{ current.english }}</span><h1>{{ current.title }}</h1><p>{{ current.description }}</p></div><span class="page-heading-mark" aria-hidden="true"><el-icon><component :is="current.icon" /></el-icon></span></div>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Odometer, OfficeBuilding, Coin, Monitor, Connection, Share, Box, User, Document, Cpu, Expand, Fold } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { roleLabel } from '../utils/labels'

const auth = useAuthStore(), router = useRouter(), route = useRoute()
const compact = ref(false)
const navigation = [
  { label: '工作台', items: [
    { path: '/dashboard', title: '首页概览', english: 'OVERVIEW', description: '从空间容量到设备状态，了解数据中心的整体情况。', icon: Odometer },
  ] },
  { label: '基础设施', items: [
    { path: '/datacenters', title: '机房与区域', english: 'SPACES', description: '组织机房与区域，让每一处空间清晰有序。', icon: OfficeBuilding },
    { path: '/racks', title: '机柜管理', english: 'RACKS', description: '管理机柜布局、使用状态与 U 位容量。', icon: Coin },
    { path: '/devices', title: '设备管理', english: 'DEVICES', description: '统一维护设备资产、安装位置与责任人信息。', icon: Monitor },
    { path: '/network', title: '网络上联', english: 'CONNECTIONS', description: '维护设备端口及链路，梳理网络连接关系。', icon: Connection },
  ] },
  { label: '空间可视化', items: [
    { path: '/network-topology', title: '3D网络拓扑', english: 'TOPOLOGY', description: '', icon: Share },
    { path: '/visualization', title: '3D可视化', english: 'DIGITAL SPACE', description: '', icon: Box },
  ] },
  { label: '管理', items: [
    { path: '/administrators', title: '服务器管理员', english: 'PEOPLE', description: '维护设备责任人及联系信息，明确管理归属。', icon: User },
    { path: '/logs', title: '操作日志', english: 'ACTIVITY', description: '查看平台操作记录，追溯关键数据变更。', icon: Document },
  ] },
]
const current = computed(() => navigation.flatMap(group => group.items).find(item => item.path === route.path) || navigation[0].items[0])
const isScene = computed(() => ['/visualization', '/network-topology'].includes(route.path))
const logout = () => { auth.logout(); router.push('/login') }
</script>

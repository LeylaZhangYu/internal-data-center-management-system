import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LayoutShell from '../components/LayoutShell.vue'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import DataCenterView from '../views/DataCenterView.vue'
import RackView from '../views/RackView.vue'
import DeviceView from '../views/DeviceView.vue'
import AdminView from '../views/AdminView.vue'
import NetworkView from '../views/NetworkView.vue'
import VisualizationView from '../views/VisualizationView.vue'
import LogsView from '../views/LogsView.vue'

const routes: RouteRecordRaw[] = [
  { path: '/login', component: LoginView },
  {
    path: '/',
    component: LayoutShell,
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: DashboardView },
      { path: 'datacenters', component: DataCenterView },
      { path: 'racks', component: RackView },
      { path: 'devices', component: DeviceView },
      { path: 'administrators', component: AdminView },
      { path: 'network', component: NetworkView },
      { path: 'visualization', component: VisualizationView },
      { path: 'logs', component: LogsView },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLoggedIn) {
    return '/login'
  }
  if (to.path === '/login' && auth.isLoggedIn) {
    return '/dashboard'
  }
})

export default router

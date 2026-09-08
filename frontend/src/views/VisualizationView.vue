<template>
  <div class="visualization-page">
    <section class="page-card scene-card">
      <div class="scene-toolbar">
        <span>选择机房</span>
        <el-select v-model="selectedDcId" size="small" placeholder="请选择机房" @change="renderSelectedDc" style="width:200px">
          <el-option v-for="dc in layoutData" :key="dc.id" :label="dc.name" :value="dc.id" />
        </el-select>
      </div>
      <div ref="canvasRef" class="scene-canvas"></div>
      <div class="scene-caption"><strong>3D 机柜视图</strong><span>旋转 / 缩放 / 平移 · 点击机柜或服务器查看详情</span></div>
      <div class="scene-legend"><i class="legend-server" />服务器 <i class="legend-rack" />机柜</div>
    </section>
    <aside class="page-card rack-inspector">
      <div class="inspector-title"><div><span>RACK INSPECTOR</span><h3>{{ selectedRack?.code || '请选择机柜' }}</h3></div><el-tag v-if="selectedRack" type="success">在线查看</el-tag></div>
      <template v-if="selectedRack">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="利用率">{{ selectedRack.utilization_rate }}%</el-descriptions-item>
          <el-descriptions-item label="设备数量">{{ selectedRack.device_count }}</el-descriptions-item>
          <el-descriptions-item label="总U数">{{ selectedRack.total_u }}U</el-descriptions-item>
          <el-descriptions-item label="方向">{{ orientationLabel(selectedRack.orientation) }}</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">设备清单</el-divider>
        <div v-if="selectedRack.devices?.length" class="device-list">
          <article v-for="item in selectedRack.devices" :key="item.id" class="device-item">
            <div class="device-head"><strong>{{ item.name }}</strong><el-tag size="small" effect="plain">U{{ item.start_u }}–{{ item.start_u + item.u_height - 1 }}</el-tag></div>
            <div class="device-meta">{{ item.asset_number }} · {{ item.model }}</div>
            <div class="device-meta">IP：{{ item.ip_address || '-' }}　状态：{{ deviceStatusLabel(item.status) }}</div>
            <div class="device-meta">管理员：{{ item.administrators?.join('、') || '-' }}</div>
            <div v-if="item.links?.length" class="device-links">上联：{{ item.links.join('；') }}</div>
          </article>
        </div>
        <el-empty v-else description="该机柜暂无已上架设备" :image-size="64" />
      </template>
      <el-empty v-else description="请在左侧点击机柜或服务器" :image-size="90" />
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import client from '../api/client'
import { deviceStatusLabel, orientationLabel } from '../utils/labels'

const canvasRef = ref<HTMLDivElement | null>(null)
const selectedRack = ref<any>(null)
const layoutData = ref<any[]>([])
const selectedDcId = ref<number | undefined>()
let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer, controls: OrbitControls, raycaster: THREE.Raycaster, animationFrame = 0
const mouse = new THREE.Vector2(), clickable: THREE.Object3D[] = []

const initScene = (data: any[]) => {
  if (renderer) { cancelAnimationFrame(animationFrame); controls?.dispose(); renderer.dispose() }
  clickable.length = 0

  if (!canvasRef.value) return
  scene = new THREE.Scene(); scene.background = new THREE.Color('#eef3f8')
  camera = new THREE.PerspectiveCamera(55, canvasRef.value.clientWidth / canvasRef.value.clientHeight, .1, 1000); camera.position.set(10, 9, 14)
  renderer = new THREE.WebGLRenderer({ antialias: true }); renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight)
  canvasRef.value.innerHTML = ''; canvasRef.value.appendChild(renderer.domElement)
  controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; raycaster = new THREE.Raycaster()
  scene.add(new THREE.HemisphereLight(0xffffff, 0x9fb1c5, 2), new THREE.DirectionalLight(0xffffff, 1.2))
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshStandardMaterial({ color: '#dbe5ef', side: THREE.DoubleSide })); floor.rotation.x = -Math.PI / 2; scene.add(floor)

  data.flatMap(dc => dc.areas).flatMap((area: any) => area.racks).forEach((rack: any) => {
    const group = new THREE.Group(); group.position.set(rack.x_position, 0, rack.y_position); group.userData = rack
    const shellGeometry = new THREE.BoxGeometry(1.5, 4.7, 1.25)
    const shell = new THREE.Mesh(shellGeometry, new THREE.MeshPhysicalMaterial({ color: '#78a9cf', transparent: true, opacity: .16, roughness: .2, metalness: .15, transmission: .12, depthWrite: false, side: THREE.DoubleSide }))
    shell.position.y = 2.35; shell.userData = rack; group.add(shell); clickable.push(shell)
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(shellGeometry), new THREE.LineBasicMaterial({ color: '#4d789b', transparent: true, opacity: .75 }))
    edges.position.y = 2.35; edges.userData = rack; group.add(edges); clickable.push(edges)
    const topLight = new THREE.Mesh(new THREE.BoxGeometry(1.18, .035, .9), new THREE.MeshBasicMaterial({ color: '#b9dcf2', transparent: true, opacity: .28 }))
    topLight.position.set(0, 4.7, 0); topLight.userData = rack; group.add(topLight); clickable.push(topLight)
    rack.devices?.forEach((device: any) => {
      const height = Math.max(.22, device.u_height * .095), y = (device.start_u - 1) * .095 + height / 2 + .12
      const server = new THREE.Mesh(new THREE.BoxGeometry(1.28, height, 1.02), new THREE.MeshStandardMaterial({ color: device.status === 'active' ? '#2779bd' : '#8a9caf', metalness: .35, roughness: .4 }))
      server.position.set(0, y, -.08); server.userData = rack; group.add(server); clickable.push(server)
      const face = new THREE.Mesh(new THREE.BoxGeometry(1.08, Math.max(.12, height * .55), .025), new THREE.MeshStandardMaterial({ color: '#5eb3e8', metalness: .2, roughness: .3 }))
      face.position.set(0, y, -.6); face.userData = rack; group.add(face); clickable.push(face)
      for (let i = 0; i < 3; i++) { const light = new THREE.Mesh(new THREE.SphereGeometry(.025, 8, 8), new THREE.MeshBasicMaterial({ color: i === 0 ? '#57d68d' : '#9cc7df' })); light.position.set(-.48 + i * .12, y, -.625); light.userData = rack; group.add(light) }
    })
    scene.add(group)
  })

  const animate = () => { controls.update(); renderer.render(scene, camera); animationFrame = requestAnimationFrame(animate) }; animate()
  renderer.domElement.onclick = (event) => { const rect = renderer.domElement.getBoundingClientRect(); mouse.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1); raycaster.setFromCamera(mouse, camera); const hit = raycaster.intersectObjects(clickable, true)[0]; if (hit) selectedRack.value = hit.object.userData }
}
const load = async () => {
  const { data } = await client.get('/visualization/layout')
  layoutData.value = data
  selectedDcId.value = data[0]?.id
  initScene(data.filter((dc: any) => dc.id === selectedDcId.value))
}
const renderSelectedDc = () => {
  selectedRack.value = null
  initScene(layoutData.value.filter((dc: any) => dc.id === selectedDcId.value))
}
onMounted(load)
onBeforeUnmount(() => { cancelAnimationFrame(animationFrame); renderer?.dispose(); controls?.dispose() })
</script>

<style scoped>
.visualization-page{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(320px,.8fr);gap:16px;height:calc(100vh - 140px)}.scene-card{padding:0;overflow:hidden;position:relative}.scene-canvas{width:100%;height:100%}.scene-toolbar{position:absolute;right:16px;top:16px;z-index:2;display:flex;align-items:center;gap:8px;padding:8px 10px;background:rgba(255,255,255,.94);border:1px solid #dbe5ef;border-radius:8px;color:#475569;font-size:12px}.scene-caption{position:absolute;left:16px;top:16px;display:flex;flex-direction:column;gap:4px;padding:11px 14px;background:rgba(255,255,255,.92);border:1px solid #dbe5ef;border-radius:8px;color:#1e3a5f}.scene-caption span{font-size:12px;color:#64748b}.scene-legend{position:absolute;right:16px;bottom:16px;padding:8px 10px;background:rgba(255,255,255,.9);border:1px solid #dbe5ef;border-radius:6px;color:#475569;font-size:12px}.scene-legend i{display:inline-block;width:10px;height:10px;margin:0 5px 0 10px;border-radius:2px}.legend-server{background:#2779bd}.legend-rack{background:#3e5d79}.rack-inspector{overflow:auto}.inspector-title{display:flex;justify-content:space-between;align-items:flex-start}.inspector-title span{font-size:10px;color:#7890a8;letter-spacing:.14em}.inspector-title h3{margin:5px 0 16px;color:#1e3a5f}.device-list{display:flex;flex-direction:column;gap:10px}.device-item{padding:11px;border:1px solid #e1eaf2;border-radius:8px;background:#f8fbfe}.device-head{display:flex;justify-content:space-between;gap:8px;align-items:center;color:#1e3a5f}.device-meta,.device-links{margin-top:5px;color:#64748b;font-size:12px;line-height:1.45}.device-links{color:#2563eb}@media(max-width:900px){.visualization-page{grid-template-columns:1fr;height:auto}.scene-card{height:520px}.rack-inspector{min-height:300px}}
</style>

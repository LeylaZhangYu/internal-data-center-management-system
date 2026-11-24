<template>
  <div ref="host" class="rack-canvas" role="img" aria-label="三维机柜布局，可通过左侧列表选择机柜查看设备">
    <div v-if="renderError" class="render-error" role="alert"><strong>3D 场景暂时不可用</strong><p>{{ renderError }}</p><span>仍可通过左侧机柜列表查看设备详情。</span></div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { placeAreas, rackHeight, devicePlacement, isMounted, unitHeight, statusColors, type AreaLayout } from './layout'

const props = defineProps<{ areas: AreaLayout[]; selectedRack: number | null; selectedDevice: number | null; labels: boolean; grid: boolean; transparent: boolean; rotate: boolean }>()
const emit = defineEmits<{ (event: 'select', rackId: number | null, deviceId: number | null): void }>()
const host = ref<HTMLDivElement>()
const renderError = ref('')
let renderer: THREE.WebGLRenderer, camera: THREE.PerspectiveCamera, scene: THREE.Scene, controls: OrbitControls
let content: THREE.Group, grid: THREE.GridHelper, observer: ResizeObserver, frame = 0, ready = false
let sceneBox = new THREE.Box3(), pointerStart = { x: 0, y: 0 }, lastAspect = 1
const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2()
const clickable: THREE.Object3D[] = []
const racks = new Map<number, { group: THREE.Group; shell: THREE.Mesh; outline: THREE.LineSegments; selection: THREE.LineSegments; label: THREE.Sprite; height: number }>()
const devices = new Map<number, THREE.Mesh>()
const labels: THREE.Sprite[] = []

function release(group?: THREE.Object3D) {
  group?.traverse((object: any) => {
    object.geometry?.dispose()
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach(material => { material?.map?.dispose(); material?.dispose() })
  })
  if (group) scene.remove(group)
}
function sprite(text: string, color: string, width: number, height: number) {
  const canvas = document.createElement('canvas'); canvas.width = 768; canvas.height = 128
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = 'rgba(9,20,38,.94)'; ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = color; ctx.fillRect(0, 0, 6, 128)
  ctx.font = '500 46px "PingFang SC", "Microsoft YaHei", sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillText(text, 384, 64, 730)
  const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace
  const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthWrite: false, transparent: true }))
  label.scale.set(width, height, 1); return label
}
function box(width: number, height: number, depth: number, color: string, basic = false) {
  return new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), basic ? new THREE.MeshBasicMaterial({ color }) : new THREE.MeshStandardMaterial({ color, metalness: .48, roughness: .4 }))
}
function outline(width: number, height: number, depth: number, color: string, opacity: number) {
  const source = new THREE.BoxGeometry(width, height, depth)
  const geometry = new THREE.EdgesGeometry(source); source.dispose()
  return new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({ color, transparent: true, opacity }))
}
function rebuild() {
  if (!ready) return
  release(content); release(grid); content = new THREE.Group(); scene.add(content)
  racks.clear(); devices.clear(); clickable.length = 0; labels.length = 0
  for (const placement of placeAreas(props.areas)) {
    const { area, width, depth, centerX, offsetX, offsetZ, color } = placement
    const platform = box(width, .12, depth, '#102239'); platform.position.set(centerX, -.14, 0); content.add(platform)
    const border = outline(width, .12, depth, color, .45); border.position.copy(platform.position); content.add(border)
    const areaLabel = sprite(`${area.name}  /  ${area.racks.length} RACKS`, color, Math.min(width - .6, 5), .55)
    areaLabel.position.set(centerX, .1, -depth / 2 - .35); content.add(areaLabel); labels.push(areaLabel)
    area.racks.forEach(rack => {
      const group = new THREE.Group(), height = rackHeight(rack)
      group.position.set(rack.x_position + offsetX, 0, rack.y_position + offsetZ)
      group.rotation.y = ({ north: 0, south: Math.PI, east: -Math.PI / 2, west: Math.PI / 2 } as Record<string, number>)[rack.orientation] || 0
      const shell = new THREE.Mesh(new THREE.BoxGeometry(1.5, height, 1.4), new THREE.MeshStandardMaterial({ color: '#3c6488', transparent: true, opacity: .12, depthWrite: false, side: THREE.DoubleSide, metalness: .3, roughness: .32 }))
      shell.position.y = height / 2; shell.userData = { rackId: rack.id }; clickable.push(shell); group.add(shell)
      const edges = outline(1.5, height, 1.4, color, .52); edges.position.y = height / 2; group.add(edges)
      const selection = outline(1.8, .06, 1.7, '#95f5e4', 1); selection.position.y = -.015; selection.visible = false; group.add(selection)
      for (const x of [-.7, .7]) for (const z of [-.65, .65]) { const rail = box(.055, height, .055, '#36536e'); rail.position.set(x, height / 2, z); group.add(rail) }
      for (const y of [.08, height - .08]) { const cap = box(1.48, .16, 1.38, '#1b334d'); cap.position.y = y; group.add(cap) }
      const strip = box(1.2, .026, .035, color, true); strip.position.set(0, height - .15, -.71); group.add(strip)
      // Physical U scale: an individual 1U server keeps its correct height, even in a tall rack.
      for (let u = 0; u <= rack.total_u; u++) { const tick = box(u % 5 === 0 ? .1 : .05, .008, .015, '#728ba8', true); tick.position.set(-.64, .22 + u * unitHeight, -.715); group.add(tick) }
      rack.devices.filter(isMounted).forEach(device => {
        const position = devicePlacement(device), statusColor = statusColors[device.status] || '#8391a9'
        const server = box(1.25, position.height, 1.15, '#2b465f'); server.position.set(0, position.y, 0); server.userData = { rackId: rack.id, deviceId: device.id }; group.add(server); clickable.push(server); devices.set(device.id, server)
        const face = box(1.12, Math.max(.035, position.height - .025), .018, '#263d55'); face.position.set(0, position.y, -.585); group.add(face)
        for (let slot = 0; slot < 4; slot++) { const vent = box(.09, Math.max(.012, position.height * .45), .01, '#0b182b'); vent.position.set(-.4 + slot * .16, position.y, -.6); group.add(vent) }
        const led = box(.045, .025, .015, statusColor, true); led.position.set(.47, position.y, -.605); group.add(led)
        const stripe = box(.018, Math.max(.035, position.height - .025), .018, statusColor, true); stripe.position.set(-.57, position.y, -.607); group.add(stripe)
      })
      const rackLabel = sprite(rack.code, '#d4e7ff', 1.95, .34); rackLabel.position.set(0, height + .4, 0); group.add(rackLabel); labels.push(rackLabel)
      content.add(group); racks.set(rack.id, { group, shell, outline: edges, selection, label: rackLabel, height })
    })
  }
  sceneBox = new THREE.Box3().setFromObject(content)
  if (sceneBox.isEmpty()) sceneBox.set(new THREE.Vector3(-4, 0, -4), new THREE.Vector3(4, 5, 4))
  const size = sceneBox.getSize(new THREE.Vector3()), center = sceneBox.getCenter(new THREE.Vector3())
  const gridSize = Math.max(16, Math.ceil(Math.max(size.x, size.z) + 12))
  grid = new THREE.GridHelper(gridSize, Math.min(120, Math.ceil(gridSize)), '#294464', '#142740'); grid.position.set(center.x, -.24, center.z); scene.add(grid)
  updateAppearance(); resetView()
}
function updateAppearance() {
  if (!ready) return
  if (grid) grid.visible = props.grid
  labels.forEach(label => { label.visible = props.labels })
  racks.forEach((rack, id) => {
    const selected = props.selectedRack === id
    rack.selection.visible = selected
    ;(rack.outline.material as THREE.LineBasicMaterial).opacity = selected ? 1 : .52
    ;(rack.shell.material as THREE.MeshStandardMaterial).opacity = props.transparent ? .10 : .62
    rack.label.visible = props.labels || selected
  })
  devices.forEach((device, id) => {
    const material = device.material as THREE.MeshStandardMaterial
    material.emissive.set(id === props.selectedDevice ? '#3298cc' : '#000000'); material.emissiveIntensity = id === props.selectedDevice ? .8 : 0
  })
}
function positionCamera(box: THREE.Box3, mode: 'perspective' | 'top' | 'front' = 'perspective') {
  if (!ready) return
  const center = box.getCenter(new THREE.Vector3()), radius = box.getSize(new THREE.Vector3()).length() / 2
  const halfFov = Math.min(THREE.MathUtils.degToRad(camera.fov / 2), Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect))
  const distance = Math.max(8, radius / Math.sin(halfFov) * 1.17)
  const direction = mode === 'top' ? new THREE.Vector3(0, 1, -.001) : mode === 'front' ? new THREE.Vector3(0, .05, -1) : new THREE.Vector3(-.9, .7, -1.2)
  camera.position.copy(center).add(direction.normalize().multiplyScalar(distance)); camera.far = Math.max(2000, distance * 5); camera.updateProjectionMatrix()
  controls.target.copy(center); controls.maxDistance = Math.max(100, distance * 4); controls.minDistance = 2; controls.update()
}
function resetView(mode: 'perspective' | 'top' | 'front' = 'perspective') { positionCamera(sceneBox, mode) }
function focusRack() {
  if (!ready || props.selectedRack === null) return
  const rack = racks.get(props.selectedRack)
  if (rack) positionCamera(new THREE.Box3().setFromCenterAndSize(rack.group.position.clone().add(new THREE.Vector3(0, rack.height / 2, 0)), new THREE.Vector3(2.5, rack.height + 1, 2.5)))
}
function down(event: PointerEvent) { pointerStart = { x: event.clientX, y: event.clientY } }
function pick(event: PointerEvent) {
  if (!ready || event.button !== 0 || Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 5) return
  const rect = renderer.domElement.getBoundingClientRect(); pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1); raycaster.setFromCamera(pointer, camera)
  const hits = raycaster.intersectObjects(clickable, false)
  // Transparent cabinet glass must not swallow clicks on a server inside that cabinet.
  const first = hits[0], hit = first && (hits.find(item => item.object.userData.rackId === first.object.userData.rackId && item.object.userData.deviceId) || first)
  emit('select', hit?.object.userData.rackId ?? null, hit?.object.userData.deviceId ?? null)
}
function contextLost(event: Event) { event.preventDefault(); ready = false; cancelAnimationFrame(frame); renderError.value = '图形上下文已中断，请刷新页面重试。' }
function resize() {
  if (!renderer || !host.value) return
  const width = Math.max(1, host.value.clientWidth), height = Math.max(1, host.value.clientHeight)
  camera.aspect = width / height; camera.updateProjectionMatrix(); renderer.setSize(width, height)
  // Preserve the camera target while keeping content in frame when the sidebars resize the canvas.
  if (ready && camera.aspect !== lastAspect) {
    const tangent = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))
    const before = Math.atan(tangent * Math.min(1, lastAspect)), after = Math.atan(tangent * Math.min(1, camera.aspect))
    const offset = camera.position.clone().sub(controls.target)
    camera.position.copy(controls.target).add(offset.multiplyScalar(Math.sin(before) / Math.sin(after)))
  }
  lastAspect = camera.aspect
}
onMounted(() => {
  try {
    scene = new THREE.Scene(); scene.background = new THREE.Color('#080f20')
    camera = new THREE.PerspectiveCamera(40, 1, .1, 2000)
    renderer = new THREE.WebGLRenderer({ antialias: true }); renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); host.value!.appendChild(renderer.domElement)
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.25
    controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.maxPolarAngle = Math.PI / 2 - .03; controls.autoRotateSpeed = .5
    scene.add(new THREE.HemisphereLight('#c5dfff', '#14253b', 2.6))
    const key = new THREE.DirectionalLight('#d8edff', 3); key.position.set(-10, 20, -12); scene.add(key)
    const fill = new THREE.DirectionalLight('#5699ff', 2); fill.position.set(12, 8, 10); scene.add(fill)
    renderer.domElement.addEventListener('pointerdown', down); renderer.domElement.addEventListener('pointerup', pick); renderer.domElement.addEventListener('webglcontextlost', contextLost)
    observer = new ResizeObserver(resize); observer.observe(host.value!); resize(); ready = true; rebuild()
    let last = 0
    const animate = (time: number) => { if (!ready) return; frame = requestAnimationFrame(animate); if (document.hidden) { last = time; return }; controls.autoRotate = props.rotate; controls.update(Math.min((time - last) / 1000, .1)); last = time; renderer.render(scene, camera) }
    frame = requestAnimationFrame(animate)
  } catch { ready = false; renderError.value = '当前浏览器无法启用 WebGL，请开启硬件加速后刷新页面。' }
})
watch(() => props.areas, rebuild)
watch(() => [props.selectedRack, props.selectedDevice, props.labels, props.grid, props.transparent], updateAppearance)
onBeforeUnmount(() => {
  ready = false; cancelAnimationFrame(frame); observer?.disconnect(); controls?.dispose(); release(content); release(grid)
  if (renderer) { renderer.domElement.removeEventListener('pointerdown', down); renderer.domElement.removeEventListener('pointerup', pick); renderer.domElement.removeEventListener('webglcontextlost', contextLost); renderer.dispose(); renderer.domElement.remove() }
})
defineExpose({ resetView, focusRack })
</script>

<style scoped>
.rack-canvas { position: absolute; inset: 0; overflow: hidden; }
.rack-canvas :deep(canvas) { display: block; touch-action: none; }
.render-error { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 28px; text-align: center; color: #dce8ff; background: #080f20; z-index: 2; }
.render-error p, .render-error span { font-size: 12px; line-height: 1.7; color: #9db0d6; }
</style>

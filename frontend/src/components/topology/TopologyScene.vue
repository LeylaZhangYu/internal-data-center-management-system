<template>
  <div ref="host" class="topology-canvas" role="img" aria-label="可交互三维网络拓扑；也可通过设备列表选择节点">
    <div v-if="renderError" class="render-error" role="alert"><strong>3D 场景暂时不可用</strong><p>{{ renderError }}</p><span>仍可使用侧栏设备列表查看详情和连接关系。</span></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { tiers, tierIndex, linkColors, type SceneDevice, type SceneLink } from './model'

const props = defineProps<{ nodes: SceneDevice[]; links: SceneLink[]; selected: number | null; labels: boolean; linkLabels: boolean; rotate: boolean; flow: boolean }>()
const emit = defineEmits<{ (event: 'select', id: number | null): void }>()
const host = ref<HTMLDivElement>()
const renderError = ref('')
let renderer: THREE.WebGLRenderer, camera: THREE.PerspectiveCamera, scene: THREE.Scene, controls: OrbitControls
let content: THREE.Group, observer: ResizeObserver, frame = 0, disposed = false
let bounds = { width: 36, depth: 24, height: 40 }
const nodeObjects = new Map<number, { body: THREE.Mesh; label: THREE.Sprite; ring: THREE.Mesh; decor: THREE.Group }>()
const edgeObjects: { link: SceneLink; line: THREE.Line; label: THREE.Sprite; dot: THREE.Mesh; curve: THREE.QuadraticBezierCurve3 }[] = []
const raycaster = new THREE.Raycaster()
const pointer = new THREE.Vector2()
let pointerStart = { x: 0, y: 0 }

function disposeGroup(group?: THREE.Group) {
  group?.traverse((object: any) => {
    object.geometry?.dispose()
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach(material => { material?.map?.dispose(); material?.dispose() })
  })
  if (group) scene.remove(group)
}
function textSprite(text: string, color = '#d8e6ff', width = 8, height = 1.1) {
  const canvas = document.createElement('canvas'); canvas.width = 768; canvas.height = 96
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = 'rgba(8,17,34,.88)'; ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.font = '500 38px "PingFang SC", "Microsoft YaHei", sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = color
  // Fit long names rather than cutting device identifiers off.
  ctx.fillText(text, canvas.width / 2, canvas.height / 2, 736)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false, depthTest: false }))
  sprite.scale.set(width, height, 1); sprite.renderOrder = 5
  return sprite
}
function rebuild() {
  if (!renderer || disposed) return
  disposeGroup(content); content = new THREE.Group(); scene.add(content)
  nodeObjects.clear(); edgeObjects.length = 0
  const grouped = tiers.map((_, index) => props.nodes.filter(node => tierIndex(node.device_type) === index))
  const largest = Math.max(1, ...grouped.map(nodes => nodes.length))
  const columns = Math.max(3, Math.ceil(Math.sqrt(largest * 1.5)))
  const rows = Math.max(2, Math.ceil(largest / columns))
  bounds = { width: columns * 8 + 8, depth: rows * 7 + 8, height: 40 }
  const positions = new Map<number, THREE.Vector3>()
  tiers.forEach((tier, index) => {
    const y = (tiers.length - index - 1) * 9
    const plate = new THREE.Mesh(new THREE.PlaneGeometry(bounds.width, bounds.depth), new THREE.MeshBasicMaterial({ color: tier.color, transparent: true, opacity: .055, side: THREE.DoubleSide, depthWrite: false }))
    plate.rotation.x = -Math.PI / 2; plate.position.y = y; content.add(plate)
    const border = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(bounds.width, .06, bounds.depth)), new THREE.LineBasicMaterial({ color: tier.color, transparent: true, opacity: .25 }))
    border.position.y = y; content.add(border)
    const title = textSprite(`${String(index + 1).padStart(2, '0')}  ${tier.name}  ·  ${grouped[index].length}`, tier.color, 12, 1.3)
    title.position.set(-bounds.width / 2 + 6, y + 1.1, bounds.depth / 2 + 1.3); content.add(title)
    grouped[index].forEach((node, i) => {
      const countInRow = Math.min(columns, grouped[index].length - Math.floor(i / columns) * columns)
      const position = new THREE.Vector3((i % columns - (countInRow - 1) / 2) * 8, y + 1.5, (Math.floor(i / columns) - (Math.ceil(grouped[index].length / columns) - 1) / 2) * 7)
      positions.set(node.id, position)
      const geometry = node.device_type === 'firewall' ? new THREE.OctahedronGeometry(1.5) : node.device_type === 'storage' ? new THREE.CylinderGeometry(1.3, 1.3, 1.7, 24) : new THREE.BoxGeometry(3.1, 1.5, 1.9)
      const material = new THREE.MeshStandardMaterial({ color: tier.color, emissive: tier.color, emissiveIntensity: .16, roughness: .4, metalness: .35, transparent: true })
      const body = new THREE.Mesh(geometry, material); body.position.copy(position); body.userData.deviceId = node.id; content.add(body)
      const decor = new THREE.Group(); decor.position.copy(position)
      if (!['firewall', 'storage'].includes(node.device_type)) {
        for (let slot = 0; slot < 5; slot++) {
          const light = new THREE.Mesh(new THREE.BoxGeometry(.25, .17, .05), new THREE.MeshBasicMaterial({ color: node.status === 'active' ? '#bcffee' : '#6b7b90', transparent: true }))
          light.position.set(-1.05 + slot * .47, -.1, 1); decor.add(light)
        }
      }
      content.add(decor)
      const ring = new THREE.Mesh(new THREE.RingGeometry(2, 2.15, 40), new THREE.MeshBasicMaterial({ color: tier.color, side: THREE.DoubleSide, transparent: true, opacity: .5, depthWrite: false }))
      ring.rotation.x = -Math.PI / 2; ring.position.set(position.x, y + .12, position.z); content.add(ring)
      const label = textSprite(node.name); label.position.copy(position).add(new THREE.Vector3(0, 2, 0)); content.add(label)
      nodeObjects.set(node.id, { body, label, ring, decor })
    })
  })
  const parallel = new Map<string, number>()
  props.links.forEach(link => {
    const start = positions.get(link.source), end = positions.get(link.target)
    if (!start || !end) return
    const key = [link.source, link.target].sort((a, b) => a - b).join(':')
    const offset = parallel.get(key) || 0; parallel.set(key, offset + 1)
    const middle = start.clone().lerp(end, .5)
    middle.z += 3 + offset * 2; middle.y += 3 + offset
    if (link.source === link.target) middle.x += 6 + offset * 2
    const curve = new THREE.QuadraticBezierCurve3(start, middle, end)
    const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(40))
    const color = linkColors[link.status] || '#94a3b8'
    const material = link.status === 'up' ? new THREE.LineBasicMaterial({ color, transparent: true, opacity: .65 }) : new THREE.LineDashedMaterial({ color, transparent: true, opacity: .65, dashSize: .7, gapSize: .45 })
    const line = new THREE.Line(geometry, material); line.computeLineDistances(); content.add(line)
    const label = textSprite(`${link.bandwidth || '带宽未填'} · VLAN ${link.vlan || '—'}`, color, 9, 1)
    label.position.copy(curve.getPoint(.5)); content.add(label)
    const dot = new THREE.Mesh(new THREE.SphereGeometry(.18, 8, 6), new THREE.MeshBasicMaterial({ color })); content.add(dot)
    edgeObjects.push({ link, line, label, dot, curve })
  })
  resetView(); updateFocus()
}
function updateFocus() {
  const nearby = new Set<number>()
  if (props.selected !== null) {
    nearby.add(props.selected)
    props.links.forEach(link => { if (link.source === props.selected || link.target === props.selected) { nearby.add(link.source); nearby.add(link.target) } })
  }
  nodeObjects.forEach((object, id) => {
    const relevant = props.selected === null || nearby.has(id)
    ;(object.body.material as THREE.MeshStandardMaterial).opacity = relevant ? 1 : .12
    ;(object.body.material as THREE.MeshStandardMaterial).emissiveIntensity = id === props.selected ? .65 : .16
    object.decor.visible = relevant
    ;(object.ring.material as THREE.MeshBasicMaterial).opacity = id === props.selected ? 1 : relevant ? .4 : .06
    object.ring.scale.setScalar(id === props.selected ? 1.25 : 1)
    object.label.visible = relevant && (props.labels || id === props.selected || (props.selected !== null && nearby.has(id)))
  })
  edgeObjects.forEach(edge => {
    const relevant = props.selected === null || edge.link.source === props.selected || edge.link.target === props.selected
    ;(edge.line.material as THREE.LineBasicMaterial).opacity = relevant ? .75 : .05
    edge.label.visible = relevant && props.linkLabels
    edge.dot.visible = relevant && props.flow && edge.link.status === 'up'
  })
}
function resetView(top = false) {
  if (!camera) return
  const center = new THREE.Vector3(0, 18, 0)
  const radius = Math.sqrt(bounds.width ** 2 + bounds.depth ** 2 + bounds.height ** 2) / 2
  const halfFov = Math.min(THREE.MathUtils.degToRad(camera.fov / 2), Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect))
  const distance = radius / Math.sin(halfFov) * 1.12
  const direction = top ? new THREE.Vector3(0, 1, .01) : new THREE.Vector3(.85, .65, 1)
  camera.position.copy(center).add(direction.normalize().multiplyScalar(distance))
  camera.far = Math.max(2000, distance * 5); camera.updateProjectionMatrix()
  controls.target.copy(center); controls.maxDistance = distance * 3; controls.minDistance = 6; controls.update()
}
function selectAt(event: PointerEvent) {
  if (!renderer || Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 5 || event.button !== 0) return
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1)
  raycaster.setFromCamera(pointer, camera)
  const hit = raycaster.intersectObjects([...nodeObjects.values()].map(object => object.body), false)[0]
  emit('select', hit ? hit.object.userData.deviceId : null)
}
function pointerDown(event: PointerEvent) { pointerStart = { x: event.clientX, y: event.clientY } }
function contextLost(event: Event) { event.preventDefault(); renderError.value = '图形上下文已中断，请刷新页面重试。'; cancelAnimationFrame(frame) }
function resize() {
  if (!host.value || !renderer) return
  const width = Math.max(1, host.value.clientWidth), height = Math.max(1, host.value.clientHeight)
  camera.aspect = width / height; camera.updateProjectionMatrix(); renderer.setSize(width, height)
}
onMounted(() => {
  try {
    scene = new THREE.Scene(); scene.background = new THREE.Color('#080f20')
    camera = new THREE.PerspectiveCamera(42, 1, .1, 3000)
    renderer = new THREE.WebGLRenderer({ antialias: true }); renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    host.value!.appendChild(renderer.domElement)
    controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.autoRotateSpeed = .45
    scene.add(new THREE.HemisphereLight('#e0efff', '#273551', 2.5))
    const light = new THREE.DirectionalLight('#ffffff', 2.5); light.position.set(30, 60, 30); scene.add(light)
    renderer.domElement.addEventListener('pointerdown', pointerDown)
    renderer.domElement.addEventListener('pointerup', selectAt)
    renderer.domElement.addEventListener('webglcontextlost', contextLost)
    observer = new ResizeObserver(resize); observer.observe(host.value!); resize(); rebuild()
    let last = 0
    const animate = (time: number) => {
      if (disposed) return
      frame = requestAnimationFrame(animate)
      if (document.hidden) { last = time; return }
      controls.autoRotate = props.rotate; controls.update(Math.min((time - last) / 1000, .1)); last = time
      edgeObjects.forEach((edge, index) => { if (edge.dot.visible) edge.dot.position.copy(edge.curve.getPoint((time / 6000 + index * .173) % 1)) })
      renderer.render(scene, camera)
    }
    frame = requestAnimationFrame(animate)
  } catch { renderError.value = '当前浏览器无法启用 WebGL，请开启硬件加速后重试。' }
})
watch(() => [props.nodes, props.links], rebuild)
watch(() => [props.selected, props.labels, props.linkLabels, props.flow], updateFocus)
onBeforeUnmount(() => {
  disposed = true; cancelAnimationFrame(frame); observer?.disconnect(); controls?.dispose(); disposeGroup(content)
  if (renderer) {
    renderer.domElement.removeEventListener('pointerdown', pointerDown); renderer.domElement.removeEventListener('pointerup', selectAt)
    renderer.domElement.removeEventListener('webglcontextlost', contextLost); renderer.dispose(); renderer.domElement.remove()
  }
})
defineExpose({ resetView })
</script>

<style scoped>
.topology-canvas{position:absolute;inset:0;overflow:hidden}.topology-canvas :deep(canvas){display:block;touch-action:none}.render-error{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:28px;text-align:center;color:#dce8ff;background:#080f20;z-index:2}.render-error p,.render-error span{font-size:13px;color:#9db0d6}
</style>

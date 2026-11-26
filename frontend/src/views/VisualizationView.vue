<template>
  <section ref="page" class="facility-view" :class="{ 'nav-closed': !sidebarOpen, 'detail-closed': !inspectorOpen }">
    <header class="facility-header">
      <div class="facility-title"><span class="eyebrow">INFRASTRUCTURE / DIGITAL SPACE</span><h1>数据中心 <span>3D 空间可视化</span></h1><p>真实机柜布局 · 设备 U 位映射 · 资源容量视图</p></div>
      <div class="header-actions"><span class="data-source"><i></i>平台录入数据</span><button :disabled="loading" @click="load">{{ loading ? '读取中…' : '↻ 刷新数据' }}</button><button @click="toggleFullscreen">{{ fullscreen ? '退出全屏' : '⛶ 全屏查看' }}</button></div>
    </header>

    <div class="facility-body">
      <aside v-show="sidebarOpen" class="facility-nav" aria-label="机房与机柜导航">
        <section class="nav-section">
          <div class="section-heading"><h2>空间导航</h2><span>EXPLORE</span></div>
          <label for="facility-room">选择机房</label>
          <select id="facility-room" v-model="selectedDcId" :disabled="loading"><option v-if="!layoutData.length" :value="null">暂无机房布局</option><option v-for="dc in layoutData" :key="dc.id" :value="dc.id">{{ dc.name }}</option></select>
          <label for="facility-area">区域</label><select id="facility-area" v-model="selectedAreaId"><option value="all">全部区域</option><option v-for="area in selectedDc?.areas || []" :key="area.id" :value="String(area.id)">{{ area.name }} · {{ area.racks.length }} 柜</option></select>
          <label for="facility-search">查找机柜或设备</label><div class="search-field"><input id="facility-search" v-model="search" type="search" placeholder="机柜编号 / 设备名称 / IP" /></div>
        </section>
        <section class="nav-section inventory">
          <div class="section-heading"><h2>机柜列表</h2><span>{{ matchingRacks.length }} RACKS</span></div>
          <button v-for="rack in matchingRacks" :key="rack.id" class="rack-entry" :class="{ selected: selectedRackId === rack.id }" @click="selectRack(rack.id)">
            <span class="rack-icon" aria-hidden="true"><i></i><i></i><i></i></span><span class="rack-entry-copy"><strong>{{ rack.code }}<small>{{ rack.utilization_rate }}%</small></strong><span>{{ rack.areaName }} · {{ rack.device_count }} 台设备</span><span class="mini-meter"><i :style="{ width: meterWidth(rack.utilization_rate), background: utilizationColor(rack.utilization_rate) }"></i></span></span>
          </button>
          <p v-if="!matchingRacks.length" class="muted-text">{{ search ? '没有找到匹配的机柜或设备。' : '该范围暂无机柜。' }}</p>
        </section>
        <section class="capacity-card"><span class="eyebrow">CAPACITY OVERVIEW</span><div><strong>{{ capacityRate }}<small>%</small></strong><span>当前范围 U 位利用率</span></div><div class="capacity-meter"><i :style="{ width: meterWidth(capacityRate) }"></i></div><p>已使用 {{ occupiedU }} U <span>总容量 {{ totalU }} U</span></p></section>
        <div class="nav-footer"><router-link to="/racks">机柜管理 ↗</router-link><router-link to="/network-topology">网络拓扑 ↗</router-link></div>
      </aside>

      <main class="facility-stage">
        <RackScene ref="scene" :areas="visibleAreas" :selected-rack="selectedRackId" :selected-device="selectedDeviceId" :labels="labels" :grid="grid" :transparent="transparent" :rotate="rotate" @select="selectFromScene" />
        <div class="stage-topbar"><button :aria-expanded="sidebarOpen" @click="sidebarOpen = !sidebarOpen">{{ sidebarOpen ? '收起导航' : '展开导航' }}</button><span>{{ selectedDc?.name || '机房空间' }} <b>/</b> {{ selectedAreaName }}</span><button class="detail-toggle" :aria-expanded="inspectorOpen" @click="inspectorOpen = !inspectorOpen">{{ inspectorOpen ? '收起详情' : '展开详情' }}</button></div>
        <div class="scene-metrics"><div><small>机柜</small><strong>{{ visibleRacks.length }}<span>柜</span></strong></div><div><small>已上架设备</small><strong>{{ deviceCount }}<span>台</span></strong></div><div><small>剩余容量</small><strong>{{ Math.max(0, totalU - occupiedU) }}<span>U</span></strong></div></div>
        <div v-if="error" class="scene-message error" role="alert"><strong>无法加载机房布局</strong><p>{{ error }}</p><button @click="load">重新加载</button></div>
        <div v-else-if="loading" class="scene-message" role="status"><span class="loading-orbit"></span><strong>正在构建机房空间…</strong><p>读取机柜布局与设备 U 位</p></div>
        <div v-else-if="!visibleRacks.length" class="scene-message"><strong>此处还没有机柜</strong><p>录入机房、区域与机柜后，将自动生成空间布局。</p><router-link to="/racks">前往机柜管理 →</router-link></div>
        <div class="scene-legend"><span><i style="background:#4edbb5"></i>运行中</span><span><i style="background:#69b2ff"></i>待机</span><span><i style="background:#ffbc69"></i>维护中</span><span><i style="background:#af98ff"></i>计划中</span><span><i style="background:#8391a9"></i>其他状态</span></div>
        <footer class="scene-controls"><div><button :class="{ on: rotate }" :aria-pressed="rotate" @click="rotate = !rotate">自动旋转</button><button :class="{ on: transparent }" :aria-pressed="transparent" @click="transparent = !transparent">透明机柜</button><button :class="{ on: labels }" :aria-pressed="labels" @click="labels = !labels">机柜标签</button><button :class="{ on: grid }" :aria-pressed="grid" @click="grid = !grid">地面网格</button><button @click="changeView('top')">俯视</button><button @click="changeView('front')">正视</button><button @click="changeView()">重置视角</button></div><p>拖动旋转 · 滚轮缩放 · 右键平移 · 点击设备查看详情</p></footer>
      </main>

      <aside v-show="inspectorOpen" class="facility-inspector" aria-label="机柜及设备详情">
        <div class="inspector-top"><span class="eyebrow">RACK INSPECTOR</span><span class="inspector-tag">{{ selectedRack ? '已选机柜' : '空间概览' }}</span></div>
        <template v-if="selectedRack">
          <div class="selected-rack-title"><h2>{{ selectedRack.code }}</h2><button @click="focusSelected">聚焦 ↗</button></div><p class="rack-location">{{ selectedDc?.name }} / {{ selectedRack.areaName }}</p>
          <div class="rack-capacity"><div><span>U 位利用率</span><strong :style="{ color: utilizationColor(selectedRack.utilization_rate) }">{{ selectedRack.utilization_rate }}<small>%</small></strong></div><div class="capacity-meter"><i :style="{ width: meterWidth(selectedRack.utilization_rate), background: utilizationColor(selectedRack.utilization_rate) }"></i></div><p>{{ selectedRack.device_count }} 台设备<span>{{ selectedRack.total_u }} U · {{ orientationLabel(selectedRack.orientation) }}</span></p></div>
          <div class="section-heading device-list-heading"><h3>已上架设备</h3><span>{{ selectedRack.devices.length }}</span></div>
          <div class="inspector-devices">
            <article v-for="device in selectedRack.devices" :key="device.id" class="device-card" :class="{ selected: selectedDeviceId === device.id }">
              <button class="device-title" :aria-expanded="selectedDeviceId === device.id" @click="selectedDeviceId = selectedDeviceId === device.id ? null : device.id"><i :style="{ background: statusColors[device.status] || '#8391a9' }"></i><strong>{{ device.name }}</strong><span>U{{ device.start_u }}–{{ (device.start_u || 1) + device.u_height - 1 }}</span></button>
              <div class="device-summary"><span>{{ device.ip_address || 'IP 未填写' }}</span><small>{{ deviceStatusLabel(device.status) }}</small></div>
              <dl v-if="selectedDeviceId === device.id"><dt>资产编号</dt><dd>{{ device.asset_number || '未填写' }}</dd><dt>型号</dt><dd>{{ device.model || '未填写' }}</dd><dt>管理员</dt><dd>{{ device.administrators?.join('、') || '未填写' }}</dd><dt>占用空间</dt><dd>{{ device.u_height }} U</dd></dl>
              <div v-if="selectedDeviceId === device.id && device.links?.length" class="device-links"><span>端口连接</span><p v-for="(link, index) in device.links" :key="index">{{ link }}</p></div>
            </article>
            <div v-if="!selectedRack.devices.length" class="empty-devices"><span>◇</span><p>此机柜暂无已上架设备</p><router-link to="/devices">录入设备 →</router-link></div>
          </div>
        </template>
        <template v-else>
          <div class="inspector-intro"><div class="rack-illustration" aria-hidden="true"><i></i><i></i><i></i><i></i></div><h2>从空间到设备</h2><p>点击场景中的机柜或设备，查看容量、U 位与端口连接。</p><span>也可以从左侧机柜列表选择</span></div>
          <div class="area-overview"><div class="section-heading"><h3>区域分布</h3><span>{{ visibleAreas.length }} ZONES</span></div><div v-for="(area, index) in visibleAreas" :key="area.id" class="area-row"><i :style="{ background: areaColors[index % areaColors.length] }"></i><span>{{ area.name }}</span><strong>{{ area.racks.length }}<small> 柜</small></strong></div></div>
        </template>
        <div class="inspector-note"><span>布局说明</span><p>区域分组展示，区内沿用录入的机柜坐标。设备灯色对应平台录入状态。</p></div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'
import RackScene from '../components/rack-scene/RackScene.vue'
import { areaColors, statusColors, isMounted, type DataCenterLayout } from '../components/rack-scene/layout'
import { deviceStatusLabel, orientationLabel } from '../utils/labels'

const layoutData = ref<DataCenterLayout[]>([])
const selectedDcId = ref<number | null>(null), selectedAreaId = ref('all'), search = ref('')
const selectedRackId = ref<number | null>(null), selectedDeviceId = ref<number | null>(null)
const sidebarOpen = ref(true), inspectorOpen = ref(true), loading = ref(true), error = ref('')
const labels = ref(true), grid = ref(true), transparent = ref(true), rotate = ref(false), fullscreen = ref(false)
const page = ref<HTMLElement>(), scene = ref<InstanceType<typeof RackScene>>()
const selectedDc = computed(() => layoutData.value.find(dc => dc.id === selectedDcId.value))
const visibleAreas = computed(() => (selectedDc.value?.areas || []).filter(area => selectedAreaId.value === 'all' || String(area.id) === selectedAreaId.value))
const selectedAreaName = computed(() => selectedAreaId.value === 'all' ? '全部区域' : visibleAreas.value[0]?.name || '区域')
const visibleRacks = computed(() => visibleAreas.value.flatMap(area => area.racks.map(rack => ({ ...rack, areaName: area.name }))))
const matchingRacks = computed(() => {
  const term = search.value.trim().toLocaleLowerCase()
  return visibleRacks.value.filter(rack => !term || [rack.code, rack.areaName, ...rack.devices.flatMap(device => [device.name, device.ip_address, device.asset_number])].some(value => value?.toLocaleLowerCase().includes(term)))
})
const selectedRack = computed(() => visibleRacks.value.find(rack => rack.id === selectedRackId.value))
const totalU = computed(() => visibleRacks.value.reduce((sum, rack) => sum + rack.total_u, 0))
const occupiedU = computed(() => visibleRacks.value.reduce((sum, rack) => sum + rack.devices.filter(isMounted).reduce((used, device) => used + device.u_height, 0), 0))
const capacityRate = computed(() => totalU.value ? Math.round(occupiedU.value / totalU.value * 1000) / 10 : 0)
const deviceCount = computed(() => visibleRacks.value.reduce((sum, rack) => sum + rack.device_count, 0))
const meterWidth = (rate: number) => `${Math.min(100, Math.max(0, rate))}%`
const utilizationColor = (rate: number) => rate >= 85 ? '#ffbd78' : rate >= 60 ? '#7dbbff' : '#67dbc4'
function selectRack(id: number) { selectedRackId.value = id; selectedDeviceId.value = null; inspectorOpen.value = true }
function selectFromScene(rackId: number | null, deviceId: number | null) { selectedRackId.value = rackId; selectedDeviceId.value = deviceId; if (rackId !== null) inspectorOpen.value = true }
function focusSelected() { rotate.value = false; scene.value?.focusRack() }
function changeView(mode: 'perspective' | 'top' | 'front' = 'perspective') { rotate.value = false; scene.value?.resetView(mode) }
watch(selectedDcId, () => { selectedAreaId.value = 'all'; selectedRackId.value = null; selectedDeviceId.value = null })
watch(visibleRacks, racks => {
  const rack = racks.find(item => item.id === selectedRackId.value)
  if (!rack) { selectedRackId.value = null; selectedDeviceId.value = null }
  else if (!rack.devices.some(device => device.id === selectedDeviceId.value)) selectedDeviceId.value = null
})
let request: AbortController | undefined
async function load() {
  request?.abort(); const controller = new AbortController(); request = controller; loading.value = true; error.value = ''
  try {
    const { data } = await client.get<DataCenterLayout[]>('/visualization/layout', { signal: controller.signal })
    if (controller.signal.aborted) return
    layoutData.value = data
    if (!data.some(dc => dc.id === selectedDcId.value)) selectedDcId.value = data[0]?.id ?? null
    if (selectedAreaId.value !== 'all' && !selectedDc.value?.areas.some(area => String(area.id) === selectedAreaId.value)) selectedAreaId.value = 'all'
  } catch { if (!controller.signal.aborted) error.value = '请检查网络或后端服务，然后重新加载。' }
  finally { if (!controller.signal.aborted) loading.value = false }
}
async function toggleFullscreen() {
  try { if (document.fullscreenElement === page.value) await document.exitFullscreen(); else await page.value?.requestFullscreen() }
  catch { ElMessage.info('当前浏览器不支持全屏，可使用浏览器的全屏功能。') }
}
function fullscreenChanged() { fullscreen.value = document.fullscreenElement === page.value }
onMounted(() => { inspectorOpen.value = window.innerWidth > 1150 || window.innerWidth <= 780; load(); document.addEventListener('fullscreenchange', fullscreenChanged) })
onBeforeUnmount(() => { request?.abort(); document.removeEventListener('fullscreenchange', fullscreenChanged) })
</script>

<style scoped>
.facility-view {
  --line: rgba(135, 170, 221, .16);
  --muted: #8ea5c7;
  --bright: #dceaff;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 106px);
  min-height: 690px;
  overflow: hidden;
  border: 1px solid #223652;
  border-radius: 14px;
  background: #080f20;
  color: var(--bright);
  font-size: 12px;
}
.facility-view:fullscreen { height: 100vh; border-radius: 0; }
.facility-view button, .facility-view input, .facility-view select { font: inherit; }
.facility-view button { cursor: pointer; padding: 8px 11px; border: 1px solid var(--line); border-radius: 7px; background: #14243c; color: #b9ceec; transition: background .18s, border-color .18s; }
.facility-view button:hover { background: #203b5e; border-color: #42678f; color: #fff; }
.facility-view button:disabled { opacity: .5; cursor: wait; }
.facility-view button:focus-visible, .facility-view input:focus-visible, .facility-view select:focus-visible { outline: 2px solid #74b7ff; outline-offset: 2px; }
.facility-view a { color: #8fc3ff; text-decoration: none; }
.facility-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 20px 24px; border-bottom: 1px solid var(--line); background: radial-gradient(ellipse at 20% 0%, #19345580, transparent 65%), #0e192d; }
.eyebrow { color: #7898c2; font-size: 9px; letter-spacing: .18em; }
.facility-title h1 { font-size: 21px; font-weight: 600; margin: 6px 0 7px; letter-spacing: .04em; }
.facility-title h1 span { color: #87bcff; }
.facility-title p { color: var(--muted); margin: 0; font-size: 11px; }
.header-actions { display: flex; gap: 9px; align-items: center; flex-wrap: wrap; }
.data-source { display: flex; align-items: center; gap: 7px; color: #97acc8; font-size: 10px; margin-right: 8px; }
.data-source i { width: 5px; height: 5px; background: #6cb5fa; border-radius: 50%; box-shadow: 0 0 10px #589de580; }
.facility-body { display: grid; grid-template-columns: 224px minmax(0, 1fr) 286px; flex: 1; min-height: 0; }
.nav-closed .facility-body { grid-template-columns: minmax(0, 1fr) 286px; }
.detail-closed .facility-body { grid-template-columns: 224px minmax(0, 1fr); }
.nav-closed.detail-closed .facility-body { grid-template-columns: minmax(0, 1fr); }
.facility-nav { display: flex; flex-direction: column; border-right: 1px solid var(--line); background: #0d192c; overflow-y: auto; min-height: 0; scrollbar-width: thin; scrollbar-color: #314d70 transparent; }
/* Keep navigation sections in document flow when a long rack list needs scrolling. */
.facility-nav > * { flex-shrink: 0; }
.nav-section { padding: 17px 15px; border-bottom: 1px solid var(--line); }
.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.section-heading h2, .section-heading h3 { margin: 0; font-size: 12px; font-weight: 500; color: #d5e3f7; }
.section-heading>span { color: #6e8bb2; font-size: 9px; letter-spacing: .07em; }
.facility-nav label { display: block; color: #8fa7c9; font-size: 10px; margin: 12px 0 7px; }
.facility-nav select, .facility-nav input { box-sizing: border-box; width: 100%; min-width: 0; padding: 9px; background: #091425; border: 1px solid #293f5e; color: #cddff8; border-radius: 6px; font-size: 11px; }
.facility-nav input::placeholder { color: #6d85a8; }
.facility-nav option { background: #0e1c31; }
.inventory { flex: 1 0 auto; min-height: 130px; }
.facility-view .rack-entry { display: flex; align-items: center; gap: 11px; width: 100%; padding: 12px 8px; text-align: left; border-color: transparent; background: transparent; margin-bottom: 4px; }
.facility-view .rack-entry.selected { background: #193351; border-color: #38628e; }
.rack-icon { display: flex; flex-direction: column; gap: 3px; padding: 6px 4px; border: 1px solid #527da4; border-radius: 3px; }
.rack-icon i { display: block; width: 12px; height: 3px; background: #426a91; border-right: 2px solid #80b8de; }
.rack-entry-copy { flex: 1; min-width: 0; }
.rack-entry-copy strong { display: flex; align-items: center; justify-content: space-between; color: #d6e7fc; font-size: 12px; font-weight: 500; overflow-wrap: anywhere; gap: 4px; }
.rack-entry-copy strong small { color: #79afce; font-size: 10px; }
.rack-entry-copy>span { display: block; margin-top: 6px; color: #819aba; font-size: 10px; }
.mini-meter, .capacity-meter { display: block; height: 3px; overflow: hidden; background: #20334a; border-radius: 3px; }
.mini-meter i, .capacity-meter i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #528fec, #6bdfce); }
.capacity-card { padding: 18px 16px 12px; margin: 10px; border: 1px solid #253c58; border-radius: 9px; background: linear-gradient(135deg, #152b45, #102035); }
.capacity-card>div:first-of-type { display: flex; align-items: flex-end; justify-content: space-between; margin: 10px 0 14px; gap: 6px; }
.capacity-card strong { font-size: 27px; font-weight: 400; color: #9cdbed; }.capacity-card strong small { font-size: 12px; margin-left: 2px; }
.capacity-card>div>span { color: #88a0c0; font-size: 9px; line-height: 1.5; max-width: 70px; }
.capacity-card p, .rack-capacity p { display: flex; justify-content: space-between; gap: 6px; color: #8fa7c6; font-size: 10px; margin: 11px 0 0; }
.nav-footer { display: flex; justify-content: space-between; padding: 8px 16px 17px; font-size: 10px; }
.facility-stage { position: relative; min-width: 0; overflow: hidden; min-height: 500px; }
.stage-topbar { position: absolute; top: 16px; left: 16px; right: 16px; display: flex; align-items: center; gap: 9px; pointer-events: none; }
.stage-topbar>* { pointer-events: auto; }
.stage-topbar button { font-size: 10px; padding: 7px 9px; }
.stage-topbar>span { color: #8ca9cf; font-size: 10px; background: #0b1728c9; padding: 6px 8px; border-radius: 5px; }
.stage-topbar b { color: #436082; font-weight: 400; margin: 0 5px; }
.detail-toggle { margin-left: auto; }
.scene-metrics { position: absolute; top: 66px; left: 19px; display: flex; gap: 26px; pointer-events: none; padding: 9px 13px; border-left: 2px solid #3e648a; background: linear-gradient(90deg, #0e1c30e8, #0e1c3040); }
.scene-metrics small { display: block; font-size: 10px; color: #8ba2c1; margin-bottom: 5px; }
.scene-metrics strong { color: #c3e1fb; font-size: 24px; font-weight: 400; font-variant-numeric: tabular-nums; }
.scene-metrics strong span { font-size: 9px; color: #7796b8; margin-left: 5px; }
.scene-controls { position: absolute; bottom: 0; left: 0; right: 0; padding: 15px 16px 12px; border-top: 1px solid var(--line); background: #0c182ce8; backdrop-filter: blur(10px); }
.scene-controls>div { display: flex; gap: 6px; flex-wrap: wrap; }
.scene-controls button { font-size: 10px; padding: 7px 9px; }
.scene-controls button.on { background: #1d395a; color: #abd1fa; border-color: #335e87; }
.scene-controls p { color: #718bab; font-size: 9px; margin: 10px 0 0; line-height: 1.5; }
.scene-legend { position: absolute; bottom: 118px; left: 18px; right: 18px; display: flex; flex-wrap: wrap; gap: 12px; font-size: 9px; color: #9bb0cd; pointer-events: none; }
.scene-legend>span { display: flex; align-items: center; gap: 5px; }
.scene-legend i { height: 5px; width: 5px; border-radius: 50%; }
.scene-message { position: absolute; top: 45%; left: 50%; transform: translate(-50%, -50%); box-sizing: border-box; width: min(340px, 85%); padding: 25px; border: 1px solid #355476; border-radius: 12px; background: #102037f5; text-align: center; box-shadow: 0 15px 40px #0005; }
.scene-message strong { display: block; font-size: 14px; font-weight: 500; }.scene-message p { color: #8ea7c8; font-size: 11px; line-height: 1.7; }.scene-message.error { border-color: #97586a; }
.loading-orbit { display: block; width: 24px; height: 24px; border: 1px solid #2b4b70; border-top-color: #78b8ff; border-radius: 50%; margin: 0 auto 16px; animation: orbit 1s linear infinite; }
@keyframes orbit { to { transform: rotate(360deg); } }
.facility-inspector { display: flex; flex-direction: column; min-height: 0; overflow: auto; scrollbar-width: thin; scrollbar-color: #314d70 transparent; padding: 20px 17px; border-left: 1px solid var(--line); background: linear-gradient(145deg, #122139, #0c182b 55%); }
.inspector-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }.inspector-tag { font-size: 9px; color: #83b2da; padding: 4px 6px; border: 1px solid #274866; border-radius: 4px; }
.selected-rack-title { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-top: 20px; }.selected-rack-title h2 { margin: 0; font-size: 26px; font-weight: 400; color: #dfedff; overflow-wrap: anywhere; }.selected-rack-title button { padding: 5px 8px; font-size: 10px; flex-shrink: 0; }
.rack-location { font-size: 10px; color: #829dbf; line-height: 1.7; margin: 8px 0 20px; }
.rack-capacity { padding: 14px; border: 1px solid #27405c; border-radius: 8px; background: #172b43a8; }.rack-capacity>div:first-child { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }.rack-capacity>div>span { color: #9bb2ce; font-size: 11px; }.rack-capacity strong { font-size: 24px; font-weight: 400; }.rack-capacity strong small { font-size: 11px; margin-left: 2px; }.rack-capacity p { flex-wrap: wrap; font-size: 9px; line-height: 1.6; }
.device-list-heading { margin-top: 25px; }.inspector-devices { margin-bottom: 16px; }.device-card { border: 1px solid #243b57; border-radius: 7px; margin-bottom: 9px; background: #101f34; overflow: hidden; }.device-card.selected { border-color: #4778a6; background: #162b44; }
.facility-view .device-title { width: 100%; display: flex; gap: 7px; align-items: center; padding: 12px 10px 5px; border: 0; background: transparent; text-align: left; }.device-title>i { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }.device-title strong { font-size: 11px; font-weight: 500; color: #cee0f7; flex: 1; overflow-wrap: anywhere; }.device-title>span { color: #8bb8e2; font-size: 9px; white-space: nowrap; }
.device-summary { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px; color: #88a4c6; padding: 6px 10px 12px; font-size: 10px; }.device-summary small { color: #6e8aa9; font-size: 9px; }
.device-card dl { display: grid; grid-template-columns: 50px minmax(0, 1fr); gap: 9px; border-top: 1px solid var(--line); margin: 0 10px; padding: 12px 0; font-size: 10px; line-height: 1.6; }.device-card dt { color: #7892b3; }.device-card dd { margin: 0; color: #b8cce8; overflow-wrap: anywhere; }
.device-links { padding: 0 10px 10px; font-size: 10px; }.device-links>span { color: #7d9bbf; }.device-links p { margin: 6px 0; color: #8cb9e4; line-height: 1.6; overflow-wrap: anywhere; }
.inspector-intro { padding: 42px 10px 30px; text-align: center; }.inspector-intro h2 { font-size: 17px; font-weight: 400; color: #c8dff8; margin: 24px 0 13px; }.inspector-intro p { font-size: 11px; line-height: 1.9; color: #8aa5c7; }.inspector-intro>span { font-size: 10px; color: #5c7ca3; }
.rack-illustration { width: 50px; display: flex; flex-direction: column; gap: 5px; padding: 9px; border: 1px solid #4272a0; border-radius: 5px; margin: auto; transform: perspective(180px) rotateY(-16deg); background: linear-gradient(120deg, #234466, #152a44); box-shadow: 10px 10px 30px #070f2080; }.rack-illustration i { height: 11px; background: #142a42; border: 1px solid #385d80; border-right: 3px solid #6dbab6; }
.area-overview { margin-top: 10px; border-top: 1px solid var(--line); padding-top: 18px; }.area-row { display: flex; align-items: center; gap: 8px; padding: 11px 0; border-bottom: 1px solid #20365080; color: #9eb8d8; font-size: 11px; }.area-row>i { width: 6px; height: 6px; border-radius: 2px; }.area-row strong { margin-left: auto; font-weight: 400; color: #c9ddf4; }.area-row small { color: #728fb1; font-size: 9px; }
.inspector-note { margin-top: auto; padding-top: 24px; font-size: 10px; color: #6583a6; line-height: 1.8; }.inspector-note>span { color: #839fc1; }.inspector-note p { margin: 5px 0 0; }.muted-text { color: var(--muted); font-size: 11px; line-height: 1.7; }.empty-devices { padding: 24px 5px; text-align: center; color: #7c99bd; font-size: 11px; }.empty-devices>span { font-size: 28px; color: #42668c; }
@media (max-width: 1400px) {
  .facility-body { grid-template-columns: 200px minmax(0, 1fr) 250px; }
  .nav-closed .facility-body { grid-template-columns: minmax(0, 1fr) 250px; }
  .detail-closed .facility-body { grid-template-columns: 200px minmax(0, 1fr); }
  .nav-closed.detail-closed .facility-body { grid-template-columns: minmax(0, 1fr); }
  .facility-inspector { padding: 17px 14px; }.scene-metrics { gap: 20px; }.data-source { display: none; }
}
@media (max-width: 1150px) {
  .facility-body, .nav-closed .facility-body { grid-template-columns: 200px minmax(0, 1fr); position: relative; }
  .nav-closed .facility-body { grid-template-columns: minmax(0, 1fr); }
  .facility-inspector { position: absolute; z-index: 3; right: 12px; top: 58px; bottom: 125px; width: 245px; box-sizing: border-box; border: 1px solid #335174; border-radius: 10px; box-shadow: 0 15px 40px #0006; }
  .facility-title h1 { font-size: 18px; }.facility-header { padding: 17px 20px; }
}
@media (max-width: 780px) {
  .facility-view { min-height: 820px; height: auto; }.facility-header { flex-direction: column; align-items: flex-start; gap: 14px; }.facility-body, .nav-closed .facility-body, .detail-closed .facility-body, .nav-closed.detail-closed .facility-body { display: flex; flex-direction: column; }
  .facility-nav { max-height: 265px; border-right: 0; border-bottom: 1px solid var(--line); }.inventory { min-height: initial; }.facility-stage { height: 660px; flex: none; }.facility-inspector { position: static; width: auto; max-height: 450px; margin: 0; border-radius: 0; border: 0; border-top: 1px solid var(--line); }.stage-topbar { gap: 6px; left: 10px; right: 10px; }.stage-topbar>span { max-width: 90px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.scene-controls { padding: 12px 10px; }.scene-legend { bottom: 140px; gap: 9px; }.scene-metrics { left: 12px; gap: 18px; }.scene-metrics strong { font-size: 21px; }
}
@media (prefers-reduced-motion: reduce) { .loading-orbit { animation: none; } }
</style>

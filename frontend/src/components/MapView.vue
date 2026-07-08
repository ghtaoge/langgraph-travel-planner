<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Activity } from '@/types'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const mapContainer = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
const markers: L.Marker[] = []

/** 初始化地图 */
onMounted(() => {
  if (mapContainer.value) {
    map = L.map(mapContainer.value).setView([30.5728, 104.0668], 11) // 默认成都
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
  }
})

/** 在地图上标记景点 */
function plotActivities(activities: Activity[]) {
  // 清除旧标记
  markers.forEach(m => m.remove())
  markers.length = 0

  if (!map || activities.length === 0) return

  const bounds: L.LatLngBounds = L.latLngBounds([])

  for (const act of activities) {
    const latlng = L.latLng(act.location.lat, act.location.lng)
    const marker = L.marker(latlng)
      .addTo(map)
      .bindPopup(`<b>${act.name}</b><br/>${act.description}<br/>¥${act.cost}`)
    markers.push(marker)
    bounds.extend(latlng)
  }

  if (bounds.isValid()) {
    map.fitBounds(bounds, { padding: [50, 50] })
  }
}

// 暴露给父组件调用
defineExpose({ plotActivities })
</script>

<template>
  <div ref="mapContainer" class="map-view"></div>
</template>

<style scoped>
.map-view {
  width: 100%;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  background: #e8eaed;
}
</style>

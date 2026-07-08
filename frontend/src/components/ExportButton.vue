<script setup lang="ts">
import html2canvas from 'html2canvas'

async function exportCard() {
  const cardEl = document.querySelector('.itinerary-card')
  if (!cardEl) return

  const canvas = await html2canvas(cardEl as HTMLElement, {
    backgroundColor: '#0f1117',
    scale: 2,
  })

  const link = document.createElement('a')
  link.download = `itinerary-${Date.now()}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}
</script>

<template>
  <button class="export-btn" @click="exportCard">
    📸 导出行程卡片
  </button>
</template>

<style scoped>
.export-btn {
  padding: 8px 16px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.export-btn:hover {
  background: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
}
</style>

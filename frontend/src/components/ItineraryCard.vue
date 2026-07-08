<script setup lang="ts">
import type { ItineraryResult } from '@/types'

defineProps<{
  itinerary: ItineraryResult | null
}>()
</script>

<template>
  <div v-if="itinerary" class="itinerary-card">
    <div class="card-header">
      <h2>{{ itinerary.destination }} {{ itinerary.duration }}日行程</h2>
      <div class="total-budget">总预算: ¥{{ itinerary.total_budget }}</div>
    </div>

    <div class="tips-section">
      <span v-for="tip in itinerary.tips" :key="tip" class="tip-tag">{{ tip }}</span>
    </div>

    <div class="daily-plans">
      <div v-for="day in itinerary.daily_plans" :key="day.day" class="day-card">
        <div class="day-header">
          <span class="day-num">Day {{ day.day }}</span>
          <span class="day-date">{{ day.date }}</span>
        </div>

        <div class="activities-list">
          <div v-for="act in day.activities" :key="act.name" class="activity-item">
            <div class="act-name">{{ act.name }}</div>
            <div class="act-desc">{{ act.description }}</div>
            <div class="act-meta">
              <span>{{ act.duration_hours }}h</span>
              <span>¥{{ act.cost }}</span>
              <span class="act-loc">{{ act.location.address }}</span>
            </div>
          </div>
        </div>

        <div class="day-logistics">
          <div v-if="day.transport" class="logistics-item">🚗 交通: {{ day.transport }}</div>
          <div v-if="day.hotel_name" class="logistics-item">🏨 酒店: {{ day.hotel_name }}</div>
          <div v-if="day.restaurant_names.length > 0" class="logistics-item">
            🍜 餐饮: {{ day.restaurant_names.join(', ') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.itinerary-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  padding: 20px;
  animation: fadeIn 0.3s ease-out;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-header h2 {
  font-size: 20px;
  color: var(--text-primary);
}

.total-budget {
  font-size: 16px;
  color: var(--accent-color);
  font-weight: 600;
}

.tips-section {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.tip-tag {
  font-size: 12px;
  background: var(--accent-color-light);
  color: var(--accent-color);
  padding: 4px 10px;
  border-radius: 6px;
}

.daily-plans {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.day-card {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.day-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.day-num {
  font-size: 14px;
  color: var(--accent-color);
  font-weight: 600;
}

.day-date {
  font-size: 13px;
  color: var(--text-secondary);
}

.activities-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.activity-item {
  padding: 8px;
  background: var(--bg-primary);
  border-radius: 6px;
}

.act-name {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.act-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.act-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.act-loc {
  color: var(--accent-color);
}

.day-logistics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

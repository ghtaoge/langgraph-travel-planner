<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores'
import type { Plan } from '@/types'

const chatStore = useChatStore()
const manualInput = ref('')

function selectPlan(plan: Plan) {
  chatStore.sendResume({ selected_plan_id: plan.plan_id })
}

function submitManual() {
  chatStore.sendResume({ selected_plan_id: Number(manualInput.value) })
  manualInput.value = ''
}
</script>

<template>
  <div v-if="chatStore.hasInterrupt && chatStore.interruptNode === 'user_select'" class="plan-selector">
    <div class="selector-header">
      <h3>🎯 请选择行程方案</h3>
      <p class="selector-desc">{{ chatStore.interruptQuestion }}</p>
    </div>

    <div v-if="chatStore.plans.length > 0" class="plan-grid">
      <div v-for="plan in chatStore.plans" :key="plan.plan_id" class="plan-card">
        <div class="card-top">
          <span class="plan-badge">#{{ plan.plan_id }}</span>
          <span class="plan-style-tag">{{ plan.style }}</span>
        </div>
        <h4 class="plan-title">{{ plan.title }}</h4>

        <div class="plan-highlights">
          <span v-for="h in plan.highlights" :key="h" class="highlight-chip">{{ h }}</span>
        </div>

        <div class="plan-overview-section">
          <div v-for="(day, idx) in plan.daily_overview" :key="idx" class="overview-row">
            <span class="overview-day">D{{ idx + 1 }}</span>
            <span class="overview-text">{{ day }}</span>
          </div>
        </div>

        <div class="plan-budget-row">{{ plan.estimated_budget }}</div>

        <button class="select-btn" @click="selectPlan(plan)">选择此方案 →</button>
      </div>
    </div>

    <div v-else class="manual-select">
      <p>请输入选择的方案编号</p>
      <div class="manual-row">
        <input v-model="manualInput" type="number" placeholder="方案编号" min="1" max="3" />
        <button @click="submitManual">确认</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plan-selector {
  padding: 20px 24px;
  background: var(--bg-secondary);
  border-radius: 16px;
  border: 1px solid var(--accent-color);
  animation: fadeIn 0.3s ease-out;
  margin: 0 24px 8px;
}
.selector-header h3 { font-size: 17px; color: var(--text-primary); margin-bottom: 4px; }
.selector-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; }

.plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.plan-card {
  background: var(--bg-tertiary);
  padding: 18px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}
.plan-card:hover { border-color: var(--accent-color); transform: translateY(-2px); }

.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.plan-badge {
  font-size: 13px;
  color: var(--accent-color);
  font-weight: 700;
  background: var(--accent-color-light);
  padding: 3px 10px;
  border-radius: 6px;
}
.plan-style-tag {
  font-size: 12px;
  background: rgba(245,158,11,0.12);
  padding: 3px 10px;
  border-radius: 6px;
  color: #f59e0b;
}

.plan-title { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; line-height: 1.4; }

.plan-highlights { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
.highlight-chip {
  font-size: 11px;
  background: var(--bg-primary);
  padding: 3px 8px;
  border-radius: 6px;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.plan-overview-section { margin-bottom: 10px; }
.overview-row { font-size: 12px; display: flex; gap: 8px; padding: 3px 0; color: var(--text-secondary); }
.overview-day { color: var(--accent-color); font-weight: 600; min-width: 24px; }
.overview-text { color: var(--text-tertiary); line-height: 1.5; }

.plan-budget-row { font-size: 15px; color: #f59e0b; font-weight: 600; margin-bottom: 14px; }

.select-btn {
  width: 100%;
  padding: 10px;
  background: var(--accent-color);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}
.select-btn:hover { background: #4f46e5; }

.manual-select { padding: 12px; }
.manual-select p { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.manual-row { display: flex; gap: 8px; }
.manual-row input { flex: 1; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-primary); color: var(--text-primary); font-size: 14px; }
.manual-row button { padding: 8px 16px; background: var(--accent-color); color: white; border: none; border-radius: 8px; cursor: pointer; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>

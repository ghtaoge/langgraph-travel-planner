<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores'

const chatStore = useChatStore()
const commentInput = ref('')

const isDailyConfirm = computed(() => chatStore.interruptNode === 'itinerary_refine')
const isUserApprove = computed(() => chatStore.interruptNode === 'user_approve')
const title = computed(() => isDailyConfirm.value ? '逐日行程确认' : '行程审批确认')

const itinerary = computed(() => {
  const d = chatStore.approveData
  if (!d) return null
  if (d.itinerary && typeof d.itinerary === 'object') return d.itinerary as any
  return null
})

const budget = computed(() => {
  const d = chatStore.approveData
  if (!d || !d.budget) return null
  return d.budget as any
})

const dailyPlans = computed(() => {
  const d = chatStore.approveData
  if (!d) return []
  if (d.daily_plans && Array.isArray(d.daily_plans)) return d.daily_plans as any[]
  if (d.itinerary && (d.itinerary as any).daily_plans) return (d.itinerary as any).daily_plans as any[]
  return []
})

const providerWarnings = computed(() => {
  const warnings = chatStore.approveData?.provider_warnings
  return Array.isArray(warnings) ? warnings.map(String) : []
})

function routeSummary(day: any): string {
  const legs = Array.isArray(day.route_legs) ? day.route_legs : []
  const distance = legs.reduce((total: number, leg: any) => total + Number(leg.distance_m || 0), 0)
  const duration = legs.reduce((total: number, leg: any) => total + Number(leg.duration_s || 0), 0)
  if (!legs.length) return ''
  return `步行 ${(distance / 1000).toFixed(1)}km · ${Math.round(duration / 60)}分钟`
}

function approve() { chatStore.sendResume({ approval_status: 'approved', approval_comment: '' }) }
function reject() {
  chatStore.sendResume({ approval_status: 'rejected', approval_comment: commentInput.value || '需要调整' })
  commentInput.value = ''
}
</script>

<template>
  <div v-if="chatStore.hasInterrupt && (isDailyConfirm || isUserApprove)" class="approval-dialog">
    <!-- 头部 -->
    <div class="dialog-header">
      <div class="header-icon">{{ isDailyConfirm ? '📅' : '✅' }}</div>
      <div>
        <h3>{{ title }}</h3>
        <p class="dialog-desc">{{ chatStore.interruptQuestion }}</p>
      </div>
    </div>

    <!-- 行程标题 -->
    <div v-if="itinerary" class="itinerary-title-card">
      <div class="itinerary-name">{{ itinerary.destination }}</div>
      <div class="itinerary-meta">{{ itinerary.duration }}天行程 · {{ budget?.total_budget || '0' }}元预算</div>
    </div>

    <!-- 每日行程卡片 -->
    <div v-if="dailyPlans.length > 0" class="days-container">
      <div v-for="day in dailyPlans" :key="day.day" class="day-card">
        <div class="day-badge">Day {{ day.day }}</div>
        <div class="day-date">{{ day.date }}</div>

        <!-- 活动 -->
        <div v-if="day.activities && day.activities.length > 0" class="activities">
          <div v-for="act in day.activities" :key="act.name" class="act-row">
            <div class="act-dot"></div>
            <div class="act-content">
              <div class="act-top">
                <span class="act-name">{{ act.name }}</span>
                <span v-if="act.time" class="act-time">{{ act.time }}</span>
                <span v-if="act.cost" class="act-price">{{ act.cost }}元</span>
              </div>
              <div v-if="act.description" class="act-desc">{{ act.description }}</div>
            </div>
          </div>
        </div>
        <div v-else class="act-empty">行程安排待细化</div>

        <!-- 住宿 / 餐饮 / 交通 -->
        <div class="day-info-tags">
          <span v-if="day.weather" class="info-tag tag-weather">
            {{ day.weather.day_weather }} {{ day.weather.day_temp_c ?? '' }}°C
          </span>
          <span v-if="routeSummary(day)" class="info-tag tag-route">{{ routeSummary(day) }}</span>
          <span v-if="day.hotel_name" class="info-tag tag-hotel">🏨 {{ day.hotel_name }}</span>
          <span v-if="day.restaurant_names && day.restaurant_names.length > 0" class="info-tag tag-food">🍜 {{ day.restaurant_names.join('、') }}</span>
          <span v-if="day.transport" class="info-tag tag-trans">🚗 {{ day.transport }}</span>
        </div>
      </div>
    </div>

    <!-- 预算卡片 -->
    <div v-if="budget" class="budget-card">
      <div class="budget-header">
        <span>💰 预算明细</span>
        <span class="budget-total-num">{{ budget.total_budget }}元</span>
      </div>
      <div class="budget-bars">
        <div v-if="budget.accommodation_cost" class="budget-bar-row">
          <span class="bar-label">住宿</span>
          <div class="bar-track"><div class="bar-fill bar-fill-hotel" :style="{ width: Math.min(budget.accommodation_cost / budget.total_budget * 100, 100) + '%' }"></div></div>
          <span class="bar-amount">{{ budget.accommodation_cost }}元</span>
        </div>
        <div v-if="budget.food_cost" class="budget-bar-row">
          <span class="bar-label">餐饮</span>
          <div class="bar-track"><div class="bar-fill bar-fill-food" :style="{ width: Math.min(budget.food_cost / budget.total_budget * 100, 100) + '%' }"></div></div>
          <span class="bar-amount">{{ budget.food_cost }}元</span>
        </div>
        <div v-if="budget.transport_cost" class="budget-bar-row">
          <span class="bar-label">交通</span>
          <div class="bar-track"><div class="bar-fill bar-fill-trans" :style="{ width: Math.min(budget.transport_cost / budget.total_budget * 100, 100) + '%' }"></div></div>
          <span class="bar-amount">{{ budget.transport_cost }}元</span>
        </div>
        <div v-if="budget.activity_cost" class="budget-bar-row">
          <span class="bar-label">活动</span>
          <div class="bar-track"><div class="bar-fill bar-fill-act" :style="{ width: Math.min(budget.activity_cost / budget.total_budget * 100, 100) + '%' }"></div></div>
          <span class="bar-amount">{{ budget.activity_cost }}元</span>
        </div>
      </div>
    </div>

    <!-- 提示 -->
    <div v-if="itinerary && itinerary.tips && itinerary.tips.length > 0" class="tips-row">
      <span v-for="tip in itinerary.tips" :key="tip" class="tip-chip">💡 {{ tip }}</span>
    </div>

    <div v-if="providerWarnings.length" class="provider-warnings">
      <div v-for="warning in providerWarnings" :key="warning" class="warning-row">{{ warning }}</div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <button class="btn-approve" @click="approve">{{ isDailyConfirm ? '✅ 确认行程' : '✅ 批准行程' }}</button>
      <button class="btn-reject" @click="reject">❌ 需要调整</button>
    </div>
    <div class="comment-row">
      <input v-model="commentInput" placeholder="输入修改意见，如：价格贵了、想换景点..." class="comment-input" />
    </div>
  </div>
</template>

<style scoped>
.approval-dialog {
  padding: 20px 24px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid rgba(245,158,11,0.4);
  animation: fadeIn 0.3s ease-out;
  margin: 0 24px 8px;
  /* 审批数据可能包含多天行程和大量活动，不能让卡片无限增高挤出聊天区域。 */
  max-height: min(70vh, 720px);
  /* 长内容在审批卡片内部滚动，底部操作区通过 sticky 保持可见。 */
  overflow-y: auto;
  /* 预留滚动条空间，避免内容高度刚好溢出时左右抖动。 */
  scrollbar-gutter: stable;
}

.approval-dialog::-webkit-scrollbar { width: 8px; }
.approval-dialog::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 8px; }

.dialog-header { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.header-icon { font-size: 28px; }
.dialog-header h3 { font-size: 17px; color: var(--text-primary); margin-bottom: 2px; }
.dialog-desc { font-size: 13px; color: var(--text-secondary); }

/* ── 行程标题卡片 ── */
.itinerary-title-card {
  background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(245,158,11,0.1));
  padding: 14px 18px;
  border-radius: 12px;
  margin-bottom: 14px;
  border: 1px solid rgba(99,102,241,0.15);
}
.itinerary-name { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.itinerary-meta { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

/* ── 每日行程卡片 ── */
.days-container { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }

.day-card {
  background: var(--bg-tertiary);
  padding: 14px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
}
.day-badge {
  font-size: 12px; color: var(--accent-color); font-weight: 700;
  background: var(--accent-color-light); padding: 2px 10px; border-radius: 6px;
  display: inline-block; margin-right: 6px;
}
.day-date { font-size: 13px; color: var(--text-secondary); margin-bottom: 10px; }

.activities { display: flex; flex-direction: column; gap: 8px; }
.act-row { display: flex; gap: 10px; }
.act-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent-color); margin-top: 6px; flex-shrink: 0; }
.act-content { flex: 1; }
.act-top { display: flex; gap: 8px; align-items: baseline; }
.act-name { font-size: 14px; color: var(--text-primary); font-weight: 600; }
.act-time { font-size: 12px; color: var(--text-tertiary); }
.act-price { font-size: 12px; color: #f59e0b; font-weight: 500; }
.act-desc { font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin-top: 2px; }
.act-empty { font-size: 13px; color: var(--text-tertiary); padding: 4px 0; }

.day-info-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.info-tag { font-size: 12px; padding: 4px 10px; border-radius: 6px; }
.tag-hotel { background: rgba(99,102,241,0.12); color: #6366f1; }
.tag-food { background: rgba(245,158,11,0.12); color: #f59e0b; }
.tag-trans { background: rgba(34,197,94,0.12); color: #22c55e; }
.tag-weather { background: rgba(14,165,233,0.12); color: #0284c7; }
.tag-route { background: rgba(20,184,166,0.12); color: #0f766e; }

/* ── 预算卡片 ── */
.budget-card {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  margin-bottom: 14px;
}
.budget-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.budget-header span { font-size: 15px; color: var(--text-primary); font-weight: 600; }
.budget-total-num { font-size: 18px; color: #f59e0b; font-weight: 700; }

.budget-bars { display: flex; flex-direction: column; gap: 8px; }
.budget-bar-row { display: flex; align-items: center; gap: 8px; }
.bar-label { font-size: 12px; color: var(--text-secondary); min-width: 36px; }
.bar-track { flex: 1; height: 8px; background: var(--bg-primary); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s; min-width: 4px; }
.bar-fill-hotel { background: #6366f1; }
.bar-fill-food { background: #f59e0b; }
.bar-fill-trans { background: #22c55e; }
.bar-fill-act { background: #ef4444; }
.bar-amount { font-size: 12px; color: var(--text-secondary); min-width: 60px; text-align: right; }

/* ── 提示 ── */
.tips-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.tip-chip { font-size: 12px; color: var(--text-tertiary); background: var(--bg-tertiary); padding: 4px 10px; border-radius: 6px; }

.provider-warnings {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-left: 3px solid #f59e0b;
  background: rgba(245,158,11,0.1);
}
.warning-row { font-size: 12px; color: var(--text-secondary); line-height: 1.6; }

/* ── 操作 ── */
.action-bar {
  /* 按钮必须始终可点：当行程内容滚动时，操作区吸附在卡片底部输入框上方。 */
  position: sticky;
  bottom: 54px;
  z-index: 2;
  display: flex;
  gap: 12px;
  margin: 0 -24px;
  padding: 12px 24px 10px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}
.btn-approve {
  padding: 12px 28px; background: #22c55e; color: white; border: none; border-radius: 10px;
  cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.2s;
}
.btn-approve:hover { background: #16a34a; transform: translateY(-1px); }
.btn-reject {
  padding: 12px 28px; background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3);
  border-radius: 10px; cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.2s;
}
.btn-reject:hover { background: rgba(239,68,68,0.25); transform: translateY(-1px); }

.comment-row {
  /* 修改意见输入框固定在审批卡片最底部，避免被长行程内容推到不可见区域。 */
  position: sticky;
  bottom: 0;
  z-index: 2;
  margin: 0 -24px -20px;
  padding: 0 24px 16px;
  background: var(--bg-secondary);
}
.comment-input {
  width: 100%; padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 10px;
  background: var(--bg-primary); color: var(--text-primary); font-size: 14px;
  transition: border-color 0.2s;
}
.comment-input:focus { border-color: var(--accent-color); outline: none; }

@media (max-width: 640px) {
  .approval-dialog {
    margin: 0 12px 8px;
    padding: 16px;
    /* 移动端视口更窄，保留略高的可视比例，同时仍限制在屏幕内。 */
    max-height: min(72vh, 640px);
  }

  .action-bar {
    bottom: 54px;
    margin: 0 -16px;
    padding: 12px 16px 10px;
  }

  .comment-row {
    margin: 0 -16px -16px;
    padding: 0 16px 14px;
  }

  .btn-approve,
  .btn-reject {
    flex: 1;
    padding: 11px 12px;
    white-space: nowrap;
  }
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>

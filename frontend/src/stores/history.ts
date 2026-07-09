/** Checkpoint timeline store */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { CheckpointState } from '@/types'

export const useHistoryStore = defineStore('history', () => {
  const checkpointTimeline = ref<CheckpointState[]>([])

  async function loadTimeline(threadId: string) {
    if (!threadId) {
      checkpointTimeline.value = []
      return
    }

    checkpointTimeline.value = []
  }

  return {
    checkpointTimeline,
    loadTimeline,
  }
})
<script setup lang="ts">
import { computed } from 'vue'

const langsmithUrl = computed(() => {
  const apiKey = import.meta.env.VITE_LANGSMITH_API_KEY
  const project = import.meta.env.VITE_LANGSMITH_PROJECT || 'langgraph-travel-planner'
  if (!apiKey) return null
  return `https://smith.langchain.com/o/default/projects/${project}`
})
</script>

<template>
  <a v-if="langsmithUrl" :href="langsmithUrl" target="_blank" class="trace-link">
    🔗 LangSmith Trace
  </a>
</template>

<style scoped>
.trace-link {
  display: inline-flex;
  padding: 4px 10px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: 4px;
  font-size: 12px;
  text-decoration: none;
  transition: background 0.2s;
}

.trace-link:hover {
  background: var(--accent-color-light);
  color: var(--accent-color);
}
</style>

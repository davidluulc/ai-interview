<template>
  <aside class="context-panel">
    <section>
      <p class="eyebrow">Agent Decision</p>
      <h2>为什么这样问</h2>
      <p>{{ decisionSummary || "开始面试后，这里会展示 Agent 决策摘要。" }}</p>
    </section>
    <section>
      <p class="eyebrow">RAG Context</p>
      <h2>检索上下文</h2>
      <p v-if="ragReasons.length === 0">Vue3 V1 先展示入口，完整 RAG 命中解释在后续迁移。</p>
      <ul v-else>
        <li v-for="reason in ragReasons" :key="reason">{{ reason }}</li>
      </ul>
    </section>
  </aside>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ decisionSummary: string; ragReasons?: string[] }>(), {
  ragReasons: () => []
});
</script>

<style scoped>
.context-panel {
  display: grid;
  gap: 16px;
}

.context-panel section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-soft);
  padding: 20px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 700;
  margin: 0 0 8px;
}

h2 {
  font-size: 18px;
  margin: 0 0 10px;
}

p,
li {
  color: var(--color-text-muted);
  line-height: 1.65;
}

ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}
</style>

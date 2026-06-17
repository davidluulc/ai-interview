<template>
  <aside class="evidence-panel">
    <section>
      <p class="eyebrow">Why this question</p>
      <h2>为什么这样问</h2>
      <p>{{ decisionSummary || "开始面试后，这里会展示面试官的追问依据。" }}</p>
    </section>

    <section>
      <p class="eyebrow">References</p>
      <h2>本题参考资料</h2>
      <ul v-if="ragReasons.length > 0">
        <li v-for="reason in ragReasons" :key="reason">{{ reason }}</li>
      </ul>
      <p v-else>当前问题暂未命中可展示的参考资料。</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  decisionSummary: string;
  ragReasons: string[];
}>();
</script>

<style scoped>
.evidence-panel {
  display: grid;
  gap: 16px;
}

section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: 18px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h2,
p {
  margin: 0;
}

p,
li {
  color: var(--color-text-muted);
  line-height: 1.7;
}

ul {
  margin: 0;
  padding-left: 18px;
}
</style>

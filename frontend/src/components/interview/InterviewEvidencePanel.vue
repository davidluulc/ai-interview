<template>
  <div class="evidence-panel">
    <BrutPanel title="决策摘要">
      <p class="evidence-panel__text">{{ decisionSummary || "开始面试后，这里会展示面试官的追问依据。" }}</p>
    </BrutPanel>

    <BrutPanel title="RAG 命中">
      <ul v-if="ragReasons.length > 0" class="evidence-panel__chunks">
        <li v-for="(reason, index) in ragReasons" :key="`${index}-${reason}`" class="evidence-panel__chunk">
          {{ reason }}
        </li>
      </ul>
      <p v-else class="evidence-panel__text">当前问题暂未命中可展示的参考资料。</p>
    </BrutPanel>
  </div>
</template>

<script setup lang="ts">
import BrutPanel from "@/components/brut/BrutPanel.vue";

defineProps<{
  decisionSummary: string;
  ragReasons: string[];
}>();
</script>

<style scoped>
.evidence-panel {
  display: grid;
  gap: var(--s4);
  font-family: var(--font-ui);
}

.evidence-panel__text {
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
  margin: 0;
  overflow-wrap: anywhere;
}

.evidence-panel__chunks {
  display: grid;
  gap: var(--s2);
  list-style: none;
  margin: 0;
  padding: 0;
}

.evidence-panel__chunk {
  border: var(--line);
  border-radius: 0;
  background: var(--panel-warm);
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  padding: var(--s2) var(--s3);
  overflow-wrap: anywhere;
}
</style>

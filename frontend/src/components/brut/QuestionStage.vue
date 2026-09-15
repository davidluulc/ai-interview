<template>
  <section class="question-stage">
    <span class="question-stage__tag">{{ tag }}</span>
    <p class="question-stage__text">{{ text }}</p>
    <ul v-if="meta.length" class="question-stage__meta">
      <li v-for="item in meta" :key="item" class="question-stage__chip">{{ item }}</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  tag: string;
  text: string;
  meta: string[];
}>();
</script>

<style scoped>
.question-stage {
  position: relative;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-family: var(--font-ui);
  box-shadow: var(--shadow-6);
  padding: var(--s5) var(--s4) var(--s4);
}

.question-stage__tag {
  position: absolute;
  top: -13px;
  left: 16px;
  display: inline-block;
  border: var(--line);
  border-radius: 0;
  background: var(--action);
  color: var(--action-ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
  box-shadow: var(--shadow-3);
}

.question-stage__text {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 800;
  line-height: 1.55;
  max-width: 30em;
}

.question-stage__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s2);
  list-style: none;
  margin: var(--s4) 0 0;
  padding: 0;
}

.question-stage__chip {
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
  box-shadow: var(--shadow-2);
}
</style>

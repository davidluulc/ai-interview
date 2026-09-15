<template>
  <aside class="hazard-banner">
    <span class="hazard-banner__stripe" aria-hidden="true"></span>
    <div class="hazard-banner__content">
      <p class="hazard-banner__title">{{ title }}</p>
      <p class="hazard-banner__detail">{{ detail }}</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  detail: string;
}>();
</script>

<style scoped>
.hazard-banner {
  display: flex;
  align-items: stretch;
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  background: var(--warn);
  color: var(--ink);
  box-shadow: var(--shadow-4);
}

.hazard-banner__stripe {
  flex: none;
  width: 14px;
  background: var(--hazard);
  border-right: 2px solid var(--ink);
}

.hazard-banner__content {
  padding: var(--s3) var(--s4);
  min-width: 0;
}

.hazard-banner__title {
  margin: 0;
  font-size: var(--text-strong);
  font-weight: 800;
  line-height: 1.2;
}

.hazard-banner__detail {
  margin: var(--s1) 0 0;
  font-size: var(--text-body);
  font-weight: 800;
  line-height: 1.4;
}
</style>

<template>
  <AppLayout>
    <section class="page">
      <p class="eyebrow">Training</p>
      <h1>训练中心</h1>
      <p>Vue3 V1 先保留训练中心入口，后续迁移 weakTag 专项训练。</p>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from "@/layouts/AppLayout.vue";
</script>

<style scoped>
.page {
  max-width: 960px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h1 {
  font-size: 40px;
  margin: 0 0 12px;
}

p {
  color: var(--color-text-muted);
}
</style>

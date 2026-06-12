<template>
  <AppLayout>
    <section class="page">
      <p class="eyebrow">Settings</p>
      <h1>设置</h1>
      <p>Vue3 V1 先保留设置入口，后续接入用户偏好和运行模式。</p>
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

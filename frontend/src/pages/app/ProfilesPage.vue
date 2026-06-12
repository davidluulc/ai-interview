<template>
  <AppLayout>
    <section class="page">
      <p class="eyebrow">Application Profiles</p>
      <h1>投递档案</h1>
      <p>Vue3 V1 会先迁移档案入口，用于连接简历、岗位 JD 和面试训练台。</p>
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

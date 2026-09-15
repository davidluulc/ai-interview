<template>
  <AppLayout>
    <section class="page">
      <h1>设置</h1>
      <p class="note">Vue3 V1 先保留设置入口，后续接入用户偏好和运行模式。</p>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from "@/layouts/AppLayout.vue";
</script>

<style scoped>
.page {
  max-width: 960px;
  min-width: 0;
  font-family: var(--font-ui);
  color: var(--ink);
}

h1 {
  margin: 0 0 var(--s4);
  font-size: var(--text-page);
  font-weight: 900;
  line-height: 1.1;
}

/* T3 工具级占位说明：墨色虚线框，不加投影。 */
.note {
  max-width: 72ch;
  border: 2px dashed var(--ink);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
  padding: var(--s4);
}
</style>

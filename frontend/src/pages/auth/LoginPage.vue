<template>
  <AuthLayout>
    <p class="eyebrow">AI Interview</p>
    <h1>欢迎回来</h1>
    <p class="muted">登录页将在 V1 的下一步接入真实认证。</p>
  </AuthLayout>
</template>

<script setup lang="ts">
import AuthLayout from "@/layouts/AuthLayout.vue";
</script>

<style scoped>
.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
  text-align: center;
}

h1 {
  font-size: 34px;
  margin: 0;
  text-align: center;
}

.muted {
  color: var(--color-text-muted);
  margin: 12px 0 0;
  text-align: center;
}
</style>

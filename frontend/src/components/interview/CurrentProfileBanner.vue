<template>
  <section class="profile-banner">
    <div>
      <p class="eyebrow">当前面试档案</p>
      <h2>{{ profile.title }}</h2>
      <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }} · {{ profile.company || "未填写公司" }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ApplicationProfile } from "@/api/profiles";

defineProps<{ profile: ApplicationProfile }>();
</script>

<style scoped>
.profile-banner {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: 18px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 6px;
}

h2,
p {
  margin: 0;
}

p:last-child {
  color: var(--color-text-muted);
  margin-top: 6px;
}
</style>

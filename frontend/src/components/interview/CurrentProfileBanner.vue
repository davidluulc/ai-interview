<template>
  <section class="profile-banner">
    <span class="profile-banner__label">当前面试档案</span>
    <strong class="profile-banner__title">{{ profile.title }}</strong>
    <span class="profile-banner__meta">
      {{ profile.targetRole || profile.target_role || "未填写目标岗位" }} · {{ profile.company || "未填写公司" }}
    </span>
  </section>
</template>

<script setup lang="ts">
import type { ApplicationProfile } from "@/api/profiles";

defineProps<{ profile: ApplicationProfile }>();
</script>

<style scoped>
.profile-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--s2) var(--s3);
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  box-shadow: var(--shadow-2);
  font-family: var(--font-ui);
  padding: var(--s2) var(--s3);
}

.profile-banner__label {
  border: 2px solid var(--ink);
  border-radius: 0;
  background: var(--action);
  color: var(--action-ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
  padding: var(--s1) var(--s2);
  text-transform: uppercase;
}

.profile-banner__title {
  color: var(--ink);
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
}

.profile-banner__meta {
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.4;
}

@media (max-width: 760px) {
  .profile-banner {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

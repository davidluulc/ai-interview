<template>
  <section class="profile-list" aria-label="投递档案列表">
    <div class="list-head">
      <h2>已有档案</h2>
      <span>{{ profiles.length }} 个</span>
    </div>

    <p v-if="loading && profiles.length === 0" class="empty">正在加载档案...</p>
    <div v-else-if="profiles.length === 0" class="empty-state">
      <h3>还没有投递档案</h3>
      <p>先创建一个档案，AI 面试官会结合简历、岗位 JD 和公司信息生成问题。</p>
    </div>

    <article
      v-for="profile in profiles"
      :key="profile.id"
      :class="['profile-card', { active: currentProfileId === profile.id }]"
    >
      <div>
        <h3>{{ profile.title }}</h3>
        <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }}</p>
        <small>{{ profile.company || "未填写公司" }}</small>
      </div>
      <div class="actions">
        <button type="button" @click="$emit('select', profile.id)">
          {{ currentProfileId === profile.id ? "当前档案" : "设为当前" }}
        </button>
        <button
          class="primary"
          type="button"
          :data-testid="`start-profile-${profile.id}`"
          @click="$emit('start', profile.id)"
        >
          开始面试
        </button>
        <button
          class="ghost"
          type="button"
          :data-testid="`archive-profile-${profile.id}`"
          @click="$emit('archive', profile.id)"
        >
          归档
        </button>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import type { ApplicationProfile } from "@/api/profiles";

defineProps<{
  profiles: ApplicationProfile[];
  currentProfileId: number | null;
  loading: boolean;
}>();

defineEmits<{
  select: [id: number];
  start: [id: number];
  archive: [id: number];
}>();
</script>

<style scoped>
.profile-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.list-head,
.profile-card,
.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.list-head,
.profile-card {
  justify-content: space-between;
}

.list-head {
  margin-bottom: 16px;
}

h2,
h3,
p {
  margin: 0;
}

.list-head span,
.profile-card p,
.empty,
small {
  color: var(--color-text-muted);
}

.empty-state {
  display: grid;
  gap: 8px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  padding: 22px;
}

.profile-card {
  border-top: 1px solid var(--color-border);
  padding: 16px 0;
}

.profile-card.active h3 {
  color: var(--color-accent);
}

button {
  white-space: nowrap;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  padding: 8px 12px;
}

button.primary {
  border-color: var(--color-accent);
  background: var(--color-accent);
  color: white;
}

button.ghost {
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
}

@media (max-width: 720px) {
  .profile-card,
  .actions {
    align-items: stretch;
    flex-direction: column;
  }

  .actions,
  .actions button {
    width: 100%;
  }
}
</style>

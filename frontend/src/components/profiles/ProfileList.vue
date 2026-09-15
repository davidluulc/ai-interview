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

    <template v-else>
      <article
        v-for="profile in profiles"
        :key="profile.id"
        :class="['profile-card', { active: currentProfileId === profile.id }]"
      >
        <div class="profile-card__main">
          <h3>{{ profile.title }}</h3>
          <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }}</p>
          <small>{{ profile.company || "未填写公司" }}</small>
        </div>
        <div class="actions">
          <BrutButton variant="ghost" type="button" @click="$emit('select', profile.id)">
            {{ currentProfileId === profile.id ? "当前档案" : "设为当前" }}
          </BrutButton>
          <BrutButton
            variant="primary"
            type="button"
            :data-testid="`start-profile-${profile.id}`"
            @click="$emit('start', profile.id)"
          >
            开始面试
          </BrutButton>
          <BrutButton
            variant="ghost"
            type="button"
            :data-testid="`archive-profile-${profile.id}`"
            @click="$emit('archive', profile.id)"
          >
            归档
          </BrutButton>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import type { ApplicationProfile } from "@/api/profiles";
import BrutButton from "@/components/brut/BrutButton.vue";

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
  display: grid;
  gap: var(--s3);
  font-family: var(--font-ui);
  color: var(--ink);
}

.list-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s3);
}

.list-head h2 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.2;
}

.list-head span {
  color: var(--ink-soft);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.empty {
  margin: 0;
  width: fit-content;
  border: 2px dashed var(--ink);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s4);
}

.empty-state {
  display: grid;
  gap: var(--s2);
  border: 2px dashed var(--ink);
  background: var(--panel);
  padding: var(--s5);
}

.empty-state h3 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
}

.empty-state p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

/* T2 行卡：2px 墨边白底装框，不加投影（投影仅交互元素，如按钮）。 */
.profile-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s4);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

/* 激活项沿用侧边栏 router-link-active 同款 --warn 黄底约定。 */
.profile-card.active {
  background: var(--warn);
}

.profile-card__main {
  display: grid;
  gap: var(--s1);
  min-width: 0;
}

.profile-card h3 {
  margin: 0;
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.profile-card p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.5;
}

.profile-card small {
  color: var(--ink-soft);
  font-size: var(--text-data);
  font-weight: 800;
  line-height: 1.4;
}

.actions {
  display: flex;
  align-items: center;
  gap: var(--s2);
}

@media (max-width: 720px) {
  .profile-card {
    flex-direction: column;
    align-items: stretch;
  }

  .actions {
    justify-content: stretch;
  }

  .actions :deep(.brut-button) {
    flex: 1;
  }
}
</style>

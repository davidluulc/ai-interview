<template>
  <section class="current-card">
    <div>
      <p class="eyebrow">当前档案</p>
      <h2>{{ profile.title }}</h2>
      <p class="meta">{{ roleText }} · {{ companyText }}</p>
    </div>

    <dl class="readiness">
      <div>
        <dt>岗位 JD</dt>
        <dd>{{ profile.jd ? "已填写" : "未填写" }}</dd>
      </div>
      <div>
        <dt>简历概况</dt>
        <dd>{{ profile.resume ? "已填写" : "未填写" }}</dd>
      </div>
    </dl>

    <button type="button" @click="$emit('start', profile.id)">开始面试</button>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ApplicationProfile } from "@/api/profiles";

const props = defineProps<{ profile: ApplicationProfile }>();
defineEmits<{ start: [id: number] }>();

const roleText = computed(() => props.profile.targetRole || props.profile.target_role || "未填写目标岗位");
const companyText = computed(() => props.profile.company || "未填写公司");
</script>

<style scoped>
.current-card {
  display: grid;
  gap: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
  padding: 24px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h2,
p,
dl,
dd {
  margin: 0;
}

.meta,
dt {
  color: var(--color-text-muted);
}

.readiness {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.readiness div {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  padding: 12px;
}

dt {
  font-size: 13px;
}

dd {
  font-weight: 700;
  margin-top: 4px;
}

button {
  width: fit-content;
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: white;
  cursor: pointer;
  font-weight: 700;
  padding: 11px 18px;
}

@media (max-width: 640px) {
  .readiness {
    grid-template-columns: 1fr;
  }
}
</style>

<template>
  <BrutPanel class="identity-card" title="当前档案">
    <div class="identity-head">
      <h2>{{ profile.title }}</h2>
      <BrutButton variant="primary" type="button" @click="$emit('start', profile.id)">
        开始面试
      </BrutButton>
    </div>

    <dl class="identity-facts">
      <div class="identity-facts__item">
        <dt>目标岗位</dt>
        <dd>{{ roleText }}</dd>
      </div>
      <div class="identity-facts__item">
        <dt>目标公司</dt>
        <dd>{{ companyText }}</dd>
      </div>
      <div class="identity-facts__item">
        <dt>岗位 JD</dt>
        <dd>{{ profile.jd ? "已填写" : "未填写" }}</dd>
      </div>
      <div class="identity-facts__item">
        <dt>简历概况</dt>
        <dd>{{ profile.resume ? "已填写" : "未填写" }}</dd>
      </div>
    </dl>
  </BrutPanel>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ApplicationProfile } from "@/api/profiles";
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutPanel from "@/components/brut/BrutPanel.vue";

const props = defineProps<{ profile: ApplicationProfile }>();
defineEmits<{ start: [id: number] }>();

const roleText = computed(() => props.profile.targetRole || props.profile.target_role || "未填写目标岗位");
const companyText = computed(() => props.profile.company || "未填写公司");
</script>

<style scoped>
/* “当前”是身份标记而非语义状态，按 T2 规格用 --action 蓝头标识激活档案。 */
.identity-card :deep(.brut-panel__head) {
  background: var(--action);
}

.identity-card :deep(.brut-panel__title) {
  color: var(--action-ink);
}

.identity-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s4);
}

.identity-head h2 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

/* 身份字段格：真实数据装框，静态信息不加投影（投影仅交互元素）。 */
.identity-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--s3);
  margin: var(--s4) 0 0;
}

.identity-facts__item {
  border: var(--line);
  background: var(--panel);
  padding: var(--s3);
}

.identity-facts dt {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.identity-facts dd {
  margin: var(--s1) 0 0;
  color: var(--ink);
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

@media (max-width: 860px) {
  .identity-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .identity-head {
    flex-direction: column;
  }

  .identity-facts {
    grid-template-columns: 1fr;
  }
}
</style>

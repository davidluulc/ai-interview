<template>
  <div class="brut-empty">
    <header class="brut-empty__head">
      <span class="brut-empty__title">{{ title }}</span>
    </header>
    <div class="brut-empty__body">
      <BrutButton variant="ghost" @click="$emit('action')">
        {{ actionLabel }}
      </BrutButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import BrutButton from "./BrutButton.vue";

defineProps<{
  actionLabel: string;
  title: string;
}>();

defineEmits<{ action: [] }>();
</script>

<style scoped>
.brut-empty {
  display: flex;
  flex-direction: column;
  border: var(--line);
  border-radius: 0;
  font-family: var(--font-ui);
  box-shadow: var(--shadow-2);
  max-width: 320px;
}

.brut-empty__head {
  background: var(--ink);
  color: var(--paper);
  padding: var(--s2) var(--s3);
}

.brut-empty__title {
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-transform: uppercase;
}

.brut-empty__body {
  display: flex;
  justify-content: center;
  background: var(--panel);
  padding: var(--s4);
}
</style>

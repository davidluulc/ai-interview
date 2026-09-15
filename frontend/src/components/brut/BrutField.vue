<template>
  <label class="brut-field" :class="$attrs.class" :style="$attrs.style">
    <span class="brut-field__label">{{ label }}</span>
    <input
      v-bind="fieldAttrs"
      class="brut-field__input"
      :type="type || 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      @input="onInput"
    />
  </label>
</template>

<script setup lang="ts">
import { computed, useAttrs } from "vue";

defineOptions({ inheritAttrs: false });

defineProps<{
  label: string;
  modelValue: string;
  placeholder?: string;
  type?: string;
}>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const attrs = useAttrs();

const fieldAttrs = computed(() => {
  const rest: Record<string, unknown> = { ...attrs };
  delete rest.class;
  delete rest.style;
  return rest;
});

function onInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
}
</script>

<style scoped>
.brut-field {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  font-family: var(--font-ui);
}

.brut-field__label {
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
  text-transform: uppercase;
}

.brut-field__input {
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-family: inherit;
  font-size: var(--text-body);
  line-height: 1.4;
  padding: var(--s3);
}

.brut-field__input::placeholder {
  color: var(--ink-soft);
}

.brut-field__input:focus {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}
</style>

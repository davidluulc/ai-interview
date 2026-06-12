<template>
  <label class="field">
    <span>{{ label }}</span>
    <input
      :autocomplete="autocomplete"
      :name="name"
      :placeholder="placeholder"
      :required="required"
      :type="type || 'text'"
      :value="modelValue"
      @input="onInput"
    />
  </label>
</template>

<script setup lang="ts">
defineProps<{
  autocomplete?: string;
  label: string;
  modelValue: string;
  name?: string;
  placeholder?: string;
  required?: boolean;
  type?: string;
}>();

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

function onInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
}
</script>

<style scoped>
.field {
  display: grid;
  gap: 8px;
}

.field span {
  color: var(--color-text-muted);
  font-size: 13px;
}

.field input {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  outline: none;
  padding: 13px 14px;
}

.field input:focus {
  border-color: rgba(0, 113, 227, 0.55);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12);
}
</style>

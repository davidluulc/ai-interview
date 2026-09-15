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
  color: var(--ink-soft);
  font-size: 13px;
}

.field input {
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  outline: none;
  padding: 13px 14px;
}

.field input:focus {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}
</style>

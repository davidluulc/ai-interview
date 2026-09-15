<template>
  <section class="answer-box" :class="$attrs.class" :style="$attrs.style">
    <div class="answer-box__head">
      <span class="answer-box__label">你的回答</span>
      <span class="answer-box__hint">{{ hint }}</span>
    </div>
    <textarea
      v-bind="boxAttrs"
      class="answer-box__textarea"
      :value="modelValue"
      :placeholder="placeholder"
      @input="onInput"
      @keydown="onKeydown"
    ></textarea>
  </section>
</template>

<script setup lang="ts">
import { computed, useAttrs } from "vue";

defineOptions({ inheritAttrs: false });

defineProps<{
  modelValue: string;
  placeholder: string;
  hint: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  submit: [];
}>();

const attrs = useAttrs();

const boxAttrs = computed(() => {
  const rest: Record<string, unknown> = { ...attrs };
  delete rest.class;
  delete rest.style;
  return rest;
});

function onInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLTextAreaElement).value);
}

function onKeydown(event: KeyboardEvent): void {
  if (event.isComposing) return;
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    emit("submit");
  }
}
</script>

<style scoped>
.answer-box {
  border: var(--line);
  border-radius: 0;
  background: var(--panel-warm);
  color: var(--ink);
  font-family: var(--font-ui);
  box-shadow: var(--shadow-5);
  padding: var(--s4);
}

.answer-box__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s2);
  margin-bottom: var(--s3);
}

.answer-box__label {
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
  text-transform: uppercase;
}

.answer-box__hint {
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 700;
  line-height: 1.2;
}

.answer-box__textarea {
  display: block;
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font-family: inherit;
  font-size: 12px;
  line-height: 1.8;
  padding: var(--s3);
  resize: vertical;
}

.answer-box__textarea::placeholder {
  color: var(--ink-soft);
}

.answer-box__textarea:focus {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}
</style>

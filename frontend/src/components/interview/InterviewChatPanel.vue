<template>
  <section class="chat-panel">
    <div class="message-list">
      <article v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
        <span>{{ message.role === "interviewer" ? "AI 面试官" : "我" }}</span>
        <p>{{ message.content }}</p>
      </article>
      <article v-if="loading" class="message interviewer thinking" data-testid="interviewer-thinking">
        <span>AI 面试官</span>
        <p>AI 面试官正在分析你的回答，检索岗位知识库和题库...</p>
      </article>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <form class="composer" @submit.prevent="$emit('submit')">
      <textarea v-model="draftProxy" placeholder="输入你的回答..." />
      <button :disabled="loading || canSubmit === false">{{ loading ? "生成中" : "提交回答" }}</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ChatMessage } from "@/stores/interview";

const props = defineProps<{
  messages: ChatMessage[];
  draft: string;
  loading: boolean;
  error?: string;
  canSubmit?: boolean;
}>();
const emit = defineEmits<{ "update:draft": [value: string]; submit: [] }>();

const draftProxy = computed({
  get: () => props.draft,
  set: (value: string) => emit("update:draft", value)
});
</script>

<style scoped>
.chat-panel {
  display: grid;
  min-height: 560px;
  grid-template-rows: 1fr auto auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: var(--shadow-soft);
  overflow: hidden;
}

.message-list {
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 22px;
}

.message {
  max-width: 78%;
}

.message span {
  display: block;
  color: var(--color-text-muted);
  font-size: 12px;
  margin-bottom: 6px;
}

.message p {
  margin: 0;
  border-radius: var(--radius-md);
  padding: 12px 14px;
}

.message.interviewer p {
  background: var(--color-surface);
}

.message.thinking p {
  color: var(--color-text-muted);
}

.message.candidate {
  justify-self: end;
}

.message.candidate p {
  background: var(--color-accent);
  color: #fff;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 112px;
  gap: 12px;
  border-top: 1px solid var(--color-border);
  padding: 16px;
}

.composer textarea {
  min-height: 76px;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  outline: none;
  padding: 12px;
}

.composer button {
  align-self: end;
  min-height: 44px;
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: #fff;
  cursor: pointer;
  font-weight: 600;
}

.composer button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.error {
  color: #b42318;
  margin: 0;
  padding: 0 16px 12px;
}

@media (max-width: 680px) {
  .composer {
    grid-template-columns: 1fr;
  }

  .message {
    max-width: 100%;
  }
}
</style>

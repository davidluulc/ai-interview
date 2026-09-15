<template>
  <AuthLayout>
    <div class="auth-copy">
      <h1>欢迎回来</h1>
      <p>进入你的面试训练工作台。</p>
    </div>

    <form class="auth-form" @submit.prevent="submit">
      <BrutField
        v-model="email"
        autocomplete="email"
        label="邮箱"
        name="email"
        placeholder="student@example.com"
        required
        type="email"
      />
      <BrutField
        v-model="password"
        autocomplete="current-password"
        label="密码"
        name="password"
        placeholder="输入密码"
        required
        type="password"
      />
      <BrutChip v-if="auth.error" class="error-chip" :label="auth.error" tone="danger" />
      <BrutButton :disabled="auth.loading" type="submit" variant="primary">
        {{ auth.loading ? "登录中" : "登录" }}
      </BrutButton>
    </form>

    <p class="switch-text">
      还没有账号？<RouterLink class="switch-link" to="/vue/auth/register">去注册</RouterLink>
    </p>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutChip from "@/components/brut/BrutChip.vue";
import BrutField from "@/components/brut/BrutField.vue";
import AuthLayout from "@/layouts/AuthLayout.vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();
const email = ref("");
const password = ref("");

async function submit(): Promise<void> {
  await auth.login(email.value, password.value);
  await router.replace("/vue/app/interview");
}
</script>

<style scoped>
.auth-copy {
  display: grid;
  gap: var(--s2);
  margin-bottom: var(--s6);
  text-align: center;
}

h1 {
  color: var(--ink);
  font-size: var(--text-page);
  margin: 0;
}

p {
  color: var(--ink-soft);
  margin: 0;
}

.auth-form {
  display: grid;
  gap: var(--s4);
}

.error-chip {
  justify-self: start;
}

.auth-form .brut-button {
  width: 100%;
}

.switch-text {
  margin-top: var(--s4);
  text-align: center;
  font-size: var(--text-body);
}

.switch-link {
  color: var(--action);
  font-weight: 800;
}
</style>

<template>
  <AuthLayout>
    <div class="auth-copy">
      <p class="eyebrow">AI Interview</p>
      <h1>创建账号</h1>
      <p>建立你的面试训练档案。</p>
    </div>

    <form class="auth-form" @submit.prevent="submit">
      <TextField
        v-model="email"
        autocomplete="email"
        label="邮箱"
        name="email"
        placeholder="student@example.com"
        required
        type="email"
      />
      <TextField
        v-model="username"
        autocomplete="username"
        label="用户名"
        name="username"
        placeholder="你的昵称"
        required
      />
      <TextField
        v-model="password"
        autocomplete="new-password"
        label="密码"
        name="password"
        placeholder="至少 8 位"
        required
        type="password"
      />
      <p v-if="auth.error" class="error">{{ auth.error }}</p>
      <PrimaryButton :disabled="auth.loading">{{ auth.loading ? "注册中" : "注册" }}</PrimaryButton>
    </form>

    <RouterLink class="switch-link" to="/vue/auth/login">已有账号？去登录</RouterLink>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import PrimaryButton from "@/components/common/PrimaryButton.vue";
import TextField from "@/components/common/TextField.vue";
import AuthLayout from "@/layouts/AuthLayout.vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();
const email = ref("");
const username = ref("");
const password = ref("");

async function submit(): Promise<void> {
  await auth.register(email.value, username.value, password.value);
  await router.push("/vue/app/interview");
}
</script>

<style scoped>
.auth-copy {
  display: grid;
  gap: 8px;
  margin-bottom: 28px;
  text-align: center;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0;
}

h1 {
  font-size: 34px;
  margin: 0;
}

p {
  color: var(--color-text-muted);
  margin: 0;
}

.auth-form {
  display: grid;
  gap: 16px;
}

.error {
  color: #b42318;
  font-size: 14px;
}

.switch-link {
  display: block;
  margin-top: 18px;
  text-align: center;
  color: var(--color-accent);
  font-size: 14px;
}
</style>

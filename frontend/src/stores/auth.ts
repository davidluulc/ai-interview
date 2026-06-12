import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as authApi from "@/api/auth";
import { clearApiTokens, getAccessToken, setApiTokens } from "@/api/client";

function normalizeToken(value: authApi.AuthResponse): { accessToken: string; refreshToken: string } {
  return {
    accessToken: value.accessToken || value.access_token || "",
    refreshToken: value.refreshToken || value.refresh_token || ""
  };
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<authApi.CurrentUser | null>(null);
  const loading = ref(false);
  const error = ref("");
  const tokenVersion = ref(0);
  const isAuthenticated = computed(() => {
    tokenVersion.value;
    return Boolean(getAccessToken());
  });

  async function applyLoginResponse(response: authApi.AuthResponse): Promise<void> {
    const tokens = normalizeToken(response);
    if (!tokens.accessToken) {
      throw new Error("登录响应缺少 accessToken");
    }

    setApiTokens(tokens);
    tokenVersion.value += 1;
    user.value = response.user || (await authApi.fetchCurrentUser());
  }

  async function login(email: string, password: string): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      await applyLoginResponse(await authApi.login(email, password));
    } catch (err) {
      error.value = err instanceof Error ? err.message : "登录失败";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function register(email: string, username: string, password: string): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      await authApi.register(email, username, password);
      await applyLoginResponse(await authApi.login(email, password));
    } catch (err) {
      error.value = err instanceof Error ? err.message : "注册失败";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function restore(): Promise<void> {
    if (!getAccessToken()) {
      return;
    }

    loading.value = true;
    error.value = "";
    try {
      user.value = await authApi.fetchCurrentUser();
    } catch (err) {
      clearApiTokens();
      tokenVersion.value += 1;
      user.value = null;
      error.value = err instanceof Error ? err.message : "登录状态已失效";
    } finally {
      loading.value = false;
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout();
    } finally {
      clearApiTokens();
      tokenVersion.value += 1;
      user.value = null;
    }
  }

  return { user, loading, error, isAuthenticated, login, register, restore, logout };
});

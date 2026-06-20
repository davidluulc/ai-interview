<template>
  <RouterView />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

function handleAuthRevoked(): void {
  void router.replace("/vue/auth/login");
}

onMounted(() => {
  window.addEventListener("ai-interview-auth-revoked", handleAuthRevoked);
  void auth.restore();
});

onUnmounted(() => {
  window.removeEventListener("ai-interview-auth-revoked", handleAuthRevoked);
});
</script>

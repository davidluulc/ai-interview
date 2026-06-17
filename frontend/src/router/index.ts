import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { ACCESS_TOKEN_KEY } from "@/api/client";

export const routes: RouteRecordRaw[] = [
  { path: "/vue", redirect: "/vue/app/interview" },
  {
    path: "/vue/auth/login",
    component: () => import("@/pages/auth/LoginPage.vue"),
    meta: { public: true }
  },
  {
    path: "/vue/auth/register",
    component: () => import("@/pages/auth/RegisterPage.vue"),
    meta: { public: true }
  },
  {
    path: "/vue/app/interview",
    component: () => import("@/pages/app/InterviewPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/profiles",
    component: () => import("@/pages/app/ProfilesPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/knowledge",
    component: () => import("@/pages/app/KnowledgePage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/history",
    component: () => import("@/pages/app/HistoryPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/reports/:recordId",
    component: () => import("@/pages/app/ReportPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/training",
    component: () => import("@/pages/app/TrainingPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/admin",
    component: () => import("@/pages/app/AdminPage.vue"),
    meta: { requiresAuth: true }
  },
  {
    path: "/vue/app/settings",
    component: () => import("@/pages/app/SettingsPage.vue"),
    meta: { requiresAuth: true }
  },
  { path: "/:pathMatch(.*)*", redirect: "/vue/app/interview" }
];

export function requiresAuth(path: string): boolean {
  const matched = routes.find((route) => route.path === path);
  return Boolean(matched?.meta?.requiresAuth);
}

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to) => {
  const isPublic = Boolean(to.meta.public);
  const hasToken = Boolean(localStorage.getItem(ACCESS_TOKEN_KEY));
  if (!isPublic && !hasToken) {
    return "/vue/auth/login";
  }
  if (isPublic && hasToken) {
    return "/vue/app/interview";
  }
  return true;
});

export default router;

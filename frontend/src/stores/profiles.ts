import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as profileApi from "@/api/profiles";

export const useProfilesStore = defineStore("profiles", () => {
  const profiles = ref<profileApi.ApplicationProfile[]>([]);
  const archivedProfiles = ref<profileApi.ApplicationProfile[]>([]);
  const currentProfileId = ref<number | null>(null);
  const loading = ref(false);
  const error = ref("");
  const currentProfile = computed(
    () => profiles.value.find((item) => item.id === currentProfileId.value) || null
  );

  async function loadProfiles(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      profiles.value = await profileApi.listProfiles("active");
      if (!currentProfileId.value && profiles.value.length > 0) {
        currentProfileId.value = profiles.value[0].id;
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "投递档案加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function loadArchivedProfiles(): Promise<void> {
    try {
      archivedProfiles.value = await profileApi.listProfiles("archived");
    } catch (err) {
      error.value = err instanceof Error ? err.message : "已归档档案加载失败";
    }
  }

  async function createProfile(payload: profileApi.CreateApplicationProfilePayload): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const created = await profileApi.createProfile(payload);
      profiles.value = [created, ...profiles.value];
      currentProfileId.value = created.id;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "投递档案创建失败";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  function selectProfile(id: number): void {
    currentProfileId.value = id;
  }

  async function archiveProfile(id: number): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const archived = await profileApi.archiveProfile(id);
      profiles.value = profiles.value.filter((item) => item.id !== id);
      archivedProfiles.value = [archived, ...archivedProfiles.value.filter((item) => item.id !== id)];
      if (currentProfileId.value === id) {
        currentProfileId.value = profiles.value[0]?.id || null;
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "投递档案归档失败";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function restoreProfile(id: number): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const restored = await profileApi.restoreProfile(id);
      archivedProfiles.value = archivedProfiles.value.filter((item) => item.id !== id);
      profiles.value = [restored, ...profiles.value.filter((item) => item.id !== id)];
      if (!currentProfileId.value) {
        currentProfileId.value = restored.id;
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "投递档案恢复失败";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  return {
    profiles,
    archivedProfiles,
    currentProfileId,
    currentProfile,
    loading,
    error,
    loadProfiles,
    loadArchivedProfiles,
    createProfile,
    selectProfile,
    archiveProfile,
    restoreProfile
  };
});

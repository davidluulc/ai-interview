import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as profileApi from "@/api/profiles";

export const useProfilesStore = defineStore("profiles", () => {
  const profiles = ref<profileApi.ApplicationProfile[]>([]);
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
      profiles.value = await profileApi.listProfiles();
      if (!currentProfileId.value && profiles.value.length > 0) {
        currentProfileId.value = profiles.value[0].id;
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "投递档案加载失败";
    } finally {
      loading.value = false;
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

  return {
    profiles,
    currentProfileId,
    currentProfile,
    loading,
    error,
    loadProfiles,
    createProfile,
    selectProfile
  };
});

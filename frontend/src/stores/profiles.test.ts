import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as profileApi from "@/api/profiles";
import { useProfilesStore } from "./profiles";

vi.mock("@/api/profiles", () => ({
  listProfiles: vi.fn(),
  createProfile: vi.fn(),
  archiveProfile: vi.fn(),
  restoreProfile: vi.fn()
}));

describe("profiles store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(profileApi.listProfiles).mockReset();
    vi.mocked(profileApi.createProfile).mockReset();
    vi.mocked(profileApi.archiveProfile).mockReset();
    vi.mocked(profileApi.restoreProfile).mockReset();
  });

  it("loads profiles and selects the first profile by default", async () => {
    vi.mocked(profileApi.listProfiles).mockResolvedValue([
      {
        id: 1,
        title: "后端实习投递",
        targetRole: "Python 后端开发实习生",
        company: "Example AI"
      }
    ]);

    const store = useProfilesStore();
    await store.loadProfiles();

    expect(store.profiles).toHaveLength(1);
    expect(store.currentProfileId).toBe(1);
    expect(store.currentProfile?.title).toBe("后端实习投递");
  });

  it("creates a profile and selects it", async () => {
    vi.mocked(profileApi.createProfile).mockResolvedValue({
      id: 2,
      title: "AI 应用开发投递",
      targetRole: "AI 应用开发实习生"
    });

    const store = useProfilesStore();
    await store.createProfile({
      title: "AI 应用开发投递",
      targetRole: "AI 应用开发实习生",
      company: "",
      jd: "",
      resume: ""
    });

    expect(store.profiles[0].id).toBe(2);
    expect(store.currentProfileId).toBe(2);
  });

  it("archives the current profile and selects the next active profile", async () => {
    vi.mocked(profileApi.archiveProfile).mockResolvedValue({
      id: 1,
      title: "后端实习投递",
      status: "archived"
    });
    const store = useProfilesStore();
    store.profiles = [
      { id: 1, title: "后端实习投递", status: "active" },
      { id: 2, title: "AI 应用开发投递", status: "active" }
    ];
    store.currentProfileId = 1;

    await store.archiveProfile(1);

    expect(profileApi.archiveProfile).toHaveBeenCalledWith(1);
    expect(store.profiles.map((item) => item.id)).toEqual([2]);
    expect(store.archivedProfiles.map((item) => item.id)).toEqual([1]);
    expect(store.currentProfileId).toBe(2);
  });

  it("restores an archived profile into the active list", async () => {
    vi.mocked(profileApi.restoreProfile).mockResolvedValue({
      id: 1,
      title: "后端实习投递",
      status: "active"
    });
    const store = useProfilesStore();
    store.archivedProfiles = [{ id: 1, title: "后端实习投递", status: "archived" }];

    await store.restoreProfile(1);

    expect(profileApi.restoreProfile).toHaveBeenCalledWith(1);
    expect(store.profiles.map((item) => item.id)).toEqual([1]);
    expect(store.archivedProfiles).toEqual([]);
  });
});

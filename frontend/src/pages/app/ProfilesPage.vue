<template>
  <AppLayout>
    <section class="page-header">
      <p class="eyebrow">Application Profiles</p>
      <h1>投递档案</h1>
      <p>先把简历、岗位 JD 和公司信息沉淀成档案，再进入模拟面试。</p>
    </section>

    <section v-if="profiles.currentProfile" class="current-section">
      <ProfileCurrentCard :profile="profiles.currentProfile" @start="startInterview" />
    </section>

    <section class="profile-workspace">
      <form class="profile-form" @submit.prevent="submit">
        <h2>新建档案</h2>
        <TextField v-model="form.title" label="档案名称" name="title" placeholder="后端实习投递" required />
        <TextField v-model="form.targetRole" label="目标岗位" name="targetRole" placeholder="Python 后端开发实习生" />
        <TextField v-model="form.company" label="目标公司" name="company" placeholder="可先留空" />
        <label class="area-field">
          <span>岗位 JD</span>
          <textarea v-model="form.jd" placeholder="粘贴岗位职责、任职要求、技术栈关键词" />
        </label>
        <label class="area-field">
          <span>简历概况</span>
          <textarea v-model="form.resume" placeholder="先用文本概括简历，后续再接入文件上传" />
        </label>
        <p v-if="profiles.error" class="error">{{ profiles.error }}</p>
        <PrimaryButton :disabled="profiles.loading">{{ profiles.loading ? "保存中" : "保存档案" }}</PrimaryButton>
      </form>

      <ProfileList
        :current-profile-id="profiles.currentProfileId"
        :loading="profiles.loading"
        :profiles="profiles.profiles"
        @archive="profiles.archiveProfile"
        @select="profiles.selectProfile"
        @start="startInterview"
      />

      <section v-if="profiles.archivedProfiles.length" class="archived-panel">
        <div class="archived-head">
          <h2>已归档档案</h2>
          <span>{{ profiles.archivedProfiles.length }} 个</span>
        </div>
        <article v-for="profile in profiles.archivedProfiles" :key="profile.id" class="archived-row">
          <div>
            <strong>{{ profile.title }}</strong>
            <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }} · {{ profile.company || "未填写公司" }}</p>
          </div>
          <button :data-testid="`restore-profile-${profile.id}`" type="button" @click="profiles.restoreProfile(profile.id)">
            恢复
          </button>
        </article>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive } from "vue";
import { useRouter } from "vue-router";
import PrimaryButton from "@/components/common/PrimaryButton.vue";
import TextField from "@/components/common/TextField.vue";
import ProfileCurrentCard from "@/components/profiles/ProfileCurrentCard.vue";
import ProfileList from "@/components/profiles/ProfileList.vue";
import AppLayout from "@/layouts/AppLayout.vue";
import { useProfilesStore } from "@/stores/profiles";

const router = useRouter();
const profiles = useProfilesStore();
const form = reactive({
  title: "",
  targetRole: "",
  company: "",
  jd: "",
  resume: ""
});

onMounted(() => {
  void profiles.loadProfiles();
  void profiles.loadArchivedProfiles();
});

async function submit(): Promise<void> {
  await profiles.createProfile({ ...form });
  form.title = "";
  form.targetRole = "";
  form.company = "";
  form.jd = "";
  form.resume = "";
}

async function startInterview(id: number): Promise<void> {
  profiles.selectProfile(id);
  await router.push("/vue/app/interview");
}
</script>

<style scoped>
.page-header {
  display: grid;
  gap: 8px;
  max-width: 880px;
  margin-bottom: 28px;
}

.current-section {
  margin-bottom: 22px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0;
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  font-size: 40px;
}

.page-header p,
small {
  color: var(--color-text-muted);
}

.profile-workspace {
  display: grid;
  grid-template-columns: minmax(300px, 420px) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.archived-panel {
  display: grid;
  gap: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.archived-head,
.archived-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.archived-head span,
.archived-row p {
  color: var(--color-text-muted);
}

.archived-row {
  border-top: 1px solid var(--color-border);
  padding-top: 12px;
}

.archived-row button {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  padding: 8px 12px;
}

.profile-form {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-soft);
  padding: 22px;
}

.profile-form {
  display: grid;
  gap: 16px;
}

.area-field {
  display: grid;
  gap: 8px;
}

.area-field span {
  color: var(--color-text-muted);
  font-size: 13px;
}

.area-field textarea {
  width: 100%;
  min-height: 106px;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  outline: none;
  padding: 13px 14px;
}

.area-field textarea:focus {
  border-color: rgba(0, 113, 227, 0.55);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12);
}

.error {
  color: #b42318;
  font-size: 14px;
}

@media (max-width: 960px) {
  .profile-workspace {
    grid-template-columns: 1fr;
  }
}
</style>

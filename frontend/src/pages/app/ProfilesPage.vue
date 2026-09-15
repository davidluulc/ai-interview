<template>
  <AppLayout>
    <div class="profiles-page">
      <section class="page-head">
        <h1>投递档案</h1>
        <p class="subtitle">先把简历、岗位 JD 和公司信息沉淀成档案，再进入模拟面试。</p>
      </section>

      <section v-if="profiles.currentProfile" class="current-section">
        <ProfileCurrentCard :profile="profiles.currentProfile" @start="startInterview" />
      </section>

      <section class="profile-workspace">
        <form class="profile-form" @submit.prevent="submit">
          <h2>新建档案</h2>
          <BrutField v-model="form.title" label="档案名称" name="title" placeholder="后端实习投递" required />
          <BrutField v-model="form.targetRole" label="目标岗位" name="targetRole" placeholder="Python 后端开发实习生" />
          <BrutField v-model="form.company" label="目标公司" name="company" placeholder="可先留空" />
          <label class="area-field">
            <span>岗位 JD</span>
            <textarea v-model="form.jd" placeholder="粘贴岗位职责、任职要求、技术栈关键词" />
          </label>
          <label class="area-field">
            <span>简历概况</span>
            <textarea v-model="form.resume" placeholder="先用文本概括简历，后续再接入文件上传" />
          </label>
          <p v-if="profiles.error" class="error">{{ profiles.error }}</p>
          <BrutButton variant="primary" type="submit" :disabled="profiles.loading">
            {{ profiles.loading ? "保存中" : "保存档案" }}
          </BrutButton>
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
            <div class="archived-row__main">
              <strong>{{ profile.title }}</strong>
              <p>{{ profile.targetRole || profile.target_role || "未填写目标岗位" }} · {{ profile.company || "未填写公司" }}</p>
            </div>
            <BrutButton
              variant="ghost"
              type="button"
              :data-testid="`restore-profile-${profile.id}`"
              @click="profiles.restoreProfile(profile.id)"
            >
              恢复
            </BrutButton>
          </article>
        </section>
      </section>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive } from "vue";
import { useRouter } from "vue-router";
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutField from "@/components/brut/BrutField.vue";
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
.profiles-page {
  display: grid;
  gap: var(--s6);
  font-family: var(--font-ui);
  color: var(--ink);
}

.page-head h1 {
  margin: 0 0 var(--s2);
  font-size: var(--text-page);
  font-weight: 900;
  line-height: 1.1;
}

.subtitle {
  margin: 0;
  max-width: 56ch;
  color: var(--ink-soft);
  font-size: var(--text-strong);
  font-weight: 700;
  line-height: 1.6;
}

.profile-workspace {
  display: grid;
  grid-template-columns: minmax(300px, 420px) minmax(0, 1fr);
  gap: var(--s5);
  align-items: start;
}

/* 新建档案表单：静态容器 2px 墨边装框，不加投影；投影只出现在提交按钮上。 */
.profile-form {
  display: grid;
  gap: var(--s3);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.profile-form h2 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.2;
}

/* 长文本字段与 BrutField 标签保持同一套视觉语言。 */
.area-field {
  display: grid;
  gap: var(--s2);
}

.area-field span {
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.area-field textarea {
  width: 100%;
  min-height: 106px;
  resize: vertical;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font: inherit;
  font-size: var(--text-body);
  line-height: 1.7;
  padding: var(--s3);
}

.area-field textarea::placeholder {
  color: var(--ink-soft);
}

.area-field textarea:focus {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

.error {
  margin: 0;
  border: var(--line);
  background: var(--danger);
  color: var(--action-ink);
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s3);
}

.profile-form .brut-button {
  justify-self: start;
}

/* 已归档区与档案列表同一套 T2 行卡语言。 */
.archived-panel {
  grid-column: 1 / -1;
  display: grid;
  gap: var(--s3);
}

.archived-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s3);
}

.archived-head h2 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.2;
}

.archived-head span {
  color: var(--ink-soft);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.archived-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s4);
  border: var(--line);
  background: var(--panel);
  padding: var(--s3) var(--s4);
}

.archived-row__main {
  display: grid;
  gap: var(--s1);
  min-width: 0;
}

.archived-row__main strong {
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.archived-row__main p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.5;
}

@media (max-width: 960px) {
  .profile-workspace {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .archived-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

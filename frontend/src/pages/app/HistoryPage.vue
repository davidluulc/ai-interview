<template>
  <AppLayout>
    <section class="page-header">
      <div>
        <p class="eyebrow">Review</p>
        <h1>历史复盘</h1>
        <p class="subtitle">回看每一次模拟面试，把问题、回答、评分和薄弱点沉淀成下一轮训练依据。</p>
      </div>
      <button type="button" @click="router.push('/vue/app/interview')">开始新面试</button>
    </section>

    <section v-if="history.error" class="notice error">
      {{ history.error }}
    </section>

    <section v-else-if="history.loading" class="notice">
      正在加载历史记录...
    </section>

    <template v-else>
      <section v-if="history.items.length > 0" class="filter-bar" aria-label="历史记录筛选">
        <label>
          <span>投递档案</span>
          <select data-testid="history-profile-filter" @change="updateProfileFilter">
            <option value="">全部档案</option>
            <option v-for="profile in history.profileOptions" :key="profile.id" :value="profile.id">
              {{ profile.title }}
            </option>
          </select>
        </label>

        <label>
          <span>岗位关键词</span>
          <input
            data-testid="history-role-filter"
            placeholder="例如 Python 后端 / AI 应用"
            type="search"
            @input="updateRoleFilter"
          />
        </label>

        <label>
          <span>时间排序</span>
          <select data-testid="history-sort-order" @change="updateSortOrder">
            <option value="newest">最新优先</option>
            <option value="oldest">最早优先</option>
          </select>
        </label>
      </section>

      <section v-if="history.items.length === 0" class="empty-state">
        <h2>还没有面试记录</h2>
        <p>先完成一次模拟面试，系统会把你的问答、报告和薄弱点保存到这里。</p>
        <button type="button" @click="router.push('/vue/app/interview')">去开始面试</button>
      </section>

      <section v-else-if="history.filteredItems.length === 0" class="empty-state">
        <h2>没有匹配的复盘记录</h2>
        <p>换一个档案或岗位关键词试试。</p>
      </section>

      <section v-else class="history-list" aria-label="历史面试记录">
        <article v-for="item in history.filteredItems" :key="item.id" class="history-card">
          <div class="card-main">
            <div class="card-title-row">
              <span class="score">{{ scoreOf(item.report) }}</span>
              <div>
                <h2>{{ profileTitle(item) }}</h2>
                <p>{{ roleTitle(item) }}</p>
              </div>
            </div>

            <dl class="meta-grid">
              <div>
                <dt>面试时间</dt>
                <dd>{{ formatDate(item.createdAt) }}</dd>
              </div>
              <div>
                <dt>问答轮次</dt>
                <dd>{{ item.answers.length }} 轮</dd>
              </div>
              <div>
                <dt>表现等级</dt>
                <dd>{{ levelOf(item.report) }}</dd>
              </div>
            </dl>

            <div class="weak-tags" aria-label="薄弱点">
              <span v-for="tag in weakTagsOf(item.report)" :key="tag">{{ tag }}</span>
            </div>
          </div>

          <button
            class="report-button"
            type="button"
            :data-testid="`open-report-${item.id}`"
            @click="openReport(item.id)"
          >
            查看报告
          </button>
        </article>
      </section>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import AppLayout from "@/layouts/AppLayout.vue";
import type { HistoryRecord } from "@/api/history";
import { useHistoryStore, type HistorySortOrder } from "@/stores/history";

const router = useRouter();
const history = useHistoryStore();

onMounted(() => {
  void history.loadHistory();
});

function openReport(id: number): void {
  void router.push(`/vue/app/reports/${id}`);
}

function updateProfileFilter(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  history.setFilters({
    applicationProfileId: value ? Number(value) : null,
    roleKeyword: "",
    sortOrder: "newest"
  });
}

function updateRoleFilter(event: Event): void {
  history.setFilters({
    applicationProfileId: null,
    roleKeyword: (event.target as HTMLInputElement).value,
    sortOrder: "newest"
  });
}

function updateSortOrder(event: Event): void {
  history.setFilters({
    applicationProfileId: null,
    roleKeyword: "",
    sortOrder: (event.target as HTMLSelectElement).value as HistorySortOrder
  });
}

function scoreOf(report: Record<string, unknown>): string {
  const score = report.score;
  return typeof score === "number" || typeof score === "string" ? String(score) : "--";
}

function levelOf(report: Record<string, unknown>): string {
  return typeof report.level === "string" && report.level.trim() ? report.level : "待复盘";
}

function weakTagsOf(report: Record<string, unknown>): string[] {
  const tags = report.weakTags;
  if (Array.isArray(tags)) {
    return tags.map(String).filter(Boolean).slice(0, 4);
  }
  return ["待识别"];
}

function profileTitle(item: HistoryRecord): string {
  return item.applicationProfile?.title || String(item.profile.title || "未命名面试");
}

function roleTitle(item: HistoryRecord): string {
  return item.applicationProfile?.targetRole || String(item.profile.targetRole || "未填写岗位");
}

function formatDate(value: string): string {
  if (!value) {
    return "未知时间";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

h1,
h2,
p,
dl,
dd {
  margin: 0;
}

h1 {
  font-size: 40px;
}

.subtitle {
  max-width: 760px;
  color: var(--color-text-muted);
  line-height: 1.7;
  margin-top: 10px;
}

.page-header button,
.empty-state button,
.report-button {
  border: 0;
  border-radius: 999px;
  background: var(--color-accent);
  color: #fff;
  cursor: pointer;
  font-weight: 700;
  padding: 11px 18px;
  white-space: nowrap;
}

.notice,
.empty-state,
.filter-bar,
.history-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
}

.notice,
.empty-state {
  padding: 24px;
}

.error {
  color: #b42318;
}

.empty-state {
  display: grid;
  gap: 12px;
  max-width: 720px;
}

.empty-state p {
  color: var(--color-text-muted);
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(220px, 1.4fr) minmax(140px, 0.8fr);
  gap: 14px;
  margin-bottom: 18px;
  padding: 18px;
}

.filter-bar label {
  display: grid;
  gap: 6px;
}

.filter-bar span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.filter-bar select,
.filter-bar input {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-text);
  font: inherit;
  padding: 10px 12px;
}

.history-list {
  display: grid;
  gap: 16px;
}

.history-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px;
}

.card-main {
  display: grid;
  min-width: 0;
  gap: 16px;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.score {
  display: grid;
  width: 58px;
  height: 58px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: #111827;
  color: #fff;
  font-size: 20px;
  font-weight: 800;
}

.card-title-row p,
dt {
  color: var(--color-text-muted);
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: 12px;
}

dt {
  font-size: 12px;
  margin-bottom: 4px;
}

dd {
  font-weight: 700;
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.weak-tags span {
  border-radius: 999px;
  background: #eef4ff;
  color: #175cd3;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 9px;
}

.report-button {
  flex: 0 0 auto;
}

@media (max-width: 760px) {
  .page-header,
  .history-card,
  .card-title-row {
    align-items: stretch;
    flex-direction: column;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    grid-template-columns: 1fr;
  }

  .score {
    border-radius: var(--radius-md);
  }
}
</style>

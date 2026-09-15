<template>
  <AppLayout>
    <div class="history-page">
      <section class="page-head">
        <div>
          <h1>历史复盘</h1>
          <p class="subtitle">回看每一次模拟面试，把问题、回答、评分和薄弱点沉淀成下一轮训练依据。</p>
        </div>
        <BrutButton variant="primary" type="button" @click="router.push('/vue/app/interview')">
          开始新面试
        </BrutButton>
      </section>

      <section v-if="history.error" class="notice notice--error">
        {{ history.error }}
      </section>

      <section v-else-if="history.loading" class="notice notice--loading">
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
          <BrutButton variant="primary" type="button" @click="router.push('/vue/app/interview')">
            去开始面试
          </BrutButton>
        </section>

        <section v-else-if="history.filteredItems.length === 0" class="empty-state">
          <h2>没有匹配的复盘记录</h2>
          <p>换一个档案或岗位关键词试试。</p>
        </section>

        <section v-else class="history-list" aria-label="历史面试记录">
          <article v-for="item in history.filteredItems" :key="item.id" class="ledger-row">
            <span class="ledger-row__date">{{ formatDate(item.createdAt) }}</span>

            <div class="ledger-row__main">
              <h2>{{ profileTitle(item) }}</h2>
              <p>{{ roleTitle(item) }}</p>
              <div class="row-meta">
                <span class="row-meta__item">
                  <span class="row-meta__label">问答轮次</span>
                  <span class="row-meta__value">{{ item.answers.length }} 轮</span>
                </span>
                <span class="row-meta__item">
                  <span class="row-meta__label">表现等级</span>
                  <span class="row-meta__value">{{ levelOf(item.report) }}</span>
                </span>
              </div>
            </div>

            <div class="ledger-row__weak" aria-label="薄弱点">
              <span v-for="tag in weakTagsOf(item.report)" :key="tag" class="weak-tag">{{ tag }}</span>
            </div>

            <span
              v-if="scoreValueOf(item.report) !== null"
              class="ledger-row__score"
              :class="scoreTierClassOf(item.report)"
            >
              {{ scoreValueOf(item.report) }}
            </span>

            <BrutButton
              variant="ghost"
              type="button"
              :data-testid="`open-report-${item.id}`"
              @click="openReport(item.id)"
            >
              查看报告
            </BrutButton>
          </article>
        </section>
      </template>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import AppLayout from "@/layouts/AppLayout.vue";
import BrutButton from "@/components/brut/BrutButton.vue";
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

/* 报告 score 实际值域为 0-100（见 backend_python/prompts/interview.py）；缺分或非数值时不渲染分块。 */
function scoreValueOf(report: Record<string, unknown>): number | null {
  const score = report.score;
  if (typeof score === "number") {
    return Number.isFinite(score) ? score : null;
  }
  if (typeof score === "string" && score.trim()) {
    const parsed = Number(score);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

/* 档位阈值与 ChunkChip 一致（0-1 归一化：0.8/0.7/0.6/0.5），底色取 score-5..1 蓝梯度。 */
function scoreTierClassOf(report: Record<string, unknown>): string {
  const score = scoreValueOf(report);
  if (score === null) {
    return "";
  }
  const normalized = score / 100;
  const tier = normalized >= 0.8 ? 5 : normalized >= 0.7 ? 4 : normalized >= 0.6 ? 3 : normalized >= 0.5 ? 2 : 1;
  return `ledger-row__score--tier-${tier}`;
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
.history-page {
  display: grid;
  gap: var(--s6);
  font-family: var(--font-ui);
  color: var(--ink);
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s5);
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

.notice {
  border: var(--line);
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s4);
}

.notice--error {
  background: var(--danger);
  color: var(--action-ink);
}

.notice--loading {
  width: fit-content;
  border-style: dashed;
  color: var(--ink-soft);
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(220px, 1.4fr) minmax(140px, 0.8fr);
  gap: var(--s3);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.filter-bar label {
  display: grid;
  gap: var(--s2);
}

.filter-bar span {
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.filter-bar select,
.filter-bar input {
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font: inherit;
  font-size: var(--text-body);
  padding: var(--s2) var(--s3);
}

.filter-bar select:focus,
.filter-bar input:focus {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

.empty-state {
  display: grid;
  gap: var(--s2);
  max-width: 720px;
  border: 2px dashed var(--ink);
  background: var(--panel);
  padding: var(--s5);
}

.empty-state h2 {
  margin: 0;
  font-size: var(--text-section);
  font-weight: 900;
}

.empty-state p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.empty-state .brut-button {
  justify-self: start;
  margin-top: var(--s2);
}

.history-list {
  display: grid;
  gap: var(--s3);
}

/* T2 台账行：2px 墨边装框，不加投影（投影仅交互元素）。 */
.ledger-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto auto;
  align-items: center;
  gap: var(--s4);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.ledger-row__date {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
  line-height: 1.5;
  white-space: nowrap;
}

.ledger-row__main {
  display: grid;
  min-width: 0;
  gap: var(--s1);
}

.ledger-row__main h2 {
  margin: 0;
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
}

.ledger-row__main p {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.5;
}

.row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s1) var(--s3);
  margin-top: var(--s1);
}

.row-meta__item {
  display: inline-flex;
  align-items: baseline;
  gap: var(--s1);
}

.row-meta__label {
  color: var(--ink-soft);
  font-size: var(--text-data);
  font-weight: 900;
  letter-spacing: 0.06em;
}

.row-meta__value {
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

/* 历史记录的 weakTags 只有叙事标签、没有出现次数，按反编造规则用中性描边标签而非热度档位。 */
.ledger-row__weak {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s1);
  max-width: 240px;
}

.weak-tag {
  border: 1px solid var(--ink);
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 800;
  line-height: 1.3;
  padding: var(--s1) var(--s2);
}

/* 总分大数字：真实报告分数 + ChunkChip 同源蓝梯度档底。 */
.ledger-row__score {
  display: inline-grid;
  place-items: center;
  min-width: 76px;
  border: var(--line);
  font-family: var(--font-mono);
  font-size: var(--text-page);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  padding: var(--s2) var(--s3);
}

.ledger-row__score--tier-5 {
  background: var(--score-5);
  color: var(--action-ink);
}

.ledger-row__score--tier-4 {
  background: var(--score-4);
  color: var(--ink);
}

.ledger-row__score--tier-3 {
  background: var(--score-3);
  color: var(--ink);
}

.ledger-row__score--tier-2 {
  background: var(--score-2);
  color: var(--ink);
}

.ledger-row__score--tier-1 {
  background: var(--score-1);
  color: var(--ink);
}

@media (max-width: 760px) {
  .page-head {
    flex-direction: column;
  }

  .filter-bar {
    grid-template-columns: 1fr;
  }

  .ledger-row {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .ledger-row__weak {
    max-width: none;
  }
}
</style>

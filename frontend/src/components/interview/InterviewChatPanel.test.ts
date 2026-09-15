import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewChatPanel from "./InterviewChatPanel.vue";

const baseProps = {
  currentRound: 2,
  totalRounds: 8,
  difficulty: "standard" as const,
  focusArea: "rag_agent" as const,
  mode: "coach" as const
};

describe("InterviewChatPanel", () => {
  it("shows the latest interviewer question on the stage", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        ...baseProps,
        messages: [
          { role: "interviewer", content: "第一题：请做一个自我介绍。" },
          { role: "candidate", content: "我是做 Python 后端的候选人。" },
          { role: "interviewer", content: "请介绍你的 RAG 项目。" }
        ],
        draft: "",
        loading: false,
        canSubmit: true
      } as any
    });

    expect(wrapper.find(".question-stage__text").text()).toBe("请介绍你的 RAG 项目。");
    expect(wrapper.find(".question-stage__tag").text()).toBe("第 2 / 8 轮 · RAG & Agent");
    expect(wrapper.text()).toContain("难度 标准");
    expect(wrapper.text()).not.toContain("第一题：请做一个自我介绍。");
  });

  it("shows first-question loading copy with a visible spinner", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        ...baseProps,
        messages: [],
        draft: "",
        loading: true,
        canSubmit: false,
        sessionStatus: "starting"
      } as any
    });

    expect(wrapper.text()).toContain("AI 面试官正在生成第一题");
    expect(wrapper.text()).not.toContain("正在分析你的回答");
    expect(wrapper.find('[data-testid="thinking-spinner"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="interviewer-thinking"]').attributes("aria-live")).toBe("polite");
    expect(wrapper.find('[data-testid="submit-answer"]').attributes("disabled")).toBeDefined();
  });

  it("shows answer-analysis loading copy after the user submits an answer", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        ...baseProps,
        messages: [
          { role: "interviewer", content: "请介绍你的项目。" },
          { role: "candidate", content: "我做过 RAG 项目。" }
        ],
        draft: "",
        loading: true,
        canSubmit: false,
        sessionStatus: "answering"
      } as any
    });

    expect(wrapper.text()).toContain("AI 面试官正在分析你的回答");
    expect(wrapper.find('[data-testid="submit-answer"]').attributes("disabled")).toBeDefined();
  });

  it("emits update:draft as the user types in the answer box", async () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        ...baseProps,
        messages: [{ role: "interviewer", content: "请介绍你的项目。" }],
        draft: "",
        loading: false,
        canSubmit: true
      } as any
    });

    await wrapper.get('[data-testid="draft-input"]').setValue("我的回答");

    expect(wrapper.emitted("update:draft")?.[0]).toEqual(["我的回答"]);
  });

  it("emits submit when the chunky submit button is clicked", async () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        ...baseProps,
        messages: [{ role: "interviewer", content: "请介绍你的项目。" }],
        draft: "我的回答",
        loading: false,
        canSubmit: true
      } as any
    });

    await wrapper.get('[data-testid="submit-answer"]').trigger("click");

    expect(wrapper.emitted("submit")).toHaveLength(1);
  });

  it("keeps the submit button disabled when the store cannot accept an answer", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        ...baseProps,
        messages: [{ role: "interviewer", content: "请介绍你的项目。" }],
        draft: "我的回答",
        loading: false,
        canSubmit: false
      } as any
    });

    expect(wrapper.find('[data-testid="submit-answer"]').attributes("disabled")).toBeDefined();
  });

  it("shows the interview error copy near the composer", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        ...baseProps,
        messages: [{ role: "interviewer", content: "请介绍你的项目。" }],
        draft: "",
        loading: false,
        error: "生成下一题失败",
        canSubmit: true
      } as any
    });

    expect(wrapper.text()).toContain("生成下一题失败");
  });
});

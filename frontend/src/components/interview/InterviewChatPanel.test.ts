import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewChatPanel from "./InterviewChatPanel.vue";

describe("InterviewChatPanel", () => {
  it("shows first-question loading copy with a visible spinner", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        messages: [{ role: "interviewer", content: "请介绍你的项目。" }],
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
    expect(wrapper.find("button").attributes("disabled")).toBeDefined();
  });

  it("shows answer-analysis loading copy after the user submits an answer", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
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
    expect(wrapper.find("button").attributes("disabled")).toBeDefined();
  });
});

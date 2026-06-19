import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewChatPanel from "./InterviewChatPanel.vue";

describe("InterviewChatPanel", () => {
  it("shows an interviewer thinking bubble while loading", () => {
    const wrapper = mount(InterviewChatPanel, {
      props: {
        messages: [{ role: "interviewer", content: "请介绍你的项目。" }],
        draft: "",
        loading: true,
        canSubmit: false
      }
    });

    expect(wrapper.text()).toContain("AI 面试官正在分析你的回答");
    expect(wrapper.find("button").attributes("disabled")).toBeDefined();
  });
});

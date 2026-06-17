import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewProgressStrip from "./InterviewProgressStrip.vue";

describe("InterviewProgressStrip", () => {
  it("renders round progress and session labels", () => {
    const wrapper = mount(InterviewProgressStrip, {
      props: {
        currentRound: 3,
        totalRounds: 8,
        mode: "coach",
        difficulty: "standard",
        focusArea: "rag_agent",
        complete: false
      }
    });

    expect(wrapper.text()).toContain("第 3 / 8 题");
    expect(wrapper.text()).toContain("学习辅导");
    expect(wrapper.text()).toContain("标准");
    expect(wrapper.text()).toContain("RAG & Agent");
  });

  it("marks the session as complete", () => {
    const wrapper = mount(InterviewProgressStrip, {
      props: {
        currentRound: 8,
        totalRounds: 8,
        mode: "interview",
        difficulty: "pressure",
        focusArea: "project_deep_dive",
        complete: true
      }
    });

    expect(wrapper.text()).toContain("已完成");
    expect(wrapper.text()).toContain("真实面试");
  });
});

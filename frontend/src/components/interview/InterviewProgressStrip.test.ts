import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewProgressStrip from "./InterviewProgressStrip.vue";

describe("InterviewProgressStrip", () => {
  it("renders round progress and session meta chips", () => {
    const wrapper = mount(InterviewProgressStrip, {
      props: {
        currentRound: 3,
        totalRounds: 8,
        difficulty: "standard",
        focusArea: "rag_agent",
        complete: false
      }
    });

    expect(wrapper.text()).toContain("进行中");
    expect(wrapper.text()).toContain("第 3 / 8 题");
    expect(wrapper.text()).toContain("难度 标准");
    expect(wrapper.text()).toContain("重点 RAG & Agent");
    expect(wrapper.text()).not.toContain("链路");
  });

  it("marks the session as complete", () => {
    const wrapper = mount(InterviewProgressStrip, {
      props: {
        currentRound: 8,
        totalRounds: 8,
        difficulty: "pressure",
        focusArea: "project_deep_dive",
        complete: true
      }
    });

    expect(wrapper.text()).toContain("已完成");
    expect(wrapper.text()).not.toContain("进行中");
  });

  it("shows the runtime label chip only when provided", () => {
    const withRuntime = mount(InterviewProgressStrip, {
      props: {
        currentRound: 1,
        totalRounds: 8,
        difficulty: "basic",
        focusArea: "mixed",
        complete: false,
        runtimeLabel: "旁路对比"
      }
    });

    expect(withRuntime.text()).toContain("链路 旁路对比");
  });
});

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewFinishPanel from "./InterviewFinishPanel.vue";

describe("InterviewFinishPanel", () => {
  it("keeps review disabled before the first answer", () => {
    const wrapper = mount(InterviewFinishPanel, {
      props: { canFinish: false, complete: false, answeredCount: 0 }
    });

    expect(wrapper.text()).toContain("至少完成 1 轮问答后再复盘");
    expect(wrapper.find('[data-testid="finish-interview"]').attributes("disabled")).toBeDefined();
  });

  it("allows users to finish after at least one answer", async () => {
    const wrapper = mount(InterviewFinishPanel, {
      props: { canFinish: true, complete: false, answeredCount: 2 }
    });

    await wrapper.get('[data-testid="finish-interview"]').trigger("click");
    expect(wrapper.emitted("finish")).toHaveLength(1);
  });

  it("shows report generation state and prevents repeated clicks", () => {
    const wrapper = mount(InterviewFinishPanel, {
      props: { canFinish: true, complete: false, answeredCount: 2, submitting: true }
    });

    expect(wrapper.text()).toContain("正在生成复盘报告");
    expect(wrapper.find('[data-testid="finish-interview"]').attributes("disabled")).toBeDefined();
  });

  it("recommends review after completing configured rounds", () => {
    const wrapper = mount(InterviewFinishPanel, {
      props: { canFinish: true, complete: true, answeredCount: 8 }
    });

    expect(wrapper.text()).toContain("本轮面试可以复盘了");
  });
});

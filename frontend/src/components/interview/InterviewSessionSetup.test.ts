import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InterviewSessionSetup from "./InterviewSessionSetup.vue";

describe("InterviewSessionSetup", () => {
  it("renders profile summary and emits session config updates", async () => {
    const wrapper = mount(InterviewSessionSetup, {
      props: {
        profile: {
          title: "后端实习投递",
          targetRole: "Python 后端开发实习生",
          company: "Example AI",
          jd: "熟悉 FastAPI、RAG 和 Agent"
        },
        config: {
          totalRounds: 8,
          difficulty: "standard",
          focusArea: "mixed"
        }
      }
    });

    expect(wrapper.text()).toContain("本次面试配置");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("Python 后端开发实习生");
    expect(wrapper.text()).toContain("Example AI");
    expect(wrapper.text()).toContain("FastAPI、RAG 和 Agent");

    await wrapper.get('[data-testid="session-total-rounds"]').setValue("10");
    await wrapper.get('[data-testid="session-difficulty"]').setValue("pressure");
    await wrapper.get('[data-testid="session-focus-area"]').setValue("rag_agent");

    expect(wrapper.emitted("update:config")?.at(-1)?.[0]).toEqual(
      expect.objectContaining({
        totalRounds: 10,
        difficulty: "pressure",
        focusArea: "rag_agent"
      })
    );
  });
});

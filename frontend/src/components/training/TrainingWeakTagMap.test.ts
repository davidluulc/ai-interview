import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TrainingWeakTagMap from "./TrainingWeakTagMap.vue";

describe("TrainingWeakTagMap", () => {
  it("renders weak tag groups and emits selection", async () => {
    const wrapper = mount(TrainingWeakTagMap, {
      props: {
        activeWeakTag: "",
        groups: [
          {
            weakTag: "rag_quality",
            weakLabel: "RAG 质量",
            total: 2,
            todo: 1,
            inProgress: 0,
            done: 1,
            averageMastery: 60,
            highestPriority: "high"
          }
        ]
      }
    });

    expect(wrapper.text()).toContain("薄弱点训练地图");
    expect(wrapper.text()).toContain("RAG 质量");
    expect(wrapper.text()).toContain("2 个任务");
    expect(wrapper.text()).toContain("平均掌握度 60");

    await wrapper.get('[data-testid="weak-tag-rag_quality"]').trigger("click");

    expect(wrapper.emitted("select")?.[0]).toEqual(["rag_quality"]);
  });

  it("renders empty guidance when there are no groups", () => {
    const wrapper = mount(TrainingWeakTagMap, {
      props: {
        activeWeakTag: "",
        groups: []
      }
    });

    expect(wrapper.text()).toContain("还没有可聚合的薄弱点");
  });
});

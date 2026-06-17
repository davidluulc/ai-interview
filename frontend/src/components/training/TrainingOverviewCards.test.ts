import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TrainingOverviewCards from "./TrainingOverviewCards.vue";

describe("TrainingOverviewCards", () => {
  it("renders training overview metrics", () => {
    const wrapper = mount(TrainingOverviewCards, {
      props: {
        todoCount: 3,
        inProgressCount: 1,
        doneCount: 5,
        archivedCount: 2,
        averageMastery: 62
      }
    });

    expect(wrapper.text()).toContain("训练概览");
    expect(wrapper.text()).toContain("待训练");
    expect(wrapper.text()).toContain("训练中");
    expect(wrapper.text()).toContain("已完成");
    expect(wrapper.text()).toContain("已归档");
    expect(wrapper.text()).toContain("平均掌握度");
    expect(wrapper.text()).toContain("62");
  });

  it("renders empty mastery as placeholder", () => {
    const wrapper = mount(TrainingOverviewCards, {
      props: {
        todoCount: 0,
        inProgressCount: 0,
        doneCount: 0,
        archivedCount: 0,
        averageMastery: null
      }
    });

    expect(wrapper.text()).toContain("--");
  });
});

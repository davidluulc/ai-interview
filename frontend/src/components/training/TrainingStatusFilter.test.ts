import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TrainingStatusFilter from "./TrainingStatusFilter.vue";

describe("TrainingStatusFilter", () => {
  it("renders status filters and emits updates", async () => {
    const wrapper = mount(TrainingStatusFilter, {
      props: {
        modelValue: ""
      }
    });

    expect(wrapper.text()).toContain("全部");
    expect(wrapper.text()).toContain("待训练");
    expect(wrapper.text()).toContain("训练中");
    expect(wrapper.text()).toContain("已完成");
    expect(wrapper.text()).toContain("已归档");

    await wrapper.get('[data-testid="status-filter-done"]').trigger("click");

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["done"]);
  });
});

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ChunkChip from "./ChunkChip.vue";
import HeatChip from "./HeatChip.vue";
import ProgressBlocks from "./ProgressBlocks.vue";
import ModeSeg from "./ModeSeg.vue";

describe("ChunkChip", () => {
  it.each([
    [0.87, "chunk-chip--tier-5"],
    [0.8, "chunk-chip--tier-5"],
    [0.79, "chunk-chip--tier-4"],
    [0.7, "chunk-chip--tier-4"],
    [0.69, "chunk-chip--tier-3"],
    [0.6, "chunk-chip--tier-3"],
    [0.59, "chunk-chip--tier-2"],
    [0.5, "chunk-chip--tier-2"],
    [0.49, "chunk-chip--tier-1"],
    [0, "chunk-chip--tier-1"]
  ] as const)("maps score %s to class %s", (score, tierClass) => {
    const wrapper = mount(ChunkChip, { props: { label: "缓存策略", score } });

    expect(wrapper.classes()).toContain("chunk-chip");
    expect(wrapper.classes()).toContain(tierClass);
  });

  it("renders the label and the score number", () => {
    const wrapper = mount(ChunkChip, { props: { label: "缓存策略", score: 0.87 } });

    expect(wrapper.text()).toContain("缓存策略");
    expect(wrapper.find(".chunk-chip__score").text()).toBe("0.87");
  });
});

describe("HeatChip", () => {
  it.each([
    [3, "heat-chip--tier-3"],
    [2, "heat-chip--tier-2"],
    [1, "heat-chip--tier-1"],
    [0, "heat-chip--tier-1"]
  ] as const)("maps count %s to class %s", (count, tierClass) => {
    const wrapper = mount(HeatChip, { props: { label: "系统设计", count } });

    expect(wrapper.classes()).toContain("heat-chip");
    expect(wrapper.classes()).toContain(tierClass);
  });

  it("appends ×count to the label when count is greater than 1", () => {
    const wrapper = mount(HeatChip, { props: { label: "系统设计", count: 3 } });

    expect(wrapper.text()).toBe("系统设计 ×3");
  });

  it("renders the plain label when count is 1", () => {
    const wrapper = mount(HeatChip, { props: { label: "幂等设计", count: 1 } });

    expect(wrapper.text()).toBe("幂等设计");
  });
});

describe("ProgressBlocks", () => {
  it("renders total blocks: prior pass/fail colors, hazard current, white rest", () => {
    const wrapper = mount(ProgressBlocks, {
      props: { total: 5, current: 4, prior: ["pass", "fail", "pass"] }
    });

    expect(wrapper.classes()).toContain("progress-blocks");
    const blocks = wrapper.findAll(".progress-blocks__block");
    expect(blocks).toHaveLength(5);
    expect(blocks[0].classes()).toContain("progress-blocks__block--pass");
    expect(blocks[1].classes()).toContain("progress-blocks__block--fail");
    expect(blocks[2].classes()).toContain("progress-blocks__block--pass");
    expect(blocks[3].classes()).toContain("progress-blocks__block--current");
    expect(blocks[4].classes()).toContain("progress-blocks__block--todo");
  });

  it("colors nothing green or red when prior is empty and marks block 1 current", () => {
    const wrapper = mount(ProgressBlocks, {
      props: { total: 3, current: 1, prior: [] }
    });

    const blocks = wrapper.findAll(".progress-blocks__block");
    expect(blocks).toHaveLength(3);
    expect(blocks[0].classes()).toContain("progress-blocks__block--current");
    expect(blocks[1].classes()).toContain("progress-blocks__block--todo");
    expect(blocks[2].classes()).toContain("progress-blocks__block--todo");
  });

  it("renders only prior-colored blocks when current is past the end", () => {
    const wrapper = mount(ProgressBlocks, {
      props: { total: 2, current: 3, prior: ["pass", "fail"] }
    });

    const blocks = wrapper.findAll(".progress-blocks__block");
    expect(blocks).toHaveLength(2);
    expect(blocks[0].classes()).toContain("progress-blocks__block--pass");
    expect(blocks[1].classes()).toContain("progress-blocks__block--fail");
  });
});

describe("ModeSeg", () => {
  const options = [
    { value: "coach", label: "学习辅导" },
    { value: "interview", label: "真实面试" }
  ];

  it("renders one native button per option with its label", () => {
    const wrapper = mount(ModeSeg, { props: { options, modelValue: "coach" } });

    const buttons = wrapper.findAll("button");
    expect(buttons).toHaveLength(2);
    expect(buttons[0].text()).toBe("学习辅导");
    expect(buttons[1].text()).toBe("真实面试");
  });

  it("marks only the segment matching modelValue as active", () => {
    const wrapper = mount(ModeSeg, { props: { options, modelValue: "coach" } });

    const buttons = wrapper.findAll("button");
    expect(buttons[0].classes()).toContain("mode-seg__btn--active");
    expect(buttons[1].classes()).not.toContain("mode-seg__btn--active");
  });

  it("emits update:modelValue with the option value on click", async () => {
    const wrapper = mount(ModeSeg, { props: { options, modelValue: "coach" } });

    await wrapper.findAll("button")[1].trigger("click");
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["interview"]);
  });
});

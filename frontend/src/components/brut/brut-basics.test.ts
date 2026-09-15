import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import BrutButton from "./BrutButton.vue";
import BrutChip from "./BrutChip.vue";
import BrutStamp from "./BrutStamp.vue";

describe("BrutButton", () => {
  it("renders as a button with the base class and slot text", () => {
    const wrapper = mount(BrutButton, {
      props: { variant: "primary" },
      slots: { default: "开始面试" }
    });

    expect(wrapper.element.tagName).toBe("BUTTON");
    expect(wrapper.classes()).toContain("brut-button");
    expect(wrapper.text()).toContain("开始面试");
  });

  it.each([
    ["primary", "brut-button--primary"],
    ["ghost", "brut-button--ghost"],
    ["danger", "brut-button--danger"]
  ] as const)("maps variant %s to class %s", (variant, variantClass) => {
    const wrapper = mount(BrutButton, {
      props: { variant },
      slots: { default: "按钮" }
    });

    expect(wrapper.classes()).toContain(variantClass);
  });

  it("is not disabled by default", () => {
    const wrapper = mount(BrutButton, {
      props: { variant: "ghost" },
      slots: { default: "保存" }
    });

    expect(wrapper.attributes("disabled")).toBeUndefined();
  });

  it("sets the disabled attribute when disabled", () => {
    const wrapper = mount(BrutButton, {
      props: { variant: "ghost", disabled: true },
      slots: { default: "保存" }
    });

    expect(wrapper.attributes("disabled")).toBeDefined();
  });

  it("replaces the label with the loading text and disables clicks while loading", () => {
    const wrapper = mount(BrutButton, {
      props: { variant: "primary", loading: true },
      slots: { default: "提交回答" }
    });

    expect(wrapper.text()).toContain("处理中…");
    expect(wrapper.text()).not.toContain("提交回答");
    expect(wrapper.attributes("disabled")).toBeDefined();
  });

  it("passes attrs through to the root element", () => {
    const wrapper = mount(BrutButton, {
      props: { variant: "ghost" },
      attrs: { "data-testid": "submit-answer" },
      slots: { default: "提交" }
    });

    expect(wrapper.attributes("data-testid")).toBe("submit-answer");
  });
});

describe("BrutChip", () => {
  it.each([
    ["ok", "brut-chip--ok"],
    ["warn", "brut-chip--warn"],
    ["danger", "brut-chip--danger"],
    ["info", "brut-chip--info"],
    ["neutral", "brut-chip--neutral"]
  ] as const)("maps tone %s to class %s and renders the label", (tone, toneClass) => {
    const wrapper = mount(BrutChip, { props: { tone, label: "就绪" } });

    expect(wrapper.classes()).toContain("brut-chip");
    expect(wrapper.classes()).toContain(toneClass);
    expect(wrapper.text()).toBe("就绪");
  });
});

describe("BrutStamp", () => {
  it.each([
    ["pass", "brut-stamp--pass"],
    ["warn", "brut-stamp--warn"],
    ["fail", "brut-stamp--fail"]
  ] as const)("maps verdict %s to class %s and renders the text", (verdict, verdictClass) => {
    const wrapper = mount(BrutStamp, { props: { verdict, text: "通过" } });

    expect(wrapper.classes()).toContain("brut-stamp");
    expect(wrapper.classes()).toContain(verdictClass);
    expect(wrapper.text()).toBe("通过");
  });
});

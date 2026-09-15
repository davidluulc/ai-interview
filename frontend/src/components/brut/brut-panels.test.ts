import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import BrutPanel from "./BrutPanel.vue";
import HazardBanner from "./HazardBanner.vue";
import ScoreBlock from "./ScoreBlock.vue";

describe("BrutPanel", () => {
  it("renders a black header with the title prop", () => {
    const wrapper = mount(BrutPanel, {
      props: { title: "面试记录" },
      slots: { default: "内容" }
    });

    expect(wrapper.classes()).toContain("brut-panel");
    const head = wrapper.find(".brut-panel__head");
    expect(head.exists()).toBe(true);
    expect(head.text()).toBe("面试记录");
  });

  it("renders the default slot as the panel body", () => {
    const wrapper = mount(BrutPanel, {
      props: { title: "评估报告" },
      slots: { default: "<p data-testid='body-slot'>报告内容</p>" }
    });

    const body = wrapper.find(".brut-panel__body");
    expect(body.exists()).toBe(true);
    expect(body.find("[data-testid='body-slot']").exists()).toBe(true);
    expect(body.text()).toBe("报告内容");
  });

  it("keeps the title out of the body", () => {
    const wrapper = mount(BrutPanel, {
      props: { title: "仅头部" },
      slots: { default: "正文" }
    });

    expect(wrapper.find(".brut-panel__body").text()).toBe("正文");
  });
});

describe("HazardBanner", () => {
  it("renders the hazard stripe strip on the left", () => {
    const wrapper = mount(HazardBanner, {
      props: { title: "警告", detail: "连接已断开" }
    });

    expect(wrapper.classes()).toContain("hazard-banner");
    expect(wrapper.find(".hazard-banner__stripe").exists()).toBe(true);
  });

  it("renders the title and detail text", () => {
    const wrapper = mount(HazardBanner, {
      props: { title: "本轮未通过", detail: "回答中断，已保存草稿" }
    });

    expect(wrapper.find(".hazard-banner__title").text()).toBe("本轮未通过");
    expect(wrapper.find(".hazard-banner__detail").text()).toBe("回答中断，已保存草稿");
  });
});

describe("ScoreBlock", () => {
  it("renders the score number as-is", () => {
    const wrapper = mount(ScoreBlock, {
      props: { score: 87, caption: "综合得分" }
    });

    expect(wrapper.classes()).toContain("score-block");
    expect(wrapper.find(".score-block__value").text()).toBe("87");
  });

  it("renders the caption column", () => {
    const wrapper = mount(ScoreBlock, {
      props: { score: 64, caption: "系统设计" }
    });

    expect(wrapper.find(".score-block__caption").text()).toBe("系统设计");
  });
});

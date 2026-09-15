import { mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { describe, expect, it } from "vitest";
import AnswerBox from "./AnswerBox.vue";
import BrutPanel from "./BrutPanel.vue";
import QuestionStage from "./QuestionStage.vue";
import RoundLedger from "./RoundLedger.vue";

describe("QuestionStage", () => {
  it("renders the tag cap, question text, and one chip per meta entry", () => {
    const wrapper = mount(QuestionStage, {
      props: {
        tag: "第 3 题 · 系统设计",
        text: "设计一个短链服务，如何保证跳转低延迟？",
        meta: ["难度 P6", "链路 缓存", "时长 45min"]
      }
    });

    expect(wrapper.classes()).toContain("question-stage");
    expect(wrapper.find(".question-stage__tag").text()).toBe("第 3 题 · 系统设计");
    expect(wrapper.find(".question-stage__text").text()).toBe(
      "设计一个短链服务，如何保证跳转低延迟？"
    );

    const chips = wrapper.findAll(".question-stage__chip");
    expect(chips.map((chip) => chip.text())).toEqual(["难度 P6", "链路 缓存", "时长 45min"]);
  });

  it("renders no meta chips when meta is empty", () => {
    const wrapper = mount(QuestionStage, {
      props: { tag: "第 1 题 · 开场", text: "请先做一个自我介绍。", meta: [] }
    });

    expect(wrapper.findAll(".question-stage__chip")).toHaveLength(0);
  });
});

describe("AnswerBox", () => {
  it("renders the label row with 你的回答 on the left and the hint on the right", () => {
    const wrapper = mount(AnswerBox, {
      props: { modelValue: "", placeholder: "输入你的回答...", hint: "Enter 提交 · Shift+Enter 换行" }
    });

    expect(wrapper.classes()).toContain("answer-box");
    expect(wrapper.find(".answer-box__label").text()).toBe("你的回答");
    expect(wrapper.find(".answer-box__hint").text()).toBe("Enter 提交 · Shift+Enter 换行");
  });

  it("shows the current modelValue and placeholder in the textarea", () => {
    const wrapper = mount(AnswerBox, {
      props: { modelValue: "已有的草稿", placeholder: "输入你的回答...", hint: "" }
    });

    const textarea = wrapper.find("textarea");
    expect(textarea.element.value).toBe("已有的草稿");
    expect(textarea.attributes("placeholder")).toBe("输入你的回答...");
  });

  it("emits update:modelValue as the user types", async () => {
    const wrapper = mount(AnswerBox, {
      props: { modelValue: "", placeholder: "", hint: "" }
    });

    await wrapper.find("textarea").setValue("我的回答");

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["我的回答"]);
  });

  it("binds two-way through v-model on a host component", async () => {
    const host = defineComponent({
      components: { AnswerBox },
      data: () => ({ draft: "旧草稿" }),
      template: `<AnswerBox v-model="draft" placeholder="" hint="" />`
    });
    const wrapper = mount(host);
    expect(wrapper.find("textarea").element.value).toBe("旧草稿");

    await wrapper.find("textarea").setValue("新草稿");

    const vm = wrapper.vm as { draft: string };
    expect(vm.draft).toBe("新草稿");
    expect(wrapper.find("textarea").element.value).toBe("新草稿");
  });

  it("emits submit and prevents the newline when Enter is pressed without shift", async () => {
    const wrapper = mount(AnswerBox, {
      props: { modelValue: "草稿", placeholder: "", hint: "" }
    });
    const textarea = wrapper.find("textarea");

    await textarea.trigger("keydown", { key: "Enter" });

    expect(wrapper.emitted("submit")).toHaveLength(1);

    const plain = new KeyboardEvent("keydown", {
      key: "Enter",
      bubbles: true,
      cancelable: true
    });
    textarea.element.dispatchEvent(plain);
    await nextTick();

    expect(plain.defaultPrevented).toBe(true);
    expect(wrapper.emitted("submit")).toHaveLength(2);
  });

  it("does not emit submit nor prevent default when Shift+Enter is pressed", async () => {
    const wrapper = mount(AnswerBox, {
      props: { modelValue: "", placeholder: "", hint: "" }
    });

    const shifted = new KeyboardEvent("keydown", {
      key: "Enter",
      shiftKey: true,
      bubbles: true,
      cancelable: true
    });
    wrapper.find("textarea").element.dispatchEvent(shifted);
    await nextTick();

    expect(shifted.defaultPrevented).toBe(false);
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("does not emit submit while an IME composition is confirming a candidate", async () => {
    const wrapper = mount(AnswerBox, {
      props: { modelValue: "pin", placeholder: "", hint: "" }
    });

    const composing = new KeyboardEvent("keydown", {
      key: "Enter",
      bubbles: true,
      cancelable: true
    });
    Object.defineProperty(composing, "isComposing", { value: true });
    wrapper.find("textarea").element.dispatchEvent(composing);
    await nextTick();

    expect(composing.defaultPrevented).toBe(false);
    expect(wrapper.emitted("submit")).toBeUndefined();
  });
});

describe("RoundLedger", () => {
  const rounds: Array<{
    index: number;
    label: string;
    status: "pass" | "fail" | "done" | "current" | "todo";
  }> = [
    { index: 1, label: "项目深挖", status: "pass" },
    { index: 2, label: "基础八股", status: "fail" },
    { index: 3, label: "项目复盘", status: "done" },
    { index: 4, label: "系统设计", status: "current" },
    { index: 5, label: "反问环节", status: "todo" }
  ];

  it("renders inside a BrutPanel titled 轮次台账", () => {
    const wrapper = mount(RoundLedger, { props: { rounds: [] } });

    const panel = wrapper.findComponent(BrutPanel);
    expect(panel.exists()).toBe(true);
    expect(panel.props("title")).toBe("轮次台账");
  });

  it("renders one row per round with its index and label", () => {
    const wrapper = mount(RoundLedger, { props: { rounds } });

    expect(wrapper.findAll(".round-ledger__row")).toHaveLength(5);
    expect(wrapper.findAll(".round-ledger__index").map((node) => node.text())).toEqual([
      "1",
      "2",
      "3",
      "4",
      "5"
    ]);
    expect(wrapper.findAll(".round-ledger__label").map((node) => node.text())).toEqual([
      "项目深挖",
      "基础八股",
      "项目复盘",
      "系统设计",
      "反问环节"
    ]);
  });

  it.each([
    ["pass", "✓"],
    ["fail", "✕"],
    ["done", "已答"],
    ["current", "回答中"],
    ["todo", "—"]
  ] as const)("maps status %s to row/badge classes and badge text %s", (status, badgeText) => {
    const wrapper = mount(RoundLedger, {
      props: { rounds: [{ index: 1, label: "某一轮", status }] }
    });

    expect(wrapper.find(".round-ledger__row").classes()).toContain(
      `round-ledger__row--${status}`
    );

    const badge = wrapper.find(".round-ledger__badge");
    expect(badge.classes()).toContain(`round-ledger__badge--${status}`);
    expect(badge.text()).toBe(badgeText);
  });

  it("renders the done badge as a neutral status distinct from pass and todo", () => {
    const wrapper = mount(RoundLedger, {
      props: { rounds: [{ index: 1, label: "项目深挖", status: "done" }] }
    });

    const row = wrapper.find(".round-ledger__row");
    expect(row.classes()).toContain("round-ledger__row--done");
    expect(row.classes()).not.toContain("round-ledger__row--pass");

    const badgeClasses = wrapper.find(".round-ledger__badge").classes();
    expect(badgeClasses).toContain("round-ledger__badge--done");
    expect(badgeClasses).not.toContain("round-ledger__badge--pass");
    expect(badgeClasses).not.toContain("round-ledger__badge--todo");
  });
});

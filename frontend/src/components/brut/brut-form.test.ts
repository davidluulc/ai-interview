import { mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { describe, expect, it } from "vitest";
import BrutButton from "./BrutButton.vue";
import BrutEmpty from "./BrutEmpty.vue";
import BrutField from "./BrutField.vue";
import BrutSkeleton from "./BrutSkeleton.vue";

describe("BrutField", () => {
  it("renders the label above the input inside one label element", () => {
    const wrapper = mount(BrutField, {
      props: { label: "候选人", modelValue: "" }
    });

    const root = wrapper.find("label.brut-field");
    expect(root.exists()).toBe(true);
    expect(root.find(".brut-field__label").text()).toBe("候选人");

    const children = Array.from(root.element.children).map((el) => el.tagName);
    expect(children).toEqual(["SPAN", "INPUT"]);
  });

  it("shows the current modelValue in the input", () => {
    const wrapper = mount(BrutField, {
      props: { label: "岗位", modelValue: "前端工程师" }
    });

    expect(wrapper.find("input").element.value).toBe("前端工程师");
  });

  it("defaults the input type to text and passes type through", () => {
    const text = mount(BrutField, { props: { label: "姓名", modelValue: "" } });
    expect(text.find("input").attributes("type")).toBe("text");

    const password = mount(BrutField, {
      props: { label: "密码", modelValue: "", type: "password" }
    });
    expect(password.find("input").attributes("type")).toBe("password");
  });

  it("passes the placeholder through", () => {
    const wrapper = mount(BrutField, {
      props: { label: "姓名", modelValue: "", placeholder: "请输入姓名" }
    });

    expect(wrapper.find("input").attributes("placeholder")).toBe("请输入姓名");
  });

  it("emits update:modelValue with the typed value", async () => {
    const wrapper = mount(BrutField, {
      props: { label: "姓名", modelValue: "" }
    });

    await wrapper.find("input").setValue("张三");

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["张三"]);
  });

  it("binds two-way through v-model on a host component", async () => {
    const host = defineComponent({
      components: { BrutField },
      data: () => ({ name: "旧值" }),
      template: `<BrutField label="姓名" v-model="name" />`
    });
    const wrapper = mount(host);
    expect(wrapper.find("input").element.value).toBe("旧值");

    await wrapper.find("input").setValue("新值");

    const vm = wrapper.vm as { name: string };
    expect(vm.name).toBe("新值");
    expect(wrapper.find("input").element.value).toBe("新值");
  });
});

describe("BrutEmpty", () => {
  it("renders a black-headed small panel with title and action button", () => {
    const wrapper = mount(BrutEmpty, {
      props: { title: "暂无面试记录", actionLabel: "新建面试" }
    });

    expect(wrapper.classes()).toContain("brut-empty");
    expect(wrapper.find(".brut-empty__head").exists()).toBe(true);
    expect(wrapper.find(".brut-empty__title").text()).toBe("暂无面试记录");

    const button = wrapper.findComponent(BrutButton);
    expect(button.exists()).toBe(true);
    expect(button.text()).toBe("新建面试");
  });

  it("emits action when the action button is clicked", async () => {
    const wrapper = mount(BrutEmpty, {
      props: { title: "暂无数据", actionLabel: "刷新" }
    });

    await wrapper.find("button").trigger("click");

    expect(wrapper.emitted("action")).toHaveLength(1);
  });
});

describe("BrutSkeleton", () => {
  it("renders a black head plus one gray block in panel variant", () => {
    const wrapper = mount(BrutSkeleton, { props: { variant: "panel" } });

    expect(wrapper.classes()).toContain("brut-skeleton--panel");
    expect(wrapper.find(".brut-skeleton__head").exists()).toBe(true);
    expect(wrapper.findAll(".brut-skeleton__block")).toHaveLength(1);
  });

  it("renders exactly the requested number of row blocks in rows variant", () => {
    const wrapper = mount(BrutSkeleton, {
      props: { variant: "rows", rows: 5 }
    });

    expect(wrapper.classes()).toContain("brut-skeleton--rows");
    expect(wrapper.findAll(".brut-skeleton__row")).toHaveLength(5);
  });

  it("defaults rows to 3", () => {
    const wrapper = mount(BrutSkeleton, { props: { variant: "rows" } });

    expect(wrapper.findAll(".brut-skeleton__row")).toHaveLength(3);
  });
});

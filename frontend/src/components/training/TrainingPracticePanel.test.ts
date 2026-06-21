import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type * as trainingApi from "@/api/training";
import TrainingPracticePanel from "./TrainingPracticePanel.vue";

describe("TrainingPracticePanel", () => {
  it("renders practice question and guidance", () => {
    const wrapper = mount(TrainingPracticePanel, {
      props: {
        ...validProps(),
        practice: makePractice({
          question: "什么是 Hit@K？",
          answerKeyPoints: ["Hit@K", "MRR"],
          commonMistakes: ["只解释字段名"],
          oneMinuteTemplate: "按指标定义、用途、项目落地回答。"
        })
      }
    });

    expect(wrapper.text()).toContain("什么是 Hit@K？");
    expect(wrapper.text()).toContain("Hit@K");
    expect(wrapper.text()).toContain("只解释字段名");
    expect(wrapper.text()).toContain("按指标定义");
  });

  it("emits answer updates and submit", async () => {
    const wrapper = mount(TrainingPracticePanel, { props: validProps() });

    await wrapper.get('[data-testid="practice-answer"]').setValue("我的回答");
    await wrapper.get('[data-testid="submit-practice"]').trigger("click");

    expect(wrapper.emitted("update:answerText")?.[0]).toEqual(["我的回答"]);
    expect(wrapper.emitted("submit")).toHaveLength(1);
    expect(wrapper.text()).not.toContain("回答状态");
    expect(wrapper.text()).not.toContain("自评分");
    expect(wrapper.text()).toContain("提交给 AI 批改");
  });

  it("shows practice attempt count without making mastery the main signal", () => {
    const wrapper = mount(TrainingPracticePanel, {
      props: {
        ...validProps(),
        result: {
          id: 1,
          weakTag: "rag_quality",
          title: "RAG 质量训练",
          description: "",
          status: "done",
          priority: "high",
          masteryScore: 85,
          attemptCount: 2
        }
      }
    });

    expect(wrapper.text()).toContain("已练习 2 次");
    expect(wrapper.text()).not.toContain("最新掌握度");
  });

  it("renders coach review and disables duplicate submit", async () => {
    const wrapper = mount(TrainingPracticePanel, {
      props: {
        ...validProps(),
        practiceSubmitted: true,
        result: {
          id: 1,
          weakTag: "rag_quality",
          title: "RAG 质量训练",
          description: "",
          status: "done",
          priority: "high",
          masteryScore: 85,
          attemptCount: 2,
          metadata: {
            lastPractice: {
              review: {
                score: 62,
                qualityLabel: "部分覆盖",
                referenceAnswer: "参考答案正文",
                strengths: ["已覆盖：Hit@K"],
                issues: ["缺少关键点：MRR"],
                missingKeyPoints: ["MRR"],
                rewrittenAnswer: "建议改写版本",
                nextPractice: "下一步练习重点"
              }
            }
          }
        }
      }
    });

    expect(wrapper.text()).toContain("AI 批改结果");
    expect(wrapper.text()).toContain("部分覆盖");
    expect(wrapper.text()).toContain("参考答案正文");
    expect(wrapper.text()).toContain("缺少关键点：MRR");
    expect(wrapper.text()).toContain("建议改写版本");
    expect(wrapper.text()).toContain("下一步练习重点");
    expect(wrapper.get('[data-testid="submit-practice"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-testid="submit-practice"]').trigger("click");

    expect(wrapper.emitted("submit")).toBeUndefined();
  });
});

function validProps() {
  return {
    practice: makePractice(),
    answerText: "",
    answerStatus: "模糊" as trainingApi.TrainingAnswerStatus,
    selfRating: null,
    loading: false,
    error: "",
    result: null,
    practiceSubmitting: false,
    practiceSubmitted: false
  };
}

function makePractice(overrides: Partial<trainingApi.TrainingPractice> = {}): trainingApi.TrainingPractice {
  return {
    weakTag: "rag_quality",
    weakLabel: "RAG 质量评估",
    mode: "coach",
    difficulty: "basic",
    question: "什么是 Hit@K？",
    answerKeyPoints: ["Hit@K"],
    commonMistakes: [],
    oneMinuteTemplate: "",
    relatedTags: [],
    rubric: ["是否覆盖：Hit@K"],
    fallbackUsed: false,
    ...overrides
  };
}

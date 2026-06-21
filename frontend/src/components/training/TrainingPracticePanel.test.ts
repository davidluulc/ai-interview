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
    await wrapper.get('[data-testid="answer-status-complete"]').trigger("click");
    await wrapper.get('[data-testid="self-rating-4"]').trigger("click");
    await wrapper.get('[data-testid="submit-practice"]').trigger("click");

    expect(wrapper.emitted("update:answerText")?.[0]).toEqual(["我的回答"]);
    expect(wrapper.emitted("update:answerStatus")?.[0]).toEqual(["完整"]);
    expect(wrapper.emitted("update:selfRating")?.[0]).toEqual([4]);
    expect(wrapper.emitted("submit")).toHaveLength(1);
  });

  it("shows latest practice result", () => {
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

    expect(wrapper.text()).toContain("最新掌握度 85");
    expect(wrapper.text()).toContain("累计练习 2 次");
  });

  it("renders correction feedback and disables duplicate submit", async () => {
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
              feedback: {
                qualityLabel: "部分覆盖",
                coveredKeyPoints: ["Hit@K"],
                missingKeyPoints: ["MRR"],
                correctionTips: ["建议补充：MRR"],
                nextAction: "补齐缺失要点"
              }
            }
          }
        }
      }
    });

    expect(wrapper.text()).toContain("练习反馈");
    expect(wrapper.text()).toContain("部分覆盖");
    expect(wrapper.text()).toContain("已覆盖：Hit@K");
    expect(wrapper.text()).toContain("建议补充：MRR");
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

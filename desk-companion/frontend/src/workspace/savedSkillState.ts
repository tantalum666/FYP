import type { Translate } from "../types";

export interface SkillCheckDraft {
  title: string;
  stepsText: string;
  namesText: string;
  passed: boolean;
}

export interface SkillRunFill {
  version: number;
  input_hash: string;
}

export function checkBody(draft: SkillCheckDraft) {
  if (!draft.passed) return { ok: false as const, reason: "not_passed" };
  const title = draft.title.trim();
  const steps = draft.stepsText
    .split("\n")
    .map((step) => step.trim())
    .filter(Boolean);
  const input_names = draft.namesText
    .split(/[\n,]/)
    .map((name) => name.trim())
    .filter(Boolean);
  if (!title || steps.length === 0 || input_names.length === 0)
    return { ok: false as const, reason: "incomplete" };
  return {
    ok: true as const,
    body: {
      title,
      steps,
      input_names,
      validation: "required_inputs" as const,
      passed: true as const,
    },
  };
}

/** A blank note is omitted. The request must not send an empty note as a value. */
export function runBody(inputs: Record<string, string>, note: string) {
  const body: { inputs: Record<string, string>; note?: string } = { inputs };
  const text = note.trim();
  if (text) body.note = text;
  return body;
}

export function decisionBody(run: SkillRunFill, action: "approve" | "reject") {
  return {
    action,
    expected_version: run.version,
    input_hash: run.input_hash,
  };
}

export function fillReady(names: string[], inputs: Record<string, string>) {
  return names.every((name) => (inputs[name] ?? "").trim().length > 0);
}

export function skillOutcomeNotice(status: string, t: Translate) {
  if (status === "succeeded")
    return t(
      "Saved on this desk after your approval.",
      "已按你的批准保存在这台桌上。",
    );
  if (status === "rejected") return t("You stopped this one.", "你停掉了这一次。");
  return t("Waiting for your approval.", "等待你的批准。");
}

export function skillError(code: string, t: Translate) {
  const messages: Record<string, [string, string]> = {
    not_passed: [
      "Mark it checked only after you have done it.",
      "只有你亲手核对之后，才勾选这一项。",
    ],
    incomplete: [
      "Add a title, one step, and one input name.",
      "请填写标题、一个步骤和一个输入名称。",
    ],
    CHECK_NOT_PASSED: [
      "Mark it checked only after you have done it.",
      "只有你亲手核对之后，才勾选这一项。",
    ],
    SKILL_LIMIT: [
      "This desk already has its limit of saved skills.",
      "这台桌面的已保存做法已到上限。",
    ],
    SKILL_INPUT_MISSING: ["Fill every named input.", "请填好每一个输入。"],
    SKILL_INPUT_UNKNOWN: [
      "Only the named inputs are accepted.",
      "只能填写已列出的输入。",
    ],
    SKILL_INPUT_INVALID: ["Use a short plain input.", "请填写简短的普通文字。"],
    SKILL_INPUT_CHANGED: [
      "This approval does not match the prepared inputs. Prepare it again.",
      "这次批准和已准备的输入不一致。请重新准备。",
    ],
    SKILL_NOTE_EMPTY: [
      "Write a note, or clear the field.",
      "请写下一句备注，或把这一栏清空。",
    ],
    VERSION_CONFLICT: [
      "This changed. Refresh it before deciding.",
      "内容已变化。请先刷新再决定。",
    ],
    RUN_CLOSED: ["This one is already decided.", "这一次已经决定过了。"],
    OPERATION_ID_CONFLICT: [
      "That attempt was already used. Refresh and try again.",
      "这次尝试已经用过。请刷新后再试。",
    ],
    PRIVATE_CONTEXT_HIDDEN: ["Private details are hidden.", "私人内容已隐藏。"],
    VALIDATION_FAILED: [
      "Check the title, steps, and input names.",
      "请检查标题、步骤和输入名称。",
    ],
    RUN_LIMIT: [
      "This desk already has its limit of prepared runs.",
      "已准备的运行已到上限。",
    ],
  };
  const pair = messages[code];
  return pair
    ? t(pair[0], pair[1])
    : t("That could not be saved. Refresh and try again.", "这次没有保存。请刷新后再试。");
}

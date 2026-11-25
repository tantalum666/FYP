export type ReviewPage = "assistant" | "today" | "tasks" | "calendar" | "memory";
export type ReviewAction = (page: ReviewPage, itemId?: string) => void;
type Target = { page: ReviewPage; itemId?: string; en: string; zh: string };

export function noticeTarget(item: { id: string; kind?: string; task_id?: string | null }): Target | undefined {
  switch (item.kind) {
    case "initiative": return {page:"assistant",itemId:item.id,en:"View in conversation",zh:"在对话中查看"};
    case "morning_brief": return {page:"today",en:"View today",zh:"查看今天"};
    case "evening_check": return {page:"tasks",en:"View tasks",zh:"查看待办"};
    case "followup": return {page:"tasks",itemId:item.task_id || undefined,en:item.task_id ? "Open task" : "View tasks",zh:item.task_id ? "打开待办" : "查看待办"};
    case "memory_morning":
    case "memory_followup": return {page:"memory",en:"View memories",zh:"查看记忆"};
    case "mail_followup": return {page:"tasks",itemId:item.task_id || undefined,en:item.task_id ? "Open the task" : "View tasks",zh:item.task_id ? "打开事务" : "查看待办"};
    case "calendar_deadline":
    case "calendar_conflict":
    case "calendar_decision":
    case "calendar_cancelled": return {page:"calendar",en:"View calendar",zh:"查看日历"};
  }
}

export function cueTarget(cue: {id: string; kind: string; task_id?: string}): Target | undefined {
  if (cue.kind === "task") return cue.task_id ? {page:"tasks",itemId:cue.task_id,en:"Open task",zh:"打开待办"} : undefined;
  if (!["initiative","morning_brief","evening_check"].includes(cue.kind)) return undefined;
  return noticeTarget(cue);
}

export function findingSource(source: {kind:string;ref:string}): {page:"tasks" | "memory" | "calendar"; itemId:string} | undefined {
  const cut=source.ref.indexOf(":");
  if (cut < 0 || source.ref.slice(0,cut)!==source.kind) return undefined;
  const rest=source.ref.slice(cut+1);
  if (!rest.trim()) return undefined;
  if (source.kind==="task") return {page:"tasks",itemId:rest};
  if (source.kind==="memory") return {page:"memory",itemId:rest};
  if (source.kind==="calendar" && !rest.startsWith("google:") && /^[^:]+:.+$/.test(rest)) return {page:"calendar",itemId:source.ref};
}

export function findingMatchesNotice(finding:{id:string;notice_id?:string|null},noticeId?:string|null) {
  return !!noticeId && (finding.notice_id === noticeId || (!finding.notice_id && noticeId === "insight-"+finding.id));
}

export function canActOnFinding(finding:{historical?:boolean;withdrawn?:boolean}) {
  return !finding.historical && !finding.withdrawn;
}

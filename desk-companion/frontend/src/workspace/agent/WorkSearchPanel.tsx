import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { ArtifactList } from "./ArtifactList";
import { agentError, modeLabel, stateLabel } from "./labels";
import { SourcePreview } from "./SourcePreview";
import { useWorkSearch } from "./useWorkSearch";
import { searchKinds, workHitKey } from "./workSearch";
import type {
  MatchedField,
  OutputMembership,
  WorkSearchHit,
  WorkSearchKind,
  WorkSearchResponse,
} from "./workSearch";

export function workKindLabel(kind: WorkSearchKind, t: Translate) {
  const labels: Record<WorkSearchKind, [string, string]> = {
    all: ["All", "全部"],
    run: ["Work", "工作"],
    artifact: ["Files", "文件"],
    source: ["Sources", "来源"],
  };
  return t(...labels[kind]);
}
export function outputMembershipLabel(value: OutputMembership, t: Translate) {
  const labels: Record<OutputMembership, [string, string]> = {
    current: ["Current output", "当前输出"],
    earlier: ["Earlier output", "较早输出"],
    unknown: ["Output relationship unknown", "输出关系未知"],
    unlinked: ["No linked work", "未关联工作"],
  };
  return t(...labels[value]);
}
export function matchedFieldLabel(value: MatchedField, t: Translate) {
  const labels: Record<MatchedField, [string, string]> = {
    id: ["Record ID", "记录ID"],
    title: ["Name or current goal", "名称或当前目标"],
    source_name: ["Linked source name", "关联来源名称"],
    current_linked_goal: ["Current linked goal", "当前关联目标"],
  };
  return t(...labels[value]);
}
export function WorkSearchResults({
  page,
  t,
  disabled,
  opening,
  onOpen,
}: {
  page: WorkSearchResponse;
  t: Translate;
  disabled: boolean;
  opening: string | null;
  onOpen: (hit: WorkSearchHit) => void;
}) {
  return (
    <div className="agent-search-results">
      {page.total > 1 && (
        <p className="workspace-hint">
          {t(
            "Several records match. Choose the exact record by its type, ID and date; similar names may refer to different work.",
            "找到多个记录。请根据类型、ID和日期选择确切记录；相同名称可能属于不同工作。",
          )}
        </p>
      )}
      {!page.items.length && (
        <p role="status">
          {t("No matching saved records.", "没有匹配的已保存记录。")}
        </p>
      )}
      <ul className="agent-search-list">
        {page.items.map((hit) => (
          <li key={workHitKey(hit)} className="agent-search-hit">
            <small>
              {workKindLabel(hit.kind, t)} · {hit.id}
            </small>
            <h4 className="agent-search-title" title={hit.title}>
              {hit.title || t("Untitled record", "未命名记录")}
            </h4>
            <small>{hit.timestamp ?? t("Date unknown", "日期未知")}</small>
            {hit.kind === "run" ? (
              <p>
                {stateLabel(hit.state, t)} · {modeLabel(hit.mode ?? "", t)}
                {hit.version !== null && (
                  <>
                    {" "}
                    · {t("Version", "版本")} {hit.version}
                  </>
                )}
                {hit.plan_revision !== null && (
                  <>
                    {" "}
                    · {t("Plan", "计划")} {hit.plan_revision}
                  </>
                )}
              </p>
            ) : (
              <p>
                {hit.format?.toUpperCase() ?? t("Format unknown", "格式未知")} ·{" "}
                {hit.byte_count === null
                  ? t("Size unknown", "大小未知")
                  : `${hit.byte_count.toLocaleString()} ${t("bytes", "字节")}`}{" "}
                · {t("Last recorded", "上次记录")}:{" "}
                {hit.recorded_status === "verified"
                  ? t("verified", "已核验")
                  : t("unknown", "未知")}
              </p>
            )}
            {hit.kind === "artifact" && (
              <>
                <p>{outputMembershipLabel(hit.output_membership, t)}</p>
                {hit.run_id && (
                  <small>
                    {t("Linked work ID", "关联工作ID")}: {hit.run_id}
                  </small>
                )}
                {hit.current_linked_goal !== null && (
                  <p
                    className="agent-search-title"
                    title={hit.current_linked_goal}
                  >
                    {t("Current linked goal", "当前关联目标")}:{" "}
                    {hit.current_linked_goal}
                  </p>
                )}
              </>
            )}
            {!!hit.matched_fields.length && (
              <small>
                {t("Matched fields", "匹配字段")}:{" "}
                {hit.matched_fields
                  .map((field) => matchedFieldLabel(field, t))
                  .join(" · ")}
              </small>
            )}
            {hit.kind !== "source" &&
              hit.matched_fields.includes("source_name") && (
                <small>
                  {t("Linked sources", "关联来源")}:{" "}
                  {hit.source_names.join(" · ")}
                </small>
              )}
            <button
              type="button"
              className="secondary"
              disabled={disabled}
              onClick={() => onOpen(hit)}
            >
              {opening === workHitKey(hit)
                ? t("Opening exact record…", "正在打开确切记录…")
                : hit.kind === "run"
                  ? t("Open this work", "打开此工作")
                  : hit.kind === "artifact"
                    ? t("Inspect this file", "检查此文件")
                    : t("Preview this source", "预览此来源")}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
export function WorkSearchPanel({
  t,
  fence,
  epoch,
  fresh,
  onOpenRun,
}: {
  t: Translate;
  fence: ResponseFence;
  epoch: number;
  fresh: boolean;
  onOpenRun: (id: string) => void;
}) {
  const search = useWorkSearch(fence, epoch, fresh);
  async function open(hit: WorkSearchHit) {
    const searchEpoch = search.fence.capture();
    const detail = await search.open(hit);
    if (
      detail?.kind === "run" &&
      fence.accepts(epoch) &&
      search.fence.accepts(searchEpoch)
    )
      onOpenRun(detail.value.run.id);
  }
  return (
    <section
      className="agent-search"
      aria-label={t("Find saved work", "查找已保存工作")}
    >
      <h3>{t("Find saved work", "查找已保存工作")}</h3>
      <p className="workspace-hint">
        {t(
          "Search local names, current goals, IDs and linked source names. File contents are not searched. Search runs only when you submit; leave the query empty to browse.",
          "搜索本地名称、当前目标、ID和关联来源名称，不搜索文件正文。仅在提交时查询；留空可浏览记录。",
        )}
      </p>
      <form
        className="agent-search-form"
        onSubmit={(event) => {
          event.preventDefault();
          search.submit();
        }}
      >
        <label>
          {t("Search saved records", "搜索已保存记录")}
          <input
            type="search"
            value={search.query}
            disabled={!search.active}
            onChange={(event) => search.setQuery(event.target.value)}
            autoComplete="off"
            spellCheck={false}
            placeholder={t("Name, goal or exact ID", "名称、目标或精确ID")}
          />
        </label>
        <label>
          {t("Record type", "记录类型")}
          <select
            value={search.kind}
            disabled={!search.active}
            onChange={(event) =>
              search.setKind(event.target.value as WorkSearchKind)
            }
          >
            {searchKinds.map((kind) => (
              <option key={kind} value={kind}>
                {workKindLabel(kind, t)}
              </option>
            ))}
          </select>
        </label>
        <div className="workspace-inline-actions">
          <button type="submit" className="primary" disabled={!search.active}>
            {t("Search", "搜索")}
          </button>
          <button type="button" className="secondary" onClick={search.clear}>
            {t("Clear search", "清除搜索")}
          </button>
        </div>
      </form>
      {!search.active && (
        <p role="status">
          {t(
            "Search is unavailable until this private view has a current connection. Reopen search after signing in or changing privacy.",
            "此私人界面连接恢复有效后才能搜索。重新登录或更改隐私后，请重新打开搜索。",
          )}
        </p>
      )}
      {search.loading && (
        <p role="status">
          {t("Searching saved records…", "正在搜索已保存记录…")}
        </p>
      )}
      {!!search.error && (
        <p className="error-message" role="alert">
          {agentError(search.error, t)}
        </p>
      )}
      {search.value && (
        <>
          <p role="status" className="agent-search-summary">
            {search.value.input.query
              ? `${t("Results for", "搜索结果")}: ${search.value.input.query}`
              : t("Browsing saved records", "正在浏览已保存记录")}{" "}
            · {workKindLabel(search.value.input.kind, t)} ·{" "}
            {search.value.page.total} {t("matches", "项匹配")}
            {search.value.page.total > 0 && (
              <>
                {" "}
                · {search.value.input.offset + 1}–
                {search.value.input.offset + search.value.page.items.length}
              </>
            )}
          </p>
          <p className="workspace-hint">
            {t(
              "These are saved metadata, not fresh file checks. File details, previews and downloads recheck stored bytes. A current linked goal may have changed since an earlier output was written.",
              "这些是已保存的元数据，不是最新文件核验。打开文件详情、预览或下载时会重新检查保存字节；较早输出写入后，当前关联目标可能已改变。",
            )}
          </p>
          <WorkSearchResults
            page={search.value.page}
            t={t}
            disabled={!search.active || search.opening !== null}
            opening={search.opening}
            onOpen={(hit) => void open(hit)}
          />
          {search.value.input.offset > 0 && (
            <button
              type="button"
              className="secondary"
              disabled={
                !search.active || search.loading || search.opening !== null
              }
              onClick={search.previousPage}
            >
              {t("Previous results", "上一页结果")}
            </button>
          )}
          {search.value.page.next_offset !== null && (
            <button
              type="button"
              className="secondary"
              disabled={
                !search.active || search.loading || search.opening !== null
              }
              onClick={search.nextPage}
            >
              {t("Next results", "下一页结果")}
            </button>
          )}
        </>
      )}
      {!!search.detailError && (
        <p className="error-message" role="alert">
          {agentError(search.detailError, t)}
        </p>
      )}
      {search.detail?.kind === "artifact" && (
        <div className="agent-notice">
          <button
            type="button"
            className="secondary"
            onClick={search.clearDetail}
          >
            {t("Close file details", "关闭文件详情")}
          </button>
          <ArtifactList
            key={search.detail.value.id}
            artifacts={[search.detail.value]}
            t={t}
            fence={search.fence}
          />
        </div>
      )}
      {search.detail?.kind === "source" && (
        <SourcePreview
          key={search.detail.value.id}
          source={search.detail.value}
          t={t}
          fence={search.fence}
          onClose={search.clearDetail}
        />
      )}
    </section>
  );
}

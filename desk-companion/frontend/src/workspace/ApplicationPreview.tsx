import type { Translate } from "../types";
import type { ApplicationStep } from "./applicationTypes";

export function ApplicationPreview({
  step,
  t,
}: {
  step: ApplicationStep;
  t: Translate;
}) {
  return (
    <div className="application-preview">
      <p>
        <strong>{step.filename}</strong>
        {step.kind === "pdf"
          ? t(
              " · Export a verified document to PDF",
              " · 将已核验文档导出为 PDF",
            )
          : step.source_job_id
            ? t(" · Update the existing file", " · 更新已有文件")
            : t(" · Create a new file", " · 创建新文件")}
      </p>
      {step.kind === "workbook" &&
        step.sheets.map((sheet) => (
          <div key={sheet.sheet}>
            <h5>{sheet.sheet}</h5>
            <div
              className="application-preview-table"
              tabIndex={0}
              aria-label={t("Workbook changes", "工作簿修改")}
            >
              <table>
                <thead>
                  <tr>
                    <th>{t("Cell", "单元格")}</th>
                    <th>{t("New value or formula", "新值或公式")}</th>
                  </tr>
                </thead>
                <tbody>
                  {sheet.cells.map((cell) => (
                    <tr key={cell.cell}>
                      <th>{cell.cell}</th>
                      <td>
                        {cell.kind === "formula" ? (
                          <code>{cell.value}</code>
                        ) : (
                          String(cell.value)
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      {step.kind === "document" && (
        <>
          <p>
            {step.mode === "append"
              ? t(
                  "Add these sections after the existing content.",
                  "在已有内容后加入以下章节。",
                )
              : t("Use the following document content.", "使用以下文档内容。")}
          </p>
          {step.blocks.map((block, index) =>
            block.kind === "table" ? (
              <div
                key={index}
                className="application-preview-table"
                tabIndex={0}
              >
                <table>
                  <tbody>
                    {block.rows.map((row, rowIndex) => (
                      <tr key={rowIndex}>
                        {row.map((cell, col) => (
                          <td key={col}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : block.kind === "page_break" ? (
              <p key={index} className="workspace-hint">
                {t("New page", "另起一页")}
              </p>
            ) : block.kind === "title" || block.kind === "heading" ? (
              <h5 key={index}>{block.text}</h5>
            ) : (
              <p key={index}>{block.text}</p>
            ),
          )}
        </>
      )}
      {step.kind === "text" && <pre tabIndex={0}>{step.text}</pre>}
      {step.kind === "pdf" && (
        <p>
          {t(
            "The source document is checked again before export.",
            "导出前会再次核对源文档。",
          )}
        </p>
      )}
    </div>
  );
}

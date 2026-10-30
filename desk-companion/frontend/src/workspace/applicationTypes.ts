export type ApplicationStep =
  | {
      kind: "workbook";
      filename: string;
      source_job_id?: string | null;
      sheets: Array<{
        sheet: string;
        cells: Array<{
          cell: string;
          kind: "text" | "number" | "formula";
          value: string | number;
        }>;
      }>;
    }
  | {
      kind: "document";
      filename: string;
      source_job_id?: string | null;
      mode: "replace" | "append";
      blocks: Array<
        | {
            kind: "title" | "heading" | "paragraph" | "page_break";
            text: string;
          }
        | { kind: "table"; rows: string[][] }
      >;
    }
  | {
      kind: "pdf";
      filename: string;
      source_job_id: string;
      replace_job_id?: string | null;
    }
  | {
      kind: "text";
      filename: string;
      text: string;
      source_job_id?: string | null;
    };

export interface ApplicationState {
  task_id: string;
  stages: Array<{
    stage: string;
    title: string;
    job_id: string;
    state: import("./jobTypes").JobState;
    error: string | null;
    filename: string;
    task_version: number;
  }>;
  artifacts: Array<{
    filename: string;
    job_id: string;
    sha256: string;
    bytes: number;
  }>;
  unresolved_jobs: string[];
}

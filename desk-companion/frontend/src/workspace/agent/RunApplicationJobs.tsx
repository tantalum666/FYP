import { useRef, useState } from "react";
import type { Translate } from "../../types";
import type { ComputerJob } from "../jobTypes";
import type { JobAction } from "../jobRequests";
import { jobApprovalPayload, requestJobAction } from "../jobRequests";
import { JobActionCard } from "../JobActionCard";
import { ExportLink } from "../ExportLink";
import { errorText } from "../../api";
import type { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import { useDraftGuard } from "../../components/DraftGuard";
import { RequestFeedback } from "./RequestFeedback";

type Props = {
  jobs: ComputerJob[];
  t: Translate;
  fence: ResponseFence;
  fresh: boolean;
  active: boolean;
  onChanged: () => void;
};

function ApplicationCard({
  job,
  t,
  fence,
  fresh,
  active,
  onChanged,
}: Omit<Props, "jobs"> & { job: ComputerJob }) {
  const mutation = usePrivateMutation();
  const epoch = useRef(fence.capture());
  const [reading, setReading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const working = useRef(false);
  useDraftGuard(mutation.pending, mutation.busy);
  const accepts = () => fresh && fence.accepts(epoch.current);
  async function act(action: JobAction) {
    if (!accepts() || working.current || mutation.busy) return;
    if (action === "approve") {
      if (!active) return;
      await mutation.run(
        `/computer/jobs/${job.id}/approve`,
        jobApprovalPayload(job),
        () => {
          if (fence.accepts(epoch.current)) onChanged();
        },
      );
      if (fence.accepts(epoch.current)) onChanged();
      return;
    }
    working.current = true;
    setReading(true);
    setError(null);
    try {
      await requestJobAction(job, action);
    } catch (reason) {
      if (fence.accepts(epoch.current)) setError(reason);
    } finally {
      working.current = false;
      if (fence.accepts(epoch.current)) {
        setReading(false);
        onChanged();
      }
    }
  }
  return (
    <div>
      <JobActionCard
        compact
        job={job}
        t={t}
        fresh={fresh}
        available={fresh && active}
        busy={mutation.busy || mutation.pending || reading}
        cancelling={reading || !fresh}
        onAction={(action) => void act(action)}
      />
      <RequestFeedback
        t={t}
        mutation={{
          ...mutation,
          busy: mutation.busy || !fresh,
          retry: () => (accepts() ? mutation.retry() : Promise.resolve(false)),
        }}
      />
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}

export function RunApplicationJobs(props: Props) {
  const [error, setError] = useState<unknown>(null);
  if (!props.jobs.length) return null;
  const latest = new Map<string, string>();
  for (const job of props.jobs)
    latest.set(`${job.task_id}/${job.request.step?.filename}`, job.id);
  return (
    <section>
      <h4>{props.t("Files", "文件")}</h4>
      {[...props.jobs]
        .sort((a, b) => {
          const priority = (job: ComputerJob) =>
            ["review", "unknown", "queued", "running", "verifying"].includes(
              job.state,
            )
              ? 0
              : 1;
          return priority(a) - priority(b);
        })
        .map((job) =>
          latest.get(`${job.task_id}/${job.request.step?.filename}`) ===
          job.id ? (
            <ApplicationCard key={job.id} {...props} job={job} />
          ) : (
            <p key={job.id}>
              {props.t("Previous version", "历史版本")} ·{" "}
              <ExportLink
                path={`/computer/jobs/${job.id}/artifact`}
                filename={job.request.step?.filename ?? "artifact"}
                onError={setError}
              >
                {job.request.title}
              </ExportLink>
            </p>
          ),
        )}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, props.t)}
        </p>
      )}
    </section>
  );
}

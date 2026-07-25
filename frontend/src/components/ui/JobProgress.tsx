export function JobProgress({
  label,
  status,
  detail,
}: {
  label: string;
  status: string;
  detail?: string;
}) {
  const running = ["queued", "running", "pending"].includes(status.toLowerCase());
  return (
    <div className="rounded-xl border border-slate-800 px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">{label}</span>
        <span className={running ? "text-amber-300" : "text-slate-400"}>{status}</span>
      </div>
      {detail ? <div className="mt-1 text-xs text-slate-500">{detail}</div> : null}
      {running ? (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-sky-500" />
        </div>
      ) : null}
    </div>
  );
}
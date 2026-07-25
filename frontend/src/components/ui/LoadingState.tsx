export function LoadingState({ label = "加载中..." }: { label?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-400">
      <div className="mx-auto mb-3 h-5 w-5 animate-pulse rounded-full bg-sky-500/70" />
      {label}
    </div>
  );
}
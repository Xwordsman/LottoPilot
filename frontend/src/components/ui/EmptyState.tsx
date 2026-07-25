export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/40 px-4 py-8 text-center">
      <div className="text-sm font-medium text-slate-200">{title}</div>
      {description ? <p className="mt-2 text-sm text-slate-500">{description}</p> : null}
    </div>
  );
}
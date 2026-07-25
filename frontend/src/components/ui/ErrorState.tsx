import { Button } from "@/components/ui/Button";

export function ErrorState({
  title = "加载失败",
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-2xl border border-rose-900/50 bg-rose-950/20 px-4 py-8 text-center">
      <div className="text-sm font-medium text-rose-300">{title}</div>
      {description ? <p className="mt-2 text-sm text-slate-400">{description}</p> : null}
      {onRetry ? (
        <div className="mt-4">
          <Button variant="secondary" onClick={onRetry}>
            重试
          </Button>
        </div>
      ) : null}
    </div>
  );
}
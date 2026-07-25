import { Skeleton } from "@/components/ui/skeleton"

export function LoadingState({ label = "加载中..." }: { label?: string }) {
  return (
    <div className="space-y-3 rounded-xl border bg-card p-6">
      <div className="flex items-center gap-3">
        <Skeleton className="size-5 rounded-full" />
        <div className="text-sm text-muted-foreground">{label}</div>
      </div>
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-24 w-full" />
    </div>
  )
}

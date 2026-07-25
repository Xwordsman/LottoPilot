import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export function JobProgress({
  label,
  status,
  detail,
}: {
  label: string
  status: string
  detail?: string
}) {
  const running = ["queued", "running", "pending"].includes(status.toLowerCase())

  return (
    <Card className="py-4">
      <CardContent className="space-y-2 px-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium">{label}</span>
          <Badge variant={running ? "default" : "secondary"}>{status}</Badge>
        </div>
        {detail ? <p className="text-xs text-muted-foreground">{detail}</p> : null}
        {running ? (
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                "h-full w-1/2 animate-pulse rounded-full bg-primary"
              )}
            />
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

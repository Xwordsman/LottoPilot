import { AlertCircle } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

export function ErrorState({
  title = "加载失败",
  description,
  onRetry,
}: {
  title?: string
  description?: string
  onRetry?: () => void
}) {
  return (
    <Alert variant="destructive">
      <AlertCircle />
      <AlertTitle>{title}</AlertTitle>
      {description ? <AlertDescription>{description}</AlertDescription> : null}
      {onRetry ? (
        <div className="col-start-2 mt-3">
          <Button size="sm" variant="outline" onClick={onRetry}>
            重试
          </Button>
        </div>
      ) : null}
    </Alert>
  )
}

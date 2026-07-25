import { cn } from "@/lib/utils"

export function NumberBall({
  n,
  tone = "red",
}: {
  n: number
  tone?: "red" | "blue"
}) {
  return (
    <span
      className={cn(
        "inline-flex size-8 items-center justify-center rounded-full text-xs font-semibold text-white shadow-sm",
        tone === "red" ? "bg-rose-500" : "bg-sky-500"
      )}
    >
      {String(n).padStart(2, "0")}
    </span>
  )
}

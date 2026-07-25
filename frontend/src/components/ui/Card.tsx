import type { PropsWithChildren } from "react";
import { cn } from "@/lib/cn";

export function Card({
  children,
  className,
}: PropsWithChildren<{ className?: string }>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-800/80 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/40 backdrop-blur",
        className,
      )}
    >
      {children}
    </div>
  );
}

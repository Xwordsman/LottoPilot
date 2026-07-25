import type { PropsWithChildren, ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost";
  }
>;

export function Button({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-sky-500 text-slate-950 hover:bg-sky-400",
        variant === "secondary" && "bg-slate-800 text-slate-100 hover:bg-slate-700",
        variant === "ghost" && "bg-transparent text-slate-300 hover:bg-slate-800/80",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

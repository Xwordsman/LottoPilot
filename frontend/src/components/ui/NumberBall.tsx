type Tone = "primary" | "secondary";

export function NumberBall({ n, tone = "primary" }: { n: number; tone?: Tone }) {
  return (
    <span
      className={
        tone === "primary"
          ? "inline-flex h-8 w-8 items-center justify-center rounded-full bg-rose-500/90 text-xs font-semibold text-white"
          : "inline-flex h-8 w-8 items-center justify-center rounded-full bg-sky-500/90 text-xs font-semibold text-slate-950"
      }
      title={tone === "primary" ? `主区 ${String(n).padStart(2, "0")}` : `次区 ${String(n).padStart(2, "0")}`}
      aria-label={tone === "primary" ? `主区号码 ${String(n).padStart(2, "0")}` : `次区号码 ${String(n).padStart(2, "0")}`}
    >
      {String(n).padStart(2, "0")}
    </span>
  );
}
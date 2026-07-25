import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { NumberBall } from "@/components/ui/NumberBall";

export type TicketCardData = {
  id: string;
  rank: number;
  primary_numbers: number[];
  secondary_numbers: number[];
  statistical_score: number;
  ai_score?: number | null;
  final_score: number;
  feature_summary?: Record<string, unknown>;
  tags?: Record<string, unknown> | string[] | null;
  explanation?: string | null;
  primary_hits?: number | null;
  secondary_hits?: number | null;
  prize_level?: string | null;
};

function tagList(tags: TicketCardData["tags"]): string[] {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags.map(String);
  if (Array.isArray((tags as { labels?: unknown }).labels)) {
    return ((tags as { labels: unknown[] }).labels || []).map(String);
  }
  return Object.keys(tags);
}

export function TicketCard({ ticket }: { ticket: TicketCardData }) {
  const [copied, setCopied] = useState(false);
  const labels = tagList(ticket.tags);
  const line = `${ticket.primary_numbers.map((n) => String(n).padStart(2, "0")).join(" ")} + ${ticket.secondary_numbers
    .map((n) => String(n).padStart(2, "0"))
    .join(" ")}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(line);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-medium">第 {ticket.rank} 组</div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
          <span>
            统计分 {Number(ticket.statistical_score).toFixed(1)}
            {ticket.ai_score != null ? ` · AI分 ${Number(ticket.ai_score).toFixed(1)}` : ""}
            {" · "}最终分 {Number(ticket.final_score).toFixed(1)}
            {ticket.primary_hits != null
              ? ` · 命中 ${ticket.primary_hits}+${ticket.secondary_hits ?? 0}`
              : ""}
            {ticket.prize_level ? ` · 奖级 ${ticket.prize_level}` : ""}
          </span>
          <Button variant="ghost" onClick={() => void copy()}>
            {copied ? "已复制" : "复制"}
          </Button>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {ticket.primary_numbers.map((n) => (
          <NumberBall key={`p-${ticket.id}-${n}`} n={n} tone="primary" />
        ))}
        {ticket.secondary_numbers.map((n) => (
          <NumberBall key={`s-${ticket.id}-${n}`} n={n} tone="secondary" />
        ))}
      </div>
      {labels.length ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {labels.map((label) => (
            <span
              key={`${ticket.id}-${label}`}
              className="rounded-full border border-slate-700 px-2 py-0.5 text-xs text-slate-300"
            >
              {label}
            </span>
          ))}
        </div>
      ) : null}
      {ticket.explanation ? <p className="mt-2 text-sm text-slate-400">{ticket.explanation}</p> : null}
    </div>
  );
}
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NumberBall } from "@/components/ui/number-ball";
import { Separator } from "@/components/ui/separator";
import { copyText } from "@/lib/clipboard";
import { formatTicketLine } from "@/lib/ticket-format";
import type { RecommendationTicket } from "@/types/recommendations";

function tagList(tags: RecommendationTicket["tags"]): string[] {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags.map(String);
  if (Array.isArray((tags as { labels?: unknown }).labels)) {
    return ((tags as { labels: unknown[] }).labels || []).map(String);
  }
  return Object.keys(tags);
}

export function TicketCard({ ticket }: { ticket: RecommendationTicket }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const labels = tagList(ticket.tags);
  const line = formatTicketLine(ticket);

  async function copy() {
    const ok = await copyText(line);
    if (!ok) {
      setFailed(true);
      setCopied(false);
      window.setTimeout(() => setFailed(false), 1800);
      return;
    }
    setFailed(false);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Card className="gap-4 py-4">
      <CardHeader className="border-b px-4 pb-4 [.border-b]:pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">第 {ticket.rank} 组</CardTitle>
            <CardDescription>
              统计 {Number(ticket.statistical_score).toFixed(1)}
              {ticket.ai_score != null
                ? ` · AI ${Number(ticket.ai_score).toFixed(1)}`
                : ""}
              {" · "}最终 {Number(ticket.final_score).toFixed(1)}
              {ticket.primary_hits != null
                ? ` · 命中 ${ticket.primary_hits}+${ticket.secondary_hits ?? 0}`
                : ""}
              {ticket.prize_level ? ` · 奖级 ${ticket.prize_level}` : ""}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">#{ticket.rank}</Badge>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                void copy();
              }}
            >
              {failed ? "复制失败" : copied ? "已复制" : "复制"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 px-4">
        <div className="flex flex-wrap gap-2">
          {ticket.primary_numbers.map((n, idx) => (
            <NumberBall key={`p-${ticket.id}-${idx}-${n}`} n={n} tone="red" />
          ))}
          {ticket.secondary_numbers.map((n, idx) => (
            <NumberBall key={`s-${ticket.id}-${idx}-${n}`} n={n} tone="blue" />
          ))}
        </div>
        {labels.length ? (
          <div className="flex flex-wrap gap-1.5">
            {labels.map((label) => (
              <Badge key={`${ticket.id}-${label}`} variant="outline">
                {label}
              </Badge>
            ))}
          </div>
        ) : null}
        {ticket.explanation ? (
          <>
            <Separator />
            <p className="text-sm leading-6 text-muted-foreground">{ticket.explanation}</p>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

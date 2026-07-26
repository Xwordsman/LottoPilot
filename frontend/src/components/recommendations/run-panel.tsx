import { Check, ChevronDown, ChevronRight, Copy, Trash2 } from "lucide-react";
import { useMemo, useState, type MouseEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TicketCard } from "@/components/ui/ticket-card";
import { copyText } from "@/lib/clipboard";
import { aiStatusLabel, lotteryLabel } from "@/lib/labels";
import { formatRunTickets } from "@/lib/ticket-format";
import { cn } from "@/lib/utils";
import type { RecommendationRun } from "@/types/recommendations";

type RunPanelProps = {
  run: RecommendationRun;
  defaultOpen?: boolean;
  actions?: ReactNode;
  className?: string;
  onDelete?: (runId: string) => void;
  deleting?: boolean;
};

export function RunPanel({
  run,
  defaultOpen = true,
  actions,
  className,
  onDelete,
  deleting = false,
}: RunPanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [copiedAll, setCopiedAll] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);

  const title = `${lotteryLabel(run.lottery_type)} · 目标期 ${run.target_issue ?? "—"}`;
  const ticketCount = run.tickets?.length ?? 0;
  const allText = useMemo(() => formatRunTickets(run), [run]);

  async function copyAll() {
    const ok = await copyText(allText);
    if (!ok) {
      setCopyError("复制失败，请手动选择文本");
      setCopiedAll(false);
      return;
    }
    setCopyError(null);
    setCopiedAll(true);
    window.setTimeout(() => setCopiedAll(false), 1600);
  }

  function handleDelete(e: MouseEvent) {
    e.stopPropagation();
    if (!onDelete) return;
    const ok = window.confirm(
      `确认删除「${lotteryLabel(run.lottery_type)} · 目标期 ${run.target_issue ?? "—"}」这期推荐？删除后不可恢复。`,
    );
    if (ok) onDelete(run.id);
  }

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="border-b pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <button
            type="button"
            className="flex min-w-0 flex-1 items-start gap-2 text-left"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            <span className="mt-1 text-muted-foreground">
              {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
            </span>
            <span className="min-w-0 space-y-1">
              <CardTitle className="text-base sm:text-lg">{title}</CardTitle>
              <CardDescription>
                复现编号 {run.seed ?? "自动"} · {aiStatusLabel(run.ai_status)}
                {ticketCount ? ` · ${ticketCount} 组` : ""}
                {run.evaluation
                  ? ` · 复盘命中 ${run.evaluation.best_primary_hits ?? "-"}+${
                      run.evaluation.best_secondary_hits ?? "-"
                    }`
                  : ""}
              </CardDescription>
            </span>
          </button>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                void copyAll();
              }}
            >
              {copiedAll ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copiedAll ? "已复制全部" : "复制本期全部"}
            </Button>
            {onDelete ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-destructive"
                disabled={deleting}
                onClick={handleDelete}
              >
                <Trash2 className="size-4" />
                {deleting ? "删除中..." : "删除本期"}
              </Button>
            ) : null}
            {actions}
            <Button type="button" variant="outline" size="sm" onClick={() => setOpen((v) => !v)}>
              {open ? "收起" : "展开"}
            </Button>
          </div>
        </div>
        {copyError ? <p className="mt-2 text-xs text-destructive">{copyError}</p> : null}
      </CardHeader>

      {open ? (
        <CardContent className="space-y-3 pt-4">
          {(run.tickets ?? [])
            .slice()
            .sort((a, b) => a.rank - b.rank)
            .map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
          <p className="text-xs text-muted-foreground">以上为模型评分与历史分析，不承诺中奖。</p>
        </CardContent>
      ) : null}
    </Card>
  );
}

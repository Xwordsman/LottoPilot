import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { PageHeader } from "@/components/ui/page-header";
import { apiRequest, ApiError } from "@/lib/api";
import type { LotteryType } from "@/types/draws";
import type { BacktestList, BacktestRun } from "@/types/recommendations";

type BacktestIssue = {
  id: string;
  target_draw_id?: string;
  training_cutoff_draw_id?: string;
  hit_metrics?: {
    best_primary_hits?: number | null;
    best_secondary_hits?: number | null;
    target_issue?: string | null;
  };
  baseline_metrics?: {
    avg_primary_hits?: number | null;
    baseline_avg_primary_hits?: number | null;
  };
  runtime_ms?: number;
};

type BacktestIssueList = {
  items: BacktestIssue[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export function BacktestsPage() {
  const queryClient = useQueryClient();
  const [lottery, setLottery] = useState<LotteryType>("ssq");
  const [startIssue, setStartIssue] = useState("");
  const [endIssue, setEndIssue] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<BacktestRun | null>(null);

  const listQuery = useQuery({
    queryKey: ["backtests", lottery],
    queryFn: async () => {
      const res = await apiRequest<BacktestList>(`/backtests?lottery_type=${lottery}&page=1&page_size=10`);
      return res.data!;
    },
  });

  const issuesQuery = useQuery({
    queryKey: ["backtest-issues", active?.id],
    enabled: Boolean(active?.id),
    queryFn: async () => {
      const res = await apiRequest<BacktestIssueList>(
        `/backtests/${active!.id}/issues?page=1&page_size=50`,
      );
      return res.data!;
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest<BacktestRun>("/backtests", {
        method: "POST",
        body: JSON.stringify({
          lottery_type: lottery,
          start_issue: startIssue,
          end_issue: endIssue,
          baseline_trials: 20,
          candidate_count: 1500,
        }),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(`回测完成：${data.start_issue} → ${data.end_issue}`);
      setActive(data);
      void queryClient.invalidateQueries({ queryKey: ["backtests"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "回测失败");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async (runId: string) => {
      const res = await apiRequest<BacktestRun>(`/backtests/${runId}/cancel`, { method: "POST" });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(`已取消回测 ${data.id.slice(0, 8)}`);
      setActive(data);
      void queryClient.invalidateQueries({ queryKey: ["backtests"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "取消失败");
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    createMutation.mutate();
  }

  const summary = (active?.summary ?? {}) as Record<string, unknown>;

  async function exportRun(fmt: "json" | "csv") {
    if (!active) return;
    try {
      const res = await fetch(`/api/v1/backtests/${active.id}/export?fmt=${fmt}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lottopilot-backtest-${active.lottery_type}-${active.start_issue}-${active.end_issue}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage(`已导出回测 ${fmt.toUpperCase()}`);
      setError(null);
    } catch {
      setError("导出失败");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="回测"
        description="Walk-forward 滚动回测，严格使用目标期之前的历史数据。结果仅供研究，不承诺收益。"
      />

      <Card>
      <CardContent className="space-y-4 px-6">
        <form className="grid gap-3 md:grid-cols-4" onSubmit={onSubmit}>
          <label className="space-y-1 text-sm">
            <span>彩种</span>
            <select
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={lottery}
              onChange={(e) => setLottery(e.target.value as LotteryType)}
            >
              <option value="ssq">SSQ</option>
              <option value="dlt">DLT</option>
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span>起始期号</span>
            <input
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={startIssue}
              onChange={(e) => setStartIssue(e.target.value)}
              required
            />
          </label>
          <label className="space-y-1 text-sm">
            <span>结束期号</span>
            <input
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={endIssue}
              onChange={(e) => setEndIssue(e.target.value)}
              required
            />
          </label>
          <div className="flex items-end">
            <Button type="submit" className="w-full" disabled={createMutation.isPending}>
              {createMutation.isPending ? "回测中..." : "开始回测"}
            </Button>
          </div>
        </form>
        {message ? <div className="mt-3 text-sm text-primary">{message}</div> : null}
        {error ? <div className="mt-3 text-sm text-destructive">{error}</div> : null}
      </CardContent>
    </Card>

      {active ? (
        <Card>
      <CardContent className="space-y-4 px-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-medium">最近结果</h2>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => void exportRun("json")}>
                导出 JSON
              </Button>
              <Button variant="secondary" onClick={() => void exportRun("csv")}>
                导出 CSV
              </Button>
              {active.status === "running" || active.status === "queued" ? (
                <Button
                  variant="secondary"
                  onClick={() => cancelMutation.mutate(active.id)}
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? "取消中..." : "取消回测"}
                </Button>
              ) : null}
            </div>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border p-3">
              <div className="text-xs text-muted-foreground">覆盖期数</div>
              <div className="mt-1 text-xl font-semibold">{String(summary.issues ?? "—")}</div>
            </div>
            <div className="rounded-xl border p-3">
              <div className="text-xs text-muted-foreground">平均最佳主区命中</div>
              <div className="mt-1 text-xl font-semibold">
                {String(summary.avg_best_primary_hits ?? "—")}
              </div>
            </div>
            <div className="rounded-xl border p-3">
              <div className="text-xs text-muted-foreground">随机基线主区命中</div>
              <div className="mt-1 text-xl font-semibold">
                {String(summary.avg_baseline_primary_hits ?? "—")}
              </div>
            </div>
            <div className="rounded-xl border p-3">
              <div className="text-xs text-muted-foreground">相对基线提升</div>
              <div className="mt-1 text-xl font-semibold">
                {String(summary.lift_primary_vs_baseline ?? "—")}
              </div>
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            {String(summary.disclaimer ?? "回测结果不代表未来表现。模型评分/历史分析，不承诺中奖。")}
          </p>

          <h3 className="mt-5 text-base font-medium">逐期结果</h3>
          {issuesQuery.isLoading ? (
            <div className="mt-2"><LoadingState label="加载逐期结果..." /></div>
          ) : issuesQuery.isError ? (
            <div className="mt-2">
              <ErrorState
                title="逐期结果加载失败"
                onRetry={() => void issuesQuery.refetch()}
              />
            </div>
          ) : (
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-muted-foreground">
                  <tr className="border-b border">
                    <th className="px-2 py-2">期号</th>
                    <th className="px-2 py-2">最佳主区</th>
                    <th className="px-2 py-2">最佳次区</th>
                    <th className="px-2 py-2">基线主区</th>
                  </tr>
                </thead>
                <tbody>
                  {(issuesQuery.data?.items ?? []).map((row) => (
                    <tr key={row.id} className="border-b border/70">
                      <td className="px-2 py-2">
                        {row.hit_metrics?.target_issue ?? row.target_draw_id?.slice(0, 8) ?? "—"}
                      </td>
                      <td className="px-2 py-2">{row.hit_metrics?.best_primary_hits ?? "—"}</td>
                      <td className="px-2 py-2">{row.hit_metrics?.best_secondary_hits ?? "—"}</td>
                      <td className="px-2 py-2">
                        {row.baseline_metrics?.avg_primary_hits ??
                          row.baseline_metrics?.baseline_avg_primary_hits ??
                          "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!issuesQuery.data?.items?.length ? (
                <div className="py-3 text-sm text-muted-foreground">暂无逐期明细。</div>
              ) : null}
            </div>
          )}
        </CardContent>
    </Card>
      ) : null}

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">历史回测</h2>
        <div className="mt-3 space-y-2 text-sm">
          {listQuery.isLoading ? <LoadingState label="加载回测记录..." /> : null}
          {listQuery.isError ? (
            <ErrorState
              title="回测列表加载失败"
              onRetry={() => void listQuery.refetch()}
            />
          ) : null}
          {!listQuery.isLoading && !listQuery.isError
            ? (listQuery.data?.items ?? []).map((run) => (
            <button
              key={run.id}
              className="flex w-full flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2 text-left hover:bg-secondary/50"
              onClick={() => setActive(run)}
            >
              <span>
                {run.lottery_type.toUpperCase()} · {run.start_issue}→{run.end_issue} · {run.status}
              </span>
              <span className="text-muted-foreground">{new Date(run.created_at).toLocaleString()}</span>
            </button>
          ))
            : null}
          {!listQuery.isLoading && !listQuery.isError && !listQuery.data?.items?.length ? (
            <EmptyState title="暂无回测记录" description="选择历史区间后开始 Walk-forward 回测。" />
          ) : null}
        </div>
      </CardContent>
    </Card>
    </div>
  );
}
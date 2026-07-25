import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { LotterySwitcher } from "@/components/ui/LotterySwitcher";
import { PageHeader } from "@/components/ui/PageHeader";
import { TicketCard } from "@/components/ui/TicketCard";
import { apiRequest, ApiError } from "@/lib/api";
import type { LotteryType } from "@/types/draws";
import type { RecommendationList, RecommendationRun } from "@/types/recommendations";

export function RecommendationsPage() {
  const queryClient = useQueryClient();
  const [lottery, setLottery] = useState<LotteryType>("ssq");
  const [enableAi, setEnableAi] = useState(true);
  const [seed, setSeed] = useState("");
  const [targetIssue, setTargetIssue] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<RecommendationRun | null>(null);

  const listQuery = useQuery({
    queryKey: ["recommendations", lottery],
    queryFn: async () => {
      const res = await apiRequest<RecommendationList>(
        `/recommendations?lottery_type=${lottery}&page=1&page_size=10`,
      );
      return res.data!;
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        lottery_type: lottery,
        candidate_count: 5000,
        enable_ai: enableAi,
      };
      if (seed.trim()) body.seed = Number(seed);
      if (targetIssue.trim()) body.target_issue = targetIssue.trim();
      const res = await apiRequest<RecommendationRun>("/recommendations", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(
        `已生成 ${data.lottery_type.toUpperCase()} 推荐，目标期 ${data.target_issue ?? "-"}，seed ${data.seed ?? "-"}，AI ${data.ai_status}`,
      );
      setActive(data);
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "生成推荐失败");
    },
  });

  const evaluateMutation = useMutation({
    mutationFn: async (runId: string) => {
      const res = await apiRequest<{ summary: Record<string, unknown>; run: RecommendationRun }>(
        `/recommendations/${runId}/evaluate`,
        { method: "POST" },
      );
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      const bestP = data.summary.best_primary_hits ?? "-";
      const bestS = data.summary.best_secondary_hits ?? "-";
      setMessage(`复盘完成：最佳命中 主区 ${bestP} / 次区 ${bestS}`);
      setActive(data.run);
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "复盘失败");
    },
  });

  const explainMutation = useMutation({
    mutationFn: async (runId: string) => {
      const res = await apiRequest<RecommendationRun>(`/recommendations/${runId}/explanations`, {
        method: "POST",
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(`已重新生成 ${data.tickets?.length ?? 0} 条统计解释`);
      setActive(data);
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "解释生成失败");
    },
  });

  const current = active ?? listQuery.data?.items?.[0] ?? null;

  async function exportRun(fmt: "json" | "csv") {
    if (!current) return;
    try {
      const res = await fetch(`/api/v1/recommendations/${current.id}/export?fmt=${fmt}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lottopilot-${current.lottery_type}-${current.target_issue ?? current.id}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage(`已导出 ${fmt.toUpperCase()}`);
      setError(null);
    } catch {
      setError("导出失败");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="推荐记录"
        description="可指定 seed / 目标期复现推荐。分数为模型评分，不承诺中奖。"
        actions={<LotterySwitcher value={lottery} onChange={setLottery} />}
      />

      <Card>
        <div className="grid gap-3 md:grid-cols-4">
          <label className="space-y-1 text-sm">
            <span>目标期（可选）</span>
            <input
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2"
              value={targetIssue}
              onChange={(e) => setTargetIssue(e.target.value)}
              placeholder="默认自动推断下一期"
            />
          </label>
          <label className="space-y-1 text-sm">
            <span>Seed（可选）</span>
            <input
              type="number"
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="固定 seed 可复现"
            />
          </label>
          <label className="inline-flex items-end gap-2 text-sm text-slate-300 pb-2">
            <input
              type="checkbox"
              checked={enableAi}
              onChange={(e) => setEnableAi(e.target.checked)}
            />
            启用 AI
          </label>
          <div className="flex items-end">
            <Button
              className="w-full"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? "生成中..." : "生成 5 组推荐"}
            </Button>
          </div>
        </div>
        {message ? <div className="mt-3 text-sm text-emerald-400">{message}</div> : null}
        {error ? <div className="mt-3 text-sm text-rose-400">{error}</div> : null}
      </Card>

      {listQuery.isLoading ? <LoadingState label="加载推荐记录..." /> : null}
      {listQuery.isError ? (
        <ErrorState
          title="推荐列表加载失败"
          description="请检查登录状态或稍后重试。"
          onRetry={() => void listQuery.refetch()}
        />
      ) : null}

      {current ? (
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-medium">
                {current.lottery_type.toUpperCase()} · 目标期 {current.target_issue ?? "—"}
              </h2>
              <div className="mt-1 text-sm text-slate-400">
                seed {current.seed ?? "—"} · snapshot {current.data_snapshot_hash?.slice(0, 10) ?? "—"} · AI{" "}
                {current.ai_status}
                {current.evaluation
                  ? ` · 复盘命中 ${current.evaluation.best_primary_hits ?? "-"}+${current.evaluation.best_secondary_hits ?? "-"}`
                  : ""}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => evaluateMutation.mutate(current.id)}
                disabled={evaluateMutation.isPending}
              >
                {evaluateMutation.isPending ? "复盘中..." : "手动复盘"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => explainMutation.mutate(current.id)}
                disabled={explainMutation.isPending}
              >
                {explainMutation.isPending ? "解释生成中..." : "重生成解释"}
              </Button>
              <Button variant="secondary" onClick={() => void exportRun("json")}>
                导出 JSON
              </Button>
              <Button variant="secondary" onClick={() => void exportRun("csv")}>
                导出 CSV
              </Button>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {(current.tickets ?? []).map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
            <p className="text-xs text-slate-500">模型评分/历史分析，不承诺中奖。</p>
          </div>
        </Card>
      ) : !listQuery.isLoading && !listQuery.isError ? (
        <EmptyState title="还没有推荐记录" description="请先同步开奖数据，再生成推荐。" />
      ) : null}

      <Card>
        <h2 className="text-lg font-medium">历史推荐</h2>
        <div className="mt-3 space-y-2 text-sm">
          {(listQuery.data?.items ?? []).map((run) => (
            <button
              key={run.id}
              className="flex w-full flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 px-3 py-2 text-left hover:bg-slate-800/50"
              onClick={() => setActive(run)}
            >
              <span>
                {run.lottery_type.toUpperCase()} · {run.target_issue ?? "—"} · seed {run.seed ?? "—"} · AI{" "}
                {run.ai_status}
              </span>
              <span className="text-slate-500">{new Date(run.created_at).toLocaleString()}</span>
            </button>
          ))}
          {!listQuery.data?.items?.length ? (
            <div className="text-slate-500">暂无历史。</div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
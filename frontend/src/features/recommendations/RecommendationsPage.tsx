import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { LotterySwitcher } from "@/components/ui/lottery-switcher";
import { PageHeader } from "@/components/ui/page-header";
import { RunPanel } from "@/components/recommendations/run-panel";
import { apiRequest, ApiError } from "@/lib/api";
import { aiStatusLabel, lotteryLabel } from "@/lib/labels";
import { buildRunTitleMetaMap } from "@/lib/run-title";
import type { LotteryType } from "@/types/draws";
import type { RecommendationList, RecommendationRun } from "@/types/recommendations";

export function RecommendationsPage() {
  const queryClient = useQueryClient();
  const [lottery, setLottery] = useState<LotteryType>("ssq");
  const [enableAi, setEnableAi] = useState(true);
  const [seed, setSeed] = useState("");
  const [targetIssue, setTargetIssue] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [freshRun, setFreshRun] = useState<RecommendationRun | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["recommendations", lottery],
    queryFn: async () => {
      const res = await apiRequest<RecommendationList>(
        `/recommendations?lottery_type=${lottery}&page=1&page_size=20`,
      );
      return res.data!;
    },
  });

  const runs = useMemo(() => {
    const items = listQuery.data?.items ?? [];
    if (freshRun && !items.some((r) => r.id === freshRun.id)) {
      return [freshRun, ...items];
    }
    return items.map((r) => (freshRun && r.id === freshRun.id ? freshRun : r));
  }, [listQuery.data?.items, freshRun]);

  const titleMetaMap = useMemo(() => buildRunTitleMetaMap(runs), [runs]);

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
        `已生成${lotteryLabel(data.lottery_type)}推荐，目标期 ${data.target_issue ?? "-"}，${aiStatusLabel(data.ai_status)}`,
      );
      setFreshRun(data);
      setActiveId(data.id);
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "生成推荐失败");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (runId: string) => {
      setDeletingId(runId);
      await apiRequest(`/recommendations/${runId}`, { method: "DELETE" });
      return runId;
    },
    onSuccess: (runId) => {
      setDeletingId(null);
      setError(null);
      setMessage("已删除该期推荐");
      if (freshRun?.id === runId) setFreshRun(null);
      if (activeId === runId) setActiveId(null);
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
    onError: (err: unknown) => {
      setDeletingId(null);
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "删除失败");
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
      setFreshRun(data.run);
      setActiveId(data.run.id);
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
      setFreshRun(data);
      setActiveId(data.id);
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "解释生成失败");
    },
  });

  async function exportRun(run: RecommendationRun, fmt: "json" | "csv") {
    try {
      const res = await fetch(`/api/v1/recommendations/${run.id}/export?fmt=${fmt}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lottopilot-${run.lottery_type}-${run.target_issue ?? run.id}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage(`已导出 ${fmt === "json" ? "JSON 文件" : "CSV 表格"}`);
      setError(null);
    } catch {
      setError("导出失败");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="推荐记录"
        description="每期推荐可折叠展开；支持复制号码，也可删除不需要的期次。"
        actions={<LotterySwitcher value={lottery} onChange={setLottery} />}
      />

      <Card>
        <CardContent className="space-y-4 px-6 pt-6">
          <div className="grid gap-3 md:grid-cols-4">
            <label className="space-y-1 text-sm">
              <span>指定目标期（可选）</span>
              <input
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
                value={targetIssue}
                onChange={(e) => setTargetIssue(e.target.value)}
                placeholder="留空=自动下一期"
              />
            </label>
            <label className="inline-flex items-end gap-2 text-sm text-foreground pb-2">
              <input type="checkbox" checked={enableAi} onChange={(e) => setEnableAi(e.target.checked)} />
              启用 AI 解释
            </label>
            <div className="flex items-end">
              <Button className="w-full" variant="outline" onClick={() => setShowAdvanced((v) => !v)}>
                {showAdvanced ? "收起高级选项" : "高级选项"}
              </Button>
            </div>
            <div className="flex items-end">
              <Button className="w-full" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                {createMutation.isPending ? "生成中..." : "生成 5 组推荐"}
              </Button>
            </div>
          </div>

          {showAdvanced ? (
            <div className="rounded-xl border bg-muted/30 p-4 space-y-2">
              <label className="space-y-1 text-sm block max-w-md">
                <span>复现编号 seed（可选，一般不用填）</span>
                <input
                  type="number"
                  className="w-full rounded-xl border border-input bg-background px-3 py-2"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  placeholder="留空即可"
                />
              </label>
              <p className="text-xs text-muted-foreground leading-5">
                用于让同一次生成结果可重复出现，方便调试对比。不影响真实中奖概率。日常使用请留空，由系统自动处理。
              </p>
            </div>
          ) : null}

          {message ? <div className="text-sm text-primary">{message}</div> : null}
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
        </CardContent>
      </Card>

      {listQuery.isLoading ? <LoadingState label="加载推荐记录..." /> : null}
      {listQuery.isError ? (
        <ErrorState title="推荐列表加载失败" description="请检查登录状态或稍后重试。" onRetry={() => void listQuery.refetch()} />
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && runs.length ? (
        <div className="space-y-3">
          {runs.map((run, idx) => (
            <RunPanel
              key={run.id}
              run={run}
              defaultOpen={activeId ? run.id === activeId : idx === 0}
              titleMeta={titleMetaMap[run.id]}
              onDelete={(id) => deleteMutation.mutate(id)}
              deleting={deletingId === run.id}
              actions={
                <>
                  <Button variant="secondary" size="sm" onClick={() => { setActiveId(run.id); evaluateMutation.mutate(run.id); }} disabled={evaluateMutation.isPending}>
                    {evaluateMutation.isPending ? "复盘中..." : "手动复盘"}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => { setActiveId(run.id); explainMutation.mutate(run.id); }} disabled={explainMutation.isPending}>
                    {explainMutation.isPending ? "解释中..." : "重生成解释"}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => void exportRun(run, "json")}>导出 JSON</Button>
                  <Button variant="secondary" size="sm" onClick={() => void exportRun(run, "csv")}>导出表格</Button>
                </>
              }
            />
          ))}
        </div>
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && !runs.length ? (
        <EmptyState title="还没有推荐记录" description="请先同步开奖数据，再生成推荐。" />
      ) : null}
    </div>
  );
}

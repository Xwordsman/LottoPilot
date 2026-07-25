import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
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
import { apiRequest, ApiError } from "@/lib/api";
import type { LotteryType } from "@/types/draws";

type StrategyProfile = {
  id: string;
  name: string;
  version: string;
  lottery_type: string;
  config: Record<string, unknown>;
  is_default: boolean;
  is_active: boolean;
  created_at: string | null;
  frozen?: boolean;
  backtest_summary?: Record<string, unknown>;
};

export function StrategiesPage() {
  const queryClient = useQueryClient();
  const [lottery, setLottery] = useState<LotteryType>("ssq");
  const [name, setName] = useState("custom");
  const [version, setVersion] = useState("v-exp");
  const [candidateCount, setCandidateCount] = useState(5000);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summaryJson, setSummaryJson] = useState('{"note":"manual acceptance summary"}');

  const listQuery = useQuery({
    queryKey: ["strategies", lottery],
    queryFn: async () => {
      const res = await apiRequest<{ items: StrategyProfile[] }>(
        `/strategies?lottery_type=${lottery}&include_inactive=true`,
      );
      return res.data!.items;
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest<StrategyProfile>("/strategies", {
        method: "POST",
        body: JSON.stringify({
          lottery_type: lottery,
          name,
          version,
          config: { candidate_count: Number(candidateCount) },
        }),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(`已创建策略 ${data.name}@${data.version}`);
      void queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "创建策略失败");
    },
  });

  const activateMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiRequest<StrategyProfile>(`/strategies/${id}/activate`, { method: "POST" });
      return res.data!;
    },
    onSuccess: () => {
      setError(null);
      setMessage("策略已启用");
      void queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "启用失败");
    },
  });

  const defaultMutation = useMutation({
    mutationFn: async (id: string) => {
      let summary: Record<string, unknown> = {};
      try {
        summary = JSON.parse(summaryJson || "{}") as Record<string, unknown>;
      } catch {
        throw new ApiError("回测摘要 JSON 无效", { code: "INVALID_JSON", status: 400 });
      }
      const res = await apiRequest<StrategyProfile>(`/strategies/${id}/set-default`, {
        method: "POST",
        body: JSON.stringify({ backtest_summary: summary }),
      });
      return res.data!;
    },
    onSuccess: () => {
      setError(null);
      setMessage("已设为默认策略");
      void queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "设为默认失败");
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="策略配置"
        description="实验版本可复制创建与启用。已被推荐/回测引用的版本冻结不可改。设为默认需提供回测摘要。"
        actions={<LotterySwitcher value={lottery} onChange={setLottery} />}
      />

      {message ? <div className="text-sm text-primary">{message}</div> : null}
      {error ? <div className="text-sm text-destructive">{error}</div> : null}

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">新建实验版本</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="space-y-1 text-sm">
            <span>名称</span>
            <input
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span>版本</span>
            <input
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span>候选池大小</span>
            <input
              type="number"
              min={500}
              max={50000}
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={candidateCount}
              onChange={(e) => setCandidateCount(Number(e.target.value))}
            />
          </label>
        </div>
        <div className="mt-4">
          <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            {createMutation.isPending ? "创建中..." : "创建策略版本"}
          </Button>
        </div>
      </CardContent>
    </Card>

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">设为默认时的回测摘要 JSON</h2>
        <textarea
          className="mt-3 min-h-24 w-full rounded-xl border border-input bg-background px-3 py-2 font-mono text-xs"
          value={summaryJson}
          onChange={(e) => setSummaryJson(e.target.value)}
        />
      </CardContent>
    </Card>

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">{lottery.toUpperCase()} 策略列表</h2>
        <div className="mt-3 space-y-2 text-sm">
          {listQuery.isLoading ? <LoadingState label="加载策略列表..." /> : null}
          {listQuery.isError ? (
            <ErrorState title="策略列表加载失败" onRetry={() => void listQuery.refetch()} />
          ) : null}
          {!listQuery.isLoading && !listQuery.isError
            ? (listQuery.data ?? []).map((item) => (
            <div
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2"
            >
              <div>
                <div className="font-medium">
                  {item.name}@{item.version}
                  {item.is_default ? " · 默认" : ""}
                  {!item.is_active ? " · 停用" : ""}
                </div>
                <div className="text-xs text-muted-foreground">
                  id {item.id.slice(0, 8)} · candidate_count{" "}
                  {String((item.config as { candidate_count?: number })?.candidate_count ?? "—")}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {!item.is_active ? (
                  <Button
                    variant="secondary"
                    onClick={() => activateMutation.mutate(item.id)}
                    disabled={activateMutation.isPending}
                  >
                    启用
                  </Button>
                ) : null}
                {!item.is_default ? (
                  <Button
                    variant="secondary"
                    onClick={() => defaultMutation.mutate(item.id)}
                    disabled={defaultMutation.isPending || !item.is_active}
                  >
                    设为默认
                  </Button>
                ) : null}
              </div>
            </div>
          ))
            : null}
          {!listQuery.isLoading && !listQuery.isError && !listQuery.data?.length ? (
            <EmptyState title="暂无策略" description="系统会在首次查询时自动创建默认策略。" />
          ) : null}
        </div>
      </CardContent>
    </Card>
    </div>
  );
}
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { LotterySwitcher } from "@/components/ui/LotterySwitcher";
import { PageHeader } from "@/components/ui/PageHeader";
import { TicketCard } from "@/components/ui/TicketCard";
import { apiRequest, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { SystemInfo } from "@/types/api";
import type { LotteryType } from "@/types/draws";
import type { RecommendationList, RecommendationRun } from "@/types/recommendations";

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [lottery, setLottery] = useState<LotteryType>("ssq");
  const [enableAi, setEnableAi] = useState(true);
  const [seed, setSeed] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generated, setGenerated] = useState<RecommendationRun | null>(null);

  const infoQuery = useQuery({
    queryKey: ["system-info"],
    queryFn: async () => {
      const res = await apiRequest<SystemInfo>("/system/info");
      return res.data!;
    },
  });

  const recQuery = useQuery({
    queryKey: ["recommendations", "dashboard", lottery],
    queryFn: async () => {
      const res = await apiRequest<RecommendationList>(
        `/recommendations?lottery_type=${lottery}&page=1&page_size=1`,
      );
      return res.data!;
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest<RecommendationRun>("/recommendations", {
        method: "POST",
        body: JSON.stringify({
          lottery_type: lottery,
          candidate_count: 5000,
          enable_ai: enableAi,
          ...(seed.trim() ? { seed: Number(seed) } : {}),
        }),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(
        `已生成 ${data.lottery_type.toUpperCase()} 5 组候选，目标期 ${data.target_issue ?? "-"}，AI ${data.ai_status}`,
      );
      setGenerated(data);
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
      void queryClient.invalidateQueries({ queryKey: ["system-info"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "生成推荐失败");
    },
  });

  const current = generated ?? recQuery.data?.items?.[0] ?? null;
  const latestIssue =
    lottery === "ssq"
      ? infoQuery.data?.latest_draws?.ssq
      : infoQuery.data?.latest_draws?.dlt;

  return (
    <div className="space-y-6">
      <PageHeader
        title="本期推荐"
        description={`欢迎${user ? `，${user.display_name}` : ""}。先看本期 5 组候选，分数为模型评分，不承诺中奖。`}
        actions={<LotterySwitcher value={lottery} onChange={setLottery} />}
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <div className="text-sm text-slate-400">最新开奖期</div>
          <div className="mt-2 text-xl font-semibold">{latestIssue ?? "暂无数据"}</div>
        </Card>
        <Card>
          <div className="text-sm text-slate-400">目标期（下一期）</div>
          <div className="mt-2 text-xl font-semibold">{current?.target_issue ?? "生成后可见"}</div>
        </Card>
        <Card>
          <div className="text-sm text-slate-400">数据版本</div>
          <div className="mt-2 text-xl font-semibold">{infoQuery.data?.version ?? "—"}</div>
          <div className="mt-1 text-xs text-slate-500">
            commit {infoQuery.data?.git_commit ?? "dev"}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-slate-400">AI 状态</div>
          <div className="mt-2 text-xl font-semibold">{current?.ai_status ?? "未生成"}</div>
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-medium">生成 5 组候选</h2>
            <p className="mt-1 text-sm text-slate-400">
              无 AI Key 时仍可纯统计生成。AI 仅做 ≤10% 有限重排/解释，失败自动降级。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="inline-flex items-center gap-2 text-sm text-slate-300">
              Seed
              <input
                type="number"
                className="w-28 rounded-xl border border-slate-700 bg-slate-950 px-2 py-1"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                placeholder="可选"
              />
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={enableAi}
                onChange={(e) => setEnableAi(e.target.checked)}
              />
              启用 AI
            </label>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? "生成中..." : "生成本期 5 组"}
            </Button>
            <Link to="/recommendations">
              <Button variant="secondary">推荐记录</Button>
            </Link>
          </div>
        </div>
        {message ? <div className="mt-3 text-sm text-emerald-400">{message}</div> : null}
        {error ? <div className="mt-3 text-sm text-rose-400">{error}</div> : null}
      </Card>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-medium">
            {current
              ? `${current.lottery_type.toUpperCase()} · 目标期 ${current.target_issue ?? "—"}`
              : "候选组合"}
          </h2>
          {current ? (
            <div className="text-xs text-slate-500">
              seed {current.seed ?? "—"} · AI {current.ai_status}
            </div>
          ) : null}
        </div>
        {recQuery.isLoading ? <div className="mt-4"><LoadingState label="加载最近推荐..." /></div> : null}
        {recQuery.isError ? (
          <div className="mt-4">
            <ErrorState
              title="推荐加载失败"
              description="请检查登录态或后端服务后重试。"
              onRetry={() => void recQuery.refetch()}
            />
          </div>
        ) : null}
        {!recQuery.isLoading && !recQuery.isError && current ? (
          <div className="mt-4 space-y-3">
            {(current.tickets ?? []).slice(0, 5).map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
            <p className="text-xs text-slate-500">模型评分/历史分析，不承诺中奖。</p>
          </div>
        ) : null}
        {!recQuery.isLoading && !recQuery.isError && !current ? (
          <div className="mt-4">
            <EmptyState
              title="还没有本期推荐"
              description="请先同步或导入开奖数据，然后点击“生成本期 5 组”。"
            />
          </div>
        ) : null}
      </Card>

      <Card>
        <h2 className="text-lg font-medium">快捷入口</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to="/draws">
            <Button variant="secondary">开奖数据</Button>
          </Link>
          <Link to="/analytics">
            <Button variant="secondary">统计分析</Button>
          </Link>
          <Link to="/backtests">
            <Button variant="secondary">历史回测</Button>
          </Link>
          <Link to="/strategies">
            <Button variant="secondary">策略配置</Button>
          </Link>
          <Link to="/settings">
            <Button variant="secondary">系统/AI 设置</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
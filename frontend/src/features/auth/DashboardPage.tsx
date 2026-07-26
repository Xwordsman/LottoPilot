import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingState } from "@/components/ui/loading-state"
import { LotterySwitcher } from "@/components/ui/lottery-switcher"
import { PageHeader } from "@/components/ui/page-header"
import { RunPanel } from "@/components/recommendations/run-panel"
import { apiRequest, ApiError } from "@/lib/api"
import { useAuthStore } from "@/lib/auth-store"
import { aiStatusLabel, lotteryLabel } from "@/lib/labels"
import { buildRunTitleMetaMap } from "@/lib/run-title"
import type { SystemInfo } from "@/types/api"
import type { LotteryType } from "@/types/draws"
import type { RecommendationList, RecommendationRun } from "@/types/recommendations"

export function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const queryClient = useQueryClient()
  const [lottery, setLottery] = useState<LotteryType>("ssq")
  const [enableAi, setEnableAi] = useState(true)
  const [seed, setSeed] = useState("")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [generated, setGenerated] = useState<RecommendationRun | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const infoQuery = useQuery({
    queryKey: ["system-info"],
    queryFn: async () => {
      const res = await apiRequest<SystemInfo>("/system/info")
      return res.data!
    },
  })

  const recQuery = useQuery({
    queryKey: ["recommendations", "dashboard", lottery],
    queryFn: async () => {
      const res = await apiRequest<RecommendationList>(
        `/recommendations?lottery_type=${lottery}&page=1&page_size=8`,
      )
      return res.data!
    },
  })

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
      })
      return res.data!
    },
    onSuccess: (data) => {
      setError(null)
      const variant = (data.metrics as Record<string, any>)?.auto_hit?.selected_variant
      setMessage(
        `已生成${lotteryLabel(data.lottery_type)} 5 组候选，目标期 ${data.target_issue ?? "-"}，${aiStatusLabel(data.ai_status)}` +
          (variant ? `，自动优选 ${variant}` : ""),
      )
      setGenerated(data)
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] })
      void queryClient.invalidateQueries({ queryKey: ["system-info"] })
    },
    onError: (err: unknown) => {
      setMessage(null)
      setError(err instanceof ApiError ? err.message : "生成推荐失败")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (runId: string) => {
      setDeletingId(runId)
      await apiRequest(`/recommendations/${runId}`, { method: "DELETE" })
      return runId
    },
    onSuccess: (runId) => {
      setDeletingId(null)
      setError(null)
      setMessage("已删除该期推荐")
      if (generated?.id === runId) setGenerated(null)
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] })
    },
    onError: (err: unknown) => {
      setDeletingId(null)
      setMessage(null)
      setError(err instanceof ApiError ? err.message : "删除失败")
    },
  })

  const titleSourceRuns = useMemo(() => {
    const items = recQuery.data?.items ?? []
    if (generated && !items.some((r) => r.id === generated.id)) {
      return [generated, ...items]
    }
    return items
  }, [generated, recQuery.data?.items])
  const titleMetaMap = useMemo(() => buildRunTitleMetaMap(titleSourceRuns), [titleSourceRuns])

  const current = generated ?? recQuery.data?.items?.[0] ?? null
  const latestIssue =
    lottery === "ssq"
      ? infoQuery.data?.latest_draws?.ssq
      : infoQuery.data?.latest_draws?.dlt

  return (
    <div className="space-y-6">
      <PageHeader
        title="本期推荐"
        description={`欢迎${user ? `，${user.display_name}` : ""}。先看本期 5 组候选，分数为模型评分，不承诺中奖。`}
        actions={<LotterySwitcher value={lottery} onChange={setLottery} />}
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>最新开奖期</CardDescription>
            <CardTitle className="text-xl">{latestIssue ?? "暂无数据"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>目标期（下一期）</CardDescription>
            <CardTitle className="text-xl">
              {current?.target_issue ?? "生成后可见"}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>程序版本</CardDescription>
            <CardTitle className="text-xl">{infoQuery.data?.version ?? "—"}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            构建号 {infoQuery.data?.git_commit ?? "开发版"}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>AI 状态</CardDescription>
            <CardTitle className="text-lg leading-snug">
              {current ? aiStatusLabel(current.ai_status) : "尚未生成"}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>生成 5 组候选</CardTitle>
          <CardDescription>
            点击后系统自动按近期历史命中表现优选策略并生成 5 组。AI 仅做不超过 10% 的辅助，失败会自动降级为纯统计；不承诺中奖。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex items-center gap-2 pb-2">
              <Checkbox
                id="enable-ai"
                checked={enableAi}
                onCheckedChange={(v) => setEnableAi(Boolean(v))}
              />
              <Label htmlFor="enable-ai">启用 AI 解释</Label>
            </div>
            <Button
              disabled={createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "生成中..." : "生成本期 5 组"}
            </Button>
            <Button asChild variant="outline">
              <Link to="/recommendations">推荐记录</Link>
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowAdvanced((v) => !v)}
            >
              {showAdvanced ? "收起高级选项" : "高级选项"}
            </Button>
          </div>

          {showAdvanced ? (
            <div className="rounded-xl border bg-muted/30 p-4 space-y-2 max-w-xl">
              <Label htmlFor="seed">复现编号（可选，一般不用填）</Label>
              <Input
                id="seed"
                className="w-56"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                placeholder="留空即可"
              />
              <p className="text-xs text-muted-foreground leading-5">
                这不是中奖相关设置。系统用它控制“随机过程”的起点：留空时自动生成；
                填写同一个数字，可以反复得到完全相同的 5 组号码，方便对比测试。日常使用请留空。
              </p>
            </div>
          ) : null}

          {message ? (
            <Alert>
              <AlertTitle>操作成功</AlertTitle>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          ) : null}
          {error ? (
            <Alert variant="destructive">
              <AlertTitle>操作失败</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>候选组合</CardTitle>
          <CardDescription>
            每一期可折叠展开；支持单注复制、一键复制该期全部号码，也可删除不需要的期次。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {recQuery.isLoading ? <LoadingState label="加载最近推荐..." /> : null}
          {recQuery.isError ? (
            <ErrorState
              title="推荐加载失败"
              description="请检查登录态或后端服务后重试。"
              onRetry={() => void recQuery.refetch()}
            />
          ) : null}
          {!recQuery.isLoading &&
          !recQuery.isError &&
          (generated || (recQuery.data?.items?.length ?? 0) > 0) ? (
            <div className="space-y-3">
              {generated ? (
                <RunPanel
                  key={generated.id}
                  run={generated}
                  defaultOpen
                  titleMeta={titleMetaMap[generated.id]}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  deleting={deletingId === generated.id}
                />
              ) : null}
              {(recQuery.data?.items ?? [])
                .filter((run) => !generated || run.id !== generated.id)
                .map((run, idx) => (
                  <RunPanel
                    key={run.id}
                    run={run}
                    defaultOpen={!generated && idx === 0}
                    titleMeta={titleMetaMap[run.id]}
                    onDelete={(id) => deleteMutation.mutate(id)}
                    deleting={deletingId === run.id}
                  />
                ))}
            </div>
          ) : null}
          {!recQuery.isLoading && !recQuery.isError && !current ? (
            <EmptyState
              title="还没有本期推荐"
              description="请先同步或导入开奖数据，然后点击“生成本期 5 组”。"
              action={
                <Button asChild variant="outline">
                  <Link to="/draws">去开奖数据</Link>
                </Button>
              }
            />
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>快捷入口</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button asChild variant="secondary">
            <Link to="/draws">开奖数据</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/analytics">统计分析</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/backtests">历史回测</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/strategies">策略配置</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/settings">系统设置</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

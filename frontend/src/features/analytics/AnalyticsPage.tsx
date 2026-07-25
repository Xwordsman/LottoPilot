import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { apiRequest } from "@/lib/api";
import type { AnalyticsOverview } from "@/types/analytics";
import type { LotteryType } from "@/types/draws";

function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border bg-background/50 px-3 py-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

function NumberBar({
  number,
  value,
  max,
  suffix,
}: {
  number: number;
  value: number;
  max: number;
  suffix?: string;
}) {
  const width = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;
  return (
    <div className="grid grid-cols-[2.5rem_1fr_3rem] items-center gap-2 text-sm">
      <div className="font-medium text-foreground">{String(number).padStart(2, "0")}</div>
      <div className="h-2 rounded-full bg-secondary">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${width}%` }} />
      </div>
      <div className="text-right text-muted-foreground">
        {value}
        {suffix ?? ""}
      </div>
    </div>
  );
}

export function AnalyticsPage() {
  const [lottery, setLottery] = useState<LotteryType>("ssq");
  const [windowSize, setWindowSize] = useState(50);

  const query = useQuery({
    queryKey: ["analytics-overview", lottery, windowSize],
    queryFn: async () => {
      const params = new URLSearchParams({
        lottery_type: lottery,
        window: String(windowSize),
      });
      const res = await apiRequest<AnalyticsOverview>(`/analytics/overview?${params.toString()}`);
      return res.data!;
    },
  });

  const data = query.data;
  const freqMax = useMemo(
    () => Math.max(1, ...(data?.frequency_primary.map((x) => x.count) ?? [1])),
    [data],
  );
  const missMax = useMemo(
    () => Math.max(1, ...(data?.missing_primary.map((x) => x.missing) ?? [1])),
    [data],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">统计分析</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            频率、遗漏、和值跨度、分区与共现。结果仅基于历史开奖，不承诺中奖。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["ssq", "dlt"] as const).map((key) => (
            <Button
              key={key}
              variant={lottery === key ? "default" : "secondary"}
              onClick={() => setLottery(key)}
            >
              {key.toUpperCase()}
            </Button>
          ))}
          {[30, 50, 100].map((w) => (
            <Button
              key={w}
              variant={windowSize === w ? "default" : "ghost"}
              onClick={() => setWindowSize(w)}
            >
              近 {w} 期
            </Button>
          ))}
        </div>
      </div>

      {query.isLoading ? <LoadingState label="加载统计中..." /> : null}
      {query.isError ? (
        <ErrorState title="统计加载失败" description="请确认已有足够历史开奖数据。" onRetry={() => void query.refetch()} />
      ) : null}

      <div className="grid gap-3 md:grid-cols-5">
        <StatPill label="样本期数" value={data?.metrics.total_draws ?? 0} />
        <StatPill label="最新期号" value={data?.metrics.latest_issue ?? "—"} />
        <StatPill label="最新日期" value={data?.metrics.latest_draw_date ?? "—"} />
        <StatPill label="平均和值" value={data?.metrics.avg_sum ?? "—"} />
        <StatPill label="平均跨度" value={data?.metrics.avg_span ?? "—"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
      <CardContent className="space-y-4 px-6">
          <h2 className="text-lg font-medium">热号 TOP</h2>
          <div className="mt-3 space-y-2">
            {(data?.hot_cold.hot ?? []).map((item) => (
              <NumberBar key={`h-${item.number}`} number={item.number} value={item.count} max={freqMax} />
            ))}
            {!data?.hot_cold.hot?.length ? <div className="text-sm text-muted-foreground">暂无数据</div> : null}
          </div>
        </CardContent>
    </Card>
        <Card>
      <CardContent className="space-y-4 px-6">
          <h2 className="text-lg font-medium">冷号 TOP</h2>
          <div className="mt-3 space-y-2">
            {(data?.hot_cold.cold ?? []).map((item) => (
              <NumberBar key={`c-${item.number}`} number={item.number} value={item.count} max={freqMax} />
            ))}
            {!data?.hot_cold.cold?.length ? <div className="text-sm text-muted-foreground">暂无数据</div> : null}
          </div>
        </CardContent>
    </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
      <CardContent className="space-y-4 px-6">
          <h2 className="text-lg font-medium">主区频率</h2>
          <div className="mt-3 max-h-96 space-y-2 overflow-auto pr-1">
            {(data?.frequency_primary ?? []).map((item) => (
              <NumberBar key={`f-${item.number}`} number={item.number} value={item.count} max={freqMax} />
            ))}
          </div>
        </CardContent>
    </Card>
        <Card>
      <CardContent className="space-y-4 px-6">
          <h2 className="text-lg font-medium">主区当前遗漏</h2>
          <div className="mt-3 max-h-96 space-y-2 overflow-auto pr-1">
            {(data?.missing_primary ?? []).map((item) => (
              <NumberBar
                key={`m-${item.number}`}
                number={item.number}
                value={item.missing}
                max={missMax}
              />
            ))}
          </div>
        </CardContent>
    </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
      <CardContent className="space-y-4 px-6">
          <h2 className="text-lg font-medium">近期和值 / 跨度 / 奇偶</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted-foreground">
                <tr className="border-b border">
                  <th className="px-2 py-2">期号</th>
                  <th className="px-2 py-2">和值</th>
                  <th className="px-2 py-2">跨度</th>
                  <th className="px-2 py-2">奇偶</th>
                </tr>
              </thead>
              <tbody>
                {(data?.sum_span ?? []).slice(0, 15).map((row) => (
                  <tr key={row.issue} className="border-b border/70">
                    <td className="px-2 py-2">{row.issue}</td>
                    <td className="px-2 py-2">{row.sum}</td>
                    <td className="px-2 py-2">{row.span}</td>
                    <td className="px-2 py-2">{row.odd_even}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
    </Card>
        
      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">分区分布（近窗）</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-muted-foreground">
              <tr className="border-b border">
                <th className="px-2 py-2">期号</th>
                <th className="px-2 py-2">分区计数</th>
              </tr>
            </thead>
            <tbody>
              {(data?.zones ?? []).slice(0, 15).map((row) => (
                <tr key={`z-${row.issue}`} className="border-b border/70">
                  <td className="px-2 py-2">{row.issue}</td>
                  <td className="px-2 py-2">
                    {row.zone_low}/{row.zone_mid}/{row.zone_high}
                    {row.pattern ? ` · ${row.pattern}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data?.zones?.length ? <div className="mt-2 text-sm text-muted-foreground">暂无分区数据</div> : null}
        </div>
      </CardContent>
    </Card>

        <Card>
      <CardContent className="space-y-4 px-6">
          <h2 className="text-lg font-medium">共现 Top 对</h2>
          <div className="mt-3 space-y-2 text-sm">
            {(data?.cooccurrence ?? []).slice(0, 12).map((pair) => (
              <div
                key={`${pair.a}-${pair.b}`}
                className="flex items-center justify-between rounded-xl border px-3 py-2"
              >
                <span>
                  {String(pair.a).padStart(2, "0")} + {String(pair.b).padStart(2, "0")}
                </span>
                <span className="text-muted-foreground">{pair.count} 次</span>
              </div>
            ))}
            {!data?.cooccurrence?.length ? <div className="text-muted-foreground">暂无数据</div> : null}
          </div>
        </CardContent>
    </Card>
      </div>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state";
import { JobProgress } from "@/components/ui/job-progress";
import { NumberBall } from "@/components/ui/number-ball";
import { PageHeader } from "@/components/ui/page-header";
import { apiRequest, ApiError } from "@/lib/api";
import type {
  DrawListData,
  ImportCommitData,
  ImportPreviewData,
  IngestionRunListData,
  LatestDrawsData,
  LotteryType,
  SyncAcceptedData,
} from "@/types/draws";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export function DrawsPage() {
  const queryClient = useQueryClient();
  const [lottery, setLottery] = useState<"all" | LotteryType>("all");
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportPreviewData | null>(null);

  const latestQuery = useQuery({
    queryKey: ["draws-latest"],
    queryFn: async () => {
      const res = await apiRequest<LatestDrawsData>("/draws/latest");
      return res.data!;
    },
  });

  const listQuery = useQuery({
    queryKey: ["draws-list", lottery, page],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "20",
      });
      if (lottery !== "all") params.set("lottery_type", lottery);
      const res = await apiRequest<DrawListData>(`/draws?${params.toString()}`);
      return res.data!;
    },
  });

  const runsQuery = useQuery({
    queryKey: ["draws-sync-runs"],
    queryFn: async () => {
      const res = await apiRequest<IngestionRunListData>("/draws/sync-runs?page=1&page_size=5");
      return res.data!;
    },
    refetchInterval: 5000,
  });

  const syncMutation = useMutation({
    mutationFn: async (payload: { lottery_type: LotteryType; mode: "incremental" | "full" }) => {
      const res = await apiRequest<SyncAcceptedData>("/draws/sync", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(`已提交 ${data.lottery_type.toUpperCase()} ${data.mode} 同步任务`);
      void queryClient.invalidateQueries({ queryKey: ["draws-sync-runs"] });
      void queryClient.invalidateQueries({ queryKey: ["draws-list"] });
      void queryClient.invalidateQueries({ queryKey: ["draws-latest"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "同步失败");
    },
  });

  const previewMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${API_BASE}/draws/import/preview`, {
        method: "POST",
        body: form,
        credentials: "include",
      });
      const body = await response.json();
      if (!response.ok || !body.success) {
        throw new ApiError(body.error?.message || "预览失败", {
          code: body.error?.code || "HTTP_ERROR",
          status: response.status,
        });
      }
      return body.data as ImportPreviewData;
    },
    onSuccess: (data) => {
      setPreview(data);
      setError(null);
      setMessage(`预览完成：有效 ${data.valid_rows} / 无效 ${data.invalid_rows}`);
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "预览失败");
    },
  });

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (!preview) throw new Error("no preview");
      const rows = preview.rows
        .filter((r) => r.valid)
        .map((r) => ({
          lottery_type: r.lottery_type,
          issue: r.issue,
          draw_date: r.draw_date,
          primary_numbers: r.primary_numbers,
          secondary_numbers: r.secondary_numbers,
        }));
      const res = await apiRequest<ImportCommitData>("/draws/import/commit", {
        method: "POST",
        body: JSON.stringify({ rows }),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(
        `导入完成：新增 ${data.inserted_count} · 更新 ${data.updated_count} · 跳过 ${data.skipped_count} · 错误 ${data.error_count}`,
      );
      setPreview(null);
      void queryClient.invalidateQueries({ queryKey: ["draws-list"] });
      void queryClient.invalidateQueries({ queryKey: ["draws-latest"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "导入提交失败");
    },
  });

  const totalPages = listQuery.data?.total_pages ?? 0;
  const items = listQuery.data?.items ?? [];

  const latestCards = useMemo(
    () => [
      { key: "ssq" as const, title: "双色球最新", draw: latestQuery.data?.ssq ?? null },
      { key: "dlt" as const, title: "大乐透最新", draw: latestQuery.data?.dlt ?? null },
    ],
    [latestQuery.data],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="开奖数据"
        description="查看历史开奖，触发官方源同步，或上传 CSV 预览后导入。"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => syncMutation.mutate({ lottery_type: "ssq", mode: "incremental" })}
              disabled={syncMutation.isPending}
            >
              同步双色球
            </Button>
            <Button
              variant="secondary"
              onClick={() => syncMutation.mutate({ lottery_type: "dlt", mode: "incremental" })}
              disabled={syncMutation.isPending}
            >
              同步大乐透
            </Button>
          </div>
        }
      />

      {message ? <div className="text-sm text-primary">{message}</div> : null}
      {error ? <div className="text-sm text-destructive">{error}</div> : null}

      <div className="grid gap-4 md:grid-cols-2">
        {latestCards.map((card) => (
          <Card key={card.key}>
      <CardContent className="space-y-4 px-6">
            <div className="text-sm text-muted-foreground">{card.title}</div>
            {card.draw ? (
              <>
                <div className="mt-2 text-xl font-semibold">第 {card.draw.issue} 期</div>
                <div className="mt-1 text-xs text-muted-foreground">{card.draw.draw_date}</div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {card.draw.primary_numbers.map((n) => (
                    <NumberBall key={`p-${n}`} n={n} tone="red" />
                  ))}
                  {card.draw.secondary_numbers.map((n) => (
                    <NumberBall key={`s-${n}`} n={n} tone="blue" />
                  ))}
                </div>
              </>
            ) : (
              <div className="mt-3 text-sm text-muted-foreground">暂无数据，请先同步或导入。</div>
            )}
          </CardContent>
    </Card>
        ))}
      </div>

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">CSV 导入</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          先预览校验，再提交有效行。样例：backend/tests/fixtures/ssq_import_20.csv
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".csv,text/csv"
            className="text-sm"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) previewMutation.mutate(file);
            }}
          />
          <Button
            variant="secondary"
            disabled={!preview?.valid_rows || commitMutation.isPending}
            onClick={() => commitMutation.mutate()}
          >
            {commitMutation.isPending ? "导入中..." : `提交有效行 (${preview?.valid_rows ?? 0})`}
          </Button>
        </div>
        {preview ? (
          <div className="mt-4 overflow-x-auto">
            <div className="mb-2 text-xs text-muted-foreground">
              总 {preview.total_rows} · 有效 {preview.valid_rows} · 无效 {preview.invalid_rows}
            </div>
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted-foreground">
                <tr className="border-b border">
                  <th className="px-2 py-2">行</th>
                  <th className="px-2 py-2">彩种</th>
                  <th className="px-2 py-2">期号</th>
                  <th className="px-2 py-2">状态</th>
                  <th className="px-2 py-2">错误</th>
                </tr>
              </thead>
              <tbody>
                {preview.rows.slice(0, 20).map((row) => (
                  <tr key={row.row_number} className="border-b border/70">
                    <td className="px-2 py-2">{row.row_number}</td>
                    <td className="px-2 py-2 uppercase">{row.lottery_type ?? "—"}</td>
                    <td className="px-2 py-2">{row.issue ?? "—"}</td>
                    <td className="px-2 py-2">{row.valid ? "有效" : "无效"}</td>
                    <td className="px-2 py-2 text-destructive">{row.errors.join("; ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </CardContent>
    </Card>

      <Card>
      <CardContent className="space-y-4 px-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-medium">历史记录</h2>
          <div className="flex gap-2">
            {(["all", "ssq", "dlt"] as const).map((key) => (
              <Button
                key={key}
                variant={lottery === key ? "default" : "ghost"}
                onClick={() => {
                  setLottery(key);
                  setPage(1);
                }}
              >
                {key === "all" ? "全部" : key.toUpperCase()}
              </Button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-muted-foreground">
              <tr className="border-b border">
                <th className="px-2 py-2 font-medium">彩种</th>
                <th className="px-2 py-2 font-medium">期号</th>
                <th className="px-2 py-2 font-medium">日期</th>
                <th className="px-2 py-2 font-medium">号码</th>
                <th className="px-2 py-2 font-medium">来源</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td className="px-2 py-6 text-muted-foreground" colSpan={5}>
                    {listQuery.isLoading ? "加载中..." : listQuery.isError ? "加载失败，可重试" : "暂无开奖记录"}
                  </td>
                </tr>
              ) : (
                items.map((row) => (
                  <tr key={row.id} className="border-b border/70">
                    <td className="px-2 py-3 uppercase">{row.lottery_type}</td>
                    <td className="px-2 py-3">{row.issue}</td>
                    <td className="px-2 py-3">{row.draw_date}</td>
                    <td className="px-2 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {row.primary_numbers.map((n) => (
                          <NumberBall key={`${row.id}-p-${n}`} n={n} tone="red" />
                        ))}
                        {row.secondary_numbers.map((n) => (
                          <NumberBall key={`${row.id}-s-${n}`} n={n} tone="blue" />
                        ))}
                      </div>
                    </td>
                    <td className="px-2 py-3 text-muted-foreground">{row.source}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <div>
            共 {listQuery.data?.total ?? 0} 条
            {totalPages ? ` · 第 ${page}/${totalPages} 页` : ""}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              上一页
            </Button>
            <Button
              variant="secondary"
              disabled={!totalPages || page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">最近同步任务</h2>
        <div className="mt-3 space-y-2 text-sm">
          {(runsQuery.data?.items ?? []).length === 0 ? (
            <EmptyState title="还没有同步记录" description="可先触发官方同步或使用 CSV 导入。" />
          ) : (
            (runsQuery.data?.items ?? []).map((run) => (
              <JobProgress
                key={run.id}
                label={`${run.lottery_type.toUpperCase()} · ${run.mode}`}
                status={run.status}
                detail={`+${run.inserted_count} / ~${run.updated_count} / skip ${run.skipped_count}${
                  run.error_count ? ` / err ${run.error_count}` : ""
                }`}
              />
            ))
          )}
        </div>
      </CardContent>
    </Card>
    </div>
  );
}
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { JobProgress } from "@/components/ui/JobProgress";
import { PageHeader } from "@/components/ui/PageHeader";
import { apiRequest } from "@/lib/api";

type JobItem = {
  id: string;
  job_type: string;
  status: string;
  progress_current: number;
  progress_total: number;
  resource_type: string | null;
  resource_id: string | null;
  payload_summary: Record<string, unknown> | null;
  error_code: string | null;
  error_summary: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
};

type JobList = {
  items: JobItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export function JobsPage() {
  const query = useQuery({
    queryKey: ["system-jobs"],
    queryFn: async () => {
      const res = await apiRequest<JobList>("/system/jobs?page=1&page_size=30");
      return res.data!;
    },
    refetchInterval: 4000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="后台任务"
        description="查看同步、推荐、回测等后台任务进度。运行中任务每 4 秒自动刷新。"
      />

      <Card>
        <h2 className="text-lg font-medium">最近任务</h2>
        <div className="mt-3 space-y-2">
          {(query.data?.items ?? []).map((job) => {
            const progress =
              job.progress_total > 0
                ? `${job.progress_current}/${job.progress_total}`
                : String(job.progress_current);
            const detailParts = [
              job.job_type,
              progress,
              job.resource_type ? `${job.resource_type}` : null,
              job.error_summary ? `err: ${job.error_summary}` : null,
              job.created_at ? new Date(job.created_at).toLocaleString() : null,
            ].filter(Boolean);
            return (
              <JobProgress
                key={job.id}
                label={`${job.job_type} · ${job.id.slice(0, 8)}`}
                status={job.status}
                detail={detailParts.join(" · ")}
              />
            );
          })}
          {query.isLoading ? <LoadingState label="加载任务中..." /> : null}
          {query.isError ? (
            <ErrorState title="任务列表加载失败" onRetry={() => void query.refetch()} />
          ) : null}
          {!query.isLoading && !query.isError && !query.data?.items?.length ? (
            <EmptyState title="暂无后台任务" description="触发同步、推荐或回测后会在此显示。" />
          ) : null}
        </div>
      </Card>
    </div>
  );
}
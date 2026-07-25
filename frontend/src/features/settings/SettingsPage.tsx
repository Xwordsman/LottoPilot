import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { apiRequest, ApiError } from "@/lib/api";
import type { AIConfig } from "@/types/recommendations";

type SystemSettings = {
  timezone: string;
  recommendation_count: number;
  ai_weight_cap: number;
  candidate_pool_max: number;
  scheduler_enabled: boolean;
  sync_cron: string;
  swagger_public: boolean;
  default_window: number;
};

type AuditItem = {
  id: string;
  actor_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  request_id: string | null;
  created_at: string | null;
};

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("default");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [model, setModel] = useState("gpt-4o-mini");
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sysForm, setSysForm] = useState<SystemSettings | null>(null);

  const listQuery = useQuery({
    queryKey: ["ai-configs"],
    queryFn: async () => {
      const res = await apiRequest<{ items: AIConfig[] }>("/settings/ai");
      return res.data!.items;
    },
  });

  const systemQuery = useQuery({
    queryKey: ["system-settings"],
    queryFn: async () => {
      const res = await apiRequest<SystemSettings>("/settings/system");
      return res.data!;
    },
  });

  const auditQuery = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () => {
      const res = await apiRequest<{ items: AuditItem[] }>("/audit-logs?page=1&page_size=10");
      return res.data!.items;
    },
  });

  useEffect(() => {
    if (systemQuery.data) {
      setSysForm(systemQuery.data);
    }
  }, [systemQuery.data]);

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest<AIConfig>("/settings/ai", {
        method: "POST",
        body: JSON.stringify({
          name,
          provider: "openai_compatible",
          base_url: baseUrl,
          model,
          api_key: apiKey,
          is_default: true,
        }),
      });
      return res.data!;
    },
    onSuccess: () => {
      setError(null);
      setMessage("AI 配置已保存（Key 已加密存储）");
      setApiKey("");
      void queryClient.invalidateQueries({ queryKey: ["ai-configs"] });
      void queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "保存失败");
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiRequest<{ status: string; model: string; latency_ms: number }>(
        `/settings/ai/${id}/test`,
        { method: "POST" },
      );
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(`连通性测试成功：${data.model} · ${data.latency_ms}ms`);
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "测试失败");
    },
  });

  const defaultMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiRequest<AIConfig>(`/settings/ai/${id}/set-default`, { method: "POST" });
      return res.data!;
    },
    onSuccess: () => {
      setError(null);
      setMessage("已设为默认 AI 配置");
      void queryClient.invalidateQueries({ queryKey: ["ai-configs"] });
      void queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "设为默认失败");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiRequest<{ deleted: boolean; mode: string }>(`/settings/ai/${id}`, {
        method: "DELETE",
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage(data.mode === "soft" ? "配置已软删除（仍被历史推荐引用）" : "配置已删除");
      void queryClient.invalidateQueries({ queryKey: ["ai-configs"] });
      void queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "删除失败");
    },
  });

  const systemMutation = useMutation({
    mutationFn: async () => {
      if (!sysForm) throw new Error("no form");
      const res = await apiRequest<SystemSettings>("/settings/system", {
        method: "PATCH",
        body: JSON.stringify({
          timezone: sysForm.timezone,
          recommendation_count: Number(sysForm.recommendation_count),
          ai_weight_cap: Number(sysForm.ai_weight_cap),
          candidate_pool_max: Number(sysForm.candidate_pool_max),
          scheduler_enabled: Boolean(sysForm.scheduler_enabled),
          sync_cron: sysForm.sync_cron,
          swagger_public: Boolean(sysForm.swagger_public),
          default_window: Number(sysForm.default_window),
        }),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setError(null);
      setMessage("系统设置已更新");
      setSysForm(data);
      void queryClient.invalidateQueries({ queryKey: ["system-settings"] });
      void queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
    },
    onError: (err: unknown) => {
      setMessage(null);
      setError(err instanceof ApiError ? err.message : "系统设置保存失败");
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    createMutation.mutate();
  }

  function onSystemSubmit(e: FormEvent) {
    e.preventDefault();
    systemMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">设置</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          AI 配置支持 OpenAI 兼容接口。Key 仅加密存储，接口只返回脱敏值。系统设置含时区、调度与候选池上限。
        </p>
      </div>

      {listQuery.isLoading ? <LoadingState label="加载 AI 配置..." /> : null}
      {listQuery.isError ? (
        <ErrorState title="AI 配置加载失败" onRetry={() => void listQuery.refetch()} />
      ) : null}
      {systemQuery.isError ? (
        <ErrorState title="系统设置加载失败" onRetry={() => void systemQuery.refetch()} />
      ) : null}
      {auditQuery.isError ? (
        <ErrorState title="审计日志加载失败" onRetry={() => void auditQuery.refetch()} />
      ) : null}

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">新增 / 更新 AI 配置</h2>
        <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onSubmit}>
          <label className="space-y-1 text-sm">
            <span>名称</span>
            <input
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="space-y-1 text-sm">
            <span>模型</span>
            <input
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              required
            />
          </label>
          <label className="space-y-1 text-sm md:col-span-2">
            <span>Base URL</span>
            <input
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              required
            />
          </label>
          <label className="space-y-1 text-sm md:col-span-2">
            <span>API Key</span>
            <input
              type="password"
              className="w-full rounded-xl border border-input bg-background px-3 py-2"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
            />
          </label>
          <div className="md:col-span-2">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "保存中..." : "保存配置"}
            </Button>
          </div>
        </form>
        {message ? <div className="mt-3 text-sm text-primary">{message}</div> : null}
        {error ? <div className="mt-3 text-sm text-destructive">{error}</div> : null}
      </CardContent>
    </Card>

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">已保存配置</h2>
        <div className="mt-3 space-y-2 text-sm">
          {listQuery.isLoading ? <div className="text-sm text-muted-foreground">加载中...</div> : null}
          {!listQuery.isLoading && !listQuery.isError
            ? (listQuery.data ?? []).map((cfg) => (
            <div
              key={cfg.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2"
            >
              <div>
                <div className="font-medium">
                  {cfg.name} {cfg.is_default ? "· 默认" : ""} {!cfg.is_active ? "· 已停用" : ""}
                </div>
                <div className="text-muted-foreground">
                  {cfg.model} · {cfg.base_url} · Key {cfg.api_key_masked || "未设置"}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  onClick={() => testMutation.mutate(cfg.id)}
                  disabled={testMutation.isPending}
                >
                  测试连接
                </Button>
                {!cfg.is_default ? (
                  <Button
                    variant="secondary"
                    onClick={() => defaultMutation.mutate(cfg.id)}
                    disabled={defaultMutation.isPending || !cfg.is_active}
                  >
                    设为默认
                  </Button>
                ) : null}
                <Button
                  variant="secondary"
                  onClick={() => deleteMutation.mutate(cfg.id)}
                  disabled={deleteMutation.isPending}
                >
                  删除
                </Button>
              </div>
            </div>
          )) : null}
          {!listQuery.isLoading && !listQuery.isError && !listQuery.data?.length ? (
            <div className="text-muted-foreground">暂无 AI 配置。</div>
          ) : null}
        </div>
      </CardContent>
    </Card>

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">系统设置</h2>
        {sysForm ? (
          <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onSystemSubmit}>
            <label className="space-y-1 text-sm">
              <span>时区</span>
              <input
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
                value={sysForm.timezone}
                onChange={(e) => setSysForm({ ...sysForm, timezone: e.target.value })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span>默认同步 Cron</span>
              <input
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
                value={sysForm.sync_cron}
                onChange={(e) => setSysForm({ ...sysForm, sync_cron: e.target.value })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span>推荐注数</span>
              <input
                type="number"
                min={1}
                max={20}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
                value={sysForm.recommendation_count}
                onChange={(e) =>
                  setSysForm({ ...sysForm, recommendation_count: Number(e.target.value) })
                }
              />
            </label>
            <label className="space-y-1 text-sm">
              <span>AI 权重上限（≤0.10）</span>
              <input
                type="number"
                step="0.01"
                min={0}
                max={0.1}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
                value={sysForm.ai_weight_cap}
                onChange={(e) => setSysForm({ ...sysForm, ai_weight_cap: Number(e.target.value) })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span>候选池上限</span>
              <input
                type="number"
                min={500}
                max={100000}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
                value={sysForm.candidate_pool_max}
                onChange={(e) =>
                  setSysForm({ ...sysForm, candidate_pool_max: Number(e.target.value) })
                }
              />
            </label>
            <label className="space-y-1 text-sm">
              <span>默认统计窗口</span>
              <input
                type="number"
                min={5}
                max={5000}
                className="w-full rounded-xl border border-input bg-background px-3 py-2"
                value={sysForm.default_window}
                onChange={(e) => setSysForm({ ...sysForm, default_window: Number(e.target.value) })}
              />
            </label>
            <label className="inline-flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={sysForm.scheduler_enabled}
                onChange={(e) => setSysForm({ ...sysForm, scheduler_enabled: e.target.checked })}
              />
              启用定时同步
            </label>
            <label className="inline-flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={sysForm.swagger_public}
                onChange={(e) => setSysForm({ ...sysForm, swagger_public: e.target.checked })}
              />
              公开 Swagger
            </label>
            <div className="md:col-span-2">
              <Button type="submit" disabled={systemMutation.isPending}>
                {systemMutation.isPending ? "保存中..." : "保存系统设置"}
              </Button>
            </div>
          </form>
        ) : (
          <div className="mt-3"><LoadingState label="加载系统设置..." /></div>
        )}
      </CardContent>
    </Card>

      <Card>
      <CardContent className="space-y-4 px-6">
        <h2 className="text-lg font-medium">最近审计日志</h2>
        <div className="mt-3 space-y-2 text-sm">
          {auditQuery.isLoading ? <LoadingState label="加载审计日志..." /> : null}
          {!auditQuery.isLoading && !auditQuery.isError
            ? (auditQuery.data ?? []).map((item) => (
            <div
              key={item.id}
              className="rounded-xl border px-3 py-2 text-foreground"
            >
              <div className="font-medium">
                {item.action} · {item.resource_type}
                {item.resource_id ? ` / ${item.resource_id.slice(0, 8)}` : ""}
              </div>
              <div className="text-xs text-muted-foreground">
                {item.created_at ? new Date(item.created_at).toLocaleString() : "—"}
              </div>
            </div>
          )) : null}
          {!auditQuery.isLoading && !auditQuery.isError && !auditQuery.data?.length ? (
            <div className="text-muted-foreground">暂无审计记录。</div>
          ) : null}
        </div>
      </CardContent>
    </Card>
    </div>
  );
}
import { useMutation } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiRequest, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { LoginData } from "@/types/api";

export function SetupPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const setInitialized = useAuthStore((s) => s.setInitialized);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("管理员");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest<LoginData>("/setup", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          display_name: displayName,
        }),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setUser(data.user);
      setInitialized(true);
      navigate("/", { replace: true });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) setError(err.message);
      else setError("初始化失败");
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate();
  }

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-lg items-center">
      <Card className="w-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">初始化 LottoPilot</h1>
          <p className="mt-2 text-sm text-slate-400">
            首次启动需要创建管理员账号。完成后即可登录使用。
          </p>
        </div>
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block space-y-2 text-sm">
            <span>显示名称</span>
            <input
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 outline-none ring-sky-500 focus:ring-2"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-2 text-sm">
            <span>管理员邮箱</span>
            <input
              type="email"
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 outline-none ring-sky-500 focus:ring-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-2 text-sm">
            <span>密码（至少 8 位）</span>
            <input
              type="password"
              minLength={8}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 outline-none ring-sky-500 focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error ? <div className="text-sm text-rose-400">{error}</div> : null}
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {mutation.isPending ? "创建中..." : "完成初始化"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

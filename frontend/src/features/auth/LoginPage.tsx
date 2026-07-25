import { useMutation } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiRequest, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { LoginData } from "@/types/api";

export function LoginPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest<LoginData>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      return res.data!;
    },
    onSuccess: (data) => {
      setUser(data.user);
      navigate("/", { replace: true });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) setError(err.message);
      else setError("登录失败");
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
          <h1 className="text-2xl font-semibold">登录</h1>
          <p className="mt-2 text-sm text-slate-400">使用管理员邮箱和密码进入 LottoPilot。</p>
        </div>
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block space-y-2 text-sm">
            <span>邮箱</span>
            <input
              type="email"
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 outline-none ring-sky-500 focus:ring-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-2 text-sm">
            <span>密码</span>
            <input
              type="password"
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 outline-none ring-sky-500 focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error ? <div className="text-sm text-rose-400">{error}</div> : null}
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {mutation.isPending ? "登录中..." : "登录"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

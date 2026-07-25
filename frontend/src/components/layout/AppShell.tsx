import { NavLink, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { apiRequest } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/cn";
import { useThemeStore } from "@/lib/theme-store";

const links = [
  { to: "/", label: "推荐" },
  { to: "/recommendations", label: "记录" },
  { to: "/draws", label: "开奖" },
  { to: "/analytics", label: "统计" },
  { to: "/backtests", label: "回测" },
  { to: "/strategies", label: "策略" },
  { to: "/jobs", label: "任务" },
  { to: "/settings", label: "设置" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const setUser = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();

  async function logout() {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } catch {
      // ignore network error; clear local session anyway
    }
    setUser(null);
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen pb-20 md:pb-0">
      <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400 to-violet-500 text-sm font-bold text-slate-950">
              LP
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight">LottoPilot</div>
              <div className="text-xs text-slate-400">历史分析 · 候选推荐 · 滚动回测</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <nav className="hidden items-center gap-1 md:flex">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === "/"}
                  className={({ isActive }) =>
                    cn(
                      "rounded-xl px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800 hover:text-white",
                      isActive && "bg-slate-800 text-white",
                    )
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <Button variant="secondary" onClick={toggleTheme} aria-label="切换主题">
              {theme === "dark" ? "浅色" : "深色"}
            </Button>
            <Button variant="ghost" onClick={() => void logout()}>
              退出
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-slate-500">
        本系统只做历史数据分析与模型评分，不承诺中奖，不提供购彩交易。
      </footer>
      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-800 bg-slate-950/95 backdrop-blur md:hidden">
        <div className="mx-auto grid max-w-7xl grid-cols-4 gap-1 px-2 py-2 sm:grid-cols-7">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                cn(
                  "rounded-lg px-1 py-2 text-center text-[11px] text-slate-400",
                  isActive && "bg-slate-800 text-white",
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
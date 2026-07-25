import {
  BarChart3,
  Database,
  History,
  LayoutDashboard,
  LogOut,
  Moon,
  Settings2,
  Sun,
  Target,
  Ticket,
  Workflow,
} from "lucide-react"
import type { ReactNode } from "react"
import { NavLink, useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { apiRequest } from "@/lib/api"
import { useAuthStore } from "@/lib/auth-store"
import { cn } from "@/lib/utils"
import { useThemeStore } from "@/lib/theme-store"

const nav = [
  { to: "/", label: "推荐", icon: LayoutDashboard },
  { to: "/recommendations", label: "记录", icon: Ticket },
  { to: "/draws", label: "开奖", icon: History },
  { to: "/analytics", label: "统计", icon: BarChart3 },
  { to: "/backtests", label: "回测", icon: Target },
  { to: "/strategies", label: "策略", icon: Workflow },
  { to: "/jobs", label: "任务", icon: Database },
  { to: "/settings", label: "设置", icon: Settings2 },
]

export function AppShell({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const theme = useThemeStore((s) => s.theme)
  const toggleTheme = useThemeStore((s) => s.toggleTheme)
  const navigate = useNavigate()

  async function logout() {
    try {
      await apiRequest("/auth/logout", { method: "POST" })
    } catch {
      // ignore
    }
    setUser(null)
    navigate("/login", { replace: true })
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen max-w-7xl">
        <aside className="hidden w-64 shrink-0 border-r bg-sidebar text-sidebar-foreground md:flex md:flex-col">
          <div className="flex h-16 items-center gap-2 px-6">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
              LP
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight">LottoPilot</div>
              <div className="text-xs text-muted-foreground">分析 · 推荐 · 回测</div>
            </div>
          </div>
          <Separator />
          <nav className="flex flex-1 flex-col gap-1 p-3">
            {nav.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                        : "text-muted-foreground hover:bg-sidebar-accent/70 hover:text-foreground"
                    )
                  }
                >
                  <Icon className="size-4" />
                  {item.label}
                </NavLink>
              )
            })}
          </nav>
          <div className="space-y-3 border-t p-4">
            <div className="text-xs text-muted-foreground">
              {user ? `${user.display_name} · ${user.email}` : "未登录"}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1" onClick={toggleTheme}>
                {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
                {theme === "dark" ? "浅色" : "深色"}
              </Button>
              <Button variant="outline" size="sm" onClick={() => void logout()}>
                <LogOut className="size-4" />
              </Button>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b bg-background/90 px-4 backdrop-blur md:hidden">
            <div className="font-semibold">LottoPilot</div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={toggleTheme}>
                {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
              </Button>
              <Button variant="outline" size="sm" onClick={() => void logout()}>
                退出
              </Button>
            </div>
          </header>
          <div className="border-b bg-background px-3 py-2 md:hidden">
            <div className="flex gap-1 overflow-x-auto">
              {nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    cn(
                      "rounded-md px-3 py-1.5 text-xs whitespace-nowrap",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
          <main className="flex-1 space-y-6 p-4 md:p-8">{children}</main>
          <footer className="border-t px-4 py-4 text-xs text-muted-foreground md:px-8">
            本系统只做历史数据分析与模型评分，不承诺中奖，不提供购彩交易。
          </footer>
        </div>
      </div>
    </div>
  )
}

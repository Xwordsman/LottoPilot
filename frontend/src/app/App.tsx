import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "@/app/router";
import { apiRequest, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useThemeStore } from "@/lib/theme-store";
import type { SetupStatus, UserPublic } from "@/types/api";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function ThemeBootstrap({ children }: { children: React.ReactNode }) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  useEffect(() => {
    setTheme(theme);
  }, [setTheme, theme]);

  return children;
}

function Bootstrap({ children }: { children: React.ReactNode }) {
  const setInitialized = useAuthStore((s) => s.setInitialized);
  const setUser = useAuthStore((s) => s.setUser);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await apiRequest<SetupStatus>("/setup/status");
        if (cancelled) return;
        setInitialized(Boolean(status.data?.initialized));
        if (status.data?.initialized) {
          try {
            const me = await apiRequest<UserPublic>("/auth/me");
            if (!cancelled) setUser(me.data);
          } catch (err) {
            if (err instanceof ApiError && err.status === 401) {
              setUser(null);
            }
          }
        }
      } catch {
        if (!cancelled) setInitialized(false);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setInitialized, setUser]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-300">
        正在加载 LottoPilot...
      </div>
    );
  }

  return children;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeBootstrap>
          <Bootstrap>
            <AppRouter />
          </Bootstrap>
        </ThemeBootstrap>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
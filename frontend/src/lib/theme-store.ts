import { create } from "zustand"

export type ThemeMode = "dark" | "light"

type ThemeState = {
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
}

function applyTheme(theme: ThemeMode) {
  if (typeof document === "undefined") return
  const rootEl = document.documentElement
  rootEl.dataset.theme = theme
  rootEl.style.colorScheme = theme
  rootEl.classList.toggle("dark", theme === "dark")
  rootEl.classList.toggle("light", theme === "light")
}

function readInitialTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark"
  const saved = window.localStorage.getItem("lottopilot-theme")
  if (saved === "light" || saved === "dark") return saved
  return "dark"
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: readInitialTheme(),
  setTheme: (theme) => {
    window.localStorage.setItem("lottopilot-theme", theme)
    applyTheme(theme)
    set({ theme })
  },
  toggleTheme: () => {
    const next = get().theme === "dark" ? "light" : "dark"
    get().setTheme(next)
  },
}))

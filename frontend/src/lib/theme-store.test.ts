import { beforeEach, describe, expect, it, vi } from "vitest"

describe("theme-store", () => {
  beforeEach(() => {
    vi.resetModules()
    const mem = new Map<string, string>()
    const classSet = new Set<string>()
    const localStorageMock = {
      getItem: (k: string) => mem.get(k) ?? null,
      setItem: (k: string, v: string) => {
        mem.set(k, v)
      },
      removeItem: (k: string) => {
        mem.delete(k)
      },
      clear: () => mem.clear(),
    }
    const documentElement = {
      dataset: {} as Record<string, string>,
      style: { colorScheme: "" },
      classList: {
        add: (v: string) => classSet.add(v),
        remove: (v: string) => classSet.delete(v),
        toggle: (v: string, force?: boolean) => {
          if (force === true) classSet.add(v)
          else if (force === false) classSet.delete(v)
          else if (classSet.has(v)) classSet.delete(v)
          else classSet.add(v)
          return classSet.has(v)
        },
        contains: (v: string) => classSet.has(v),
      },
    }
    vi.stubGlobal("localStorage", localStorageMock)
    vi.stubGlobal("window", { localStorage: localStorageMock })
    vi.stubGlobal("document", { documentElement })
  })

  it("defaults to dark and persists toggle", async () => {
    const { useThemeStore } = await import("./theme-store")
    expect(useThemeStore.getState().theme).toBe("dark")
    useThemeStore.getState().toggleTheme()
    expect(useThemeStore.getState().theme).toBe("light")
    expect(window.localStorage.getItem("lottopilot-theme")).toBe("light")
    expect(document.documentElement.dataset.theme).toBe("light")
    expect(document.documentElement.style.colorScheme).toBe("light")
    useThemeStore.getState().setTheme("dark")
    expect(useThemeStore.getState().theme).toBe("dark")
    expect(window.localStorage.getItem("lottopilot-theme")).toBe("dark")
  })

  it("reads saved light theme on init", async () => {
    window.localStorage.setItem("lottopilot-theme", "light")
    const { useThemeStore } = await import("./theme-store")
    expect(useThemeStore.getState().theme).toBe("light")
  })
})

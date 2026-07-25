import { beforeEach, describe, expect, it, vi } from "vitest";

describe("auth-store", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("tracks user and initialized flags", async () => {
    const { useAuthStore } = await import("./auth-store");
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().initialized).toBeNull();
    useAuthStore.getState().setInitialized(false);
    expect(useAuthStore.getState().initialized).toBe(false);
    useAuthStore.getState().setInitialized(true);
    useAuthStore.getState().setUser({
      id: "u1",
      email: "a@example.com",
      display_name: "A",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    } as never);
    expect(useAuthStore.getState().user?.email).toBe("a@example.com");
    useAuthStore.getState().reset();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().initialized).toBeNull();
  });
});

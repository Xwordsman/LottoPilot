import { create } from "zustand";
import type { UserPublic } from "@/types/api";

type AuthState = {
  user: UserPublic | null;
  initialized: boolean | null;
  setUser: (user: UserPublic | null) => void;
  setInitialized: (value: boolean) => void;
  reset: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  initialized: null,
  setUser: (user) => set({ user }),
  setInitialized: (initialized) => set({ initialized }),
  reset: () => set({ user: null, initialized: null }),
}));

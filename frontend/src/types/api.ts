export type APIErrorBody = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type APIResponse<T> = {
  success: boolean;
  data: T | null;
  error: APIErrorBody | null;
  request_id: string;
};

export type SetupStatus = {
  initialized: boolean;
};

export type UserPublic = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
};

export type LoginData = {
  user: UserPublic;
};

export type SystemInfo = {
  app_name: string;
  version: string;
  git_commit: string;
  build_time: string | null;
  env: string;
  latest_draws: Record<string, string | null>;
};

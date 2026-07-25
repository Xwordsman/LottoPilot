import type { APIResponse } from "@/types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;
  requestId?: string;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    opts: { code: string; status: number; requestId?: string; details?: Record<string, unknown> },
  ) {
    super(message);
    this.name = "ApiError";
    this.code = opts.code;
    this.status = opts.status;
    this.requestId = opts.requestId;
    this.details = opts.details;
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<APIResponse<T>> {
  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  let body: APIResponse<T> | null = null;
  try {
    body = (await response.json()) as APIResponse<T>;
  } catch {
    throw new ApiError("响应不是合法 JSON", {
      code: "INVALID_JSON",
      status: response.status,
    });
  }

  if (!response.ok || !body.success) {
    throw new ApiError(body.error?.message || "请求失败", {
      code: body.error?.code || "HTTP_ERROR",
      status: response.status,
      requestId: body.request_id,
      details: body.error?.details,
    });
  }

  return body;
}

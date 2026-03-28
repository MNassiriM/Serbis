/**
 * API client — typed fetch wrapper for the GenERP backend.
 */

import type { SSEEvent } from "@/types/erp";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Base fetch utility
// ---------------------------------------------------------------------------

async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Tenant API
// ---------------------------------------------------------------------------

export interface CreateTenantPayload {
  name: string;
  industry: string;
  size: "1-10" | "11-50" | "51-200" | "200+";
  plan?: "free" | "pro" | "enterprise";
}

export interface CreateTenantResult {
  tenant: {
    id: string;
    name: string;
    slug: string;
    plan: string;
    schema_name: string;
  };
  access_token: string;
  token_type: string;
}

export const tenantsApi = {
  create: (payload: CreateTenantPayload) =>
    apiFetch<CreateTenantResult>("/api/v1/tenants", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: (token: string) =>
    apiFetch<CreateTenantResult["tenant"]>("/api/v1/tenants/me", { token }),
};

// ---------------------------------------------------------------------------
// Chat / SSE API
// ---------------------------------------------------------------------------

export interface ChatPayload {
  message: string;
  conversation_id?: string;
}

/**
 * Opens an SSE connection to the chat endpoint and calls the callback
 * for each parsed event. Resolves when the stream is done.
 */
export async function streamChat(
  payload: ChatPayload,
  token: string,
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => ({ detail: "Stream failed" }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (!data) continue;
        try {
          const event = JSON.parse(data) as SSEEvent;
          onEvent(event);
          if (event.type === "done") return;
        } catch {
          console.warn("Failed to parse SSE event:", data);
        }
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Modules API
// ---------------------------------------------------------------------------

export const modulesApi = {
  list: (token: string) =>
    apiFetch<
      Array<{
        id: string;
        name: string;
        display_name: string;
        category: string;
        ui_config: Record<string, unknown>;
        is_active: boolean;
      }>
    >("/api/v1/modules", { token }),
};

// ---------------------------------------------------------------------------
// Data API (CRUD on generated tenant entities)
// ---------------------------------------------------------------------------

export function createDataApi(tenantId: string, token: string) {
  const base = `/api/v1/data/${tenantId}`;

  return {
    list: <T>(entity: string, params?: Record<string, string>) => {
      const qs = params ? `?${new URLSearchParams(params)}` : "";
      return apiFetch<T[]>(`${base}/${entity}${qs}`, { token });
    },
    get: <T>(entity: string, id: string) =>
      apiFetch<T>(`${base}/${entity}/${id}`, { token }),
    create: <T>(entity: string, data: unknown) =>
      apiFetch<T>(`${base}/${entity}`, {
        method: "POST",
        body: JSON.stringify(data),
        token,
      }),
    update: <T>(entity: string, id: string, data: unknown) =>
      apiFetch<T>(`${base}/${entity}/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
        token,
      }),
    delete: (entity: string, id: string) =>
      apiFetch<void>(`${base}/${entity}/${id}`, {
        method: "DELETE",
        token,
      }),
  };
}

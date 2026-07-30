// Тонкий клиент к бэкенду. Все запросы идут на относительный /api,
// а проксирование настроено в vite.config.ts (dev).

import type { Constraints, LookOut, LookSummary, Profile } from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`${resp.status}: ${detail}`);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  // Задать вопрос или попросить образ — главный эндпоинт.
  ask(
    userId: string,
    text: string,
    constraints?: Partial<Constraints>,
  ): Promise<LookOut> {
    return request<LookOut>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, text, constraints: constraints ?? {} }),
    });
  },

  // История образов и ответов.
  listLooks(userId: string): Promise<LookSummary[]> {
    return request<LookSummary[]>(`/api/looks?user_id=${encodeURIComponent(userId)}`);
  },

  getLook(id: number): Promise<LookOut> {
    return request<LookOut>(`/api/looks/${id}`);
  },

  // Профиль: внешность, вкус, постоянные ограничения.
  getProfile(userId: string): Promise<Profile> {
    return request<Profile>(`/api/profile?user_id=${encodeURIComponent(userId)}`);
  },

  saveProfile(userId: string, data: unknown): Promise<Profile> {
    return request<Profile>(`/api/profile?user_id=${encodeURIComponent(userId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
};

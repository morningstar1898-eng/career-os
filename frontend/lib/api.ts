const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("career_os_token") || "";
}

export async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (res.status === 401 || res.status === 403) {
    // Session token expired (backend redeploy) or missing — force re-login.
    if (typeof window !== "undefined") localStorage.removeItem("career_os_token");
    throw new Error(`API auth error: ${res.status}`);
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function wsURL(path: string): string {
  const base = API_BASE.replace(/^http/, "ws");
  const token = getToken();
  // Browsers can't set headers on WebSocket connections — token goes in the query string.
  return `${base}${path}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
}

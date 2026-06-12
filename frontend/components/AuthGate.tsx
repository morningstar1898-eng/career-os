"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "../lib/api";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("career_os_token");
    if (!token) {
      setAuthed(false);
      return;
    }
    fetchAPI<{ valid: boolean }>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then((res) => setAuthed(res.valid))
      .catch(() => setAuthed(false));
  }, []);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetchAPI<{ token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      localStorage.setItem("career_os_token", res.token);
      setAuthed(true);
    } catch {
      setError("Wrong password");
    }
    setLoading(false);
  }

  if (authed === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!authed) {
    return (
      <main className="min-h-screen flex items-center justify-center p-4">
        <form onSubmit={handleLogin} className="glass-card p-8 w-full max-w-sm space-y-4">
          <h1 className="text-xl font-bold text-center">Career <span className="text-accent">OS</span></h1>
          <p className="text-sm text-zinc-400 text-center">Enter password to access the dashboard</p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full bg-transparent border border-card-border rounded-lg p-3 text-sm focus:outline-none focus:border-accent"
            autoFocus
          />
          {error && <p className="text-danger text-sm text-center">{error}</p>}
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-2 bg-accent rounded-lg text-sm font-medium disabled:opacity-50 glow"
          >
            {loading ? "Logging in..." : "Log In"}
          </button>
        </form>
      </main>
    );
  }

  return <>{children}</>;
}

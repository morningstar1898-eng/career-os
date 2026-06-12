"use client";

import { useEffect, useState, useRef } from "react";
import { fetchAPI, wsURL } from "../../lib/api";
import Link from "next/link";

interface Run {
  id: number;
  started_at: string;
  finished_at?: string;
  status: string;
  trigger: string;
}

export default function AgentsPage() {
  const [logs, setLogs] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [latestRun, setLatestRun] = useState<Run | null>(null);
  const [triggering, setTriggering] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAPI<Run>("/runs/latest").then(setLatestRun).catch(() => {});

    const ws = new WebSocket(wsURL("/ws/agents"));
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      setLogs((prev) => [...prev.slice(-500), event.data]);
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  async function triggerRun() {
    setTriggering(true);
    setLogs([]);
    const run = await fetchAPI<Run>("/runs/trigger", { method: "POST", body: JSON.stringify({ trigger: "manual" }) });
    setLatestRun(run);
    setTriggering(false);
  }

  return (
    <main className="min-h-screen p-6 max-w-6xl mx-auto">
      <nav className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Agent <span className="text-[var(--color-accent)]">Monitor</span></h1>
        <div className="flex gap-4 text-sm items-center">
          <span className={`flex items-center gap-1.5 text-xs ${connected ? "text-[var(--color-success)]" : "text-zinc-500"}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-[var(--color-success)] pulse-dot" : "bg-zinc-600"}`} />
            {connected ? "Live" : "Disconnected"}
          </span>
          <Link href="/dashboard" className="text-zinc-400 hover:text-white">Dashboard</Link>
        </div>
      </nav>

      <div className="flex items-center gap-4 mb-6">
        <button onClick={triggerRun} disabled={triggering || latestRun?.status === "running"}
          className="px-4 py-2 bg-[var(--color-accent)] rounded-lg text-sm font-medium disabled:opacity-50 glow">
          {triggering ? "Starting..." : "Trigger Run"}
        </button>
        {latestRun && (
          <span className="text-sm text-zinc-400">
            Last run: <span className={latestRun.status === "success" ? "text-[var(--color-success)]" : latestRun.status === "running" ? "text-[var(--color-warning)]" : "text-[var(--color-danger)]"}>
              {latestRun.status}
            </span>
            {" "}({latestRun.trigger})
          </span>
        )}
      </div>

      <div className="glass-card p-4 h-[70vh] overflow-y-auto font-mono text-xs">
        {logs.length === 0 ? (
          <p className="text-zinc-500">Waiting for agent output... Trigger a run or wait for the daily cron.</p>
        ) : (
          logs.map((line, i) => (
            <div key={i} className="py-0.5 border-b border-zinc-800/50">
              <span className="text-zinc-500 mr-2">{String(i + 1).padStart(3)}</span>
              <span className={line.includes("[Agent]") ? "text-[var(--color-accent)]" : line.includes("ERROR") ? "text-[var(--color-danger)]" : ""}>{line}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </main>
  );
}

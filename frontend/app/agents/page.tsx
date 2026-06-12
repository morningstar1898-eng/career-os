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

const AGENT_NAMES = ["Skills Scout", "Data Analyst", "Tutor", "Job Applicant", "Interview Coach", "Orchestrator"];
const AGENT_COLORS: Record<string, string> = {
  "Skills Scout": "text-blue-400",
  "Data Analyst": "text-emerald-400",
  "Tutor": "text-amber-400",
  "Job Applicant": "text-rose-400",
  "Interview Coach": "text-violet-400",
  "Orchestrator": "text-cyan-400",
};

function colorLine(line: string): { className: string; agent: string | null } {
  for (const name of AGENT_NAMES) {
    if (line.toLowerCase().includes(name.toLowerCase())) {
      return { className: AGENT_COLORS[name] || "", agent: name };
    }
  }
  if (line.includes("ERROR") || line.includes("error") || line.includes("failed")) {
    return { className: "text-danger", agent: null };
  }
  if (line.includes("✅") || line.includes("success") || line.includes("Done")) {
    return { className: "text-success", agent: null };
  }
  return { className: "", agent: null };
}

export default function AgentsPage() {
  const [logs, setLogs] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [latestRun, setLatestRun] = useState<Run | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [elapsed, setElapsed] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchAPI<Run>("/runs/latest").then(setLatestRun).catch(() => {});

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsURL("/ws/agents"));
      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onerror = () => setConnected(false);
      ws.onmessage = (event) => {
        setLogs((prev) => [...prev.slice(-500), event.data]);
      };
    } catch {
      setConnected(false);
    }
    return () => { if (ws) ws.close(); };
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    if (latestRun?.status === "running") {
      const start = new Date(latestRun.started_at).getTime();
      timerRef.current = setInterval(() => {
        const secs = Math.floor((Date.now() - start) / 1000);
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        setElapsed(`${m}:${String(s).padStart(2, "0")}`);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setElapsed(null);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [latestRun?.status]);

  async function triggerRun() {
    setTriggering(true);
    setLogs([]);
    try {
      const run = await fetchAPI<Run>("/runs/trigger", { method: "POST", body: JSON.stringify({ trigger: "manual" }) });
      setLatestRun(run);
    } catch {
      alert("Start the backend API first.");
    }
    setTriggering(false);
  }

  function pollStatus() {
    if (latestRun) {
      fetchAPI<Run>(`/runs/status/${latestRun.id}`).then(setLatestRun).catch(() => {});
    }
  }

  useEffect(() => {
    if (latestRun?.status === "running") {
      const interval = setInterval(pollStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [latestRun?.status, latestRun?.id]);

  return (
    <main className="min-h-screen p-6 max-w-6xl mx-auto pb-24">
      <nav className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Agent <span className="text-accent">Monitor</span></h1>
        <div className="flex gap-4 text-sm items-center">
          <span className={`flex items-center gap-1.5 text-xs ${connected ? "text-success" : "text-zinc-500"}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-success pulse-dot" : "bg-zinc-600"}`} />
            {connected ? "Live" : "Disconnected"}
          </span>
          <Link href="/dashboard" className="text-zinc-400 hover:text-white">Dashboard</Link>
        </div>
      </nav>

      {/* Agent status chips */}
      <div className="flex flex-wrap gap-2 mb-6">
        {AGENT_NAMES.map((name) => {
          const active = logs.some((l) => l.toLowerCase().includes(name.toLowerCase()));
          return (
            <span key={name} className={`px-3 py-1 rounded-full text-xs border ${active ? `${AGENT_COLORS[name]} border-current` : "text-zinc-600 border-zinc-800"}`}>
              {active && <span className="inline-block w-1.5 h-1.5 rounded-full bg-current mr-1.5 pulse-dot" />}
              {name}
            </span>
          );
        })}
      </div>

      <div className="flex items-center gap-4 mb-6">
        <button onClick={triggerRun} disabled={triggering || latestRun?.status === "running"}
          className="px-4 py-2 bg-accent rounded-lg text-sm font-medium disabled:opacity-50 glow">
          {triggering ? "Starting..." : latestRun?.status === "running" ? "Running..." : "Trigger Run"}
        </button>
        {elapsed && (
          <span className="text-sm text-warning font-mono">{elapsed}</span>
        )}
        {latestRun && (
          <span className="text-sm text-zinc-400">
            Last run:{" "}
            <span className={latestRun.status === "success" ? "text-success" : latestRun.status === "running" ? "text-warning" : "text-danger"}>
              {latestRun.status}
            </span>
            {" "}({latestRun.trigger})
          </span>
        )}
      </div>

      <div className="glass-card p-4 h-[65vh] overflow-y-auto font-mono text-xs">
        {logs.length === 0 ? (
          <p className="text-zinc-500">Waiting for agent output... Trigger a run or wait for the daily cron.</p>
        ) : (
          logs.map((line, i) => {
            const { className } = colorLine(line);
            return (
              <div key={i} className="py-0.5 border-b border-zinc-800/30 hover:bg-zinc-800/30">
                <span className="text-zinc-600 mr-2 select-none">{String(i + 1).padStart(3)}</span>
                <span className={className}>{line}</span>
              </div>
            );
          })
        )}
        <div ref={logsEndRef} />
      </div>
    </main>
  );
}

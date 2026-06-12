"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "../../lib/api";
import { AnalyticsCharts } from "../../components/AnalyticsCharts";
import Link from "next/link";

interface Summary {
  total_jobs_applied: number;
  total_successful_runs: number;
  avg_interview_score: number;
  days_active: number;
}

interface Briefing {
  date: string;
  content_json: string;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAPI<Summary>("/analytics/summary").then(setSummary).catch(() => {});
    fetchAPI<Briefing>("/briefings/today").then(setBriefing).catch(() => setError("No briefing today yet"));
  }, []);

  return (
    <main className="min-h-screen p-6 max-w-6xl mx-auto">
      <nav className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Career OS <span className="text-[var(--color-accent)]">Dashboard</span></h1>
        <div className="flex gap-4 text-sm">
          <Link href="/" className="text-zinc-400 hover:text-white">Home</Link>
          <Link href="/interview" className="text-zinc-400 hover:text-white">Interview</Link>
          <Link href="/agents" className="text-zinc-400 hover:text-white">Agents</Link>
        </div>
      </nav>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Jobs Applied" value={summary.total_jobs_applied} />
          <StatCard label="Successful Runs" value={summary.total_successful_runs} />
          <StatCard label="Avg Interview Score" value={`${summary.avg_interview_score}/10`} />
          <StatCard label="Days Active" value={summary.days_active} />
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold mb-4">Today&apos;s Briefing</h2>
          {error ? (
            <p className="text-zinc-500 text-sm">{error}</p>
          ) : briefing ? (
            <div className="text-sm text-zinc-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
              {JSON.parse(briefing.content_json).raw_output || "Loading..."}
            </div>
          ) : (
            <p className="text-zinc-500 text-sm">Loading...</p>
          )}
        </div>

        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold mb-4">Progress Over Time</h2>
          <AnalyticsCharts />
        </div>
      </div>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="glass-card p-4 text-center">
      <div className="text-2xl font-bold text-[var(--color-accent)]">{value}</div>
      <div className="text-xs text-zinc-400 mt-1">{label}</div>
    </div>
  );
}

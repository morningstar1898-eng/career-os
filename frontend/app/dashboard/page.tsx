"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "../../lib/api";
import { speak, stopSpeaking } from "../../lib/voice";
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
  const [briefing, setBriefing] = useState<any>(null);
  const [error, setError] = useState("");
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    fetchAPI<Summary>("/analytics/summary").then(setSummary).catch(() => {});
    fetchAPI<Briefing>("/briefings/today")
      .then((b) => setBriefing(JSON.parse(b.content_json)))
      .catch(() => setError("No briefing today yet. Run agents or seed demo data."));
  }, []);

  function readBriefing() {
    if (!briefing) return;
    if (speaking) { stopSpeaking(); setSpeaking(false); return; }
    setSpeaking(true);
    const text = briefing.raw_output ||
      `Today's market signals: ${briefing.market_signal?.join(", ")}. ${briefing.lesson_summary || ""}. ${briefing.portfolio_update || ""}. ${briefing.tomorrow_focus || ""}`;
    speak(text, () => setSpeaking(false));
  }

  return (
    <main className="min-h-screen p-6 max-w-6xl mx-auto">
      <nav className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Career OS <span className="text-accent">Dashboard</span></h1>
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
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Today&apos;s Briefing</h2>
            {briefing && (
              <button onClick={readBriefing} className="text-xs px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700">
                {speaking ? "Stop" : "Read Aloud"}
              </button>
            )}
          </div>
          {error ? (
            <p className="text-zinc-500 text-sm">{error}</p>
          ) : briefing ? (
            <div className="text-sm space-y-4 max-h-[500px] overflow-y-auto">
              {briefing.raw_output ? (
                <p className="text-zinc-300 whitespace-pre-wrap">{briefing.raw_output}</p>
              ) : (
                <>
                  {briefing.market_signal && (
                    <div>
                      <h3 className="text-xs text-accent uppercase mb-1">Market Signals</h3>
                      <ul className="text-zinc-300 space-y-1">
                        {briefing.market_signal.map((s: string, i: number) => <li key={i}>- {s}</li>)}
                      </ul>
                    </div>
                  )}
                  {briefing.lesson_summary && (
                    <div>
                      <h3 className="text-xs text-accent uppercase mb-1">Today&apos;s Lesson</h3>
                      <p className="text-zinc-300">{briefing.lesson_summary}</p>
                    </div>
                  )}
                  {briefing.jobs_applied && (
                    <div>
                      <h3 className="text-xs text-accent uppercase mb-1">Jobs Applied</h3>
                      <div className="space-y-1">
                        {briefing.jobs_applied.map((j: any, i: number) => (
                          <div key={i} className="flex justify-between text-zinc-300">
                            <span>{j.company} — {j.role}</span>
                            <span className="text-success text-xs">{j.status}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {briefing.portfolio_update && (
                    <div>
                      <h3 className="text-xs text-accent uppercase mb-1">Portfolio</h3>
                      <p className="text-zinc-300">{briefing.portfolio_update}</p>
                    </div>
                  )}
                  {briefing.tomorrow_focus && (
                    <div>
                      <h3 className="text-xs text-accent uppercase mb-1">Tomorrow&apos;s Focus</h3>
                      <p className="text-zinc-300">{briefing.tomorrow_focus}</p>
                    </div>
                  )}
                </>
              )}
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
      <div className="text-2xl font-bold text-accent">{value}</div>
      <div className="text-xs text-zinc-400 mt-1">{label}</div>
    </div>
  );
}

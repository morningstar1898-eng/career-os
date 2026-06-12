"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { fetchAPI } from "../lib/api";

interface Metric {
  date: string;
  jobs_applied: number;
  skills_gap_count: number;
  interview_score: number;
  portfolio_items: number;
}

export function AnalyticsCharts() {
  const [metrics, setMetrics] = useState<Metric[]>([]);

  useEffect(() => {
    fetchAPI<Metric[]>("/analytics/metrics?days=30").then((data) => {
      setMetrics(data.reverse());
    }).catch(() => {});
  }, []);

  if (metrics.length === 0) {
    return <p className="text-zinc-500 text-sm">No data yet. Run the agents to start collecting metrics.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xs text-zinc-400 mb-2 uppercase">Jobs Applied</h3>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={metrics}>
            <XAxis dataKey="date" hide />
            <YAxis hide />
            <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 8 }} />
            <Line type="monotone" dataKey="jobs_applied" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div>
        <h3 className="text-xs text-zinc-400 mb-2 uppercase">Interview Score</h3>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={metrics}>
            <XAxis dataKey="date" hide />
            <YAxis hide domain={[0, 10]} />
            <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 8 }} />
            <Line type="monotone" dataKey="interview_score" stroke="#22c55e" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

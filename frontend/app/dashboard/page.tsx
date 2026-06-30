"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchAPI } from "../../lib/api";
import { speak, stopSpeaking } from "../../lib/voice";
import { AnalyticsCharts } from "../../components/AnalyticsCharts";
import Link from "next/link";

interface Activity {
  type: string;
  status: string;
  description: string;
  timestamp: string;
}

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

interface ParsedSection {
  title: string;
  icon: string;
  content: string;
}

/* ------------------------------------------------------------------ */
/*  Smart parser: splits raw CrewAI output into titled sections        */
/* ------------------------------------------------------------------ */
function parseBriefingOutput(raw: string): ParsedSection[] {
  const sections: ParsedSection[] = [];

  const iconMap: Record<string, string> = {
    job: "briefcase", career: "briefcase", application: "briefcase", applied: "briefcase",
    market: "chart", signal: "chart", trend: "chart",
    skill: "graduation", learning: "graduation", lesson: "graduation", training: "graduation",
    portfolio: "folder", project: "folder",
    interview: "mic", practice: "mic",
    focus: "target", tomorrow: "target", action: "target",
    recommendation: "lightbulb", insight: "lightbulb",
    summary: "document", overview: "document",
    network: "people", connection: "people",
  };

  function pickIcon(title: string): string {
    const lower = title.toLowerCase();
    for (const [keyword, icon] of Object.entries(iconMap)) {
      if (lower.includes(keyword)) return icon;
    }
    return "document";
  }

  // Strategy 1: CrewAI agent markers like "## Agent Name" or "**Agent Name**"
  const agentPattern = /(?:^|\n)(?:#{1,3}\s+|[*]{2})(.+?)(?:[*]{2})?[ \t]*\n/g;
  // Strategy 2: Section headers like "SECTION:" or "Section:\n"
  const headerPattern = /(?:^|\n)(?:[-=]{3,}\s*)?([A-Z][A-Za-z &/,'-]{2,60})(?:\s*[-=]{3,})?:\s*\n/g;
  // Strategy 3: Numbered sections like "1. Section Title"
  const numberedPattern = /(?:^|\n)(\d+)[.)]\s+([A-Z][A-Za-z &/,'-]{2,60})\s*\n/g;

  type SplitResult = { title: string; start: number; headerEnd: number }[];

  function extractSplits(pattern: RegExp, text: string, titleGroup: number): SplitResult {
    const results: SplitResult = [];
    let match;
    const re = new RegExp(pattern.source, pattern.flags);
    while ((match = re.exec(text)) !== null) {
      results.push({
        title: match[titleGroup].replace(/[*#_]/g, "").trim(),
        start: match.index,
        headerEnd: match.index + match[0].length,
      });
    }
    return results;
  }

  const strategies = [
    extractSplits(agentPattern, raw, 1),
    extractSplits(headerPattern, raw, 1),
    extractSplits(numberedPattern, raw, 2),
  ];

  const best = strategies.reduce((a, b) => (b.length > a.length ? b : a), [] as SplitResult);

  if (best.length >= 2) {
    for (let i = 0; i < best.length; i++) {
      const contentStart = best[i].headerEnd;
      const contentEnd = i + 1 < best.length ? best[i + 1].start : raw.length;
      const content = raw.slice(contentStart, contentEnd).trim();
      if (content) {
        sections.push({ title: best[i].title, icon: pickIcon(best[i].title), content });
      }
    }
  }

  // Fallback: split by double-newline paragraphs
  if (sections.length === 0) {
    const paragraphs = raw.split(/\n{2,}/).map((p) => p.trim()).filter((p) => p.length > 30);

    if (paragraphs.length <= 1) {
      sections.push({ title: "Briefing", icon: "document", content: raw.trim() });
    } else {
      const fallbackTitles = ["Overview", "Job Market", "Skills & Learning", "Portfolio", "Action Items", "Additional Notes"];
      paragraphs.forEach((p, i) => {
        const firstLine = p.split("\n")[0];
        let title = fallbackTitles[i] || `Section ${i + 1}`;
        let content = p;
        if (firstLine.length < 60 && firstLine.length > 3) {
          title = firstLine.replace(/^[#*\-_\d.)]+\s*/, "").trim() || title;
          content = p.slice(firstLine.length).trim() || p;
        }
        sections.push({ title, icon: pickIcon(title), content });
      });
    }
  }

  return sections;
}

function generateSummary(sections: ParsedSection[]): string {
  const total = sections.length;
  const topics = sections.map((s) => s.title).slice(0, 3).join(", ");
  const extra = total > 3 ? ` and ${total - 3} more` : "";
  return `${total} section${total !== 1 ? "s" : ""}: ${topics}${extra}`;
}

const SECTION_ICONS: Record<string, string> = {
  briefcase: "💼",
  chart: "📈",
  graduation: "🎓",
  folder: "📂",
  mic: "🎤",
  target: "🎯",
  lightbulb: "💡",
  document: "📄",
  people: "🤝",
};

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [briefing, setBriefing] = useState<any>(null);
  const [briefingDate, setBriefingDate] = useState("");
  const [activities, setActivities] = useState<Activity[]>([]);
  const [error, setError] = useState("");
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    fetchAPI<Summary>("/analytics/summary").then(setSummary).catch(() => {});
    fetchAPI<Briefing>("/briefings/today")
      .then((b) => {
        setBriefingDate(b.date);
        setBriefing(JSON.parse(b.content_json));
      })
      .catch(() => setError("No briefing today yet. Run agents or seed demo data."));
    fetchAPI<Activity[]>("/activity/recent").then(setActivities).catch(() => {});
  }, []);

  const parsedSections = useMemo(() => {
    if (!briefing?.raw_output) return null;
    return parseBriefingOutput(briefing.raw_output);
  }, [briefing]);

  const briefingSummary = useMemo(() => {
    if (!parsedSections) return "";
    return generateSummary(parsedSections);
  }, [parsedSections]);

  function readBriefing() {
    if (!briefing) return;
    if (speaking) { stopSpeaking(); setSpeaking(false); return; }
    setSpeaking(true);
    const text = briefing.raw_output ||
      `Today's market signals: ${briefing.market_signal?.join(", ")}. ${briefing.lesson_summary || ""}. ${briefing.portfolio_update || ""}. ${briefing.tomorrow_focus || ""}`;
    speak(text, () => setSpeaking(false));
  }

  function formatDate(dateStr: string): string {
    try {
      const d = new Date(dateStr + "T00:00:00");
      return d.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
    } catch {
      return dateStr;
    }
  }

  return (
    <main className="min-h-screen p-4 sm:p-6 max-w-6xl mx-auto">
      <nav className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold">Career OS <span className="text-accent">Dashboard</span></h1>
        <div className="flex gap-3 sm:gap-4 text-sm">
          <Link href="/" className="text-zinc-400 hover:text-white">Home</Link>
          <Link href="/pipeline" className="text-zinc-400 hover:text-white">Pipeline</Link>
          <Link href="/interview" className="text-zinc-400 hover:text-white">Interview</Link>
          <Link href="/agents" className="text-zinc-400 hover:text-white">Agents</Link>
          <button onClick={() => { localStorage.removeItem("career_os_token"); window.location.href = "/"; }} className="text-zinc-500 hover:text-white text-xs">Logout</button>
        </div>
      </nav>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
          <StatCard label="Jobs Applied" value={summary.total_jobs_applied} />
          <StatCard label="Successful Runs" value={summary.total_successful_runs} />
          <StatCard label="Avg Interview Score" value={`${summary.avg_interview_score}/10`} />
          <StatCard label="Days Active" value={summary.days_active} />
        </div>
      )}

      {/* Briefing header with date and Read Aloud */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
        <div>
          <h2 className="text-lg sm:text-xl font-semibold">Today&apos;s Briefing</h2>
          {briefingDate && (
            <p className="text-xs text-zinc-500 mt-0.5">{formatDate(briefingDate)}</p>
          )}
        </div>
        {briefing && (
          <button
            onClick={readBriefing}
            className="flex items-center gap-2 text-xs px-4 py-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 border border-zinc-700/50 transition-colors"
          >
            <span>{speaking ? "⏹" : "🔊"}</span>
            {speaking ? "Stop" : "Read Aloud"}
          </button>
        )}
      </div>

      {/* Summary line */}
      {briefingSummary && (
        <p className="text-xs text-zinc-400 mb-4">{briefingSummary}</p>
      )}

      {error ? (
        <div className="glass-card p-6 text-center">
          <p className="text-zinc-500 text-sm">{error}</p>
        </div>
      ) : briefing ? (
        <>
          {/* Parsed sections from raw_output */}
          {parsedSections ? (
            <div className="grid sm:grid-cols-2 gap-4 sm:gap-5 mb-6">
              {parsedSections.map((section, i) => (
                <div key={i} className="glass-card p-4 sm:p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{SECTION_ICONS[section.icon] || "📄"}</span>
                    <h3 className="text-sm font-semibold text-accent uppercase tracking-wide">{section.title}</h3>
                  </div>
                  <div className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
                    {section.content}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Structured fields (non-raw_output briefings) */
            <div className="grid sm:grid-cols-2 gap-4 sm:gap-5 mb-6">
              {briefing.market_signal && (
                <div className="glass-card p-4 sm:p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{SECTION_ICONS.chart}</span>
                    <h3 className="text-sm font-semibold text-accent uppercase tracking-wide">Market Signals</h3>
                  </div>
                  <ul className="text-sm text-zinc-300 space-y-1">
                    {briefing.market_signal.map((s: string, i: number) => <li key={i}>- {s}</li>)}
                  </ul>
                </div>
              )}
              {briefing.lesson_summary && (
                <div className="glass-card p-4 sm:p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{SECTION_ICONS.graduation}</span>
                    <h3 className="text-sm font-semibold text-accent uppercase tracking-wide">Today&apos;s Lesson</h3>
                  </div>
                  <p className="text-sm text-zinc-300">{briefing.lesson_summary}</p>
                </div>
              )}
              {briefing.jobs_applied && (
                <div className="glass-card p-4 sm:p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{SECTION_ICONS.briefcase}</span>
                    <h3 className="text-sm font-semibold text-accent uppercase tracking-wide">Jobs Applied</h3>
                  </div>
                  <div className="space-y-1">
                    {briefing.jobs_applied.map((j: any, i: number) => (
                      <div key={i} className="flex justify-between text-sm text-zinc-300">
                        <span>{j.company} -- {j.role}</span>
                        <span className="text-success text-xs">{j.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {briefing.portfolio_update && (
                <div className="glass-card p-4 sm:p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{SECTION_ICONS.folder}</span>
                    <h3 className="text-sm font-semibold text-accent uppercase tracking-wide">Portfolio</h3>
                  </div>
                  <p className="text-sm text-zinc-300">{briefing.portfolio_update}</p>
                </div>
              )}
              {briefing.tomorrow_focus && (
                <div className="glass-card p-4 sm:p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{SECTION_ICONS.target}</span>
                    <h3 className="text-sm font-semibold text-accent uppercase tracking-wide">Tomorrow&apos;s Focus</h3>
                  </div>
                  <p className="text-sm text-zinc-300">{briefing.tomorrow_focus}</p>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="glass-card p-6 text-center">
          <p className="text-zinc-500 text-sm">Loading...</p>
        </div>
      )}

      {/* Analytics chart */}
      <div className="glass-card p-4 sm:p-6">
        <h2 className="text-lg font-semibold mb-4">Progress Over Time</h2>
        <AnalyticsCharts />
      </div>

      {/* Activity feed */}
      {activities.length > 0 && (
        <div className="glass-card p-4 sm:p-6 mt-4 sm:mt-6">
          <h2 className="text-lg font-semibold mb-4">Activity</h2>
          <div className="space-y-3">
            {activities.map((a, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className={`mt-1.5 h-2.5 w-2.5 rounded-full shrink-0 ${
                  a.status === "success" ? "bg-emerald-400" :
                  a.status === "interview" ? "bg-amber-400" :
                  "bg-red-400"
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-300">{a.description}</p>
                  <p className="text-xs text-zinc-500">{relativeTime(a.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}

function relativeTime(ts: string): string {
  if (!ts) return "";
  const now = Date.now();
  const then = new Date(ts.endsWith("Z") ? ts : ts + "Z").getTime();
  const diff = Math.max(0, now - then);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs === 1 ? "" : "s"} ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="glass-card p-3 sm:p-4 text-center">
      <div className="text-lg sm:text-2xl font-bold text-accent">{value}</div>
      <div className="text-xs text-zinc-400 mt-1">{label}</div>
    </div>
  );
}

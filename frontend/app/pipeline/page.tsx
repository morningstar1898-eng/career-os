"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "../../lib/api";
import Link from "next/link";

type Status = "Applied" | "Phone Screen" | "Interview" | "Offer" | "Rejected" | "Ghosted" | "Withdrawn";

interface Application {
  id: number;
  date_applied: string;
  company: string;
  role: string;
  url?: string;
  status: Status;
  notes?: string;
  blob_url?: string;
  days_since_applied?: number;
}

const COLUMNS: Status[] = ["Applied", "Phone Screen", "Interview", "Offer", "Rejected"];
const GHOST_COLS: Status[] = ["Ghosted", "Withdrawn"];

const COL_STYLES: Record<Status, { border: string; badge: string; dot: string }> = {
  Applied:      { border: "border-zinc-600",   badge: "bg-zinc-700 text-zinc-300",        dot: "bg-zinc-400"   },
  "Phone Screen": { border: "border-blue-500/60", badge: "bg-blue-900/60 text-blue-300", dot: "bg-blue-400"   },
  Interview:    { border: "border-amber-500/60", badge: "bg-amber-900/60 text-amber-300", dot: "bg-amber-400" },
  Offer:        { border: "border-emerald-500/60", badge: "bg-emerald-900/60 text-emerald-300", dot: "bg-emerald-400" },
  Rejected:     { border: "border-red-700/50",  badge: "bg-red-900/40 text-red-400",       dot: "bg-red-500"    },
  Ghosted:      { border: "border-zinc-700/40", badge: "bg-zinc-800/60 text-zinc-500",     dot: "bg-zinc-600"   },
  Withdrawn:    { border: "border-zinc-700/40", badge: "bg-zinc-800/60 text-zinc-500",     dot: "bg-zinc-600"   },
};

const ALL_STATUSES: Status[] = [...COLUMNS, "Ghosted", "Withdrawn"];

export default function PipelinePage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<number | null>(null);
  const [showGhosted, setShowGhosted] = useState(false);
  const [selected, setSelected] = useState<Application | null>(null);

  useEffect(() => {
    loadApps();
  }, []);

  async function loadApps() {
    try {
      const data = await fetchAPI<Application[]>("/pipeline/");
      setApps(data);
    } catch {
      setApps([]);
    } finally {
      setLoading(false);
    }
  }

  async function changeStatus(app: Application, newStatus: Status) {
    if (newStatus === app.status) return;
    setUpdating(app.id);
    try {
      await fetchAPI(`/pipeline/${app.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      setApps((prev) => prev.map((a) => a.id === app.id ? { ...a, status: newStatus } : a));
      if (selected?.id === app.id) setSelected({ ...selected, status: newStatus });
    } catch {
      alert("Failed to update status.");
    } finally {
      setUpdating(null);
    }
  }

  const byStatus = (col: Status) => apps.filter((a) => a.status === col);

  const urgentFollowups = apps.filter(
    (a) => a.status === "Applied" && (a.days_since_applied ?? 0) >= 7
  );

  function daysColor(days: number): string {
    if (days >= 14) return "text-red-400";
    if (days >= 7) return "text-amber-400";
    return "text-zinc-500";
  }

  if (loading) {
    return (
      <main className="min-h-screen p-6 max-w-7xl mx-auto">
        <p className="text-zinc-500 text-sm">Loading pipeline…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Nav */}
      <nav className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6">
        <h1 className="text-xl sm:text-2xl font-bold">Application <span className="text-accent">Pipeline</span></h1>
        <div className="flex gap-3 sm:gap-4 text-sm">
          <Link href="/" className="text-zinc-400 hover:text-white">Home</Link>
          <Link href="/dashboard" className="text-zinc-400 hover:text-white">Dashboard</Link>
          <Link href="/interview" className="text-zinc-400 hover:text-white">Interview</Link>
          <Link href="/agents" className="text-zinc-400 hover:text-white">Agents</Link>
        </div>
      </nav>

      {/* Follow-up alert banner */}
      {urgentFollowups.length > 0 && (
        <div className="mb-5 p-3 rounded-lg bg-amber-900/30 border border-amber-500/40 flex items-start gap-3">
          <span className="text-amber-400 text-lg shrink-0">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-amber-300">
              {urgentFollowups.length} application{urgentFollowups.length > 1 ? "s" : ""} need follow-up
            </p>
            <p className="text-xs text-amber-400/80 mt-0.5">
              {urgentFollowups.map((a) => `${a.company} (${a.days_since_applied}d)`).join(" · ")}
            </p>
          </div>
        </div>
      )}

      {/* Summary row */}
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 sm:gap-3 mb-6">
        {COLUMNS.map((col) => {
          const count = byStatus(col).length;
          const s = COL_STYLES[col];
          return (
            <div key={col} className={`glass-card p-3 text-center border ${s.border}`}>
              <div className={`text-xs font-medium mb-1 ${s.badge.split(" ")[1]}`}>{col}</div>
              <div className="text-xl font-bold text-white">{count}</div>
            </div>
          );
        })}
      </div>

      {/* Kanban board */}
      {apps.length === 0 ? (
        <div className="glass-card p-8 text-center">
          <p className="text-zinc-500 text-sm">No applications tracked yet.</p>
          <p className="text-zinc-600 text-xs mt-2">The pipeline populates automatically after each daily run.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4 mb-6">
          {COLUMNS.map((col) => {
            const colApps = byStatus(col);
            const s = COL_STYLES[col];
            return (
              <div key={col} className={`glass-card p-3 border-t-2 ${s.border.replace("border-", "border-t-")}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`h-2 w-2 rounded-full ${s.dot}`} />
                  <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">{col}</h3>
                  <span className="ml-auto text-xs text-zinc-500">{colApps.length}</span>
                </div>
                <div className="space-y-2 min-h-[60px]">
                  {colApps.map((app) => (
                    <AppCard
                      key={app.id}
                      app={app}
                      updating={updating === app.id}
                      onChangeStatus={(s) => changeStatus(app, s)}
                      onClick={() => setSelected(app)}
                      daysColor={daysColor}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Ghosted / Withdrawn toggle */}
      {(byStatus("Ghosted").length > 0 || byStatus("Withdrawn").length > 0) && (
        <div className="mt-2">
          <button
            onClick={() => setShowGhosted((v) => !v)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors mb-3"
          >
            {showGhosted ? "▼" : "▶"} {byStatus("Ghosted").length + byStatus("Withdrawn").length} archived (Ghosted/Withdrawn)
          </button>
          {showGhosted && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {GHOST_COLS.map((col) => {
                const colApps = byStatus(col);
                if (!colApps.length) return null;
                const s = COL_STYLES[col];
                return (
                  <div key={col} className="glass-card p-3 opacity-60">
                    <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2">{col}</h3>
                    <div className="space-y-2">
                      {colApps.map((app) => (
                        <AppCard
                          key={app.id}
                          app={app}
                          updating={updating === app.id}
                          onChangeStatus={(s) => changeStatus(app, s)}
                          onClick={() => setSelected(app)}
                          daysColor={daysColor}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Detail drawer */}
      {selected && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-end sm:items-center justify-center p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="glass-card p-5 w-full max-w-md rounded-2xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-base font-bold text-white">{selected.company}</h2>
                <p className="text-sm text-zinc-400">{selected.role}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-zinc-500 hover:text-white text-xl leading-none">✕</button>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400">
              <span>Applied: <span className="text-zinc-300">{selected.date_applied}</span></span>
              <span>Days: <span className={daysColor(selected.days_since_applied ?? 0)}>{selected.days_since_applied ?? "—"}d</span></span>
              {selected.url && (
                <span className="col-span-2 truncate">
                  <a href={selected.url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline truncate">{selected.url}</a>
                </span>
              )}
            </div>

            {selected.notes && (
              <p className="text-xs text-zinc-400 bg-zinc-800/50 rounded-lg p-2">{selected.notes}</p>
            )}

            {selected.blob_url && (
              <p className="text-xs">
                <span className="text-zinc-500">Materials: </span>
                <a href={selected.blob_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">View in Azure</a>
              </p>
            )}

            <div>
              <p className="text-xs text-zinc-500 mb-2">Change status:</p>
              <div className="flex flex-wrap gap-2">
                {ALL_STATUSES.map((s) => {
                  const style = COL_STYLES[s];
                  return (
                    <button
                      key={s}
                      disabled={s === selected.status || updating === selected.id}
                      onClick={() => changeStatus(selected, s)}
                      className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                        s === selected.status
                          ? `${style.badge} border-transparent opacity-80 cursor-default`
                          : "border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
                      }`}
                    >
                      {s === selected.status ? `✓ ${s}` : s}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function AppCard({
  app,
  updating,
  onChangeStatus,
  onClick,
  daysColor,
}: {
  app: Application;
  updating: boolean;
  onChangeStatus: (s: Status) => void;
  onClick: () => void;
  daysColor: (d: number) => string;
}) {
  const days = app.days_since_applied ?? 0;
  const needsFollowup = app.status === "Applied" && days >= 7;

  return (
    <div
      onClick={onClick}
      className={`group p-2.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-700/60 cursor-pointer transition-colors border ${
        needsFollowup ? "border-amber-500/40" : "border-zinc-700/30"
      } ${updating ? "opacity-50 pointer-events-none" : ""}`}
    >
      <div className="flex justify-between items-start gap-1">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-zinc-200 truncate">{app.company}</p>
          <p className="text-xs text-zinc-500 truncate mt-0.5">{app.role}</p>
        </div>
        <span className={`text-xs shrink-0 ${daysColor(days)}`}>{days}d</span>
      </div>
      {needsFollowup && (
        <p className="text-xs text-amber-400 mt-1.5">⚠ Follow up</p>
      )}
    </div>
  );
}

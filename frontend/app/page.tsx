"use client";

import Link from "next/link";
import { useState } from "react";
import { fetchAPI } from "../lib/api";

const AGENTS = [
  { label: "Skills Scout", desc: "Scans 100+ job postings for skill trends", icon: "🔍" },
  { label: "Data Analyst", desc: "Builds portfolio projects from real datasets", icon: "📊" },
  { label: "Tutor", desc: "Teaches the #1 missing skill each day", icon: "📚" },
  { label: "Job Applicant", desc: "Tailors resumes and cover letters", icon: "📝" },
  { label: "Interview Coach", desc: "Generates personalized Q&A prep", icon: "🎤" },
  { label: "Orchestrator", desc: "Compiles everything into a daily briefing", icon: "🧠" },
];

const TECH_STACK = [
  "Next.js 14", "TypeScript", "Tailwind CSS", "FastAPI", "Python",
  "CrewAI", "Claude AI", "SQLite", "Recharts", "Web Speech API",
  "Azure Blob Storage", "GitHub Actions", "Vercel",
];

export default function Home() {
  const [seeding, setSeeding] = useState(false);
  const [seeded, setSeeded] = useState(false);

  async function seedDemo() {
    setSeeding(true);
    try {
      await fetchAPI("/demo/seed", { method: "POST" });
      setSeeded(true);
    } catch {
      alert("Start the backend API first (uvicorn api.main:app)");
    }
    setSeeding(false);
  }

  return (
    <main className="min-h-screen">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center min-h-screen px-6 text-center">
        <div className="max-w-3xl">
          <div className="mb-6 inline-flex items-center gap-2 px-4 py-2 rounded-full border border-card-border text-sm text-zinc-400">
            <span className="w-2 h-2 rounded-full bg-success pulse-dot" />
            6 AI Agents Running Daily
          </div>

          <h1 className="text-3xl sm:text-5xl md:text-7xl font-bold tracking-tight mb-6">
            Career <span className="text-accent">OS</span>
          </h1>

          <p className="text-base sm:text-xl text-zinc-400 mb-8 leading-relaxed max-w-2xl mx-auto">
            An autonomous AI system that searches jobs, builds portfolio projects,
            teaches in-demand skills, preps for interviews, and delivers a daily briefing.
            Zero manual effort.
          </p>

          <div className="flex gap-4 justify-center flex-wrap">
            <Link href="/dashboard" className="px-6 py-3 bg-accent text-white rounded-lg font-medium hover:opacity-90 transition glow">
              Open Dashboard
            </Link>
            <Link href="/interview" className="px-6 py-3 border border-card-border rounded-lg font-medium hover:border-accent transition">
              Practice Interview
            </Link>
            <Link href="/projects" className="px-6 py-3 border border-card-border rounded-lg font-medium hover:border-accent transition">
              Projects
            </Link>
            <Link href="/resume" className="px-6 py-3 border border-card-border rounded-lg font-medium hover:border-accent transition">
              Resume
            </Link>
            <button onClick={seedDemo} disabled={seeding || seeded}
              className="px-6 py-3 border border-card-border rounded-lg font-medium text-zinc-400 hover:border-accent transition disabled:opacity-50">
              {seeded ? "Demo Loaded" : seeding ? "Loading..." : "Load Demo Data"}
            </button>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-6 py-20 max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-4">How It Works</h2>
        <p className="text-zinc-400 text-center mb-12 max-w-xl mx-auto">
          Every weekday at 7am, six AI agents wake up and handle the entire job search pipeline autonomously.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
          {AGENTS.map((agent, i) => (
            <div key={agent.label} className="glass-card p-3 sm:p-5 hover:border-accent/50 transition group">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{agent.icon}</span>
                <span className="text-xs text-zinc-500 font-mono">Agent {i + 1}</span>
              </div>
              <h3 className="font-semibold text-sm text-accent group-hover:text-white transition">{agent.label}</h3>
              <p className="text-xs text-zinc-400 mt-1">{agent.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture */}
      <section className="px-6 py-20 max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">Architecture</h2>
        <div className="glass-card p-3 sm:p-8 font-mono text-[10px] sm:text-xs text-zinc-400 leading-relaxed">
          <pre className="overflow-x-auto">{`
  GitHub Actions (cron 7am CT)
         │
         ▼
  ┌──────────────────────────────────────┐
  │  FastAPI Backend (Python)            │
  │  ┌────────┐ ┌────────┐ ┌──────────┐ │
  │  │ CrewAI │→│ Claude  │→│ SQLite   │ │
  │  │6 agents│ │Haiku 4.5│ │ results  │ │
  │  └────────┘ └────────┘ └──────────┘ │
  │       │          │           │       │
  │  Notion    Google Sheets   Azure     │
  └──────────────┬───────────────────────┘
                 │ REST + WebSocket
  ┌──────────────▼───────────────────────┐
  │  Next.js Dashboard (Vercel)          │
  │  ┌──────┐ ┌─────────┐ ┌───────────┐ │
  │  │Briefing│ │Interview│ │Agent      │ │
  │  │+Charts│ │Practice │ │Monitor    │ │
  │  └──────┘ └─────────┘ └───────────┘ │
  │       Voice: Web Speech API          │
  └──────────────────────────────────────┘
          `}</pre>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="px-6 py-20 max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">Tech Stack</h2>
        <div className="flex flex-wrap gap-3 justify-center">
          {TECH_STACK.map((tech) => (
            <span key={tech} className="px-4 py-2 glass-card text-sm text-zinc-300 hover:text-accent transition">
              {tech}
            </span>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 text-center border-t border-card-border">
        <p className="text-zinc-400">
          Built by <span className="text-white font-medium">Meagan Parsons</span>
        </p>
        <p className="text-zinc-500 text-sm mt-2">
          MBA in Finance & Data Analytics &middot; 5+ years healthcare data at Optum/UHG
        </p>
        <div className="mt-4 flex gap-4 justify-center text-sm">
          <a href="https://github.com/morningstar1898-eng/career-os" target="_blank" rel="noopener noreferrer" className="text-accent hover:text-white transition">
            GitHub
          </a>
          <a href="https://public.tableau.com/app/profile/meagan.parsons" target="_blank" rel="noopener noreferrer" className="text-accent hover:text-white transition">
            Tableau Public
          </a>
          <a href="https://www.linkedin.com/in/meagan-parsons-37321a177/" target="_blank" rel="noopener noreferrer" className="text-accent hover:text-white transition">
            LinkedIn
          </a>
          <a href="https://www.kaggle.com/meaganparsons" target="_blank" rel="noopener noreferrer" className="text-accent hover:text-white transition">
            Kaggle
          </a>
        </div>
      </footer>
    </main>
  );
}

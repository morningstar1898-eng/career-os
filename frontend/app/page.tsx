import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="text-center max-w-3xl">
        <div className="mb-6 inline-flex items-center gap-2 px-4 py-2 rounded-full border border-card-border text-sm text-zinc-400">
          <span className="w-2 h-2 rounded-full bg-success pulse-dot" />
          6 AI Agents Running Daily
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          Career <span className="text-accent">OS</span>
        </h1>

        <p className="text-xl text-zinc-400 mb-8 leading-relaxed">
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
        </div>

        <div className="mt-16 grid grid-cols-2 md:grid-cols-3 gap-4 text-left">
          {[
            { label: "Skills Scout", desc: "Scans 100+ job postings for skill trends" },
            { label: "Data Analyst", desc: "Builds portfolio projects from real datasets" },
            { label: "Tutor", desc: "Teaches the #1 missing skill each day" },
            { label: "Job Applicant", desc: "Tailors resumes and cover letters" },
            { label: "Interview Coach", desc: "Generates personalized Q&A prep" },
            { label: "Orchestrator", desc: "Compiles everything into a daily briefing" },
          ].map((agent) => (
            <div key={agent.label} className="glass-card p-4">
              <h3 className="font-semibold text-sm text-accent">{agent.label}</h3>
              <p className="text-xs text-zinc-400 mt-1">{agent.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-16 text-sm text-zinc-500">
          Built by <span className="text-zinc-300">Meagan Parsons</span> &mdash;
          Next.js &middot; FastAPI &middot; CrewAI &middot; Claude AI &middot; Azure
        </div>
      </div>
    </main>
  );
}

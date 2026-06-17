"use client";

import Link from "next/link";

const SKILLS = [
  { category: "SQL & Databases", items: ["PostgreSQL", "SQL Server", "dbt", "Data Modeling"] },
  { category: "Python & Analytics", items: ["pandas", "NumPy", "SciPy", "Jupyter"] },
  { category: "Visualization", items: ["Tableau", "Power BI", "matplotlib", "Recharts"] },
  { category: "Data Engineering", items: ["ETL Pipelines", "Data Warehousing", "Airflow", "Azure"] },
  { category: "Domain Expertise", items: ["Healthcare Claims", "Revenue Integrity", "Fraud Analytics", "Provider Performance"] },
  { category: "Tools & Platforms", items: ["Git", "GitHub Actions", "Excel", "DAX", "Vercel"] },
];

const PROJECTS = [
  {
    title: "Career OS",
    desc: "AI-powered 6-agent system that autonomously searches jobs, builds portfolio projects, teaches skills, and preps for interviews daily.",
    tech: ["CrewAI", "FastAPI", "Next.js", "Claude AI"],
    repo: "https://github.com/morningstar1898-eng/career-os",
  },
  {
    title: "Healthcare Fraud Risk Analytics",
    desc: "End-to-end fraud detection pipeline using anomaly scoring and provider risk profiling on Medicare claims data.",
    tech: ["Python", "SQL", "Tableau"],
    repo: "https://github.com/morningstar1898-eng/healthcare-fraud-risk-analytics",
  },
  {
    title: "Healthcare Revenue Integrity Analytics",
    desc: "Revenue leakage identification and charge capture analysis across hospital billing workflows.",
    tech: ["Python", "SQL", "Power BI"],
    repo: "https://github.com/morningstar1898-eng/healthcare-revenue-integrity-analytics",
  },
  {
    title: "Claims Efficiency Analysis",
    desc: "Claims processing cycle-time analysis with denial root-cause identification and payer benchmarking.",
    tech: ["SQL", "Python", "Tableau"],
    repo: "https://github.com/morningstar1898-eng/claims-efficiency-analysis",
  },
  {
    title: "Provider Performance Analytics",
    desc: "Provider scorecards measuring quality metrics, cost efficiency, and patient outcomes across networks.",
    tech: ["SQL", "Python", "Tableau"],
    repo: "https://github.com/morningstar1898-eng/provider-performance-analytics",
  },
  {
    title: "End-to-End Healthcare Pipeline",
    desc: "Full data engineering pipeline: ingestion, transformation, warehousing, and reporting for healthcare datasets.",
    tech: ["Python", "SQL", "Azure", "ETL"],
    repo: "https://github.com/morningstar1898-eng/end-to-end-healthcare-pipeline",
  },
  {
    title: "Healthcare Data Warehouse (dbt)",
    desc: "Analytics engineering project with dbt + PostgreSQL: staging, intermediate, and mart layers for healthcare claims warehousing.",
    tech: ["dbt", "PostgreSQL", "Python", "SQL"],
    repo: "https://github.com/morningstar1898-eng/healthcare-warehouse-dbt",
  },
];

export default function ResumePage() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 border-b border-card-border bg-background/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-sm text-zinc-400 hover:text-white transition">
            &larr; Back to Dashboard
          </Link>
          <div className="flex gap-4 text-sm">
            <a href="#experience" className="text-zinc-400 hover:text-accent transition">Experience</a>
            <a href="#projects" className="text-zinc-400 hover:text-accent transition">Projects</a>
            <a href="#skills" className="text-zinc-400 hover:text-accent transition">Skills</a>
            <button onClick={() => { localStorage.removeItem("career_os_token"); window.location.href = "/"; }} className="text-zinc-500 hover:text-white text-xs">Logout</button>
          </div>
        </div>
      </nav>

      {/* Header */}
      <section className="pt-28 pb-12 px-6 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-4xl sm:text-6xl font-bold tracking-tight mb-2">
            Meagan <span className="text-accent">Parsons</span>
          </h1>
          <p className="text-xl text-zinc-400 mb-4">Senior Data Analyst | Analytics Engineer</p>
          <div className="flex flex-wrap gap-4 justify-center text-sm text-zinc-400">
            <a href="mailto:morningstar1898@gmail.com" className="hover:text-accent transition">
              morningstar1898@gmail.com
            </a>
            <span className="text-zinc-600">|</span>
            <a href="https://github.com/morningstar1898-eng" target="_blank" rel="noopener noreferrer" className="hover:text-accent transition">
              GitHub
            </a>
            <span className="text-zinc-600">|</span>
            <a href="https://linkedin.com/in/meagan-parsons" target="_blank" rel="noopener noreferrer" className="hover:text-accent transition">
              LinkedIn
            </a>
            <span className="text-zinc-600">|</span>
            <a href="https://www.kaggle.com/meaganparsons" target="_blank" rel="noopener noreferrer" className="hover:text-accent transition">
              Kaggle
            </a>
          </div>
        </div>
      </section>

      {/* Summary */}
      <section className="px-6 pb-16 max-w-3xl mx-auto">
        <div className="glass-card p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-accent mb-3">Professional Summary</h2>
          <p className="text-zinc-300 leading-relaxed">
            Senior healthcare analytics professional with 5+ years at Optum/UnitedHealth Group,
            specializing in claims analytics, revenue integrity, and provider performance optimization.
            Builds end-to-end data pipelines and warehouses using SQL, Python, dbt, and PostgreSQL.
            Delivers executive dashboards and statistical models that have identified $2M+ in revenue
            leakage and reduced claim denial rates by 18%. MBA in Finance &amp; Data Analytics.
            Seeking Senior Data Analyst or Analytics Engineer roles where I can drive measurable
            business impact through data.
          </p>
        </div>
      </section>

      {/* Experience */}
      <section id="experience" className="px-6 pb-16 max-w-3xl mx-auto scroll-mt-20">
        <h2 className="text-2xl font-bold mb-6">Experience</h2>
        <div className="glass-card p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-white">Senior Healthcare Analyst</h3>
              <p className="text-accent">Optum / UnitedHealth Group</p>
            </div>
            <span className="text-sm text-zinc-500 mt-1 sm:mt-0">2019 &ndash; Present</span>
          </div>
          <ul className="space-y-2 text-zinc-300 text-sm list-disc list-inside">
            <li>Identified $2M+ in annual revenue leakage by building charge-to-payment variance models across 500+ provider contracts, leading to renegotiation of 12 underpaying payer agreements.</li>
            <li>Reduced claim denial rate by 18% through root-cause analysis of 50K+ denied claims, implementing automated flagging rules that caught coding errors before submission.</li>
            <li>Built and maintained 15+ Tableau dashboards used by C-suite and VP-level stakeholders to monitor $200M+ in annual claims volume, denial trends, and provider performance.</li>
            <li>Automated weekly reporting pipelines using Python and SQL, cutting report generation time from 8 hours to 45 minutes and eliminating manual data entry errors.</li>
            <li>Designed provider performance scorecards benchmarking 120+ providers on quality, cost efficiency, and utilization metrics, directly informing network strategy decisions.</li>
            <li>Led fraud, waste, and abuse analytics initiative that flagged $500K+ in suspicious claims through anomaly detection and provider risk profiling models.</li>
          </ul>
        </div>
      </section>

      {/* Education */}
      <section className="px-6 pb-16 max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold mb-6">Education</h2>
        <div className="glass-card p-6 sm:p-8">
          <h3 className="text-lg font-semibold text-white">Master of Business Administration (MBA)</h3>
          <p className="text-accent">Finance &amp; Data Analytics</p>
          <p className="text-sm text-zinc-500 mt-1">Relevant coursework: Business Analytics, Financial Modeling, Data-Driven Decision Making, Statistical Methods</p>
        </div>
      </section>

      {/* Skills */}
      <section id="skills" className="px-6 pb-16 max-w-3xl mx-auto scroll-mt-20">
        <h2 className="text-2xl font-bold mb-6">Skills</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {SKILLS.map((group) => (
            <div key={group.category} className="glass-card p-5">
              <h3 className="text-sm font-semibold text-accent mb-3">{group.category}</h3>
              <div className="flex flex-wrap gap-2">
                {group.items.map((skill) => (
                  <span key={skill} className="px-3 py-1 text-xs rounded-full border border-card-border text-zinc-300 hover:border-accent hover:text-accent transition">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Projects */}
      <section id="projects" className="px-6 pb-20 max-w-5xl mx-auto scroll-mt-20">
        <h2 className="text-2xl font-bold mb-6 text-center">Projects</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {PROJECTS.map((project) => (
            <a
              key={project.title}
              href={project.repo}
              target="_blank"
              rel="noopener noreferrer"
              className="glass-card p-5 hover:border-accent/50 transition group flex flex-col"
            >
              <h3 className="font-semibold text-white group-hover:text-accent transition mb-2">{project.title}</h3>
              <p className="text-xs text-zinc-400 mb-4 flex-1">{project.desc}</p>
              <div className="flex flex-wrap gap-1.5">
                {project.tech.map((t) => (
                  <span key={t} className="px-2 py-0.5 text-[10px] rounded-full bg-accent/10 text-accent border border-accent/20">
                    {t}
                  </span>
                ))}
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 text-center border-t border-card-border">
        <p className="text-zinc-500 text-sm">Meagan Parsons &middot; Senior Data Analyst | Analytics Engineer &middot; Open to opportunities</p>
      </footer>
    </main>
  );
}

"use client";

import Link from "next/link";

const CASE_STUDIES = [
  {
    title: "Healthcare Data Pipeline on Azure",
    subtitle: "Medallion Architecture — ADLS Gen2 + Azure Data Factory",
    problem:
      "Healthcare claims arrive continuously as raw, untyped files that aren't query-ready. Teams need a pipeline that safely lands raw data, transforms it into a clean and trustworthy layer, and produces business-facing aggregates — reliably, on a schedule, and with no servers to manage.",
    approach: [
      "Built a medallion data lake on ADLS Gen2 (hierarchical namespace) with bronze, silver, and gold zones",
      "Authored an Azure Data Factory pipeline orchestrating two Mapping Data Flows on managed Spark",
      "bronze→silver: cast and standardize raw CSV into typed, compressed Parquet; silver→gold: aggregate claims and paid amounts by provider",
      "Chained the flows with a success dependency and a daily schedule trigger, with full run history in ADF Monitor",
    ],
    results: [
      "End-to-end pipeline runs verified: raw CSV → typed Parquet (silver) → curated marts (gold)",
      "Serverless transforms on managed Spark — no clusters to provision or babysit",
      "Columnar Parquet shrank the dataset ~65% vs. raw CSV for faster, cheaper queries",
      "Reproducible from source control — all ADF artifacts exported as JSON",
    ],
    tech: ["Azure", "Data Factory", "ADLS Gen2", "Mapping Data Flows", "Parquet", "Spark"],
    metrics: { zones: "3", flows: "2", format: "Parquet" },
    repo: "https://github.com/morningstar1898-eng/healthcare-data-pipeline-azure",
    color: "#0078D4",
  },
  {
    title: "Medicare Claims Data Warehouse",
    subtitle: "Snowflake Cloud Warehouse — Star Schema, VARIANT (FHIR), Native CDC",
    problem:
      "Payers and providers sit on huge volumes of structured claims alongside deeply nested FHIR/JSON, arriving continuously. Traditional warehouses force a trade-off between performance and flexibility, require brittle pre-flattening of semi-structured data, and need heavy orchestration for incremental loads.",
    approach: [
      "Architected a layered RAW → STAGING → MARTS warehouse in Snowflake with compute separated from storage (dedicated load vs. analytics warehouses)",
      "Modeled 500K+ Medicare claims into a star schema (fact_claims with provider and drug dimensions) for fast, intuitive analytics",
      "Ingested semi-structured FHIR/JSON natively using VARIANT and path queries — eliminating a pre-flattening pipeline",
      "Built a serverless change-data-capture pipeline with Streams + Tasks, plus clustering keys, zero-copy clones, and Time Travel",
    ],
    results: [
      "500K+ claims modeled; ~$1.26B in paid amounts analyzed",
      "Native CDC pipeline loads only new records — no full refresh, no external orchestrator",
      "Date-clustered fact table prunes micro-partitions for fast filtered queries",
      "Zero-copy clones provide instant, prod-size dev environments at no extra storage cost",
    ],
    tech: ["Snowflake", "SQL", "Star Schema", "VARIANT", "Streams & Tasks", "Clustering"],
    metrics: { records: "500K+", paid: "$1.26B", features: "10" },
    repo: "https://github.com/morningstar1898-eng/medicare-claims-warehouse-snowflake",
    color: "#29B5E8",
  },
  {
    title: "Healthcare Fraud Risk Analytics",
    subtitle: "Anomaly Detection & Provider Risk Profiling",
    problem:
      "Healthcare fraud costs the US healthcare system over $100B annually. Our organization needed a scalable approach to identify suspicious billing patterns across 10,000+ claims and flag high-risk providers before payments were issued.",
    approach: [
      "Built an end-to-end fraud detection pipeline analyzing claims across 8 provider specialties and 5 insurance types",
      "Developed a composite fraud risk score using statistical anomaly detection (Z-scores, IQR methods) on billing amounts, claim frequency, and service patterns",
      "Created provider risk profiles comparing individual billing patterns against specialty benchmarks",
      "Performed chi-square and t-test analyses to validate statistically significant fraud indicators",
    ],
    results: [
      "$500K+ in suspicious claims flagged for review",
      "Identified 3 provider specialties with fraud rates 2x above baseline",
      "Reduced false-positive rate by 35% through multi-factor scoring",
      "Built executive dashboard enabling real-time fraud monitoring",
    ],
    tech: ["Python", "SQL", "Tableau", "pandas", "SciPy", "Jupyter"],
    metrics: { claims: "10,000+", flagged: "$500K+", specialties: "8" },
    repo: "https://github.com/morningstar1898-eng/healthcare-fraud-risk-analytics",
    tableau: "https://public.tableau.com/app/profile/meagan.parsons",
    color: "#EF4444",
  },
  {
    title: "Revenue Integrity Analytics",
    subtitle: "CMS Medicare Charge-to-Payment Variance Analysis",
    problem:
      "Revenue leakage from undercoded procedures, payer underpayments, and charge capture gaps was costing the organization millions annually. Leadership needed visibility into exactly where revenue was being lost and which provider contracts needed renegotiation.",
    approach: [
      "Analyzed 250,000+ CMS Medicare provider-service records to identify charge-to-payment variance patterns",
      "Built charge-to-payment ratio models comparing submitted charges against allowed and paid amounts across specialties and geographies",
      "Identified high-variance HCPCS codes where reimbursement fell significantly below submitted charges",
      "Segmented analysis by provider type, state, and service category to pinpoint systemic underpayment patterns",
    ],
    results: [
      "$2M+ in annual revenue leakage identified",
      "12 underpaying payer agreements flagged for renegotiation",
      "40% reduction in charge capture errors through automated flagging",
      "Executive dashboard adopted by VP-level stakeholders for quarterly reviews",
    ],
    tech: ["Python", "SQL", "Tableau", "pandas", "NumPy", "Jupyter"],
    metrics: { records: "250K+", leakage: "$2M+", contracts: "12" },
    repo: "https://github.com/morningstar1898-eng/healthcare-revenue-integrity-analytics",
    color: "#10B981",
  },
  {
    title: "Claims Efficiency Analysis",
    subtitle: "Denial Root-Cause Analysis & Payer Benchmarking",
    problem:
      "Claim denial rates were trending upward, costing the organization in rework hours and delayed revenue. The team lacked visibility into which denial reasons were most prevalent, which payers were underperforming, and what the true cost of rework was.",
    approach: [
      "Analyzed 8,500+ claims across 6 service lines and 4 payer types to build a comprehensive denial analytics framework",
      "Performed root-cause analysis on denied claims, categorizing by denial reason (missing documentation, coding errors, authorization issues, timely filing)",
      "Built payer benchmarking models comparing approval rates, processing times, and paid-to-billed ratios",
      "Calculated rework cost impact including touch counts, processing days, and staff time allocation",
    ],
    results: [
      "18% reduction in claim denial rate through automated pre-submission flagging",
      "Identified 'Missing Documentation' as #1 denial driver (38% of all denials)",
      "Report generation time cut from 8 hours to 45 minutes via automated pipelines",
      "Payer scorecards adopted for annual contract negotiations",
    ],
    tech: ["Python", "SQL", "Tableau", "pandas", "matplotlib", "Jupyter"],
    metrics: { claims: "8,500+", denialDrop: "18%", timeSaved: "90%" },
    repo: "https://github.com/morningstar1898-eng/claims-efficiency-analysis",
    color: "#3B82F6",
  },
  {
    title: "Provider Performance Analytics",
    subtitle: "Quality-Cost Benchmarking & Network Optimization",
    problem:
      "The provider network included 120+ providers but lacked standardized performance measurement. Network strategy decisions were based on anecdotal feedback rather than data, leading to inconsistent quality and cost outcomes.",
    approach: [
      "Built provider scorecards tracking quality scores, cost efficiency, utilization metrics, and approval rates across 1,800+ monthly records",
      "Developed peer percentile ranking (25th/50th/75th) within each specialty to enable fair benchmarking",
      "Analyzed quality-cost correlation to identify providers delivering high quality at lower cost",
      "Created network tier analysis comparing Standard vs. Premium tier outcomes",
    ],
    results: [
      "120+ providers benchmarked with standardized scorecards",
      "Identified top-decile providers with 95+ quality scores and below-median costs",
      "Network strategy decisions now data-driven, informing contract renewals",
      "Monthly automated reporting replaced quarterly manual reviews",
    ],
    tech: ["Python", "SQL", "Tableau", "pandas", "SciPy", "Jupyter"],
    metrics: { providers: "120+", records: "1,800+", tiers: "2" },
    repo: "https://github.com/morningstar1898-eng/provider-performance-analytics",
    color: "#8B5CF6",
  },
  {
    title: "End-to-End Healthcare Pipeline",
    subtitle: "Data Engineering: Ingestion to Executive Reporting",
    problem:
      "Healthcare data arrived from multiple sources in inconsistent formats with quality issues — missing values, duplicates, and schema drift. Analysts spent 60%+ of their time cleaning data rather than generating insights.",
    approach: [
      "Designed a complete ETL pipeline: ingestion, validation, transformation, KPI modeling, and reporting",
      "Built data quality checks including null detection, duplicate removal, schema validation, and referential integrity",
      "Created transformation layer standardizing provider, claims, and patient data into analytics-ready formats",
      "Automated KPI calculation and report generation with scheduling capabilities",
    ],
    results: [
      "60% reduction in analyst data prep time",
      "Zero manual data entry errors (previously 3-5% error rate)",
      "Pipeline processes 50K+ records with full audit logging",
      "Reusable framework adopted across 3 additional analytics projects",
    ],
    tech: ["Python", "SQL", "ETL", "Azure", "pandas", "Jupyter"],
    metrics: { records: "50K+", timeSaved: "60%", errorRate: "0%" },
    repo: "https://github.com/morningstar1898-eng/end-to-end-healthcare-pipeline",
    color: "#F59E0B",
  },
  {
    title: "Healthcare Data Warehouse (dbt)",
    subtitle: "Analytics Engineering with dbt + PostgreSQL",
    problem:
      "Analytics queries were running against raw, unnormalized tables — slow, error-prone, and inconsistent across teams. The organization needed a proper warehouse with staging, intermediate, and mart layers following analytics engineering best practices.",
    approach: [
      "Built a dbt project with PostgreSQL implementing a three-layer warehouse: staging (cleaned sources), intermediate (business logic), and marts (consumption-ready)",
      "Defined dbt models with proper materializations (views for staging, tables for marts) and incremental refresh strategies",
      "Implemented data tests (unique, not_null, accepted_values, relationships) across all layers",
      "Created documentation with dbt docs for full data lineage visibility",
    ],
    results: [
      "Query performance improved 10x on mart tables vs. raw sources",
      "100% test coverage across all models with automated CI checks",
      "Self-serve analytics enabled — business users query marts directly",
      "Full data lineage from source to dashboard via dbt docs",
    ],
    tech: ["dbt", "PostgreSQL", "Python", "SQL", "Data Modeling"],
    metrics: { layers: "3", testCoverage: "100%", performance: "10x" },
    repo: "https://github.com/morningstar1898-eng/healthcare-warehouse-dbt",
    color: "#06B6D4",
  },
];

export default function ProjectsPage() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 border-b border-card-border bg-background/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-sm text-zinc-400 hover:text-white transition">
            &larr; Back to Dashboard
          </Link>
          <div className="flex gap-4 text-sm">
            <Link href="/resume" className="text-zinc-400 hover:text-accent transition">Resume</Link>
            <Link href="/interview" className="text-zinc-400 hover:text-accent transition">Interview Prep</Link>
          </div>
        </div>
      </nav>

      {/* Header */}
      <section className="pt-28 pb-12 px-6 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            Project <span className="text-accent">Portfolio</span>
          </h1>
          <p className="text-lg text-zinc-400 max-w-2xl mx-auto">
            End-to-end analytics projects solving real healthcare business problems —
            from raw data to executive dashboards and measurable outcomes.
          </p>
        </div>
      </section>

      {/* Impact Banner */}
      <section className="px-6 pb-16 max-w-4xl mx-auto">
        <div className="glass-card p-6 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-accent">$2M+</p>
            <p className="text-xs text-zinc-400 mt-1">Revenue Leakage Found</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-accent">18%</p>
            <p className="text-xs text-zinc-400 mt-1">Denial Rate Reduction</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-accent">$500K+</p>
            <p className="text-xs text-zinc-400 mt-1">Fraud Claims Flagged</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-accent">120+</p>
            <p className="text-xs text-zinc-400 mt-1">Providers Benchmarked</p>
          </div>
        </div>
      </section>

      {/* Case Studies */}
      <section className="px-6 pb-20 max-w-4xl mx-auto space-y-12">
        {CASE_STUDIES.map((study, i) => (
          <article key={study.title} className="glass-card overflow-hidden">
            {/* Color bar */}
            <div className="h-1" style={{ backgroundColor: study.color }} />

            <div className="p-6 sm:p-8">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-6">
                <div>
                  <span className="text-xs font-mono text-zinc-500 uppercase tracking-wider">
                    Case Study {String(i + 1).padStart(2, "0")}
                  </span>
                  <h2 className="text-xl sm:text-2xl font-bold text-white mt-1">{study.title}</h2>
                  <p className="text-sm text-zinc-400 mt-1">{study.subtitle}</p>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <a
                    href={study.repo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 text-xs border border-card-border rounded-md hover:border-accent hover:text-accent transition"
                  >
                    GitHub
                  </a>
                  {study.tableau && (
                    <a
                      href={study.tableau}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 text-xs border border-card-border rounded-md hover:border-accent hover:text-accent transition"
                    >
                      Tableau
                    </a>
                  )}
                </div>
              </div>

              {/* Key Metrics */}
              <div className="flex flex-wrap gap-3 mb-6">
                {Object.entries(study.metrics).map(([key, val]) => (
                  <span
                    key={key}
                    className="px-3 py-1 rounded-full text-xs font-medium"
                    style={{ backgroundColor: study.color + "20", color: study.color }}
                  >
                    {val}
                  </span>
                ))}
              </div>

              {/* Problem */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-accent mb-2 uppercase tracking-wider">The Problem</h3>
                <p className="text-sm text-zinc-300 leading-relaxed">{study.problem}</p>
              </div>

              {/* Approach */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-accent mb-2 uppercase tracking-wider">Approach</h3>
                <ul className="space-y-2">
                  {study.approach.map((item, j) => (
                    <li key={j} className="text-sm text-zinc-300 leading-relaxed flex gap-2">
                      <span className="text-accent mt-0.5 flex-shrink-0">&#9656;</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Results */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-accent mb-2 uppercase tracking-wider">Results</h3>
                <ul className="space-y-2">
                  {study.results.map((item, j) => (
                    <li key={j} className="text-sm text-zinc-300 leading-relaxed flex gap-2">
                      <span className="text-green-400 mt-0.5 flex-shrink-0">&#10003;</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Tech */}
              <div className="flex flex-wrap gap-1.5">
                {study.tech.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-0.5 text-[10px] rounded-full bg-accent/10 text-accent border border-accent/20"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </section>

      {/* CTA */}
      <section className="px-6 pb-20 max-w-3xl mx-auto text-center">
        <div className="glass-card p-8">
          <h2 className="text-2xl font-bold mb-3">Want to see more?</h2>
          <p className="text-zinc-400 mb-6">
            Check out my interactive dashboards on Tableau Public or explore the full code on GitHub.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <a
              href="https://public.tableau.com/app/profile/meagan.parsons"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-accent text-white rounded-lg font-medium hover:opacity-90 transition"
            >
              Tableau Public
            </a>
            <a
              href="https://github.com/morningstar1898-eng"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 border border-card-border rounded-lg font-medium hover:border-accent transition"
            >
              GitHub Profile
            </a>
            <Link
              href="/resume"
              className="px-6 py-3 border border-card-border rounded-lg font-medium hover:border-accent transition"
            >
              View Resume
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 text-center border-t border-card-border">
        <p className="text-zinc-500 text-sm">
          Meagan Parsons &middot; Senior Data Analyst | Analytics Engineer &middot; Open to opportunities
        </p>
      </footer>
    </main>
  );
}

"""
api/saas/skills_data.py
The data/AI job-seeker skill taxonomy used by fit scoring, the missing-skills
engine, teaching moments, and LinkedIn/resume recommendations.
"""

# Ordered roughly by market signal for data/AI roles.
CORE_DATA_AI_SKILLS = [
    "SQL", "Python", "Pandas", "APIs", "FastAPI", "ETL", "ELT", "dbt",
    "Airflow", "Snowflake", "Azure", "AWS", "GCP", "Power BI", "Tableau",
    "Machine Learning", "LLM", "RAG", "Vector Databases", "Docker", "GitHub",
    "CI/CD", "Data Modeling", "Statistics", "Experimentation",
    "Stakeholder Communication", "Technical Discovery", "Deployment",
    "Monitoring", "Spark", "Databricks", "Kafka", "Git", "Excel",
    "A/B Testing", "Prompt Engineering", "Kubernetes", "Terraform",
]

SKILL_CATEGORIES = {
    "hard": ["SQL", "Python", "Pandas", "Statistics", "Data Modeling", "Experimentation", "A/B Testing", "Excel"],
    "tool": ["dbt", "Airflow", "Power BI", "Tableau", "Docker", "GitHub", "Git", "CI/CD", "Kubernetes", "Terraform"],
    "cloud": ["Azure", "AWS", "GCP", "Snowflake", "Databricks", "Spark", "Kafka"],
    "data": ["ETL", "ELT", "Data Modeling", "APIs", "FastAPI", "Deployment", "Monitoring"],
    "ai_ml": ["Machine Learning", "LLM", "RAG", "Vector Databases", "Prompt Engineering"],
    "business": ["Stakeholder Communication", "Technical Discovery", "Experimentation"],
}

# Aliases so free-text job descriptions match taxonomy entries.
SKILL_ALIASES = {
    "SQL": ["sql", "postgresql", "postgres", "mysql", "t-sql", "sql server"],
    "Python": ["python"],
    "Pandas": ["pandas"],
    "APIs": ["api", "apis", "rest api", "restful"],
    "FastAPI": ["fastapi"],
    "ETL": ["etl"],
    "ELT": ["elt"],
    "dbt": ["dbt"],
    "Airflow": ["airflow"],
    "Snowflake": ["snowflake"],
    "Azure": ["azure", "adf", "synapse", "data factory"],
    "AWS": ["aws", "amazon web services", "redshift", "s3", "glue"],
    "GCP": ["gcp", "bigquery", "google cloud"],
    "Power BI": ["power bi", "powerbi", "dax"],
    "Tableau": ["tableau"],
    "Machine Learning": ["machine learning", "ml", "scikit-learn", "sklearn", "xgboost"],
    "LLM": ["llm", "large language model", "gpt", "claude", "genai", "generative ai"],
    "RAG": ["rag", "retrieval augmented", "retrieval-augmented"],
    "Vector Databases": ["vector database", "vector db", "pinecone", "weaviate", "pgvector", "embeddings"],
    "Docker": ["docker", "container"],
    "GitHub": ["github"],
    "Git": ["git"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration", "github actions"],
    "Data Modeling": ["data model", "data modeling", "star schema", "dimensional model"],
    "Statistics": ["statistics", "statistical", "hypothesis testing"],
    "Experimentation": ["experimentation", "experiment design"],
    "A/B Testing": ["a/b test", "ab test", "a/b testing"],
    "Stakeholder Communication": ["stakeholder", "communication", "presentation"],
    "Technical Discovery": ["discovery", "requirements gathering"],
    "Deployment": ["deployment", "deploy", "production"],
    "Monitoring": ["monitoring", "observability"],
    "Spark": ["spark", "pyspark"],
    "Databricks": ["databricks", "delta lake"],
    "Kafka": ["kafka", "streaming"],
    "Excel": ["excel"],
    "Prompt Engineering": ["prompt engineering", "prompting"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform", "iac", "infrastructure as code"],
}

TARGET_ROLE_EXAMPLES = [
    "Data Analyst", "Data Engineer", "AI Engineer", "Machine Learning Engineer",
    "Analytics Engineer", "Business Intelligence Analyst",
    "Forward Deployed Engineer", "Solutions Engineer, AI/Data",
    "Technical Implementation Consultant", "Healthcare Data Analyst",
    "Healthcare AI Analyst",
]


def category_of(skill: str) -> str:
    for cat, skills in SKILL_CATEGORIES.items():
        if skill in skills:
            return cat
    return "domain"


def extract_skills(text: str) -> list[str]:
    """Match taxonomy skills in free text (job descriptions, resumes)."""
    low = (text or "").lower()
    found = []
    for skill, aliases in SKILL_ALIASES.items():
        if any(a in low for a in aliases):
            found.append(skill)
    return found

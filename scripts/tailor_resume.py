#!/usr/bin/env python3
"""
Roy's Resume Tailor — ATS keyword-based (free, no API)
Picks top 5 ATS-scored jobs and tailors resume + cold email for each.
"""

import json, os, re
from datetime import datetime

JOBS_FILE   = "jobs_found.json"
RESUME_FILE = "resume/base_resume.json"
OUTPUT_FILE = "tailored_resumes.json"

# Roy's core resume data
ROY = {
    "name":     "Ravikumar",
    "title":    "Java Full Stack Developer",
    "email":    "rn5127610@gmail.com",
    "phone":    "+91 9686906521",
    "linkedin": "linkedin.com/in/ravikumar2002",
    "github":   "github.com/ravigithubcse",
    "location": "Bengaluru, India",
    "yoe":      "1.5 years",
    "summary":  (
        "Java Full Stack Developer with 1.5 years of experience building "
        "enterprise-grade Spring Boot microservices and Angular frontends at "
        "Trinity Mobility. Proficient in REST APIs, JWT security, Kafka/Redis "
        "real-time pipelines, Docker CI/CD, and Angular 15/17."
    ),
    "skills": {
        "backend":  ["Java 21", "Spring Boot 3.x", "Spring Security", "Spring Cloud",
                     "REST APIs", "Microservices", "JPA/Hibernate", "JWT"],
        "frontend": ["Angular 15/17", "TypeScript", "RxJS", "HTML5", "CSS3", "WebSocket"],
        "data":     ["PostgreSQL", "MS SQL Server", "Redis", "Kafka", "MongoDB"],
        "devops":   ["Docker", "Jenkins", "GitHub Actions", "CI/CD", "Git"],
        "ai":       ["OpenAI GPT-4o", "Model Context Protocol (MCP)", "LangChain"],
        "testing":  ["JUnit", "Mockito", "Swagger", "Postman"],
    },
    "experience": [
        {
            "company":  "Trinity Mobility Pvt. Ltd.",
            "role":     "Associate Software Engineer",
            "period":   "Aug 2025 – May 2026",
            "bullets": [
                "Designed scalable multi-tenant Spring Boot + Angular 15 applications for 40+ enterprise clients",
                "Built Kafka/Redis IoT pipelines processing 100,000+ data points daily",
                "Reduced page load latency by 25%+ via targeted optimisation and caching",
                "Automated CI/CD pipelines using Docker and Jenkins",
                "Implemented JWT-secured REST APIs with Spring Security",
            ]
        }
    ],
    "projects": [
        {
            "name": "AdaptiveFlow AI",
            "tech": "Java, Spring Boot, Angular, OpenAI GPT-4o, WebSocket",
            "desc": "Real-Time Cognitive Process Intelligence Engine with anomaly detection and NLP querying",
        },
        {
            "name": "SkillDNA AI",
            "tech": "Java 21, Spring Boot, Angular, Kafka, Redis, PostgreSQL, Neo4j, Docker",
            "desc": "AI-powered Career Digital Twin — 7 microservices, predicts career trajectories",
        },
        {
            "name": "SupplySense AI",
            "tech": "Java, Spring Boot, Python, FastAPI, PyTorch, Kafka, TimescaleDB",
            "desc": "Predictive supply chain risk platform with LSTM forecasting and RoBERTa NLP",
        },
        {
            "name": "Agri-Twin AI",
            "tech": "Java 21, Spring Boot 3, Angular 19, PostgreSQL, Docker, GitHub Actions",
            "desc": "Farm Commodity Digital Twin for Indian smallholder farmers",
        },
    ],
    "education": "B.E. CSE — Akshaya Institute of Technology (VTU, 2024) — CGPA: 8.96/10",
    "certs": [
        "Java Spring Framework + Spring Boot + Spring AI — Udemy",
        "Databricks Generative AI Fundamentals",
        "Comprehensive Angular 15 Training — Udemy",
    ],
}

# Skill keyword → resume section mapping
SKILL_MAP = {
    "java":           ROY["skills"]["backend"],
    "spring":         ROY["skills"]["backend"],
    "spring boot":    ROY["skills"]["backend"],
    "spring security":ROY["skills"]["backend"],
    "spring cloud":   ROY["skills"]["backend"],
    "microservices":  ROY["skills"]["backend"],
    "rest api":       ROY["skills"]["backend"],
    "restful":        ROY["skills"]["backend"],
    "jpa":            ROY["skills"]["backend"],
    "hibernate":      ROY["skills"]["backend"],
    "angular":        ROY["skills"]["frontend"],
    "typescript":     ROY["skills"]["frontend"],
    "rxjs":           ROY["skills"]["frontend"],
    "html":           ROY["skills"]["frontend"],
    "css":            ROY["skills"]["frontend"],
    "websocket":      ROY["skills"]["frontend"],
    "kafka":          ROY["skills"]["data"],
    "redis":          ROY["skills"]["data"],
    "postgresql":     ROY["skills"]["data"],
    "sql":            ROY["skills"]["data"],
    "docker":         ROY["skills"]["devops"],
    "jenkins":        ROY["skills"]["devops"],
    "ci/cd":          ROY["skills"]["devops"],
    "git":            ROY["skills"]["devops"],
    "github actions": ROY["skills"]["devops"],
    "openai":         ROY["skills"]["ai"],
    "gpt":            ROY["skills"]["ai"],
    "mcp":            ROY["skills"]["ai"],
    "junit":          ROY["skills"]["testing"],
    "mockito":        ROY["skills"]["testing"],
    "swagger":        ROY["skills"]["testing"],
    "postman":        ROY["skills"]["testing"],
    "jwt":            ROY["skills"]["backend"],
    "agile":          ["Agile (JIRA, Scrum, Sprint planning)"],
    "jira":           ["JIRA", "Agile", "Sprint planning"],
}


def extract_jd_skills(job):
    """Extract skills from job title + skills field."""
    combined = f"{job.get('title','')} {job.get('skills','')}".lower()
    matched = []
    for kw, skills in SKILL_MAP.items():
        if kw in combined:
            matched.extend(skills)
    return list(dict.fromkeys(matched))[:10]  # unique, max 10


def cold_email(job, matched_skills):
    company = (job.get("company","") or "").strip()
    if not company or company.lower() in ("n/a","na","confidential company",""):
        company = "your company"
    title   = job.get("title", "Software Developer")
    skills_line = ", ".join(matched_skills[:5]) if matched_skills else "Java, Spring Boot, Angular"
    return {
        "email_subject": f"Application: {title} | Ravikumar | Java Full Stack | 1.5 YOE | Bengaluru",
        "email_body": (
            f"Hi Hiring Team,\n\n"
            f"I am excited to apply for the {title} role at {company}.\n\n"
            f"I am a Java Full Stack Developer with 1.5 years of experience at Trinity Mobility, "
            f"where I built Spring Boot microservices + Angular 15 applications for 40+ enterprise clients, "
            f"managed Kafka/Redis IoT pipelines processing 100,000+ daily data points, and reduced "
            f"page load latency by 25%+ via targeted optimisation.\n\n"
            f"Key skills matching your requirement: {skills_line}.\n\n"
            f"I have also built several AI/full-stack portfolio projects (SkillDNA AI, AdaptiveFlow AI, "
            f"SupplySense AI, Agri-Twin AI) — all open-source on GitHub.\n\n"
            f"I would love to discuss how I can contribute to {company}. "
            f"My resume and GitHub are attached/linked below.\n\n"
            f"Best regards,\n"
            f"Ravikumar\n"
            f"📧 rn5127610@gmail.com | 📞 +91 9686906521\n"
            f"🔗 linkedin.com/in/ravikumar2002 | 💻 github.com/ravigithubcse"
        ),
    }


def build_resume_html(job, matched_skills):
    """Generate a clean HTML resume tailored for this job."""
    company = (job.get("company","") or "Hiring Company").strip()
    if company.lower() in ("n/a","na","confidential company",""):
        company = "Hiring Company"
    title = job.get("title","Software Developer")

    # Highlight matched skills at top
    skill_pills = "".join(
        f'<span style="background:#e8f0fe;color:#1565c0;padding:4px 12px;border-radius:20px;'
        f'font-size:12px;font-weight:700;margin:3px;display:inline-block">{s}</span>'
        for s in matched_skills[:8]
    )

    exp_bullets = "".join(
        f"<li style='margin-bottom:6px;font-size:13px'>{b}</li>"
        for b in ROY["experience"][0]["bullets"]
    )

    projects_html = ""
    for p in ROY["projects"][:3]:
        projects_html += f"""
<div style="margin-bottom:12px">
  <div style="font-weight:700;color:#1a237e;font-size:13px">{p["name"]}</div>
  <div style="font-size:11px;color:#546e7a;margin:2px 0">{p["tech"]}</div>
  <div style="font-size:12px;color:#37474f">{p["desc"]}</div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Ravikumar — Resume for {company}</title></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;max-width:800px;margin:0 auto;
             padding:30px;color:#222;background:#fff">
  <div style="border-bottom:3px solid #1565c0;padding-bottom:16px;margin-bottom:20px">
    <h1 style="margin:0;color:#1565c0;font-size:26px">RAVIKUMAR</h1>
    <div style="color:#546e7a;font-size:14px;margin-top:4px">
      Java Full Stack Developer · 1.5 Years Experience · Bengaluru, India
    </div>
    <div style="font-size:12px;margin-top:6px;color:#37474f">
      📧 rn5127610@gmail.com &nbsp;|&nbsp; 📞 +91 9686906521 &nbsp;|&nbsp;
      🔗 linkedin.com/in/ravikumar2002 &nbsp;|&nbsp; 💻 github.com/ravigithubcse
    </div>
  </div>

  <div style="background:#e8f0fe;border-radius:10px;padding:12px 16px;margin-bottom:18px">
    <div style="font-size:11px;color:#1565c0;font-weight:800;margin-bottom:6px">
      🎯 SKILLS MATCHING: {title} @ {company}
    </div>
    <div>{skill_pills}</div>
  </div>

  <h2 style="color:#1565c0;font-size:15px;border-bottom:1px solid #e0e0e0;
             padding-bottom:4px">PROFESSIONAL SUMMARY</h2>
  <p style="font-size:13px;line-height:1.6;margin-top:8px">{ROY["summary"]}</p>

  <h2 style="color:#1565c0;font-size:15px;border-bottom:1px solid #e0e0e0;
             padding-bottom:4px">EXPERIENCE</h2>
  <div style="margin-top:8px">
    <div style="display:flex;justify-content:space-between">
      <strong style="font-size:14px">{ROY["experience"][0]["company"]}</strong>
      <span style="font-size:12px;color:#546e7a">{ROY["experience"][0]["period"]}</span>
    </div>
    <div style="color:#546e7a;font-size:13px;margin:3px 0">{ROY["experience"][0]["role"]}</div>
    <ul style="margin:8px 0;padding-left:20px">{exp_bullets}</ul>
  </div>

  <h2 style="color:#1565c0;font-size:15px;border-bottom:1px solid #e0e0e0;
             padding-bottom:4px">PROJECTS</h2>
  <div style="margin-top:8px">{projects_html}</div>

  <h2 style="color:#1565c0;font-size:15px;border-bottom:1px solid #e0e0e0;
             padding-bottom:4px">EDUCATION</h2>
  <p style="font-size:13px;margin-top:8px">{ROY["education"]}</p>

  <h2 style="color:#1565c0;font-size:15px;border-bottom:1px solid #e0e0e0;
             padding-bottom:4px">CERTIFICATIONS</h2>
  <ul style="margin-top:8px;padding-left:20px">
    {"".join(f"<li style='font-size:13px;margin-bottom:4px'>{c}</li>" for c in ROY["certs"])}
  </ul>
</body></html>"""


def tailor_all():
    print(f"\n{'='*55}")
    print(f"  RESUME TAILOR — {datetime.now().strftime('%d %b %Y %I:%M %p')}")
    print(f"{'='*55}\n")

    if not os.path.exists(JOBS_FILE):
        print("  ❌ No jobs_found.json found")
        return []

    with open(JOBS_FILE) as f:
        jobs_data = json.load(f)

    all_jobs = jobs_data.get("all_jobs", [])

    # Pick top 5 by ATS score (already sorted)
    top_jobs = all_jobs[:5]
    print(f"  🎯 Tailoring for top {len(top_jobs)} ATS-matched jobs...")

    results = []
    for i, job in enumerate(top_jobs):
        matched = extract_jd_skills(job)
        email   = cold_email(job, matched)
        rhtml   = build_resume_html(job, matched)
        score   = job.get("ats_score", 0)
        print(f"  [{i+1}] {job.get('title','')} @ "
              f"{job.get('company','Confidential')[:25]} — ATS: {score}% — "
              f"{len(matched)} skills matched")
        results.append({
            "job":         job,
            "tailored": {
                "top_skills":    matched,
                "email_subject": email["email_subject"],
                "email_body":    email["email_body"],
            },
            "resume_html": rhtml,
        })

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  ✅ {len(results)} tailored resumes saved to {OUTPUT_FILE}")
    return results

if __name__ == "__main__":
    tailor_all()

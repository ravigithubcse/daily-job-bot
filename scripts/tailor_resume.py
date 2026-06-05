#!/usr/bin/env python3
"""
Resume Tailor — 100% FREE, No API needed
Uses smart keyword matching to tailor resume for each job
"""

import json
import os
from datetime import datetime

BASE_RESUME_PATH = "resume/base_resume.json"
JOBS_FILE        = "jobs_found.json"
OUTPUT_FILE      = "tailored_resumes.json"
MAX_TAILOR       = 5

# ── Keyword → skill mapping ────────────────────────────────────────────────
SKILL_MAP = {
    "java":          "Java 17/18",
    "spring boot":   "Spring Boot 3.x",
    "spring":        "Spring Framework",
    "angular":       "Angular 15/17",
    "typescript":    "TypeScript",
    "javascript":    "JavaScript",
    "microservice":  "Microservices Architecture",
    "rest":          "RESTful APIs",
    "api":           "REST API Development",
    "kafka":         "Apache Kafka (IoT pipeline — 100K+ events/day)",
    "redis":         "Redis Caching",
    "docker":        "Docker & Containerization",
    "jenkins":       "Jenkins CI/CD",
    "git":           "Git & Version Control",
    "postgresql":    "PostgreSQL",
    "mongodb":       "MongoDB",
    "sql":           "SQL & Data Modelling",
    "hibernate":     "Hibernate / JPA",
    "jpa":           "JPA & Hibernate ORM",
    "junit":         "JUnit 5 & Mockito",
    "mockito":       "Mockito Unit Testing",
    "devops":        "DevOps & CI/CD Pipelines",
    "agile":         "Agile / Scrum",
    "swagger":       "Swagger / OpenAPI",
    "postman":       "Postman API Testing",
    "security":      "Spring Security",
    "jwt":           "JWT Authentication",
    "openai":        "OpenAI GPT Integration",
    "mcp":           "Model Context Protocol (MCP)",
    "ai":            "Agentic AI Integration",
    "websocket":     "WebSocket / STOMP",
    "rxjs":          "RxJS",
    "html":          "HTML5 & CSS3",
    "css":           "CSS3 & Responsive UI",
    "multi.tenant":  "Multi-tenant Architecture (40+ clients)",
    "full.stack":    "Full Stack Development (Java + Angular)",
    "backend":       "Backend Development (Java/Spring Boot)",
    "fresher":       "Quick learner, production-ready from day 1",
}

BULLET_KEYWORDS = {
    "kafka":        "Championed CI/CD pipelines and DevOps practices, managing real-time data pipelines (Kafka/Redis) processing 100,000+ IoT data points daily, automating release cycles using Docker and Jenkins.",
    "microservice": "Designed and developed robust, scalable, and secure multi-tenant Java-based enterprise applications using Spring Boot and Angular 15, streamlining template management operations for over 40 enterprise clients.",
    "api":          "Built and maintained backend services and RESTful APIs, utilizing Swagger and Postman for comprehensive API management and documentation.",
    "angular":      "Authored Angular component logic with strict testing coverage, clearing localized client state and session storage during secure application logouts.",
    "jpa":          "Implemented a Java-based Template Data Access Object (DAO) system utilizing Spring Boot and JPA for advanced data modeling and efficient management of tenant-specific data.",
    "agile":        "Participated in Agile development processes, performing peer code reviews and ensuring all deliverables consisted of clean, efficient, and well-documented code.",
    "performance":  "Troubleshot, debugged, and upgraded existing systems, identifying root causes to reduce average page load latency by over 25%.",
    "devops":       "Championed CI/CD pipelines and DevOps practices, managing real-time data pipelines (Kafka/Redis) processing 100,000+ IoT data points daily.",
    "docker":       "Championed CI/CD pipelines and DevOps practices, automating release cycles using Docker and Jenkins.",
    "security":     "Collaborated directly with cross-functional teams including UI/UX designers, product managers, and QA to seamlessly integrate frontend components with backend services.",
    "default":      "Designed and developed robust, scalable, and secure multi-tenant Java-based enterprise applications using Spring Boot and Angular 15.",
}

SUMMARY_TEMPLATES = {
    "mnc": (
        "Results-driven Java Full Stack Developer with 1.5 years of enterprise experience at Trinity Mobility, "
        "building scalable multi-tenant applications serving 40+ enterprise clients using {skills}. "
        "Proven track record in Agile environments with strong focus on code quality, CI/CD automation, and cross-functional collaboration. "
        "Seeking to leverage production-grade Java expertise at {company} to deliver high-impact software solutions."
    ),
    "startup": (
        "Passionate Java Full Stack Developer with 1.5 years of hands-on experience delivering production-ready applications using {skills}. "
        "Built Kafka-based IoT data pipelines processing 100K+ events/day and led R&D on Agentic AI/MCP architecture. "
        "Thrive in fast-paced startup environments — quick learner, self-driven, and comfortable owning features end-to-end at {company}."
    ),
    "default": (
        "Dedicated Java Full Stack Developer with 1.5 years of industry experience in designing and developing robust, scalable applications using {skills}. "
        "Delivered measurable impact: 25% latency reduction, 100K+ daily IoT events via Kafka, and multi-tenant systems for 40+ clients. "
        "Eager to contribute strong technical fundamentals and problem-solving skills to the team at {company}."
    ),
}

EMAIL_TEMPLATES = {
    "walkin": (
        "Dear Hiring Team,\n\n"
        "I am writing to express my keen interest in the {title} walk-in drive at {company}. "
        "I am a Java Full Stack Developer with 1.5 years of experience at Trinity Mobility (Bengaluru), "
        "specialising in {top_skills}.\n\n"
        "Key highlights:\n"
        "• Managed Kafka/Redis pipelines processing 100,000+ IoT events daily\n"
        "• Built REST APIs & multi-tenant Spring Boot apps for 40+ enterprise clients\n"
        "• Reduced page load latency by 25% through systematic debugging\n"
        "• CGPA 8.96/10 | B.E. CSE, 2024 batch\n\n"
        "I will be attending the walk-in with my resume and supporting documents. "
        "Looking forward to the opportunity.\n\n"
        "Best regards,\nRavikumar N\n+91 9686906521 | rn5127610@gmail.com\ngithub.com/ravigithubcse"
    ),
    "mnc": (
        "Dear Hiring Manager,\n\n"
        "I am applying for the {title} position at {company}. "
        "With 1.5 years of experience building enterprise Java applications at Trinity Mobility, Bengaluru, "
        "I bring strong expertise in {top_skills}.\n\n"
        "Notable achievements:\n"
        "• Kafka-based IoT pipeline handling 100K+ data points/day\n"
        "• Multi-tenant Spring Boot application for 40+ enterprise clients\n"
        "• 25% reduction in page load latency through optimisation\n"
        "• Led R&D on Agentic AI & MCP architecture (2026)\n\n"
        "Please find my tailored resume attached. I would welcome the opportunity to discuss how I can contribute to {company}.\n\n"
        "Best regards,\nRavikumar N\n+91 9686906521 | rn5127610@gmail.com\ngithub.com/ravigithubcse"
    ),
    "default": (
        "Dear Hiring Team,\n\n"
        "I am excited to apply for the {title} role at {company}. "
        "I am a Java Full Stack Developer with 1.5 years of production experience in {top_skills}, "
        "recently at Trinity Mobility Pvt. Ltd., Bengaluru.\n\n"
        "I have hands-on experience with:\n"
        "• Spring Boot 3.x REST APIs & Microservices\n"
        "• Angular 15/17 frontend development\n"
        "• Kafka, Redis, Docker, Jenkins CI/CD\n"
        "• PostgreSQL, MongoDB, JPA/Hibernate\n\n"
        "Attached is my resume tailored for this role. I look forward to hearing from you.\n\n"
        "Best regards,\nRavikumar N\n+91 9686906521 | rn5127610@gmail.com\ngithub.com/ravigithubcse"
    ),
}


def match_skills(job_text):
    job_lower = job_text.lower()
    matched = []
    seen = set()
    for kw, skill in SKILL_MAP.items():
        if kw.replace(".", " ") in job_lower or kw in job_lower:
            if skill not in seen:
                matched.append(skill)
                seen.add(skill)
        if len(matched) >= 6:
            break
    if not matched:
        matched = ["Java 17/18", "Spring Boot 3.x", "Angular 15/17", "REST APIs", "Microservices"]
    return matched[:6]


def pick_bullets(job_text):
    job_lower = job_text.lower()
    bullets = []
    seen = set()
    for kw, bullet in BULLET_KEYWORDS.items():
        if kw == "default":
            continue
        if kw in job_lower and bullet not in seen:
            bullets.append(bullet)
            seen.add(bullet)
        if len(bullets) >= 3:
            break
    if len(bullets) < 3:
        for bullet in BULLET_KEYWORDS.values():
            if bullet not in seen:
                bullets.append(bullet)
                seen.add(bullet)
            if len(bullets) >= 3:
                break
    return bullets[:3]


def build_summary(job, matched_skills):
    ct = job.get("company_type", "").lower()
    company = job.get("company", "your organisation")
    skills_str = ", ".join(matched_skills[:4])
    if ct == "mnc":
        tmpl = SUMMARY_TEMPLATES["mnc"]
    elif ct == "startup":
        tmpl = SUMMARY_TEMPLATES["startup"]
    else:
        tmpl = SUMMARY_TEMPLATES["default"]
    return tmpl.format(skills=skills_str, company=company)


def build_email(job, matched_skills):
    title   = job.get("title", "Software Developer")
    company = job.get("company", "your organisation")
    top_skills = ", ".join(matched_skills[:3])
    if job.get("is_walkin"):
        tmpl = EMAIL_TEMPLATES["walkin"]
    elif job.get("company_type") == "MNC":
        tmpl = EMAIL_TEMPLATES["mnc"]
    else:
        tmpl = EMAIL_TEMPLATES["default"]
    return tmpl.format(title=title, company=company, top_skills=top_skills)


def resume_html(resume, tailored, job):
    skills   = resume["skills"]
    top_bul  = tailored["top_bullets"]
    all_bul  = resume["experience"][0]["bullets"]
    rest_bul = [b for b in all_bul if b not in top_bul]

    bul_html  = "".join(f"<li>{b}</li>" for b in top_bul)
    rest_html = "".join(f"<li>{b}</li>" for b in rest_bul[:4])
    cert_html = "".join(f"<li>{c}</li>" for c in resume["certifications"])

    proj_html = ""
    for p in resume["projects"]:
        pb = "".join(f"<li>{b}</li>" for b in p["bullets"])
        proj_html += f"""<div style="margin-bottom:8px">
<div style="display:flex;justify-content:space-between;margin-bottom:2px">
  <span style="font-weight:700">{p["name"]}</span>
  <span style="color:#777;font-size:9pt">{p["tech"]} | {p["year"]}</span>
</div><ul style="margin:0">{pb}</ul></div>"""

    edu_html = ""
    for e in resume["education"]:
        edu_html += f"""<div style="display:flex;justify-content:space-between">
  <span><strong>{e["degree"]}</strong> — {e["institution"]}</span>
  <span style="color:#1565c0;font-weight:600">{e["score"]}</span>
</div><div style="font-size:9pt;color:#666;margin-bottom:4px">{e["duration"]}</div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Ravikumar — Resume</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;font-size:10.5pt;color:#111;line-height:1.45;padding:22px 30px}}
h1{{font-size:20pt;font-weight:700;color:#1a237e}}
.sub{{font-size:11pt;color:#1565c0;margin-top:2px}}
.con{{font-size:9.5pt;color:#555;margin-top:4px}}
h2{{font-size:11pt;font-weight:700;color:#1a237e;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}}
hr{{border:none;border-top:1.5px solid #1a237e;margin:7px 0}}
.thr{{border:none;border-top:1px solid #e0e0e0;margin:6px 0}}
ul{{padding-left:18px}}li{{margin-bottom:2px;font-size:10pt}}
.sg{{display:grid;grid-template-columns:110px 1fr;gap:2px 8px;font-size:10pt}}
.sc{{font-weight:600;color:#1a237e}}
section{{margin-bottom:9px}}
</style></head><body>
<div style="text-align:center;margin-bottom:8px">
<h1>{resume["name"]}</h1>
<div class="sub">{resume["title"]}</div>
<div class="con">{resume["email"]} | {resume["phone"]} | {resume["location"]}<br>
{resume["linkedin"]} | {resume["github"]}</div></div>
<hr>
<section><h2>Professional Summary</h2>
<p style="font-size:10pt;margin-top:3px">{tailored["summary"]}</p></section>
<div class="thr"></div>
<section><h2>Technical Skills</h2>
<div class="sg">
<span class="sc">Frontend</span><span>{skills["frontend"]}</span>
<span class="sc">Backend</span><span>{skills["backend"]}</span>
<span class="sc">API & Tools</span><span>{skills["api_tools"]}</span>
<span class="sc">Testing/DevOps</span><span>{skills["testing_devops"]}</span>
<span class="sc">Databases</span><span>{skills["databases"]}</span>
</div></section>
<div class="thr"></div>
<section><h2>Professional Experience</h2>
<div style="display:flex;justify-content:space-between">
<span style="font-weight:700;font-size:11pt">Trinity Mobility Pvt. Ltd.</span>
<span style="color:#666;font-size:9.5pt">Aug 2025 – May 2026</span></div>
<div style="color:#1565c0;font-size:10.5pt;margin-bottom:3px">Associate Software Engineer | Bengaluru, India</div>
<ul>{bul_html}{rest_html}</ul></section>
<div class="thr"></div>
<section><h2>Projects</h2>{proj_html}</section>
<div class="thr"></div>
<section><h2>Education</h2>{edu_html}</section>
<div class="thr"></div>
<section><h2>Certifications</h2><ul>{cert_html}</ul></section>
</body></html>"""


def tailor_all():
    print(f"\n{'='*55}")
    print(f"  FREE RESUME TAILOR (keyword-based)")
    print(f"  {datetime.now().strftime('%d %b %Y %I:%M %p')}")
    print(f"{'='*55}\n")

    with open(BASE_RESUME_PATH) as f:
        resume = json.load(f)
    with open(JOBS_FILE) as f:
        jobs_data = json.load(f)

    priority = (
        jobs_data.get("walkin_jobs",  []) +
        jobs_data.get("mnc_jobs",     []) +
        jobs_data.get("startup_jobs", []) +
        jobs_data.get("other_jobs",   [])
    )
    top = priority[:MAX_TAILOR]

    results = []
    for i, job in enumerate(top):
        title   = job.get("title", "Role")
        company = job.get("company", "Company")
        print(f"  [{i+1}/{len(top)}] {title} @ {company}")

        job_text      = f"{title} {company} {job.get('skills','')} {job.get('experience','')}"
        matched       = match_skills(job_text)
        bullets       = pick_bullets(job_text)
        summary       = build_summary(job, matched)
        email_body    = build_email(job, matched)
        email_subject = (
            f"Application: {title} | Java Full Stack | 1.5 YOE | Spring Boot + Angular | Bengaluru"
        )

        tailored = {
            "summary":       summary,
            "top_skills":    matched,
            "top_bullets":   bullets,
            "email_subject": email_subject,
            "email_body":    email_body,
        }

        html = resume_html(resume, tailored, job)
        results.append({"job": job, "tailored": tailored, "resume_html": html})

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  ✅ Tailored {len(results)} resumes (FREE — no API used)\n")
    return results


if __name__ == "__main__":
    tailor_all()

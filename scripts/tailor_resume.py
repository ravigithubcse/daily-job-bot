#!/usr/bin/env python3
"""
AI Resume Tailor — Claude API
Generates tailored resume HTML + cold email for top jobs
"""

import json
import os
import time
import anthropic
from datetime import datetime

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BASE_RESUME_PATH  = "resume/base_resume.json"
JOBS_FILE         = "jobs_found.json"
OUTPUT_FILE       = "tailored_resumes.json"
MAX_TAILOR        = 5   # Top 5 jobs per day (API cost ~$0.01/run)


def load_base():
    with open(BASE_RESUME_PATH) as f:
        return json.load(f)


def load_jobs():
    with open(JOBS_FILE) as f:
        return json.load(f)


def tailor(client, resume, job):
    prompt = f"""You are an expert ATS resume writer for Indian tech job market.

CANDIDATE RESUME:
{json.dumps(resume, indent=2)}

JOB TO APPLY FOR:
Title: {job.get('title')}
Company: {job.get('company')} ({job.get('company_type', '')})
Source: {job.get('source')}
Experience: {job.get('experience')}

TASKS:
1. Write a tailored Professional Summary (3-4 sentences, ATS-optimized, use keywords from job title/company type)
2. List top 5 most relevant skills from candidate's profile matching this role
3. Pick 3 strongest bullet points from experience that best match this role (copy verbatim from resume)
4. Write a professional cold email body (greeting + 4-5 lines + closing). Subject line should be crisp.

Respond ONLY as valid JSON (no markdown fences):
{{
  "tailored_summary": "...",
  "top_skills": ["skill1","skill2","skill3","skill4","skill5"],
  "top_bullets": ["bullet1","bullet2","bullet3"],
  "email_subject": "...",
  "email_body": "..."
}}"""

    try:
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        text = msg.content[0].text.strip()
        # Strip markdown fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        print(f"    ⚠ AI error: {e}")
        return {
            "tailored_summary": resume["summary"],
            "top_skills": ["Java 17/18", "Spring Boot 3.x", "Angular 15/17", "REST APIs", "Microservices"],
            "top_bullets": resume["experience"][0]["bullets"][:3],
            "email_subject": f"Application for {job.get('title')} | Java Full Stack | 1.5 YOE | Bengaluru",
            "email_body": (
                f"Dear Hiring Team,\n\n"
                f"I am writing to express my interest in the {job.get('title')} position at {job.get('company')}. "
                f"With 1.5 years of experience building enterprise Java applications using Spring Boot, Angular, and Microservices architecture at Trinity Mobility, "
                f"I am confident I can contribute effectively from day one.\n\n"
                f"Key highlights: Kafka-based IoT pipeline (100K+ data points/day), Spring Security JWT/SAML, "
                f"CI/CD with Docker & Jenkins, CGPA 8.96/10 (CSE).\n\n"
                f"Please find my tailored resume attached. I would love to discuss this opportunity further.\n\n"
                f"Best regards,\nRavikumar\n+91 9686906521 | rn5127610@gmail.com"
            )
        }


def resume_html(resume, tailored, job):
    skills = resume["skills"]
    bullets_html = "".join(f"<li>{b}</li>" for b in tailored.get("top_bullets", resume["experience"][0]["bullets"][:4]))
    remaining = [b for b in resume["experience"][0]["bullets"] if b not in tailored.get("top_bullets", [])]
    remaining_html = "".join(f"<li>{b}</li>" for b in remaining[:4])
    certs_html = "".join(f"<li>{c}</li>" for c in resume["certifications"])
    proj_html = ""
    for p in resume["projects"]:
        pb = "".join(f"<li>{b}</li>" for b in p["bullets"])
        proj_html += f"""<div style="margin-bottom:8px">
  <div style="display:flex;justify-content:space-between"><span style="font-weight:700">{p["name"]}</span><span style="color:#777;font-size:9.5pt">{p["tech"]} | {p["year"]}</span></div>
  <ul style="margin:2px 0">{pb}</ul></div>"""
    edu_html = ""
    for e in resume["education"]:
        edu_html += f"""<div style="display:flex;justify-content:space-between;margin-bottom:3px">
  <span><strong>{e["degree"]}</strong> — {e["institution"]}</span>
  <span style="color:#1565c0;font-weight:600">{e["score"]}</span></div>
  <div style="font-size:9.5pt;color:#666">{e["duration"]}</div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Ravikumar Resume</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;font-size:10.5pt;color:#111;line-height:1.45;padding:22px 30px}}
h1{{font-size:20pt;font-weight:700;color:#1a237e}}
.sub{{font-size:11pt;color:#1565c0;margin-top:2px}}
.contact{{font-size:9.5pt;color:#555;margin-top:4px}}
h2{{font-size:11pt;font-weight:700;color:#1a237e;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}}
hr{{border:none;border-top:1.5px solid #1a237e;margin:7px 0}}
.thr{{border:none;border-top:1px solid #e0e0e0;margin:6px 0}}
ul{{padding-left:18px}}li{{margin-bottom:2px;font-size:10pt}}
.sg{{display:grid;grid-template-columns:110px 1fr;gap:2px 6px;font-size:10pt}}
.sc{{font-weight:600;color:#1a237e}}
</style></head><body>
<div style="text-align:center;margin-bottom:8px">
<h1>{resume["name"]}</h1>
<div class="sub">{resume["title"]}</div>
<div class="contact">{resume["email"]} | {resume["phone"]} | {resume["location"]}<br>{resume["linkedin"]} | {resume["github"]}</div>
</div>
<hr>
<section style="margin-bottom:9px"><h2>Professional Summary</h2>
<p style="font-size:10pt;margin-top:3px">{tailored.get("tailored_summary", resume["summary"])}</p></section>
<div class="thr"></div>
<section style="margin-bottom:9px"><h2>Technical Skills</h2>
<div class="sg">
<span class="sc">Frontend</span><span>{skills["frontend"]}</span>
<span class="sc">Backend</span><span>{skills["backend"]}</span>
<span class="sc">API & Tools</span><span>{skills["api_tools"]}</span>
<span class="sc">Testing/DevOps</span><span>{skills["testing_devops"]}</span>
<span class="sc">Databases</span><span>{skills["databases"]}</span>
</div></section>
<div class="thr"></div>
<section style="margin-bottom:9px"><h2>Professional Experience</h2>
<div style="display:flex;justify-content:space-between">
<span style="font-weight:700;font-size:11pt">Trinity Mobility Pvt. Ltd.</span>
<span style="color:#666;font-size:9.5pt">Aug 2025 – May 2026</span></div>
<div style="color:#1565c0;font-size:10.5pt;margin-bottom:3px">Associate Software Engineer | Bengaluru, India</div>
<ul>{bullets_html}{remaining_html}</ul></section>
<div class="thr"></div>
<section style="margin-bottom:9px"><h2>Projects</h2>{proj_html}</section>
<div class="thr"></div>
<section style="margin-bottom:9px"><h2>Education</h2>{edu_html}</section>
<div class="thr"></div>
<section><h2>Certifications</h2><ul>{certs_html}</ul></section>
</body></html>"""


def tailor_all():
    print(f"\n{'='*55}")
    print(f"  AI RESUME TAILORING — {datetime.now().strftime('%d %b %Y %I:%M %p')}")
    print(f"{'='*55}\n")

    if not ANTHROPIC_API_KEY:
        print("  ⚠ ANTHROPIC_API_KEY not set — skipping AI tailoring")
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resume = load_base()
    jobs_data = load_jobs()

    # Prioritize: walk-ins first, then MNC, then startup
    priority = (
        jobs_data.get("walkin_jobs", []) +
        jobs_data.get("mnc_jobs", []) +
        jobs_data.get("startup_jobs", []) +
        jobs_data.get("other_jobs", [])
    )
    top = priority[:MAX_TAILOR]

    results = []
    for i, job in enumerate(top):
        print(f"  [{i+1}/{len(top)}] {job.get('title')} @ {job.get('company')}")
        t = tailor(client, resume, job)
        html = resume_html(resume, t, job)
        results.append({"job": job, "tailored": t, "resume_html": html})
        time.sleep(1)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  ✅ Tailored {len(results)} resumes\n")
    return results


if __name__ == "__main__":
    tailor_all()

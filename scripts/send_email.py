#!/usr/bin/env python3
"""
Daily Job Email Digest Sender
Sends to rn5127610@gmail.com every morning with:
- Walk-In drives (highlighted first)
- MNC openings
- Startup openings
- Other companies
- AI-tailored resumes attached (top 5)
"""

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

RECIPIENT   = "rn5127610@gmail.com"
SENDER      = os.environ.get("GMAIL_SENDER", "rn5127610@gmail.com")
APP_PASS    = os.environ.get("GMAIL_APP_PASSWORD", "")
JOBS_FILE   = "jobs_found.json"
TAILORED    = "tailored_resumes.json"


def load():
    jobs, tailored = {}, []
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE) as f: jobs = json.load(f)
    if os.path.exists(TAILORED):
        with open(TAILORED) as f: tailored = json.load(f)
    return jobs, tailored


def job_card(job, num, highlight=False):
    src_color = {
        "LinkedIn": "#0077b5", "Wellfound": "#fb6404",
        "Internshala": "#00b4d8", "TimesJobs": "#c62828",
        "TimesJobs Walk-In": "#e65100", "Freshersworld": "#2e7d32",
    }.get(job.get("source",""), "#546e7a")

    ct_badge = ""
    ct = job.get("company_type","")
    if ct == "MNC":
        ct_badge = '<span style="background:#1a237e;color:white;padding:1px 7px;border-radius:10px;font-size:10px;margin-left:4px">🏢 MNC</span>'
    elif ct == "Startup":
        ct_badge = '<span style="background:#4a148c;color:white;padding:1px 7px;border-radius:10px;font-size:10px;margin-left:4px">🚀 Startup</span>'

    wi_badge = ""
    wi_info = ""
    if job.get("is_walkin"):
        wi_badge = '<span style="background:#e65100;color:white;padding:2px 9px;border-radius:12px;font-size:11px;font-weight:700;margin-left:6px">🚶 WALK-IN</span>'
        if job.get("walkin_info"):
            wi_info = f'<div style="color:#e65100;font-size:11px;margin-top:3px;font-weight:600">📅 {job["walkin_info"]}</div>'

    skills_row = f'<div style="color:#555;font-size:11px;margin-top:2px">🔧 {job["skills"]}</div>' if job.get("skills") else ""
    salary_row = f'<div style="color:#2e7d32;font-size:11px;margin-top:2px">💰 {job["salary"]}</div>' if job.get("salary") else ""

    bg = "#fff8e1" if job.get("is_walkin") else ("#f3f8ff" if highlight else "#ffffff")
    border = "#e65100" if job.get("is_walkin") else ("#bbdefb" if highlight else "#e0e0e0")

    src_badge = f'<span style="background:{src_color};color:white;padding:1px 6px;border-radius:8px;font-size:10px">{job.get("source","")}</span>'

    return f"""
<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:13px 15px;margin-bottom:9px">
  <div style="display:flex;flex-wrap:wrap;align-items:center;gap:5px">
    <span style="font-size:13.5px;font-weight:700;color:#1a237e">{num}. {job.get("title","Role")}</span>
    {wi_badge}{ct_badge}
  </div>
  <div style="color:#333;margin-top:4px;font-size:12.5px">
    🏢 <strong>{job.get("company","")}</strong> &nbsp;|&nbsp; 📍 {job.get("location","Bengaluru")} &nbsp;|&nbsp; ⏱ {job.get("experience","")}
  </div>
  {wi_info}{skills_row}{salary_row}
  <div style="color:#999;font-size:10.5px;margin-top:3px">📅 Posted: {job.get("posted","Recent")} &nbsp;|&nbsp; {src_badge}</div>
  <a href="{job.get("link","#")}" style="display:inline-block;margin-top:8px;background:#1565c0;color:white;padding:5px 15px;border-radius:5px;text-decoration:none;font-size:12px;font-weight:600">Apply Now →</a>
</div>"""


def section(title_str, icon, jobs, color, highlight=False):
    if not jobs:
        return ""
    cards = "".join(job_card(j, i+1, highlight) for i, j in enumerate(jobs))
    return f"""
<div style="margin-bottom:22px">
  <h2 style="color:{color};font-size:15px;border-bottom:2px solid {color};padding-bottom:5px;margin-bottom:11px">{icon} {title_str} ({len(jobs)})</h2>
  {cards}
</div>"""


def tailored_section(items):
    if not items:
        return ""
    rows = ""
    for i, item in enumerate(items):
        job = item.get("job", {})
        t   = item.get("tailored", {})
        skills = ", ".join(t.get("top_skills", []))
        subj   = t.get("email_subject", "")
        body   = t.get("email_body", "").replace("\n", "<br>")
        rows += f"""
<div style="background:#f3f8ff;border:1px solid #90caf9;border-radius:8px;padding:13px;margin-bottom:10px">
  <div style="font-weight:700;color:#1a237e;font-size:13px">{i+1}. {job.get("title")} @ {job.get("company")}
    <span style="font-size:10px;color:#555;font-weight:400;margin-left:6px">({job.get("company_type","")}, {job.get("source","")})</span>
  </div>
  <div style="font-size:11.5px;color:#333;margin-top:5px">🎯 <strong>Matched Skills:</strong> {skills}</div>
  <div style="margin-top:8px;font-size:11.5px">
    <strong>📧 Subject:</strong> <span style="color:#1565c0">{subj}</span><br><br>
    <strong>Email Body:</strong><br>
    <div style="background:white;border:1px solid #ddd;border-radius:5px;padding:9px;margin-top:4px;font-size:11px;font-family:monospace;line-height:1.6">{body}</div>
  </div>
  <div style="margin-top:7px;font-size:10.5px;color:#777">✅ Tailored resume attached: <em>Resume_{i+1}_{job.get("company","").replace(" ","_")[:15]}.html</em></div>
</div>"""

    return f"""
<div style="margin-bottom:22px">
  <h2 style="color:#1b5e20;font-size:15px;border-bottom:2px solid #388e3c;padding-bottom:5px;margin-bottom:11px">🤖 AI-Tailored Resumes + Cold Emails ({len(items)})</h2>
  {rows}
</div>"""


def build_html(jobs_data, tailored_data):
    today     = datetime.now().strftime("%A, %d %B %Y")
    total     = jobs_data.get("total_found", 0)
    wi_count  = jobs_data.get("walkin_count", 0)
    mnc_count = jobs_data.get("mnc_count", 0)
    st_count  = jobs_data.get("startup_count", 0)
    ot_count  = jobs_data.get("other_count", 0)

    walkin_jobs  = jobs_data.get("walkin_jobs",  [])
    mnc_jobs     = jobs_data.get("mnc_jobs",     [])
    startup_jobs = jobs_data.get("startup_jobs", [])
    other_jobs   = jobs_data.get("other_jobs",   [])[:15]  # cap to 15

    empty_msg = ""
    if total == 0:
        empty_msg = '<div style="background:#fff3e0;border:1px solid #ffb74d;border-radius:8px;padding:14px;text-align:center;color:#e65100;margin-bottom:20px">⚠️ No matching jobs found today. Will retry tomorrow!</div>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#eceff1;font-family:Arial,sans-serif">
<div style="max-width:700px;margin:0 auto;padding:20px">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#1a237e 0%,#0d47a1 60%,#1565c0 100%);border-radius:14px;padding:22px 26px;margin-bottom:20px;text-align:center">
    <div style="font-size:26px;margin-bottom:4px">☕</div>
    <div style="color:white;font-size:21px;font-weight:700">Good Morning, Roy!</div>
    <div style="color:#90caf9;font-size:13px;margin-top:3px">{today} &nbsp;|&nbsp; Your Daily Job Digest</div>
    <div style="display:flex;justify-content:center;gap:14px;margin-top:16px;flex-wrap:wrap">
      <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:9px 18px">
        <div style="color:white;font-size:22px;font-weight:700">{total}</div>
        <div style="color:#90caf9;font-size:11px">Total Jobs</div>
      </div>
      <div style="background:rgba(230,81,0,0.4);border-radius:10px;padding:9px 18px">
        <div style="color:white;font-size:22px;font-weight:700">{wi_count}</div>
        <div style="color:#ffcc80;font-size:11px">Walk-Ins</div>
      </div>
      <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:9px 18px">
        <div style="color:white;font-size:22px;font-weight:700">{mnc_count}</div>
        <div style="color:#90caf9;font-size:11px">MNCs</div>
      </div>
      <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:9px 18px">
        <div style="color:white;font-size:22px;font-weight:700">{st_count}</div>
        <div style="color:#90caf9;font-size:11px">Startups</div>
      </div>
    </div>
  </div>

  <!-- CONTENT -->
  {empty_msg}
  {section("Walk-In Drives – Bengaluru", "🚶", walkin_jobs, "#e65100", highlight=True)}
  {section("MNC Openings", "🏢", mnc_jobs, "#1a237e", highlight=True)}
  {section("Startup Openings", "🚀", startup_jobs, "#4a148c")}
  {section("Other Companies", "💼", other_jobs, "#37474f")}
  {tailored_section(tailored_data)}

  <!-- TIPS -->
  <div style="background:#f5f5f5;border-radius:10px;padding:14px 16px;margin-bottom:18px">
    <div style="font-weight:700;color:#424242;font-size:13px;margin-bottom:8px">💡 Today's Tips</div>
    <ul style="font-size:12px;color:#555;padding-left:18px;margin:0;line-height:1.8">
      <li>Walk-in jobs are first-come-first-serve — go early!</li>
      <li>For MNCs: apply on their official careers portal too</li>
      <li>Follow up on LinkedIn 3 days after applying</li>
      <li>Customise email subject: <em>Java Developer | Spring Boot + Angular | 1.5 YOE | Bengaluru</em></li>
    </ul>
  </div>

  <!-- FOOTER -->
  <div style="text-align:center;color:#9e9e9e;font-size:11px;padding:8px 0">
    🤖 Roy's Job Bot &nbsp;|&nbsp; Runs daily at 7:00 AM IST via GitHub Actions<br>
    Java Full Stack | Spring Boot | Angular | Bengaluru
  </div>
</div>
</body></html>"""


def send(html, tailored_data):
    today = datetime.now().strftime("%d %b %Y")
    subj  = f"☕ Daily Jobs – {today} | Java Full Stack Bengaluru"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subj
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT

    msg.attach(MIMEText(html, "html"))

    # Attach tailored resumes
    for i, item in enumerate(tailored_data[:5]):
        job       = item.get("job", {})
        res_html  = item.get("resume_html", "")
        company   = job.get("company","Co").replace(" ","_")[:15]
        fname     = f"Resume_{i+1}_{company}.html"
        part = MIMEBase("text", "html")
        part.set_payload(res_html.encode("utf-8"))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=fname)
        msg.attach(part)

    if not APP_PASS:
        print("  ⚠ GMAIL_APP_PASSWORD not set — saving preview only")
        with open("email_preview.html","w") as f: f.write(html)
        return False

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(SENDER, APP_PASS)
            srv.sendmail(SENDER, RECIPIENT, msg.as_string())
        print(f"  ✅ Email sent → {RECIPIENT} ({len(tailored_data)} resumes attached)")
        return True
    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        with open("email_preview.html","w") as f: f.write(html)
        return False


def send_digest():
    print(f"\n{'='*55}")
    print(f"  EMAIL SENDER — {datetime.now().strftime('%d %b %Y %I:%M %p')}")
    print(f"{'='*55}\n")
    jobs_data, tailored_data = load()
    html = build_html(jobs_data, tailored_data)
    with open("email_preview.html","w") as f: f.write(html)
    print("  📄 Preview saved: email_preview.html")
    send(html, tailored_data)


if __name__ == "__main__":
    send_digest()

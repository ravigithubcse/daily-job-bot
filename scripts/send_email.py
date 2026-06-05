#!/usr/bin/env python3
"""
Daily Job Email Digest Sender - Beautiful UI Version
Sends to rn5127610@gmail.com every morning
"""

import json, os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

RECIPIENT = "rn5127610@gmail.com"
SENDER    = os.environ.get("GMAIL_SENDER", "rn5127610@gmail.com")
APP_PASS  = os.environ.get("GMAIL_APP_PASSWORD", "")
JOBS_FILE = "jobs_found.json"
TAILORED  = "tailored_resumes.json"


def load():
    jobs, tailored = {}, []
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE) as f: jobs = json.load(f)
    if os.path.exists(TAILORED):
        with open(TAILORED) as f: tailored = json.load(f)
    return jobs, tailored


def job_card(job, num):
    is_walkin = job.get("is_walkin", False)
    ct        = job.get("company_type", "Company")
    source    = job.get("source", "")

    # Source pill color
    src_colors = {
        "LinkedIn": "#0077b5", "Wellfound": "#fb6404",
        "Internshala": "#00b4d8", "TimesJobs": "#c62828",
        "TimesJobs Walk-In": "#e65100", "Freshersworld": "#2e7d32",
    }
    src_color = src_colors.get(source, "#546e7a")

    # Company type badge
    ct_badge = ""
    if ct == "MNC":
        ct_badge = '<span style="background:linear-gradient(135deg,#1a237e,#283593);color:white;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:0.5px">🏢 MNC</span>'
    elif ct == "Startup":
        ct_badge = '<span style="background:linear-gradient(135deg,#6a1b9a,#7b1fa2);color:white;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:0.5px">🚀 Startup</span>'

    walkin_badge = ""
    walkin_info  = ""
    if is_walkin:
        walkin_badge = '<span style="background:linear-gradient(135deg,#e65100,#f4511e);color:white;padding:3px 12px;border-radius:20px;font-size:10px;font-weight:800;letter-spacing:0.5px;animation:pulse 1s infinite">🚶 WALK-IN</span>'
        if job.get("walkin_info"):
            walkin_info = f'<div style="margin-top:6px;padding:6px 10px;background:rgba(230,81,0,0.08);border-left:3px solid #e65100;border-radius:4px;color:#bf360c;font-size:11px;font-weight:600">📅 {job["walkin_info"]}</div>'

    skills_row = f'<div style="margin-top:5px;font-size:11px;color:#555">🔧 <span style="color:#37474f">{job["skills"]}</span></div>' if job.get("skills") else ""
    salary_row = f'<div style="margin-top:3px;font-size:11px;color:#2e7d32;font-weight:600">💰 {job["salary"]}</div>' if job.get("salary") else ""

    # Card style
    if is_walkin:
        card_bg     = "linear-gradient(135deg,#fff8e1,#fff3e0)"
        card_border = "#ffb74d"
        card_shadow = "0 2px 12px rgba(230,81,0,0.12)"
    elif ct == "MNC":
        card_bg     = "linear-gradient(135deg,#f8f9ff,#f0f4ff)"
        card_border = "#90caf9"
        card_shadow = "0 2px 12px rgba(26,35,126,0.08)"
    else:
        card_bg     = "#ffffff"
        card_border = "#e8eaf0"
        card_shadow = "0 1px 6px rgba(0,0,0,0.06)"

    return f"""
<div style="background:{card_bg};border:1px solid {card_border};border-radius:12px;padding:16px 18px;margin-bottom:12px;box-shadow:{card_shadow}">
  <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-bottom:8px">
    <span style="font-size:15px;font-weight:800;color:#1a237e;flex:1;min-width:200px">{num}. {job.get("title","Role")}</span>
    {walkin_badge}
    {ct_badge}
  </div>
  <div style="font-size:12.5px;color:#37474f;margin-bottom:4px">
    🏢 <strong style="color:#1a237e">{job.get("company","")}</strong>
    &nbsp;·&nbsp; 📍 {job.get("location","Bengaluru")}
    &nbsp;·&nbsp; ⏱ <span style="color:#1565c0">{job.get("experience","0-2 years")}</span>
  </div>
  {walkin_info}{skills_row}{salary_row}
  <div style="display:flex;align-items:center;justify-content:space-between;margin-top:10px;flex-wrap:wrap;gap:8px">
    <span style="font-size:10px;color:#9e9e9e">📅 {job.get("posted","Recent")} &nbsp;·&nbsp;
      <span style="background:{src_color};color:white;padding:2px 8px;border-radius:10px;font-size:9.5px">{source}</span>
    </span>
    <a href="{job.get("link","#")}" style="background:linear-gradient(135deg,#1565c0,#1976d2);color:white;padding:7px 18px;border-radius:20px;text-decoration:none;font-size:12px;font-weight:700;letter-spacing:0.3px;box-shadow:0 2px 8px rgba(21,101,192,0.3)">Apply Now →</a>
  </div>
</div>"""


def section_html(title_str, icon, jobs, grad_start, grad_end, show_all=True):
    if not jobs: return ""
    display = jobs if show_all else jobs[:15]
    cards = "".join(job_card(j, i+1) for i, j in enumerate(display))
    more = f'<div style="text-align:center;font-size:11px;color:#9e9e9e;margin-top:4px">+ {len(jobs)-15} more jobs not shown</div>' if not show_all and len(jobs) > 15 else ""
    return f"""
<div style="margin-bottom:28px">
  <div style="background:linear-gradient(135deg,{grad_start},{grad_end});border-radius:12px;padding:12px 18px;margin-bottom:14px;display:flex;align-items:center;gap:10px">
    <span style="font-size:20px">{icon}</span>
    <span style="color:white;font-size:15px;font-weight:800;letter-spacing:0.3px">{title_str}</span>
    <span style="margin-left:auto;background:rgba(255,255,255,0.25);color:white;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700">{len(jobs)}</span>
  </div>
  {cards}{more}
</div>"""


def tailored_section_html(items):
    if not items: return ""
    rows = ""
    for i, item in enumerate(items):
        job     = item.get("job", {})
        t       = item.get("tailored", {})
        skills  = " &nbsp;·&nbsp; ".join(f'<span style="background:#e8f0fe;color:#1565c0;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600">{s}</span>' for s in t.get("top_skills", [])[:4])
        subj    = t.get("email_subject", "")
        body    = t.get("email_body", "").replace("\n", "<br>")
        company = job.get("company","")
        title   = job.get("title","")
        ct      = job.get("company_type","")
        ct_icon = "🏢" if ct == "MNC" else ("🚀" if ct == "Startup" else "💼")

        rows += f"""
<div style="background:white;border:1px solid #e3f2fd;border-radius:12px;padding:16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(21,101,192,0.06)">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
    <span style="background:linear-gradient(135deg,#1565c0,#1976d2);color:white;width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;flex-shrink:0">{i+1}</span>
    <div>
      <div style="font-weight:800;color:#1a237e;font-size:13px">{title}</div>
      <div style="font-size:11px;color:#666">{ct_icon} {company} &nbsp;·&nbsp; {job.get("source","")}</div>
    </div>
  </div>
  <div style="margin-bottom:8px;flex-wrap:wrap;display:flex;gap:4px">{skills}</div>
  <div style="background:#f8f9ff;border-radius:8px;padding:10px 12px;margin-bottom:8px">
    <div style="font-size:10.5px;color:#666;font-weight:700;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.5px">📧 Email Subject</div>
    <div style="font-size:11.5px;color:#1565c0;font-weight:600">{subj}</div>
  </div>
  <div style="background:#f8f9ff;border-radius:8px;padding:10px 12px">
    <div style="font-size:10.5px;color:#666;font-weight:700;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px">✉️ Cold Email Body</div>
    <div style="font-size:11px;color:#333;font-family:Georgia,serif;line-height:1.7;border-left:3px solid #90caf9;padding-left:10px">{body}</div>
  </div>
  <div style="margin-top:8px;font-size:10.5px;color:#43a047;font-weight:600">📎 Resume attached: Resume_{i+1}_{company.replace(" ","_")[:15]}_{title.replace(" ","_")[:20]}.html</div>
</div>"""

    return f"""
<div style="margin-bottom:28px">
  <div style="background:linear-gradient(135deg,#1b5e20,#2e7d32);border-radius:12px;padding:12px 18px;margin-bottom:14px;display:flex;align-items:center;gap:10px">
    <span style="font-size:20px">🤖</span>
    <span style="color:white;font-size:15px;font-weight:800;letter-spacing:0.3px">AI-Tailored Resumes + Cold Emails</span>
    <span style="margin-left:auto;background:rgba(255,255,255,0.25);color:white;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700">{len(items)}</span>
  </div>
  {rows}
</div>"""


def build_html(jobs_data, tailored_data):
    today    = datetime.now().strftime("%A, %d %B %Y")
    total    = jobs_data.get("total_found", 0)
    wi_count = jobs_data.get("walkin_count", 0)
    mnc_count= jobs_data.get("mnc_count", 0)
    st_count = jobs_data.get("startup_count", 0)
    ot_count = jobs_data.get("other_count", 0)

    walkin_jobs  = jobs_data.get("walkin_jobs", [])
    mnc_jobs     = jobs_data.get("mnc_jobs", [])
    startup_jobs = jobs_data.get("startup_jobs", [])
    other_jobs   = jobs_data.get("other_jobs", [])

    stat = lambda val, label, bg: f'''
<div style="background:{bg};border-radius:12px;padding:12px 20px;text-align:center;min-width:70px">
  <div style="color:white;font-size:24px;font-weight:900;line-height:1">{val}</div>
  <div style="color:rgba(255,255,255,0.8);font-size:10px;font-weight:600;margin-top:3px;letter-spacing:0.5px">{label}</div>
</div>'''

    stats = (
        stat(total,    "TOTAL JOBS",  "rgba(255,255,255,0.18)") +
        stat(wi_count, "WALK-INS",    "rgba(230,81,0,0.5)" if wi_count else "rgba(255,255,255,0.1)") +
        stat(mnc_count,"MNCs",        "rgba(255,255,255,0.18)") +
        stat(st_count, "STARTUPS",    "rgba(255,255,255,0.18)") +
        stat(len(tailored_data),"AI RESUMES","rgba(46,125,50,0.5)")
    )

    empty = ""
    if total == 0:
        empty = '<div style="background:#fff3e0;border:2px dashed #ffb74d;border-radius:12px;padding:20px;text-align:center;color:#e65100;margin-bottom:20px;font-weight:600">⚠️ No matching jobs found today. Bot will retry tomorrow at 7 AM!</div>'

    tips = """
<div style="background:linear-gradient(135deg,#f0f4ff,#e8f0fe);border:1px solid #c5cae9;border-radius:12px;padding:16px 18px;margin-bottom:20px">
  <div style="font-weight:800;color:#1a237e;font-size:13px;margin-bottom:10px">💡 Today's Action Tips</div>
  <div style="display:grid;gap:7px">
    <div style="font-size:12px;color:#37474f;display:flex;gap:8px"><span style="color:#1565c0;font-weight:700">①</span> Walk-in jobs are first-come-first-serve — go early with printed resume!</div>
    <div style="font-size:12px;color:#37474f;display:flex;gap:8px"><span style="color:#1565c0;font-weight:700">②</span> For MNCs: apply on official careers portal + LinkedIn both</div>
    <div style="font-size:12px;color:#37474f;display:flex;gap:8px"><span style="color:#1565c0;font-weight:700">③</span> Send cold email with subject: <em style="color:#1565c0">Java Developer | Spring Boot + Angular | 1.5 YOE | Bengaluru</em></div>
    <div style="font-size:12px;color:#37474f;display:flex;gap:8px"><span style="color:#1565c0;font-weight:700">④</span> Follow up on LinkedIn 3 days after applying — it doubles your response rate!</div>
  </div>
</div>"""

    walkin_section  = section_html(f"Walk-In Drives — Bengaluru", "🚶", walkin_jobs,  "#e65100", "#f4511e")
    mnc_section     = section_html(f"MNC Openings", "🏢", mnc_jobs,     "#1a237e", "#1565c0")
    startup_section = section_html(f"Startup Openings", "🚀", startup_jobs, "#6a1b9a", "#7b1fa2")
    other_section   = section_html(f"Other Companies", "💼", other_jobs,  "#37474f", "#455a64", show_all=False)
    ai_section      = tailored_section_html(tailored_data)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Job Digest</title></head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif">
<div style="max-width:680px;margin:0 auto;padding:24px 16px">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#0d1b6e 0%,#1a237e 40%,#1565c0 100%);border-radius:20px;padding:28px 24px 24px;margin-bottom:20px;text-align:center;box-shadow:0 8px 32px rgba(13,27,110,0.3)">
    <div style="font-size:36px;margin-bottom:6px">☕</div>
    <div style="color:white;font-size:26px;font-weight:900;letter-spacing:-0.5px">Good Morning, Roy!</div>
    <div style="color:rgba(255,255,255,0.7);font-size:13px;margin-top:4px;letter-spacing:0.3px">{today} &nbsp;·&nbsp; Your Daily Job Digest</div>
    <div style="display:flex;justify-content:center;gap:10px;margin-top:20px;flex-wrap:wrap">
      {stats}
    </div>
  </div>

  <!-- CONTENT -->
  {empty}
  {walkin_section}
  {mnc_section}
  {startup_section}
  {other_section}
  {ai_section}
  {tips}

  <!-- FOOTER -->
  <div style="text-align:center;padding:16px 0 8px">
    <div style="display:inline-block;background:linear-gradient(135deg,#1a237e,#1565c0);border-radius:20px;padding:10px 24px">
      <div style="color:white;font-size:11px;font-weight:700;letter-spacing:0.5px">🤖 ROY'S JOB BOT</div>
      <div style="color:rgba(255,255,255,0.7);font-size:10px;margin-top:2px">Runs daily at 7:00 AM IST · Java Full Stack · Bengaluru · 100% Free</div>
    </div>
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

    for i, item in enumerate(tailored_data[:5]):
        job      = item.get("job", {})
        res_html = item.get("resume_html", "")
        company  = job.get("company","Co").replace(" ","_").replace("/","_")[:15]
        title_s  = job.get("title","Role").replace(" ","_").replace("/","_")[:20]
        fname    = f"Resume_{i+1}_{company}_{title_s}.html"
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
        print(f"  ✅ Beautiful email sent → {RECIPIENT}")
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

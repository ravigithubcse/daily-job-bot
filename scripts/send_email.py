#!/usr/bin/env python3
"""
Roy's Daily Job Digest Email — Professional UI v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ATS score badge on every job card
- Company name NEVER shows "N/A" — uses "Confidential Company" fallback
- Proper Walk-In drives section with date/venue
- 13 platform pills in header
- Professional dark-header email layout
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

SOURCE_COLORS = {
    "LinkedIn":           "#0077b5",
    "Naukri":             "#ff7555",
    "Instahire":          "#7c3aed",
    "Wellfound":          "#fb6404",
    "Internshala":        "#00b4d8",
    "TimesJobs":          "#c62828",
    "TimesJobs Walk-In":  "#e65100",
    "Freshersworld":      "#2e7d32",
    "Shine":              "#f59e0b",
    "Indeed India":       "#003a9b",
    "Glassdoor":          "#0caa41",
    "Cutshort":           "#6c63ff",
    "Hirist":             "#00897b",
    "Adzuna India":       "#d84315",
}

PLATFORMS = ["Naukri","LinkedIn","Indeed","TimesJobs","Shine","Glassdoor",
             "Freshersworld","Wellfound","Internshala","Instahire",
             "Cutshort","Hirist","Adzuna"]


def load():
    jobs, tailored = {}, []
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE) as f: jobs = json.load(f)
    if os.path.exists(TAILORED):
        with open(TAILORED) as f: tailored = json.load(f)
    return jobs, tailored


def ats_badge(score):
    score = int(score or 0)
    if score >= 80:
        bg, label = "#1b5e20", "🎯 ATS Match"
    elif score >= 65:
        bg, label = "#0d47a1", "✅ Good Match"
    elif score >= 55:
        bg, label = "#e65100", "🔶 Partial Match"
    else:
        bg, label = "#546e7a", "Match"
    return (f'<span style="background:{bg};color:white;padding:3px 9px;'
            f'border-radius:14px;font-size:10px;font-weight:800">'
            f'{label} {score}%</span>')


def company_display(company, company_type):
    """Never shows N/A — always shows proper name or Confidential Company."""
    co = (company or "").strip()
    if not co or co.lower() in ("n/a", "na", "company name n/a", "unknown", ""):
        co = "Confidential Company"
    icon = {"MNC": "🏢", "Startup": "🚀", "Company": "💼"}.get(company_type, "💼")
    color = {"MNC": "#0d47a1", "Startup": "#4a148c", "Company": "#1b5e20"}.get(company_type, "#1b5e20")
    return f'<span style="color:{color};font-weight:900;font-size:17px">{icon} {co}</span>'


def job_card(job, num):
    is_wi   = job.get("is_walkin", False)
    ct      = job.get("company_type", "Company")
    source  = job.get("source", "")
    src_col = SOURCE_COLORS.get(source, "#546e7a")
    title   = job.get("title", "Role")
    exp     = job.get("experience", "0-2 years (Fresher)")
    score   = job.get("ats_score", 0)
    rec_email = job.get("recruiter_email", "")
    rec_phone = job.get("recruiter_phone", "")

    # Company display
    co_html = company_display(job.get("company", ""), ct)

    # ATS badge
    ats_html = ats_badge(score)

    # Walk-in badge
    wi_badge = ('<span style="background:#e65100;color:white;padding:3px 10px;'
                'border-radius:20px;font-size:10px;font-weight:900">🚶 WALK-IN DRIVE</span>&nbsp;'
                if is_wi else "")

    # Exp badge
    exp_badge = (f'<span style="background:#e8f5e9;color:#2e7d32;padding:3px 10px;'
                 f'border-radius:20px;font-size:10px;font-weight:700;border:1px solid #c8e6c9">'
                 f'⏱ {exp}</span>')

    # Source badge
    src_badge = (f'<span style="background:{src_col};color:white;padding:2px 9px;'
                 f'border-radius:10px;font-size:10px;font-weight:600">{source}</span>')

    # Walk-in info box
    walkin_box = ""
    if is_wi and job.get("walkin_info"):
        walkin_box = (f'<div style="margin:6px 0;padding:6px 12px;background:#fff3e0;'
                      f'border-left:4px solid #e65100;border-radius:6px;'
                      f'font-size:11px;color:#bf360c;font-weight:600">'
                      f'📅 {job["walkin_info"]}</div>')

    skills_row = (f'<div style="margin-top:4px;font-size:11px;color:#546e7a">🔧 {job["skills"]}</div>'
                  if job.get("skills") else "")
    salary_row = (f'<div style="margin-top:3px;font-size:11.5px;color:#2e7d32;font-weight:700">💰 {job["salary"]}</div>'
                  if job.get("salary") else "")

    contact_box = ""
    if rec_email or rec_phone:
        email_part = (f'📧 <a href="mailto:{rec_email}" style="color:#1565c0;font-weight:700;'
                      f'text-decoration:none">{rec_email}</a>&nbsp;&nbsp;' if rec_email else "")
        phone_part = (f'📞 <span style="color:#2e7d32;font-weight:700">{rec_phone}</span>'
                      if rec_phone else "")
        contact_box = (f'<div style="margin-top:7px;padding:7px 12px;background:#e3f2fd;'
                       f'border-left:4px solid #1565c0;border-radius:6px;font-size:11px">'
                       f'{email_part}{phone_part}</div>')

    # Card colour scheme
    if is_wi:      bg, border, shadow = "#fffbf0", "#ffd54f", "0 3px 14px rgba(255,111,0,0.15)"
    elif ct=="MNC":bg, border, shadow = "#f7f9ff", "#c5cae9", "0 2px 10px rgba(26,35,126,0.07)"
    elif ct=="Startup":bg,border,shadow="#faf5ff","#e1bee7","0 2px 10px rgba(106,27,154,0.07)"
    else:          bg, border, shadow = "#ffffff", "#eeeeee", "0 1px 6px rgba(0,0,0,0.05)"

    return f"""
<div style="background:{bg};border:1.5px solid {border};border-radius:14px;
            padding:16px 18px;margin-bottom:12px;box-shadow:{shadow}">
  <!-- Company — prominent, never N/A -->
  <div style="margin-bottom:4px">{co_html}</div>
  <!-- Title + number -->
  <div style="font-size:14px;font-weight:700;color:#1a237e;margin-bottom:8px">{num}. {title}</div>
  <!-- Badges row -->
  <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px;align-items:center">
    {wi_badge}{ats_html}&nbsp;{exp_badge}
  </div>
  <!-- Location -->
  <div style="font-size:12px;color:#546e7a;margin-bottom:3px">
    📍 {job.get("location","Bengaluru, India")}
  </div>
  {walkin_box}{skills_row}{salary_row}{contact_box}
  <!-- Footer -->
  <div style="display:flex;align-items:center;justify-content:space-between;
              margin-top:12px;flex-wrap:wrap;gap:8px">
    <div style="font-size:10.5px;color:#9e9e9e">
      📅 {job.get("posted","Today")} &nbsp;·&nbsp; {src_badge}
    </div>
    <a href="{job.get("link","#")}"
       style="background:linear-gradient(135deg,#1565c0,#1976d2);color:white;
              padding:8px 20px;border-radius:22px;text-decoration:none;
              font-size:12px;font-weight:800;
              box-shadow:0 3px 10px rgba(21,101,192,0.35)">Apply Now →</a>
  </div>
</div>"""


def section_block(label, icon, jobs, c1, c2, cap=None):
    if not jobs: return ""
    shown = jobs[:cap] if cap else jobs
    # Sort by ATS within section
    shown = sorted(shown, key=lambda x: x.get("ats_score", 0), reverse=True)
    cards = "".join(job_card(j, i+1) for i, j in enumerate(shown))
    extra = (f'<p style="text-align:center;font-size:11px;color:#9e9e9e;margin:0 0 8px">'
             f'+ {len(jobs)-cap} more not shown</p>'
             if cap and len(jobs) > cap else "")
    return f"""
<div style="margin-bottom:30px">
  <div style="background:linear-gradient(135deg,{c1},{c2});border-radius:14px;
              padding:13px 20px;margin-bottom:14px;display:flex;align-items:center;
              gap:10px;box-shadow:0 4px 16px rgba(0,0,0,0.12)">
    <span style="font-size:22px">{icon}</span>
    <span style="color:white;font-size:15px;font-weight:900;letter-spacing:0.2px;flex:1">{label}</span>
    <span style="background:rgba(255,255,255,0.22);color:white;padding:4px 13px;
                 border-radius:20px;font-size:12px;font-weight:800">{len(jobs)}</span>
  </div>
  {cards}{extra}
</div>"""


def ai_section(items):
    if not items: return ""
    rows = ""
    for i, item in enumerate(items):
        job = item.get("job", {})
        t   = item.get("tailored", {})
        ct  = job.get("company_type", "")
        icon = "🏢" if ct=="MNC" else ("🚀" if ct=="Startup" else "💼")
        src_col = SOURCE_COLORS.get(job.get("source",""), "#546e7a")
        co = job.get("company","") or "Confidential Company"
        if co.lower() in ("n/a","na","company name n/a",""):
            co = "Confidential Company"
        skills_pills = "".join(
            f'<span style="background:#e8f0fe;color:#1565c0;padding:3px 9px;'
            f'border-radius:12px;font-size:10px;font-weight:700;margin:2px;'
            f'display:inline-block">{s}</span>'
            for s in t.get("top_skills", [])[:5]
        )
        body_html = t.get("email_body", "").replace("\n", "<br>")
        score_html = ats_badge(job.get("ats_score", 0))
        fname = f'Resume_{i+1}_{co.replace(" ","_")[:12]}_{job.get("title","Role").replace(" ","_")[:18]}.html'
        rows += f"""
<div style="background:white;border:1.5px solid #e3f2fd;border-radius:14px;
            padding:18px;margin-bottom:14px;box-shadow:0 2px 10px rgba(21,101,192,0.06)">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:12px">
    <div style="background:linear-gradient(135deg,#1565c0,#1976d2);color:white;
                width:32px;height:32px;border-radius:50%;display:flex;align-items:center;
                justify-content:center;font-size:13px;font-weight:900;flex-shrink:0">{i+1}</div>
    <div style="flex:1">
      <div style="font-weight:900;color:#1a237e;font-size:14px">{job.get("title","")}</div>
      <div style="font-size:11.5px;color:#666;margin-top:2px">
        {icon} {co} &nbsp;·&nbsp;
        <span style="background:{src_col};color:white;padding:1px 8px;border-radius:10px;
                     font-size:10px">{job.get("source","")}</span>
        &nbsp;{score_html}
      </div>
    </div>
  </div>
  <div style="margin-bottom:10px">{skills_pills}</div>
  <div style="background:#f8f9ff;border-radius:10px;padding:11px 14px;margin-bottom:10px">
    <div style="font-size:10px;color:#7986cb;font-weight:800;text-transform:uppercase;
                letter-spacing:0.8px;margin-bottom:4px">📧 Email Subject</div>
    <div style="font-size:12px;color:#1565c0;font-weight:700">{t.get("email_subject","")}</div>
  </div>
  <div style="background:#f8fff8;border:1px solid #c8e6c9;border-radius:10px;
              padding:11px 14px;margin-bottom:10px">
    <div style="font-size:10px;color:#43a047;font-weight:800;text-transform:uppercase;
                letter-spacing:0.8px;margin-bottom:6px">✉️ Cold Email Body</div>
    <div style="font-size:11.5px;color:#2e3d2f;font-family:Georgia,serif;line-height:1.75;
                border-left:3px solid #81c784;padding-left:10px">{body_html}</div>
  </div>
  <div style="background:#e8f5e9;border-radius:8px;padding:8px 12px;
              font-size:11px;color:#2e7d32;font-weight:700">📎 Attached: {fname}</div>
</div>"""

    return f"""
<div style="margin-bottom:30px">
  <div style="background:linear-gradient(135deg,#1b5e20,#388e3c);border-radius:14px;
              padding:13px 20px;margin-bottom:14px;display:flex;align-items:center;
              gap:10px;box-shadow:0 4px 16px rgba(0,0,0,0.12)">
    <span style="font-size:22px">🤖</span>
    <span style="color:white;font-size:15px;font-weight:900;flex:1">AI-Tailored CVs + Cold Emails</span>
    <span style="background:rgba(255,255,255,0.22);color:white;padding:4px 13px;
                 border-radius:20px;font-size:12px;font-weight:800">{len(items)}</span>
  </div>
  {rows}
</div>"""


def build_html(jobs_data, tailored_data):
    today    = datetime.now().strftime("%A, %d %B %Y")
    total    = jobs_data.get("total_found", 0)
    wi_count = jobs_data.get("walkin_count", 0)
    mnc_c    = jobs_data.get("mnc_count", 0)
    st_c     = jobs_data.get("startup_count", 0)
    ats_thr  = jobs_data.get("ats_threshold", 55)

    def stat_box(val, label, bg, highlight=False):
        glow = "box-shadow:0 0 0 2px rgba(255,255,255,0.4);" if highlight and val > 0 else ""
        return (f'<div style="background:{bg};border-radius:12px;padding:12px 18px;'
                f'text-align:center;min-width:68px;{glow}">'
                f'<div style="color:white;font-size:26px;font-weight:900;line-height:1">{val}</div>'
                f'<div style="color:rgba(255,255,255,0.75);font-size:9.5px;font-weight:700;'
                f'margin-top:3px;letter-spacing:0.8px;text-transform:uppercase">{label}</div></div>')

    stats = (
        stat_box(total,   "Total Jobs",     "rgba(255,255,255,0.16)") +
        stat_box(wi_count,"Walk-Ins",       "rgba(230,81,0,0.55)" if wi_count else "rgba(255,255,255,0.1)", True) +
        stat_box(mnc_c,   "MNCs",           "rgba(255,255,255,0.16)") +
        stat_box(st_c,    "Startups",       "rgba(255,255,255,0.16)") +
        stat_box(len(tailored_data), "AI CVs", "rgba(46,125,50,0.55)")
    )

    fs = jobs_data.get("filter_stats", {})
    filter_banner = ""
    if fs:
        filter_banner = f"""
<div style="margin-top:10px;background:rgba(255,255,255,0.1);border-radius:10px;
            padding:8px 14px;display:flex;justify-content:center;gap:16px;flex-wrap:wrap">
  <span style="color:rgba(255,255,255,0.7);font-size:10px">
    🔍 Scraped: <strong style="color:white">{fs.get("total_scraped",0)}</strong></span>
  <span style="color:rgba(255,255,255,0.7);font-size:10px">
    🔄 Dupes removed: <strong style="color:#ffcc80">{fs.get("duplicates_removed",0)}</strong></span>
  <span style="color:rgba(255,255,255,0.7);font-size:10px">
    ❌ Inactive removed: <strong style="color:#ef9a9a">{fs.get("inactive_removed",0)}</strong></span>
  <span style="color:rgba(255,255,255,0.7);font-size:10px">
    🎯 ATS ≥{ats_thr}%: <strong style="color:#a5d6a7">{fs.get("final_sent",total)}</strong></span>
</div>"""

    platform_pills = "".join(
        f'<span style="background:rgba(255,255,255,0.15);color:rgba(255,255,255,0.85);'
        f'padding:3px 10px;border-radius:12px;font-size:10px;font-weight:600;margin:2px">{p}</span>'
        for p in PLATFORMS
    )

    content = ""
    if total == 0:
        content = (f'<div style="background:#fff3e0;border:2px dashed #ffb74d;border-radius:14px;'
                   f'padding:24px;text-align:center;color:#e65100;margin-bottom:24px;'
                   f'font-weight:700;font-size:14px">'
                   f'⚠️ No ATS-matched jobs found today (threshold: {ats_thr}%).<br>'
                   f'<span style="font-size:12px;font-weight:500">Bot retries tomorrow at 8:00 AM IST</span></div>')
    else:
        walkin_jobs  = jobs_data.get("walkin_jobs", [])
        mnc_jobs     = jobs_data.get("mnc_jobs", [])
        startup_jobs = jobs_data.get("startup_jobs", [])
        other_jobs   = jobs_data.get("other_jobs", [])

        # Add fresh jobs indicator in walk-in section title if any posted today
        wi_title = "Walk-In Drives — Bengaluru"
        if walkin_jobs:
            today_wi = [j for j in walkin_jobs if "today" in j.get("posted","").lower()
                        or datetime.now().strftime("%Y-%m-%d") in j.get("posted","")]
            if today_wi:
                wi_title = f"Walk-In Drives — Bengaluru 🔴 {len(today_wi)} NEW Today"

        content = (
            section_block(wi_title, "🚶", walkin_jobs, "#bf360c", "#e64a19") +
            section_block("MNC Openings", "🏢", mnc_jobs, "#1a237e", "#283593") +
            section_block("Startup Openings", "🚀", startup_jobs, "#4a148c", "#6a1b9a") +
            section_block("Other IT Companies", "💼", other_jobs, "#37474f", "#455a64", cap=20) +
            ai_section(tailored_data)
        )

    tips = """
<div style="background:linear-gradient(135deg,#e8eaf6,#e3f2fd);border:1px solid #c5cae9;
            border-radius:14px;padding:18px 20px;margin-bottom:22px">
  <div style="font-size:13px;font-weight:900;color:#1a237e;margin-bottom:12px">💡 Today's Action Plan</div>
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td width="28" style="vertical-align:top;padding-bottom:8px">
      <div style="background:#1565c0;color:white;width:22px;height:22px;border-radius:50%;
                  text-align:center;font-size:11px;font-weight:800;line-height:22px">1</div>
    </td><td style="padding-bottom:8px;padding-left:8px;font-size:12px;color:#37474f">
      Walk-in drives → <strong>go before 9 AM with 3 printed copies</strong> of your resume + originals
    </td></tr>
    <tr><td width="28" style="vertical-align:top;padding-bottom:8px">
      <div style="background:#1565c0;color:white;width:22px;height:22px;border-radius:50%;
                  text-align:center;font-size:11px;font-weight:800;line-height:22px">2</div>
    </td><td style="padding-bottom:8px;padding-left:8px;font-size:12px;color:#37474f">
      High ATS score (≥80%) jobs → <strong>apply first</strong>, these are your best matches
    </td></tr>
    <tr><td width="28" style="vertical-align:top;padding-bottom:8px">
      <div style="background:#1565c0;color:white;width:22px;height:22px;border-radius:50%;
                  text-align:center;font-size:11px;font-weight:800;line-height:22px">3</div>
    </td><td style="padding-bottom:8px;padding-left:8px;font-size:12px;color:#37474f">
      Cold email subject: <em style="color:#1565c0">Java Full Stack Developer | Spring Boot + Angular | 1.5 YOE | Bengaluru</em>
    </td></tr>
    <tr><td width="28" style="vertical-align:top">
      <div style="background:#1565c0;color:white;width:22px;height:22px;border-radius:50%;
                  text-align:center;font-size:11px;font-weight:800;line-height:22px">4</div>
    </td><td style="padding-left:8px;font-size:12px;color:#37474f">
      LinkedIn follow-up after <strong>3 days</strong> → doubles your response rate
    </td></tr>
  </table>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Daily Job Digest — Roy</title>
</head>
<body style="margin:0;padding:0;background:#eef2f7;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif">
<div style="max-width:680px;margin:0 auto;padding:20px 14px">

  <!-- HERO HEADER -->
  <div style="background:linear-gradient(160deg,#0a1463 0%,#1a237e 45%,#1565c0 100%);
              border-radius:20px;padding:30px 24px 26px;margin-bottom:20px;
              text-align:center;box-shadow:0 10px 40px rgba(10,20,99,0.35)">
    <div style="font-size:40px;margin-bottom:8px">☕</div>
    <div style="color:white;font-size:27px;font-weight:900;letter-spacing:-0.5px">Good Morning, Roy!</div>
    <div style="color:rgba(255,255,255,0.65);font-size:13px;margin-top:5px;letter-spacing:0.3px">
      {today} &nbsp;·&nbsp; Your Daily IT Job Digest
    </div>
    <!-- ATS info line -->
    <div style="margin-top:6px;color:rgba(255,255,255,0.5);font-size:10px">
      🎯 ATS-matched vs your Java Full Stack resume &nbsp;·&nbsp;
      Bengaluru only &nbsp;·&nbsp; 0-2 YOE &nbsp;·&nbsp; IT roles only
    </div>
    <!-- Stats Row -->
    <div style="display:flex;justify-content:center;gap:10px;margin-top:22px;flex-wrap:wrap">
      {stats}
    </div>
    <!-- Platforms -->
    <div style="margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.15)">
      <div style="color:rgba(255,255,255,0.5);font-size:9.5px;font-weight:700;
                  text-transform:uppercase;letter-spacing:1px;margin-bottom:7px">
        Searched across 13 IT job platforms
      </div>
      <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:3px">
        {platform_pills}
      </div>
      {filter_banner}
    </div>
  </div>

  <!-- JOB SECTIONS -->
  {content}

  <!-- TIPS -->
  {tips}

  <!-- FOOTER -->
  <div style="text-align:center;padding:8px 0 16px">
    <div style="display:inline-block;background:linear-gradient(135deg,#1a237e,#1565c0);
                border-radius:24px;padding:12px 28px;
                box-shadow:0 4px 16px rgba(26,35,126,0.3)">
      <div style="color:white;font-size:12px;font-weight:800;letter-spacing:0.5px">
        🤖 ROY'S JOB BOT v3.0
      </div>
      <div style="color:rgba(255,255,255,0.65);font-size:10px;margin-top:3px">
        Every day 8:00 AM IST · Java Full Stack · Bengaluru · ATS-filtered · 100% Free
      </div>
    </div>
  </div>

</div>
</body>
</html>"""


def send(html, tailored_data):
    today = datetime.now().strftime("%d %b %Y")
    subj  = f"☕ {today} — IT Jobs Bengaluru | Java Full Stack | ATS-Filtered"
    msg   = MIMEMultipart("mixed")
    msg["Subject"] = subj
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html"))

    for i, item in enumerate(tailored_data[:5]):
        job   = item.get("job", {})
        rhtml = item.get("resume_html", "")
        co    = (job.get("company","") or "Co").replace(" ","_").replace("/","_")[:12]
        if co.lower() in ("n/a","na","company_name_n/a",""):
            co = "Confidential"
        tl    = job.get("title","Role").replace(" ","_").replace("/","_")[:18]
        fname = f"Resume_{i+1}_{co}_{tl}.html"
        part  = MIMEBase("text","html")
        part.set_payload(rhtml.encode("utf-8"))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition","attachment",filename=fname)
        msg.attach(part)

    with open("email_preview.html","w") as f: f.write(html)

    if not APP_PASS:
        print("  ⚠ GMAIL_APP_PASSWORD not set — preview saved only")
        return False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com",465) as srv:
            srv.login(SENDER, APP_PASS)
            srv.sendmail(SENDER, RECIPIENT, msg.as_string())
        print(f"  ✅ Email sent → {RECIPIENT} ({len(tailored_data)} AI resumes attached)")
        return True
    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        return False


def send_digest():
    print(f"\n{'='*55}")
    print(f"  EMAIL SENDER — {datetime.now().strftime('%d %b %Y %I:%M %p')}")
    print(f"{'='*55}\n")
    jobs_data, tailored_data = load()
    html = build_html(jobs_data, tailored_data)
    send(html, tailored_data)

if __name__ == "__main__":
    send_digest()

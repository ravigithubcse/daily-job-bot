#!/usr/bin/env python3
"""
Roy Job Bot — run_all.py
Pipeline: Scrape → Filter (dedup+quality) → Tailor → Send
"""
import subprocess, sys, os, json
from datetime import datetime

def run(label, script):
    print(f"\n{'─'*55}")
    print(f"  ▶ {label}")
    print(f"{'─'*55}")
    r = subprocess.run([sys.executable, f"scripts/{script}"],
                       capture_output=False, text=True)
    ok = r.returncode == 0
    print(f"  {'✅' if ok else '⚠'} {label} finished (exit {r.returncode})")
    return ok

def count_jobs():
    try:
        with open("jobs_found.json") as f: d = json.load(f)
        return d.get("total_found", 0), d.get("filter_stats", {})
    except: return 0, {}

def main():
    print(f"\n{'═'*55}")
    print(f"  🤖 ROY JOB BOT")
    print(f"  {datetime.now().strftime('%A, %d %B %Y — %I:%M %p UTC')}")
    print(f"  Bengaluru | Java Full Stack | 0-2 YOE | Fresh only")
    print(f"{'═'*55}")

    # Step 1: Scrape all platforms
    run("Step 1 — Scraping 12 platforms", "scrape_jobs.py")
    raw, _ = count_jobs()
    print(f"\n  Raw scraped: {raw} jobs")

    # Step 2: Filter — dedup + quality + active check (IMPORTANT!)
    run("Step 2 — Filter: 24h dedup + easy-apply + company limit + active check",
        "job_tracker.py")
    final, stats = count_jobs()
    print(f"  Final after filters: {final} jobs")
    if stats:
        print(f"  Seen 24h: -{stats.get('seen_24h_removed',0)}")
        print(f"  Easy apply: -{stats.get('easy_apply_removed',0)}")
        print(f"  Old jobs: -{stats.get('old_removed',0)}")
        print(f"  Same company: -{stats.get('same_company_removed',0)}")
        print(f"  Inactive: -{stats.get('inactive_removed',0)}")

    # Step 3: Tailor top 5 resumes
    run("Step 3 — Tailoring top 5 resumes", "tailor_resume.py")

    # Step 4: Send email
    run("Step 4 — Sending email digest", "send_email.py")

    print(f"\n{'═'*55}")
    print(f"  ✅ Done! → rn5127610@gmail.com")
    print(f"  {final} fresh unique active IT jobs sent")
    print(f"{'═'*55}\n")

if __name__ == "__main__":
    main()

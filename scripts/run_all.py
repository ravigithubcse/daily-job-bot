#!/usr/bin/env python3
"""
Roy's Job Bot — run_all.py v4.1
Pipeline: Scrape → Tailor → Send (NO job_tracker to avoid seen-job filtering issue)
"""
import subprocess, sys, os, json
from datetime import datetime

def run(name, script):
    print(f"\n{'─'*55}")
    print(f"  ▶ {name}")
    print(f"{'─'*55}")
    result = subprocess.run([sys.executable, f"scripts/{script}"],
                            capture_output=False, text=True)
    ok = result.returncode == 0
    print(f"  {'✅' if ok else '⚠'} {name} {'done' if ok else 'completed with warnings'}")
    return ok

def main():
    print(f"\n{'═'*55}")
    print(f"  🤖 ROY'S JOB BOT v4.1")
    print(f"  {datetime.now().strftime('%A, %d %B %Y — %I:%M %p UTC')}")
    print(f"  Java Full Stack | 0-2 YOE | Bengaluru | 13 Platforms")
    print(f"{'═'*55}")

    # Step 1: Scrape
    run("Scraper — 13 platforms", "scrape_jobs.py")

    # Print scraper result
    try:
        with open("jobs_found.json") as f:
            data = json.load(f)
        total = data.get("total_found", 0)
        print(f"\n  📊 Jobs scraped  : {total}")
        print(f"  🚶 Walk-ins      : {data.get('walkin_count', 0)}")
        print(f"  🏢 MNCs          : {data.get('mnc_count', 0)}")
        print(f"  🚀 Startups      : {data.get('startup_count', 0)}")
        print(f"  💼 Others        : {data.get('other_count', 0)}")
    except Exception as e:
        print(f"  ⚠ Could not read jobs_found.json: {e}")
        total = 0

    # Step 2: Tailor resumes
    run("Resume Tailor — top 5 ATS jobs", "tailor_resume.py")

    # Step 3: Send email
    run("Email Digest — Gmail", "send_email.py")

    print(f"\n{'═'*55}")
    print(f"  ✅ Pipeline done! → rn5127610@gmail.com")
    print(f"  Total jobs sent: {total}")
    print(f"{'═'*55}\n")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Roy's Job Bot — run_all.py
Orchestrates: scrape → tailor → send email
"""
import subprocess, sys, os, json
from datetime import datetime

def run(script, label):
    print(f"\n{'─'*55}")
    print(f"  ▶  {label}")
    print(f"{'─'*55}")
    result = subprocess.run([sys.executable, f"scripts/{script}"],
                            capture_output=False, text=True)
    if result.returncode != 0:
        print(f"  ⚠  {label} exited with code {result.returncode}")
    return result.returncode == 0

def main():
    print(f"\n{'═'*55}")
    print(f"  🤖 ROY'S JOB BOT v4.0")
    print(f"  📅 {datetime.now().strftime('%A %d %B %Y — %I:%M %p UTC')}")
    print(f"{'═'*55}")

    # Step 1: Scrape jobs
    ok1 = run("scrape_jobs.py", "Step 1 — Scraping 13 platforms...")

    # Check what was found
    if os.path.exists("jobs_found.json"):
        with open("jobs_found.json") as f:
            data = json.load(f)
        total = data.get("total_found", 0)
        print(f"\n  📊 Jobs found: {total}")
        print(f"  🚶 Walk-ins  : {data.get('walkin_count', 0)}")
        print(f"  🏢 MNCs      : {data.get('mnc_count', 0)}")
        print(f"  🚀 Startups  : {data.get('startup_count', 0)}")
    else:
        print("  ⚠  jobs_found.json not created — scraper may have failed")
        total = 0

    # Step 2: Tailor resumes
    ok2 = run("tailor_resume.py", "Step 2 — Tailoring resumes for top jobs...")

    # Step 3: Send email
    ok3 = run("send_email.py", "Step 3 — Sending email digest...")

    print(f"\n{'═'*55}")
    print(f"  ✅ Pipeline complete!")
    print(f"  Jobs found : {total}")
    print(f"  Scraper    : {'OK' if ok1 else 'FAILED'}")
    print(f"  Tailor     : {'OK' if ok2 else 'FAILED'}")
    print(f"  Email      : {'OK' if ok3 else 'FAILED'}")
    print(f"{'═'*55}\n")

if __name__ == "__main__":
    main()

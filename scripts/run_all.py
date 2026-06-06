#!/usr/bin/env python3
"""
Roy's Job Bot — Main Orchestrator
100% FREE — No paid APIs
Pipeline: Scrape → Filter (dedup+active) → Tailor → Email
Scheduled daily at 7:00 AM IST via GitHub Actions
"""

import sys, os, subprocess, json
from datetime import datetime


def run(name, script):
    print(f"\n{'─'*55}")
    print(f"  ▶ {name}")
    print(f"{'─'*55}")
    result = subprocess.run([sys.executable, f"scripts/{script}"])
    ok = result.returncode == 0
    print(f"  {'✅' if ok else '⚠'} {name} {'done' if ok else 'completed with warnings'}")
    return ok


def main():
    print(f"\n{'═'*55}")
    print(f"  🤖 ROY'S JOB BOT  (100% FREE)")
    print(f"  {datetime.now().strftime('%A, %d %B %Y — %I:%M %p IST')}")
    print(f"  Java Full Stack | 0-2 YOE | Bengaluru")
    print(f"{'═'*55}")

    # Step 1: Scrape all platforms
    run("Scraper (Naukri, Instahire, LinkedIn, Wellfound, Internshala, TimesJobs, Freshersworld, Shine, Indeed, Glassdoor)", "scrape_jobs.py")

    # Step 2: Filter — remove duplicates + inactive jobs
    run("Filter (Remove duplicates this week + dead job links)", "job_tracker.py")

    # Step 3: Tailor resumes (free keyword-based)
    run("Resume Tailor (free keyword-based, no API)", "tailor_resume.py")

    # Step 4: Send email digest
    run("Email Digest Sender (Gmail)", "send_email.py")

    # Print final count
    try:
        with open("jobs_found.json") as f:
            data = json.load(f)
        stats = data.get("filter_stats", {})
        print(f"\n{'═'*55}")
        print(f"  📊 Final Report:")
        print(f"     Scraped today   : {stats.get('total_scraped', data.get('total_found','?'))}")
        print(f"     Duplicates removed: {stats.get('duplicates_removed', 0)}")
        print(f"     Inactive removed  : {stats.get('inactive_removed', 0)}")
        print(f"     ✅ Sent to email : {stats.get('final_sent', data.get('total_found','?'))} fresh active jobs")
    except Exception:
        pass

    print(f"\n{'═'*55}")
    print(f"  ✅ Done! Check: rn5127610@gmail.com")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()

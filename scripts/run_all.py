#!/usr/bin/env python3
"""
Roy's Job Bot — Main Orchestrator
100% FREE — No paid APIs
Runs: Scrape → Tailor (free) → Email
Scheduled daily at 7:00 AM IST via GitHub Actions
"""

import sys
import subprocess
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

    run("Job Scraper (LinkedIn, Wellfound, Internshala, TimesJobs, Freshersworld)", "scrape_jobs.py")
    run("Resume Tailor (Free keyword-based, no API)", "tailor_resume.py")
    run("Email Digest Sender (Gmail)", "send_email.py")

    print(f"\n{'═'*55}")
    print(f"  ✅ Done! Check: rn5127610@gmail.com")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()

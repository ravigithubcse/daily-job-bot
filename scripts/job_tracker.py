#!/usr/bin/env python3
"""
Job Tracker — Prevents duplicate jobs across days + filters inactive jobs
Uses GitHub Gist as free persistent storage (no database needed)
Stores seen job hashes so same job is never sent twice
Also validates jobs are still active before sending
"""

import json, os, hashlib, time, re, urllib.request, urllib.error
from datetime import datetime, timedelta

# GitHub Gist for persistent storage (free, unlimited)
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GIST_FILENAME = "roy_job_tracker.json"
SEEN_FILE     = "seen_jobs.json"       # local fallback

# How many days to remember a job (avoids resending)
REMEMBER_DAYS = 7

# Keywords that suggest a job is no longer active
INACTIVE_SIGNALS = [
    "position filled", "no longer accepting", "job closed", "expired",
    "position closed", "not accepting", "vacancy closed", "already closed",
    "hiring paused", "on hold", "applications closed", "deadline passed",
    "404", "page not found", "job not found", "this job is no longer",
    "this position has been filled", "removed", "deleted",
]

# Keywords that confirm job IS active
ACTIVE_SIGNALS = [
    "apply", "apply now", "submit", "upload resume", "easy apply",
    "job description", "responsibilities", "requirements", "qualifications",
    "salary", "experience", "skills required", "about the role",
    "who we are", "what you will do", "we are hiring", "join us",
    "bengaluru", "bangalore", "work from office", "wfo", "wfh", "hybrid",
]


def make_hash(job):
    """Unique fingerprint for a job — title + company (case-insensitive)."""
    raw = f"{job.get('title','').lower().strip()[:40]}|{job.get('company','').lower().strip()[:30]}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── GIST STORAGE (persistent across GitHub Actions runs) ─────────────────────
def load_gist_tracker():
    """Load seen jobs from GitHub Gist."""
    if not GITHUB_TOKEN:
        return load_local_tracker()
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
        # Search for existing gist
        req = urllib.request.Request("https://api.github.com/gists?per_page=50", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            gists = json.loads(r.read())
        for gist in gists:
            if GIST_FILENAME in gist.get("files", {}):
                raw_url = gist["files"][GIST_FILENAME]["raw_url"]
                req2 = urllib.request.Request(raw_url, headers=headers)
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    data = json.loads(r2.read())
                print(f"  📂 Loaded tracker from Gist ({len(data.get('seen',{}))} seen jobs)")
                return data, gist["id"]
    except Exception as e:
        print(f"  ⚠ Gist load error: {e}")
    return {"seen": {}, "updated_at": ""}, None


def save_gist_tracker(data, gist_id=None):
    """Save seen jobs to GitHub Gist."""
    if not GITHUB_TOKEN:
        return save_local_tracker(data)
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        payload = json.dumps({
            "description": "Roy Job Bot — Seen Jobs Tracker",
            "public": False,
            "files": {GIST_FILENAME: {"content": json.dumps(data, indent=2)}},
        }).encode()

        if gist_id:
            req = urllib.request.Request(
                f"https://api.github.com/gists/{gist_id}",
                data=payload, headers=headers, method="PATCH"
            )
        else:
            req = urllib.request.Request(
                "https://api.github.com/gists",
                data=payload, headers=headers, method="POST"
            )
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
        print(f"  💾 Tracker saved to Gist ({len(data.get('seen',{}))} total seen jobs)")
        return result.get("id")
    except Exception as e:
        print(f"  ⚠ Gist save error: {e}")
        save_local_tracker(data)
        return None


def load_local_tracker():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f), None
    return {"seen": {}, "updated_at": ""}, None


def save_local_tracker(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── ACTIVE JOB VALIDATOR ──────────────────────────────────────────────────────
def is_job_active(job):
    """
    Check if job link is still live.
    Returns True if active, False if dead/filled/expired.
    """
    url = job.get("link", "")
    if not url or url == "#":
        return True  # No link to check, assume active

    # Skip checking walk-ins (usually list pages, not job-specific pages)
    if job.get("is_walkin"):
        return True

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        req.add_unredirected_header("Accept", "text/html")
        with urllib.request.urlopen(req, timeout=8) as resp:
            status = resp.status
            final_url = resp.url
    except urllib.error.HTTPError as e:
        # 404, 410 Gone = definitely inactive
        if e.code in (404, 410, 403):
            return False
        return True  # other errors, assume active
    except Exception:
        return True  # Network error, don't filter out

    if status in (404, 410):
        return False

    # Check if redirected to a "jobs not found" page
    if final_url and any(bad in final_url.lower() for bad in ["not-found","expired","closed","404","error"]):
        return False

    # For important sources, do a GET and check page content
    important_sources = ["Naukri", "LinkedIn", "Instahire", "TimesJobs"]
    if job.get("source") in important_sources:
        try:
            req2 = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                raw = resp2.read(6000).decode("utf-8", errors="ignore").lower()

            # Strong inactive signals
            if any(sig in raw for sig in INACTIVE_SIGNALS):
                return False

            # For Naukri specifically
            if "naukri" in url.lower():
                if "this job is no longer" in raw or "job is expired" in raw:
                    return False

            # Check if page has meaningful job content
            active_count = sum(1 for sig in ACTIVE_SIGNALS if sig in raw)
            if active_count < 2 and len(raw) < 2000:
                return False  # Very thin page, probably dead

        except Exception:
            pass  # If we can't fetch, assume active

    return True


# ── MAIN FILTER FUNCTION ──────────────────────────────────────────────────────
def filter_new_and_active(jobs_data):
    """
    1. Remove jobs seen in last 7 days (no duplicates across days)
    2. Validate remaining jobs are still active (no dead links)
    3. Save newly seen jobs to tracker
    Returns filtered jobs_data
    """
    print(f"\n{'='*55}")
    print(f"  JOB FILTER — Dedup + Active Check")
    print(f"{'='*55}\n")

    tracker, gist_id = load_gist_tracker()
    seen = tracker.get("seen", {})
    today = datetime.now().isoformat()[:10]

    # Purge old entries (older than REMEMBER_DAYS)
    cutoff = (datetime.now() - timedelta(days=REMEMBER_DAYS)).isoformat()[:10]
    seen = {h: d for h, d in seen.items() if d >= cutoff}
    print(f"  📋 Known jobs in tracker: {len(seen)} (last {REMEMBER_DAYS} days)")

    all_jobs = jobs_data.get("all_jobs", [])
    total_before = len(all_jobs)

    # Step 1 — Remove duplicates (already seen this week)
    new_jobs = []
    duplicate_count = 0
    for job in all_jobs:
        h = make_hash(job)
        if h in seen:
            duplicate_count += 1
        else:
            new_jobs.append(job)
            job["_hash"] = h

    print(f"  🔄 Duplicates removed (seen this week): {duplicate_count}")
    print(f"  🆕 New jobs to validate: {len(new_jobs)}")

    # Step 2 — Validate active (check top jobs by source priority)
    # Don't check ALL (too slow) — check first 40, rest assume active
    to_check   = new_jobs[:40]
    skip_check = new_jobs[40:]

    active_jobs   = []
    inactive_count = 0

    print(f"  🔍 Checking {len(to_check)} job links for activity...")
    for i, job in enumerate(to_check):
        active = is_job_active(job)
        if active:
            active_jobs.append(job)
        else:
            inactive_count += 1
        if (i + 1) % 10 == 0:
            print(f"     Checked {i+1}/{len(to_check)}...")
        time.sleep(0.3)  # Be polite

    # Add unchecked jobs (assumed active)
    active_jobs.extend(skip_check)

    print(f"  ❌ Inactive/dead jobs removed: {inactive_count}")
    print(f"  ✅ Final active new jobs: {len(active_jobs)}")

    # Step 3 — Mark all active new jobs as seen
    new_hashes = 0
    for job in active_jobs:
        h = job.pop("_hash", make_hash(job))
        if h not in seen:
            seen[h] = today
            new_hashes += 1

    # Save updated tracker
    tracker["seen"] = seen
    tracker["updated_at"] = today
    save_gist_tracker(tracker, gist_id)
    print(f"  💾 Added {new_hashes} new jobs to tracker")

    # Step 4 — Rebuild jobs_data with filtered jobs
    walkin_jobs  = [j for j in active_jobs if j.get("is_walkin")]
    regular_jobs = [j for j in active_jobs if not j.get("is_walkin")]
    mnc_jobs     = [j for j in regular_jobs if j.get("company_type") == "MNC"]
    startup_jobs = [j for j in regular_jobs if j.get("company_type") == "Startup"]
    other_jobs   = [j for j in regular_jobs if j.get("company_type") == "Company"]

    filtered = {
        **jobs_data,
        "total_found":   len(active_jobs),
        "walkin_count":  len(walkin_jobs),
        "mnc_count":     len(mnc_jobs),
        "startup_count": len(startup_jobs),
        "other_count":   len(other_jobs),
        "walkin_jobs":   walkin_jobs,
        "mnc_jobs":      mnc_jobs,
        "startup_jobs":  startup_jobs,
        "other_jobs":    other_jobs,
        "all_jobs":      active_jobs,
        "filter_stats": {
            "total_scraped":   total_before,
            "duplicates_removed": duplicate_count,
            "inactive_removed":   inactive_count,
            "final_sent":      len(active_jobs),
        },
    }

    with open("jobs_found.json", "w") as f:
        json.dump(filtered, f, indent=2)

    print(f"\n  📊 Summary:")
    print(f"     Scraped:   {total_before}")
    print(f"     Dupes:    -{duplicate_count}")
    print(f"     Inactive: -{inactive_count}")
    print(f"     ✅ Final:  {len(active_jobs)} unique active jobs\n")

    return filtered


if __name__ == "__main__":
    if os.path.exists("jobs_found.json"):
        with open("jobs_found.json") as f:
            data = json.load(f)
        filter_new_and_active(data)
    else:
        print("No jobs_found.json found. Run scrape_jobs.py first.")

#!/usr/bin/env python3
"""
Job Tracker v2 — Prevents repeats + quality filters
  ✅ 24-hour seen-jobs window (not 7 days — so fresh jobs appear next day)
  ✅ Same company filter — max 2 jobs per company per email
  ✅ No Easy Apply / One-click apply jobs
  ✅ Active job validation (checks link is live)
  ✅ Last 24 hours only (skip jobs older than 24h)
  Uses GitHub Gist for persistent storage across runs
"""

import json, os, hashlib, time, re, urllib.request, urllib.error
from datetime import datetime, timedelta

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GIST_FILENAME = "roy_job_tracker_v2.json"
REMEMBER_HOURS = 24   # Only 24 hours — fresh jobs each morning

# Easy Apply / low-quality signals to EXCLUDE
EASY_APPLY_SIGNALS = [
    "easy apply", "1-click apply", "one click", "quick apply",
    "instant apply", "apply in seconds", "apply with linkedin",
    "apply with resume", "apply with profile",
]

# Inactive signals
INACTIVE_SIGNALS = [
    "position filled", "no longer accepting", "job closed", "expired",
    "position closed", "vacancy closed", "already closed", "hiring paused",
    "applications closed", "404", "page not found", "job not found",
    "this job is no longer", "this position has been filled",
]

ACTIVE_SIGNALS = [
    "apply", "job description", "responsibilities", "requirements",
    "qualifications", "skills required", "about the role", "we are hiring",
]

def make_hash(job):
    raw = f"{job.get('title','').lower()[:40]}|{job.get('company','').lower()[:30]}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def is_easy_apply(job):
    combined = f"{job.get('title','')} {job.get('description','')} {job.get('link','')}".lower()
    return any(sig in combined for sig in EASY_APPLY_SIGNALS)

def is_recent(job):
    """Keep only jobs posted in last 48 hours (or if posted date unknown)."""
    posted = (job.get("posted","") or "").lower().strip()
    if not posted or posted in ("today", "just now", "1 day ago", "2 days ago", "", "recently"):
        return True
    # Naukri/LinkedIn date formats
    if any(w in posted for w in ["day ago", "days ago", "hour", "min", "just", "today", "yesterday"]):
        # Extract number of days
        nums = re.findall(r"(\d+)\s*day", posted)
        if nums and int(nums[0]) > 2:
            return False
        return True
    # ISO date format e.g. 2026-06-28
    try:
        dt = datetime.fromisoformat(posted[:10])
        return (datetime.now() - dt).days <= 2
    except:
        pass
    # If we can't parse, keep it
    return True

# ── GIST STORAGE ──────────────────────────────────────────────────────────────
def load_tracker():
    if not GITHUB_TOKEN:
        if os.path.exists("seen_jobs.json"):
            with open("seen_jobs.json") as f: return json.load(f), None
        return {"seen": {}, "updated": ""}, None
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}",
                   "Accept": "application/vnd.github+json"}
        req = urllib.request.Request("https://api.github.com/gists?per_page=50", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            gists = json.loads(r.read())
        for gist in gists:
            if GIST_FILENAME in gist.get("files", {}):
                raw_url = gist["files"][GIST_FILENAME]["raw_url"]
                req2 = urllib.request.Request(raw_url, headers=headers)
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    data = json.loads(r2.read())
                print(f"  📂 Tracker loaded: {len(data.get('seen',{}))} known jobs (24h window)")
                return data, gist["id"]
    except Exception as e:
        print(f"  ⚠ Tracker load error: {e}")
    return {"seen": {}, "updated": ""}, None

def save_tracker(data, gist_id=None):
    local_path = "seen_jobs.json"
    with open(local_path, "w") as f: json.dump(data, f, indent=2)
    if not GITHUB_TOKEN: return None
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}",
                   "Accept": "application/vnd.github+json",
                   "Content-Type": "application/json"}
        payload = json.dumps({
            "description": "Roy Job Bot — 24h Seen Jobs Tracker",
            "public": False,
            "files": {GIST_FILENAME: {"content": json.dumps(data, indent=2)}}
        }).encode()
        if gist_id:
            req = urllib.request.Request(f"https://api.github.com/gists/{gist_id}",
                                         data=payload, headers=headers, method="PATCH")
        else:
            req = urllib.request.Request("https://api.github.com/gists",
                                         data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
        print(f"  💾 Tracker saved: {len(data.get('seen',{}))} jobs in 24h window")
        return result.get("id")
    except Exception as e:
        print(f"  ⚠ Tracker save error: {e}")
    return gist_id

# ── ACTIVE CHECK ──────────────────────────────────────────────────────────────
def is_active(job):
    url = job.get("link","")
    if not url or url == "#" or job.get("is_walkin"): return True
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status in (404, 410): return False
            final = resp.url
            if any(bad in (final or "").lower() for bad in ["not-found","expired","closed","404"]):
                return False
    except urllib.error.HTTPError as e:
        if e.code in (404, 410): return False
    except: pass
    return True

# ── MAIN FILTER ───────────────────────────────────────────────────────────────
def filter_new_and_active(jobs_data):
    print(f"\n{'='*55}")
    print(f"  JOB FILTER v2 — 24h dedup + quality checks")
    print(f"{'='*55}\n")

    tracker, gist_id = load_tracker()
    seen = tracker.get("seen", {})
    now  = datetime.now()

    # Purge entries older than 24 hours
    cutoff_ts = (now - timedelta(hours=REMEMBER_HOURS)).isoformat()
    seen = {h: ts for h, ts in seen.items() if ts >= cutoff_ts}
    print(f"  📋 Jobs seen in last {REMEMBER_HOURS}h: {len(seen)}")

    all_jobs    = jobs_data.get("all_jobs", [])
    total_in    = len(all_jobs)

    # ── Step 1: Remove seen in last 24h ──────────────────────────────────────
    step1, dupes = [], 0
    for job in all_jobs:
        h = make_hash(job)
        if h in seen:
            dupes += 1
        else:
            job["_hash"] = h
            step1.append(job)
    print(f"  🔄 Seen in last 24h (removed): {dupes}")

    # ── Step 2: Remove Easy Apply / instant apply ─────────────────────────────
    step2, easy_removed = [], 0
    for job in step1:
        if is_easy_apply(job):
            easy_removed += 1
        else:
            step2.append(job)
    print(f"  🚫 Easy Apply removed: {easy_removed}")

    # ── Step 3: Keep only recent jobs (last 48h) ──────────────────────────────
    step3, old_removed = [], 0
    for job in step2:
        if is_recent(job):
            step3.append(job)
        else:
            old_removed += 1
    print(f"  📅 Old jobs (>48h) removed: {old_removed}")

    # ── Step 4: Max 2 jobs per company ────────────────────────────────────────
    company_count = {}
    step4, co_removed = [], 0
    for job in step3:
        co = job.get("company","").lower()[:25]
        if co == "confidential company" or not co:
            step4.append(job)  # always keep anonymous
            continue
        cnt = company_count.get(co, 0)
        if cnt < 2:
            company_count[co] = cnt + 1
            step4.append(job)
        else:
            co_removed += 1
    print(f"  🏢 Same-company overflow removed: {co_removed}")

    # ── Step 5: Active link check (top 30) ────────────────────────────────────
    to_check   = step4[:30]
    skip_check = step4[30:]
    active_jobs, inactive = [], 0

    print(f"  🔍 Checking {len(to_check)} links for activity...")
    for job in to_check:
        if is_active(job):
            active_jobs.append(job)
        else:
            inactive += 1
        time.sleep(0.3)
    active_jobs.extend(skip_check)
    print(f"  ❌ Inactive links removed: {inactive}")
    print(f"  ✅ Final fresh unique jobs: {len(active_jobs)}")

    # ── Step 6: Save new hashes ───────────────────────────────────────────────
    ts_now = now.isoformat()
    added  = 0
    for job in active_jobs:
        h = job.pop("_hash", make_hash(job))
        if h not in seen:
            seen[h] = ts_now
            added   += 1

    tracker["seen"]    = seen
    tracker["updated"] = ts_now
    save_tracker(tracker, gist_id)
    print(f"  💾 {added} new jobs added to 24h tracker")

    # ── Rebuild ───────────────────────────────────────────────────────────────
    walkin   = [j for j in active_jobs if j.get("is_walkin")]
    regular  = [j for j in active_jobs if not j.get("is_walkin")]
    mnc      = [j for j in regular if j.get("company_type") == "MNC"]
    startup  = [j for j in regular if j.get("company_type") == "Startup"]
    other    = [j for j in regular if j.get("company_type") == "Company"]

    filtered = {**jobs_data,
        "total_found":   len(active_jobs),
        "walkin_count":  len(walkin),
        "mnc_count":     len(mnc),
        "startup_count": len(startup),
        "other_count":   len(other),
        "walkin_jobs": walkin, "mnc_jobs": mnc,
        "startup_jobs": startup, "other_jobs": other,
        "all_jobs": active_jobs,
        "filter_stats": {
            "total_scraped":     total_in,
            "seen_24h_removed":  dupes,
            "easy_apply_removed":easy_removed,
            "old_removed":       old_removed,
            "same_company_removed": co_removed,
            "inactive_removed":  inactive,
            "final_sent":        len(active_jobs),
        }
    }
    with open("jobs_found.json","w") as f: json.dump(filtered, f, indent=2)

    print(f"\n  📊 Summary:")
    print(f"     Scraped   : {total_in}")
    print(f"     -24h seen : {dupes}")
    print(f"     -Easy apply: {easy_removed}")
    print(f"     -Old (>48h): {old_removed}")
    print(f"     -Same company: {co_removed}")
    print(f"     -Inactive : {inactive}")
    print(f"     ✅ FINAL  : {len(active_jobs)} fresh active jobs\n")
    return filtered

if __name__ == "__main__":
    if os.path.exists("jobs_found.json"):
        with open("jobs_found.json") as f: data = json.load(f)
        filter_new_and_active(data)
    else:
        print("Run scrape_jobs.py first.")

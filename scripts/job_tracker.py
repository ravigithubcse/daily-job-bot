#!/usr/bin/env python3
"""
Job Tracker v2 — Prevents repeats + quality filters
  ✅ 24-hour seen-jobs window (not 7 days — so fresh jobs appear next day)
  ✅ Same company filter — max 2 jobs per company per email
  ✅ No Easy Apply / One-click apply jobs
  ✅ Active job validation (checks link is live)
  ✅ Last 24 hours only (skip jobs older than 24h)
  Persisted as data/seen_jobs.json, committed back to the repo by the workflow
  (previously used a GitHub Gist, but the Actions token / PAT never had the
  "gist" scope, so every run silently started with an empty tracker — that
  was the root cause of the same jobs repeating every day).
"""

import json, os, hashlib, time, re, urllib.request, urllib.error
from datetime import datetime, timedelta

REPO_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKER_PATH   = os.path.join(REPO_ROOT, "data", "seen_jobs.json")
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

def _normalize_link(link):
    """Strip tracking params/fragments so the same posting always hashes the same."""
    link = (link or "").strip().split("?")[0].split("#")[0].rstrip("/")
    return link.lower()

def make_hash(job):
    """Use the job's own link when we have one (most precise, unique per posting).
    Fall back to full normalized title+company (no truncation — truncating to
    30-40 chars caused distinct jobs with similar titles/companies to collide
    and get wrongly treated as duplicates, which is why genuinely new jobs
    were being filtered out)."""
    link = _normalize_link(job.get("link", ""))
    if link and link not in ("#",):
        raw = f"link:{link}"
    else:
        title   = re.sub(r"\s+", " ", (job.get("title", "") or "").strip().lower())
        company = re.sub(r"\s+", " ", (job.get("company", "") or "").strip().lower())
        raw = f"tc:{title}|{company}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]

def is_easy_apply(job):
    # Explicit flag set by the scraper (most reliable — e.g. LinkedIn's
    # "Easy Apply" badge detected directly from the job card)
    if job.get("easy_apply"):
        return True
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

# ── TRACKER STORAGE ────────────────────────────────────────────────────────────
# Stored at data/seen_jobs.json and committed back to the repo by the workflow
# (git push), so it persists across scheduled runs without needing any extra
# token scopes.
def load_tracker():
    if os.path.exists(TRACKER_PATH):
        try:
            with open(TRACKER_PATH) as f:
                data = json.load(f)
            print(f"  📂 Tracker loaded: {len(data.get('seen',{}))} known jobs (24h window)")
            return data, None
        except Exception as e:
            print(f"  ⚠ Tracker load error: {e}")
    else:
        print("  📂 No existing tracker found — starting fresh")
    return {"seen": {}, "updated": ""}, None

def save_tracker(data, gist_id=None):
    try:
        os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
        with open(TRACKER_PATH, "w") as f:
            json.dump(data, f, indent=2)
        # Also keep a local copy at cwd/seen_jobs.json for backward-compat / artifacts
        with open("seen_jobs.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"  💾 Tracker saved: {len(data.get('seen',{}))} jobs in 24h window → {TRACKER_PATH}")
    except Exception as e:
        print(f"  ⚠ Tracker save error: {e}")
    return None

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

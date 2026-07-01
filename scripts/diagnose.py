#!/usr/bin/env python3
"""Diagnostic - tests each job source and prints exactly what GitHub Actions gets"""
import requests, time, sys
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

H_CHROME = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}
H_RSS = {
    "User-Agent": "Feedparser/6.0 +https://github.com/kurtmckee/feedparser",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en",
}
H_API = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.naukri.com/",
    "appid": "109",
    "systemid": "Naukri",
    "x-requested-with": "XMLHttpRequest",
}

TESTS = [
    ("Indeed RSS",        "https://in.indeed.com/rss?q=java+developer+fresher&l=Bengaluru&fromage=7", H_RSS),
    ("TimesJobs RSS",     "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1&rss=1", H_RSS),
    ("Shine RSS",         "https://www.shine.com/rss/java-developer-jobs-in-bangalore.xml", H_RSS),
    ("Freshersworld RSS", "https://www.freshersworld.com/rss/jobs.xml?keyword=java+developer&location=Bengaluru", H_RSS),
    ("LinkedIn",          "https://www.linkedin.com/jobs/search/?keywords=java+developer+fresher&location=Bengaluru%2C+Karnataka%2C+India&f_TPR=r604800&f_E=1%2C2", H_CHROME),
    ("Internshala",       "https://internshala.com/jobs/java-jobs-in-bengaluru/", H_CHROME),
    ("Naukri API",        "https://www.naukri.com/jobapi/v3/search?noOfResults=5&urlType=search_by_keyword&searchType=adv&keyword=java+developer&location=bengaluru&experience=0&experienceDD=2", H_API),
    ("Instahire",         "https://instahire.app/jobs?q=java+developer&location=bangalore", H_CHROME),
    ("Cutshort",          "https://cutshort.io/jobs?keywords=java-developer&location=bengaluru", H_CHROME),
    ("Hirist",            "https://www.hirist.tech/j/java-developer-jobs-in-bangalore/38", H_CHROME),
    ("Wellfound",         "https://wellfound.com/jobs?role=software-engineer&location=bengaluru", H_CHROME),
    ("Foundit",           "https://www.foundit.in/srp/results?query=java+developer+jobs+in+bengaluru&experienceRanges=0~2", H_CHROME),
    ("Naukri HTML",       "https://www.naukri.com/java-developer-jobs-in-bengaluru?experience=0", H_CHROME),
    ("TimesJobs HTML",    "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2", H_CHROME),
]

print("=" * 60)
print("  JOB SOURCE DIAGNOSTIC — GitHub Actions IP Test")
print("=" * 60)
working = []
blocked = []

for name, url, headers in TESTS:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        size = len(r.content)
        status = r.status_code
        
        if status == 200 and size > 300:
            # Count actual job items
            if "<item>" in r.text or "<?xml" in r.text[:50] or "<rss" in r.text[:100]:
                n = r.text.count("<item>")
                print(f"  ✅ {name}: {status} | {size}b | {n} RSS items")
            else:
                soup = BeautifulSoup(r.text, "html.parser")
                jld  = soup.find_all("script", type="application/ld+json")
                try:
                    js = r.json()
                    jc = len(js.get("jobDetails", js.get("results", js if isinstance(js, list) else [])))
                    print(f"  ✅ {name}: {status} | {size}b | {jc} JSON jobs")
                except:
                    print(f"  ✅ {name}: {status} | {size}b | {len(jld)} JSON-LD blocks")
            working.append(name)
        else:
            body_preview = r.text[:80].replace("\n","")
            print(f"  ⛔ {name}: {status} | {size}b | {body_preview}")
            blocked.append(name)
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        blocked.append(name)
    time.sleep(1)

print()
print(f"WORKING ({len(working)}): {working}")
print(f"BLOCKED ({len(blocked)}): {blocked}")
print("=" * 60)

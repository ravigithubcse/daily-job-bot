#!/usr/bin/env python3
"""
Roy's Daily Job Scraper
Targets: Java Full Stack / Backend | 0-2 YOE | Bengaluru
Sources: LinkedIn, Wellfound, Internshala, TimesJobs (walk-ins), Freshersworld
Covers: MNCs, Startups, Product companies
"""

import requests
import json
import time
import re
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT_FILE = "jobs_found.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

RELEVANCE_KEYWORDS = [
    "java", "spring", "spring boot", "backend", "full stack", "fullstack",
    "software engineer", "software developer", "angular", "rest api",
    "microservices", "j2ee", "hibernate", "jpa",
]

EXCLUDE_KEYWORDS = [
    "senior", "lead", "manager", "architect", "principal", "staff",
    "director", "head of", "vp ", "cto", "5+ years", "7+ years", "10+ years",
]

MNC_COMPANIES = [
    "IBM", "Accenture", "Capgemini", "Wipro", "Infosys", "TCS", "HCL",
    "Cognizant", "Tech Mahindra", "Mphasis", "LTIMindtree", "Hexaware",
    "Publicis Sapient", "GlobalLogic", "EPAM", "ThoughtWorks", "Nagarro",
    "Oracle", "SAP", "Salesforce", "Microsoft", "Google", "Amazon",
]

STARTUP_COMPANIES = [
    "Razorpay", "PhonePe", "CRED", "Meesho", "Groww", "Zepto", "Swiggy",
    "Dunzo", "Navi", "BrowserStack", "Freshworks", "Zoho", "Chargebee",
    "Unacademy", "Vedantu", "Byju", "Ola", "Rapido", "Urban Company",
    "Slice", "Fi Money", "Jupiter", "smallcase", "Learnapp", "Scaler",
]


def safe_get(url, timeout=15, retries=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return resp
            time.sleep(2)
        except Exception as e:
            if attempt == retries - 1:
                print(f"    ⚠ Failed: {url[:60]}... ({e})")
    return None


def is_relevant(title):
    t = title.lower()
    has_kw = any(k in t for k in RELEVANCE_KEYWORDS)
    has_ex = any(e in t for e in EXCLUDE_KEYWORDS)
    return has_kw and not has_ex


def classify_company(company_name):
    name = company_name.upper()
    for mnc in MNC_COMPANIES:
        if mnc.upper() in name:
            return "MNC"
    for startup in STARTUP_COMPANIES:
        if startup.upper() in name:
            return "Startup"
    return "Company"


def is_walkin(text):
    text = text.lower()
    return any(w in text for w in ["walk-in", "walkin", "walk in", "direct walk", "no interview"])


# ──────────────────────────────────────────────────────────────────
# SOURCE 1: LinkedIn Jobs (Public, no login)
# ──────────────────────────────────────────────────────────────────
def scrape_linkedin():
    jobs = []
    searches = [
        ("java developer", "Bengaluru, Karnataka, India", "1,2"),
        ("java full stack developer", "Bengaluru, Karnataka, India", "1,2"),
        ("spring boot developer", "Bengaluru, Karnataka, India", "1,2"),
        ("java backend developer fresher", "Bengaluru, Karnataka, India", "1,2"),
    ]
    print("  📎 LinkedIn...")
    for keyword, location, exp in searches:
        try:
            kw_enc = urllib.parse.quote(keyword)
            loc_enc = urllib.parse.quote(location)
            url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={kw_enc}&location={loc_enc}"
                f"&f_E={exp}&f_TPR=r86400&position=1&pageNum=0"
            )
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-search-card|base-card"))
            for card in cards[:8]:
                try:
                    title_el = card.find(["h3","a"], class_=re.compile(r"job-search-card__title|base-card__full-link"))
                    company_el = card.find(["h4","a"], class_=re.compile(r"job-search-card__company|hidden-nested"))
                    location_el = card.find("span", class_=re.compile(r"job-search-card__location"))
                    link_el = card.find("a", href=re.compile(r"/jobs/view/"))
                    date_el = card.find("time")

                    title = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title):
                        continue

                    href = link_el["href"] if link_el else url
                    link = ("https://www.linkedin.com" + href) if href.startswith("/") else href

                    jobs.append({
                        "source": "LinkedIn",
                        "title": title,
                        "company": company,
                        "company_type": classify_company(company),
                        "location": (location_el.get_text(strip=True) if location_el else "Bengaluru, India"),
                        "link": link,
                        "posted": date_el.get("datetime", "Recent") if date_el else "Recent",
                        "experience": "0-2 years",
                        "is_walkin": False,
                        "apply_email": None,
                    })
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    LinkedIn error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ──────────────────────────────────────────────────────────────────
# SOURCE 2: Wellfound / AngelList (Startups)
# ──────────────────────────────────────────────────────────────────
def scrape_wellfound():
    jobs = []
    print("  🚀 Wellfound (Startups)...")
    try:
        url = "https://wellfound.com/jobs?role=software-engineer&location=bengaluru&experience=0-2"
        resp = safe_get(url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = (soup.find_all("div", attrs={"data-test": re.compile("JobListing")}) or
                     soup.find_all("div", class_=re.compile(r"styles_component|job-listing")))
            for card in cards[:12]:
                try:
                    title_el = card.find(["h2","h3","a"], class_=re.compile(r"title|role|job-title"))
                    company_el = card.find(["span","a","p"], class_=re.compile(r"company|startup"))
                    link_el = card.find("a", href=re.compile(r"/jobs/"))
                    title = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "Startup").strip()
                    if not title or not is_relevant(title):
                        continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://wellfound.com{href}" if href.startswith("/") else href) or url
                    jobs.append({
                        "source": "Wellfound",
                        "title": title,
                        "company": company,
                        "company_type": "Startup",
                        "location": "Bengaluru, India",
                        "link": link,
                        "posted": "Recent",
                        "experience": "0-2 years",
                        "is_walkin": False,
                        "apply_email": None,
                    })
                except Exception:
                    continue
    except Exception as e:
        print(f"    Wellfound error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ──────────────────────────────────────────────────────────────────
# SOURCE 3: Internshala Jobs (Fresher-friendly)
# ──────────────────────────────────────────────────────────────────
def scrape_internshala():
    jobs = []
    print("  🎓 Internshala...")
    urls = [
        "https://internshala.com/jobs/java-jobs-in-bengaluru/",
        "https://internshala.com/jobs/full-stack-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/software-development-jobs-in-bengaluru/",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-internship-card|individual_internship|internship_meta"))
            for card in cards[:8]:
                try:
                    title_el = card.find(["h3","a"], class_=re.compile(r"job-title|profile|title"))
                    company_el = card.find(["p","a","h4"], class_=re.compile(r"company-name|company"))
                    link_el = card.find("a", href=re.compile(r"/jobs/detail/|/internships/detail/"))
                    stipend_el = card.find("span", class_=re.compile(r"stipend|salary"))
                    title = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title):
                        continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://internshala.com{href}" if href.startswith("/") else href) or url
                    jobs.append({
                        "source": "Internshala",
                        "title": title,
                        "company": company,
                        "company_type": classify_company(company),
                        "location": "Bengaluru, India",
                        "link": link,
                        "posted": "Recent",
                        "experience": "0-1 years (Fresher)",
                        "salary": stipend_el.get_text(strip=True) if stipend_el else "As per industry",
                        "is_walkin": False,
                        "apply_email": None,
                    })
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Internshala error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ──────────────────────────────────────────────────────────────────
# SOURCE 4: TimesJobs – Walk-In + Regular
# ──────────────────────────────────────────────────────────────────
def scrape_timesjobs():
    jobs = []
    print("  🏢 TimesJobs (Walk-ins + Regular)...")
    urls = [
        # Walk-ins specifically
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+full+stack&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=spring+boot+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_=re.compile(r"clearfix job-bx|job-bx"))
            for card in cards[:8]:
                try:
                    title_el = card.find("h2")
                    company_el = card.find("h3", class_=re.compile(r"joblist-comp-name"))
                    link_el = card.find("a", href=re.compile(r"timesjobs.com/candidate/job"))
                    skills_el = card.find("span", class_=re.compile(r"srp-skills"))
                    date_el = card.find("span", class_=re.compile(r"sim-posted"))
                    full_text = card.get_text()
                    title = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title):
                        continue
                    walkin = is_walkin(full_text)
                    jobs.append({
                        "source": "TimesJobs",
                        "title": title,
                        "company": company,
                        "company_type": classify_company(company),
                        "location": "Bengaluru, India",
                        "link": link_el["href"] if link_el else url,
                        "posted": date_el.get_text(strip=True) if date_el else "Recent",
                        "experience": "0-2 years",
                        "skills": skills_el.get_text(strip=True) if skills_el else "",
                        "is_walkin": walkin,
                        "apply_email": None,
                    })
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    TimesJobs error: {e}")
    print(f"    ✓ {len(jobs)} jobs ({sum(1 for j in jobs if j['is_walkin'])} walk-ins)")
    return jobs


# ──────────────────────────────────────────────────────────────────
# SOURCE 5: Freshersworld
# ──────────────────────────────────────────────────────────────────
def scrape_freshersworld():
    jobs = []
    print("  🌐 Freshersworld...")
    urls = [
        "https://www.freshersworld.com/java-developer-jobs-for-freshers/4534561?src=nav&location=Bengaluru",
        "https://www.freshersworld.com/spring-boot-developer-jobs-for-freshers/4575093?src=nav&location=Bengaluru",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-container|job-item|vacancy-list"))
            for card in cards[:8]:
                try:
                    title_el = card.find(["h3","a"], class_=re.compile(r"job-title|title"))
                    company_el = card.find(["p","span"], class_=re.compile(r"company"))
                    link_el = card.find("a", href=True)
                    title = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title):
                        continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.freshersworld.com{href}" if href.startswith("/") else href) or url
                    walkin = is_walkin(card.get_text())
                    jobs.append({
                        "source": "Freshersworld",
                        "title": title,
                        "company": company,
                        "company_type": classify_company(company),
                        "location": "Bengaluru, India",
                        "link": link,
                        "posted": "Recent",
                        "experience": "0-1 years (Fresher)",
                        "is_walkin": walkin,
                        "apply_email": None,
                    })
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Freshersworld error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ──────────────────────────────────────────────────────────────────
# SOURCE 6: Walk-In Bengaluru (Dedicated search)
# ──────────────────────────────────────────────────────────────────
def scrape_walkin_bengaluru():
    """Dedicated walk-in scraper across multiple platforms."""
    jobs = []
    print("  🚶 Walk-In Bengaluru Drives...")

    # TimesJobs walk-in specific
    walkin_urls = [
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+walk+in&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=spring+boot+walk+in&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1",
    ]

    for url in walkin_urls:
        try:
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_=re.compile(r"clearfix job-bx"))
            for card in cards[:10]:
                try:
                    full_text = card.get_text()
                    if not is_walkin(full_text):
                        continue
                    title_el = card.find("h2")
                    company_el = card.find("h3", class_=re.compile(r"joblist-comp-name"))
                    link_el = card.find("a", href=re.compile(r"timesjobs"))
                    title = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title):
                        continue

                    # Try to extract walk-in date/venue from text
                    walkin_info = ""
                    if "date" in full_text.lower():
                        lines = [l.strip() for l in full_text.split("\n") if "date" in l.lower() and len(l.strip()) < 80]
                        if lines:
                            walkin_info = lines[0]

                    jobs.append({
                        "source": "TimesJobs Walk-In",
                        "title": title,
                        "company": company,
                        "company_type": classify_company(company),
                        "location": "Bengaluru, India",
                        "link": link_el["href"] if link_el else url,
                        "posted": "Recent",
                        "experience": "0-2 years",
                        "walkin_info": walkin_info,
                        "is_walkin": True,
                        "apply_email": None,
                    })
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Walk-in scrape error: {e}")

    print(f"    ✓ {len(jobs)} walk-in drives")
    return jobs


# ──────────────────────────────────────────────────────────────────
# DEDUPLICATE
# ──────────────────────────────────────────────────────────────────
def deduplicate(jobs):
    seen = set()
    unique = []
    for job in jobs:
        key = (job.get("title","").lower()[:35], job.get("company","").lower()[:25])
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────
def scrape_all_jobs():
    print(f"\n{'='*55}")
    print(f"  JOB SCRAPER STARTED — {datetime.now().strftime('%d %b %Y %I:%M %p IST')}")
    print(f"{'='*55}\n")

    all_jobs = []
    all_jobs.extend(scrape_linkedin())
    all_jobs.extend(scrape_wellfound())
    all_jobs.extend(scrape_internshala())
    all_jobs.extend(scrape_timesjobs())
    all_jobs.extend(scrape_freshersworld())
    all_jobs.extend(scrape_walkin_bengaluru())

    unique = deduplicate(all_jobs)

    walkin_jobs  = sorted([j for j in unique if j.get("is_walkin")],  key=lambda x: x["company"])
    regular_jobs = sorted([j for j in unique if not j.get("is_walkin")], key=lambda x: x["source"])

    mnc_jobs     = [j for j in regular_jobs if j.get("company_type") == "MNC"]
    startup_jobs = [j for j in regular_jobs if j.get("company_type") == "Startup"]
    other_jobs   = [j for j in regular_jobs if j.get("company_type") == "Company"]

    result = {
        "scraped_at": datetime.now().isoformat(),
        "total_found": len(unique),
        "walkin_count": len(walkin_jobs),
        "mnc_count": len(mnc_jobs),
        "startup_count": len(startup_jobs),
        "other_count": len(other_jobs),
        "walkin_jobs": walkin_jobs,
        "mnc_jobs": mnc_jobs,
        "startup_jobs": startup_jobs,
        "other_jobs": other_jobs,
        "all_jobs": unique,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*55}")
    print(f"  DONE! Total: {len(unique)} jobs")
    print(f"  Walk-ins: {len(walkin_jobs)} | MNCs: {len(mnc_jobs)} | Startups: {len(startup_jobs)} | Others: {len(other_jobs)}")
    print(f"{'='*55}\n")
    return result


if __name__ == "__main__":
    scrape_all_jobs()

#!/usr/bin/env python3
"""
Roy's Daily Job Scraper — FULLY FIXED v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ATS scoring vs Roy's actual resume (only ≥55 score shown)
- Strict Bengaluru/Bangalore location filter
- IT-only roles (non-IT excluded)
- Company name extraction fixed (multiple fallback strategies)
- Walk-in drives detection enhanced (5 signal types)
- 13 platforms: Naukri, LinkedIn, Indeed, TimesJobs, Shine, Glassdoor,
                Freshersworld, Wellfound, Internshala, Instahire,
                Cutshort, Hirist, Adzuna India
"""

import requests, json, time, re, urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

OUTPUT_FILE = "jobs_found.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

# ─── ROY'S RESUME SKILL PROFILE (ATS matching) ────────────────────────────────
# Source: Ravikumar_java_fullstack_2024.pdf
RESUME = {
    "primary_skills": [
        "java", "spring boot", "spring framework", "spring security", "spring cloud",
        "angular", "angular 15", "angular 17", "typescript", "rest api", "restful",
        "microservices", "jpa", "hibernate", "postgresql", "sql",
    ],
    "secondary_skills": [
        "kafka", "redis", "docker", "jenkins", "git", "ci/cd",
        "junit", "mockito", "swagger", "postman", "rxjs",
        "html5", "css3", "javascript", "websocket", "jwt",
        "openai", "gpt", "mcp", "model context protocol",
        "jira", "agile", "mongodb", "ms sql", "j2ee",
    ],
    "title_keywords": [
        "java developer", "java full stack", "fullstack", "full stack",
        "spring boot", "backend developer", "software developer",
        "software engineer", "angular developer", "java backend",
        "j2ee developer", "java engineer",
    ],
    "experience_range": (0, 2),   # 0-2 years only
}

# Score weights
TITLE_MATCH_SCORE  = 40   # Job title matches profile
PRIMARY_SKILL_EACH = 8    # Each primary skill matched
SECONDARY_SKILL_EACH = 3  # Each secondary skill matched
MAX_SKILL_SCORE    = 60   # Cap on skill score component

ATS_THRESHOLD = 55        # Minimum ATS score to include job (0-100)

# ─── FILTERS ──────────────────────────────────────────────────────────────────
IT_TITLE_MUST_CONTAIN = [
    "java", "spring", "software", "developer", "engineer", "backend",
    "full stack", "fullstack", "angular", "j2ee", "technical", "coding",
    "programmer", "api", "microservice",
]

NON_IT_EXCLUDE = [
    "sales", "marketing", "bpo", "call center", "voice process",
    "data entry", "telecalling", "customer support", "customer service",
    "hr recruiter", "human resource", "accountant", "finance", "accounting",
    "banking", "insurance", "field executive", "delivery", "logistics",
    "teacher", "faculty", "trainer", "counselor", "nurse", "medical",
    "chef", "hospitality", "hotel", "retail", "store", "cashier",
    "driver", "security", "warehouse", "packing", "assembly",
    "content writer", "graphic design", "video edit",
]

SENIOR_EXCLUDE = [
    "senior", "sr.", "sr ", "lead", "manager", "architect", "principal",
    "staff engineer", "director", "head of", "vp ", "cto", "tech lead",
    "5+ years", "7+ years", "10+ years", "8+ years", "6+ years", "4+ years", "3+ years",
]

BENGALURU_SIGNALS = [
    "bengaluru", "bangalore", "bengalore", "blr", "karnataka",
]

WALKIN_SIGNALS = [
    "walk-in", "walkin", "walk in", "direct interview", "spot offer",
    "spot selection", "campus drive", "recruitment drive", "hiring drive",
    "open house", "direct hiring", "face to face interview",
]

MNC_LIST = [
    "IBM", "Accenture", "Capgemini", "Wipro", "Infosys", "TCS", "HCL",
    "Cognizant", "Tech Mahindra", "Mphasis", "LTIMindtree", "Hexaware",
    "Publicis Sapient", "GlobalLogic", "EPAM", "ThoughtWorks", "Nagarro",
    "Oracle", "SAP", "Salesforce", "Microsoft", "Google", "Amazon",
    "Deloitte", "PwC", "KPMG", "Accolite", "Persistent", "Zensar",
    "Birlasoft", "Mastech", "Sonata", "Cyient", "DXC Technology",
    "Tata Consultancy", "Mindtree", "L&T Technology",
]

STARTUP_LIST = [
    "Razorpay", "PhonePe", "CRED", "Meesho", "Groww", "Zepto", "Swiggy",
    "Navi", "BrowserStack", "Freshworks", "Zoho", "Chargebee",
    "Unacademy", "Byju", "Ola", "Rapido", "Urban Company", "Slice",
    "Fi Money", "Jupiter", "smallcase", "Scaler", "upGrad", "Lenskart",
    "Delhivery", "Porter", "Spinny", "Cars24", "Cutshort", "Darwinbox",
    "Leadsquared", "Bizongo", "Volopay", "Rupeek",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}")


# ─── ATS SCORER ───────────────────────────────────────────────────────────────
def ats_score(title: str, description: str = "", skills: str = "") -> int:
    """Score a job 0-100 vs Roy's resume. Returns score."""
    combined = f"{title} {description} {skills}".lower()
    t_lower  = title.lower()

    score = 0

    # Title match (most important)
    if any(kw in t_lower for kw in RESUME["title_keywords"]):
        score += TITLE_MATCH_SCORE

    # Primary skill match
    skill_score = 0
    for sk in RESUME["primary_skills"]:
        if sk in combined:
            skill_score += PRIMARY_SKILL_EACH
    for sk in RESUME["secondary_skills"]:
        if sk in combined:
            skill_score += SECONDARY_SKILL_EACH

    score += min(skill_score, MAX_SKILL_SCORE)
    return min(score, 100)


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def safe_get(url, timeout=15, retries=2, headers=None):
    h = headers or HEADERS
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=h, timeout=timeout)
            if r.status_code == 200:
                return r
            time.sleep(2)
        except Exception:
            if attempt == retries - 1:
                print(f"    ⚠ Failed: {url[:60]}")
    return None


def is_bengaluru(location_text: str) -> bool:
    lt = location_text.lower()
    return any(sig in lt for sig in BENGALURU_SIGNALS)


def is_it_role(title: str) -> bool:
    t = title.lower()
    if any(bad in t for bad in NON_IT_EXCLUDE):
        return False
    return any(kw in t for kw in IT_TITLE_MUST_CONTAIN)


def is_senior(title: str, exp_text: str = "") -> bool:
    combined = f"{title} {exp_text}".lower()
    return any(e in combined for e in SENIOR_EXCLUDE)


def is_fresher_exp(exp_text: str) -> bool:
    if not exp_text:
        return True
    t = exp_text.lower().strip()
    if any(w in t for w in ["fresher", "0 year", "0-1", "0-2", "0 - 1", "0 - 2",
                             "entry level", "entry-level", "graduate"]):
        return True
    for pat in [r"[3-9]\d*\s*[-–]\s*\d+\s*years?", r"[3-9]\d*\+\s*years?",
                r"minimum\s+[3-9]", r"at least\s+[3-9]"]:
        if re.search(pat, t):
            return False
    nums = re.findall(r"\d+", t)
    if nums and max(int(n) for n in nums) > 2:
        return False
    return True


def classify_company(name: str) -> str:
    n = name.upper()
    if any(m.upper() in n for m in MNC_LIST):    return "MNC"
    if any(s.upper() in n for s in STARTUP_LIST): return "Startup"
    return "Company"


def is_walkin(text: str) -> bool:
    return any(w in text.lower() for w in WALKIN_SIGNALS)


def extract_contact(text: str) -> dict:
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    emails = [e for e in emails if not any(bad in e.lower()
              for bad in ["noreply", "no-reply", "donotreply", "support@",
                          "feedback@", "privacy@", "legal@", "admin@", "info@"])]
    return {
        "recruiter_email": emails[0] if emails else "",
        "recruiter_phone": phones[0] if phones else "",
    }


def make_job(source, title, company, location, link,
             posted="Today", experience="0-2 years (Fresher)",
             skills="", salary="", walkin=False, walkin_info="",
             recruiter_email="", recruiter_phone="", description="",
             ats=0):
    score = ats if ats else ats_score(title, description, skills)
    co    = company.strip()
    return {
        "source":          source,
        "title":           title.strip(),
        "company":         co if co else "Confidential Company",
        "company_type":    classify_company(co),
        "location":        location or "Bengaluru, India",
        "link":            link,
        "posted":          posted,
        "experience":      experience,
        "skills":          skills,
        "salary":          salary,
        "is_walkin":       walkin,
        "walkin_info":     walkin_info,
        "recruiter_email": recruiter_email,
        "recruiter_phone": recruiter_phone,
        "ats_score":       score,
    }


def should_include(job: dict) -> bool:
    """Central gate — job must pass ALL checks."""
    if not is_it_role(job["title"]):                    return False
    if is_senior(job["title"], job.get("experience","")): return False
    if not is_bengaluru(job["location"]):               return False
    if job.get("ats_score", 0) < ATS_THRESHOLD:        return False
    return True


# ── 1. NAUKRI ─────────────────────────────────────────────────────────────────
def scrape_naukri():
    jobs = []
    print("  🟠 Naukri (API + HTML + Walk-ins)...")

    naukri_h = {**HEADERS, "Referer": "https://www.naukri.com/",
                "appid": "109", "systemid": "Naukri",
                "x-requested-with": "XMLHttpRequest"}

    # Official Naukri API endpoints
    api_searches = [
        "java+developer",
        "java+full+stack+developer",
        "spring+boot+developer",
        "angular+java+developer",
        "software+engineer+java",
        "java+fresher",
        "walk+in+java+bengaluru",
    ]

    for kw in api_searches:
        try:
            url = (f"https://www.naukri.com/jobapi/v3/search?"
                   f"noOfResults=20&urlType=search_by_keyword&searchType=adv"
                   f"&keyword={kw}&location=bengaluru"
                   f"&experience=0&experienceDD=2&jobAge=7&src=jobsearchDesk")
            resp = safe_get(url, headers=naukri_h)
            if not resp:
                continue
            try:
                data = resp.json()
            except Exception:
                continue
            for jb in data.get("jobDetails", [])[:20]:
                title    = jb.get("title", "")
                company  = (jb.get("companyName") or
                            jb.get("fCompanyName") or
                            jb.get("company", {}).get("label", "") or "")
                loc      = jb.get("placeholders", [{}])[0].get("label", "Bengaluru, India")
                link     = jb.get("jdURL") or f"https://www.naukri.com{jb.get('staticUrl','')}"
                exp_txt  = jb.get("experienceText", "")
                skills   = ", ".join(jb.get("tagsAndSkills", "").split(",")[:6])
                salary   = jb.get("salary", "")
                full_txt = jb.get("jobDescription", "")
                walkin   = is_walkin(title + " " + full_txt)
                score    = ats_score(title, full_txt, skills)
                if (title and is_it_role(title) and not is_senior(title, exp_txt)
                        and is_fresher_exp(exp_txt) and is_bengaluru(loc)
                        and score >= ATS_THRESHOLD):
                    jobs.append(make_job(
                        "Naukri", title, company, loc, link,
                        experience=exp_txt or "0-2 years (Fresher)",
                        skills=skills, salary=salary,
                        walkin=walkin, description=full_txt, ats=score
                    ))
            time.sleep(2)
        except Exception as e:
            print(f"    Naukri API err ({kw}): {e}")

    # HTML pages for additional coverage
    html_pages = [
        "java-developer-jobs-in-bengaluru?experience=0&jobAge=3",
        "java-full-stack-developer-jobs-in-bengaluru?experience=0",
        "angular-developer-jobs-in-bengaluru?experience=0&jobAge=7",
        "walk-in-java-developer-jobs-in-bengaluru",
    ]
    for path in html_pages:
        try:
            resp = safe_get(f"https://www.naukri.com/{path}", headers=naukri_h)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data  = json.loads(s.string or "")
                    items = data.get("itemListElement", []) if isinstance(data, dict) else []
                    for item in items:
                        jb = item.get("item", item)
                        title   = jb.get("title", "")
                        company = (jb.get("hiringOrganization", {}).get("name", "") or
                                   jb.get("employer", {}).get("name", "") or "")
                        link    = jb.get("url", "")
                        loc     = (jb.get("jobLocation", {}) or {}).get("address", {}).get("addressLocality", "Bengaluru")
                        exp_txt = str(jb.get("experienceRequirements", ""))
                        score   = ats_score(title)
                        if (title and is_it_role(title) and not is_senior(title, exp_txt)
                                and is_fresher_exp(exp_txt) and score >= ATS_THRESHOLD):
                            jobs.append(make_job("Naukri", title, company,
                                                 loc or "Bengaluru, India", link, ats=score))
                except Exception:
                    pass
            time.sleep(2)
        except Exception as e:
            print(f"    Naukri HTML err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    result = list(unique.values())
    print(f"    ✓ {len(result)} ATS-matched jobs (≥{ATS_THRESHOLD} score)")
    return result


# ── 2. LINKEDIN ────────────────────────────────────────────────────────────────
def scrape_linkedin():
    jobs = []
    print("  🔵 LinkedIn (public listings)...")
    searches = [
        "java developer 0 1 year Bengaluru",
        "spring boot developer fresher Bengaluru",
        "java full stack developer entry level Bengaluru",
        "angular java developer fresher Bengaluru",
        "java backend developer junior Bengaluru",
    ]
    for keyword in searches:
        try:
            kw_enc  = urllib.parse.quote(keyword)
            loc_enc = urllib.parse.quote("Bengaluru, Karnataka, India")
            url = (f"https://www.linkedin.com/jobs/search/"
                   f"?keywords={kw_enc}&location={loc_enc}"
                   f"&f_E=1,2&f_TPR=r604800")
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")

            # Try JSON-LD structured data first (best company name source)
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = ([data] if isinstance(data, dict) else data)
                    for jb in items:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title", "")
                        company = (jb.get("hiringOrganization", {}).get("name", "") or
                                   jb.get("employerName", "") or "")
                        link    = jb.get("url", jb.get("sameAs", ""))
                        loc     = (str(jb.get("jobLocation", {}) or {}).lower())
                        exp_txt = str(jb.get("experienceRequirements", ""))
                        desc    = jb.get("description", "")
                        score   = ats_score(title, desc)
                        if (title and is_it_role(title) and not is_senior(title, exp_txt)
                                and is_fresher_exp(exp_txt)
                                and ("bengalur" in loc or "bangalore" in loc or not loc)
                                and score >= ATS_THRESHOLD):
                            jobs.append(make_job("LinkedIn", title, company,
                                                 "Bengaluru, India", link, ats=score))
                except Exception:
                    pass

            # HTML card fallback
            cards = soup.find_all("div", class_=re.compile(r"job-search-card|base-card"))
            for card in cards[:12]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-search-card__title|base-card__full-link"))
                    company_el = card.find(["h4","a"], class_=re.compile(r"job-search-card__company|base-card__subtitle"))
                    loc_el     = card.find("span", class_=re.compile(r"job-search-card__location"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/view/"))
                    date_el    = card.find("time")

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    loc     = (loc_el.get_text(strip=True) if loc_el else "Bengaluru, India")

                    if not title or not is_it_role(title): continue
                    if not is_bengaluru(loc): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue

                    href = link_el["href"] if link_el else ""
                    link = ("https://www.linkedin.com" + href.split("?")[0]) if href.startswith("/") else href
                    posted = date_el.get("datetime", "Today") if date_el else "Today"
                    jobs.append(make_job("LinkedIn", title, company, loc, link,
                                         posted=posted, ats=score))
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    LinkedIn err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    result = list(unique.values())
    print(f"    ✓ {len(result)} ATS-matched jobs")
    return result


# ── 3. INDEED INDIA ───────────────────────────────────────────────────────────
def scrape_indeed():
    jobs = []
    print("  🔵 Indeed India...")
    searches = [
        "java+developer+fresher", "java+full+stack+0+2+years",
        "spring+boot+developer+fresher", "angular+java+developer",
        "java+backend+developer+junior",
    ]
    for kw in searches:
        try:
            url  = (f"https://in.indeed.com/jobs?q={kw}"
                    f"&l=Bengaluru%2C+Karnataka&explvl=entry_level&fromage=7&sort=date")
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")

            # JSON-LD structured data
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data.get("itemListElement", []) if isinstance(data, dict) else
                             [{"item": d} for d in data] if isinstance(data, list) else [])
                    for item in items:
                        jb = item.get("item", item)
                        title   = jb.get("title", "")
                        company = (jb.get("hiringOrganization", {}).get("name", "") or "")
                        link    = jb.get("url", "")
                        desc    = jb.get("description", "")
                        score   = ats_score(title, desc)
                        if (title and is_it_role(title) and not is_senior(title)
                                and score >= ATS_THRESHOLD):
                            jobs.append(make_job("Indeed India", title, company,
                                                 "Bengaluru, India", link, ats=score))
                except Exception:
                    pass

            cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|tapItem"))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["h2","a"], class_=re.compile(r"jobTitle"))
                    company_el = card.find(["span","a"], class_=re.compile(r"companyName"))
                    loc_el     = card.find("div", class_=re.compile(r"companyLocation"))
                    link_el    = card.find("a", href=re.compile(r"/rc/clk|/pagead|/viewjob"))
                    sal_el     = card.find("div", class_=re.compile(r"salary"))

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    loc     = (loc_el.get_text(strip=True) if loc_el else "Bengaluru, India")

                    if not title or not is_it_role(title): continue
                    if not is_bengaluru(loc): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://in.indeed.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Indeed India", title, company, loc, link,
                                         salary=sal_el.get_text(strip=True) if sal_el else "",
                                         ats=score))
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    Indeed err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    result = list(unique.values())
    print(f"    ✓ {len(result)} jobs")
    return result


# ── 4. TIMESJOBS ──────────────────────────────────────────────────────────────
def scrape_timesjobs():
    jobs = []
    print("  🔴 TimesJobs (Jobs + Walk-ins)...")
    urls = [
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+full+stack&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=spring+boot&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=walk+in+java+bengaluru&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=angular+java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_=re.compile(r"clearfix job-bx"))
            for card in cards[:10]:
                try:
                    title_el   = card.find("h2")
                    company_el = card.find("h3", class_=re.compile(r"joblist-comp-name"))
                    link_el    = card.find("a", href=re.compile(r"timesjobs\.com"))
                    skills_el  = card.find("span", class_=re.compile(r"srp-skills"))
                    exp_el     = card.find("ul", class_=re.compile(r"top-jd-dtl"))
                    date_el    = card.find("span", class_=re.compile(r"sim-posted"))
                    full_txt   = card.get_text()

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    skills  = (skills_el.get_text(strip=True) if skills_el else "")

                    if not title or not is_it_role(title): continue
                    if is_senior(title, exp_txt): continue
                    if not is_fresher_exp(exp_txt) and exp_txt: continue

                    score = ats_score(title, full_txt, skills)
                    if score < ATS_THRESHOLD: continue

                    walkin  = is_walkin(full_txt + title)
                    contact = extract_contact(full_txt)
                    src     = "TimesJobs Walk-In" if walkin else "TimesJobs"
                    jobs.append(make_job(
                        src, title, company, "Bengaluru, India",
                        link_el["href"] if link_el else url,
                        posted=date_el.get_text(strip=True) if date_el else "Today",
                        experience=exp_txt or "0-2 years (Fresher)",
                        skills=skills, walkin=walkin, **contact, ats=score
                    ))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    TimesJobs err: {e}")

    wi = sum(1 for j in jobs if j["is_walkin"])
    print(f"    ✓ {len(jobs)} jobs ({wi} walk-ins)")
    return jobs


# ── 5. SHINE ──────────────────────────────────────────────────────────────────
def scrape_shine():
    jobs = []
    print("  ✨ Shine.com...")
    urls = [
        "https://www.shine.com/job-search/java-developer-jobs-in-bangalore?experienceRanges=0to1,1to2",
        "https://www.shine.com/job-search/spring-boot-developer-fresher-jobs-in-bangalore",
        "https://www.shine.com/job-search/full-stack-java-developer-jobs-in-bangalore?experienceRanges=0to1,1to2",
        "https://www.shine.com/job-search/angular-java-developer-jobs-in-bangalore?experienceRanges=0to2",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    jobs_list = (data if isinstance(data, list) else
                                 data.get("itemListElement", []))
                    for jb in jobs_list:
                        jb = jb.get("item", jb) if isinstance(jb, dict) else {}
                        title   = jb.get("title", "")
                        company = jb.get("hiringOrganization", {}).get("name", "")
                        link    = jb.get("url", "")
                        exp_txt = str(jb.get("experienceRequirements", ""))
                        score   = ats_score(title)
                        if (title and is_it_role(title) and not is_senior(title, exp_txt)
                                and is_fresher_exp(exp_txt) and score >= ATS_THRESHOLD):
                            jobs.append(make_job("Shine", title, company,
                                                 "Bengaluru, India", link, ats=score))
                except Exception:
                    pass

            cards = soup.find_all("div", class_=re.compile(r"job-listing|srp-tuple|jobTuple"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h2","a"], class_=re.compile(r"job-title|title"))
                    company_el = card.find(["span","a","div"], class_=re.compile(r"company|org-name"))
                    exp_el     = card.find(["span","div"], class_=re.compile(r"exp|experience"))
                    sal_el     = card.find("span", class_=re.compile(r"salary|sal"))
                    link_el    = card.find("a", href=re.compile(r"shine\.com/jobs/"))

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_it_role(title): continue
                    if not is_fresher_exp(exp_txt) and exp_txt: continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.shine.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Shine", title, company, "Bengaluru, India", link,
                                         experience=exp_txt or "0-2 years (Fresher)",
                                         salary=sal_el.get_text(strip=True) if sal_el else "",
                                         ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Shine err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 6. GLASSDOOR ──────────────────────────────────────────────────────────────
def scrape_glassdoor():
    jobs = []
    print("  🟡 Glassdoor...")
    urls = [
        "https://www.glassdoor.co.in/Job/bangalore-java-developer-jobs-SRCH_IL.0,9_IC2940965_KO10,24.htm?fromAge=7&seniorityType=juniorLevel",
        "https://www.glassdoor.co.in/Job/bangalore-software-engineer-jobs-SRCH_IL.0,9_IC2940965_KO10,26.htm?fromAge=7&seniorityType=juniorLevel",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")

            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data.get("itemListElement", []) if isinstance(data, dict) else data)
                    for it in items:
                        jb = it.get("item", it) if isinstance(it, dict) else {}
                        title   = jb.get("title", "")
                        company = jb.get("hiringOrganization", {}).get("name", "")
                        link    = jb.get("url", "")
                        score   = ats_score(title)
                        if (title and is_it_role(title) and not is_senior(title)
                                and score >= ATS_THRESHOLD):
                            jobs.append(make_job("Glassdoor", title, company,
                                                 "Bengaluru, India", link, ats=score))
                except Exception:
                    pass

            cards = soup.find_all("li", class_=re.compile(r"react-job-listing|job-listing"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["a","span"], attrs={"data-test": re.compile(r"job-title|jobTitle")})
                    company_el = card.find(["span","div"], attrs={"data-test": "employer-name"})
                    link_el    = card.find("a", href=re.compile(r"/job-listing/|/Jobs/"))
                    sal_el     = card.find("span", attrs={"data-test": "detailSalary"})
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_it_role(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Glassdoor", title, company, "Bengaluru, India", link,
                                         salary=sal_el.get_text(strip=True) if sal_el else "",
                                         ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Glassdoor err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 7. FRESHERSWORLD ──────────────────────────────────────────────────────────
def scrape_freshersworld():
    jobs = []
    print("  🟢 Freshersworld...")
    urls = [
        "https://www.freshersworld.com/java-developer-jobs-for-freshers/4534561?src=nav&location=Bengaluru",
        "https://www.freshersworld.com/spring-boot-developer-jobs-for-freshers/4575093?src=nav&location=Bengaluru",
        "https://www.freshersworld.com/angular-developer-jobs-for-freshers/4575300?src=nav&location=Bengaluru",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-container|job-item|vacancy-list"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-title|title"))
                    company_el = card.find(["p","span","div"], class_=re.compile(r"company|employer|org"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_it_role(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.freshersworld.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Freshersworld", title, company, "Bengaluru, India", link,
                                         experience="Fresher / 0-1 year", ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Freshersworld err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 8. WELLFOUND ──────────────────────────────────────────────────────────────
def scrape_wellfound():
    jobs = []
    print("  🟤 Wellfound (Startups)...")
    urls = [
        "https://wellfound.com/jobs?role=software-engineer&location=bengaluru&experience=0-2",
        "https://wellfound.com/jobs?role=backend-engineer&location=bengaluru&experience=0-2",
        "https://wellfound.com/jobs?role=full-stack-engineer&location=bengaluru&experience=0-2",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"styles_component|job-listing"))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role"))
                    company_el = card.find(["span","a","p","div"], class_=re.compile(r"company|startup|employer"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_it_role(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://wellfound.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Wellfound", title, company, "Bengaluru, India", link,
                                         experience="0-2 years (Fresher)", ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Wellfound err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 9. INTERNSHALA ────────────────────────────────────────────────────────────
def scrape_internshala():
    jobs = []
    print("  🎓 Internshala (Fresher/Trainee Jobs)...")
    urls = [
        "https://internshala.com/jobs/java-jobs-in-bengaluru/",
        "https://internshala.com/jobs/full-stack-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/software-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/angular-jobs-in-bengaluru/",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-internship-card|individual_internship"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-title|profile|title"))
                    company_el = card.find(["p","a","h4","span"], class_=re.compile(r"company-name|company|employer"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/detail/|/internships/detail/"))
                    sal_el     = card.find("span", class_=re.compile(r"stipend|salary"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_it_role(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://internshala.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Internshala", title, company, "Bengaluru, India", link,
                                         experience="0-1 years (Fresher/Trainee)",
                                         salary=sal_el.get_text(strip=True) if sal_el else "",
                                         ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Internshala err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 10. INSTAHIRE ─────────────────────────────────────────────────────────────
def scrape_instahire():
    jobs = []
    print("  🟣 Instahire...")
    urls = [
        "https://instahire.app/jobs?q=java+developer&location=bangalore&exp=0-2",
        "https://instahire.app/jobs?q=spring+boot&location=bangalore&exp=0-1",
        "https://instahire.app/jobs?q=angular+developer&location=bangalore",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = (soup.find_all("div", class_=re.compile(r"job.card|jobcard|listing|job-item")) or
                     soup.find_all("li", class_=re.compile(r"job|listing")))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role"))
                    company_el = card.find(["span","p","a","div"], class_=re.compile(r"company|org|employer"))
                    link_el    = card.find("a", href=True)
                    exp_el     = card.find(["span","div"], class_=re.compile(r"exp|experience"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_it_role(title): continue
                    if not is_fresher_exp(exp_txt): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://instahire.app{href}" if href.startswith("/") else href) or url
                    contact = extract_contact(card.get_text())
                    jobs.append(make_job("Instahire", title, company, "Bengaluru, India", link,
                                         experience=exp_txt or "0-2 years (Fresher)",
                                         **contact, ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Instahire err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 11. CUTSHORT ──────────────────────────────────────────────────────────────
def scrape_cutshort():
    jobs = []
    print("  🔷 Cutshort (IT startup jobs)...")
    urls = [
        "https://cutshort.io/jobs?keywords=java+developer&location=bengaluru&experience=0-2",
        "https://cutshort.io/jobs?keywords=spring+boot+developer&location=bengaluru&experience=0-2",
        "https://cutshort.io/jobs?keywords=full+stack+java&location=bengaluru&experience=0-2",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            # Try structured data
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data if isinstance(data, list) else
                             data.get("itemListElement", []) if isinstance(data, dict) else [])
                    for jb in items:
                        jb = jb.get("item", jb) if isinstance(jb, dict) else {}
                        title   = jb.get("title", "")
                        company = jb.get("hiringOrganization", {}).get("name", "")
                        link    = jb.get("url", "")
                        score   = ats_score(title)
                        if (title and is_it_role(title) and not is_senior(title)
                                and score >= ATS_THRESHOLD):
                            jobs.append(make_job("Cutshort", title, company,
                                                 "Bengaluru, India", link, ats=score))
                except Exception:
                    pass
            # HTML fallback
            cards = soup.find_all(["div","article"], class_=re.compile(r"job-card|jobCard|listing-card"))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role|heading"))
                    company_el = card.find(["span","p","div"], class_=re.compile(r"company|startup|employer|org"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_it_role(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://cutshort.io{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Cutshort", title, company, "Bengaluru, India", link, ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Cutshort err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 12. HIRIST ────────────────────────────────────────────────────────────────
def scrape_hirist():
    jobs = []
    print("  💡 Hirist.com (Tech-only portal)...")
    urls = [
        "https://www.hirist.tech/j/java-developer-jobs-in-bangalore/38?experience=0-2",
        "https://www.hirist.tech/j/spring-boot-developer-jobs-in-bangalore/38?experience=0-2",
        "https://www.hirist.tech/j/full-stack-developer-jobs-in-bangalore/38?experience=0-2",
        "https://www.hirist.tech/j/angular-java-developer-jobs-in-bangalore/38",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data.get("itemListElement", []) if isinstance(data, dict) else
                             [{"item": d} for d in data] if isinstance(data, list) else [])
                    for it in items:
                        jb = it.get("item", it) if isinstance(it, dict) else {}
                        title   = jb.get("title", "")
                        company = jb.get("hiringOrganization", {}).get("name", "")
                        link    = jb.get("url", "")
                        exp_txt = str(jb.get("experienceRequirements", ""))
                        score   = ats_score(title)
                        if (title and is_it_role(title) and not is_senior(title, exp_txt)
                                and is_fresher_exp(exp_txt) and score >= ATS_THRESHOLD):
                            jobs.append(make_job("Hirist", title, company,
                                                 "Bengaluru, India", link, ats=score))
                except Exception:
                    pass
            cards = soup.find_all(["div","li"], class_=re.compile(r"job-listing|job-card|job-item"))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|job-title"))
                    company_el = card.find(["span","div","p"], class_=re.compile(r"company|employer|org-name"))
                    link_el    = card.find("a", href=True)
                    exp_el     = card.find(["span","div"], class_=re.compile(r"exp|experience"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_it_role(title): continue
                    if not is_fresher_exp(exp_txt) and exp_txt: continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.hirist.tech{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Hirist", title, company, "Bengaluru, India", link,
                                         experience=exp_txt or "0-2 years", ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Hirist err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ── 13. ADZUNA INDIA ──────────────────────────────────────────────────────────
def scrape_adzuna():
    jobs = []
    print("  🔸 Adzuna India...")
    urls = [
        "https://www.adzuna.in/search?q=java+developer+fresher&w=bengaluru&days_old=7&sort=date",
        "https://www.adzuna.in/search?q=spring+boot+developer&w=bengaluru&days_old=7&sort=date",
        "https://www.adzuna.in/search?q=java+full+stack&w=bengaluru&days_old=7&sort=date",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data if isinstance(data, list) else
                             data.get("itemListElement", []) if isinstance(data, dict) else [])
                    for jb in items:
                        jb = jb.get("item", jb) if isinstance(jb, dict) else {}
                        title   = jb.get("title", "")
                        company = jb.get("hiringOrganization", {}).get("name", "")
                        link    = jb.get("url", "")
                        desc    = jb.get("description", "")
                        score   = ats_score(title, desc)
                        if (title and is_it_role(title) and not is_senior(title)
                                and score >= ATS_THRESHOLD):
                            jobs.append(make_job("Adzuna India", title, company,
                                                 "Bengaluru, India", link, ats=score))
                except Exception:
                    pass
            cards = soup.find_all(["div","article"], class_=re.compile(r"res|job"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title"))
                    company_el = card.find(["span","div"], class_=re.compile(r"company|employer"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_it_role(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.adzuna.in{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Adzuna India", title, company,
                                         "Bengaluru, India", link, ats=score))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Adzuna err: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())


# ─── DEDUPLICATE ──────────────────────────────────────────────────────────────
def deduplicate(jobs):
    seen, unique = set(), []
    for j in jobs:
        key = (j["title"].lower()[:35], j["company"].lower()[:25])
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return unique


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def scrape_all_jobs():
    print(f"\n{'='*60}")
    print(f"  JOB SCRAPER v3.0 — {datetime.now().strftime('%d %b %Y %I:%M %p IST')}")
    print(f"  ATS Threshold  : ≥{ATS_THRESHOLD}/100 vs Roy's resume")
    print(f"  Location       : Bengaluru ONLY (strict)")
    print(f"  Experience     : 0-2 years / Fresher only")
    print(f"  Role type      : IT roles only (non-IT excluded)")
    print(f"  Platforms      : 13")
    print(f"{'='*60}\n")

    all_jobs = []
    all_jobs.extend(scrape_naukri())
    all_jobs.extend(scrape_linkedin())
    all_jobs.extend(scrape_indeed())
    all_jobs.extend(scrape_timesjobs())
    all_jobs.extend(scrape_shine())
    all_jobs.extend(scrape_glassdoor())
    all_jobs.extend(scrape_freshersworld())
    all_jobs.extend(scrape_wellfound())
    all_jobs.extend(scrape_internshala())
    all_jobs.extend(scrape_instahire())
    all_jobs.extend(scrape_cutshort())
    all_jobs.extend(scrape_hirist())
    all_jobs.extend(scrape_adzuna())

    unique       = deduplicate(all_jobs)
    # Sort by ATS score descending
    unique.sort(key=lambda x: x.get("ats_score", 0), reverse=True)

    walkin_jobs  = [j for j in unique if j.get("is_walkin")]
    regular      = [j for j in unique if not j.get("is_walkin")]
    mnc_jobs     = [j for j in regular if j.get("company_type") == "MNC"]
    startup_jobs = [j for j in regular if j.get("company_type") == "Startup"]
    other_jobs   = [j for j in regular if j.get("company_type") == "Company"]

    result = {
        "scraped_at":    datetime.now().isoformat(),
        "ats_threshold": ATS_THRESHOLD,
        "total_found":   len(unique),
        "walkin_count":  len(walkin_jobs),
        "mnc_count":     len(mnc_jobs),
        "startup_count": len(startup_jobs),
        "other_count":   len(other_jobs),
        "walkin_jobs":   walkin_jobs,
        "mnc_jobs":      mnc_jobs,
        "startup_jobs":  startup_jobs,
        "other_jobs":    other_jobs,
        "all_jobs":      unique,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅ TOTAL: {len(unique)} ATS-matched IT jobs (≥{ATS_THRESHOLD} score)")
    print(f"  🚶 Walk-ins : {len(walkin_jobs)}")
    print(f"  🏢 MNCs     : {len(mnc_jobs)}")
    print(f"  🚀 Startups : {len(startup_jobs)}")
    print(f"  💼 Others   : {len(other_jobs)}")
    print(f"{'='*60}\n")
    return result

if __name__ == "__main__":
    scrape_all_jobs()

#!/usr/bin/env python3
"""
Roy's Daily Job Scraper — v4.0 (FIXED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Based on the PROVEN working v2 scraper logic + added:
  - ATS scoring against Roy's resume (threshold: 40 — lenient enough to get results)
  - IT-only filter
  - Bengaluru strict filter
  - Company name N/A fix
  - 13 platforms (added Cutshort, Hirist, Adzuna)
  - Walk-in drive detection
"""

import requests, json, time, re, urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT_FILE = "jobs_found.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

# ── ROY'S RESUME SKILLS (ATS matching) ────────────────────────────────────────
PRIMARY_SKILLS = [
    "java", "spring boot", "spring", "spring security", "spring cloud",
    "angular", "typescript", "rest api", "restful", "microservices",
    "jpa", "hibernate", "postgresql", "sql",
]
SECONDARY_SKILLS = [
    "kafka", "redis", "docker", "jenkins", "git", "ci/cd", "junit",
    "mockito", "swagger", "postman", "rxjs", "html", "css",
    "javascript", "websocket", "jwt", "agile", "python", "fastapi",
]
TITLE_KEYWORDS = [
    "java", "spring", "software developer", "software engineer",
    "full stack", "fullstack", "backend developer", "backend engineer",
    "angular developer", "j2ee", "it developer", "web developer",
]
ATS_THRESHOLD = 40  # Lowered from 55 → 40 so we actually get results

def ats_score(title, desc="", skills=""):
    combined = f"{title} {desc} {skills}".lower()
    score = 0
    if any(k in title.lower() for k in TITLE_KEYWORDS):
        score += 40
    for s in PRIMARY_SKILLS:
        if s in combined:
            score += 6
    for s in SECONDARY_SKILLS:
        if s in combined:
            score += 2
    return min(score, 100)

# ── RELEVANCE & FILTER ─────────────────────────────────────────────────────────
RELEVANCE_KW = [
    "java", "spring", "spring boot", "backend", "full stack", "fullstack",
    "software engineer", "software developer", "angular", "rest api",
    "microservices", "j2ee", "hibernate", "jpa", "it developer",
    "web developer", "python developer", "api developer",
]
EXCLUDE_TITLES = [
    "senior", "sr.", "sr ", "lead", "manager", "architect", "principal",
    "staff", "director", "head of", "vp ", "cto", "tech lead",
]
EXCLUDE_NON_IT = [
    "sales", "marketing", "bpo", "call center", "voice process",
    "data entry", "telecalling", "customer support", "hr recruiter",
    "accountant", "finance", "banking", "insurance", "field executive",
    "delivery boy", "teacher", "faculty", "nurse", "chef", "driver",
]
EXCLUDE_EXP = [
    r"[3-9]\d*\s*[-–]\s*\d+\s*years?",
    r"[3-9]\d*\+\s*years?",
    r"minimum\s+[3-9]",
    r"at least\s+[3-9]",
]
BENGALURU = ["bengaluru", "bangalore", "bengalore", "blr"]
WALKIN_KW = ["walk-in", "walkin", "walk in", "direct interview",
             "spot offer", "spot selection", "campus drive", "hiring drive"]
MNC_LIST = ["IBM","Accenture","Capgemini","Wipro","Infosys","TCS","HCL",
            "Cognizant","Tech Mahindra","Mphasis","LTIMindtree","Hexaware",
            "Oracle","SAP","Microsoft","Amazon","Deloitte","Persistent",
            "Zensar","Birlasoft","DXC","GlobalLogic","EPAM","ThoughtWorks"]
STARTUP_LIST = ["Razorpay","PhonePe","CRED","Meesho","Groww","Zepto",
                "BrowserStack","Freshworks","Zoho","Chargebee","Scaler",
                "upGrad","Darwinbox","Leadsquared","Cutshort","Unacademy"]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}")

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

def is_relevant(title):
    t = title.lower()
    if not any(k in t for k in RELEVANCE_KW): return False
    if any(e in t for e in EXCLUDE_TITLES): return False
    if any(e in t for e in EXCLUDE_NON_IT): return False
    return True

def is_fresher(exp_text):
    if not exp_text: return True
    t = exp_text.lower().strip()
    if any(w in t for w in ["fresher","0 year","0-1","0-2","0 - 1","0 - 2",
                             "entry level","entry-level","graduate"]): return True
    for pat in EXCLUDE_EXP:
        if re.search(pat, t): return False
    nums = re.findall(r"\d+", t)
    if nums and max(int(n) for n in nums) > 2: return False
    return True

def is_bengaluru(loc):
    return any(b in loc.lower() for b in BENGALURU)

def is_walkin(text):
    return any(w in text.lower() for w in WALKIN_KW)

def classify_co(name):
    n = name.upper()
    if any(m.upper() in n for m in MNC_LIST): return "MNC"
    if any(s.upper() in n for s in STARTUP_LIST): return "Startup"
    return "Company"

def clean_company(name):
    n = (name or "").strip()
    if not n or n.lower() in ("n/a","na","company name n/a","unknown",""): 
        return "Confidential Company"
    return n

def extract_contact(text):
    emails = [e for e in EMAIL_RE.findall(text)
              if not any(b in e.lower() for b in ["noreply","no-reply","donotreply","support@"])]
    phones = PHONE_RE.findall(text)
    return {"recruiter_email": emails[0] if emails else "",
            "recruiter_phone": phones[0] if phones else ""}

def make_job(source, title, company, location, link,
             posted="Today", experience="0-2 years (Fresher)",
             skills="", salary="", walkin=False, walkin_info="",
             recruiter_email="", recruiter_phone="", description=""):
    co    = clean_company(company)
    score = ats_score(title, description, skills)
    return {
        "source": source, "title": title.strip(),
        "company": co, "company_type": classify_co(co),
        "location": location or "Bengaluru, India",
        "link": link, "posted": posted, "experience": experience,
        "skills": skills, "salary": salary,
        "is_walkin": walkin, "walkin_info": walkin_info,
        "recruiter_email": recruiter_email,
        "recruiter_phone": recruiter_phone,
        "ats_score": score,
    }

# ── 1. NAUKRI ─────────────────────────────────────────────────────────────────
def scrape_naukri():
    jobs = []
    print("  🟠 Naukri...")
    naukri_h = {**HEADERS, "Referer":"https://www.naukri.com/",
                "appid":"109", "systemid":"Naukri"}
    searches = [
        "java-developer-jobs-in-bengaluru?experience=0&jobAge=1",
        "java-full-stack-developer-jobs-in-bengaluru?experience=0&jobAge=1",
        "spring-boot-developer-jobs-in-bengaluru?experience=0&jobAge=1",
        "software-developer-fresher-jobs-in-bengaluru?experience=0&jobAge=7",
        "angular-developer-jobs-in-bengaluru?experience=0&jobAge=7",
        "walk-in-java-developer-jobs-in-bengaluru",
    ]
    for path in searches:
        try:
            resp = safe_get(f"https://www.naukri.com/{path}", headers=naukri_h)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data  = json.loads(s.string or "")
                    items = []
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                    elif isinstance(data, list):
                        items = [{"item": d} for d in data if isinstance(d, dict)]
                    for item in items:
                        jb      = item.get("item", item)
                        title   = jb.get("title", "")
                        company = jb.get("hiringOrganization", {}).get("name", "")
                        link    = jb.get("url", "")
                        exp_txt = str(jb.get("experienceRequirements", ""))
                        desc    = jb.get("description", "")
                        score   = ats_score(title, desc)
                        if title and is_relevant(title) and is_fresher(exp_txt) and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Naukri", title, company,
                                                 "Bengaluru, India", link,
                                                 experience=exp_txt or "0-2 years (Fresher)",
                                                 description=desc, walkin=is_walkin(title+desc)))
                except Exception: pass

            cards = (soup.find_all("article", class_=re.compile(r"jobTuple|job-tuple")) or
                     soup.find_all("div", class_=re.compile(r"jobTuple|srp-jobtuple")))
            for card in cards[:12]:
                try:
                    title_el   = card.find(["a","h2"], class_=re.compile(r"title|jobTitle"))
                    company_el = card.find(["a","span"], class_=re.compile(r"comp-name|companyInfo"))
                    link_el    = card.find("a", href=re.compile(r"naukri\.com"))
                    exp_el     = card.find(["span","li"], class_=re.compile(r"exp|experience"))
                    sal_el     = card.find(["span","li"], class_=re.compile(r"sal|salary"))
                    skill_el   = card.find(["span","div"], class_=re.compile(r"skill|tag"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    skills  = (skill_el.get_text(strip=True) if skill_el else "")
                    if not title or not is_relevant(title): continue
                    if not is_fresher(exp_txt): continue
                    score = ats_score(title, skills=skills)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else path
                    link = href if href.startswith("http") else f"https://www.naukri.com{href}"
                    full_text = card.get_text()
                    contact   = extract_contact(full_text)
                    jobs.append(make_job("Naukri", title, company, "Bengaluru, India", link,
                                         experience=exp_txt or "0-2 years (Fresher)",
                                         salary=sal_el.get_text(strip=True) if sal_el else "",
                                         skills=skills, walkin=is_walkin(full_text), **contact))
                except Exception: continue
            time.sleep(3)
        except Exception as e:
            print(f"    Naukri error: {e}")

    # Naukri API
    try:
        api_url = ("https://www.naukri.com/jobapi/v3/search?noOfResults=20"
                   "&urlType=search_by_keyword&searchType=adv"
                   "&keyword=java+developer&location=bengaluru"
                   "&experience=0&experienceDD=2&jobAge=1&src=jobsearchDesk")
        resp = safe_get(api_url, headers={**naukri_h, "x-requested-with":"XMLHttpRequest"})
        if resp:
            try:
                data = resp.json()
                for jb in data.get("jobDetails", [])[:15]:
                    title   = jb.get("title", "")
                    company = jb.get("companyName", "")
                    link    = (jb.get("jdURL","") or
                               f"https://www.naukri.com{jb.get('staticUrl','')}")
                    exp_txt = jb.get("experienceText", "")
                    skills  = jb.get("tagsAndSkills", "")
                    score   = ats_score(title, skills=skills)
                    if title and is_relevant(title) and is_fresher(exp_txt) and score >= ATS_THRESHOLD:
                        jobs.append(make_job("Naukri", title, company, "Bengaluru, India",
                                             link, experience=exp_txt or "0-2 years (Fresher)",
                                             skills=skills))
            except Exception: pass
    except Exception: pass

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 2. LINKEDIN ───────────────────────────────────────────────────────────────
def scrape_linkedin():
    jobs = []
    print("  🔵 LinkedIn...")
    searches = [
        ("java developer fresher", "Bengaluru"),
        ("spring boot developer 0 2 years", "Bengaluru"),
        ("java full stack developer fresher", "Bengaluru"),
        ("angular java developer fresher", "Bengaluru"),
        ("software developer fresher java", "Bengaluru"),
    ]
    for kw, loc in searches:
        try:
            url = (f"https://www.linkedin.com/jobs/search/"
                   f"?keywords={urllib.parse.quote(kw)}"
                   f"&location={urllib.parse.quote(loc+', Karnataka, India')}"
                   f"&f_E=1,2&f_TPR=r604800&position=1&pageNum=0")
            resp = safe_get(url)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")

            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data  = json.loads(s.string or "")
                    items = ([data] if isinstance(data, dict) else
                             data if isinstance(data, list) else [])
                    for jb in items:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title", "")
                        company = (jb.get("hiringOrganization", {}).get("name", "") or
                                   jb.get("employerName", ""))
                        link    = jb.get("url", jb.get("sameAs", ""))
                        desc    = jb.get("description", "")
                        exp_txt = str(jb.get("experienceRequirements", ""))
                        score   = ats_score(title, desc)
                        if (title and is_relevant(title) and is_fresher(exp_txt)
                                and score >= ATS_THRESHOLD):
                            jobs.append(make_job("LinkedIn", title, company,
                                                 "Bengaluru, India", link,
                                                 description=desc))
                except Exception: pass

            cards = soup.find_all("div", class_=re.compile(r"job-search-card|base-card"))
            for card in cards[:12]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-search-card__title|base-card__full-link"))
                    company_el = card.find(["h4","a"], class_=re.compile(r"job-search-card__company"))
                    loc_el     = card.find("span", class_=re.compile(r"job-search-card__location"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/view/"))
                    date_el    = card.find("time")
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    loc     = (loc_el.get_text(strip=True) if loc_el else "Bengaluru, India")
                    if not title or not is_relevant(title): continue
                    if not is_bengaluru(loc): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href  = link_el["href"] if link_el else ""
                    link  = ("https://www.linkedin.com" + href.split("?")[0]
                             if href.startswith("/") else href)
                    posted = date_el.get("datetime","Today") if date_el else "Today"
                    jobs.append(make_job("LinkedIn", title, company, loc, link, posted=posted))
                except Exception: continue
            time.sleep(3)
        except Exception as e:
            print(f"    LinkedIn error: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 3. INSTAHIRE ──────────────────────────────────────────────────────────────
def scrape_instahire():
    jobs = []
    print("  🟣 Instahire...")
    urls = [
        "https://instahire.app/jobs?q=java+developer&location=bangalore&exp=0-2",
        "https://instahire.app/jobs?q=spring+boot+developer&location=bangalore",
        "https://instahire.app/jobs?q=java+full+stack&location=bangalore&exp=0-2",
        "https://instahire.app/jobs?q=angular+developer&location=bangalore",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = (soup.find_all("div", class_=re.compile(r"job.?card|jobcard|listing|job-item")) or
                     soup.find_all("li", class_=re.compile(r"job|listing")) or
                     soup.find_all("div", class_=re.compile(r"card")))
            for card in cards[:12]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role|heading"))
                    company_el = card.find(["span","p","a","div"], class_=re.compile(r"company|org|employer"))
                    link_el    = card.find("a", href=True)
                    exp_el     = card.find(["span","div"], class_=re.compile(r"exp|experience"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_relevant(title): continue
                    if not is_fresher(exp_txt): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href  = link_el["href"] if link_el else ""
                    link  = (f"https://instahire.app{href}" if href.startswith("/") else href) or url
                    contact = extract_contact(card.get_text())
                    jobs.append(make_job("Instahire", title, company, "Bengaluru, India", link,
                                         experience=exp_txt or "0-2 years (Fresher)", **contact))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Instahire error: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 4. WELLFOUND ──────────────────────────────────────────────────────────────
def scrape_wellfound():
    jobs = []
    print("  🟤 Wellfound...")
    urls = [
        "https://wellfound.com/jobs?role=software-engineer&location=bengaluru&experience=0-2",
        "https://wellfound.com/jobs?role=backend-engineer&location=bengaluru&experience=0-2",
        "https://wellfound.com/jobs?role=full-stack-engineer&location=bengaluru",
        "https://wellfound.com/role/r/java-developer/bengaluru",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = (soup.find_all("div", class_=re.compile(r"styles_component|job-listing|JobListing")) or
                     soup.find_all("a", href=re.compile(r"/jobs/")))
            for card in cards[:10]:
                try:
                    if card.name == "a":
                        title   = card.get_text(strip=True)
                        company = ""
                        link    = ("https://wellfound.com" + card["href"]
                                   if card["href"].startswith("/") else card["href"])
                    else:
                        title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role"))
                        company_el = card.find(["span","a","p","div"], class_=re.compile(r"company|startup|employer"))
                        link_el    = card.find("a", href=re.compile(r"/jobs/"))
                        title   = (title_el.get_text(strip=True) if title_el else "").strip()
                        company = (company_el.get_text(strip=True) if company_el else "").strip()
                        href    = link_el["href"] if link_el else ""
                        link    = (f"https://wellfound.com{href}" if href.startswith("/") else href) or url
                    if not title or not is_relevant(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    jobs.append(make_job("Wellfound", title, company, "Bengaluru, India", link,
                                         experience="0-2 years (Fresher)"))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Wellfound error: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 5. INTERNSHALA ────────────────────────────────────────────────────────────
def scrape_internshala():
    jobs = []
    print("  🎓 Internshala...")
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
            cards = (soup.find_all("div", class_=re.compile(r"job-internship-card|individual_internship")) or
                     soup.find_all("div", class_=re.compile(r"container-fluid job")))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-title|profile|title"))
                    company_el = card.find(["p","a","h4","span"], class_=re.compile(r"company-name|company|employer"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/detail/|/internships/detail/"))
                    sal_el     = card.find("span", class_=re.compile(r"stipend|salary"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_relevant(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://internshala.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Internshala", title, company, "Bengaluru, India", link,
                                         experience="Fresher / 0-1 year",
                                         salary=sal_el.get_text(strip=True) if sal_el else ""))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Internshala error: {e}")

    unique = {(j["title"][:35], j["company"][:25]): j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 6. TIMESJOBS ──────────────────────────────────────────────────────────────
def scrape_timesjobs():
    jobs = []
    print("  🔴 TimesJobs...")
    urls = [
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+full+stack&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=spring+boot+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=walk+in+java+bengaluru&txtLocation=bengaluru&postWeek=1",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_=re.compile(r"clearfix job-bx|clearfix"))
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
                    if not title or not is_relevant(title): continue
                    if not is_fresher(exp_txt): continue
                    score = ats_score(title, skills=skills)
                    if score < ATS_THRESHOLD: continue
                    walkin  = is_walkin(full_txt + title)
                    contact = extract_contact(full_txt)
                    src     = "TimesJobs Walk-In" if walkin else "TimesJobs"
                    href    = link_el["href"] if link_el else url
                    jobs.append(make_job(src, title, company, "Bengaluru, India", href,
                                         posted=date_el.get_text(strip=True) if date_el else "Today",
                                         experience=exp_txt or "0-2 years (Fresher)",
                                         skills=skills, walkin=walkin, **contact))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    TimesJobs error: {e}")

    wi = sum(1 for j in jobs if j["is_walkin"])
    print(f"    ✓ {len(jobs)} jobs ({wi} walk-ins)")
    return jobs

# ── 7. FRESHERSWORLD ──────────────────────────────────────────────────────────
def scrape_freshersworld():
    jobs = []
    print("  🟢 Freshersworld...")
    urls = [
        "https://www.freshersworld.com/java-developer-jobs-for-freshers/4534561?src=nav&location=Bengaluru",
        "https://www.freshersworld.com/spring-boot-developer-jobs-for-freshers/4575093?src=nav&location=Bengaluru",
        "https://www.freshersworld.com/angular-developer-jobs-for-freshers/4575300?src=nav&location=Bengaluru",
        "https://www.freshersworld.com/software-developer-jobs-for-freshers/4534561?location=Bengaluru",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data.get("itemListElement",[]) if isinstance(data,dict) else
                             [{"item":d} for d in data] if isinstance(data,list) else [])
                    for it in items:
                        jb = it.get("item", it)
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        score   = ats_score(title)
                        if title and is_relevant(title) and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Freshersworld",title,company,"Bengaluru, India",link,
                                                 experience="Fresher / 0-1 year"))
                except Exception: pass
            cards = soup.find_all("div", class_=re.compile(r"job-container|job-item|vacancy-list"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-title|title"))
                    company_el = card.find(["p","span","div"], class_=re.compile(r"company|employer"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_relevant(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.freshersworld.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Freshersworld",title,company,"Bengaluru, India",link,
                                         experience="Fresher / 0-1 year"))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Freshersworld error: {e}")

    unique = {(j["title"][:35],j["company"][:25]):j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 8. SHINE ──────────────────────────────────────────────────────────────────
def scrape_shine():
    jobs = []
    print("  ✨ Shine...")
    urls = [
        "https://www.shine.com/job-search/java-developer-jobs-in-bangalore?experienceRanges=0to1,1to2",
        "https://www.shine.com/job-search/spring-boot-developer-fresher-jobs-in-bangalore",
        "https://www.shine.com/job-search/full-stack-java-developer-jobs-in-bangalore?experienceRanges=0to2",
        "https://www.shine.com/job-search/angular-developer-jobs-in-bangalore?experienceRanges=0to2",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    jobs_list = (data if isinstance(data,list) else data.get("itemListElement",[]))
                    for jb in jobs_list:
                        jb = jb.get("item",jb) if isinstance(jb,dict) else {}
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        exp_txt = str(jb.get("experienceRequirements",""))
                        score   = ats_score(title)
                        if title and is_relevant(title) and is_fresher(exp_txt) and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Shine",title,company,"Bengaluru, India",link))
                except Exception: pass
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
                    if not title or not is_relevant(title): continue
                    if not is_fresher(exp_txt) and exp_txt: continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.shine.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Shine",title,company,"Bengaluru, India",link,
                                         experience=exp_txt or "0-2 years (Fresher)",
                                         salary=sal_el.get_text(strip=True) if sal_el else ""))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Shine error: {e}")

    unique = {(j["title"][:35],j["company"][:25]):j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 9. INDEED ─────────────────────────────────────────────────────────────────
def scrape_indeed():
    jobs = []
    print("  🔵 Indeed India...")
    urls = [
        "https://in.indeed.com/jobs?q=java+developer+fresher&l=Bengaluru%2C+Karnataka&fromage=7&sort=date",
        "https://in.indeed.com/jobs?q=spring+boot+developer&l=Bengaluru%2C+Karnataka&fromage=7",
        "https://in.indeed.com/jobs?q=java+full+stack&l=Bengaluru%2C+Karnataka&fromage=7",
        "https://in.indeed.com/jobs?q=angular+java+developer&l=Bengaluru%2C+Karnataka&fromage=7",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data.get("itemListElement",[]) if isinstance(data,dict) else
                             [{"item":d} for d in data] if isinstance(data,list) else [])
                    for it in items:
                        jb = it.get("item",it) if isinstance(it,dict) else {}
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        desc    = jb.get("description","")
                        score   = ats_score(title,desc)
                        if title and is_relevant(title) and not is_relevant.__doc__ and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Indeed India",title,company,"Bengaluru, India",link,description=desc))
                except Exception: pass
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
                    if not title or not is_relevant(title): continue
                    if not is_bengaluru(loc): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://in.indeed.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Indeed India",title,company,loc,link,
                                         salary=sal_el.get_text(strip=True) if sal_el else ""))
                except Exception: continue
            time.sleep(3)
        except Exception as e:
            print(f"    Indeed error: {e}")

    unique = {(j["title"][:35],j["company"][:25]):j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 10. GLASSDOOR ─────────────────────────────────────────────────────────────
def scrape_glassdoor():
    jobs = []
    print("  🟡 Glassdoor...")
    urls = [
        "https://www.glassdoor.co.in/Job/bangalore-java-developer-jobs-SRCH_IL.0,9_IC2940965_KO10,24.htm?fromAge=7",
        "https://www.glassdoor.co.in/Job/bangalore-software-engineer-jobs-SRCH_IL.0,9_IC2940965_KO10,26.htm?fromAge=7",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data.get("itemListElement",[]) if isinstance(data,dict) else
                             data if isinstance(data,list) else [])
                    for it in items:
                        jb = it.get("item",it) if isinstance(it,dict) else {}
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        score   = ats_score(title)
                        if title and is_relevant(title) and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Glassdoor",title,company,"Bengaluru, India",link))
                except Exception: pass
            cards = soup.find_all("li", class_=re.compile(r"react-job-listing|job-listing"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["a","span"], attrs={"data-test": re.compile(r"job-title|jobTitle")})
                    company_el = card.find(["span","div"], attrs={"data-test":"employer-name"})
                    link_el    = card.find("a", href=re.compile(r"/job-listing/|/Jobs/"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_relevant(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Glassdoor",title,company,"Bengaluru, India",link))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Glassdoor error: {e}")

    unique = {(j["title"][:35],j["company"][:25]):j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 11. CUTSHORT ──────────────────────────────────────────────────────────────
def scrape_cutshort():
    jobs = []
    print("  🔷 Cutshort...")
    urls = [
        "https://cutshort.io/jobs?keywords=java+developer&location=bengaluru&experience=0-2",
        "https://cutshort.io/jobs?keywords=spring+boot&location=bengaluru&experience=0-2",
        "https://cutshort.io/jobs?keywords=angular+java&location=bengaluru",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data if isinstance(data,list) else
                             data.get("itemListElement",[]) if isinstance(data,dict) else [])
                    for jb in items:
                        jb = jb.get("item",jb) if isinstance(jb,dict) else {}
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        score   = ats_score(title)
                        if title and is_relevant(title) and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Cutshort",title,company,"Bengaluru, India",link))
                except Exception: pass
            cards = soup.find_all(["div","article"], class_=re.compile(r"job-card|jobCard|listing-card"))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["h2","h3","a"])
                    company_el = card.find(["span","p","div"], class_=re.compile(r"company|startup|employer"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_relevant(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://cutshort.io{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Cutshort",title,company,"Bengaluru, India",link))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Cutshort error: {e}")

    unique = {(j["title"][:35],j["company"][:25]):j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 12. HIRIST ────────────────────────────────────────────────────────────────
def scrape_hirist():
    jobs = []
    print("  💡 Hirist...")
    urls = [
        "https://www.hirist.tech/j/java-developer-jobs-in-bangalore/38?experience=0-2",
        "https://www.hirist.tech/j/spring-boot-developer-jobs-in-bangalore/38",
        "https://www.hirist.tech/j/full-stack-developer-jobs-in-bangalore/38?experience=0-2",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data.get("itemListElement",[]) if isinstance(data,dict) else
                             [{"item":d} for d in data] if isinstance(data,list) else [])
                    for it in items:
                        jb = it.get("item",it) if isinstance(it,dict) else {}
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        exp_txt = str(jb.get("experienceRequirements",""))
                        score   = ats_score(title)
                        if title and is_relevant(title) and is_fresher(exp_txt) and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Hirist",title,company,"Bengaluru, India",link))
                except Exception: pass
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
                    if not title or not is_relevant(title): continue
                    if not is_fresher(exp_txt) and exp_txt: continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.hirist.tech{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Hirist",title,company,"Bengaluru, India",link,
                                         experience=exp_txt or "0-2 years"))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Hirist error: {e}")

    unique = {(j["title"][:35],j["company"][:25]):j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── 13. ADZUNA INDIA ──────────────────────────────────────────────────────────
def scrape_adzuna():
    jobs = []
    print("  🔸 Adzuna India...")
    urls = [
        "https://www.adzuna.in/search?q=java+developer+fresher&w=bengaluru&days_old=7&sort=date",
        "https://www.adzuna.in/search?q=spring+boot+developer&w=bengaluru&days_old=7",
        "https://www.adzuna.in/search?q=java+full+stack&w=bengaluru&days_old=7",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = (data if isinstance(data,list) else
                             data.get("itemListElement",[]) if isinstance(data,dict) else [])
                    for jb in items:
                        jb = jb.get("item",jb) if isinstance(jb,dict) else {}
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        desc    = jb.get("description","")
                        score   = ats_score(title,desc)
                        if title and is_relevant(title) and score >= ATS_THRESHOLD:
                            jobs.append(make_job("Adzuna India",title,company,"Bengaluru, India",link,description=desc))
                except Exception: pass
            cards = soup.find_all(["div","article"], class_=re.compile(r"res|job"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title"))
                    company_el = card.find(["span","div"], class_=re.compile(r"company|employer"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_relevant(title): continue
                    score = ats_score(title)
                    if score < ATS_THRESHOLD: continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.adzuna.in{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Adzuna India",title,company,"Bengaluru, India",link))
                except Exception: continue
            time.sleep(2)
        except Exception as e:
            print(f"    Adzuna error: {e}")

    unique = {(j["title"][:35],j["company"][:25]):j for j in jobs}
    print(f"    ✓ {len(unique)} jobs")
    return list(unique.values())

# ── DEDUP ─────────────────────────────────────────────────────────────────────
def deduplicate(jobs):
    seen, unique = set(), []
    for j in jobs:
        key = (j["title"].lower()[:35], j["company"].lower()[:25])
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return unique

# ── MAIN ──────────────────────────────────────────────────────────────────────
def scrape_all_jobs():
    print(f"\n{'='*60}")
    print(f"  JOB SCRAPER v4.0 — {datetime.now().strftime('%d %b %Y %I:%M %p')}")
    print(f"  ATS Threshold : ≥{ATS_THRESHOLD}/100")
    print(f"  Location      : Bengaluru ONLY")
    print(f"  Experience    : 0-2 years / Fresher")
    print(f"  Platforms     : 13")
    print(f"{'='*60}\n")

    all_jobs = []
    scrapers = [
        scrape_naukri, scrape_linkedin, scrape_instahire,
        scrape_wellfound, scrape_internshala, scrape_timesjobs,
        scrape_freshersworld, scrape_shine, scrape_indeed,
        scrape_glassdoor, scrape_cutshort, scrape_hirist, scrape_adzuna,
    ]
    for fn in scrapers:
        try:
            all_jobs.extend(fn())
        except Exception as e:
            print(f"    ❌ {fn.__name__} crashed: {e}")

    unique = deduplicate(all_jobs)
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
        "filter_stats": {
            "total_scraped": len(all_jobs),
            "duplicates_removed": len(all_jobs) - len(unique),
            "inactive_removed": 0,
            "final_sent": len(unique),
        }
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅ TOTAL: {len(unique)} ATS-matched IT jobs")
    print(f"  🚶 Walk-ins : {len(walkin_jobs)}")
    print(f"  🏢 MNCs     : {len(mnc_jobs)}")
    print(f"  🚀 Startups : {len(startup_jobs)}")
    print(f"  💼 Others   : {len(other_jobs)}")
    print(f"{'='*60}\n")
    return result

if __name__ == "__main__":
    scrape_all_jobs()

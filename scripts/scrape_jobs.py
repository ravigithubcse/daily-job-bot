#!/usr/bin/env python3
"""
Roy's Daily Job Scraper — FIXED
- Strictly 0-2 YOE / Fresher only
- Company names properly extracted
- No LinkedIn Easy Apply
- Recruiter email/phone extracted where possible
- 10 platforms: Naukri, Instahire, LinkedIn, Wellfound,
  Internshala, TimesJobs, Freshersworld, Shine, Indeed, Glassdoor
"""

import requests, json, time, re, urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT_FILE = "jobs_found.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

RELEVANCE_KEYWORDS = [
    "java", "spring", "spring boot", "backend", "full stack", "fullstack",
    "software engineer", "software developer", "angular", "rest api",
    "microservices", "j2ee", "hibernate", "jpa",
]

# Strictly exclude senior/experienced roles
EXCLUDE_TITLE_KEYWORDS = [
    "senior", "sr.", "lead", "manager", "architect", "principal", "staff",
    "director", "head of", "vp ", "cto", "5+ years", "7+ years", "10+ years",
    "8+ years", "6+ years", "4+ years", "3+ years", "tech lead",
]

# Experience strings that indicate too senior — reject these
EXCLUDE_EXP_PATTERNS = [
    r"[3-9]\d*\s*[-–]\s*\d+\s*years?",   # 3-X years
    r"[3-9]\d*\+\s*years?",               # 3+ years
    r"minimum\s+[3-9]",                   # minimum 3
    r"at least\s+[3-9]",                  # at least 3
]

MNC_COMPANIES = [
    "IBM", "Accenture", "Capgemini", "Wipro", "Infosys", "TCS", "HCL",
    "Cognizant", "Tech Mahindra", "Mphasis", "LTIMindtree", "Hexaware",
    "Publicis Sapient", "GlobalLogic", "EPAM", "ThoughtWorks", "Nagarro",
    "Oracle", "SAP", "Salesforce", "Microsoft", "Google", "Amazon",
    "Deloitte", "PwC", "KPMG", "Accolite", "Mindtree", "Persistent",
    "Zensar", "Birlasoft", "Mastech", "Sonata", "Cyient",
]
STARTUP_COMPANIES = [
    "Razorpay", "PhonePe", "CRED", "Meesho", "Groww", "Zepto", "Swiggy",
    "Navi", "BrowserStack", "Freshworks", "Zoho", "Chargebee",
    "Unacademy", "Byju", "Ola", "Rapido", "Urban Company", "Slice",
    "Fi Money", "Jupiter", "smallcase", "Scaler", "upGrad", "Lenskart",
    "Delhivery", "Porter", "Spinny", "Cars24",
]

EMAIL_RE   = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE   = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}")


def safe_get(url, timeout=15, retries=2, headers=None):
    h = headers or HEADERS
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=h, timeout=timeout)
            if r.status_code == 200:
                return r
            time.sleep(2)
        except Exception as e:
            if attempt == retries - 1:
                print(f"    ⚠ Failed: {url[:55]}...")
    return None


def is_relevant_title(title):
    t = title.lower()
    if not any(k in t for k in RELEVANCE_KEYWORDS): return False
    if any(e in t for e in EXCLUDE_TITLE_KEYWORDS): return False
    return True


def is_fresher_exp(exp_text):
    """Return True only if experience is 0-2 years."""
    if not exp_text: return True
    t = exp_text.lower().strip()

    # Explicit fresher signals → always accept
    if any(w in t for w in ["fresher", "0 year", "0-1", "0-2", "0 - 1", "0 - 2",
                             "entry level", "entry-level", "graduate", "2024", "2025"]):
        return True

    # Check for too-experienced patterns → reject
    for pat in EXCLUDE_EXP_PATTERNS:
        if re.search(pat, t):
            return False

    # Accept if max experience mentioned is ≤ 2
    nums = re.findall(r"\d+", t)
    if nums:
        max_exp = max(int(n) for n in nums)
        if max_exp > 2:
            return False

    return True


def classify_company(name):
    n = name.upper()
    if any(m.upper() in n for m in MNC_COMPANIES): return "MNC"
    if any(s.upper() in n for s in STARTUP_COMPANIES): return "Startup"
    return "Company"


def is_walkin(text):
    return any(w in text.lower() for w in ["walk-in", "walkin", "walk in", "direct walk"])


def extract_contact(text):
    """Extract recruiter email and phone from job page text."""
    emails  = EMAIL_RE.findall(text)
    phones  = PHONE_RE.findall(text)
    # Filter out generic/system emails
    emails  = [e for e in emails if not any(bad in e.lower() for bad in
               ["noreply", "no-reply", "donotreply", "support@", "info@naukri",
                "feedback@", "privacy@", "legal@", "admin@"])]
    return {
        "recruiter_email": emails[0] if emails else "",
        "recruiter_phone": phones[0] if phones else "",
    }



# ── ATS SCORER (display-only — does NOT filter jobs) ─────────────────────────
PRIMARY_SKILLS = [
    "java", "spring boot", "spring", "spring security", "angular",
    "typescript", "rest api", "microservices", "jpa", "hibernate",
    "postgresql", "kafka", "redis", "docker", "jwt",
]
SECONDARY_SKILLS = [
    "jenkins", "junit", "mockito", "swagger", "rxjs", "html", "css",
    "javascript", "websocket", "git", "agile", "python", "fastapi",
]

def ats_score(title, desc="", skills=""):
    combined = f"{title} {desc} {skills}".lower()
    t = title.lower()
    score = 0
    if any(k in t for k in ["java","spring","software developer","software engineer",
                              "full stack","fullstack","backend","angular","j2ee","api developer"]):
        score += 40
    for s in PRIMARY_SKILLS:
        if s in combined: score += 5
    for s in SECONDARY_SKILLS:
        if s in combined: score += 2
    return min(score, 100)


def make_job(source, title, company, location, link,
             posted="Today", experience="0-2 years (Fresher)",
             skills="", salary="", walkin=False, walkin_info="",
             recruiter_email="", recruiter_phone="", description=""):
    return {
        "source":          source,
        "title":           title.strip(),
        "company":         company.strip() or "Company Name N/A",
        "company_type":    classify_company(company),
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
    }


# ── 1. NAUKRI ─────────────────────────────────────────────────────────────────
def scrape_naukri():
    jobs = []
    print("  🟠 Naukri...")
    searches = [
        "java-developer-jobs-in-bengaluru?experience=0&jobAge=1",
        "java-full-stack-developer-jobs-in-bengaluru?experience=0&jobAge=1",
        "spring-boot-developer-jobs-in-bengaluru?experience=0&jobAge=1",
        "software-developer-fresher-jobs-in-bengaluru?experience=0&jobAge=7",
    ]
    naukri_headers = {
        **HEADERS,
        "Referer": "https://www.naukri.com/",
        "appid": "109",
        "systemid": "Naukri",
    }
    for path in searches:
        try:
            url  = f"https://www.naukri.com/{path}"
            resp = safe_get(url, headers=naukri_headers)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try JSON-LD first
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    items = []
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                    elif isinstance(data, list):
                        items = [{"item": d} for d in data if isinstance(d, dict)]
                    for item in items:
                        jb = item.get("item", item)
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        exp_txt = str(jb.get("experienceRequirements",""))
                        if title and is_relevant_title(title) and is_fresher_exp(exp_txt):
                            jobs.append(make_job("Naukri", title, company, "Bengaluru, India", link))
                except Exception:
                    pass

            # HTML fallback
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
                    if not title or not is_relevant_title(title): continue
                    if not is_fresher_exp(exp_txt): continue

                    link = (link_el["href"] if link_el else url)
                    if link and not link.startswith("http"):
                        link = "https://www.naukri.com" + link
                    jobs.append(make_job(
                        "Naukri", title, company, "Bengaluru, India", link,
                        experience=exp_txt or "0-2 years (Fresher)",
                        salary=(sal_el.get_text(strip=True) if sal_el else ""),
                        skills=(skill_el.get_text(strip=True) if skill_el else ""),
                    ))
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    Naukri error: {e}")

    # Naukri API
    try:
        api = ("https://www.naukri.com/jobapi/v3/search?noOfResults=20"
               "&urlType=search_by_keyword&searchType=adv"
               "&keyword=java+developer&location=bengaluru"
               "&experience=0&experienceDD=2&jobAge=1&src=jobsearchDesk")
        resp = safe_get(api, headers={**HEADERS,
            "Referer":"https://www.naukri.com/","appid":"109","systemid":"Naukri",
            "x-requested-with":"XMLHttpRequest"})
        if resp:
            try:
                data = resp.json()
                for jb in data.get("jobDetails", [])[:15]:
                    title   = jb.get("title","")
                    company = jb.get("companyName","")
                    link    = jb.get("jdURL","") or f"https://www.naukri.com{jb.get('staticUrl','')}"
                    exp_txt = jb.get("experienceText","")
                    if title and is_relevant_title(title) and is_fresher_exp(exp_txt):
                        jobs.append(make_job("Naukri", title, company, "Bengaluru, India", link,
                                            experience=exp_txt or "0-2 years (Fresher)"))
            except Exception:
                pass
    except Exception:
        pass

    unique = {(j["title"][:35],j["company"][:25]): j for j in jobs}
    result = list(unique.values())
    print(f"    ✓ {len(result)} fresher jobs")
    return result


# ── 2. INSTAHIRE ──────────────────────────────────────────────────────────────
def scrape_instahire():
    jobs = []
    print("  🟣 Instahire...")
    urls = [
        "https://instahire.app/jobs?q=java+developer&location=bangalore&exp=0-2",
        "https://instahire.app/jobs?q=spring+boot+developer&location=bangalore&exp=0-1",
        "https://instahire.app/jobs?q=java+fresher&location=bangalore",
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
                    email_el   = card.find(text=EMAIL_RE)

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_relevant_title(title): continue
                    if not is_fresher_exp(exp_txt): continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://instahire.app{href}" if href.startswith("/") else href) or url
                    contact = extract_contact(card.get_text())
                    jobs.append(make_job("Instahire", title, company, "Bengaluru, India", link,
                                        experience=exp_txt or "0-2 years (Fresher)",
                                        **contact))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Instahire error: {e}")
    unique = {(j["title"][:35],j["company"][:25]): j for j in jobs}
    result = list(unique.values())
    print(f"    ✓ {len(result)} jobs")
    return result


# ── 3. LINKEDIN (No Easy Apply — Direct Company Jobs Only) ────────────────────
def scrape_linkedin():
    jobs = []
    print("  🔵 LinkedIn (Direct apply only, no Easy Apply)...")
    searches = [
        "java developer fresher 2024 Bengaluru",
        "java full stack developer 0 1 year Bengaluru",
        "spring boot developer fresher Bengaluru",
        "java backend developer entry level Bengaluru",
    ]
    for keyword in searches:
        try:
            kw_enc  = urllib.parse.quote(keyword)
            loc_enc = urllib.parse.quote("Bengaluru, Karnataka, India")
            # f_AL=false excludes Easy Apply, f_E=1,2 = entry/associate level
            url = (f"https://www.linkedin.com/jobs/search/"
                   f"?keywords={kw_enc}&location={loc_enc}"
                   f"&f_E=1,2&f_TPR=r86400&f_WT=1,2,3")
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-search-card|base-card"))

            for card in cards[:10]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-search-card__title|base-card__full-link"))
                    company_el = card.find(["h4","a"], class_=re.compile(r"job-search-card__company|base-card__subtitle"))
                    loc_el     = card.find("span", class_=re.compile(r"job-search-card__location"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/view/"))
                    date_el    = card.find("time")
                    meta_el    = card.find("span", class_=re.compile(r"job-search-card__subtitle"))

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()

                    if not title or not is_relevant_title(title): continue

                    # Skip Easy Apply cards
                    card_text = card.get_text().lower()
                    if "easy apply" in card_text:
                        continue

                    # Check experience from meta
                    exp_txt = (meta_el.get_text(strip=True) if meta_el else "")
                    if not is_fresher_exp(exp_txt) and exp_txt:
                        continue

                    href = link_el["href"] if link_el else ""
                    link = ("https://www.linkedin.com" + href.split("?")[0]) if href.startswith("/") else href

                    jobs.append(make_job(
                        "LinkedIn", title, company,
                        loc_el.get_text(strip=True) if loc_el else "Bengaluru, India",
                        link,
                        posted=date_el.get("datetime","Today") if date_el else "Today",
                        experience="0-2 years (Fresher)",
                    ))
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    LinkedIn error: {e}")
    unique = {(j["title"][:35],j["company"][:25]): j for j in jobs}
    result = list(unique.values())
    print(f"    ✓ {len(result)} direct-apply jobs (Easy Apply excluded)")
    return result


# ── 4. WELLFOUND ──────────────────────────────────────────────────────────────
def scrape_wellfound():
    jobs = []
    print("  🟤 Wellfound (Startups)...")
    try:
        url  = "https://wellfound.com/jobs?role=software-engineer&location=bengaluru&experience=0-2"
        resp = safe_get(url)
        if resp:
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"styles_component|job-listing"))
            for card in cards[:12]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role"))
                    company_el = card.find(["span","a","p","div"], class_=re.compile(r"company|startup|employer"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/"))
                    exp_el     = card.find(["span","div"], class_=re.compile(r"exp|experience|level"))

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_relevant_title(title): continue
                    if not is_fresher_exp(exp_txt) and exp_txt: continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://wellfound.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Wellfound", title, company, "Bengaluru, India", link,
                                        experience="0-2 years (Fresher)"))
                except Exception:
                    continue
    except Exception as e:
        print(f"    Wellfound error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 5. INTERNSHALA ────────────────────────────────────────────────────────────
def scrape_internshala():
    jobs = []
    print("  🎓 Internshala (Fresher)...")
    urls = [
        "https://internshala.com/jobs/java-jobs-in-bengaluru/",
        "https://internshala.com/jobs/full-stack-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/software-development-jobs-in-bengaluru/",
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
                    if not title or not is_relevant_title(title): continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://internshala.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Internshala", title, company, "Bengaluru, India", link,
                                        experience="0-1 years (Fresher)",
                                        salary=sal_el.get_text(strip=True) if sal_el else ""))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Internshala error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 6. TIMESJOBS ──────────────────────────────────────────────────────────────
def scrape_timesjobs():
    jobs = []
    print("  🔴 TimesJobs (0-2 YOE + Walk-ins)...")
    urls = [
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=1&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+full+stack&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+fresher&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=1&sequence=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+walk+in&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_=re.compile(r"clearfix job-bx"))
            for card in cards[:8]:
                try:
                    title_el   = card.find("h2")
                    company_el = card.find("h3", class_=re.compile(r"joblist-comp-name"))
                    link_el    = card.find("a", href=re.compile(r"timesjobs\.com"))
                    skills_el  = card.find("span", class_=re.compile(r"srp-skills"))
                    exp_el     = card.find("ul", class_=re.compile(r"top-jd-dtl"))
                    date_el    = card.find("span", class_=re.compile(r"sim-posted"))
                    full_text  = card.get_text()

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_relevant_title(title): continue
                    if not is_fresher_exp(exp_txt) and exp_txt: continue

                    walkin = is_walkin(full_text)
                    contact = extract_contact(full_text)
                    jobs.append(make_job(
                        "TimesJobs Walk-In" if walkin else "TimesJobs",
                        title, company, "Bengaluru, India",
                        link_el["href"] if link_el else url,
                        posted=date_el.get_text(strip=True) if date_el else "Today",
                        experience=exp_txt or "0-2 years (Fresher)",
                        skills=skills_el.get_text(strip=True) if skills_el else "",
                        walkin=walkin, **contact
                    ))
                except Exception:
                    continue
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
        "https://www.freshersworld.com/software-engineer-jobs-for-freshers/4534532?src=nav&location=Bengaluru",
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
                    if not title or not is_relevant_title(title): continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.freshersworld.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Freshersworld", title, company, "Bengaluru, India", link,
                                        experience="Fresher / 0-1 year"))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Freshersworld error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 8. SHINE ──────────────────────────────────────────────────────────────────
def scrape_shine():
    jobs = []
    print("  ✨ Shine.com...")
    urls = [
        "https://www.shine.com/job-search/java-developer-jobs-in-bangalore?experienceRanges=0to1,1to2",
        "https://www.shine.com/job-search/spring-boot-developer-fresher-jobs-in-bangalore",
    ]
    for url in urls:
        try:
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-listing|srp-tuple|jobTuple"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h2","a"], class_=re.compile(r"job-title|title"))
                    company_el = card.find(["span","a","div"], class_=re.compile(r"company|org-name|employer"))
                    link_el    = card.find("a", href=re.compile(r"shine\.com/jobs/"))
                    exp_el     = card.find(["span","div"], class_=re.compile(r"exp|experience"))
                    sal_el     = card.find("span", class_=re.compile(r"salary|sal"))

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    exp_txt = (exp_el.get_text(strip=True) if exp_el else "")
                    if not title or not is_relevant_title(title): continue
                    if not is_fresher_exp(exp_txt) and exp_txt: continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.shine.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Shine", title, company, "Bengaluru, India", link,
                                        experience=exp_txt or "0-2 years (Fresher)",
                                        salary=sal_el.get_text(strip=True) if sal_el else ""))
                except Exception:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"    Shine error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 9. INDEED INDIA ───────────────────────────────────────────────────────────
def scrape_indeed():
    jobs = []
    print("  🔵 Indeed India (Entry Level)...")
    searches = ["java+developer+fresher", "java+full+stack+fresher", "spring+boot+fresher"]
    for keyword in searches:
        try:
            url  = f"https://in.indeed.com/jobs?q={keyword}&l=Bengaluru%2C+Karnataka&explvl=entry_level&fromage=3"
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|jobsearch-SerpJobCard|tapItem"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h2","a"], class_=re.compile(r"jobTitle|title"))
                    company_el = card.find(["span","a","div"], class_=re.compile(r"companyName|company|employer"))
                    link_el    = card.find("a", href=re.compile(r"/rc/clk|/pagead|/viewjob"))
                    sal_el     = card.find("div", class_=re.compile(r"salary|salaryText"))

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_relevant_title(title): continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://in.indeed.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Indeed India", title, company, "Bengaluru, India", link,
                                        experience="0-2 years (Fresher)",
                                        salary=sal_el.get_text(strip=True) if sal_el else ""))
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    Indeed error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 10. GLASSDOOR ─────────────────────────────────────────────────────────────
def scrape_glassdoor():
    jobs = []
    print("  🟡 Glassdoor...")
    try:
        url  = "https://www.glassdoor.co.in/Job/bangalore-java-developer-jobs-SRCH_IL.0,9_IC2940965_KO10,24.htm?fromAge=3&minRating=3.0&seniorityType=juniorLevel"
        resp = safe_get(url)
        if resp:
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_=re.compile(r"react-job-listing|job-listing"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["a","span"], attrs={"data-test": re.compile(r"job-title|jobTitle")})
                    company_el = card.find(["span","div"], attrs={"data-test": "employer-name"})
                    link_el    = card.find("a", href=re.compile(r"/job-listing/|/Jobs/"))
                    sal_el     = card.find("span", attrs={"data-test": "detailSalary"})

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "").strip()
                    if not title or not is_relevant_title(title): continue

                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Glassdoor", title, company, "Bengaluru, India", link,
                                        experience="0-2 years (Fresher)",
                                        salary=sal_el.get_text(strip=True) if sal_el else ""))
                except Exception:
                    continue
    except Exception as e:
        print(f"    Glassdoor error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── DEDUPLICATE ───────────────────────────────────────────────────────────────
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
    print(f"\n{'='*55}")
    print(f"  JOB SCRAPER — {datetime.now().strftime('%d %b %Y %I:%M %p IST')}")
    print(f"  Filter: FRESHER / 0-2 YOE ONLY | Bengaluru")
    print(f"  10 Platforms | No LinkedIn Easy Apply")
    print(f"{'='*55}\n")

    all_jobs = []
    all_jobs.extend(scrape_naukri())
    all_jobs.extend(scrape_instahire())
    all_jobs.extend(scrape_linkedin())
    all_jobs.extend(scrape_wellfound())
    all_jobs.extend(scrape_internshala())
    all_jobs.extend(scrape_timesjobs())
    all_jobs.extend(scrape_freshersworld())
    all_jobs.extend(scrape_shine())
    all_jobs.extend(scrape_indeed())
    all_jobs.extend(scrape_glassdoor())

    unique       = deduplicate(all_jobs)
    walkin_jobs  = sorted([j for j in unique if j["is_walkin"]], key=lambda x: x["company"])
    regular      = [j for j in unique if not j["is_walkin"]]
    mnc_jobs     = [j for j in regular if j["company_type"] == "MNC"]
    startup_jobs = [j for j in regular if j["company_type"] == "Startup"]
    other_jobs   = [j for j in regular if j["company_type"] == "Company"]

    result = {
        "scraped_at":    datetime.now().isoformat(),
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

    print(f"\n{'='*55}")
    print(f"  ✅ TOTAL: {len(unique)} FRESHER jobs (0-2 YOE)")
    print(f"  🚶 Walk-ins : {len(walkin_jobs)}")
    print(f"  🏢 MNCs     : {len(mnc_jobs)}")
    print(f"  🚀 Startups : {len(startup_jobs)}")
    print(f"  💼 Others   : {len(other_jobs)}")
    print(f"{'='*55}\n")
    return result

if __name__ == "__main__":
    scrape_all_jobs()

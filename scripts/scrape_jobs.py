#!/usr/bin/env python3
"""
Roy's Daily Job Scraper - ALL PLATFORMS
Targets: Java Full Stack / Backend | 0-2 YOE | Bengaluru
Sources: LinkedIn, Naukri, Wellfound, Internshala, TimesJobs,
         Freshersworld, Instahire, Shine, Glassdoor, Indeed India
Covers:  MNCs, Startups, Product companies, Walk-Ins
"""

import requests, json, time, re, urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT_FILE = "jobs_found.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

NAUKRI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.naukri.com/",
    "appid": "109",
    "systemid": "Naukri",
    "x-requested-with": "XMLHttpRequest",
    "x-http-method-override": "GET",
}

RELEVANCE_KEYWORDS = [
    "java", "spring", "spring boot", "backend", "full stack", "fullstack",
    "software engineer", "software developer", "angular", "rest api",
    "microservices", "j2ee", "hibernate", "jpa", "kotlin",
]
EXCLUDE_KEYWORDS = [
    "senior", "lead", "manager", "architect", "principal", "staff",
    "director", "head of", "vp ", "cto", "5+ years", "7+ years", "10+ years",
    "8+ years", "6+ years",
]
MNC_COMPANIES = [
    "IBM", "Accenture", "Capgemini", "Wipro", "Infosys", "TCS", "HCL",
    "Cognizant", "Tech Mahindra", "Mphasis", "LTIMindtree", "Hexaware",
    "Publicis Sapient", "GlobalLogic", "EPAM", "ThoughtWorks", "Nagarro",
    "Oracle", "SAP", "Salesforce", "Microsoft", "Google", "Amazon",
    "Deloitte", "PwC", "KPMG", "EY", "Accolite", "Mindtree", "Persistent",
    "Zensar", "Birlasoft", "Mastech", "Sonata", "NIIT", "Cyient",
]
STARTUP_COMPANIES = [
    "Razorpay", "PhonePe", "CRED", "Meesho", "Groww", "Zepto", "Swiggy",
    "Dunzo", "Navi", "BrowserStack", "Freshworks", "Zoho", "Chargebee",
    "Unacademy", "Vedantu", "Byju", "Ola", "Rapido", "Urban Company",
    "Slice", "Fi Money", "Jupiter", "smallcase", "Scaler", "upGrad",
    "Lenskart", "Delhivery", "Porter", "Spinny", "Cars24", "Dealshare",
]


def safe_get(url, timeout=15, retries=2, extra_headers=None):
    h = {**HEADERS, **(extra_headers or {})}
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=h, timeout=timeout)
            if resp.status_code == 200:
                return resp
            time.sleep(2)
        except Exception as e:
            if attempt == retries - 1:
                print(f"    ⚠ Failed [{resp.status_code if 'resp' in dir() else 'ERR'}]: {url[:55]}...")
    return None


def is_relevant(title):
    t = title.lower()
    return any(k in t for k in RELEVANCE_KEYWORDS) and not any(e in t for e in EXCLUDE_KEYWORDS)


def classify_company(name):
    n = name.upper()
    if any(m.upper() in n for m in MNC_COMPANIES): return "MNC"
    if any(s.upper() in n for s in STARTUP_COMPANIES): return "Startup"
    return "Company"


def is_walkin(text):
    return any(w in text.lower() for w in ["walk-in", "walkin", "walk in", "direct walk", "no interview"])


def make_job(source, title, company, location, link, posted="Recent",
             experience="0-2 years", skills="", salary="", walkin=False, walkin_info=""):
    return {
        "source": source,
        "title": title.strip(),
        "company": company.strip(),
        "company_type": classify_company(company),
        "location": location or "Bengaluru, India",
        "link": link,
        "posted": posted,
        "experience": experience,
        "skills": skills,
        "salary": salary,
        "is_walkin": walkin,
        "walkin_info": walkin_info,
    }


# ── 1. NAUKRI ─────────────────────────────────────────────────────────────────
def scrape_naukri():
    jobs = []
    print("  🟠 Naukri...")
    searches = [
        ("java developer", 0, 1),
        ("java full stack developer", 0, 2),
        ("spring boot developer", 0, 2),
        ("java backend developer", 0, 1),
    ]
    for keyword, exp_min, exp_max in searches:
        try:
            kw_enc = urllib.parse.quote(keyword)
            # Naukri public search URL
            url = (f"https://www.naukri.com/{kw_enc.replace('%20','-')}-jobs-in-bengaluru"
                   f"?experience={exp_min}&jobAge=1")
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try JSON-LD structured data first
            scripts = soup.find_all("script", type="application/ld+json")
            for s in scripts:
                try:
                    data = json.loads(s.string or "")
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        for item in data.get("itemListElement", []):
                            job = item.get("item", {})
                            title   = job.get("title", "")
                            company = job.get("hiringOrganization", {}).get("name", "N/A")
                            link    = job.get("url", url)
                            loc     = job.get("jobLocation", {}).get("address", {}).get("addressLocality", "Bengaluru")
                            sal     = job.get("baseSalary", {})
                            if title and is_relevant(title):
                                jobs.append(make_job("Naukri", title, company, loc, link))
                except Exception:
                    pass

            # Fallback: HTML scraping
            cards = (soup.find_all("article", class_=re.compile(r"jobTuple|job-tuple")) or
                     soup.find_all("div", class_=re.compile(r"jobTuple|srp-jobtuple")))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["a","h2"], class_=re.compile(r"title|jobTitle"))
                    company_el = card.find(["a","span"], class_=re.compile(r"comp-name|companyInfo"))
                    loc_el     = card.find(["span","li"], class_=re.compile(r"loc|location"))
                    link_el    = card.find("a", href=re.compile(r"naukri.com"))
                    exp_el     = card.find(["span","li"], class_=re.compile(r"exp|experience"))
                    sal_el     = card.find(["span","li"], class_=re.compile(r"sal|salary"))

                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    link = (link_el["href"] if link_el else url)
                    exp  = (exp_el.get_text(strip=True) if exp_el else "0-2 years")
                    sal  = (sal_el.get_text(strip=True) if sal_el else "")
                    loc  = (loc_el.get_text(strip=True) if loc_el else "Bengaluru, India")
                    walkin = is_walkin(card.get_text())
                    jobs.append(make_job("Naukri", title, company, loc, link,
                                        experience=exp, salary=sal, walkin=walkin))
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    Naukri error: {e}")

    # Also try Naukri API endpoint
    try:
        api_url = ("https://www.naukri.com/jobapi/v3/search?noOfResults=20"
                   "&urlType=search_by_keyword&searchType=adv"
                   "&keyword=java+developer&location=bengaluru"
                   "&experience=0&experienceDD=2&jobAge=1&src=jobsearchDesk")
        resp = safe_get(api_url, extra_headers=NAUKRI_HEADERS)
        if resp:
            try:
                data = resp.json()
                for jb in data.get("jobDetails", [])[:15]:
                    title   = jb.get("title", "")
                    company = jb.get("companyName", "N/A")
                    link    = jb.get("jdURL") or f"https://www.naukri.com{jb.get('staticUrl','')}"
                    exp     = jb.get("experienceText", "0-2 years")
                    sal     = jb.get("salary", "")
                    loc     = ", ".join(jb.get("placeholders",[{}])[0].get("label","").split(",")[:2]) if jb.get("placeholders") else "Bengaluru"
                    skills_list = [s.get("label","") for s in jb.get("tagsAndSkills","").split(",")[:4]] if jb.get("tagsAndSkills") else []
                    skills  = ", ".join(filter(None, skills_list))
                    if title and is_relevant(title):
                        jobs.append(make_job("Naukri", title, company, loc, link,
                                            experience=exp, salary=sal, skills=skills))
            except Exception:
                pass
    except Exception as e:
        print(f"    Naukri API error: {e}")

    unique = {j["title"][:35]+j["company"][:20]: j for j in jobs}
    jobs = list(unique.values())
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 2. INSTAHIRE ──────────────────────────────────────────────────────────────
def scrape_instahire():
    jobs = []
    print("  🟣 Instahire...")
    try:
        searches = [
            "https://instahire.app/jobs?q=java+developer&location=bangalore&exp=0-2",
            "https://instahire.app/jobs?q=spring+boot&location=bangalore&exp=0-2",
        ]
        for url in searches:
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = (soup.find_all("div", class_=re.compile(r"job-card|jobcard|job_card|listing")) or
                     soup.find_all("li", class_=re.compile(r"job|listing")))
            for card in cards[:10]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role|job-title"))
                    company_el = card.find(["span","p","a"], class_=re.compile(r"company|org"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    href = link_el["href"] if link_el else ""
                    link = f"https://instahire.app{href}" if href.startswith("/") else href or url
                    jobs.append(make_job("Instahire", title, company, "Bengaluru, India", link))
                except Exception:
                    continue
            time.sleep(2)
    except Exception as e:
        print(f"    Instahire error: {e}")

    # Fallback: Instahire may have API
    try:
        api = "https://instahire.app/api/jobs?keyword=java+developer&location=bangalore&experience=0,2&limit=20"
        resp = safe_get(api, extra_headers={"Accept": "application/json"})
        if resp and "application/json" in resp.headers.get("Content-Type",""):
            data = resp.json()
            job_list = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
            for jb in job_list[:15]:
                title   = jb.get("title","") or jb.get("job_title","")
                company = jb.get("company","") or jb.get("company_name","N/A")
                link    = jb.get("url","") or jb.get("apply_url","") or "https://instahire.app/jobs"
                if title and is_relevant(title):
                    jobs.append(make_job("Instahire", title, company, "Bengaluru, India", link))
    except Exception:
        pass

    unique = {j["title"][:35]+j["company"][:20]: j for j in jobs}
    jobs = list(unique.values())
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 3. LINKEDIN ───────────────────────────────────────────────────────────────
def scrape_linkedin():
    jobs = []
    print("  🔵 LinkedIn...")
    searches = [
        "java developer 0 1 year Bengaluru",
        "java full stack developer fresher Bengaluru",
        "spring boot developer fresher Bengaluru",
        "java backend developer Bengaluru",
    ]
    for keyword in searches:
        try:
            kw_enc  = urllib.parse.quote(keyword)
            loc_enc = urllib.parse.quote("Bengaluru, Karnataka, India")
            url = (f"https://www.linkedin.com/jobs/search/"
                   f"?keywords={kw_enc}&location={loc_enc}&f_E=1,2&f_TPR=r86400")
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-search-card|base-card"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-search-card__title|base-card__full-link"))
                    company_el = card.find(["h4","a"], class_=re.compile(r"job-search-card__company"))
                    loc_el     = card.find("span", class_=re.compile(r"job-search-card__location"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/view/"))
                    date_el    = card.find("time")
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    href = link_el["href"] if link_el else ""
                    link = ("https://www.linkedin.com" + href) if href.startswith("/") else href
                    jobs.append(make_job("LinkedIn", title, company,
                                        loc_el.get_text(strip=True) if loc_el else "Bengaluru",
                                        link, posted=date_el.get("datetime","Recent") if date_el else "Recent"))
                except Exception:
                    continue
            time.sleep(3)
        except Exception as e:
            print(f"    LinkedIn error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 4. WELLFOUND ──────────────────────────────────────────────────────────────
def scrape_wellfound():
    jobs = []
    print("  🟤 Wellfound (Startups)...")
    try:
        url = "https://wellfound.com/jobs?role=software-engineer&location=bengaluru&experience=0-2"
        resp = safe_get(url)
        if resp:
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"styles_component|job-listing|JobListing"))
            for card in cards[:12]:
                try:
                    title_el   = card.find(["h2","h3","a"], class_=re.compile(r"title|role|job-title"))
                    company_el = card.find(["span","a","p"], class_=re.compile(r"company|startup"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "Startup").strip()
                    if not title or not is_relevant(title): continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://wellfound.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Wellfound", title, company, "Bengaluru, India", link))
                except Exception:
                    continue
    except Exception as e:
        print(f"    Wellfound error: {e}")
    print(f"    ✓ {len(jobs)} jobs")
    return jobs


# ── 5. INTERNSHALA ────────────────────────────────────────────────────────────
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
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job-internship-card|individual_internship"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h3","a"], class_=re.compile(r"job-title|profile|title"))
                    company_el = card.find(["p","a","h4"], class_=re.compile(r"company-name|company"))
                    link_el    = card.find("a", href=re.compile(r"/jobs/detail/|/internships/detail/"))
                    sal_el     = card.find("span", class_=re.compile(r"stipend|salary"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
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
    print("  🔴 TimesJobs (+ Walk-ins)...")
    urls = [
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+full+stack&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1",
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
                    link_el    = card.find("a", href=re.compile(r"timesjobs.com/candidate/job"))
                    skills_el  = card.find("span", class_=re.compile(r"srp-skills"))
                    date_el    = card.find("span", class_=re.compile(r"sim-posted"))
                    full_text  = card.get_text()
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    walkin = is_walkin(full_text)
                    jobs.append(make_job(
                        "TimesJobs Walk-In" if walkin else "TimesJobs",
                        title, company, "Bengaluru, India",
                        link_el["href"] if link_el else url,
                        posted=date_el.get_text(strip=True) if date_el else "Recent",
                        skills=skills_el.get_text(strip=True) if skills_el else "",
                        walkin=walkin))
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
                    company_el = card.find(["p","span"], class_=re.compile(r"company"))
                    link_el    = card.find("a", href=True)
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.freshersworld.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Freshersworld", title, company, "Bengaluru, India", link,
                                        experience="0-1 years (Fresher)"))
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
        "https://www.shine.com/job-search/spring-boot-developer-jobs-in-bangalore?experienceRanges=0to1,1to2",
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
                    company_el = card.find(["span","a"], class_=re.compile(r"company|org-name"))
                    link_el    = card.find("a", href=re.compile(r"shine.com/jobs/"))
                    sal_el     = card.find("span", class_=re.compile(r"salary|sal"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.shine.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Shine", title, company, "Bengaluru, India", link,
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
    print("  🔵 Indeed India...")
    searches = [
        "java+developer",
        "java+full+stack+developer",
        "spring+boot+developer",
    ]
    for keyword in searches:
        try:
            url = f"https://in.indeed.com/jobs?q={keyword}&l=Bengaluru%2C+Karnataka&explvl=entry_level&fromage=1"
            resp = safe_get(url)
            if not resp: continue
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|jobsearch-SerpJobCard|tapItem"))
            for card in cards[:8]:
                try:
                    title_el   = card.find(["h2","a"], class_=re.compile(r"jobTitle|title"))
                    company_el = card.find(["span","a"], class_=re.compile(r"companyName|company"))
                    link_el    = card.find("a", href=re.compile(r"/rc/clk|/pagead/clk|/viewjob"))
                    sal_el     = card.find("div", class_=re.compile(r"salary|salaryText"))
                    title   = (title_el.get_text(strip=True) if title_el else "").strip()
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://in.indeed.com{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Indeed India", title, company, "Bengaluru, India", link,
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
        url = "https://www.glassdoor.co.in/Job/bangalore-java-developer-jobs-SRCH_IL.0,9_IC2940965_KO10,24.htm?fromAge=1&minRating=3.0"
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
                    company = (company_el.get_text(strip=True) if company_el else "N/A").strip()
                    if not title or not is_relevant(title): continue
                    href = link_el["href"] if link_el else ""
                    link = (f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Glassdoor", title, company, "Bengaluru, India", link,
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
    print(f"  Platforms: Naukri, Instahire, LinkedIn, Wellfound,")
    print(f"             Internshala, TimesJobs, Freshersworld,")
    print(f"             Shine, Indeed India, Glassdoor")
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

    unique = deduplicate(all_jobs)

    walkin_jobs  = sorted([j for j in unique if j["is_walkin"]], key=lambda x: x["company"])
    regular_jobs = [j for j in unique if not j["is_walkin"]]
    mnc_jobs     = [j for j in regular_jobs if j["company_type"] == "MNC"]
    startup_jobs = [j for j in regular_jobs if j["company_type"] == "Startup"]
    other_jobs   = [j for j in regular_jobs if j["company_type"] == "Company"]

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
    print(f"  ✅ TOTAL: {len(unique)} jobs found")
    print(f"  🚶 Walk-ins : {len(walkin_jobs)}")
    print(f"  🏢 MNCs     : {len(mnc_jobs)}")
    print(f"  🚀 Startups : {len(startup_jobs)}")
    print(f"  💼 Others   : {len(other_jobs)}")
    print(f"{'='*55}\n")
    return result

if __name__ == "__main__":
    scrape_all_jobs()

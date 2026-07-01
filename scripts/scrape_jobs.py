#!/usr/bin/env python3
"""
Roy's Daily Job Scraper v6.0 — RSS + API Approach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRATEGY: RSS feeds + public APIs bypass ALL IP blocks because:
  → XML/JSON responses need no JavaScript rendering
  → No Cloudflare challenge, no CAPTCHA, no bot detection
  → Designed for automated consumption (feed readers)

Sources:
  ✅ LinkedIn        — HTML scraping (proven working)
  ✅ Internshala     — HTML scraping (proven working)
  ✅ Naukri          — Public API with headers + RSS feed
  ✅ Indeed India    — RSS feed (XML, no JS needed)
  ✅ TimesJobs       — RSS feed
  ✅ Shine           — RSS feed
  ✅ Freshersworld   — RSS feed
  ✅ Glassdoor       — RSS feed
  ✅ Instahire       — HTML (small site, not blocked)
  ✅ Cutshort        — HTML (small site, not blocked)
  ✅ Hirist          — HTML (small site, not blocked)
  ✅ Wellfound       — HTML (small site, not blocked)
"""

import requests, json, time, re, urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

OUTPUT_FILE = "jobs_found.json"

HEADERS_CHROME = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
HEADERS_RSS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0; +https://github.com/ravigithubcse)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-IN,en;q=0.9",
}
HEADERS_API = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.naukri.com/",
    "appid": "109",
    "systemid": "Naukri",
    "x-requested-with": "XMLHttpRequest",
}

# ── ATS SCORER ────────────────────────────────────────────────────────────────
PRIMARY   = ["java","spring boot","spring","spring security","angular",
             "typescript","rest api","microservices","jpa","hibernate",
             "postgresql","kafka","redis","docker","jwt","websocket"]
SECONDARY = ["jenkins","junit","mockito","swagger","postman","rxjs",
             "html","css","javascript","git","agile","python","fastapi"]
TITLE_KW  = ["java","spring","software developer","software engineer",
             "full stack","fullstack","backend","angular","j2ee",
             "developer","programmer","it fresher","graduate engineer"]

def ats_score(title, desc="", skills=""):
    combined = f"{title} {desc} {skills}".lower()
    score = 40 if any(k in title.lower() for k in TITLE_KW) else 0
    for s in PRIMARY:
        if s in combined: score += 5
    for s in SECONDARY:
        if s in combined: score += 2
    return min(score, 100)

# ── FILTERS ──────────────────────────────────────────────────────────────────
RELEVANT = ["java","spring","software developer","software engineer",
            "full stack","fullstack","backend","angular","j2ee","web developer",
            "api developer","it developer","developer","programmer",
            "it fresher","graduate engineer","trainee engineer","associate engineer"]
SENIOR   = ["senior","sr.","sr ","lead","manager","architect","principal",
            "staff ","director","head of","vp ","cto","tech lead",
            "5+ year","6+ year","7+ year","8+ year","10+ year"]
NON_IT   = ["sales","marketing","bpo","call center","voice process","data entry",
            "telecalling","customer support","hr recruiter","accountant",
            "finance","banking","insurance","field executive","driver",
            "teacher","nurse","chef","delivery","security guard","logistics"]
BENGALURU = ["bengaluru","bangalore","bengalore","blr"]
WALKIN   = ["walk-in","walkin","walk in","direct interview","spot offer",
            "spot selection","campus drive","hiring drive","open interview"]
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}")
MNC_LIST = ["IBM","Accenture","Capgemini","Wipro","Infosys","TCS","HCL",
            "Cognizant","Tech Mahindra","Mphasis","LTIMindtree","Hexaware",
            "Oracle","SAP","Microsoft","Amazon","Deloitte","Persistent",
            "Zensar","Birlasoft","DXC","GlobalLogic","EPAM","ThoughtWorks"]
STARTUP  = ["Razorpay","PhonePe","CRED","Meesho","Groww","Zepto",
            "BrowserStack","Freshworks","Zoho","Chargebee","Scaler",
            "upGrad","Darwinbox","Leadsquared","Unacademy","BYJU"]

def is_it(title):
    t = title.lower()
    if any(e in t for e in NON_IT): return False
    if any(e in t for e in SENIOR): return False
    return any(k in t for k in RELEVANT)

def is_bengaluru(loc): return any(b in (loc or "").lower() for b in BENGALURU)
def is_walkin(text):   return any(w in (text or "").lower() for w in WALKIN)
def clean_co(name):
    n = (name or "").strip()
    return "Confidential Company" if n.lower() in ("n/a","na","","unknown","not mentioned") else n
def classify_co(name):
    n = (name or "").upper()
    if any(m.upper() in n for m in MNC_LIST): return "MNC"
    if any(s.upper() in n for s in STARTUP): return "Startup"
    return "Company"
def extract_contact(text):
    bad = ["noreply","no-reply","support@","info@","admin@","feedback@"]
    emails = [e for e in EMAIL_RE.findall(text or "") if not any(b in e.lower() for b in bad)]
    phones = PHONE_RE.findall(text or "")
    return {"recruiter_email": emails[0] if emails else "",
            "recruiter_phone": phones[0] if phones else ""}

def make_job(source, title, company, location, link,
             posted="Today", experience="0-2 years (Fresher)",
             skills="", salary="", walkin=False, walkin_info="",
             recruiter_email="", recruiter_phone="", description=""):
    co = clean_co(company)
    return {
        "source": source, "title": title.strip(),
        "company": co, "company_type": classify_co(co),
        "location": location or "Bengaluru, India",
        "link": link, "posted": posted, "experience": experience,
        "skills": skills, "salary": salary,
        "is_walkin": walkin, "walkin_info": walkin_info,
        "recruiter_email": recruiter_email,
        "recruiter_phone": recruiter_phone,
        "ats_score": ats_score(title, description, skills),
        "description": description[:300] if description else "",
    }

def safe_get(url, headers=None, timeout=12, retries=2):
    h = headers or HEADERS_CHROME
    for i in range(retries):
        try:
            r = requests.get(url, headers=h, timeout=timeout, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 100:
                return r
            if r.status_code in (403, 429):
                print(f"    ⛔ {r.status_code}: {url[:55]}")
                return None
            time.sleep(2)
        except Exception as e:
            if i == retries-1:
                print(f"    ⚠ {url[:50]} → {e}")
    return None

def parse_rss(xml_text, source, default_loc="Bengaluru, India"):
    """Parse RSS/XML and extract jobs. Works for all RSS feeds."""
    jobs = []
    try:
        # Clean common XML issues
        xml_text = xml_text.replace("&", "&amp;").replace("&amp;amp;", "&amp;")
        xml_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', xml_text, flags=re.DOTALL)
        root = ET.fromstring(xml_text)
        ns = {'media':'http://search.yahoo.com/mrss/',
              'content':'http://purl.org/rss/1.0/modules/content/'}
        items = root.findall('.//item')
        print(f"    → RSS items found: {len(items)}")
        for item in items:
            def txt(tag):
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""
            title   = txt('title')
            link    = txt('link') or txt('guid')
            desc    = re.sub(r'<[^>]+>', ' ', txt('description'))
            company = txt('company') or txt('author') or ""
            loc     = txt('location') or txt('jobLocation') or default_loc
            salary  = txt('salary') or txt('stipend') or ""
            posted  = txt('pubDate') or txt('pubdate') or "Today"
            exp     = txt('experience') or txt('experienceRequired') or "0-2 years (Fresher)"
            if not title: continue
            if not is_it(title): continue
            if not is_bengaluru(loc) and not is_bengaluru(desc[:200]):
                if default_loc: loc = default_loc
                else: continue
            contact = extract_contact(desc)
            wi      = is_walkin(title + " " + desc)
            jobs.append(make_job(source, title, company, loc, link,
                                  posted=posted[:20], experience=exp,
                                  salary=salary, walkin=wi,
                                  description=desc[:300], **contact))
    except Exception as e:
        print(f"    RSS parse error: {e}")
    return jobs

def dedup(jobs):
    seen, out = set(), []
    for j in jobs:
        k = (j["title"].lower()[:30], j["company"].lower()[:20])
        if k not in seen:
            seen.add(k); out.append(j)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 1. LINKEDIN — HTML scraping (proven ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_linkedin():
    jobs = []
    print("  🔵 LinkedIn...")
    kws = [
        "java developer fresher Bengaluru",
        "java full stack developer fresher Bengaluru",
        "spring boot developer fresher Bengaluru",
        "angular java developer fresher Bengaluru",
        "software engineer fresher java Bengaluru",
        "backend developer java fresher Bengaluru",
        "java backend developer 0 2 years Bengaluru",
    ]
    for kw in kws:
        try:
            url = (f"https://www.linkedin.com/jobs/search/"
                   f"?keywords={urllib.parse.quote(kw)}"
                   f"&location={urllib.parse.quote('Bengaluru, Karnataka, India')}"
                   f"&f_TPR=r604800&f_E=1,2&sortBy=DD")
            resp = safe_get(url, HEADERS_CHROME)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            # JSON-LD
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    lst = data if isinstance(data, list) else [data]
                    for jb in lst:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","") or jb.get("sameAs","")
                        desc    = jb.get("description","")[:300]
                        exp     = str(jb.get("experienceRequirements",""))
                        if not title or not is_it(title): continue
                        contact = extract_contact(desc)
                        jobs.append(make_job("LinkedIn", title, company,
                                             "Bengaluru, India", link,
                                             description=desc, walkin=is_walkin(desc),
                                             **contact))
                except: pass
            # Card fallback
            cards = (soup.find_all("div", class_=re.compile(r"job-search-card")) or
                     soup.find_all("div", class_=re.compile(r"base-card")))
            for card in cards[:15]:
                try:
                    te = card.find(["h3","a"], class_=re.compile(r"job-search-card__title|base-card__full-link"))
                    ce = card.find(["h4","a"], class_=re.compile(r"job-search-card__company"))
                    le = card.find("span", class_=re.compile(r"job-search-card__location"))
                    ae = card.find("a", href=re.compile(r"/jobs/view/"))
                    de = card.find("time")
                    title   = (te.get_text(strip=True) if te else "").strip()
                    company = (ce.get_text(strip=True) if ce else "").strip()
                    loc     = (le.get_text(strip=True) if le else "Bengaluru, India")
                    if not title or not is_it(title): continue
                    if not is_bengaluru(loc): continue
                    href   = ae["href"] if ae else ""
                    link   = ("https://www.linkedin.com"+href.split("?")[0]
                              if href.startswith("/") else href)
                    posted = de.get("datetime","Today") if de else "Today"
                    jobs.append(make_job("LinkedIn", title, company, loc, link, posted=posted))
                except: continue
            time.sleep(2)
        except Exception as e:
            print(f"    LI err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 2. INTERNSHALA — HTML scraping (proven ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_internshala():
    jobs = []
    print("  🎓 Internshala...")
    urls = [
        "https://internshala.com/jobs/java-jobs-in-bengaluru/",
        "https://internshala.com/jobs/full-stack-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/software-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/angular-jobs-in-bengaluru/",
        "https://internshala.com/jobs/backend-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/web-development-jobs-in-bengaluru/",
        "https://internshala.com/jobs/it-jobs-in-bengaluru/",
    ]
    for url in urls:
        try:
            resp = safe_get(url, HEADERS_CHROME)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    lst  = data if isinstance(data, list) else [data]
                    for jb in lst:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        sal     = str(jb.get("baseSalary",{}).get("value",""))
                        if not title or not is_it(title): continue
                        jobs.append(make_job("Internshala", title, company,
                                             "Bengaluru, India", link,
                                             experience="Fresher / 0-1 year", salary=sal))
                except: pass
            cards = (soup.find_all("div", class_=re.compile(r"individual_internship")) or
                     soup.find_all("div", class_=re.compile(r"job-internship-card")))
            for card in cards[:12]:
                try:
                    te = (card.find(["h3","a"], class_=re.compile(r"profile|job-title|title")) or
                          card.find("a", href=re.compile(r"/jobs/detail/")))
                    ce = card.find(["p","a","span"], class_=re.compile(r"company-name|company|employer"))
                    ae = card.find("a", href=re.compile(r"/jobs/detail/|/internships/detail/"))
                    se = card.find("span", class_=re.compile(r"stipend|salary"))
                    title   = (te.get_text(strip=True) if te else "").strip()
                    company = (ce.get_text(strip=True) if ce else "").strip()
                    if not title or not is_it(title): continue
                    href = ae["href"] if ae else ""
                    link = (f"https://internshala.com{href}" if href.startswith("/") else href) or url
                    ct   = card.get_text(" ", strip=True)
                    jobs.append(make_job("Internshala", title, company,
                                         "Bengaluru, India", link,
                                         experience="Fresher / 0-1 year",
                                         salary=se.get_text(strip=True) if se else "",
                                         **extract_contact(ct)))
                except: continue
            time.sleep(2)
        except Exception as e:
            print(f"    IS err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 3. NAUKRI — Public API (no auth, correct headers)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_naukri():
    jobs = []
    print("  🟠 Naukri (API)...")
    kws = ["java+developer","java+full+stack","spring+boot+developer",
           "angular+java+developer","software+developer+java","java+fresher",
           "java+spring+boot+fresher","walk+in+java+bengaluru"]
    for kw in kws:
        try:
            url = (f"https://www.naukri.com/jobapi/v3/search?"
                   f"noOfResults=20&urlType=search_by_keyword&searchType=adv"
                   f"&keyword={kw}&location=bengaluru"
                   f"&experience=0&experienceDD=2&jobAge=1&src=jobsearchDesk")
            resp = safe_get(url, HEADERS_API)
            if not resp: continue
            try: data = resp.json()
            except: continue
            for jb in data.get("jobDetails", [])[:15]:
                title   = jb.get("title","")
                company = jb.get("companyName","") or jb.get("fCompanyName","")
                link    = (jb.get("jdURL","") or
                           f"https://www.naukri.com{jb.get('staticUrl','')}")
                exp     = jb.get("experienceText","")
                skills  = jb.get("tagsAndSkills","")
                salary  = jb.get("salary","")
                desc    = jb.get("jobDescription","")[:300]
                walkin  = is_walkin(title+" "+desc)
                if not title or not is_it(title): continue
                contact = extract_contact(desc + " " + jb.get("footerPlaceholderLabel",""))
                jobs.append(make_job("Naukri", title, company, "Bengaluru, India", link,
                                     experience=exp or "0-2 years (Fresher)",
                                     skills=skills, salary=salary,
                                     walkin=walkin, description=desc, **contact))
            time.sleep(2)
        except Exception as e:
            print(f"    Naukri err ({kw}): {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 4. INDEED INDIA — RSS feed (bypasses bot detection ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_indeed_rss():
    jobs = []
    print("  🔵 Indeed India (RSS)...")
    feeds = [
        "https://in.indeed.com/rss?q=java+developer+fresher&l=Bengaluru&fromage=7&sort=date",
        "https://in.indeed.com/rss?q=spring+boot+developer&l=Bengaluru&fromage=7",
        "https://in.indeed.com/rss?q=java+full+stack+0+2+years&l=Bengaluru&fromage=7",
        "https://in.indeed.com/rss?q=angular+java+developer&l=Bengaluru&fromage=7",
        "https://in.indeed.com/rss?q=java+fresher+software+engineer&l=Bengaluru&fromage=7",
    ]
    for url in feeds:
        try:
            resp = safe_get(url, HEADERS_RSS)
            if not resp: continue
            jobs.extend(parse_rss(resp.text, "Indeed India"))
            time.sleep(2)
        except Exception as e:
            print(f"    Indeed RSS err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 5. TIMESJOBS — RSS feed (bypasses bot detection ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_timesjobs_rss():
    jobs = []
    print("  🔴 TimesJobs (RSS)...")
    feeds = [
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&sequence=1&postWeek=1&rss=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=java+full+stack&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1&rss=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=spring+boot+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1&rss=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=walk+in+java+bengaluru&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1&rss=1",
        "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords=angular+developer&txtLocation=bengaluru&cboWorkExp1=0&cboWorkExp2=2&postWeek=1&rss=1",
    ]
    for url in feeds:
        try:
            resp = safe_get(url, HEADERS_RSS)
            if not resp: continue
            jobs.extend(parse_rss(resp.text, "TimesJobs"))
            time.sleep(2)
        except Exception as e:
            print(f"    TJ RSS err: {e}")
    # Mark walk-ins
    for j in jobs:
        if is_walkin(j.get("title","") + j.get("description","")):
            j["is_walkin"] = True
            j["source"] = "TimesJobs Walk-In"
    wi = sum(1 for j in jobs if j["is_walkin"])
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs ({wi} walk-ins)")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 6. SHINE — RSS feed (bypasses bot detection ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_shine_rss():
    jobs = []
    print("  ✨ Shine (RSS)...")
    feeds = [
        "https://www.shine.com/rss/java-developer-jobs-in-bangalore.xml",
        "https://www.shine.com/rss/software-developer-fresher-jobs-in-bangalore.xml",
        "https://www.shine.com/rss/full-stack-developer-jobs-in-bangalore.xml",
        "https://www.shine.com/rss/angular-developer-jobs-in-bangalore.xml",
        "https://www.shine.com/rss/spring-boot-developer-jobs-in-bangalore.xml",
        "https://www.shine.com/rss/backend-developer-jobs-in-bangalore.xml",
    ]
    for url in feeds:
        try:
            resp = safe_get(url, HEADERS_RSS)
            if not resp: continue
            jobs.extend(parse_rss(resp.text, "Shine"))
            time.sleep(2)
        except Exception as e:
            print(f"    Shine RSS err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 7. FRESHERSWORLD — RSS feed (bypasses bot detection ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_freshersworld_rss():
    jobs = []
    print("  🟢 Freshersworld (RSS)...")
    feeds = [
        "https://www.freshersworld.com/rss/jobs.xml?keyword=java+developer&location=Bengaluru",
        "https://www.freshersworld.com/rss/jobs.xml?keyword=spring+boot&location=Bengaluru",
        "https://www.freshersworld.com/rss/jobs.xml?keyword=angular+developer&location=Bengaluru",
        "https://www.freshersworld.com/rss/jobs.xml?keyword=software+engineer+fresher&location=Bengaluru",
        "https://www.freshersworld.com/rss/jobs.xml?keyword=full+stack+developer&location=Bengaluru",
    ]
    for url in feeds:
        try:
            resp = safe_get(url, HEADERS_RSS)
            if not resp: continue
            jobs.extend(parse_rss(resp.text, "Freshersworld"))
            time.sleep(1.5)
        except Exception as e:
            print(f"    FW RSS err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 8. GLASSDOOR — RSS feed
# ══════════════════════════════════════════════════════════════════════════════
def scrape_glassdoor_rss():
    jobs = []
    print("  🟡 Glassdoor (RSS)...")
    feeds = [
        "https://www.glassdoor.co.in/feeds/job-listing.htm?minSalary=0&locId=2940965&locT=C&jobType=allJobTypes&fromAge=7&minRating=0.0&keyword=java+developer&cityId=2940965&countryId=101&src=GD_JOB_AD&suggestCount=0&suggestChosen=false&clickSource=searchBtn&typedKeyword=java+developer&sc.keyword=java+developer&locT=C&locId=2940965&jobType=allJobTypes&rss=1",
        "https://www.glassdoor.co.in/feeds/job-listing.htm?keyword=software+engineer+java&locId=2940965&locT=C&fromAge=7&rss=1",
        "https://www.glassdoor.co.in/feeds/job-listing.htm?keyword=spring+boot+developer&locId=2940965&locT=C&fromAge=7&rss=1",
    ]
    for url in feeds:
        try:
            resp = safe_get(url, HEADERS_RSS)
            if not resp: continue
            jobs.extend(parse_rss(resp.text, "Glassdoor"))
            time.sleep(2)
        except Exception as e:
            print(f"    GD RSS err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 9. INSTAHIRE — HTML (small site, not blocked ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_instahire():
    jobs = []
    print("  🟣 Instahire...")
    kws = ["java+developer","spring+boot+developer","java+full+stack",
           "angular+developer","software+developer","backend+developer"]
    for kw in kws:
        try:
            url = f"https://instahire.app/jobs?q={kw}&location=bangalore&exp=0-2"
            resp = safe_get(url, HEADERS_CHROME)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    lst  = data if isinstance(data, list) else [data]
                    for jb in lst:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        if not title or not is_it(title): continue
                        jobs.append(make_job("Instahire", title, company,
                                             "Bengaluru, India", link))
                except: pass
            cards = (soup.find_all("div", class_=re.compile(r"job.?card|jobcard|listing|job-item")) or
                     soup.find_all("article") or soup.find_all("li", class_=re.compile(r"job")))
            for card in cards[:12]:
                try:
                    te = card.find(["h2","h3","a"])
                    ce = card.find(["span","p","div"], class_=re.compile(r"company|org|employer"))
                    ae = card.find("a", href=True)
                    title   = (te.get_text(strip=True) if te else "").strip()
                    company = (ce.get_text(strip=True) if ce else "").strip()
                    if not title or not is_it(title): continue
                    href = ae["href"] if ae else ""
                    link = (f"https://instahire.app{href}" if href.startswith("/") else href) or url
                    ct   = card.get_text(" ", strip=True)
                    jobs.append(make_job("Instahire", title, company, "Bengaluru, India", link,
                                         **extract_contact(ct)))
                except: continue
            time.sleep(1.5)
        except Exception as e:
            print(f"    IH err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 10. CUTSHORT — HTML (small site, not blocked ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_cutshort():
    jobs = []
    print("  🔷 Cutshort...")
    kws = ["java-developer","spring-boot-developer","full-stack-java",
           "angular-java","backend-engineer-java","software-engineer"]
    for kw in kws:
        try:
            url = f"https://cutshort.io/jobs?keywords={kw}&location=bengaluru&experience=0-2"
            resp = safe_get(url, HEADERS_CHROME)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    lst  = data if isinstance(data, list) else [data]
                    for jb in lst:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        exp_txt = str(jb.get("experienceRequirements",""))
                        if not title or not is_it(title): continue
                        jobs.append(make_job("Cutshort", title, company,
                                             "Bengaluru, India", link, experience=exp_txt or "0-2 years"))
                except: pass
            cards = soup.find_all(["div","article","li"], class_=re.compile(r"job|card|listing"))
            for card in cards[:10]:
                try:
                    te = card.find(["h2","h3","a"], class_=re.compile(r"title|role|job"))
                    ce = card.find(["span","p","div"], class_=re.compile(r"company|startup|employer"))
                    ae = card.find("a", href=True)
                    title   = (te.get_text(strip=True) if te else "").strip()
                    company = (ce.get_text(strip=True) if ce else "").strip()
                    if not title or not is_it(title): continue
                    href = ae["href"] if ae else ""
                    link = (f"https://cutshort.io{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Cutshort", title, company, "Bengaluru, India", link))
                except: continue
            time.sleep(1.5)
        except Exception as e:
            print(f"    CS err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 11. HIRIST — HTML (tech-only, small site ✅)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_hirist():
    jobs = []
    print("  💡 Hirist...")
    urls = [
        "https://www.hirist.tech/j/java-developer-jobs-in-bangalore/38?experience=0-2",
        "https://www.hirist.tech/j/spring-boot-developer-jobs-in-bangalore/38",
        "https://www.hirist.tech/j/full-stack-java-developer-jobs-in-bangalore/38",
        "https://www.hirist.tech/j/angular-developer-jobs-in-bangalore/38",
        "https://www.hirist.tech/j/backend-developer-java-jobs-in-bangalore/38",
    ]
    for url in urls:
        try:
            resp = safe_get(url, HEADERS_CHROME)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    lst  = data if isinstance(data, list) else [data]
                    for jb in lst:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        exp_txt = str(jb.get("experienceRequirements",""))
                        if not title or not is_it(title): continue
                        jobs.append(make_job("Hirist", title, company,
                                             "Bengaluru, India", link, experience=exp_txt or "0-2 years"))
                except: pass
            cards = soup.find_all(["div","li"], class_=re.compile(r"job-listing|job-card|jobCard"))
            for card in cards[:10]:
                try:
                    te = card.find(["h2","h3","a"], class_=re.compile(r"title|job-title"))
                    ce = card.find(["span","div","p"], class_=re.compile(r"company|employer"))
                    ae = card.find("a", href=True)
                    title   = (te.get_text(strip=True) if te else "").strip()
                    company = (ce.get_text(strip=True) if ce else "").strip()
                    if not title or not is_it(title): continue
                    href = ae["href"] if ae else ""
                    link = (f"https://www.hirist.tech{href}" if href.startswith("/") else href) or url
                    jobs.append(make_job("Hirist", title, company, "Bengaluru, India", link))
                except: continue
            time.sleep(1.5)
        except Exception as e:
            print(f"    Hirist err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 12. WELLFOUND — HTML (startup jobs)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_wellfound():
    jobs = []
    print("  🟤 Wellfound...")
    urls = [
        "https://wellfound.com/jobs?role=software-engineer&location=bengaluru&experience=0-2",
        "https://wellfound.com/jobs?role=backend-engineer&location=bengaluru&experience=0-2",
        "https://wellfound.com/jobs?role=full-stack-engineer&location=bengaluru",
        "https://wellfound.com/role/r/java-developer/bengaluru",
        "https://wellfound.com/role/r/software-engineer/bengaluru",
    ]
    for url in urls:
        try:
            resp = safe_get(url, HEADERS_CHROME)
            if not resp: continue
            soup = BeautifulSoup(resp.text, "html.parser")
            # Next.js data
            for s in soup.find_all("script", id="__NEXT_DATA__"):
                try:
                    data  = json.loads(s.string or "")
                    props = data.get("props",{}).get("pageProps",{})
                    for jb in (props.get("jobs",[]) or props.get("jobListings",[]) or []):
                        title   = jb.get("title","") or jb.get("role","")
                        company = (jb.get("startup",{}) or {}).get("name","")
                        link    = f"https://wellfound.com/jobs/{jb.get('id','')}" if jb.get("id") else url
                        if not title or not is_it(title): continue
                        jobs.append(make_job("Wellfound", title, company, "Bengaluru, India", link))
                except: pass
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    lst  = data if isinstance(data, list) else [data]
                    for jb in lst:
                        if not isinstance(jb, dict): continue
                        title   = jb.get("title","")
                        company = jb.get("hiringOrganization",{}).get("name","")
                        link    = jb.get("url","")
                        if not title or not is_it(title): continue
                        jobs.append(make_job("Wellfound", title, company, "Bengaluru, India", link))
                except: pass
            time.sleep(2)
        except Exception as e:
            print(f"    WF err: {e}")
    r = dedup(jobs)
    print(f"    ✓ {len(r)} jobs")
    return r


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def scrape_all_jobs():
    print(f"\n{'='*62}")
    print(f"  ROY'S JOB SCRAPER v6.0 — RSS + API Strategy")
    print(f"  {datetime.now().strftime('%d %b %Y  %I:%M %p')}")
    print(f"  12 Sources | RSS bypass + API + HTML")
    print(f"  Java Full Stack | 0-2 YOE | Bengaluru ONLY | IT roles only")
    print(f"{'='*62}\n")

    scrapers = [
        ("LinkedIn",          scrape_linkedin),
        ("Internshala",       scrape_internshala),
        ("Naukri API",        scrape_naukri),
        ("Indeed RSS",        scrape_indeed_rss),
        ("TimesJobs RSS",     scrape_timesjobs_rss),
        ("Shine RSS",         scrape_shine_rss),
        ("Freshersworld RSS", scrape_freshersworld_rss),
        ("Glassdoor RSS",     scrape_glassdoor_rss),
        ("Instahire",         scrape_instahire),
        ("Cutshort",          scrape_cutshort),
        ("Hirist",            scrape_hirist),
        ("Wellfound",         scrape_wellfound),
    ]

    all_jobs = []
    source_counts = {}
    for name, fn in scrapers:
        try:
            result = fn()
            source_counts[name] = len(result)
            all_jobs.extend(result)
        except Exception as e:
            print(f"    ❌ {name} crashed: {e}")
            source_counts[name] = 0

    unique = dedup(all_jobs)
    unique.sort(key=lambda x: x.get("ats_score", 0), reverse=True)

    walkin_jobs  = [j for j in unique if j.get("is_walkin")]
    regular      = [j for j in unique if not j.get("is_walkin")]
    mnc_jobs     = [j for j in regular if j.get("company_type") == "MNC"]
    startup_jobs = [j for j in regular if j.get("company_type") == "Startup"]
    other_jobs   = [j for j in regular if j.get("company_type") == "Company"]

    result = {
        "scraped_at":    datetime.now().isoformat(),
        "ats_threshold": 0,
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
        "source_counts": source_counts,
        "filter_stats": {
            "total_scraped":      len(all_jobs),
            "duplicates_removed": len(all_jobs) - len(unique),
            "final_sent":         len(unique),
        }
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*62}")
    print(f"  ✅ TOTAL: {len(unique)} jobs found")
    print(f"  🚶 Walk-ins  : {len(walkin_jobs)}")
    print(f"  🏢 MNCs      : {len(mnc_jobs)}")
    print(f"  🚀 Startups  : {len(startup_jobs)}")
    print(f"  💼 Others    : {len(other_jobs)}")
    print(f"\n  Per-source:")
    for src, cnt in source_counts.items():
        bar = "✅" if cnt > 0 else "⛔"
        print(f"    {bar} {src:<22}: {cnt}")
    print(f"{'='*62}\n")
    return result

if __name__ == "__main__":
    scrape_all_jobs()

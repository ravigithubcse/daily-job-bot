# 🤖 Roy's Daily Job Bot
### Java Full Stack | 0-2 YOE | Bengaluru | Auto-runs at 7 AM IST every day

---

## What Runs Every Morning at 7:00 AM

1. Scrapes **LinkedIn, Wellfound, Internshala, TimesJobs, Freshersworld**
2. Finds **Java Full Stack / Spring Boot / Backend** roles (0-2 YOE, Bengaluru)
3. Separates **Walk-In Drives, MNCs, Startups, Others**
4. AI tailors your resume for top 5 jobs using **Claude API**
5. Sends a **beautiful HTML email** to `rn5127610@gmail.com` with everything

---

## ⚙️ One-Time Setup (takes ~15 minutes)

### ① Gmail App Password
1. Go to [myaccount.google.com](https://myaccount.google.com) → Security
2. Enable 2-Step Verification
3. Search "App passwords" → Generate for Mail → copy the 16-char code

### ② Anthropic API Key (for AI resume tailoring)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create API Key → add $5 credit (~₹0.83/day)

### ③ Add GitHub Secrets
Go to: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `GMAIL_APP_PASSWORD` | 16-char Gmail app password |
| `GMAIL_SENDER` | `rn5127610@gmail.com` |
| `ANTHROPIC_API_KEY` | Your Claude API key |

### ④ Enable Actions + Test Now
1. Click **Actions tab** → Enable workflows
2. Click **"Roy's Daily Job Bot"** → **"Run workflow"** → Test immediately!

---

## 💰 Cost
- GitHub Actions: **FREE** (runs ~3 min/day, well within 2000 min/month limit)
- Gmail: **FREE**
- Claude AI: ~**₹0.83/day** (< ₹25/month)

---

*Built for Roy | Java Full Stack Developer | Bengaluru*

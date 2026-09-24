# 🌦 WeatherWatch — National Weather Big Data Analytics Platform

> **"Existing tools either aggregate official data (IMD portal, Windy) OR crowdsource unverified reports (social media) — never both, cross-checked against each other. This platform is the first to combine citizen crowdsourcing with automated verification against official IMD/satellite ground truth, scoring every report's credibility before it reaches the map."**

---

## Quick Start (Local Dev — No Docker Needed)

### Backend (FastAPI + SQLite)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

Open `frontend/index.html` directly in a browser, or serve with:

```bash
cd frontend
python -m http.server 5173
```

Then open http://localhost:5173

### Full Stack (Docker)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000  
- Backend API: http://localhost:8000  
- API docs: http://localhost:8000/docs

---

## Section 2 — Acceptance Criteria Demo Script

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click **⟳ Replay Feed** | 8 social posts ingested, appears in list + map |
| 2 | Click **+ Submit Report** → fill form → Submit | Report appears on dashboard within 10 seconds |
| 3 | Check submitted report | Shows timestamp, GPS, city/state, category — all from form |
| 4 | Click any report | Score breakdown shows category + confidence % |
| 5 | Click a flagged report | Shows numeric score 0–100 with step-by-step breakdown |
| 6 | Submit near-duplicate | Second report shows `is_duplicate=true`, flagged |
| 7 | Open report panel → Geo-Verification section | Shows IMD station, km distance, event match ✓/✗ |
| 8 | Click **Admin Queue** → Approve a report | Status changes to Published on dashboard immediately |
| 9 | Use Category / Status / State / Date filters | List and map narrow to matching reports |

---

## Section 3 — Scoring Pipeline

```
Step 1: Source Credibility  (0–40 pts)
  +10  Account age > 6 months
  +15  Verified/official account
  +15  Prior verified reports (3 pts each, capped)

Step 2: Content Consistency (0–30 pts)
  +15  NLP keyword match (claimed category matches text)
  +15  Image EXIF valid (7.5 if no image — neutral)

Step 3: Geo-Temporal       (0–30 pts)
  +30  Scaled by: distance to nearest IMD station + event on record

Total < 40  → Auto-flagged for admin review
Total ≥ 70  → Auto-published
40–70       → Pending (admin queue)
```

---

## Section 4 — Feasibility Numbers

Run these to generate real numbers for your pitch deck:

```bash
cd backend

# Load test (RPS + latency)
python load_test.py

# Fake detection accuracy (precision/recall/F1 on 65-report test set)
python accuracy_test.py
```

---

## Section 5 — Labeling Strategy

The `accuracy_test.py` test set uses:
1. **Synthetic negatives** — physically impossible combos (snow in Mumbai, cyclone in Jaisalmer)
2. **Rule-based labels** — reports that contradict IMD station event records = likely fake
3. **Manual seed** — 65 hand-labeled examples (35 real, 30 fake) in `accuracy_test.py`

---

## Project Structure

```
SIH/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── db/database.py       # SQLite + SQLAlchemy
│   │   ├── models/report.py     # ORM model
│   │   ├── api/
│   │   │   ├── reports.py       # Reports CRUD + admin review
│   │   │   └── social.py        # Social feed simulation
│   │   └── ml/
│   │       ├── scorer.py        # Section 3 pipeline (0–100)
│   │       ├── classifier.py    # NLP keyword event classifier
│   │       └── imd_stations.py  # 28 IMD station reference + geo scoring
│   ├── load_test.py             # Section 4 RPS/latency benchmark
│   ├── accuracy_test.py         # Section 4+5 precision/recall/F1
│   └── requirements.txt
├── frontend/
│   └── index.html               # Complete 3-screen UI (single file, no build step)
├── docker-compose.yml
└── README.md
```

---

## Ethics / Legal (Section 7)

- ⚠ Disclaimer on every page: *"Crowdsourced supplementary data — not an official IMD alert. Verify with official sources before acting."*
- Appeal path: submitters see exact score breakdown explaining why report was flagged
- Consent checkbox required at submission; GPS/media retained 90 days, anonymised for public display

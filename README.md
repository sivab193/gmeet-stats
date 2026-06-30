# 📹 Meet Analyzer

An interactive analytics dashboard for your **Google Meet** conference history, built from Google Takeout data.

Upload your `conference_history_records.csv` and instantly get:
- 📊 KPI cards (total meetings, hours, avg duration, longest session)
- 📈 Monthly trends, duration breakdown, day-of-week heatmaps
- 🏆 Top meeting rooms by time spent
- 🧠 Behavioral heuristics (Marathon Grinder, Weekend Warrior, Hub Loyalty)
- 🌐 Timezone-aware conference records explorer

The **homepage** shows the owner's live stats publicly, so visitors can see an example before uploading their own data.

---

## 🚀 Quick Start (Local)

### 1. Clone & set up

```bash
git clone https://github.com/YOUR_USERNAME/meet-analyzer.git
cd meet-analyzer
```

### 2. Create virtual environment & install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your Google Meet data

Place your `conference_history_records.csv` (from Google Takeout) in the project root.

> **How to export:** Go to [takeout.google.com](https://takeout.google.com) → select **Google Meet** → export → extract the archive → find `conference_history_records.csv`.

### 4. Run the server

```bash
python app.py
```

Open [http://127.0.0.1:1903](http://127.0.0.1:1903)

---

## 📁 Project Structure

```
meet-analyzer/
├── app.py                          # Flask server (falls back to stdlib if Flask not installed)
├── analyzer.py                     # CSV parsing & analytics engine
├── requirements.txt                # Python dependencies
├── vercel.json                     # Vercel deployment config
├── conference_history_records.csv  # Your Google Takeout data (not committed if private)
├── templates/
│   ├── upload.html                 # Homepage — upload page + owner's live stats
│   └── dashboard.html              # Full analytics dashboard
└── static/
    ├── css/style.css               # Design system (Dark Glassmorphism)
    └── js/main.js                  # Charts, timezone conversion, table pagination
```

---

## 🌐 Deploy to Vercel

### Prerequisites
- [Vercel CLI](https://vercel.com/docs/cli): `npm install -g vercel`
- Or deploy via the [Vercel Dashboard](https://vercel.com/new) by importing your GitHub repo.

### Steps

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Initial commit: Meet Analyzer dashboard"
git remote add origin https://github.com/YOUR_USERNAME/meet-analyzer.git
git push -u origin main

# 2. Deploy to Vercel
vercel --prod
```

Or connect your GitHub repo to Vercel and it will auto-deploy on every push.

> **Note:** The bundled `conference_history_records.csv` is included in the repo so Vercel can serve the owner's public stats on the homepage. If you want to keep your data private, remove it from the repo and the homepage stats will be empty.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Upload page (homepage) with owner's live stats |
| `GET` | `/dashboard` | Full analytics dashboard |
| `GET` | `/api/public-stats` | Owner's pre-loaded stats (from bundled CSV) |
| `GET` | `/api/stats?year=ALL` | Stats for currently active dataset (filtered by year) |
| `GET` | `/api/meetings?page=1&search=` | Paginated, searchable meeting records |
| `POST` | `/api/upload` | Upload a new `conference_history_records.csv` at runtime |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x — Flask (Vercel) / stdlib fallback (local) |
| Frontend | Vanilla HTML5, CSS3, JavaScript (ES2020+) |
| Charts | [Chart.js 4.4](https://www.chartjs.org/) |
| Fonts | Google Fonts — Outfit, Inter |
| Hosting | Vercel (Python serverless) |

---

## 📜 License

MIT — do whatever you want with it.

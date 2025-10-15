# Corporate Culture Monitor

## Project Structure

```
capstone-project-25t3-9900-f18a-donut/
│
├─ crawler/                                 # Data collection & cleaning
│  ├─ reddit-crawler-master/                # Reddit crawler code – fetches posts/comments using Reddit API
│  │  ├─ Rio_tinto_crawler.py               # Main crawler program
│  │  ├─ export_to_csv.py                   # Export SQLite data to CSV
│  │  ├─ process_submissions.py             # Format raw data -> standardized dataset
│  │  └─ reddit_data.db                     # SQLite database (submissions, users)
│  └─ data_cleaning.py                      # Clean raw data -> reviews.csv
│
├─ data/                                    # Data storage
│  ├─ raw/                                  # Raw scraped data
│  │  └─ reviews.csv                        # Raw review data
│  ├─ processed/                            # Processed & annotated data
│  │  └─ annotated.csv                      # Annotated data (Sprint 1)
│
├─ backend/                                 # Flask backend
│  ├─ app.py                                # Flask API server (KPIs + Reviews)
│  ├─ download_models.py                    # Downloads sentiment/NLP models
│  └─ pipeline.py                           # Sentiment labeling + dimension classification
│
├─ frontend/                                # React frontend with Tailwind
│  ├─ index.html                            # Entry point with Tailwind & fonts
│  ├─ src/                                  # React source files
│  │  ├─ App.jsx                            # Main React app with dynamic background
│  │  ├─ index.css                          # Global stylesheet, imports Tailwind & custom styles
│  │  ├─ main.jsx                           # React entry file mounted into #root
│  │  ├─ components/                        # Modularized UI components
│  │  │  ├─ Header.jsx                      # Header component
│  │  │  ├─ KpiCards.jsx                    # KPI summary cards
│  │  │  ├─ SentimentTabs.jsx               # Sentiment filter tabs
│  │  │  ├─ DimensionFilter.jsx             # Cultural dimension filter
│  │  │  ├─ RegionFilter.jsx                # Region-based review filter
│  │  │  ├─ DateFilter.jsx                  # Date range filter for reviews
│  │  │  ├─ ReviewsList.jsx                 # Review list display
│  │  │  └─ Pager.jsx                       # Pagination component
│  │  └─ api.js                             # API helper functions
│  └─ tailwind.config.js                    # Tailwind CSS configuration
│
└─ README.md                                # Project documentation
```

---

## Data Pipeline
```
[crawler] → Collects raw reviews → `data/raw/reviews.csv`  
    ↓  
[backend/pipeline.py] → Cleans and saves → `data/processed/annotated.csv`  
    ↓  
[backend/app.py] → Serves REST API endpoints (`/api/reviews`)  
    ↓  
[frontend/src/api.js] → Fetches data via HTTP  
    ↓  
[App.jsx + components/*] → Displays interactive dashboard in browser
```
---

## Setup & Run

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # (Windows)
# or
source .venv/bin/activate     # (Mac)
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

🔗 http://localhost:5173

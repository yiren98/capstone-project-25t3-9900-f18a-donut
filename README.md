# Corporate Culture Monitor

## Project Structure

```
capstone-project-25t3-9900-f18a-donut/
│
├─ crawler/                                       # Initial data collection (platform-specific adapters)
│  ├─ reddit-crawler-master/ 
│  │  ├─ Rio_tinto_crawler.py                     # Reddit crawler script for collecting Rio Tinto-related posts
│  │  ├─ export_to_csv.py                         # Export Reddit SQLite data into CSV format
│  │  ├─ process_submissions.py                   # Process and normalize Reddit submission data
│  │  └─ reddit_data.db                           # Local SQLite database storing raw Reddit data
│  ├─ adapters/                                   # Data cleaning & field normalization
│  │  ├─ reddit_adapter.py                        # Adapter for Reddit data structure
│  │  ├─ twitter_adapter.py                       # Adapter for Twitter/X data structure
│  │  └─ guardian_adapter.py                      # Adapter for The Guardian news articles
│  └─ aggregator.py                               # Multi-source data aggregation and unification
│  
├─ data/
│  ├─ raw/                                        # Raw and cleaned data from each source
│  │  ├─ reddit/                                  # Reddit raw data files
│  │  ├─ twitter/                                 # Twitter raw data files
│  │  └─ guardian/                                # The Guardian raw data files
│  ├─ processed/
│  │  ├─ annotated.csv                            # Processed data with sentiment & dimension annotations
│  │  └─ unified.csv                              # Unified CSV after aggregation (standardized schema)
│  └─ taxonomy/
│     ├─ dimensions.txt                           # Preliminary list of cultural dimensions
│     └─ suggestions.csv                          # Dimension-based improvement suggestions
│
├─ backend/                                       # Backend service layer (Flask API & model pipeline)
│  ├─ app.py                                      # Flask API entrypoint (KPI endpoints, Tag validation & expansion)
│  ├─ pipeline.py                                 # Sentiment & dimension classification pipeline
│  ├─ download_models.py                          # Script for downloading or initializing NLP models
│  ├─ suggestions.py                              # Automatic generation of dimension-level improvement suggestions
│  ├─ Dockerfile/                                 # Backend Docker image definition
│  └─ tests.py                                    # Backend unit/integration tests
│
├─ frontend/                                      # React + Tailwind responsive web interface
│  ├─ index.html                                  # Main HTML entry file (root mounting point for React)
│  ├─ tailwind.config.js                          # Tailwind CSS configuration file
│  ├─ Dockerfile/                                 # Frontend Docker image (Vite build + Nginx serve)
│  └─ src/
│     ├─ App.jsx                                  # Main React app – defines routes and global layout
│     ├─ index.css                                # Global stylesheet (imports Tailwind and custom styles)
│     ├─ main.jsx                                 # React entrypoint (mounts App to index.html)
│     ├─ api.js                                   # API wrapper with Source parameter support
│     ├─ components/                              # Reusable UI components
│     │  ├─ Header.jsx                            # Top navigation bar (logo, title, login/logout)
│     │  ├─ KpiCards.jsx                          # KPI summary cards (total, positive, negative, eNPS)
│     │  ├─ DateFilter.jsx                        # Date range filter for temporal filtering
│     │  ├─ RegionFilter.jsx                      # Region/location-based filter
│     │  ├─ DimensionFilter.jsx                   # Cultural dimension filter
│     │  ├─ SentimentTabs.jsx                     # Sentiment toggle tabs (positive/negative/all)
│     │  ├─ SourceFilter.jsx                      # Information source filter (Reddit / Guardian / Twitter)
│     │  ├─ DimensionSuggestions.jsx              # Dimension-specific recommendation display area
│     │  ├─ DetailView.jsx                        # Detail view or modal for full review/news content
│     │  ├─ LoginForm.jsx                         # Login form component (email/password input)
│     │  └─ Pager.jsx                             # Pagination component for review lists
│     └─ routes/
│        └─ Login.jsx                             # Login page route (/login)
│ 
├─ deployment/                                    # Cloud deployment configuration (Docker Compose, CI/CD)
│
└─ README.md                                      # Project documentation and setup instructions
```

---

## Data Pipeline
```
[crawler/*] → Collects multi-source data 
    → saved in `data/raw/{reddit,twitter,guardian}/*.csv`
    ↓
[crawler/adapters/*] → Cleans & normalizes fields 
    → unified schema: ID, Location, Time, Text, Initial Dimensions, Source, Tag
    → references taxonomy definitions in `data/taxonomy/dimensions.txt`
    ↓
[crawler/aggregator.py] → Aggregates all sources 
    → outputs `data/processed/unified.csv`
    ↓
[backend/pipeline.py] → Performs sentiment & dimension analysis 
    → outputs annotated results to `data/processed/annotated.csv`
    ↓
[backend/suggestions.py] → Generates improvement suggestions by dimension 
    → saves to `data/taxonomy/suggestions.csv`
    ↓
[backend/app.py] → Serves RESTful APIs
    ↓
[frontend/src/api.js] → Fetches API data (with Source, Time, Region, Sentiment filters)
    ↓
[frontend/src/App.jsx + components/*] → Renders interactive dashboard in browser

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

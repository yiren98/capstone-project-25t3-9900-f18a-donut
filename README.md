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
backend/
│
├── dimensions_sr/                  # Dimension-level summary & recommendation JSONs
├── subthemes_sr/                   # Subtheme-level summary & recommendation JSONs
├── tests/                          # Pytest suite for backend pipeline
│   ├── __init__.py                 # Mark tests/ as a Python package
│   ├── test_data_process.py        # Tests for data_process.py
│   ├── test_sentiment_dbcheck.py   # Tests for neutral re-check logic
│   ├── test_mapping_sub2dim.py     # Tests for mapping_sub2dim.py
│   ├── test_subtheme_classify_cluster.py  # Tests for subtheme clustering & dimension mapping
│   ├── test_overall_sr.py          # Tests for overall_sr summary generator
│   ├── test_subthe_dimen_sr.py     # Tests for subtheme/dimension summaries
│   ├── test_pipeline_structure.py  # Sanity checks on pipeline wiring
│   ├── test_suggestions.py         # Tests for suggestions utilities
│   ├── test_imports.py             # Import coverage for backend modules
│   └── test_train_cr_encoder.py    # Tests for Cross-Encoder training helper
│
├── data_process.py                 # [Step 1] Generate comments.csv & subthemes.csv from raw data
├── download_models.py              # [Step 1.5] Download required models, wrapped with a main entry
├── sentiment_dbcheck.py            # [Step 2] Re-check neutral subthemes and refine sentiment
├── train_cr_encoder.py             # [Step 3, optional] Train Cross-Encoder for subtheme → dimension mapping
├── subtheme_classify_cluster.py    # [Step 4] Predict dimensions & cluster subthemes, output dimension_clusters.json
├── mapping_sub2dim.py              # [Step 5] Write representative subthemes & mapped dimensions back into comments.csv
├── pipeline.py                     # One-command 5-step NLP workflow orchestrator
│
├── overall_sr.py                   # Generate an overall corporate culture summary JSON from comments.csv
├── subthe_dimen_sr.py              # Generate JSON summaries for each subtheme & dimension (DeepSeek-based)
├── suggestions.py                  # Utilities for suggestions & recommendation text generation
│
├── app.py                          # REST API server entrypoint
|
├── overall_sr.json                 # Generated overall summary JSON (artefact)
├── requirements.txt                # Python dependencies for backend
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
[backend/pipeline.py]
    → Runs the full 5-step NLP workflow:
      1. data_process.py
      2. sentiment_dbcheck.py
      3. train_cr_encoder.py (optional)
      4. subtheme_classify_cluster.py
      5. mapping_sub2dim.py
    → Produces enriched `comments.csv` + `dimension_clusters.json`
    ↓
[backend/suggestions.py]
    → Orchestrates all summary-generation modules:
        - Runs overall_sr.py to generate the overall summary JSON
        - Runs subthe_dimen_sr.py to generate per-subtheme & per-dimension summaries
    → Stores JSON outputs into:
        - backend/overall_sr.json
        - backend/dimensions_sr/
        - backend/subthemes_sr/
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

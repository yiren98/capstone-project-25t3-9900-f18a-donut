# **Corporate Culture Monitor**

## **Project Structure**

capstone-project-25t3-9900-f18a-donut/<br>
│<br>
├─ crawler/&emsp;&emsp;&emsp;&emsp;  &emsp;&emsp; &emsp; &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# Data collection & cleaning<br>
│&emsp;├─ crawler.py&emsp;&emsp;  &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# Scrape comments from Reddit, Twitter<br>
│&emsp;└─ data_cleaning.py&emsp; &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# Clean raw data -> reviews.csv<br>
│<br>
├─ data/<br>
│&emsp;├─ raw/&emsp;  &emsp;   &emsp;  &emsp;  &emsp;  &emsp;&emsp;    &emsp;&emsp;&emsp;&emsp;&emsp;# Raw scraped data<br>
│&emsp;│&emsp; └─ reviews.csv<br>
│&emsp;└─ processed/<br>
│&emsp;&emsp;&emsp;└─ annotated.csv/&emsp;  &emsp;&emsp;  &emsp;  &emsp;&emsp;# Annotated data (simulated for Sprint 1)<br>
├─ backend/<br>
│&emsp;├─ app.py&emsp;  &emsp;   &emsp;  &emsp;  &emsp;  &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# Flask API server (KPI + Reviews) <br>
│&emsp;└─ pipeline.py &emsp;&emsp;   &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# Sentiment labeling + dimension classification<br>
│<br>
├─ frontend/<br>
│&emsp;├─ index.html&emsp;&emsp;   &emsp;  &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# Entry point with Tailwind & fonts <br>
│&emsp;├─ src/<br>
│&emsp;│&emsp;├─ App.jsx&emsp; &emsp;   &emsp;  &emsp;  &emsp;&emsp;&emsp;&emsp; &emsp;# Main React app with dynamic background<br>
│&emsp;│&emsp;├─ index.css&emsp;&emsp;   &emsp;  &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# Global stylesheet, imports Tailwind & custom styles<br>
│&emsp;│&emsp;├─ main.jsx&emsp; &emsp;   &emsp;  &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# React app entry file that mounts <App /> into #root<br>
│&emsp;│&emsp;├─ components/ &emsp;  &emsp;  &emsp;  &emsp;  &emsp;&emsp;# Modularized UI components<br>
│&emsp;│&emsp;│&emsp;├─ Header.jsx<br>
│&emsp;│&emsp;│&emsp;├─ KpiCards.jsx<br>
│&emsp;│&emsp;│&emsp;├─ SentimentTabs.jsx<br>
│&emsp;│&emsp;│&emsp;├─ DimensionFilter.jsx<br>
│&emsp;│&emsp;│&emsp;├─ ReviewsList.jsx<br>
│&emsp;│&emsp;│&emsp;└─ Pager.jsx<br>
│&emsp;│&emsp;└─ api.js&emsp; &emsp;   &emsp;  &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# API helper functions<br>
│&emsp;├─ main.jsx &emsp; &emsp;   &emsp;  &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;# React root<br>
│&emsp;└─ tailwind.config.js<br>


## **Data Pipeline**

[crawler] → Collects raw reviews → data/raw/reviews.csv<br>
&emsp;&emsp;↓<br>
[backend/pipeline.py] → Cleans and saves → data/processed/annotated.csv<br>
&emsp;&emsp;↓<br>
[backend/app.py] → Serves REST API endpoints (/api/reviews)<br>
&emsp;&emsp;↓<br>
[frontend/src/api.js] → Fetches data via HTTP<br>
&emsp;&emsp;↓<br>
[App.jsx + components/*] → Displays interactive dashboard in browser<br>

## **Setup & Run**

###  Backend ###
cd backend<br>
python -m venv .venv<br>
.venv\Scripts\activate &emsp;  &emsp; &emsp;&emsp;&emsp;# (Windows)<br>
&emsp;or<br>
source .venv/bin/activate  &emsp; &emsp; &emsp;# (Mac)<br>
pip install -r requirements.txt<br>
python app.py<br>

### Frontend ###
cd frontend<br>
npm install<br>
npm run dev<br>
<br>
📍http://localhost:5173
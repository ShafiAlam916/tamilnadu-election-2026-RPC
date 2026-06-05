# 🗳️ Tamil Nadu 2026 Assembly Election Analysis

An interactive data dashboard built with **Streamlit** and **Plotly** to analyse the Tamil Nadu 2026 Legislative Assembly Election results — including constituency-level breakdowns, party performance, voter turnout, and comparisons with the 2021 election.

---

## 📁 Repository Structure

| File | Description |
|---|---|
| `app.py` | Main Streamlit web application with all analyses and interactive Plotly visualisations |
| `tn_analysis_notebook.ipynb` | Jupyter notebook that outputs a consolidated table of all analysed data shown in the dashboard |
| `constituency_master.csv` | Master list of all Tamil Nadu constituencies *(provided in challenge)* |
| `tn_2021_results.csv` | 2021 Tamil Nadu Assembly Election results *(provided in challenge)* |
| `tn_2026_results.csv` | 2026 Tamil Nadu Assembly Election results *(provided in challenge)* |
| `tn_2026_electors.csv` | Elector (registered voter) counts per constituency — **self-collected** to calculate voter turnout % |
| `tamilnadu_districts.geojson` | GeoJSON boundary file for Tamil Nadu districts, used for choropleth maps |
| `requirements.txt` | Python dependencies for deploying on Streamlit Cloud |

---

## 📊 Features

- Constituency-wise and district-wise result breakdown
- Party performance comparison: 2021 vs 2026
- Voter turnout percentage analysis (using self-collected electors data)
- Interactive choropleth maps using the GeoJSON boundary file
- Winning margin analysis across constituencies

---

## 🗂️ Data Sources

- `constituency_master.csv`, `tn_2021_results.csv`, `tn_2026_results.csv` — provided as part of the challenge dataset
- `tn_2026_electors.csv` — independently collected to enable turnout percentage calculations (votes polled / total electors × 100)

---

## 🚀 Run Locally

### Prerequisites

- Python 3.9 or above
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Streamlit app
streamlit run app.py
```

The app will open at `http://localhost:8501` in your browser.

---

## ☁️ Deploy on Streamlit Cloud

This app is live on **Streamlit Community Cloud**. To redeploy your own instance:

1. **Fork or push** this repository to your GitHub account. Make sure all files — `app.py`, `requirements.txt`, `tamilnadu_districts.geojson`, and all CSV files — are present at the root level.

2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

3. Click **"New app"** and fill in:
   - **Repository:** `your-username/your-repo-name`
   - **Branch:** `main`
   - **Main file path:** `app.py`

4. Click **"Deploy"**. Streamlit Cloud will automatically install packages from `requirements.txt` and launch the app.

> **Note:** The `tamilnadu_districts.geojson` file must be in the same directory as `app.py` for the choropleth maps to render correctly.

---

## 📓 Notebook

`tn_analysis_notebook.ipynb` reproduces all the metrics shown on the dashboard as a single consolidated table. To run it:

```bash
jupyter notebook tn_analysis_notebook.ipynb
```

---

## 🛠️ Tech Stack

- [Streamlit](https://streamlit.io/) — web app framework
- [Plotly](https://plotly.com/python/) — interactive charts and maps
- [Pandas](https://pandas.pydata.org/) — data processing
- [GeoPandas / JSON](https://geopandas.org/) — geospatial rendering via GeoJSON

# EV Charging Concept Drift Thesis

**Working Title:** *Concept-Drift-Aware Machine Learning for Day-Ahead EV Charging Energy Demand and High-Demand Risk Prediction Across ACN Sites*

## Project Overview

This project will develop a concept-drift-aware machine-learning approach for predicting next-day EV charging energy demand and high-demand risk. Historical charging sessions from the **Caltech** and **JPL** sites of [ACN-Data](https://ev.caltech.edu/dataset) will be used.

This README will be updated as the project progresses.

## Planned Workflow

1. Data gathering
2. Data validation and preprocessing
3. Daily aggregation and feature engineering
4. Seasonal-naive, Random Forest, and XGBoost modeling
5. Concept-drift detection and model retraining
6. Model evaluation and comparison

## Current Stage: Data Gathering

The `download_acndata.py` script retrieves all available session-level records from Caltech and JPL through the ACN-Data API.

### Prerequisites

- Python 3.10 or newer
- Internet connection
- `download_acndata.py`
- ACN API token from the group Discord
- Python `requests` package

### Instructions

1. Place `download_acndata.py` inside the project folder.
2. Open PowerShell or Command Prompt in that folder.
3. Install the required package:

   ```powershell
   py -m pip install requests
   ```

4. Run the downloader:

   ```powershell
   py download_acndata.py
   ```

5. Copy the API token from the group Discord, paste it when requested, and press **Enter**.

   ```text
   Enter your ACN API token (input hidden):
   ```

   Nothing will appear while pasting the token. This is normal.

6. Keep the terminal open until the following message appears:

   ```text
   All requested sites downloaded and passed the completeness check.
   ```

### Project Files

```text
EV-Thesis/
├── README.md
├── download_acndata.py
└── acndata_download/
    ├── acndata_caltech_sessions.jsonl
    ├── acndata_jpl_sessions.jsonl
    └── acndata_download_summary_YYYYMMDDTHHMMSSZ.json
```

Each line in a `.jsonl` file represents one charging session. The raw files must remain unchanged, and the download summary must be kept as the data-gathering record. Do not place the API token inside the script or README.

## Next Stage

The next update will document data validation, cleaning, and daily site-level aggregation.

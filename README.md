# EV Charging Concept Drift Thesis

**Working Title:** *Concept-Drift-Aware Machine Learning for Day-Ahead EV Charging Energy Demand and High-Demand Risk Prediction in the Palo Alto Municipal Charging Network*

## Project Overview

This project will develop a concept-drift-aware machine-learning approach for predicting next-day EV charging energy demand and high-demand risk. Historical charging sessions from the [City of Palo Alto’s official EV-charging dataset](https://data.paloalto.gov/datasets/194693/electric-vehicle-charging-station-usage-july-2011-dec-2020/) will be used.

The dataset contains **259,415 charging sessions** recorded from **July 29, 2011 to December 31, 2020**, covering **47 station names across 20 physical addresses**. Valid charging sessions will be aggregated by date to create one city-wide daily time series.

The forecasting target is the **total energy, in kWh, expected to be delivered across the Palo Alto municipal charging network on the following day**. The study evaluates historical forecasting and model-maintenance performance and does not estimate present-day charging demand.

This README will be updated as the project progresses.

## Planned Workflow

1. Dataset acquisition and validation
2. Session-level data cleaning
3. City-wide daily energy aggregation
4. Time-series feature engineering
5. Seasonal-naive, Random Forest, and XGBoost modeling
6. High-demand risk prediction
7. Concept-drift detection using ADWIN
8. Comparison of frozen, monthly-retrained, and ADWIN-retrained models
9. Chronological model evaluation and comparison

## Current Stage: Data Gathering

The full session-level dataset will be downloaded from the City of Palo Alto Open Data portal. No API token is required.

### Prerequisites

* Internet connection
* Web browser
* Sufficient storage for the full CSV file
* Python 3.10 or newer for the succeeding stages

### Download Instructions

1. Open the [official Palo Alto dataset page](https://data.paloalto.gov/datasets/194693/electric-vehicle-charging-station-usage-july-2011-dec-2020/).

2. Open the dataset’s **Information** section.

3. Locate **Data Collected From**.

4. Download the source file named:

   ```text
   ChargePoint Data CY20Q4.csv
   ```

5. Save the file inside the project’s `data/raw/` folder.

6. Confirm that the downloaded file contains **259,415 charging-session rows**.

Do not use the portal’s ordinary export option because it may export only 10,000 rows. Download the complete source CSV through the **Data Collected From** section.

### Project Files

```text
EV-Thesis/
├── README.md
└── data/
    └── raw/
        └── ChargePoint Data CY20Q4.csv
```

Each CSV row represents one charging session. Important fields include the charging start and end times, delivered energy, station name, and physical address.

The raw CSV must remain unchanged. Cleaned, aggregated, and feature-engineered datasets must be saved separately so that the original source data remains available for verification.

## Forecasting Scope

The 47 station names will not initially be modeled as separate forecasting targets. Instead, their delivered energy will be summed by date to produce the total daily demand of the Palo Alto municipal charging network.

Therefore, each prediction will answer:

> How much total EV-charging energy will the Palo Alto municipal charging network require tomorrow?

Station additions and changes in network size will be examined when interpreting detected drift because changes in city-wide demand may result from EV adoption, charging behaviour, exceptional events, or expansion of the charging network.

## Next Stage

The next update will document session-level data validation, cleaning, duplicate handling, date conversion, and city-wide daily energy aggregation.

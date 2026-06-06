# InsightFlow

InsightFlow is a Streamlit analytics copilot for CSV and Excel files. Upload a dataset, let the app clean common data-quality issues, ask questions in plain English, and get SQL-backed results with charts and business insights.

## Current Features

- CSV, XLS, and XLSX upload
- Built-in sample datasets for no-file demos
- Local pandas cleaning for missing values, duplicate rows, text whitespace/casing, and numeric text columns
- Statistical anomaly detection for numeric outliers, value spikes, and date gaps
- Selectable anomaly table with batch fixes for safe numeric anomalies
- Dataset overview with suggested easy SQL/chart questions
- Auto-dashboard with up to 3 overview charts generated after upload
- Chat-style question and answer interface with fixed bottom input
- Sidebar history for the last 10 successful questions
- Natural-language-to-DuckDB SQL generation with dataset-relevance validation
- Smart Plotly chart selection for query results
- Plain-English insight generation with local fallback
- CSV export for cleaned data and query results
- Structured logging to console and `logs/insightflow.log`

## Stack

- Streamlit for the app UI
- Groq for dataset summaries, SQL generation, and AI insights
- DuckDB for in-memory SQL over pandas DataFrames
- pandas and openpyxl for file parsing
- Plotly Express for charts
- Python logging with JSON file output for observability

## Project Structure

```text
InsightFlow/
|-- app.py
|-- data/
|   |-- Airbnb_Open_Data.csv
|   |-- Sample - Superstore.csv
|   `-- Titanic-Dataset.csv
|-- agents/
|   |-- __init__.py
|   |-- cleaning_agent.py
|   |-- anomaly_agent.py
|   |-- dashboard_agent.py
|   |-- dataset_agent.py
|   |-- query_agent.py
|   |-- insight_agent.py
|   `-- chart_agent.py
|-- services/
|   |-- __init__.py
|   |-- groq_service.py
|   |-- gemini_service.py
|   |-- duckdb_service.py
|   `-- chart_service.py
|-- utils/
|   |-- __init__.py
|   |-- helpers.py
|   |-- schema.py
|   |-- validators.py
|   `-- logger.py
|-- logs/
|   `-- insightflow.log
|-- .streamlit/
|   `-- config.toml
|-- .gitignore
|-- LOGGING.md
|-- requirements.txt
`-- README.md
```

Note: `services/groq_service.py` is the active AI service used by the current agents. `services/gemini_service.py` is a legacy Gemini service file from an earlier implementation and is not used by the active app flow.

## Architecture

- `app.py` is the Streamlit UI layer and imports agents.
- `agents/` orchestrate workflows.
- `services/` wrap external systems such as Groq, DuckDB, and Plotly chart generation.
- `utils/` contains pure helpers, schema extraction, validation, and logging setup.
- Cleaning is local and does not spend AI API calls.
- Anomaly detection is local first; Groq is only used to add business explanations.
- Dataset summaries and insights fall back to local summaries if the AI service fails.

## Local Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=mixtral-8x7b-32768

LOG_LEVEL=INFO
LOG_FILE=logs/insightflow.log
```

Run the app:

```powershell
streamlit run app.py
```

## Demo Flow

1. Upload a CSV or Excel file, or click a built-in sample dataset.
2. Review the raw preview.
3. Let the cleaning agent apply local pandas fixes.
4. Review the anomaly scan for outliers, spikes, or irregular date gaps.
5. Read the dataset overview and suggested questions.
6. Review the auto-generated dashboard charts.
7. Click a suggested question or type your own in the bottom chat input.
8. Review the generated SQL, result table, chart, and insight.
9. Use the sidebar to rerun previous questions.
10. Download cleaned data or query results as CSV.

## Sample Datasets

The app includes three datasets in `data/` for fast demos:

- `Sample - Superstore.csv`: retail orders, customer segments, regions, products, sales, discounts, and profit
- `Airbnb_Open_Data.csv`: listings, hosts, neighborhoods, room types, prices, reviews, availability, and licenses
- `Titanic-Dataset.csv`: passenger survival, class, demographics, tickets, cabins, fares, and embarkation data

These are available from the "Try a Sample Dataset" section near the top of the app.

## Anomaly Detection

The anomaly agent runs after cleaning and before the dataset overview. It detects:

- Numeric outliers using the IQR rule
- Value spikes using z-scores above 3 standard deviations
- Date gaps where the gap is more than 3 times the typical interval

Detected anomalies are grouped by column and type, labeled as medium or high severity, and shown in a selectable table. You can check multiple anomalies and fix them in one batch. Numeric anomalies are capped to statistical bounds; date gaps are reported but not changed automatically. If Groq is available, each anomaly gets a one-sentence business explanation. If Groq fails or rate limits, the app uses a local fallback explanation.

## Auto Dashboard

After the dataset overview, the dashboard agent asks Groq for 3 simple DuckDB overview queries based on the current schema and sample rows. The app validates each query, runs it through DuckDB, and renders the results as Plotly charts in a 3-column grid.

If Groq fails or returns invalid queries, the dashboard agent falls back to local chart specs such as:

- row count by top categorical column
- top categories by a numeric total
- a date trend when a date-like column exists
- a numeric distribution when categorical/date options are limited


## Query Guardrails

The query agent validates generated SQL before execution:

- Only `SELECT` and `WITH` queries are allowed.
- Dangerous SQL keywords such as `DROP`, `DELETE`, `UPDATE`, and `ALTER` are blocked.
- Random or off-dataset questions are rejected.
- Constant-only SQL such as `SELECT 'sky is blue' FROM df` is blocked.
- Generated SQL must reference uploaded dataset columns, except valid `COUNT(*)` queries.

## Logging

InsightFlow logs app flow, agent execution, API calls, SQL execution, chart selection, and failures.

- Console logs are human-readable.
- File logs are JSON-formatted at `logs/insightflow.log`.
- Configure with `LOG_LEVEL` and `LOG_FILE`.

See `LOGGING.md` for the full logging and observability guide.

## Environment Variables

```text
GROQ_API_KEY=required
GROQ_MODEL=optional, defaults to mixtral-8x7b-32768
LOG_LEVEL=optional, defaults to INFO
LOG_FILE=optional, defaults to logs/insightflow.log
```

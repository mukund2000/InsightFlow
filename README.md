# InsightFlow

InsightFlow is a Streamlit analytics copilot for CSV and Excel files. Upload a dataset, let the app clean common data-quality issues, ask questions in plain English, and get SQL-backed results with charts and business insights.

## Current Features

- CSV, XLS, and XLSX upload
- Local pandas cleaning for missing values, duplicate rows, text whitespace/casing, and numeric text columns
- Dataset overview with suggested easy SQL/chart questions
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
|-- agents/
|   |-- __init__.py
|   |-- cleaning_agent.py
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

1. Upload a CSV or Excel file.
2. Review the raw preview.
3. Let the cleaning agent apply local pandas fixes.
4. Read the dataset overview and suggested questions.
5. Click a suggested question or type your own in the bottom chat input.
6. Review the generated SQL, result table, chart, and insight.
7. Use the sidebar to rerun previous questions.
8. Download cleaned data or query results as CSV.

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

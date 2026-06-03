# InsightFlow

InsightFlow is an AI-powered analytics copilot for CSV and Excel files. Upload a dataset, let the cleaning agent prepare it, ask a natural-language question, and get a DuckDB SQL query, result table, smart chart, and plain-English business insight.

## Stack

- Streamlit for the UI
- Groq Mixtral-8x7b for dataset summaries, SQL, and insights
- DuckDB for in-memory SQL over pandas DataFrames
- pandas and openpyxl for CSV/Excel parsing
- Plotly Express for charts

## Project Structure

```text
InsightFlow/
|-- app.py
|-- agents/
|   |-- cleaning_agent.py
|   |-- dataset_agent.py
|   |-- query_agent.py
|   |-- insight_agent.py
|   `-- chart_agent.py
|-- services/
|   |-- groq_service.py
|   |-- duckdb_service.py
|   `-- chart_service.py
|-- utils/
|   |-- helpers.py
|   |-- schema.py
|   `-- validators.py
|-- .streamlit/
|   `-- config.toml
`-- requirements.txt
```

## Architecture Rules

- `app.py` imports agents only.
- `agents/` orchestrate workflows and call services or utils.
- `services/` wrap external tools and APIs.
- `utils/` are pure helper functions.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` file:

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=mixtral-8x7b-32768
```

Run the app:

```bash
streamlit run app.py
```

## Logging & Observability

InsightFlow includes comprehensive logging for debugging and monitoring:

### Log Output
- **Console**: Human-readable logs printed to stdout
- **File**: JSON-formatted structured logs saved to `logs/insightflow.log`

### Configuration

Add these optional variables to `.env`:

```text
LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/insightflow.log  # Custom log file path
```

### Log Levels
- **DEBUG**: Detailed diagnostics (DataFrame operations, SQL execution details)
- **INFO**: General flow (file uploads, agent execution, API calls)
- **WARNING**: Issues that don't stop execution (fallback methods, skipped operations)
- **ERROR**: Failures that need attention (API errors, validation failures)

### Sample Log Output

**Console** (human-readable):
```
2026-06-02 14:32:10 | insightflow.app | INFO     | New file uploaded: sales.csv
2026-06-02 14:32:11 | insightflow.agents.cleaning | INFO     | Starting data cleaning for 1000 rows, 12 columns
2026-06-02 14:32:12 | insightflow.services.groq | INFO     | Groq API call succeeded
```

**File** (JSON for parsing):
```json
{"timestamp": "2026-06-02T14:32:10.123456", "level": "INFO", "logger": "insightflow.app", "message": "New file uploaded: sales.csv", "module": "app", "function": "read_upload", "line": 35}
{"timestamp": "2026-06-02T14:32:12.654321", "level": "INFO", "logger": "insightflow.services.groq", "message": "Groq API call succeeded", "duration_ms": 1250.45}
```

### Debugging Tips

1. **Enable DEBUG logs**:
   ```text
   LOG_LEVEL=DEBUG
   ```

2. **Monitor Groq API usage**: Check `logs/insightflow.log` for all API call timings

3. **Track data cleaning**: View detailed cleaning operations and transformations

4. **Trace query execution**: See SQL generation, validation, and DuckDB execution times

## Demo Flow

1. Upload a CSV or Excel file.
2. Review the raw preview and AI cleaning log.
3. Read the AI-generated dataset overview.
4. Click a suggested question or type your own.
5. Inspect the generated SQL, result table, chart, and insight.
6. Download cleaned data or query results as CSV.

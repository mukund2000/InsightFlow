import json
import os

from google import genai

from utils.helpers import safe_parse_json, strip_code_fences


DEFAULT_MODEL_NAME = "gemini-2.0-flash"
_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        _client = genai.Client(api_key=api_key)
    return _client


def _call(prompt: str) -> str:
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME)
    try:
        response = _get_client().models.generate_content(
            model=model_name,
            contents=prompt,
        )
    except Exception as exc:
        message = str(exc)
        if "RESOURCE_EXHAUSTED" in message or "429" in message:
            raise RuntimeError(
                "Gemini quota is exhausted right now. Wait a minute and retry, or switch GEMINI_MODEL in .env."
            ) from exc
        raise
    return (response.text or "").strip()


def explain_dataset(stats: dict) -> dict:
    prompt = f"""You are a data analyst. Here are computed statistics:
{json.dumps(stats, indent=2, default=str)}

Return a JSON object with exactly these keys:
{{
  "overview": "One sentence describing what this dataset is about",
  "scale": ["fact about row count", "fact about categories", "fact about time range or columns"],
  "findings": ["Finding with specific number 1", "Finding with specific number 2", "Finding with specific number 3"],
  "quality_note": "One sentence about data completeness",
  "questions": ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]
}}

For "questions", suggest easy business questions that are simple to answer with SQL and simple to visualize.
Prefer questions that use one categorical column and one numeric column, such as:
- Top 10 categories by a numeric total
- Average numeric value by category
- Count of rows by category
- Trend of a numeric value over a date column
- Comparison between two simple categories
Avoid complex joins, predictions, correlations, percentages, window functions, multi-step reasoning, or questions that require columns not listed in the statistics.

Base ALL numbers ONLY on the provided statistics. Return ONLY valid JSON."""
    result = safe_parse_json(_call(prompt))
    if not isinstance(result, dict):
        raise ValueError("Gemini returned a dataset overview that was not a JSON object.")
    return result


def generate_sql(question: str, schema: str, sample: str) -> str:
    prompt = f"""You are a SQL expert using DuckDB syntax.
Table name: df
Schema:
{schema}

Sample rows:
{sample}

Write a DuckDB SQL query to answer: "{question}"

Rules:
- The question must be answerable using ONLY the listed columns and sample rows
- If the question is not about this dataset, return exactly: NOT_RELEVANT
- Do not answer general knowledge, opinions, definitions, greetings, or random statements
- Do not create literal/constant answers such as SELECT 'text' FROM df
- Every SELECT expression must reference at least one real dataset column unless it is COUNT(*)
- Use FROM df
- Return ONLY the SQL query, no markdown, no explanation
- Use DuckDB date functions such as date_trunc and strftime for date operations
- Add LIMIT 500 unless the query is an aggregation"""
    return strip_code_fences(_call(prompt)).strip().rstrip(";")


def generate_insight(sql: str, result_preview: str) -> str:
    prompt = f"""SQL: {sql}
Result:
{result_preview}

In exactly 2 sentences, explain what this result means for the business.
Be specific and reference numbers from the result. Do not mention SQL."""
    return _call(prompt)

import json
import os
import time

from groq import Groq

from utils.helpers import safe_parse_json, strip_code_fences
from utils.logger import get_logger


logger = get_logger("services.groq")
DEFAULT_MODEL_NAME = "mixtral-8x7b-32768"
_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error("GROQ_API_KEY environment variable not set")
            raise RuntimeError("GROQ_API_KEY is not configured.")
        logger.info("Initializing Groq client")
        _client = Groq(api_key=api_key)
    return _client


def _call(prompt: str) -> str:
    model_name = os.getenv("GROQ_MODEL", DEFAULT_MODEL_NAME)
    prompt_length = len(prompt)
    logger.debug(f"Calling Groq API with model={model_name}, prompt_length={prompt_length}")
    
    start_time = time.time()
    try:
        response = _get_client().chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        duration_ms = (time.time() - start_time) * 1000
        response_text = (response.choices[0].message.content or "").strip()
        logger.info(
            f"Groq API call succeeded",
            extra={"duration": duration_ms, "response_length": len(response_text)}
        )
        return response_text
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        message = str(exc)
        if "429" in message or "rate_limit" in message.lower():
            logger.warning(f"Groq rate limit exceeded (duration: {duration_ms:.0f}ms)", exc_info=True)
            raise RuntimeError(
                "Groq rate limit exceeded. Wait a moment and retry, or switch GROQ_MODEL in .env."
            ) from exc
        logger.error(f"Groq API call failed (duration: {duration_ms:.0f}ms)", exc_info=True)
        raise


def explain_dataset(stats: dict) -> dict:
    logger.info(f"Starting dataset explanation for {len(stats)} statistics")
    try:
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
            logger.error("Groq returned non-dict object for dataset explanation")
            raise ValueError("Groq returned a dataset overview that was not a JSON object.")
        logger.info(f"Dataset explanation completed with {len(result.get('questions', []))} suggested questions")
        return result
    except Exception as exc:
        logger.error("Dataset explanation failed", exc_info=True)
        raise


def generate_sql(question: str, schema: str, sample: str) -> str:
    logger.info(f"Generating SQL for question: {question[:100]}")
    try:
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
        sql = strip_code_fences(_call(prompt)).strip().rstrip(";")
        logger.info(f"SQL generated successfully: {sql[:100]}...")
        return sql
    except Exception as exc:
        logger.error(f"SQL generation failed for question: {question[:100]}", exc_info=True)
        raise


def generate_insight(sql: str, result_preview: str) -> str:
    logger.info(f"Generating business insight from SQL result")
    try:
        prompt = f"""SQL: {sql}
Result:
{result_preview}

In exactly 2 sentences, explain what this result means for the business.
Be specific and reference numbers from the result. Do not mention SQL."""
        insight = _call(prompt)
        logger.info(f"Business insight generated successfully")
        return insight
    except Exception as exc:
        logger.error("Insight generation failed", exc_info=True)
        raise

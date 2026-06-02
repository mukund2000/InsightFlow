import pandas as pd

from services.duckdb_service import run_query
from services.groq_service import generate_sql
from utils.schema import get_sample_string, get_schema_string
from utils.validators import validate_sql
from utils.logger import get_logger


logger = get_logger("agents.query")


class QueryAgent:
    def run(self, question: str, df: pd.DataFrame) -> dict:
        logger.info(f"Processing question: {question[:100]}")
        schema = get_schema_string(df)
        sample = get_sample_string(df)
        try:
            logger.debug("Generating SQL for question")
            sql = generate_sql(question, schema, sample)
            logger.debug(f"Generated SQL: {sql[:100]}...")
        except Exception as exc:
            logger.error(f"SQL generation failed for question: {question[:100]}", exc_info=True)
            return {"sql": "", "result_df": None, "error": str(exc)}

        valid, error = validate_sql(sql, df.columns.tolist())
        if not valid:
            logger.warning(f"SQL validation failed: {error}")
            return {"sql": sql, "result_df": None, "error": error}

        try:
            logger.debug("Executing validated SQL query")
            result_df = run_query(df, sql)
            logger.info(f"Query succeeded: {len(result_df)} rows returned")
            return {"sql": sql, "result_df": result_df, "error": None}
        except Exception as exc:
            logger.error(f"Query execution failed", exc_info=True)
            return {"sql": sql, "result_df": None, "error": str(exc)}

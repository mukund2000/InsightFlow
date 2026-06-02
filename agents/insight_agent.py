import pandas as pd

from services.groq_service import generate_insight
from utils.logger import get_logger


logger = get_logger("agents.insight")


class InsightAgent:
    def run(self, sql: str, result_df: pd.DataFrame) -> str:
        logger.info("Generating business insight from query results")
        if result_df is None or result_df.empty:
            logger.warning("Skipping insight generation: no results")
            return "No results to analyze."
        preview = result_df.head(10).to_string(index=False)
        try:
            insight = generate_insight(sql, preview)
            logger.info("Business insight generated successfully")
            return insight
        except Exception as exc:
            logger.warning("AI insight generation failed, using fallback", exc_info=True)
            return self._fallback_insight(result_df)

    def _fallback_insight(self, result_df: pd.DataFrame) -> str:
        rows, cols = result_df.shape
        numeric_cols = result_df.select_dtypes("number").columns.tolist()
        if numeric_cols:
            metric = numeric_cols[0]
            total = result_df[metric].sum()
            return f"The query returned {rows:,} rows and {cols:,} columns. The total {metric} in this result is {total:,.2f}."
        return f"The query returned {rows:,} rows and {cols:,} columns. Review the table above for the matching records."

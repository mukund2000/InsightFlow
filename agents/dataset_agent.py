import pandas as pd

from services.groq_service import explain_dataset
from utils.schema import compute_stats
from utils.logger import get_logger


logger = get_logger("agents.dataset")


class DatasetAgent:
    def run(self, df: pd.DataFrame) -> dict:
        logger.info(f"Generating dataset overview for {len(df)} rows, {len(df.columns)} columns")
        stats = compute_stats(df)
        try:
            result = explain_dataset(stats)
            logger.info(f"Dataset overview generated with {len(result.get('questions', []))} suggested questions")
        except Exception as exc:
            logger.warning(f"Failed to generate AI overview, using fallback", exc_info=True)
            result = self._fallback_overview(stats)
        return {
            "overview": result.get("overview", ""),
            "scale": result.get("scale", []),
            "findings": result.get("findings", []),
            "quality_note": result.get("quality_note", ""),
            "questions": result.get("questions", []),
        }

    def _fallback_overview(self, stats: dict) -> dict:
        numeric_cols = stats.get("numeric_columns", [])
        categorical_cols = stats.get("categorical_columns", [])
        date_cols = stats.get("datetime_columns", [])
        questions = []

        if categorical_cols and numeric_cols:
            questions.append(f"What are the top 10 {categorical_cols[0]} by total {numeric_cols[0]}?")
            questions.append(f"What is the average {numeric_cols[0]} by {categorical_cols[0]}?")
        if categorical_cols:
            questions.append(f"How many rows are there by {categorical_cols[0]}?")
        if date_cols and numeric_cols:
            questions.append(f"What is the trend of total {numeric_cols[0]} over {date_cols[0]}?")
        if len(categorical_cols) > 1:
            questions.append(f"How many rows are there by {categorical_cols[1]}?")

        while len(questions) < 5:
            questions.append("How many rows are in this dataset?")

        null_counts = stats.get("null_counts", {})
        quality_note = "No missing values were detected."
        if null_counts:
            quality_note = f"Missing values were detected in {len(null_counts)} columns."

        return {
            "overview": "This dataset is ready for SQL-based exploration.",
            "scale": [
                f"{stats.get('total_rows', 0):,} rows",
                f"{stats.get('total_columns', 0):,} columns",
                f"{len(numeric_cols)} numeric columns and {len(categorical_cols)} categorical columns",
            ],
            "findings": [
                f"Numeric columns available: {', '.join(numeric_cols[:3]) or 'none'}",
                f"Categorical columns available: {', '.join(categorical_cols[:3]) or 'none'}",
                f"Columns include: {', '.join(stats.get('column_names', [])[:5])}",
            ],
            "quality_note": quality_note,
            "questions": questions[:5],
        }

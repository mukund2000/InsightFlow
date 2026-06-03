import pandas as pd

from services.chart_service import auto_chart
from services.duckdb_service import run_query
from services.groq_service import suggest_dashboard_queries
from utils.logger import get_logger
from utils.schema import get_sample_string, get_schema_string
from utils.validators import validate_dataframe, validate_sql


logger = get_logger("agents.dashboard")


class DashboardAgent:
    def _date_like_columns(self, df: pd.DataFrame) -> list[str]:
        date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
        for col in df.select_dtypes(include=["object", "category"]).columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() >= len(df) * 0.8:
                date_cols.append(col)
        return date_cols

    def _fallback_specs(self, df: pd.DataFrame) -> list[dict]:
        numeric_cols = df.select_dtypes("number").columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        datetime_cols = self._date_like_columns(df)

        specs = []
        if categorical_cols:
            col = categorical_cols[0]
            specs.append(
                {
                    "title": f"Rows by {col}",
                    "description": "Shows the most common categories in the dataset.",
                    "sql": f'SELECT "{col}", COUNT(*) AS row_count FROM df GROUP BY "{col}" ORDER BY row_count DESC LIMIT 10',
                }
            )

        if categorical_cols and numeric_cols:
            cat = categorical_cols[0]
            metric = numeric_cols[0]
            specs.append(
                {
                    "title": f"Top {cat} by {metric}",
                    "description": "Highlights the largest categories by total value.",
                    "sql": f'SELECT "{cat}", SUM("{metric}") AS total_{self._safe_alias(metric)} FROM df GROUP BY "{cat}" ORDER BY total_{self._safe_alias(metric)} DESC LIMIT 10',
                }
            )

        if datetime_cols and numeric_cols:
            date_col = datetime_cols[0]
            metric = numeric_cols[0]
            specs.append(
                {
                    "title": f"{metric} trend",
                    "description": "Shows how the main numeric value changes over time.",
                    "sql": f'SELECT date_trunc(\'month\', try_cast("{date_col}" AS DATE)) AS month, SUM("{metric}") AS total_{self._safe_alias(metric)} FROM df WHERE try_cast("{date_col}" AS DATE) IS NOT NULL GROUP BY month ORDER BY month LIMIT 24',
                }
            )

        if len(specs) < 3 and numeric_cols:
            metric = numeric_cols[0]
            specs.append(
                {
                    "title": f"{metric} distribution",
                    "description": "Shows the distribution of a key numeric column.",
                    "sql": f'SELECT "{metric}" FROM df WHERE "{metric}" IS NOT NULL LIMIT 500',
                }
            )

        while len(specs) < 3:
            specs.append(
                {
                    "title": "Dataset rows",
                    "description": "Shows the total number of rows available for analysis.",
                    "sql": "SELECT COUNT(*) AS row_count FROM df",
                }
            )

        return specs[:3]

    def _safe_alias(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_").lower() or "value"

    def _get_specs(self, df: pd.DataFrame) -> list[dict]:
        try:
            return suggest_dashboard_queries(get_schema_string(df), get_sample_string(df))
        except Exception:
            logger.warning("Using fallback dashboard query specs", exc_info=True)
            return self._fallback_specs(df)

    def _build_widgets(self, df: pd.DataFrame, specs: list[dict]) -> list[dict]:
        widgets = []
        for spec in specs:
            sql = str(spec.get("sql", "")).strip().rstrip(";")
            valid, error = validate_sql(sql, df.columns.tolist())
            if not valid:
                logger.warning(f"Skipping invalid dashboard SQL: {error}")
                continue

            try:
                result_df = run_query(df, sql)
                figure = auto_chart(result_df)
                if figure is None:
                    logger.warning(f"Skipping dashboard widget without chart: {spec.get('title', 'Untitled')}")
                    continue
                widgets.append(
                    {
                        "title": spec.get("title", "Dashboard chart"),
                        "description": spec.get("description", ""),
                        "sql": sql,
                        "result_df": result_df,
                        "figure": figure,
                    }
                )
            except Exception:
                logger.warning(f"Skipping dashboard widget that failed: {spec.get('title', 'Untitled')}", exc_info=True)
        return widgets

    def run(self, df: pd.DataFrame) -> dict:
        logger.info(f"Building auto-dashboard for {len(df)} rows, {len(df.columns)} columns")
        ok, error = validate_dataframe(df)
        if not ok:
            logger.error(f"DataFrame validation failed: {error}")
            raise ValueError(error)

        widgets = self._build_widgets(df, self._get_specs(df))
        if not widgets:
            logger.warning("AI dashboard specs produced no widgets, retrying with fallback specs")
            widgets = self._build_widgets(df, self._fallback_specs(df))

        return {"widgets": widgets, "had_widgets": bool(widgets)}

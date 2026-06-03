import pandas as pd

from services.groq_service import explain_anomalies
from utils.logger import get_logger
from utils.validators import validate_dataframe


logger = get_logger("agents.anomaly")


class AnomalyAgent:
    def _detect_numeric_outliers(self, df: pd.DataFrame) -> list[dict]:
        anomalies = []
        for col in df.select_dtypes("number").columns:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if pd.isna(iqr) or iqr == 0:
                continue

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = series[(series < lower) | (series > upper)]
            if outliers.empty:
                continue

            anomaly_count = int(len(outliers))
            severity = "high" if anomaly_count > len(series) * 0.05 else "medium"
            anomalies.append(
                {
                    "type": "numeric_outlier",
                    "column": col,
                    "count": anomaly_count,
                    "severity": severity,
                    "expected_range": f"{lower:.2f} to {upper:.2f}",
                    "min_outlier": round(float(outliers.min()), 2),
                    "max_outlier": round(float(outliers.max()), 2),
                }
            )

        return anomalies

    def _detect_value_spikes(self, df: pd.DataFrame) -> list[dict]:
        anomalies = []
        for col in df.select_dtypes("number").columns:
            series = df[col].dropna()
            if len(series) < 20:
                continue

            mean = series.mean()
            std = series.std()
            if pd.isna(std) or std == 0:
                continue

            z_scores = ((series - mean) / std).abs()
            spikes = series[z_scores > 3]
            if spikes.empty:
                continue

            anomalies.append(
                {
                    "type": "value_spike",
                    "column": col,
                    "count": int(len(spikes)),
                    "severity": "high",
                    "spike_value": round(float(spikes.abs().max()), 2),
                    "column_mean": round(float(mean), 2),
                    "standard_deviation": round(float(std), 2),
                }
            )

        return anomalies

    def _detect_date_gaps(self, df: pd.DataFrame) -> list[dict]:
        anomalies = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                continue

            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() < len(df) * 0.8:
                continue

            diffs = parsed.dropna().sort_values().diff().dropna()
            if diffs.empty:
                continue

            median_diff = diffs.median()
            if pd.isna(median_diff) or median_diff <= pd.Timedelta(0):
                continue

            gaps = diffs[diffs > median_diff * 3]
            if gaps.empty:
                continue

            anomalies.append(
                {
                    "type": "date_gap",
                    "column": col,
                    "count": int(len(gaps)),
                    "severity": "medium",
                    "typical_gap_days": round(median_diff / pd.Timedelta(days=1), 2),
                    "largest_gap_days": round(gaps.max() / pd.Timedelta(days=1), 2),
                }
            )

        return anomalies

    def _deduplicate(self, anomalies: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for anomaly in anomalies:
            key = (anomaly.get("column"), anomaly.get("type"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(anomaly)
        return unique

    def _fallback_explanations(self, anomalies: list[dict]) -> list[dict]:
        explained = []
        for anomaly in anomalies:
            item = dict(anomaly)
            anomaly_type = item.get("type", "").replace("_", " ")
            column = item.get("column", "this column")
            count = item.get("count", 0)
            item["business_explanation"] = (
                f"{count} unusual values were found in {column}, which may indicate rare events, data entry issues, or segments worth reviewing."
                if anomaly_type != "date gap"
                else f"{count} unusual date gaps were found in {column}, which may indicate missing periods or irregular reporting."
            )
            explained.append(item)
        return explained

    def fix_anomaly(self, df: pd.DataFrame, anomaly: dict) -> tuple[pd.DataFrame, str]:
        df = df.copy()
        column = anomaly.get("column")
        anomaly_type = anomaly.get("type")

        if column not in df.columns:
            return df, f"Skipped fix because column '{column}' was not found."

        if anomaly_type == "numeric_outlier":
            series = df[column]
            if not pd.api.types.is_numeric_dtype(series):
                return df, f"Skipped fix because '{column}' is not numeric."

            clean_series = series.dropna()
            q1 = clean_series.quantile(0.25)
            q3 = clean_series.quantile(0.75)
            iqr = q3 - q1
            if pd.isna(iqr) or iqr == 0:
                return df, f"Skipped fix because '{column}' has no usable outlier range."

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mask = (df[column] < lower) | (df[column] > upper)
            changed = int(mask.sum())
            df[column] = df[column].clip(lower=lower, upper=upper)
            return df, f"Capped {changed} outliers in '{column}' to the IQR range {lower:.2f} to {upper:.2f}."

        if anomaly_type == "value_spike":
            series = df[column]
            if not pd.api.types.is_numeric_dtype(series):
                return df, f"Skipped fix because '{column}' is not numeric."

            mean = series.mean()
            std = series.std()
            if pd.isna(std) or std == 0:
                return df, f"Skipped fix because '{column}' has no usable spike range."

            lower = mean - 3 * std
            upper = mean + 3 * std
            mask = (df[column] < lower) | (df[column] > upper)
            changed = int(mask.sum())
            df[column] = df[column].clip(lower=lower, upper=upper)
            return df, f"Capped {changed} spike values in '{column}' to mean +/- 3 standard deviations."

        if anomaly_type == "date_gap":
            return df, (
                f"Date gaps in '{column}' were not changed automatically because fixing them safely requires "
                "knowing whether rows are missing or reporting was intentionally irregular."
            )

        return df, f"No automatic fix is available for anomaly type '{anomaly_type}'."

    def run(self, df: pd.DataFrame) -> dict:
        logger.info(f"Scanning anomalies for {len(df)} rows, {len(df.columns)} columns")
        ok, error = validate_dataframe(df)
        if not ok:
            logger.error(f"DataFrame validation failed: {error}")
            raise ValueError(error)

        raw_anomalies = (
            self._detect_numeric_outliers(df)
            + self._detect_date_gaps(df)
            + self._detect_value_spikes(df)
        )
        anomalies = self._deduplicate(raw_anomalies)
        if not anomalies:
            logger.info("No anomalies detected")
            return {"anomalies": [], "had_anomalies": False}

        logger.info(f"Detected {len(anomalies)} anomaly groups")
        try:
            anomalies = explain_anomalies(anomalies)
        except Exception:
            logger.warning("AI anomaly explanation failed, using fallback explanations", exc_info=True)
            anomalies = self._fallback_explanations(anomalies)

        return {"anomalies": anomalies, "had_anomalies": True}

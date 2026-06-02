import pandas as pd

from utils.validators import validate_dataframe
from utils.logger import get_logger


logger = get_logger("agents.cleaning")


class CleaningAgent:
    def detect_issues(self, df: pd.DataFrame) -> dict:
        logger.debug(f"Detecting data quality issues in {len(df)} rows, {len(df.columns)} columns")
        issues = {}

        nulls = df.isnull().sum()
        if nulls.any():
            issues["missing_values"] = nulls[nulls > 0].to_dict()

        duplicate_count = int(df.duplicated().sum())
        if duplicate_count > 0:
            logger.debug(f"Found {duplicate_count} duplicate rows")
            issues["duplicate_rows"] = duplicate_count

        numeric_as_string = []
        for col in df.select_dtypes(include=["object"]).columns:
            cleaned = df[col].dropna().astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False)
            if cleaned.empty:
                continue
            converted = pd.to_numeric(cleaned, errors="coerce")
            if converted.notna().mean() >= 0.85:
                numeric_as_string.append(col)
        if numeric_as_string:
            issues["numeric_as_string"] = numeric_as_string

        casing_issues = []
        for col in df.select_dtypes(include=["object"]).columns:
            values = df[col].dropna().astype(str).str.strip()
            if values.empty:
                continue
            lowered = set(values.str.lower())
            if len(lowered) < values.nunique():
                casing_issues.append(col)
        if casing_issues:
            issues["inconsistent_casing"] = casing_issues

        whitespace_columns = []
        for col in df.select_dtypes(include=["object"]).columns:
            values = df[col].dropna().astype(str)
            if values.ne(values.str.strip()).any():
                whitespace_columns.append(col)
        if whitespace_columns:
            issues["extra_whitespace"] = whitespace_columns

        return issues

    def apply_fixes(self, df: pd.DataFrame, ops: list[dict]) -> tuple[pd.DataFrame, list[str]]:
        logger.info(f"Applying {len(ops)} cleaning operations to DataFrame")
        df = df.copy()
        log = []

        for op in ops:
            col = op.get("column", "all")
            action = op.get("action")
            try:
                if action == "fill_mean" and col in df.columns:
                    count = int(df[col].isnull().sum())
                    df[col] = df[col].fillna(df[col].mean())
                    log.append(f"Filled {count} missing values in '{col}' with the mean.")

                elif action == "fill_mode" and col in df.columns:
                    count = int(df[col].isnull().sum())
                    modes = df[col].mode(dropna=True)
                    if modes.empty:
                        log.append(f"Skipped mode fill for '{col}' because no mode exists.")
                    else:
                        df[col] = df[col].fillna(modes.iloc[0])
                        log.append(f"Filled {count} missing values in '{col}' with the mode.")

                elif action == "drop_duplicates":
                    before = len(df)
                    df = df.drop_duplicates()
                    log.append(f"Removed {before - len(df)} duplicate rows.")

                elif action == "normalize_text" and col in df.columns:
                    df[col] = df[col].astype(str).str.strip().str.title()
                    log.append(f"Normalized text casing in '{col}'.")

                elif action == "fix_numeric" and col in df.columns:
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False),
                        errors="coerce",
                    )
                    log.append(f"Converted '{col}' to numeric type.")

                elif action == "strip_whitespace" and col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
                    log.append(f"Stripped whitespace from '{col}'.")

                else:
                    log.append(f"Skipped unsupported action '{action}' on '{col}'.")
            except Exception as exc:
                log.append(f"Skipped '{action}' on '{col}': {exc}")

        return df, log

    def build_cleaning_plan(self, df: pd.DataFrame, issues: dict) -> list[dict]:
        logger.debug(f"Building cleaning plan for {len(issues)} issue categories")
        ops = []

        if "duplicate_rows" in issues:
            ops.append(
                {
                    "issue": "Duplicate rows detected",
                    "action": "drop_duplicates",
                    "column": "all",
                    "reason": "Duplicate rows can double-count results.",
                }
            )

        for col in issues.get("numeric_as_string", []):
            ops.append(
                {
                    "issue": "Numeric values stored as text",
                    "action": "fix_numeric",
                    "column": col,
                    "reason": "Numeric columns should be queryable with aggregations.",
                }
            )

        for col in issues.get("extra_whitespace", []):
            ops.append(
                {
                    "issue": "Extra whitespace in text values",
                    "action": "strip_whitespace",
                    "column": col,
                    "reason": "Whitespace can split matching categories.",
                }
            )

        for col in issues.get("inconsistent_casing", []):
            ops.append(
                {
                    "issue": "Inconsistent text casing",
                    "action": "normalize_text",
                    "column": col,
                    "reason": "Consistent casing improves grouping and filtering.",
                }
            )

        for col in issues.get("missing_values", {}):
            if pd.api.types.is_numeric_dtype(df[col]):
                action = "fill_mean"
                reason = "The mean keeps numeric rows available for aggregation."
            else:
                action = "fill_mode"
                reason = "The mode is a simple default for missing category values."
            ops.append(
                {
                    "issue": "Missing values detected",
                    "action": action,
                    "column": col,
                    "reason": reason,
                }
            )

        return ops

    def run(self, df: pd.DataFrame) -> dict:
        logger.info(f"Starting data cleaning for {len(df)} rows, {len(df.columns)} columns")
        ok, error = validate_dataframe(df)
        if not ok:
            logger.error(f"DataFrame validation failed: {error}")
            raise ValueError(error)

        issues = self.detect_issues(df)
        if not issues:
            logger.info("No data quality issues detected - data is clean")
            return {
                "cleaned_df": df,
                "ops": [],
                "log": ["No issues found. Data is clean."],
                "issues": {},
                "had_issues": False,
            }

        logger.info(f"Found {len(issues)} issue categories - generating cleaning plan")
        ops = self.build_cleaning_plan(df, issues)
        cleaned_df, log = self.apply_fixes(df, ops)
        logger.info(f"Data cleaning completed - {len(log)} operations applied")
        return {
            "cleaned_df": cleaned_df,
            "ops": ops,
            "log": log,
            "issues": issues,
            "had_issues": True,
        }

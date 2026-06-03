import re

import pandas as pd


DANGEROUS_KEYWORDS = [
    "DROP",
    "DELETE",
    "INSERT",
    "UPDATE",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "COPY",
    "EXPORT",
    "ATTACH",
]


def validate_sql(sql: str, columns: list[str] | None = None) -> tuple[bool, str]:
    normalized = re.sub(r"\s+", " ", (sql or "").strip())
    upper = normalized.upper()
    if not normalized:
        return False, "SQL is empty"
    if upper == "NOT_RELEVANT":
        return False, "Please ask a question related to the uploaded dataset and its columns."
    if not upper.startswith("SELECT") and not upper.startswith("WITH"):
        return False, "Only SELECT queries are allowed"
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            return False, f"SQL contains disallowed keyword: {keyword}"
    if " FROM " not in f" {upper} ":
        return False, "SQL must contain a FROM clause"
    if _is_constant_select(normalized):
        return False, "Please ask a question that uses columns from the uploaded dataset."
    if columns and not _references_dataset_column(normalized, columns) and not _is_count_star_query(normalized):
        return False, "Generated SQL does not reference any uploaded dataset columns. Please ask about the dataset."
    if ";" in normalized.rstrip(";"):
        return False, "Only one SQL statement is allowed"
    return True, ""


def _is_constant_select(sql: str) -> bool:
    match = re.match(r"^\s*SELECT\s+(.*?)\s+FROM\s+df\b", sql, re.IGNORECASE | re.DOTALL)
    if not match:
        return False

    select_expr = match.group(1).strip()
    if re.search(r"\bCOUNT\s*\(\s*\*\s*\)", select_expr, re.IGNORECASE):
        return False

    has_identifier = re.search(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", select_expr)
    if not has_identifier:
        return True

    cleaned = re.sub(r"'[^']*'|\"[^\"]*\"", "", select_expr)
    cleaned = re.sub(r"\bAS\b\s+\w+", "", cleaned, flags=re.IGNORECASE)
    keywords = {"SELECT", "NULL", "TRUE", "FALSE"}
    identifiers = {
        token.upper()
        for token in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", cleaned)
        if token.upper() not in keywords
    }
    return not identifiers


def _references_dataset_column(sql: str, columns: list[str]) -> bool:
    upper_sql = sql.upper()
    for column in columns:
        escaped = re.escape(str(column))
        if re.search(rf'(?<!\w)"{escaped}"(?!\w)', sql, re.IGNORECASE):
            return True
        if re.search(rf"(?<!\w){escaped}(?!\w)", upper_sql, re.IGNORECASE):
            return True
    return False


def _is_count_star_query(sql: str) -> bool:
    return bool(re.search(r"^\s*SELECT\s+COUNT\s*\(\s*\*\s*\)", sql, re.IGNORECASE))


def validate_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    if df is None or df.empty:
        return False, "DataFrame is empty"
    if len(df.columns) == 0:
        return False, "DataFrame has no columns"
    return True, ""

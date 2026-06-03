import pandas as pd


def get_schema_string(df: pd.DataFrame) -> str:
    lines = [f"{col}: {dtype}" for col, dtype in df.dtypes.items()]
    return "\n".join(lines)


def get_sample_string(df: pd.DataFrame, n: int = 5) -> str:
    return df.head(n).to_string(index=False)


def compute_stats(df: pd.DataFrame) -> dict:
    nulls = df.isnull().sum()
    stats = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "numeric_columns": df.select_dtypes("number").columns.tolist(),
        "categorical_columns": df.select_dtypes(include=["object", "category"]).columns.tolist(),
        "datetime_columns": df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist(),
        "null_counts": nulls[nulls > 0].to_dict(),
    }

    top_categories = {}
    for col in df.select_dtypes(include=["object", "category"]).columns[:5]:
        top_categories[col] = df[col].value_counts(dropna=True).head(5).to_dict()
    stats["top_categories"] = top_categories

    numeric_summary = {}
    for col in df.select_dtypes("number").columns[:6]:
        series = df[col].dropna()
        if series.empty:
            continue
        numeric_summary[col] = {
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
            "mean": round(float(series.mean()), 2),
        }
    stats["numeric_summary"] = numeric_summary
    return stats


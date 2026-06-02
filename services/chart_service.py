import pandas as pd
import plotly.express as px

from utils.logger import get_logger


logger = get_logger("services.chart")


def auto_chart(df: pd.DataFrame):
    if df is None or df.empty or len(df.columns) < 1:
        logger.warning("auto_chart called with None, empty, or single-column DataFrame")
        return None

    logger.debug(f"Analyzing DataFrame for chart generation: {len(df)} rows, {len(df.columns)} columns")
    
    num_cols = df.select_dtypes("number").columns.tolist()
    date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    cat_cols = [
        col
        for col in df.columns
        if col not in num_cols and col not in date_cols and df[col].nunique(dropna=True) <= 50
    ]

    logger.debug(f"Column types: {len(num_cols)} numeric, {len(date_cols)} date, {len(cat_cols)} categorical")

    try:
        if date_cols and num_cols:
            logger.info(f"Creating line chart: {date_cols[0]} (x) vs {num_cols[0]} (y)")
            return px.line(df, x=date_cols[0], y=num_cols[0], title="Trend over time")

        if cat_cols and num_cols:
            if df[cat_cols[0]].nunique(dropna=True) <= 6:
                logger.info(f"Creating pie chart: {num_cols[0]} by {cat_cols[0]}")
                return px.pie(df, names=cat_cols[0], values=num_cols[0])
            logger.info(f"Creating bar chart: {num_cols[0]} by {cat_cols[0]}")
            return px.bar(df, x=cat_cols[0], y=num_cols[0], title=f"{num_cols[0]} by {cat_cols[0]}")

        if len(num_cols) >= 2:
            logger.info(f"Creating scatter plot: {num_cols[0]} vs {num_cols[1]}")
            return px.scatter(df, x=num_cols[0], y=num_cols[1])

        if num_cols:
            logger.info(f"Creating histogram: {num_cols[0]}")
            return px.histogram(df, x=num_cols[0])

        logger.warning("No suitable chart type found for DataFrame")
        return None
    except Exception as exc:
        logger.error("Chart generation failed", exc_info=True)
        return None


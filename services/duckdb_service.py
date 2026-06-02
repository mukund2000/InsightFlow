import time

import duckdb
import pandas as pd

from utils.logger import get_logger


logger = get_logger("services.duckdb")


def run_query(df: pd.DataFrame, sql: str) -> pd.DataFrame:
    logger.info(f"Executing SQL query: {sql[:100]}...")
    connection = duckdb.connect(database=":memory:")
    try:
        start_time = time.time()
        connection.register("df", df)
        logger.debug(f"Registered DataFrame with {len(df)} rows, {len(df.columns)} columns")
        result = connection.execute(sql).fetchdf()
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Query executed successfully",
            extra={"duration": duration_ms, "result_rows": len(result)}
        )
        return result
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Query execution failed (duration: {duration_ms:.0f}ms)", exc_info=True)
        raise
    finally:
        connection.close()
        logger.debug("DuckDB connection closed")


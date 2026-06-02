import pandas as pd

from services.chart_service import auto_chart


class ChartAgent:
    def run(self, result_df: pd.DataFrame):
        return auto_chart(result_df)


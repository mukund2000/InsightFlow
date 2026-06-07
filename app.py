import os
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from utils.logger import setup_logging, get_logger

# Initialize logging at app startup
setup_logging()
logger = get_logger("app")

logger.info("Starting InsightFlow application")

load_dotenv()
if not os.getenv("GROQ_API_KEY"):
    try:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
        logger.info("Loaded GROQ_API_KEY from Streamlit secrets")
    except Exception:
        logger.debug("GROQ_API_KEY not found in Streamlit secrets, checking .env")

from agents.chart_agent import ChartAgent
from agents.anomaly_agent import AnomalyAgent
from agents.cleaning_agent import CleaningAgent
from agents.dashboard_agent import DashboardAgent
from agents.dataset_agent import DatasetAgent
from agents.insight_agent import InsightAgent
from agents.query_agent import QueryAgent


st.set_page_config(page_title="InsightFlow", page_icon=":bar_chart:", layout="wide")

SAMPLE_DATASETS = {
    "Retail analytics": {
        "filename": "Sample - Superstore.csv",
        "path": Path("data/Sample - Superstore.csv"),
        "description": "Orders, customers, regions, products, sales, discounts, and profit.",
    },
    "Airbnb listings": {
        "filename": "Airbnb_Open_Data.csv",
        "path": Path("data/Airbnb_Open_Data.csv"),
        "description": "Listings, hosts, locations, room types, prices, reviews, and availability.",
    },
    "Titanic passengers": {
        "filename": "Titanic-Dataset.csv",
        "path": Path("data/Titanic-Dataset.csv"),
        "description": "Passenger survival, class, demographics, tickets, cabins, and fares.",
    },
}


def read_upload(uploaded_file) -> pd.DataFrame:
    logger.info(f"Reading uploaded file: {uploaded_file.name}")

    try:
        name = uploaded_file.name.lower()

        # ---------------- CSV HANDLING ----------------
        if name.endswith(".csv"):
            encodings = ["utf-8", "cp1252", "latin1", "ISO-8859-1"]

            for enc in encodings:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding=enc, low_memory=False)
                    logger.info(f"Loaded CSV using encoding={enc}: {len(df)} rows, {len(df.columns)} cols")
                    return df
                except UnicodeDecodeError:
                    continue

            raise ValueError("Unable to decode CSV with common encodings")

        # ---------------- EXCEL HANDLING ----------------
        if name.endswith((".xlsx", ".xls")):
            uploaded_file.seek(0)  # IMPORTANT for Streamlit

            content = BytesIO(uploaded_file.read())
            workbook = pd.ExcelFile(content)

            sheet = workbook.sheet_names[0]
            df = pd.read_excel(workbook, sheet_name=sheet)

            logger.info(f"Loaded Excel: {len(df)} rows, {len(df.columns)} columns from sheet '{sheet}'")
            return df

        # ---------------- UNSUPPORTED ----------------
        logger.error(f"Unsupported file type: {name}")
        raise ValueError("Unsupported file type. Only CSV and Excel are supported.")

    except Exception as exc:
        logger.error(f"Failed to read uploaded file: {uploaded_file.name}", exc_info=True)
        raise


def read_sample_dataset(path: Path) -> pd.DataFrame:
    logger.info(f"Reading sample dataset: {path}")

    encodings = ["utf-8", "cp1252", "latin1"]

    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            logger.info(f"Loaded dataset using encoding: {enc}")
            return df
        except UnicodeDecodeError:
            continue

    raise ValueError("Unable to decode CSV file with common encodings")


def reset_dataset_state(filename: str, df: pd.DataFrame, clear_upload: bool = False) -> None:
    upload_key = st.session_state.get("upload_key", 0)
    st.session_state.clear()
    st.session_state.upload_key = upload_key + 1 if clear_upload else upload_key
    st.session_state.filename = filename
    st.session_state.raw_df = df
    st.session_state.history = []
    st.session_state.messages = []
    st.session_state.anomaly_fix_log = []
    logger.info("Session cleared and initialized for new dataset")


def init_agents() -> dict:
    return {
        "cleaning": CleaningAgent(),
        "anomaly": AnomalyAgent(),
        "dashboard": DashboardAgent(),
        "dataset": DatasetAgent(),
        "query": QueryAgent(),
        "insight": InsightAgent(),
        "chart": ChartAgent(),
    }


agents = init_agents()

if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "anomaly_fix_log" not in st.session_state:
    st.session_state.anomaly_fix_log = []
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0


def render_history_sidebar() -> None:
    with st.sidebar:
        st.header("History")
        if not st.session_state.history:
            st.caption("Ask a question to start a history.")
        for index, item in enumerate(st.session_state.history):
            if st.button(item["q"][:60], key=f"history_{index}", width="stretch"):
                st.session_state.pending_question = item["q"]
                st.rerun()


def add_answer(question: str, query_result: dict, result_df: pd.DataFrame, insight: str) -> None:
    message = {
        "q": question,
        "sql": query_result["sql"],
        "result_df": result_df,
        "insight": insight,
    }
    st.session_state.messages.append(message)

    existing_questions = [item["q"] for item in st.session_state.history]
    if question not in existing_questions:
        st.session_state.history.insert(0, {"q": question, "sql": query_result["sql"]})
        st.session_state.history = st.session_state.history[:10]


def render_conversation() -> None:
    for index, message in enumerate(st.session_state.messages):
        with st.chat_message("user"):
            st.markdown(message["q"])

        with st.chat_message("assistant"):
            st.info(message["insight"])
            with st.expander("Generated SQL", expanded=False):
                st.code(message["sql"], language="sql")

            result_df = message["result_df"]
            st.dataframe(result_df, width="stretch")

            figure = agents["chart"].run(result_df)
            if figure:
                st.plotly_chart(figure, width="stretch")

            st.download_button(
                "Download results",
                result_df.to_csv(index=False),
                file_name=f"query_results_{index + 1}.csv",
                mime="text/csv",
                key=f"download_result_{index}",
            )


def apply_anomaly_fixes(anomalies: list[dict]) -> None:
    fixed_df = st.session_state.clean_result["cleaned_df"]
    messages = []
    for anomaly in anomalies:
        fixed_df, message = agents["anomaly"].fix_anomaly(fixed_df, anomaly)
        messages.append(message)

    st.session_state.clean_result["cleaned_df"] = fixed_df
    st.session_state.anomaly_fix_log.extend(messages)
    st.session_state.pop("anomaly_result", None)
    st.session_state.pop("dataset_result", None)
    st.session_state.pop("dashboard_result", None)
    st.session_state.messages = []
    st.session_state.history = []
    logger.info(f"Applied {len(anomalies)} anomaly fixes")
    st.rerun()


def build_anomaly_table(anomalies: list[dict]) -> pd.DataFrame:
    rows = []
    for index, anomaly in enumerate(anomalies):
        details = {
            key: value
            for key, value in anomaly.items()
            if key not in {"column", "type", "severity", "business_explanation"}
        }
        detail_text = ", ".join(f"{key}: {value}" for key, value in details.items())
        rows.append(
            {
                "Fix": False,
                "Index": index,
                "Severity": anomaly.get("severity", "medium").title(),
                "Column": anomaly.get("column", ""),
                "Type": anomaly.get("type", "anomaly").replace("_", " ").title(),
                "Count": anomaly.get("count", ""),
                "Details": detail_text,
                "Explanation": anomaly.get("business_explanation", ""),
            }
        )
    return pd.DataFrame(rows)


st.title("InsightFlow")
st.caption("Upload a dataset, clean it with AI, ask questions in plain English, and get SQL-backed insights.")

uploaded = st.file_uploader(
    "Upload CSV or Excel",
    type=["csv", "xlsx", "xls"],
    key=f"uploaded_file_{st.session_state.upload_key}",
)

st.subheader("Try a Sample Dataset")
sample_cols = st.columns(len(SAMPLE_DATASETS))
for index, (label, sample) in enumerate(SAMPLE_DATASETS.items()):
    with sample_cols[index]:
        st.caption(sample["description"])
        if st.button(label, key=f"sample_{sample['filename']}", width="stretch"):
            reset_dataset_state(
                sample["filename"],
                read_sample_dataset(sample["path"]),
                clear_upload=True,
            )
            st.rerun()

if uploaded:
    if st.session_state.get("filename") != uploaded.name:
        logger.info(f"New file uploaded: {uploaded.name}")
        reset_dataset_state(uploaded.name, read_upload(uploaded))

if "raw_df" not in st.session_state:
    render_history_sidebar()
    st.info("Upload a CSV or Excel file, or choose one of the sample datasets above.")
    st.stop()

raw_df = st.session_state.raw_df
st.success(f"Loaded {st.session_state.filename}: {len(raw_df):,} rows x {len(raw_df.columns):,} columns")

with st.expander("Raw data preview", expanded=False):
    st.dataframe(raw_df.head(20), width="stretch")

st.divider()
st.subheader("Data Cleaning Agent")

if not os.getenv("GROQ_API_KEY"):
    render_history_sidebar()
    st.error("Set GROQ_API_KEY in a local .env file or Streamlit secrets before running AI agents.")
    st.stop()

if "clean_result" not in st.session_state:
    logger.info("Running cleaning agent")
    with st.spinner("Analyzing data quality and applying safe fixes..."):
        try:
            st.session_state.clean_result = agents["cleaning"].run(raw_df)
        except Exception as exc:
            logger.error("Cleaning agent failed", exc_info=True)
            render_history_sidebar()
            st.error(f"Cleaning failed: {exc}")
            st.stop()

clean = st.session_state.clean_result
cleaned_df = clean["cleaned_df"]

if clean["had_issues"]:
    for item in clean["log"]:
        st.markdown(f"- {item}")
    before_col, after_col, column_col = st.columns(3)
    before_col.metric("Rows before", f"{len(raw_df):,}")
    after_col.metric("Rows after", f"{len(cleaned_df):,}")
    column_col.metric("Columns", f"{len(cleaned_df.columns):,}")
else:
    st.success(clean["log"][0])

st.download_button(
    "Download cleaned data",
    cleaned_df.to_csv(index=False),
    file_name="cleaned_data.csv",
    mime="text/csv",
)

st.divider()
st.subheader("Anomaly Detection Agent")

for item in st.session_state.get("anomaly_fix_log", []):
    st.info(item)

if "anomaly_result" not in st.session_state:
    logger.info("Running anomaly agent")
    with st.spinner("Scanning for statistical anomalies..."):
        try:
            st.session_state.anomaly_result = agents["anomaly"].run(cleaned_df)
        except Exception as exc:
            logger.error("Anomaly agent failed", exc_info=True)
            st.warning(f"Anomaly scan skipped: {exc}")
            st.session_state.anomaly_result = {"anomalies": [], "had_anomalies": False}

anomaly_result = st.session_state.anomaly_result
if anomaly_result["had_anomalies"]:
    anomalies = anomaly_result["anomalies"]
    with st.expander(f"{len(anomalies)} anomalies detected", expanded=True):
        edited_anomalies = st.data_editor(
            build_anomaly_table(anomalies),
            hide_index=True,
            width="stretch",
            disabled=["Index", "Severity", "Column", "Type", "Count", "Details", "Explanation"],
            column_config={
                "Fix": st.column_config.CheckboxColumn("Fix", help="Select anomalies to fix."),
                "Index": None,
                "Details": st.column_config.TextColumn("Details", width="medium"),
                "Explanation": st.column_config.TextColumn("Explanation", width="large"),
            },
            key="anomaly_fix_table",
        )

        selected_rows = edited_anomalies[edited_anomalies["Fix"]]
        selected_anomalies = [
            anomalies[int(row["Index"])]
            for _, row in selected_rows.iterrows()
        ]

        fix_col, note_col = st.columns([1, 3])
        with fix_col:
            if st.button("Fix selected anomalies", width="stretch", disabled=not selected_anomalies):
                apply_anomaly_fixes(selected_anomalies)
        with note_col:
            st.caption(
                "Numeric anomalies are capped to statistical bounds. Date gaps are reported but not changed automatically."
            )
else:
    st.success("No major statistical anomalies detected.")

st.divider()
st.subheader("Dataset Overview")

if "dataset_result" not in st.session_state:
    logger.info("Running dataset agent")
    with st.spinner("Building dataset overview and suggested questions..."):
        try:
            st.session_state.dataset_result = agents["dataset"].run(cleaned_df)
        except Exception as exc:
            logger.error("Dataset agent failed", exc_info=True)
            render_history_sidebar()
            st.error(f"Dataset overview failed: {exc}")
            st.stop()

dataset = st.session_state.dataset_result
st.markdown(f"**{dataset['overview']}**")

scale_col, finding_col = st.columns(2)
with scale_col:
    st.markdown("**Scale**")
    for item in dataset["scale"]:
        st.markdown(f"- {item}")
with finding_col:
    st.markdown("**Key findings**")
    for item in dataset["findings"]:
        st.markdown(f"- {item}")

if dataset["quality_note"]:
    st.info(dataset["quality_note"])

st.divider()
st.subheader("Auto Dashboard")

if "dashboard_result" not in st.session_state:
    logger.info("Running dashboard agent")
    with st.spinner("Building overview dashboard..."):
        try:
            st.session_state.dashboard_result = agents["dashboard"].run(cleaned_df)
        except Exception as exc:
            logger.error("Dashboard agent failed", exc_info=True)
            st.warning(f"Auto dashboard skipped: {exc}")
            st.session_state.dashboard_result = {"widgets": [], "had_widgets": False}

dashboard = st.session_state.dashboard_result
if dashboard["had_widgets"]:
    chart_cols = st.columns(len(dashboard["widgets"]))
    for index, widget in enumerate(dashboard["widgets"]):
        with chart_cols[index]:
            st.markdown(f"**{widget['title']}**")
            if widget.get("description"):
                st.caption(widget["description"])
            st.plotly_chart(widget["figure"], width="stretch", key=f"auto_dashboard_chart_{index}")
            with st.expander("SQL", expanded=False):
                st.code(widget["sql"], language="sql")
else:
    st.info("No automatic dashboard charts were generated for this dataset.")

questions = dataset.get("questions", [])[:5]
if questions:
    st.divider()
    st.subheader("Try These Questions")
    columns = st.columns(len(questions))
    for index, question in enumerate(questions):
        if columns[index].button(question, key=f"suggested_{index}", width="stretch"):
            st.session_state.pending_question = question
            st.rerun()

st.divider()
st.subheader("Questions and Answers")

render_conversation()

pending_question = st.session_state.pop("pending_question", "")
chat_question = st.chat_input("Ask a question about this dataset")
user_question = (pending_question or chat_question or "").strip()

if not user_question:
    render_history_sidebar()
    st.stop()

logger.info(f"Processing user question: {user_question[:100]}")

with st.spinner("Generating SQL, chart, and insight..."):
    logger.debug("Running query agent")
    query_result = agents["query"].run(user_question, cleaned_df)

if query_result["error"]:
    logger.error(f"Query execution failed: {query_result['error']}")
    render_history_sidebar()
    st.error(f"Query failed: {query_result['error']}")
    st.stop()

result_df = query_result["result_df"]
logger.debug("Running insight agent")
insight = agents["insight"].run(query_result["sql"], result_df)
add_answer(user_question, query_result, result_df, insight)
logger.info(f"Question processed successfully: {user_question[:100]}")
render_history_sidebar()
st.rerun()

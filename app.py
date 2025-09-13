import os
import json
import io
from typing import List, Tuple, Dict, Any

import requests
import pandas as pd
import gradio as gr


# -----------------------------
# Settings & simple tickers parser
# -----------------------------
APP_TITLE = os.getenv("APP_TITLE", "Checklist Scoring UI")


def parse_tickers(raw: str) -> List[str]:
    """Accept comma/space/newline separated tickers; normalize to UPPER."""
    if not raw:
        return []
    parts = [p.strip().upper() for p in raw.replace(",", " ").split()]
    return [p for p in parts if p]


def _post_to_apps_script(df: pd.DataFrame) -> dict:
    url = os.environ.get("APPS_SCRIPT_URL")
    secret = os.environ.get("APPS_SCRIPT_SECRET")
    if not url or not secret:
        raise RuntimeError("APPS_SCRIPT_URL or APPS_SCRIPT_SECRET is missing.")

    payload = {
        "secret": secret,
        "rows": df.to_dict(orient="records")
    }
    r = requests.post(url, json=payload, timeout=30)
    try:
        data = r.json()
    except Exception:
        data = {"ok": False, "error": f"Non-JSON response: {r.text[:200]}"}

    if r.status_code != 200 or not data.get("ok"):
        raise RuntimeError(f"Apps Script error ({r.status_code}): {data}")

    sheet_id = os.getenv("GSHEET_ID")  # optional, just for link building
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}" if sheet_id else None
    return {"appended": data.get("appended", 0), "sheet_url": sheet_url}


def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    import openpyxl  # ensures engine is present
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Scores")
    bio.seek(0)
    return bio.read()


# -----------------------------
# Adapter to your existing engine
# -----------------------------
def run_checklist_adapter(tickers: List[str]) -> Tuple[pd.DataFrame, dict]:
    """
    Import and call the real scoring function(s) used today. Do NOT modify business logic; only adapt I/O.

    Returns:
        df: pd.DataFrame -> one row per ticker with current sheet columns
        meta: dict        -> e.g., {"count": len(df)}
    """
    # Import inside to avoid import-time side-effects if app is imported by hosts
    from Checklist.main import process_all_sections_batch, calculate_total_score, SECTION_ROW_MAPS

    # Keep the same default sections order as CLI default
    sections_in_order: List[str] = [
        "financial",
        "potential",
        "customers",
        "specific_factors",
        "management",
        "stock",
        "penalties",
    ]

    # Run existing batch pipeline
    results_by_section: Dict[str, Dict[str, Dict[str, Any]]] = process_all_sections_batch(tickers, sections_in_order)

    # Build ordered column list to mirror spreadsheet schema
    ordered_columns: List[str] = ["Ticker"]
    for section in sections_in_order:
        rows_map = SECTION_ROW_MAPS.get(section, {})
        ordered_columns.extend(list(rows_map.keys()))
    ordered_columns.append("Total Score")

    # Flatten results into rows
    rows: List[Dict[str, Any]] = []
    for ticker in tickers:
        row: Dict[str, Any] = {"Ticker": ticker.upper()}

        # Pull metrics for each section strictly by sheet schema names
        for section in sections_in_order:
            rows_map = SECTION_ROW_MAPS.get(section, {})
            section_result = results_by_section.get(section, {}).get(ticker, {}) or {}
            for metric_name in rows_map.keys():
                # Use None when metric is missing (manual fields etc.)
                value = section_result.get(metric_name, None)
                row[metric_name] = value

        # Compute total score using existing logic
        total_score, _section_scores = calculate_total_score(results_by_section, ticker)
        row["Total Score"] = total_score

        rows.append(row)

    df = pd.DataFrame(rows, columns=ordered_columns)
    return df, {"count": len(df)}


# -----------------------------
# Pipeline bound to UI
# -----------------------------
def run_pipeline(raw_tickers: str, write_to_sheet: bool):
    # Parse
    tickers = parse_tickers(raw_tickers)
    if not tickers:
        return "Please enter at least one ticker.", None, None, None, None

    # Call existing engine via adapter
    try:
        df, meta = run_checklist_adapter(tickers)
    except Exception as e:
        return f"Engine error: {e}", None, None, None, None

    # Optional: write to Google Sheets via Apps Script
    sheet_url = None
    status = f"Processed {len(df)} tickers."
    if write_to_sheet:
        try:
            res = _post_to_apps_script(df)
            sheet_url = res.get("sheet_url")
            status = f"Processed {len(df)} tickers and wrote to Google Sheets."
        except Exception as e:
            status = f"Processed {len(df)} tickers. Google Sheets write failed: {e}"

    # Prepare downloads
    try:
        csv_bytes = _df_to_csv_bytes(df)
        xlsx_bytes = _df_to_xlsx_bytes(df)
        csv_file = ("scores.csv", csv_bytes)
        xlsx_file = ("scores.xlsx", xlsx_bytes)
    except Exception as e:
        csv_file = None
        xlsx_file = None
        status += f" Download generation failed: {e}"

    return status, df, sheet_url, csv_file, xlsx_file


# -----------------------------
# Gradio UI (mobile-friendly)
# -----------------------------
with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"# {APP_TITLE}\nEnter one or more tickers, then run the scoring.")

    tickers_in = gr.Textbox(
        label="Tickers",
        placeholder="e.g., AAPL, MSFT, GOOGL",
        lines=2
    )
    write_to_sheet = gr.Checkbox(label="Write to Google Sheet (Apps Script)", value=True)

    run_btn = gr.Button("Run Scoring", variant="primary")
    status = gr.Markdown()
    df_out = gr.Dataframe(label="Results", interactive=False)
    sheet_link = gr.Markdown()
    dl_csv = gr.File(label="Download CSV")
    dl_xlsx = gr.File(label="Download Excel")

    def _postprocess(status_text, df, sheet_url, csv_file, xlsx_file):
        link_md = f"[Open Google Sheet]({sheet_url})" if sheet_url else ""
        return status_text, df, link_md, csv_file, xlsx_file

    run_btn.click(
        fn=run_pipeline,
        inputs=[tickers_in, write_to_sheet],
        outputs=[status, df_out, sheet_link, dl_csv, dl_xlsx],
        api_name="run"
    ).then(
        fn=_postprocess,
        inputs=[status, df_out, sheet_link, dl_csv, dl_xlsx],
        outputs=[status, df_out, sheet_link, dl_csv, dl_xlsx]
    )

demo.queue()
app = demo  # for hosts that import `app`

if __name__ == "__main__":
    # Allow overriding port via env (useful for cloud hosts)
    port = int(os.getenv("PORT", "7860"))
    demo.launch(server_name="0.0.0.0", server_port=port)



from typing import List, Dict, Tuple
import pandas as pd

# Import your existing section functions and helpers
from Checklist.stock import fetch_and_score_stock
from Checklist.management import fetch_and_score_management, clear_mission_statements_file
from Checklist.financial import fetch_and_score_financials
from Checklist.potential import fetch_and_score_potential
from Checklist.customers import fetch_and_score_customers
from Checklist.penalties import fetch_and_score_penalties
from Checklist.specific_factors import fetch_and_score_specific_factors

# Same default sections as your CLI
DEFAULT_SECTIONS = [
    "financial",
    "potential",
    "customers",
    "specific_factors",
    "management",
    "stock",
    "penalties",
]

SECTION_FUNCS = {
    "financial": fetch_and_score_financials,
    "potential": fetch_and_score_potential,
    "customers": fetch_and_score_customers,
    "specific_factors": fetch_and_score_specific_factors,
    "management": fetch_and_score_management,
    "stock": fetch_and_score_stock,
    "penalties": fetch_and_score_penalties,
}


def _score_one_ticker(ticker: str, sections: List[str]) -> Tuple[Dict[str, float], float]:
    """
    Returns (section_totals, total_score) for a single ticker.
    - Per-section totals are sum of metrics (excluding 'Gauntlet Score' for penalties).
    - None scores are ignored (treated as 0).
    """
    section_totals: Dict[str, float] = {}

    for section in sections:
        fn = SECTION_FUNCS.get(section)
        if not fn:
            continue
        try:
            scores = fn(ticker)  # dict[str, float] or None
        except Exception:
            scores = None

        if not scores:
            section_totals[section] = 0.0
            continue

        if section == "penalties":
            # exclude 'Gauntlet Score' to avoid double counting
            scores = {k: v for k, v in scores.items() if k != "Gauntlet Score"}

        subtotal = sum(float(v) for v in scores.values() if v is not None)
        section_totals[section] = subtotal

    total = sum(section_totals.values())
    return section_totals, total


def score_companies(tickers: List[str], sections: List[str] | None = None) -> pd.DataFrame:
    """
    Engine entrypoint for UI:
      - No Excel I/O
      - No printing, just compute and return a DataFrame
    Columns: Ticker, <section totals...>, Total Score
    """
    if sections is None:
        sections = DEFAULT_SECTIONS[:]

    # Clear management file once if needed
    if "management" in sections:
        try:
            clear_mission_statements_file()
        except Exception:
            pass

    rows = []
    for t in tickers:
        section_totals, total = _score_one_ticker(t, sections)
        row = {"Ticker": t}
        # Beautify column names (e.g., Specific Factors -> Specific Factors)
        for sec, val in section_totals.items():
            col = sec.replace("_", " ").title()
            row[col] = val
        row["Total Score"] = total
        rows.append(row)

    # Ensure all section columns exist even if some tickers failed a section
    all_cols = {"Ticker"} | {k.replace("_", " ").title() for k in SECTION_FUNCS.keys()}
    all_cols.add("Total Score")

    df = pd.DataFrame(rows)
    for col in [c for c in all_cols if c not in df.columns]:
        df[col] = 0.0

    # Order columns: Ticker | sections... | Total Score
    section_cols = [c for c in sorted(all_cols) if c not in {"Ticker", "Total Score"}]
    df = df[["Ticker"] + section_cols + ["Total Score"]]
    return df



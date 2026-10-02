"""Shared formatting and startup helpers for the Streamlit dashboard."""

from pathlib import Path

import streamlit as st

from src.db import DB_PATH
from scripts.load_db import DEFAULT_EXCEL_PATH, load_database


def ensure_database() -> None:
    """Create the SQLite database from Excel when it does not exist."""
    if Path(DB_PATH).exists():
        return

    if not Path(DEFAULT_EXCEL_PATH).exists():
        st.error(
            "Source data is missing. Expected: "
            f"{DEFAULT_EXCEL_PATH.relative_to(DEFAULT_EXCEL_PATH.parents[1])}"
        )
        st.stop()

    with st.spinner("Preparing analytics database..."):
        load_database(
            excel_path=DEFAULT_EXCEL_PATH,
            db_path=DB_PATH,
            reset=True,
        )


def format_number(value: float | int, decimals: int = 0) -> str:
    """Format numbers with separators."""
    return f"{value:,.{decimals}f}"


def format_money(value: float | int, compact: bool = False) -> str:
    """Format monetary values in Toman."""
    if compact:
        abs_value = abs(value)

        if abs_value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B Toman"
        if abs_value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M Toman"
        if abs_value >= 1_000:
            return f"{value / 1_000:.1f}K Toman"

    return f"{value:,.0f} Toman"


def format_percent(value: float, decimals: int = 1) -> str:
    """Format a percentage value."""
    return f"{value:.{decimals}f}%"


def format_duration(seconds: float | int) -> str:
    """Format seconds as a compact minutes/seconds string."""
    seconds = int(round(seconds))
    minutes, seconds = divmod(seconds, 60)

    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def page_header(title: str, description: str) -> None:
    """Render a consistent page heading."""
    st.title(title)
    st.caption(description)

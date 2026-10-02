"""Streamlit entry point and navigation configuration."""

from pathlib import Path

from src.utils import ensure_database

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "assets" / "icon.png"

st.set_page_config(
    page_title="Bozhan Product Analytics",
    page_icon=str(ICON_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_database()

overview_page = st.Page(
    "pages/overview.py",
    title="Overview",
    icon=":material/dashboard:",
    default=True,
)

monthly_review_page = st.Page(
    "pages/monthly_review.py",
    title="Monthly Review",
    icon=":material/calendar_month:",
)

commercial_page = st.Page(
    "pages/commercial.py",
    title="Commercial",
    icon=":material/payments:",
)

product_ai_page = st.Page(
    "pages/product.py",
    title="Product",
    icon=":material/smart_toy:",
)

customers_page = st.Page(
    "pages/customers.py",
    title="Customers",
    icon=":material/group:",
)

navigation = st.navigation(
    {
        "Analytics": [
            overview_page,
            commercial_page,
            product_ai_page,
            customers_page,
            monthly_review_page,
        ]
    }
)

navigation.run()

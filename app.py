"""Streamlit entry point and navigation configuration."""

import streamlit as st

from src.utils import ensure_database


st.set_page_config(
    page_title="Startup Product Analytics",
    page_icon="📊",
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
        ]
    }
)

navigation.run()

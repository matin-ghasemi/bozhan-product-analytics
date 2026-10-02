"""Commercial performance dashboard."""

import plotly.express as px
import streamlit as st

from src.queries import (
    get_category_performance,
    get_marketing_campaign_performance,
    get_payment_method_performance,
    get_product_performance,
    get_sales_call_metrics,
)
from src.utils import ensure_database, format_number, format_percent, page_header

ensure_database()

page_header(
    "Commercial",
    "Revenue drivers, payment behavior, product/category performance, campaigns, and sales calls.",
)

payments = get_payment_method_performance()
products = get_product_performance()
categories = get_category_performance()
campaigns = get_marketing_campaign_performance()
sales = get_sales_call_metrics()

c1, c2, c3 = st.columns(3)
c1.metric("Sales Calls", format_number(sales["total_calls"]))
c2.metric("Sales Call Purchases", format_number(sales["purchases"]))
c3.metric("Sales Call Conversion", format_percent(sales["conversion_rate"]))

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Revenue by Payment Method")
    fig = px.bar(payments, x="payment_type", y="revenue",
                 labels={"payment_type": "Payment Method", "revenue": "Revenue (Toman)"})
    fig.update_yaxes(tickformat=",")
    fig.update_traces(hovertemplate="Payment Method=%{x}<br>Revenue=%{y:,.0f} Toman<extra></extra>")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Transaction Share")
    fig = px.pie(payments, names="payment_type", values="transactions", hole=0.45)
    fig.update_traces(textinfo="percent+label",
                      hovertemplate="%{label}<br>Transactions=%{value:,}<br>Share=%{percent}<extra></extra>")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("Units Sold by Category")
    fig = px.bar(categories, x="category_name", y="units_sold",
                 labels={"category_name": "Category", "units_sold": "Units Sold"})
    fig.update_yaxes(tickformat=",")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top Products by Units Sold")
    top_products = products.nlargest(10, "units_sold")
    fig = px.bar(top_products, x="units_sold", y="product_name", orientation="h",
                 labels={"units_sold": "Units Sold", "product_name": "Product"})
    fig.update_xaxes(tickformat=",")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Marketing Campaign Efficiency")
campaign_view = campaigns[["campaign_id", "budget", "clicks", "conversions", "conversion_rate_pct", "cost_per_click", "cost_per_conversion"]].copy()

st.dataframe(
    campaign_view,
    use_container_width=True,
    hide_index=True,
    column_config={
        "campaign_id": st.column_config.NumberColumn("Campaign ID", format="%d"),
        "budget": st.column_config.NumberColumn("Budget (Toman)", format="%,d"),
        "clicks": st.column_config.NumberColumn("Clicks", format="%,d"),
        "conversions": st.column_config.NumberColumn("Conversions", format="%,d"),
        "conversion_rate_pct": st.column_config.NumberColumn("Conversion Rate", format="%.2f%%"),
        "cost_per_click": st.column_config.NumberColumn("Cost per Click (Toman)", format="%,.0f"),
        "cost_per_conversion": st.column_config.NumberColumn("Cost per Conversion (Toman)", format="%,.0f"),
    },
)

with st.expander("Revenue allocation note"):
    st.markdown("""
    Product-level revenue is not directly available in the dataset because transaction
    revenue is recorded at the order level and product prices are missing.

    The query layer therefore allocates each order's transaction amount proportionally
    by item quantity. Product **units sold** should be treated as the stronger direct metric.
    """)

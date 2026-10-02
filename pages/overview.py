"""Executive overview dashboard."""

import plotly.express as px
import streamlit as st

from src.queries import (
    get_customer_metrics,
    get_monthly_performance,
    get_monthly_visits,
    get_overview_metrics,
    get_visit_metrics,
)
from src.utils import (
    ensure_database,
    format_money,
    format_number,
    format_percent,
    page_header,
)

ensure_database()

page_header(
    "Overview",
    "High-level view of commercial performance, traffic, and customer behavior.",
)

overview = get_overview_metrics()
visits = get_visit_metrics()
customers = get_customer_metrics()
monthly = get_monthly_performance()
monthly_visits = get_monthly_visits()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Revenue", format_money(overview["total_revenue"], compact=True))
k2.metric("Completed Orders", format_number(overview["total_orders"]))
k3.metric("Average Order Value", format_money(overview["average_order_value"], compact=True))
k4.metric("Purchasing Customers", format_number(overview["purchasing_customers"]))

k5, k6, k7, k8 = st.columns(4)
k5.metric("Sessions", format_number(visits["total_sessions"]))
k6.metric("Unique Visitors", format_number(visits["unique_visitors"]))
k7.metric("Buyer Rate", format_percent(customers["buyers"] / customers["total_customers"] * 100))
k8.metric("Repeat Purchase Rate", format_percent(customers["repeat_purchase_rate"]))

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Monthly Revenue")
    fig = px.line(monthly, x="month", y="revenue", markers=True,
                  labels={"month": "Month", "revenue": "Revenue (Toman)"})
    fig.update_yaxes(tickformat=",")
    fig.update_traces(hovertemplate="Month=%{x}<br>Revenue=%{y:,.0f} Toman<extra></extra>")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Orders by Month")
    fig = px.bar(monthly, x="month", y="orders",
                 labels={"month": "Month", "orders": "Orders"})
    fig.update_yaxes(tickformat=",")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("Traffic Trend")
    fig = px.line(monthly_visits, x="month", y="sessions", markers=True,
                  labels={"month": "Month", "sessions": "Sessions"})
    fig.update_yaxes(tickformat=",")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("AOV by Month")
    fig = px.bar(monthly, x="month", y="average_order_value",
                 labels={"month": "Month", "average_order_value": "Average Order Value (Toman)"})
    fig.update_yaxes(tickformat=",")
    fig.update_traces(hovertemplate="Month=%{x}<br>AOV=%{y:,.0f} Toman<extra></extra>")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with st.expander("Metric notes"):
    st.markdown("""
    - **Revenue** uses transactions linked to completed orders.
    - **Buyer Rate** = customers with at least one completed order / all customers.
    - **Repeat Purchase Rate** = customers with more than one completed order / buyers.
    - Monetary values are presented in **Toman** based on the project context.
    """)

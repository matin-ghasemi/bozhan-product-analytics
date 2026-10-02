"""Monthly drill-down dashboard."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.queries import (
    get_available_months,
    get_monthly_category_performance,
    get_monthly_consultation_outcomes,
    get_monthly_customer_mix,
    get_monthly_daily_activity,
    get_monthly_payment_performance,
    get_monthly_product_performance,
    get_monthly_review_metrics,
    get_available_months
)
from src.theme import MATERIAL
from src.utils import (
    ensure_database,
    format_money,
    format_number,
    format_percent,
    page_header,
)


ensure_database()


def pct_change(current: float, previous: float) -> float | None:
    """Return percentage change from the previous period."""
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def delta_text(value: float | None) -> str | None:
    """Format a month-over-month delta."""
    if value is None:
        return None
    return f"{value:+.1f}% vs previous month"


months = get_available_months()

if not months:
    st.warning("No monthly data is available.")
    st.stop()

page_header(
    "Monthly Review",
    "Select a month and drill into commercial, traffic, customer, product, and AI performance.",
)

selected_month = st.selectbox(
    "Select Month",
    months,
    index=len(months) - 1,
    format_func=lambda month: pd.to_datetime(
        f"{month}-01"
    ).strftime("%B %Y"),
)

selected_index = months.index(selected_month)
previous_month = months[selected_index - 1] if selected_index > 0 else None

metrics = get_monthly_review_metrics(selected_month)
previous_metrics = (
    get_monthly_review_metrics(previous_month)
    if previous_month
    else None
)

# -------------------------------------------------------------------
# Monthly snapshot
# -------------------------------------------------------------------

st.subheader("Monthly Snapshot")

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Revenue",
    format_money(metrics["revenue"], compact=True),
    delta=(
        delta_text(
            pct_change(
                metrics["revenue"],
                previous_metrics["revenue"],
            )
        )
        if previous_metrics
        else None
    ),
)

k2.metric(
    "Completed Orders",
    format_number(metrics["orders"]),
    delta=(
        delta_text(
            pct_change(
                metrics["orders"],
                previous_metrics["orders"],
            )
        )
        if previous_metrics
        else None
    ),
)

k3.metric(
    "Average Order Value",
    format_money(metrics["average_order_value"], compact=True),
    delta=(
        delta_text(
            pct_change(
                metrics["average_order_value"],
                previous_metrics["average_order_value"],
            )
        )
        if previous_metrics
        else None
    ),
)

k4.metric(
    "Sessions",
    format_number(metrics["sessions"]),
    delta=(
        delta_text(
            pct_change(
                metrics["sessions"],
                previous_metrics["sessions"],
            )
        )
        if previous_metrics
        else None
    ),
)

k5, k6, k7, k8 = st.columns(4)

k5.metric(
    "Buyers",
    format_number(metrics["buyers"]),
)

k6.metric(
    "Unique Visitors",
    format_number(metrics["unique_visitors"]),
)

k7.metric(
    "Buyer Rate",
    format_percent(metrics["buyer_rate"]),
)

k8.metric(
    "AI Consultations",
    format_number(metrics["consultations"]),
)

st.divider()


# -------------------------------------------------------------------
# Daily activity
# -------------------------------------------------------------------

daily = get_monthly_daily_activity(selected_month)

left, right = st.columns(2)

with left:
    st.subheader("Daily Revenue")

    if daily.empty:
        st.info("No revenue data for this month.")
    else:
        fig = px.line(
            daily,
            x="day",
            y="revenue",
            markers=True,
            labels={
                "day": "Day",
                "revenue": "Revenue (Toman)",
            },
            color_discrete_sequence=[MATERIAL["primary"]],
        )
        fig.update_traces(
            hovertemplate=(
                "%{x}<br>"
                "Revenue=%{y:,.0f} Toman"
                "<extra></extra>"
            )
        )
        fig.update_yaxes(tickformat=",")
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Daily Sessions")

    if daily.empty:
        st.info("No session data for this month.")
    else:
        fig = px.line(
            daily,
            x="day",
            y="sessions",
            markers=True,
            labels={
                "day": "Day",
                "sessions": "Sessions",
            },
            color_discrete_sequence=[MATERIAL["secondary"]],
        )
        fig.update_yaxes(tickformat=",")
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)


# -------------------------------------------------------------------
# Commercial and customer mix
# -------------------------------------------------------------------

payment = get_monthly_payment_performance(selected_month)
customer_mix = get_monthly_customer_mix(selected_month)

left, right = st.columns(2)

with left:
    st.subheader("Revenue by Payment Method")

    if payment.empty:
        st.info("No completed-order transactions for this month.")
    else:
        fig = px.bar(
            payment,
            x="payment_type",
            y="revenue",
            labels={
                "payment_type": "Payment Method",
                "revenue": "Revenue (Toman)",
            },
            color_discrete_sequence=[MATERIAL["primary"]],
        )
        fig.update_traces(
            hovertemplate=(
                "%{x}<br>"
                "Revenue=%{y:,.0f} Toman"
                "<extra></extra>"
            )
        )
        fig.update_yaxes(tickformat=",")
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("New vs. Returning Buyers")

    if customer_mix.empty:
        st.info("No buyers for this month.")
    else:
        fig = px.pie(
            customer_mix,
            names="segment",
            values="customers",
            hole=0.45,
            color="segment",
            color_discrete_map={
                "New Buyer": MATERIAL["primary"],
                "Returning Buyer": MATERIAL["success"],
            },
        )
        fig.update_traces(
            textinfo="percent+label",
            hovertemplate=(
                "%{label}<br>"
                "Customers=%{value:,}<br>"
                "Share=%{percent}"
                "<extra></extra>"
            ),
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=20, b=0),
            legend_title=None,
        )
        st.plotly_chart(fig, use_container_width=True)


# -------------------------------------------------------------------
# Product performance
# -------------------------------------------------------------------

products = get_monthly_product_performance(selected_month)
categories = get_monthly_category_performance(selected_month)

left, right = st.columns(2)

with left:
    st.subheader("Top Products by Units Sold")

    if products.empty:
        st.info("No product sales for this month.")
    else:
        top_products = (
            products.head(10)
            .sort_values("units_sold", ascending=True)
        )

        fig = px.bar(
            top_products,
            x="units_sold",
            y="product_name",
            orientation="h",
            labels={
                "units_sold": "Units Sold",
                "product_name": "Product",
            },
            color_discrete_sequence=[MATERIAL["ai"]],
        )
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Units Sold by Category")

    if categories.empty:
        st.info("No category sales for this month.")
    else:
        fig = px.bar(
            categories,
            x="category_name",
            y="units_sold",
            labels={
                "category_name": "Category",
                "units_sold": "Units Sold",
            },
            color_discrete_sequence=[MATERIAL["secondary"]],
        )
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)


# -------------------------------------------------------------------
# AI outcomes
# -------------------------------------------------------------------

outcomes = get_monthly_consultation_outcomes(selected_month)

st.subheader("AI Consultation Outcomes")

if outcomes.empty:
    st.info("No AI consultations for this month.")
else:
    outcomes = outcomes.copy()
    total_consultations = outcomes["consultations"].sum()

    outcomes["percentage"] = (
        outcomes["consultations"]
        / total_consultations
        * 100
    )
    outcomes["group"] = "Consultations"

    fig = px.bar(
        outcomes,
        x="consultations",
        y="group",
        color="outcome",
        orientation="h",
        barmode="stack",
        color_discrete_map={
            "Purchased later": MATERIAL["success"],
            "No later purchase": MATERIAL["danger"],
        },
        category_orders={
            "outcome": [
                "Purchased later",
                "No later purchase",
            ],
        },
        custom_data=["percentage"],
        labels={
            "consultations": "Consultations",
            "group": "",
            "outcome": "Outcome",
        },
    )

    fig.update_traces(
        texttemplate="%{x} (%{customdata[0]:.1f}%)",
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate=(
            "%{fullData.name}<br>"
            "Consultations=%{x}<br>"
            "Share=%{customdata[0]:.1f}%"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=280,
        legend=dict(
            title=None,
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="left",
            x=0,
        ),
        xaxis_title="Consultations",
        yaxis_title=None,
        margin=dict(l=0, r=0, t=70, b=0),
    )

    fig.update_yaxes(showticklabels=False)

    st.plotly_chart(fig, use_container_width=True)


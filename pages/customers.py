"""Customer analytics dashboard."""

import plotly.express as px
import streamlit as st

from src.queries import (
    get_customer_metrics,
    get_customer_purchase_summary,
)
from src.theme import MATERIAL
from src.utils import (
    ensure_database,
    format_number,
    format_percent,
    page_header,
)


ensure_database()

page_header(
    "Customers",
    "Customer activation, repeat purchase behavior, and revenue concentration.",
)

metrics = get_customer_metrics()
customers = get_customer_purchase_summary()

buyer_rate = (
    metrics["buyers"] / metrics["total_customers"] * 100
    if metrics["total_customers"]
    else 0
)

# -------------------------
# KPI Metrics
# -------------------------

c1, c2, c3 = st.columns(3)

c1.metric(
    "Registered Customers",
    format_number(metrics["total_customers"]),
)

c2.metric(
    "Buyers",
    format_number(metrics["buyers"]),
)

c3.metric(
    "Buyer Rate",
    format_percent(buyer_rate),
)

c4, c5, c6 = st.columns(3)

c4.metric(
    "Repeat Buyers",
    format_number(metrics["repeat_buyers"]),
)

c5.metric(
    "Repeat Purchase Rate",
    format_percent(metrics["repeat_purchase_rate"]),
)

c6.metric(
    "Avg. Orders / Customer",
    f"{metrics['average_orders_per_customer']:.2f}",
)

st.divider()

# -------------------------
# Customer Behavior
# -------------------------

left, right = st.columns(2)

with left:
    st.subheader("Orders per Customer")

    order_distribution = (
        customers["orders"]
        .value_counts()
        .sort_index()
        .rename_axis("orders")
        .reset_index(name="customers")
    )

    fig = px.bar(
        order_distribution,
        x="orders",
        y="customers",
        labels={
            "orders": "Completed Orders",
            "customers": "Customers",
        },
        color_discrete_sequence=[MATERIAL["primary"]],
    )

    fig.update_yaxes(
        tickformat=",",
    )

    fig.update_layout(
        margin=dict(
            l=0,
            r=0,
            t=20,
            b=0,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


with right:
    st.subheader("Buyer vs. Non-Buyer")

    buyers = int(
        (customers["orders"] > 0).sum()
    )

    non_buyers = int(
        (customers["orders"] == 0).sum()
    )

    buyer_data = {
        "segment": [
            "Buyer",
            "No Purchase",
        ],
        "customers": [
            buyers,
            non_buyers,
        ],
    }

    fig = px.pie(
        buyer_data,
        names="segment",
        values="customers",
        hole=0.45,
        color="segment",
        color_discrete_map={
            "Buyer": MATERIAL["success"],
            "No Purchase": MATERIAL["danger"],
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
        margin=dict(
            l=0,
            r=0,
            t=20,
            b=0,
        ),
        legend_title=None,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# -------------------------
# Revenue Concentration
# -------------------------

st.subheader("Top Customers by Revenue")

top_customers = (
    customers[
        customers["revenue"] > 0
    ]
    .nlargest(
        15,
        "revenue",
    )
    .copy()
)

top_customers["customer_id"] = (
    top_customers["user_id"]
    .astype(str)
)

fig = px.bar(
    top_customers,
    x="revenue",
    y="customer_id",
    orientation="h",
    labels={
        "revenue": "Revenue (Toman)",
        "customer_id": "Customer ID",
    },
    color_discrete_sequence=[
        MATERIAL["secondary"]
    ],
)

fig.update_xaxes(
    tickformat=",",
)

fig.update_traces(
    hovertemplate=(
        "Customer ID=%{y}<br>"
        "Revenue=%{x:,.0f} Toman"
        "<extra></extra>"
    ),
)

fig.update_layout(
    yaxis={
        "categoryorder": "total ascending",
    },
    margin=dict(
        l=0,
        r=0,
        t=20,
        b=0,
    ),
)

st.plotly_chart(
    fig,
    use_container_width=True,
)
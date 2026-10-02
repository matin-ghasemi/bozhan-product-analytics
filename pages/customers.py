"""Customer analytics dashboard."""

import plotly.express as px
import streamlit as st

from src.queries import (
    get_customer_metrics,
    get_customer_purchase_summary,
)
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

c1, c2, c3, c4 = st.columns(4)

c1.metric("Registered Customers", format_number(metrics["total_customers"]))
c2.metric("Buyers", format_number(metrics["buyers"]))
c3.metric("Repeat Buyers", format_number(metrics["repeat_buyers"]))
c4.metric("Repeat Purchase Rate", format_percent(metrics["repeat_purchase_rate"]))

buyer_rate = (
    metrics["buyers"] / metrics["total_customers"] * 100
    if metrics["total_customers"]
    else 0
)

st.caption(
    f"Buyer rate: {format_percent(buyer_rate)} · "
    f"Average completed orders per registered customer: "
    f"{metrics['average_orders_per_customer']:.2f}"
)

st.divider()

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
        labels={"orders": "Completed Orders", "customers": "Customers"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Buyer vs. Non-Buyer")
    buyers = int((customers["orders"] > 0).sum())
    non_buyers = int((customers["orders"] == 0).sum())

    buyer_split = {
        "segment": ["Buyer", "No Purchase"],
        "customers": [buyers, non_buyers],
    }

    fig = px.pie(
        buyer_split,
        names="segment",
        values="customers",
        hole=0.45,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Top Customers by Revenue")
top_customers = customers[customers["revenue"] > 0].nlargest(15, "revenue")

fig = px.bar(
    top_customers,
    x="revenue",
    y=top_customers["user_id"].astype(str),
    orientation="h",
    labels={"revenue": "Revenue", "y": "Customer ID"},
)
fig.update_layout(
    yaxis={"categoryorder": "total ascending"},
    margin=dict(l=0, r=0, t=20, b=0),
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Metric definition"):
    st.markdown(
        """
        - **Buyer**: customer with at least one completed order.
        - **Repeat Buyer**: customer with more than one completed order.
        - **Repeat Purchase Rate**: repeat buyers / buyers.
        """
    )

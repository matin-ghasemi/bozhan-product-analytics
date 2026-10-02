"""Product and AI consultation dashboard."""

import plotly.express as px
import streamlit as st

from src.queries import (
    get_consultation_details,
    get_consultation_metrics,
    get_monthly_visits,
    get_visit_metrics,
)
from src.utils import (
    ensure_database,
    format_duration,
    format_number,
    format_percent,
    page_header,
)


ensure_database()

page_header(
    "Product & AI",
    "Website engagement and AI consultation behavior, including post-consultation purchase signals.",
)

visits = get_visit_metrics()
monthly_visits = get_monthly_visits()
consultation = get_consultation_metrics()
details = get_consultation_details()

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Sessions", format_number(visits["total_sessions"]))
c2.metric("Avg. Page Views", f"{visits['average_page_views']:.1f}")
c3.metric("Avg. Session Duration", format_duration(visits["average_session_seconds"]))
c4.metric("AI Consultations", format_number(consultation["total_consultations"]))

c5, c6, c7 = st.columns(3)

c5.metric(
    "Avg. Consultation Duration",
    format_duration(consultation["average_duration_seconds"]),
)
c6.metric(
    "Avg. Messages",
    f"{consultation['average_message_count']:.1f}",
)
c7.metric(
    "Post-Consultation Purchase Rate",
    format_percent(consultation["post_consultation_purchase_rate"]),
)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Monthly Website Sessions")
    fig = px.line(
        monthly_visits,
        x="month",
        y="sessions",
        markers=True,
        labels={"month": "Month", "sessions": "Sessions"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Consultation Duration vs. Messages")
    plot_data = details.copy()
    plot_data["purchase_outcome"] = plot_data[
        "purchased_after_consultation"
    ].map({1: "Purchased later", 0: "No later purchase"})

    fig = px.scatter(
        plot_data,
        x="duration_seconds",
        y="message_count",
        color="purchase_outcome",
        hover_data=["user_id"],
        labels={
            "duration_seconds": "Consultation Duration (seconds)",
            "message_count": "Message Count",
            "purchase_outcome": "Outcome",
        },
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("AI Consultation Outcomes")

outcome_counts = (
    details["purchased_after_consultation"]
    .map({1: "Purchased later", 0: "No later purchase"})
    .value_counts()
    .rename_axis("outcome")
    .reset_index(name="users")
)

fig = px.bar(
    outcome_counts,
    x="outcome",
    y="users",
    labels={"outcome": "Outcome", "users": "Consultations"},
)
fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Important interpretation"):
    st.markdown(
        """
        The dataset does not contain a direct event linking an AI consultation to an order.
        Here, a user is counted as a **post-consultation purchaser** when they have a completed
        order at or after their first consultation.

        This is an observational signal, not proof that the AI consultation caused the purchase.
        """
    )

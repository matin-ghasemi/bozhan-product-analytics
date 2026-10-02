"""Product and AI consultation dashboard."""

import plotly.express as px
import streamlit as st

from src.theme import MATERIAL

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
    "Product",
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
        color_discrete_map={
            "Purchased later": MATERIAL["success"],
            "No later purchase": MATERIAL["danger"],
        },
        category_orders={
            "purchase_outcome": [
                "Purchased later",
                "No later purchase",
            ]
        },
        hover_data=["user_id"],
        labels={
            "duration_seconds": "Consultation Duration (seconds)",
            "message_count": "Message Count",
            "purchase_outcome": "Outcome",
        },
    )
    fig.update_traces(
        marker={
            "size": 11,
            "opacity": 0.9,
        }
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("AI Consultation Outcomes")

outcome_counts = (
    details["purchased_after_consultation"]
    .map({
        1: "Purchased later",
        0: "No later purchase",
    })
    .value_counts()
    .rename_axis("outcome")
    .reset_index(name="users")
)

total_consultations = outcome_counts["users"].sum()

outcome_counts["percentage"] = (
    outcome_counts["users"] / total_consultations * 100
)

# One horizontal bar
outcome_counts["group"] = "Consultations"

fig = px.bar(
    outcome_counts,
    x="users",
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
        ]
    },
    custom_data=["percentage"],
    labels={
        "users": "Consultations",
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
        "Consultations: %{x}<br>"
        "Share: %{customdata[0]:.1f}%"
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

    margin=dict(
        l=0,
        r=0,
        t=70,
        b=0,
        ),
)

fig.update_xaxes(
    tickformat=",",
    rangemode="tozero",
)

fig.update_yaxes(showticklabels=False)

st.plotly_chart(
    fig,
    use_container_width=True,
)
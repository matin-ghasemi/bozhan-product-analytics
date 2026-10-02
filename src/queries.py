"""Reusable SQL queries for the startup analytics dashboard."""

from __future__ import annotations

from contextlib import closing

import pandas as pd

from src.db import get_connection


def _read_sql(query: str, params: dict | None = None) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""
    with closing(get_connection()) as connection:
        return pd.read_sql_query(query, connection, params=params or {})


def get_overview_metrics() -> dict:
    """Return the main commercial KPIs for the overview page."""
    query = """
        SELECT
            COUNT(DISTINCT o.order_id) AS total_orders,
            COUNT(DISTINCT o.user_id) AS purchasing_customers,
            COALESCE(SUM(t.amount), 0) AS total_revenue,
            COALESCE(1.0 * SUM(t.amount) /
                NULLIF(COUNT(DISTINCT o.order_id), 0), 0) AS average_order_value
        FROM orders AS o
        LEFT JOIN transactions AS t
            ON t.order_id = o.order_id
        WHERE o.status = 'Completed';
    """

    row = _read_sql(query).iloc[0]

    return {
        "total_orders": int(row["total_orders"]),
        "purchasing_customers": int(row["purchasing_customers"]),
        "total_revenue": int(row["total_revenue"]),
        "average_order_value": float(row["average_order_value"]),
    }


def get_monthly_performance() -> pd.DataFrame:
    """Return monthly orders, customers, revenue, and AOV."""
    query = """
        SELECT
            strftime('%Y-%m', o.order_date) AS month,
            COUNT(DISTINCT o.order_id) AS orders,
            COUNT(DISTINCT o.user_id) AS customers,
            COALESCE(SUM(t.amount), 0) AS revenue,
            COALESCE(1.0 * SUM(t.amount) /
                NULLIF(COUNT(DISTINCT o.order_id), 0), 0) AS average_order_value
        FROM orders AS o
        LEFT JOIN transactions AS t
            ON t.order_id = o.order_id
        WHERE o.status = 'Completed'
        GROUP BY strftime('%Y-%m', o.order_date)
        ORDER BY month;
    """

    return _read_sql(query)


def get_payment_method_performance() -> pd.DataFrame:
    """Return transaction performance grouped by payment method."""
    query = """
        WITH payment_summary AS (
            SELECT
                payment_type,
                COUNT(*) AS transactions,
                SUM(amount) AS revenue,
                AVG(amount) AS average_transaction_value
            FROM transactions AS t
            JOIN orders AS o ON o.order_id = t.order_id
            WHERE o.status = 'Completed'
            GROUP BY payment_type
        )
        SELECT
            payment_type,
            transactions,
            revenue,
            average_transaction_value,
            ROUND(
                100.0 * transactions /
                (SELECT SUM(transactions) FROM payment_summary),
                2
            ) AS transaction_share_pct
        FROM payment_summary
        ORDER BY revenue DESC;
    """

    return _read_sql(query)


def get_product_performance() -> pd.DataFrame:
    """Return product-level sales volume and allocated revenue."""
    query = """
        WITH order_payments AS (
            SELECT order_id, SUM(amount) AS amount
            FROM transactions
            GROUP BY order_id
        ), order_quantities AS (
            SELECT
                order_id,
                SUM(quantity) AS total_quantity
            FROM order_details
            GROUP BY order_id
        ),
        product_sales AS (
            SELECT
                p.product_id,
                p.name AS product_name,
                c.name AS category_name,
                od.order_id,
                od.quantity,
                p.stock_quantity,
                COALESCE(t.amount, 0) * od.quantity * 1.0 / oq.total_quantity
                    AS allocated_revenue
            FROM order_details AS od
            JOIN order_quantities AS oq
                ON oq.order_id = od.order_id
            JOIN products AS p
                ON p.product_id = od.product_id
            JOIN categories AS c
                ON c.category_id = p.category_id
            JOIN orders AS o ON o.order_id = od.order_id
            LEFT JOIN order_payments AS t
                ON t.order_id = od.order_id
            WHERE o.status = 'Completed'
        )
        SELECT
            product_id,
            product_name,
            category_name,
            SUM(quantity) AS units_sold,
            COUNT(DISTINCT order_id) AS orders,
            ROUND(SUM(allocated_revenue), 2) AS allocated_revenue,
            stock_quantity
        FROM product_sales
        GROUP BY
            product_id,
            product_name,
            category_name,
            stock_quantity
        ORDER BY units_sold DESC, allocated_revenue DESC;
    """

    return _read_sql(query)


def get_category_performance() -> pd.DataFrame:
    """Return category-level order and unit performance."""
    query = """
        SELECT
            c.category_id,
            c.name AS category_name,
            COUNT(DISTINCT od.order_id) AS orders,
            SUM(od.quantity) AS units_sold,
            COUNT(DISTINCT p.product_id) AS products
        FROM order_details AS od
        JOIN orders AS o ON o.order_id = od.order_id
        JOIN products AS p
            ON p.product_id = od.product_id
        JOIN categories AS c
            ON c.category_id = p.category_id
        WHERE o.status = 'Completed'
        GROUP BY c.category_id, c.name
        ORDER BY units_sold DESC;
    """

    return _read_sql(query)


def get_visit_metrics() -> dict:
    """Return high-level website/session engagement metrics."""
    query = """
        SELECT
            COUNT(*) AS total_sessions,
            COUNT(DISTINCT user_id) AS unique_visitors,
            COALESCE(AVG(page_views), 0) AS average_page_views,
            COALESCE(AVG(
                (julianday(end_time) - julianday(start_time)) * 86400
            ), 0) AS average_session_seconds
        FROM visits;
    """

    row = _read_sql(query).iloc[0]

    return {
        "total_sessions": int(row["total_sessions"]),
        "unique_visitors": int(row["unique_visitors"]),
        "average_page_views": float(row["average_page_views"]),
        "average_session_seconds": float(row["average_session_seconds"]),
    }


def get_monthly_visits() -> pd.DataFrame:
    """Return monthly sessions, visitors, and page views."""
    query = """
        SELECT
            strftime('%Y-%m', start_time) AS month,
            COUNT(*) AS sessions,
            COUNT(DISTINCT user_id) AS unique_visitors,
            SUM(page_views) AS page_views,
            AVG(page_views) AS average_page_views
        FROM visits
        GROUP BY strftime('%Y-%m', start_time)
        ORDER BY month;
    """

    return _read_sql(query)


def get_customer_purchase_summary() -> pd.DataFrame:
    """Return order and revenue history for each customer."""
    query = """
        SELECT
            c.user_id,
            c.signup_date,
            COUNT(DISTINCT o.order_id) AS orders,
            COALESCE(SUM(t.amount), 0) AS revenue,
            MIN(o.order_date) AS first_order_date,
            MAX(o.order_date) AS latest_order_date
        FROM customers AS c
        LEFT JOIN orders AS o
            ON o.user_id = c.user_id
           AND o.status = 'Completed'
        LEFT JOIN transactions AS t
            ON t.order_id = o.order_id
        GROUP BY c.user_id, c.signup_date
        ORDER BY revenue DESC;
    """

    return _read_sql(query)


def get_customer_metrics() -> dict:
    """Return customer and repeat-purchase metrics."""
    query = """
        WITH customer_orders AS (
            SELECT
                c.user_id,
                COUNT(DISTINCT o.order_id) AS order_count
            FROM customers AS c
            LEFT JOIN orders AS o
                ON o.user_id = c.user_id
               AND o.status = 'Completed'
            GROUP BY c.user_id
        )
        SELECT
            COUNT(*) AS total_customers,
            COALESCE(SUM(CASE WHEN order_count > 0 THEN 1 ELSE 0 END), 0) AS buyers,
            COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_buyers,
            COALESCE(AVG(order_count), 0) AS average_orders_per_customer
        FROM customer_orders;
    """

    row = _read_sql(query).iloc[0]

    buyers = int(row["buyers"])
    repeat_buyers = int(row["repeat_buyers"])

    return {
        "total_customers": int(row["total_customers"]),
        "buyers": buyers,
        "repeat_buyers": repeat_buyers,
        "repeat_purchase_rate": repeat_buyers / buyers * 100 if buyers else 0,
        "average_orders_per_customer": float(row["average_orders_per_customer"]),
    }


def get_consultation_metrics() -> dict:
    """Return AI consultation usage and post-consultation purchase metrics."""
    query = """
        WITH consultation_users AS (
            SELECT
                user_id,
                MIN(consultation_date) AS first_consultation_date
            FROM consultations
            GROUP BY user_id
        ),
        consultation_outcomes AS (
            SELECT
                cu.user_id,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM orders AS o
                        WHERE o.user_id = cu.user_id
                          AND o.status = 'Completed'
                          AND o.order_date >= cu.first_consultation_date
                    )
                    THEN 1
                    ELSE 0
                END AS purchased_after_consultation
            FROM consultation_users AS cu
        )
        SELECT
            (SELECT COUNT(*) FROM consultations) AS total_consultations,
            (SELECT COUNT(DISTINCT user_id) FROM consultations)
                AS consultation_users,
            (SELECT COALESCE(AVG(duration_seconds), 0) FROM consultations)
                AS avg_duration_seconds,
            (SELECT COALESCE(AVG(message_count), 0) FROM consultations)
                AS avg_message_count,
            COALESCE(SUM(purchased_after_consultation), 0)
                AS users_purchased_after_consultation
        FROM consultation_outcomes;
    """

    row = _read_sql(query).iloc[0]

    users = int(row["consultation_users"])
    purchasers = int(row["users_purchased_after_consultation"])

    return {
        "total_consultations": int(row["total_consultations"]),
        "consultation_users": users,
        "average_duration_seconds": float(row["avg_duration_seconds"]),
        "average_message_count": float(row["avg_message_count"]),
        "users_purchased_after_consultation": purchasers,
        "post_consultation_purchase_rate": purchasers / users * 100 if users else 0,
    }


def get_consultation_details() -> pd.DataFrame:
    """Return consultations with a later-purchase indicator."""
    query = """
        SELECT
            c.consultation_id,
            c.user_id,
            c.consultation_date,
            c.duration_seconds,
            c.message_count,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM orders AS o
                    WHERE o.user_id = c.user_id
                      AND o.status = 'Completed'
                      AND o.order_date >= c.consultation_date
                )
                THEN 1
                ELSE 0
            END AS purchased_after_consultation
        FROM consultations AS c
        ORDER BY c.consultation_date;
    """

    return _read_sql(query)


def get_sales_call_metrics() -> dict:
    """Return sales-call performance metrics."""
    query = """
        SELECT
            COUNT(*) AS total_calls,
            COALESCE(SUM(is_purchased), 0) AS purchases,
            COALESCE(AVG(call_duration), 0) AS average_call_duration
        FROM sales_calls;
    """

    row = _read_sql(query).iloc[0]

    total_calls = int(row["total_calls"])
    purchases = int(row["purchases"])

    return {
        "total_calls": total_calls,
        "purchases": purchases,
        "conversion_rate": purchases / total_calls * 100 if total_calls else 0,
        "average_call_duration": float(row["average_call_duration"]),
    }


def get_marketing_campaign_performance() -> pd.DataFrame:
    """Return campaign efficiency metrics."""
    query = """
        SELECT
            campaign_id,
            start_date,
            end_date,
            budget,
            clicks,
            conversions,
            ROUND(
                100.0 * conversions / NULLIF(clicks, 0),
                2
            ) AS conversion_rate_pct,
            ROUND(
                1.0 * budget / NULLIF(clicks, 0),
                2
            ) AS cost_per_click,
            ROUND(
                1.0 * budget / NULLIF(conversions, 0),
                2
            ) AS cost_per_conversion
        FROM marketing_campaigns
        ORDER BY conversion_rate_pct DESC;
    """

    return _read_sql(query)


def get_available_months() -> list[str]:
    """Return all months that have order, visit, or consultation activity."""
    query = """
        SELECT month
        FROM (
            SELECT DISTINCT strftime('%Y-%m', order_date) AS month
            FROM orders
            WHERE order_date IS NOT NULL

            UNION

            SELECT DISTINCT strftime('%Y-%m', start_time) AS month
            FROM visits
            WHERE start_time IS NOT NULL

            UNION

            SELECT DISTINCT strftime('%Y-%m', consultation_date) AS month
            FROM consultations
            WHERE consultation_date IS NOT NULL
        )
        WHERE month IS NOT NULL
        ORDER BY month;
    """

    return _read_sql(query)["month"].tolist()


def get_monthly_review_metrics(month: str) -> dict:
    """Return the main KPIs for one selected month."""
    query = """
        WITH completed_orders AS (
            SELECT
                order_id,
                user_id
            FROM orders
            WHERE status = 'Completed'
              AND strftime('%Y-%m', order_date) = :month
        ),
        order_metrics AS (
            SELECT
                COUNT(*) AS orders,
                COUNT(DISTINCT user_id) AS buyers
            FROM completed_orders
        ),
        revenue_metrics AS (
            SELECT
                COALESCE(SUM(t.amount), 0) AS revenue
            FROM transactions AS t
            JOIN completed_orders AS o
                ON o.order_id = t.order_id
        ),
        visit_metrics AS (
            SELECT
                COUNT(*) AS sessions,
                COUNT(DISTINCT user_id) AS unique_visitors
            FROM visits
            WHERE strftime('%Y-%m', start_time) = :month
        ),
        consultation_metrics AS (
            SELECT
                COUNT(*) AS consultations
            FROM consultations
            WHERE strftime('%Y-%m', consultation_date) = :month
        )
        SELECT
            om.orders,
            om.buyers,
            rm.revenue,
            CASE
                WHEN om.orders > 0
                THEN 1.0 * rm.revenue / om.orders
                ELSE 0
            END AS average_order_value,
            vm.sessions,
            vm.unique_visitors,
            cm.consultations
        FROM order_metrics AS om
        CROSS JOIN revenue_metrics AS rm
        CROSS JOIN visit_metrics AS vm
        CROSS JOIN consultation_metrics AS cm;
    """

    row = _read_sql(query, {"month": month}).iloc[0]

    buyers = int(row["buyers"])
    visitors = int(row["unique_visitors"])

    return {
        "month": month,
        "revenue": float(row["revenue"]),
        "orders": int(row["orders"]),
        "buyers": buyers,
        "average_order_value": float(row["average_order_value"]),
        "sessions": int(row["sessions"]),
        "unique_visitors": visitors,
        "consultations": int(row["consultations"]),
        "buyer_rate": buyers / visitors * 100 if visitors else 0,
    }


def get_monthly_daily_activity(month: str) -> pd.DataFrame:
    """Return daily revenue, completed orders, and sessions for one month."""
    query = """
        WITH order_daily AS (
            SELECT
                date(o.order_date) AS day,
                COUNT(DISTINCT o.order_id) AS orders,
                COALESCE(SUM(t.amount), 0) AS revenue
            FROM orders AS o
            LEFT JOIN transactions AS t
                ON t.order_id = o.order_id
            WHERE o.status = 'Completed'
              AND strftime('%Y-%m', o.order_date) = :month
            GROUP BY date(o.order_date)
        ),
        visit_daily AS (
            SELECT
                date(start_time) AS day,
                COUNT(*) AS sessions
            FROM visits
            WHERE strftime('%Y-%m', start_time) = :month
            GROUP BY date(start_time)
        ),
        days AS (
            SELECT day FROM order_daily
            UNION
            SELECT day FROM visit_daily
        )
        SELECT
            d.day,
            COALESCE(od.orders, 0) AS orders,
            COALESCE(od.revenue, 0) AS revenue,
            COALESCE(vd.sessions, 0) AS sessions
        FROM days AS d
        LEFT JOIN order_daily AS od
            ON od.day = d.day
        LEFT JOIN visit_daily AS vd
            ON vd.day = d.day
        ORDER BY d.day;
    """

    return _read_sql(query, {"month": month})


def get_monthly_payment_performance(month: str) -> pd.DataFrame:
    """Return payment-method performance for completed orders in one month."""
    query = """
        SELECT
            t.payment_type,
            COUNT(*) AS transactions,
            SUM(t.amount) AS revenue,
            AVG(t.amount) AS average_transaction_value
        FROM transactions AS t
        JOIN orders AS o
            ON o.order_id = t.order_id
        WHERE o.status = 'Completed'
          AND strftime('%Y-%m', o.order_date) = :month
        GROUP BY t.payment_type
        ORDER BY revenue DESC;
    """

    return _read_sql(query, {"month": month})


def get_monthly_customer_mix(month: str) -> pd.DataFrame:
    """Return new-vs-returning buyer counts for one month."""
    query = """
        WITH month_buyers AS (
            SELECT DISTINCT user_id
            FROM orders
            WHERE status = 'Completed'
              AND strftime('%Y-%m', order_date) = :month
        ),
        first_purchase AS (
            SELECT
                user_id,
                MIN(strftime('%Y-%m', order_date)) AS first_purchase_month
            FROM orders
            WHERE status = 'Completed'
            GROUP BY user_id
        )
        SELECT
            CASE
                WHEN fp.first_purchase_month = :month
                THEN 'New Buyer'
                ELSE 'Returning Buyer'
            END AS segment,
            COUNT(*) AS customers
        FROM month_buyers AS mb
        JOIN first_purchase AS fp
            ON fp.user_id = mb.user_id
        GROUP BY segment
        ORDER BY customers DESC;
    """

    return _read_sql(query, {"month": month})


def get_monthly_product_performance(month: str) -> pd.DataFrame:
    """Return product sales and allocated revenue for one month."""
    query = """
        WITH order_payments AS (
            SELECT order_id, SUM(amount) AS amount
            FROM transactions
            GROUP BY order_id
        ), order_quantities AS (
            SELECT
                od.order_id,
                SUM(od.quantity) AS total_quantity
            FROM order_details AS od
            GROUP BY od.order_id
        ),
        product_sales AS (
            SELECT
                p.product_id,
                p.name AS product_name,
                c.name AS category_name,
                od.order_id,
                od.quantity,
                COALESCE(t.amount, 0) * od.quantity * 1.0 / oq.total_quantity
                    AS allocated_revenue
            FROM orders AS o
            JOIN order_details AS od
                ON od.order_id = o.order_id
            JOIN order_quantities AS oq
                ON oq.order_id = od.order_id
            JOIN products AS p
                ON p.product_id = od.product_id
            JOIN categories AS c
                ON c.category_id = p.category_id
            LEFT JOIN order_payments AS t
                ON t.order_id = o.order_id
            WHERE o.status = 'Completed'
              AND strftime('%Y-%m', o.order_date) = :month
        )
        SELECT
            product_id,
            product_name,
            category_name,
            SUM(quantity) AS units_sold,
            COUNT(DISTINCT order_id) AS orders,
            ROUND(SUM(allocated_revenue), 2) AS allocated_revenue
        FROM product_sales
        GROUP BY
            product_id,
            product_name,
            category_name
        ORDER BY units_sold DESC, allocated_revenue DESC;
    """

    return _read_sql(query, {"month": month})


def get_monthly_category_performance(month: str) -> pd.DataFrame:
    """Return category sales volume for completed orders in one month."""
    query = """
        SELECT
            c.category_id,
            c.name AS category_name,
            COUNT(DISTINCT o.order_id) AS orders,
            SUM(od.quantity) AS units_sold
        FROM orders AS o
        JOIN order_details AS od
            ON od.order_id = o.order_id
        JOIN products AS p
            ON p.product_id = od.product_id
        JOIN categories AS c
            ON c.category_id = p.category_id
        WHERE o.status = 'Completed'
          AND strftime('%Y-%m', o.order_date) = :month
        GROUP BY c.category_id, c.name
        ORDER BY units_sold DESC;
    """

    return _read_sql(query, {"month": month})


def get_monthly_consultation_outcomes(month: str) -> pd.DataFrame:
    """Return later-purchase outcomes for consultations in one month."""
    query = """
        SELECT
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM orders AS o
                    WHERE o.user_id = c.user_id
                      AND o.status = 'Completed'
                      AND o.order_date >= c.consultation_date
                )
                THEN 'Purchased later'
                ELSE 'No later purchase'
            END AS outcome,
            COUNT(*) AS consultations
        FROM consultations AS c
        WHERE strftime('%Y-%m', c.consultation_date) = :month
        GROUP BY outcome
        ORDER BY consultations DESC;
    """

    return _read_sql(query, {"month": month})


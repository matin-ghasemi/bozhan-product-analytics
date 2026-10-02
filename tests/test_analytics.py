"""Regression coverage for metric consistency and safe workbook imports."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from scripts.load_db import DEFAULT_EXCEL_PATH, load_database, read_workbook, to_integer, prepare_table
from src import queries
from src.db import create_schema, get_connection

ROOT = Path(__file__).resolve().parents[1]


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"
        self.addCleanup(self.temp.cleanup)
        with closing(get_connection(self.db)) as connection:
            create_schema(connection)
        self.mock = patch("src.queries.get_connection", lambda: get_connection(self.db))
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def seed(self):
        with closing(get_connection(self.db)) as connection, connection:
            connection.executescript("""
                INSERT INTO customers VALUES (1, 'A', 'a@example.test', '2026-01-01');
                INSERT INTO categories VALUES (1, 'Skincare');
                INSERT INTO products VALUES (1, 'Cream', 1, 10), (2, 'Serum', 1, 10);
                INSERT INTO orders VALUES
                    (1, 1, '2026-01-10 12:00:00', 'Completed'),
                    (2, 1, '2026-01-20 12:00:00', 'Completed'),
                    (3, 1, '2026-01-25 12:00:00', 'Returned');
                INSERT INTO transactions VALUES
                    (1, 1, 'Card', 100, '2026-01-10 12:00:00'),
                    (2, 1, 'Card', 200, '2026-01-10 12:00:00'),
                    (3, 3, 'Card', 900, '2026-01-25 12:00:00');
                INSERT INTO order_details VALUES (1, 1, 2), (1, 2, 1), (2, 1, 1), (3, 1, 9);
                INSERT INTO consultations VALUES
                    (1, 1, '2026-01-05 12:00:00', 60, 3),
                    (2, 1, '2026-03-01 12:00:00', 60, 3);
            """)

    def test_aov_is_per_completed_order_including_unpaid_orders(self):
        self.seed()
        overview = queries.get_overview_metrics()
        monthly = queries.get_monthly_performance().iloc[0]
        review = queries.get_monthly_review_metrics("2026-01")
        self.assertEqual(overview["total_orders"], 2)
        self.assertEqual(overview["total_revenue"], 300)
        self.assertEqual(overview["average_order_value"], 150)
        self.assertEqual(monthly["orders"], 2)
        self.assertEqual(monthly["average_order_value"], 150)
        self.assertEqual(review["average_order_value"], 150)

    def test_product_units_are_not_multiplied_by_payments(self):
        self.seed()
        products = queries.get_product_performance().set_index("product_id")
        monthly = queries.get_monthly_product_performance("2026-01").set_index("product_id")
        self.assertEqual(products.loc[1, "units_sold"], 3)
        self.assertEqual(products.loc[2, "units_sold"], 1)
        self.assertEqual(products["allocated_revenue"].sum(), 300)
        self.assertEqual(monthly["allocated_revenue"].sum(), 300)
        self.assertEqual(monthly["units_sold"].sum(), 4)

    def test_commercial_queries_exclude_returned_orders(self):
        self.seed()
        payments = queries.get_payment_method_performance()
        categories = queries.get_category_performance()
        self.assertEqual(payments["revenue"].sum(), 300)
        self.assertEqual(payments["transactions"].sum(), 2)
        self.assertEqual(categories["units_sold"].sum(), 4)

    def test_empty_metrics_are_zero(self):
        for getter in [queries.get_overview_metrics, queries.get_visit_metrics,
                       queries.get_customer_metrics, queries.get_consultation_metrics,
                       queries.get_sales_call_metrics]:
            with self.subTest(query=getter.__name__):
                self.assertTrue(all(value == 0 for value in getter().values()))
        self.assertEqual(queries.get_available_months(), [])

    def test_consultation_only_month_is_selectable(self):
        self.seed()
        self.assertEqual(queries.get_available_months(), ["2026-01", "2026-03"])

    def test_consultation_users_and_events_have_distinct_denominators(self):
        self.seed()
        metrics = queries.get_consultation_metrics()
        self.assertEqual(metrics["consultation_users"], 1)
        self.assertEqual(metrics["post_consultation_purchase_rate"], 100)
        self.assertEqual(queries.get_consultation_details()["purchased_after_consultation"].tolist(), [1, 0])

    def test_integer_fields_reject_fractions(self):
        with self.assertRaises(ValueError):
            to_integer(pd.Series([1, 1.5], name="quantity"))

    def test_failed_reset_preserves_original_data_and_foreign_keys(self):
        self.seed()
        tables = read_workbook(DEFAULT_EXCEL_PATH)
        tables["marketing_campaigns"].loc[0, "budget"] = -1
        with patch("scripts.load_db.read_workbook", return_value=tables):
            with self.assertRaises(sqlite3.IntegrityError):
                load_database(db_path=self.db, reset=True)
        self.assertEqual(queries.get_overview_metrics()["total_revenue"], 300)
        with closing(get_connection(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_workbook_import_and_repeated_reset(self):
        counts = load_database(db_path=self.db)
        self.assertEqual(counts, load_database(db_path=self.db, reset=True))
        monthly = queries.get_monthly_performance()
        total = queries.get_overview_metrics()
        self.assertEqual(monthly["revenue"].sum(), total["total_revenue"])
        self.assertEqual(queries.get_payment_method_performance()["revenue"].sum(), total["total_revenue"])
        self.assertAlmostEqual(queries.get_product_performance()["allocated_revenue"].sum(), total["total_revenue"], places=1)

    def test_invalid_foreign_key_rolls_back_import(self):
        self.seed()
        tables = read_workbook(DEFAULT_EXCEL_PATH)
        tables["products"].loc[0, "category_id"] = -1
        with patch("scripts.load_db.read_workbook", return_value=tables):
            with self.assertRaises(sqlite3.IntegrityError):
                load_database(db_path=self.db, reset=True)
        self.assertEqual(queries.get_overview_metrics()["total_revenue"], 300)

    def test_invalid_visit_dates_are_rejected(self):
        visit = pd.DataFrame([dict(session_id=1, user_id=1,
                                   start_time="2026-01-02", end_time="2026-01-01",
                                   page_views=1)])
        with self.assertRaisesRegex(ValueError, "end_time precedes start_time"):
            prepare_table("visits", visit)

    def test_shipped_dashboard_and_every_month_render(self):
        with patch("src.queries.get_connection", get_connection):
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=20)
            self.assertEqual(list(app.exception), [])
            for name in ["commercial", "product", "customers", "monthly_review"]:
                app = AppTest.from_file(str(ROOT / "pages" / f"{name}.py")).run(timeout=20)
                self.assertEqual(list(app.exception), [])
                if name == "monthly_review":
                    for month in queries.get_available_months():
                        app.selectbox[0].select(month).run(timeout=20)
                        self.assertEqual(list(app.exception), [])

    def test_pages_render_with_empty_and_populated_data(self):
        for populated in [False, True]:
            if populated:
                self.seed()
            for name in ["overview", "commercial", "product", "customers", "monthly_review"]:
                with self.subTest(page=name, populated=populated):
                    app = AppTest.from_file(str(ROOT / "pages" / f"{name}.py")).run(timeout=20)
                    self.assertEqual(list(app.exception), [])
                    if name == "monthly_review" and populated:
                        # March has no orders and February is absent: no fake MoM comparison.
                        self.assertTrue(all(metric.delta is None or metric.delta == "" for metric in app.metric))
                        app.selectbox[0].select("2026-01").run(timeout=20)
                        self.assertEqual(list(app.exception), [])


if __name__ == "__main__":
    unittest.main()

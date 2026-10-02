"""Database configuration and schema for the startup analytics dashboard."""

from contextlib import closing
from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "startup.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a configured SQLite connection."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Create all database tables and indexes."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            signup_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );

        CREATE TABLE IF NOT EXISTS visits (
            session_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            page_views INTEGER NOT NULL CHECK (page_views >= 0),
            FOREIGN KEY (user_id) REFERENCES customers(user_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES customers(user_id)
        );

        CREATE TABLE IF NOT EXISTS order_details (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            payment_type TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK (amount >= 0),
            transaction_date TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );

        CREATE TABLE IF NOT EXISTS consultations (
            consultation_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            consultation_date TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
            message_count INTEGER NOT NULL CHECK (message_count >= 0),
            FOREIGN KEY (user_id) REFERENCES customers(user_id)
        );

        CREATE TABLE IF NOT EXISTS sales_calls (
            call_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            call_duration INTEGER NOT NULL CHECK (call_duration >= 0),
            is_purchased INTEGER NOT NULL CHECK (is_purchased IN (0, 1)),
            FOREIGN KEY (user_id) REFERENCES customers(user_id)
        );

        CREATE TABLE IF NOT EXISTS marketing_campaigns (
            campaign_id INTEGER PRIMARY KEY,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            budget INTEGER NOT NULL CHECK (budget >= 0),
            clicks INTEGER NOT NULL CHECK (clicks >= 0),
            conversions INTEGER NOT NULL CHECK (conversions >= 0)
        );

        CREATE INDEX IF NOT EXISTS idx_visits_user_id
            ON visits(user_id);

        CREATE INDEX IF NOT EXISTS idx_visits_start_time
            ON visits(start_time);

        CREATE INDEX IF NOT EXISTS idx_orders_user_id
            ON orders(user_id);

        CREATE INDEX IF NOT EXISTS idx_orders_order_date
            ON orders(order_date);

        CREATE INDEX IF NOT EXISTS idx_order_details_product_id
            ON order_details(product_id);

        CREATE INDEX IF NOT EXISTS idx_transactions_order_id
            ON transactions(order_id);

        CREATE INDEX IF NOT EXISTS idx_transactions_date
            ON transactions(transaction_date);

        CREATE INDEX IF NOT EXISTS idx_consultations_user_id
            ON consultations(user_id);

        CREATE INDEX IF NOT EXISTS idx_consultations_date
            ON consultations(consultation_date);

        CREATE INDEX IF NOT EXISTS idx_sales_calls_user_id
            ON sales_calls(user_id);

        CREATE INDEX IF NOT EXISTS idx_products_category_id
            ON products(category_id);
        """
    )
    connection.commit()


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize an empty SQLite database."""
    with closing(get_connection(db_path)) as connection:
        create_schema(connection)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")

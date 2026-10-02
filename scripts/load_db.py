"""Load the startup Excel workbook into SQLite."""

from argparse import ArgumentParser
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.db import DB_PATH, create_schema, get_connection  # noqa: E402


DEFAULT_EXCEL_PATH = PROJECT_ROOT / "data" / "startup_data.xlsx"

SHEETS = {
    "customers": "PAT-customers-table",
    "categories": "PAT-categories-table",
    "products": "PAT-products-table",
    "visits": "PAT-visits-table",
    "orders": "PAT-orders-table",
    "order_details": "PAT-orderdetails-table",
    "transactions": "PAT-transactions-table",
    "consultations": "PAT-consultation-table",
    "sales_calls": "PAT-Sales-table",
    "marketing_campaigns": "PAT-marketingcampaigns-table",
}

LOAD_ORDER = [
    "customers",
    "categories",
    "products",
    "visits",
    "orders",
    "order_details",
    "transactions",
    "consultations",
    "sales_calls",
    "marketing_campaigns",
]


def money_to_int(series: pd.Series) -> pd.Series:
    """Convert currency strings such as '$4,932,900' to integers."""
    cleaned = (
        series.astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="raise").astype("int64")


def to_datetime_iso(series: pd.Series) -> pd.Series:
    """Convert timestamps to SQLite-friendly ISO strings."""
    return pd.to_datetime(series, errors="raise").dt.strftime("%Y-%m-%d %H:%M:%S")


def to_date_iso(series: pd.Series) -> pd.Series:
    """Convert dates to YYYY-MM-DD."""
    return pd.to_datetime(series, errors="raise").dt.strftime("%Y-%m-%d")


def duration_to_seconds(series: pd.Series) -> pd.Series:
    """Convert consultation durations to whole seconds."""
    return (
        pd.to_timedelta(series.astype("string"), errors="raise")
        .dt.total_seconds()
        .astype("int64")
    )


def require_columns(
    df: pd.DataFrame,
    table_name: str,
    required_columns: list[str],
) -> None:
    """Validate that a source sheet contains all required columns."""
    missing = set(required_columns) - set(df.columns)

    if missing:
        raise ValueError(
            f"{table_name}: missing columns: {', '.join(sorted(missing))}"
        )


def prepare_table(table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Clean one worksheet and align it with the SQLite schema."""

    if table_name == "customers":
        columns = ["user_id", "name", "email", "signup_date"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        df["user_id"] = pd.to_numeric(df["user_id"], errors="raise").astype("int64")
        df["name"] = df["name"].astype("string").str.strip()
        df["email"] = df["email"].astype("string").str.strip()
        df["signup_date"] = to_date_iso(df["signup_date"])

    elif table_name == "categories":
        columns = ["category_id", "name"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        df["category_id"] = pd.to_numeric(
            df["category_id"], errors="raise"
        ).astype("int64")
        df["name"] = df["name"].astype("string").str.strip()

    elif table_name == "products":
        columns = ["product_id", "name", "category_id", "stock_quantity"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in ["product_id", "category_id", "stock_quantity"]:
            df[column] = pd.to_numeric(df[column], errors="raise").astype("int64")

        df["name"] = df["name"].astype("string").str.strip()

    elif table_name == "visits":
        columns = ["session_id", "user_id", "start_time", "end_time", "page_views"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in ["session_id", "user_id", "page_views"]:
            df[column] = pd.to_numeric(df[column], errors="raise").astype("int64")

        df["start_time"] = to_datetime_iso(df["start_time"])
        df["end_time"] = to_datetime_iso(df["end_time"])

    elif table_name == "orders":
        columns = ["order_id", "user_id", "order_date", "status"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        df["order_id"] = pd.to_numeric(df["order_id"], errors="raise").astype("int64")
        df["user_id"] = pd.to_numeric(df["user_id"], errors="raise").astype("int64")
        df["order_date"] = to_datetime_iso(df["order_date"])
        df["status"] = df["status"].astype("string").str.strip()

    elif table_name == "order_details":
        columns = ["order_id", "product_id", "quantity"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in columns:
            df[column] = pd.to_numeric(df[column], errors="raise").astype("int64")

    elif table_name == "transactions":
        columns = [
            "transaction_id",
            "order_id",
            "payment_type",
            "amount",
            "transaction_date",
        ]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        df["transaction_id"] = pd.to_numeric(
            df["transaction_id"], errors="raise"
        ).astype("int64")
        df["order_id"] = pd.to_numeric(df["order_id"], errors="raise").astype("int64")
        df["payment_type"] = df["payment_type"].astype("string").str.strip()
        df["amount"] = money_to_int(df["amount"])
        df["transaction_date"] = to_datetime_iso(df["transaction_date"])

    elif table_name == "consultations":
        source_columns = [
            "id",
            "user_id",
            "consultation_date",
            "consultation_duration",
            "consultaion_msg_count",
        ]
        require_columns(df, table_name, source_columns)
        df = df[source_columns].copy()

        df = df.rename(
            columns={
                "id": "consultation_id",
                "consultation_duration": "duration_seconds",
                "consultaion_msg_count": "message_count",
            }
        )

        df["consultation_id"] = pd.to_numeric(
            df["consultation_id"], errors="raise"
        ).astype("int64")
        df["user_id"] = pd.to_numeric(df["user_id"], errors="raise").astype("int64")
        df["consultation_date"] = to_datetime_iso(df["consultation_date"])
        df["duration_seconds"] = duration_to_seconds(df["duration_seconds"])
        df["message_count"] = pd.to_numeric(
            df["message_count"], errors="raise"
        ).astype("int64")

    elif table_name == "sales_calls":
        columns = ["call_id", "user_id", "call_duration", "is_purchased"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in columns:
            df[column] = pd.to_numeric(df[column], errors="raise").astype("int64")

    elif table_name == "marketing_campaigns":
        columns = [
            "campaign_id",
            "start_date",
            "end_date",
            "budget",
            "clicks",
            "conversions",
        ]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        df["campaign_id"] = pd.to_numeric(
            df["campaign_id"], errors="raise"
        ).astype("int64")
        df["start_date"] = to_date_iso(df["start_date"])
        df["end_date"] = to_date_iso(df["end_date"])
        df["budget"] = money_to_int(df["budget"])
        df["clicks"] = pd.to_numeric(df["clicks"], errors="raise").astype("int64")
        df["conversions"] = pd.to_numeric(
            df["conversions"], errors="raise"
        ).astype("int64")

    else:
        raise ValueError(f"Unsupported table: {table_name}")

    if df.isna().any().any():
        null_columns = df.columns[df.isna().any()].tolist()
        raise ValueError(
            f"{table_name}: null values found in columns: "
            f"{', '.join(null_columns)}"
        )

    return df


def read_workbook(excel_path: Path) -> dict[str, pd.DataFrame]:
    """Read and clean all expected worksheets."""
    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    workbook = pd.ExcelFile(excel_path)

    missing_sheets = set(SHEETS.values()) - set(workbook.sheet_names)
    if missing_sheets:
        raise ValueError(
            "Missing worksheets: " + ", ".join(sorted(missing_sheets))
        )

    tables = {}

    for table_name, sheet_name in SHEETS.items():
        raw_df = pd.read_excel(workbook, sheet_name=sheet_name)
        tables[table_name] = prepare_table(table_name, raw_df)

    return tables


def reset_database(connection) -> None:
    """Delete existing rows while respecting foreign-key relationships."""
    connection.execute("PRAGMA foreign_keys = OFF;")

    for table_name in reversed(LOAD_ORDER):
        connection.execute(f"DELETE FROM {table_name};")

    connection.execute("PRAGMA foreign_keys = ON;")


def load_database(
    excel_path: Path = DEFAULT_EXCEL_PATH,
    db_path: Path = DB_PATH,
    reset: bool = False,
) -> dict[str, int]:
    """Load all Excel worksheets into SQLite."""
    tables = read_workbook(excel_path)

    with get_connection(db_path) as connection:
        create_schema(connection)

        if reset:
            reset_database(connection)

        for table_name in LOAD_ORDER:
            tables[table_name].to_sql(
                table_name,
                connection,
                if_exists="append",
                index=False,
                method="multi",
            )

        connection.commit()

    return {
        table_name: len(tables[table_name])
        for table_name in LOAD_ORDER
    }


def parse_args():
    parser = ArgumentParser(
        description="Load startup Excel data into SQLite."
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=DEFAULT_EXCEL_PATH,
        help="Path to the source Excel workbook.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="Path to the SQLite database.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing database rows before loading.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    row_counts = load_database(
        excel_path=args.excel,
        db_path=args.db,
        reset=args.reset,
    )

    print(f"Database loaded successfully: {args.db}")
    print(f"Source workbook: {args.excel}")
    print()

    for table_name, count in row_counts.items():
        print(f"{table_name:<22} {count:>6,} rows")

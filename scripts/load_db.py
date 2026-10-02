"""Load the startup Excel workbook into SQLite."""

from argparse import ArgumentParser
from contextlib import closing
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


def to_integer(series: pd.Series) -> pd.Series:
    """Reject missing or fractional values instead of silently truncating them."""
    numeric = pd.to_numeric(series, errors="raise")
    if numeric.isna().any() or (numeric % 1 != 0).any():
        raise ValueError(f"{series.name}: expected non-null whole numbers")
    return numeric.astype("int64")


def money_to_int(series: pd.Series) -> pd.Series:
    """Convert currency strings such as '$4,932,900' to integers."""
    cleaned = (
        series.astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return to_integer(cleaned)


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

        df["user_id"] = to_integer(df["user_id"])
        df["name"] = df["name"].astype("string").str.strip()
        df["email"] = df["email"].astype("string").str.strip()
        df["signup_date"] = to_date_iso(df["signup_date"])

    elif table_name == "categories":
        columns = ["category_id", "name"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        df["category_id"] = to_integer(df["category_id"])
        df["name"] = df["name"].astype("string").str.strip()

    elif table_name == "products":
        columns = ["product_id", "name", "category_id", "stock_quantity"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in ["product_id", "category_id", "stock_quantity"]:
            df[column] = to_integer(df[column])

        df["name"] = df["name"].astype("string").str.strip()

    elif table_name == "visits":
        columns = ["session_id", "user_id", "start_time", "end_time", "page_views"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in ["session_id", "user_id", "page_views"]:
            df[column] = to_integer(df[column])

        df["start_time"] = to_datetime_iso(df["start_time"])
        df["end_time"] = to_datetime_iso(df["end_time"])

    elif table_name == "orders":
        columns = ["order_id", "user_id", "order_date", "status"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        df["order_id"] = to_integer(df["order_id"])
        df["user_id"] = to_integer(df["user_id"])
        df["order_date"] = to_datetime_iso(df["order_date"])
        df["status"] = df["status"].astype("string").str.strip()

    elif table_name == "order_details":
        columns = ["order_id", "product_id", "quantity"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in columns:
            df[column] = to_integer(df[column])

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

        df["transaction_id"] = to_integer(df["transaction_id"])
        df["order_id"] = to_integer(df["order_id"])
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

        df["consultation_id"] = to_integer(df["consultation_id"])
        df["user_id"] = to_integer(df["user_id"])
        df["consultation_date"] = to_datetime_iso(df["consultation_date"])
        df["duration_seconds"] = duration_to_seconds(df["duration_seconds"])
        df["message_count"] = to_integer(df["message_count"])

    elif table_name == "sales_calls":
        columns = ["call_id", "user_id", "call_duration", "is_purchased"]
        require_columns(df, table_name, columns)
        df = df[columns].copy()

        for column in columns:
            df[column] = to_integer(df[column])

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

        df["campaign_id"] = to_integer(df["campaign_id"])
        df["start_date"] = to_date_iso(df["start_date"])
        df["end_date"] = to_date_iso(df["end_date"])
        df["budget"] = money_to_int(df["budget"])
        df["clicks"] = to_integer(df["clicks"])
        df["conversions"] = to_integer(df["conversions"])

    else:
        raise ValueError(f"Unsupported table: {table_name}")

    if df.isna().any().any():
        null_columns = df.columns[df.isna().any()].tolist()
        raise ValueError(
            f"{table_name}: null values found in columns: "
            f"{', '.join(null_columns)}"
        )

    text_columns = df.select_dtypes(include="string").columns
    for column in text_columns:
        if df[column].str.strip().eq("").any():
            raise ValueError(f"{table_name}: empty values in {column}")

    for start, end in [("start_time", "end_time"), ("start_date", "end_date")]:
        if start in df and end in df and (df[end] < df[start]).any():
            raise ValueError(f"{table_name}: {end} precedes {start}")

    return df


def read_workbook(excel_path: Path) -> dict[str, pd.DataFrame]:
    """Read and clean all expected worksheets."""
    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    with pd.ExcelFile(excel_path) as workbook:

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
    for table_name in reversed(LOAD_ORDER):
        connection.execute(f"DELETE FROM {table_name};")


def load_database(
    excel_path: Path = DEFAULT_EXCEL_PATH,
    db_path: Path = DB_PATH,
    reset: bool = False,
) -> dict[str, int]:
    """Load all Excel worksheets into SQLite."""
    tables = read_workbook(excel_path)

    with closing(get_connection(db_path)) as connection:
        create_schema(connection)

        # One transaction covers deletion and every insert. pandas.to_sql with a
        # raw SQLite connection commits each table, so use executemany instead.
        with connection:
            if reset:
                reset_database(connection)

            for table_name in LOAD_ORDER:
                table = tables[table_name]
                columns = ', '.join(f'"{column}"' for column in table.columns)
                placeholders = ', '.join('?' for _ in table.columns)
                connection.executemany(
                    f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})',
                    table.itertuples(index=False, name=None),
                )

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

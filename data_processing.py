"""
data_processing.py
-------------------
Handles all data ingestion and cleaning logic for the AI-Powered Excel
Automation System for Supply Chain Operations.

Responsibilities:
    1. Load raw Excel data (Orders + Inventory sheets)
    2. Clean and standardize messy real-world data
    3. Track data-quality metrics (used later for the Research Insights Panel)

Designed to be readable and explainable for an academic paper: every
cleaning step is isolated into its own function with a docstring describing
the rationale, so the methodology section of a paper can reference this
file directly.
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Canonical set of order statuses the system understands.
# Messy input data (typos, case differences, abbreviations) gets mapped
# onto this canonical set in standardize_status().
VALID_STATUSES = ["Pending", "Processing", "Shipped", "Completed"]

STATUS_ALIASES = {
    "pending": "Pending",
    "pend": "Pending",
    "processing": "Processing",
    "proc": "Processing",
    "in process": "Processing",
    "in progress": "Processing",
    "shipped": "Shipped",
    "ship": "Shipped",
    "dispatched": "Shipped",
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
    "delivered": "Completed",
}

REQUIRED_ORDER_COLUMNS = [
    "Order ID", "Date", "Item", "Quantity",
    "Status", "Customer", "Region", "Revenue",
]


def load_excel(file) -> dict:
    """
    Load an uploaded Excel file and return a dict of DataFrames.

    The expected workbook has two sheets:
        - "Orders": transactional order data
        - "Inventory": current stock levels per item (optional; if missing,
          a synthetic inventory table is derived from order history)

    Returns
    -------
    dict: {"orders": DataFrame, "inventory": DataFrame or None}
    """
    sheets = pd.read_excel(file, sheet_name=None)  # read all sheets

    # Find the orders sheet (first sheet, or one literally named "Orders")
    orders_df = None
    inventory_df = None

    for name, df in sheets.items():
        lname = name.strip().lower()
        if "inventory" in lname or "stock" in lname:
            inventory_df = df
        elif "order" in lname or orders_df is None:
            orders_df = df

    if orders_df is None:
        # Fallback: first sheet in the workbook
        orders_df = list(sheets.values())[0]

    return {"orders": orders_df, "inventory": inventory_df}


def clean_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean a raw Orders DataFrame.

    Cleaning steps (in order):
        1. Strip whitespace from column names and text fields
        2. Drop fully empty rows
        3. Standardize the Status column against VALID_STATUSES
        4. Coerce Quantity / Revenue to numeric, fill missing with 0
        5. Parse Date column into datetime
        6. Remove exact duplicate rows
        7. Drop rows missing a critical field (Order ID or Item)

    Returns
    -------
    (cleaned_df, report)
        report: dict of data-quality metrics used by the
        Research Insights Panel (rows fixed, duplicates removed, etc.)
    """
    report = {
        "rows_before": len(df),
        "missing_values_filled": 0,
        "duplicates_removed": 0,
        "status_values_standardized": 0,
        "rows_dropped_critical": 0,
    }

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Ensure all expected columns exist (create empty ones if missing,
    # so downstream code never KeyErrors on a malformed upload)
    for col in REQUIRED_ORDER_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    # 1. Strip whitespace on text columns
    text_cols = ["Order ID", "Item", "Status", "Customer", "Region"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})

    # 2. Drop fully empty rows
    df = df.dropna(how="all")

    # 3. Standardize Status values using alias map
    before_null_status = df["Status"].isna().sum()

    def _map_status(val):
        if pd.isna(val):
            return "Pending"  # assume unspecified orders are new/pending
        key = str(val).strip().lower()
        return STATUS_ALIASES.get(key, val.strip().title() if isinstance(val, str) else val)

    original_status = df["Status"].copy()
    df["Status"] = df["Status"].apply(_map_status)
    # Anything still not in the valid set gets bucketed as "Pending"
    df.loc[~df["Status"].isin(VALID_STATUSES), "Status"] = "Pending"
    report["status_values_standardized"] = int((original_status != df["Status"]).sum())

    # 4. Numeric coercion
    missing_before = df[["Quantity", "Revenue"]].isna().sum().sum()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0)
    missing_after_fill = missing_before  # all coerced NaNs were filled with 0
    report["missing_values_filled"] += int(missing_after_fill)

    # Fill remaining missing categorical fields with explicit placeholders
    for col in ["Customer", "Region", "Item"]:
        n_missing = df[col].isna().sum()
        if n_missing:
            df[col] = df[col].fillna("Unknown")
            report["missing_values_filled"] += int(n_missing)

    # 5. Parse dates
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # 6. Remove duplicates
    n_before_dedup = len(df)
    df = df.drop_duplicates(subset=["Order ID", "Item", "Date", "Customer"], keep="first")
    df = df.drop_duplicates()  # catch any fully identical repeated rows too
    report["duplicates_removed"] = n_before_dedup - len(df)

    # 7. Drop rows missing a critical identifier
    n_before_critical = len(df)
    df = df.dropna(subset=["Order ID", "Item"])
    report["rows_dropped_critical"] = n_before_critical - len(df)

    df = df.reset_index(drop=True)
    report["rows_after"] = len(df)

    return df, report


def build_synthetic_inventory(orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    If no Inventory sheet is provided, derive a working inventory table
    from historical order data so the Inventory Management module still
    functions. This is clearly labeled as *simulated* in the UI so it
    remains academically transparent (not presented as real stock data).

    Logic:
        current_stock  = 2x average order quantity per item (simulated buffer)
        reorder_level  = average daily demand x assumed 7-day lead time
    """
    item_stats = orders_df.groupby("Item").agg(
        avg_order_qty=("Quantity", "mean"),
        total_qty=("Quantity", "sum"),
        n_orders=("Order ID", "count"),
    ).reset_index()

    # Estimate the span of the dataset in days to compute daily demand
    date_span_days = 1
    if orders_df["Date"].notna().any():
        span = (orders_df["Date"].max() - orders_df["Date"].min()).days
        date_span_days = max(span, 1)

    item_stats["avg_daily_demand"] = item_stats["total_qty"] / date_span_days
    item_stats["Current Stock"] = (item_stats["avg_order_qty"] * 2).round().astype(int)
    item_stats["Reorder Level"] = (item_stats["avg_daily_demand"] * 7).round().astype(int).clip(lower=1)

    inventory_df = item_stats[["Item", "Current Stock", "Reorder Level"]].rename(
        columns={"Item": "Item"}
    )
    return inventory_df


def clean_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """Light cleaning pass for a user-provided Inventory sheet."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "Item" in df.columns:
        df["Item"] = df["Item"].astype(str).str.strip()
    for col in df.columns:
        if col != "Item":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df.drop_duplicates(subset=["Item"], keep="first").reset_index(drop=True)
    return df

"""
analytics.py
------------
AI Insight Panel + Dashboard metric logic for the AI-Powered Excel
Automation System for Supply Chain Operations.

"AI" here is intentionally implemented as transparent, explainable
rule-based logic and lightweight statistics rather than a black-box model.
This is a deliberate design choice for the academic use case: every number
shown to the user can be traced back to a simple, reproducible formula,
which is important when writing a methodology section for a research paper.

Where scikit-learn is used (simple linear trend for demand forecasting),
it is clearly separated into its own function and documented.
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# 1. DASHBOARD METRICS
# ---------------------------------------------------------------------------

def get_dashboard_metrics(orders_df: pd.DataFrame) -> dict:
    """Compute top-line KPIs shown on the Dashboard tab."""
    total_orders = orders_df["Order ID"].nunique()
    total_revenue = orders_df["Revenue"].sum()
    total_quantity = orders_df["Quantity"].sum()
    pending_orders = (orders_df["Status"] == "Pending").sum()

    status_breakdown = orders_df["Status"].value_counts().to_dict()

    return {
        "total_orders": int(total_orders),
        "total_revenue": float(total_revenue),
        "total_quantity": float(total_quantity),
        "pending_orders": int(pending_orders),
        "status_breakdown": status_breakdown,
    }


# ---------------------------------------------------------------------------
# 2. INVENTORY MANAGEMENT
# ---------------------------------------------------------------------------

def get_low_stock_items(inventory_df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag items where Current Stock has fallen to or below the Reorder Level.

    Suggested reorder quantity uses a simple, explainable heuristic:
        reorder_qty = (Reorder Level * 2) - Current Stock
    i.e. restock enough to reach double the reorder threshold (a basic
    safety-stock buffer), clipped to be non-negative.
    """
    df = inventory_df.copy()
    df["Low Stock"] = df["Current Stock"] <= df["Reorder Level"]
    df["Suggested Reorder Qty"] = (
        (df["Reorder Level"] * 2) - df["Current Stock"]
    ).clip(lower=0).astype(int)

    low_stock_df = df[df["Low Stock"]].sort_values("Current Stock")
    return low_stock_df[["Item", "Current Stock", "Reorder Level", "Suggested Reorder Qty"]]


# ---------------------------------------------------------------------------
# 3. AI INSIGHTS
# ---------------------------------------------------------------------------

def top_selling_items(orders_df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Rank items by total quantity sold (a simple demand-ranking heuristic)."""
    grouped = (
        orders_df.groupby("Item")
        .agg(Total_Quantity=("Quantity", "sum"), Total_Revenue=("Revenue", "sum"), Orders=("Order ID", "count"))
        .reset_index()
        .sort_values("Total_Quantity", ascending=False)
    )
    return grouped.head(n)


def top_customers(orders_df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Rank customers by number of orders placed and total spend."""
    grouped = (
        orders_df.groupby("Customer")
        .agg(Total_Orders=("Order ID", "count"), Total_Spend=("Revenue", "sum"))
        .reset_index()
        .sort_values("Total_Orders", ascending=False)
    )
    return grouped.head(n)


def stock_risk_alerts(orders_df: pd.DataFrame, inventory_df: pd.DataFrame, lead_time_days: int = 7) -> pd.DataFrame:
    """
    Rule-based stock shortage prediction.

    For each item:
        avg_daily_demand = total historical quantity sold / dataset span (days)
        projected_need    = avg_daily_demand * lead_time_days
        risk = "High" if Current Stock < projected_need
             = "Medium" if Current Stock < projected_need * 1.5
             = "Low" otherwise

    This is a transparent proxy for a reorder-point / safety-stock model
    commonly used in inventory theory, making it easy to cite and explain
    in a research paper's methodology section.
    """
    date_span_days = 1
    if orders_df["Date"].notna().any():
        span = (orders_df["Date"].max() - orders_df["Date"].min()).days
        date_span_days = max(span, 1)

    demand = orders_df.groupby("Item")["Quantity"].sum().reset_index()
    demand["avg_daily_demand"] = demand["Quantity"] / date_span_days

    merged = inventory_df.merge(demand[["Item", "avg_daily_demand"]], on="Item", how="left")
    merged["avg_daily_demand"] = merged["avg_daily_demand"].fillna(0)
    merged["Projected Need"] = (merged["avg_daily_demand"] * lead_time_days).round(1)

    def _risk(row):
        if row["Current Stock"] < row["Projected Need"]:
            return "High"
        elif row["Current Stock"] < row["Projected Need"] * 1.5:
            return "Medium"
        return "Low"

    merged["Risk Level"] = merged.apply(_risk, axis=1)
    merged = merged.sort_values(
        by="Risk Level", key=lambda s: s.map({"High": 0, "Medium": 1, "Low": 2})
    )
    return merged[["Item", "Current Stock", "Projected Need", "Risk Level"]]


def demand_forecast_trend(orders_df: pd.DataFrame, item: str) -> dict:
    """
    Optional lightweight ML component: fits a simple linear regression
    (scikit-learn) of quantity sold over time for a single item, to
    illustrate a basic forecasting extension beyond rule-based logic.

    Returns slope (units/day trend) and a qualitative label.
    Falls back gracefully if scikit-learn isn't installed or there isn't
    enough data.
    """
    item_df = orders_df[orders_df["Item"] == item].dropna(subset=["Date"]).sort_values("Date")
    if len(item_df) < 3:
        return {"available": False, "reason": "Not enough historical data points."}

    try:
        from sklearn.linear_model import LinearRegression
    except ImportError:
        return {"available": False, "reason": "scikit-learn not installed."}

    x = (item_df["Date"] - item_df["Date"].min()).dt.days.values.reshape(-1, 1)
    y = item_df["Quantity"].values

    model = LinearRegression().fit(x, y)
    slope = float(model.coef_[0])

    if slope > 0.1:
        trend = "Increasing demand"
    elif slope < -0.1:
        trend = "Decreasing demand"
    else:
        trend = "Stable demand"

    return {"available": True, "slope": round(slope, 3), "trend": trend}


# ---------------------------------------------------------------------------
# 4. RESEARCH INSIGHTS PANEL
# ---------------------------------------------------------------------------

def research_insights(raw_row_count: int, cleaning_report: dict, orders_df: pd.DataFrame) -> dict:
    """
    Produce a Before vs After automation comparison for the Research
    Insights Panel. Time and error estimates are based on commonly cited
    manual-data-entry benchmarks and are clearly labeled as *estimates*
    for academic transparency, not measured lab results.

    Manual baseline assumptions (documented, adjustable):
        - ~1.5 minutes per row for manual review/cleaning/categorization
        - ~2% human error rate on manual categorical entry (status field)
        - Automated processing: near-instant, deterministic rule application
    """
    MINUTES_PER_ROW_MANUAL = 1.5
    ASSUMED_MANUAL_ERROR_RATE = 0.02  # 2%, based on typical manual data-entry error benchmarks

    manual_time_minutes = raw_row_count * MINUTES_PER_ROW_MANUAL
    automated_time_seconds = max(raw_row_count * 0.01, 0.5)  # near-instant automated processing
    automated_time_minutes = automated_time_seconds / 60

    time_saved_minutes = manual_time_minutes - automated_time_minutes
    time_saved_pct = (time_saved_minutes / manual_time_minutes * 100) if manual_time_minutes > 0 else 0

    # Errors "caught" by automation = actual corrections made during cleaning
    errors_corrected = (
        cleaning_report.get("missing_values_filled", 0)
        + cleaning_report.get("duplicates_removed", 0)
        + cleaning_report.get("status_values_standardized", 0)
    )
    estimated_manual_errors = round(raw_row_count * ASSUMED_MANUAL_ERROR_RATE)
    error_reduction_pct = (
        (errors_corrected / max(estimated_manual_errors, 1)) * 100
        if estimated_manual_errors > 0 else 0
    )
    error_reduction_pct = min(error_reduction_pct, 100)

    efficiency_improvement_pct = time_saved_pct  # time-based efficiency proxy

    return {
        "rows_processed": raw_row_count,
        "manual_time_minutes": round(manual_time_minutes, 1),
        "automated_time_seconds": round(automated_time_seconds, 2),
        "time_saved_minutes": round(time_saved_minutes, 1),
        "time_saved_pct": round(time_saved_pct, 1),
        "estimated_manual_errors": estimated_manual_errors,
        "errors_corrected_by_system": errors_corrected,
        "error_reduction_pct": round(error_reduction_pct, 1),
        "efficiency_improvement_pct": round(efficiency_improvement_pct, 1),
        "assumptions": {
            "minutes_per_row_manual": MINUTES_PER_ROW_MANUAL,
            "assumed_manual_error_rate": ASSUMED_MANUAL_ERROR_RATE,
        },
    }

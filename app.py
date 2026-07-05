"""
app.py
------
AI-Powered Excel Automation System for Supply Chain Operations
Main Streamlit application entry point.

Run with:
    streamlit run app.py

Structure:
    - Sidebar: file upload + navigation
    - Tab 1: Dashboard
    - Tab 2: Data Upload & Preview
    - Tab 3: Processing Engine (cleaning report)
    - Tab 4: AI Insight Panel
    - Tab 5: Research Insights Panel (for academic paper use)
"""

import io
import streamlit as st
import pandas as pd
import plotly.express as px

import data_processing as dp
import analytics as an

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Supply Chain Automation",
    page_icon="📦",
    layout="wide",
)

st.title("📦 AI-Powered Excel Automation System for Supply Chain Operations")
st.caption(
    "A research prototype demonstrating rule-based AI automation of inventory "
    "and order management workflows using Excel data."
)

# ---------------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------------
for key in ["raw_orders", "orders_df", "inventory_df", "cleaning_report", "inventory_is_synthetic"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------------------------------------------------------
# SIDEBAR — FILE UPLOAD
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📁 Data Upload")
    uploaded_file = st.file_uploader(
        "Upload an Excel file (.xlsx)",
        type=["xlsx"],
        help="Expected columns: Order ID, Date, Item, Quantity, Status, Customer, Region, Revenue. "
             "An optional 'Inventory' sheet with Item / Current Stock / Reorder Level is also supported.",
    )

    st.markdown("---")
    st.markdown(
        "**Don't have a file?** Use the sample dataset provided with this "
        "project (`sample_supply_chain_data.xlsx`) to try the system."
    )

    if uploaded_file is not None:
        try:
            sheets = dp.load_excel(uploaded_file)
            raw_orders = sheets["orders"]
            st.session_state.raw_orders = raw_orders

            cleaned_orders, report = dp.clean_orders(raw_orders)
            st.session_state.orders_df = cleaned_orders
            st.session_state.cleaning_report = report

            if sheets["inventory"] is not None:
                st.session_state.inventory_df = dp.clean_inventory(sheets["inventory"])
                st.session_state.inventory_is_synthetic = False
            else:
                st.session_state.inventory_df = dp.build_synthetic_inventory(cleaned_orders)
                st.session_state.inventory_is_synthetic = True

            st.success(f"Loaded {len(raw_orders)} raw rows successfully.")
        except Exception as e:
            st.error(f"Failed to process file: {e}")

# Guard: nothing loaded yet
if st.session_state.orders_df is None:
    st.info("👈 Upload an Excel file from the sidebar to begin.")
    st.stop()

orders_df = st.session_state.orders_df
inventory_df = st.session_state.inventory_df
report = st.session_state.cleaning_report

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_dash, tab_upload, tab_process, tab_ai, tab_research = st.tabs(
    ["📊 Dashboard", "📥 Data Upload", "⚙️ Processing Engine", "🧠 AI Insights", "📈 Research Insights"]
)

# ---------------------------------------------------------------------------
# TAB 1: DASHBOARD
# ---------------------------------------------------------------------------
with tab_dash:
    metrics = an.get_dashboard_metrics(orders_df)
    low_stock_df = an.get_low_stock_items(inventory_df)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders", metrics["total_orders"])
    c2.metric("Total Revenue", f"${metrics['total_revenue']:,.2f}")
    c3.metric("Total Quantity Sold", f"{metrics['total_quantity']:,.0f}")
    c4.metric("Pending Orders", metrics["pending_orders"])
    c5.metric("Low Stock Alerts", len(low_stock_df))

    st.markdown("### Order Status Breakdown")
    status_df = pd.DataFrame(
        list(metrics["status_breakdown"].items()), columns=["Status", "Count"]
    )
    fig = px.pie(status_df, names="Status", values="Count", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### ⚠️ Low Stock Alerts")
    if st.session_state.inventory_is_synthetic:
        st.caption(
            "No Inventory sheet was found in the uploaded file — stock levels shown "
            "below are *simulated* from order history for demonstration purposes."
        )
    if low_stock_df.empty:
        st.success("No items are currently below their reorder level.")
    else:
        st.dataframe(low_stock_df, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 2: DATA UPLOAD & PREVIEW
# ---------------------------------------------------------------------------
with tab_upload:
    st.markdown("### Raw Data Preview (Before Cleaning)")
    st.dataframe(st.session_state.raw_orders.head(20), use_container_width=True)

    st.markdown("### Cleaned Data Preview (After Processing)")
    st.dataframe(orders_df.head(20), use_container_width=True)

    st.markdown("### Inventory Table")
    st.dataframe(inventory_df, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 3: PROCESSING ENGINE
# ---------------------------------------------------------------------------
with tab_process:
    st.markdown("### Data Cleaning Report")
    st.write(
        "The Processing Engine automatically cleans uploaded data using the "
        "following deterministic rules:"
    )
    st.markdown(
        """
        - **Missing values**: numeric fields filled with `0`; categorical fields filled with `"Unknown"`
        - **Status standardization**: text variants (e.g. "ship", "done", "in progress") mapped to
          canonical values: `Pending`, `Processing`, `Shipped`, `Completed`
        - **Duplicate removal**: exact and near-duplicate rows (same Order ID, Item, Date, Customer) removed
        - **Critical field validation**: rows missing an Order ID or Item are dropped
        """
    )

    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Rows Before", report["rows_before"])
    rc2.metric("Rows After", report["rows_after"])
    rc3.metric("Duplicates Removed", report["duplicates_removed"])
    rc4.metric("Values Standardized/Filled", report["missing_values_filled"] + report["status_values_standardized"])

    st.markdown("### Download Cleaned Excel File")
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
        orders_df.to_excel(writer, sheet_name="Cleaned Orders", index=False)
        inventory_df.to_excel(writer, sheet_name="Inventory", index=False)
    st.download_button(
        label="⬇️ Download Cleaned Excel Output",
        data=output_buffer.getvalue(),
        file_name="cleaned_supply_chain_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ---------------------------------------------------------------------------
# TAB 4: AI INSIGHTS
# ---------------------------------------------------------------------------
with tab_ai:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏆 Top 5 Selling Items")
        top_items = an.top_selling_items(orders_df, n=5)
        st.dataframe(top_items, use_container_width=True)
        fig_items = px.bar(top_items, x="Item", y="Total_Quantity", title="Top Items by Quantity Sold")
        st.plotly_chart(fig_items, use_container_width=True)

    with col2:
        st.markdown("### 👥 Top 5 Frequent Customers")
        top_cust = an.top_customers(orders_df, n=5)
        st.dataframe(top_cust, use_container_width=True)
        fig_cust = px.bar(top_cust, x="Customer", y="Total_Orders", title="Top Customers by Order Count")
        st.plotly_chart(fig_cust, use_container_width=True)

    st.markdown("### 🚨 Stock Risk Alerts (Rule-Based Prediction)")
    st.caption(
        "Risk level compares current stock against projected demand over a 7-day "
        "lead time, estimated from historical average daily sales per item."
    )
    risk_df = an.stock_risk_alerts(orders_df, inventory_df)

    def _highlight_risk(val):
        color = {"High": "#ffcccc", "Medium": "#fff3cd", "Low": "#d4edda"}.get(val, "")
        return f"background-color: {color}"

    st.dataframe(risk_df.style.applymap(_highlight_risk, subset=["Risk Level"]), use_container_width=True)

    st.markdown("### 📉 Optional: Demand Trend Forecast (scikit-learn)")
    item_choice = st.selectbox("Select an item to forecast", sorted(orders_df["Item"].unique()))
    trend = an.demand_forecast_trend(orders_df, item_choice)
    if trend["available"]:
        st.write(f"**Trend for {item_choice}:** {trend['trend']} (slope = {trend['slope']} units/day)")
    else:
        st.info(trend["reason"])

# ---------------------------------------------------------------------------
# TAB 5: RESEARCH INSIGHTS PANEL
# ---------------------------------------------------------------------------
with tab_research:
    st.markdown("### 📈 Research Insights Panel")
    st.caption(
        "Quantitative comparison of manual vs. AI-automated processing, intended "
        "for use in an academic paper's results/discussion section. All manual "
        "baseline figures are clearly stated assumptions, not measured values."
    )

    ri = an.research_insights(report["rows_before"], report, orders_df)

    rcol1, rcol2, rcol3, rcol4 = st.columns(4)
    rcol1.metric("Time Saved", f"{ri['time_saved_minutes']} min", f"{ri['time_saved_pct']}%")
    rcol2.metric("Error Reduction", f"{ri['error_reduction_pct']}%")
    rcol3.metric("Efficiency Improvement", f"{ri['efficiency_improvement_pct']}%")
    rcol4.metric("Rows Processed", ri["rows_processed"])

    st.markdown("#### Before vs After Automation")
    comparison_df = pd.DataFrame({
        "Metric": ["Processing Time", "Estimated Errors"],
        "Manual (Before)": [f"{ri['manual_time_minutes']} min", ri["estimated_manual_errors"]],
        "Automated (After)": [f"{ri['automated_time_seconds']} sec", ri["errors_corrected_by_system"]],
    })
    st.table(comparison_df)

    fig_compare = px.bar(
        pd.DataFrame({
            "Stage": ["Manual (Before)", "Automated (After)"],
            "Time (minutes)": [ri["manual_time_minutes"], ri["automated_time_seconds"] / 60],
        }),
        x="Stage", y="Time (minutes)", title="Processing Time: Manual vs Automated",
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    with st.expander("📋 Methodology & Assumptions (for citation in your paper)"):
        st.markdown(
            f"""
            - **Manual processing baseline**: {ri['assumptions']['minutes_per_row_manual']} minutes per row,
              reflecting typical manual data entry/review time for structured order records.
            - **Assumed manual error rate**: {ri['assumptions']['assumed_manual_error_rate']*100:.0f}% of rows,
              based on commonly cited manual data-entry error benchmarks.
            - **Automated processing time**: measured directly from this system's execution
              (rule-based cleaning + aggregation over the uploaded dataset).
            - **Errors corrected**: sum of missing values filled, duplicate rows removed, and
              status values standardized during the Processing Engine stage.
            - These figures are estimates intended to illustrate *relative* efficiency gains,
              not clinically validated productivity measurements. State this limitation explicitly
              in any published paper.
            """
        )

st.markdown("---")
st.caption("AI-Powered Excel Automation System for Supply Chain Operations — Academic Research Prototype")

# AI-Powered Excel Automation System for Supply Chain Operations

A research-prototype web application that automates inventory tracking, order
processing, and rule-based AI insight generation from Excel supply chain data.
Built with Python, Streamlit, Pandas, OpenPyXL, and scikit-learn.

---

## 1. System Architecture

```
supply_chain_ai/
├── app.py                       # Streamlit UI — the entry point
├── data_processing.py           # Excel ingestion + cleaning logic
├── analytics.py                 # Dashboard metrics, AI insights, research panel
├── generate_sample_data.py      # Script that produced the sample dataset
├── sample_supply_chain_data.xlsx# Sample messy input file (Orders + Inventory sheets)
├── requirements.txt
└── README.md
```

**Data flow:**

```
Excel Upload (.xlsx)
      │
      ▼
data_processing.load_excel()      → splits into Orders / Inventory sheets
      │
      ▼
data_processing.clean_orders()    → missing values, status standardization,
                                     dedup, critical-field validation
      │
      ▼
analytics.py                      → dashboard metrics, top items/customers,
                                     rule-based stock risk, optional ML trend
      │
      ▼
Streamlit UI (app.py)             → Dashboard / Upload / Processing / AI / Research tabs
      │
      ▼
Excel Export (openpyxl)           → cleaned_supply_chain_data.xlsx
```

**Design principle for the paper:** every "AI" output is either (a) a
deterministic rule (e.g. status standardization, low-stock thresholding,
reorder-point risk classification) or (b) a simple, interpretable model
(linear regression demand trend via scikit-learn). This keeps every number
traceable to a formula you can cite in a methodology section — no black-box
components.

---

## 2. Setup Instructions

### Prerequisites
- Python 3.9+

### Steps

```bash
# 1. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

### Using the app
1. In the sidebar, upload an `.xlsx` file (use `sample_supply_chain_data.xlsx`
   to try it immediately).
2. Expected columns on the **Orders** sheet: `Order ID, Date, Item, Quantity,
   Status, Customer, Region, Revenue`.
3. An optional **Inventory** sheet with `Item, Current Stock, Reorder Level`
   enables real inventory tracking. If omitted, the system simulates
   inventory from order history (clearly labeled in the UI).
4. Explore the five tabs: Dashboard, Data Upload, Processing Engine, AI
   Insights, and Research Insights.
5. Download the cleaned Excel output from the Processing Engine tab.

### Regenerating the sample dataset (optional)
```bash
python generate_sample_data.py
```

---

## 3. Sample Excel Dataset

`sample_supply_chain_data.xlsx` is included with:
- **Orders sheet**: 270 rows with intentionally messy data — inconsistent
  status text ("ship", "done", "in progress"), missing customers/regions,
  duplicate rows, and blank rows — to demonstrate the Processing Engine.
- **Inventory sheet**: 10 items with current stock and reorder levels.

---

## 4. Turning This Into a Research Paper

**Suggested paper structure:**

1. **Introduction** — motivate the problem: manual Excel-based supply chain
   workflows are slow and error-prone in SMEs; propose rule-based AI
   automation as an accessible alternative to heavyweight ERP/ML systems.
2. **Related Work** — cite literature on inventory reorder-point models
   (safety stock, EOQ), RPA (robotic process automation) in supply chains,
   and lightweight ML for demand forecasting.
3. **System Design / Methodology** — describe the architecture above;
   explicitly document the cleaning rules and the reorder-point / risk
   formulas in `analytics.py` since these form your "algorithm" section.
4. **Implementation** — Python/Streamlit stack, screenshots of each tab.
5. **Evaluation** — run the system on your sample dataset (and ideally a
   second, independent dataset) and report the Research Insights Panel
   metrics: time saved, error reduction, efficiency improvement. Be explicit
   that manual-time baselines are literature-informed *assumptions*, and
   discuss this as a limitation — recommend a follow-up user study (timing
   real staff performing the same task manually) to validate the estimates
   empirically.
6. **Discussion** — scalability (how the same rules extend to larger
   datasets/multiple warehouses), limitations of rule-based "AI" vs. true
   ML/forecasting, and future work (e.g. replacing the linear trend model
   with ARIMA/Prophet, or adding classification models for demand
   forecasting).
7. **Conclusion**.

**Tip:** Because every metric in the Research Insights Panel is generated
from a documented formula (see `analytics.research_insights()`), you can
include the formulas directly in your methodology section and vary the
assumptions (minutes/row, error rate) as a sensitivity analysis.

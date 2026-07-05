"""
generate_sample_data.py
------------------------
One-off script used to generate sample_supply_chain_data.xlsx — a realistic,
intentionally messy dataset for demoing and testing the AI-Powered Excel
Automation System. Not part of the main application; run manually if you
want to regenerate the sample file.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

items = [
    "Steel Bolts M8", "Hydraulic Pump HP-200", "Conveyor Belt 5m",
    "Industrial Sensor X1", "Packaging Box Large", "Aluminum Sheet 2mm",
    "Ball Bearing 6205", "Safety Helmet", "Forklift Tire", "Circuit Board CB-12",
]

customers = [
    "Ace Manufacturing", "Bangsar Logistics", "Cyberjaya Robotics",
    "Delta Freight", "EverGreen Traders", "Fujiwara Industries",
    "Puchong Warehousing", "Global Parts Sdn Bhd",
]

regions = ["Selangor", "Johor", "Penang", "Kuala Lumpur", "Sabah", "Sarawak"]

status_variants = [
    "Pending", "pending", "PENDING", "Processing", "processing", "in progress",
    "Shipped", "ship", "dispatched", "Completed", "done", "delivered", "complete",
]

rows = []
start_date = datetime(2025, 1, 1)

for i in range(1, 261):
    order_id = f"ORD-{1000 + i}"
    date = start_date + timedelta(days=random.randint(0, 180))
    item = random.choice(items)
    quantity = random.choice([5, 10, 12, 15, 20, 25, 30, 40, 50, np.nan])
    status = random.choice(status_variants)
    customer = random.choice(customers)
    region = random.choice(regions)
    unit_price = round(random.uniform(8, 150), 2)
    revenue = round(quantity * unit_price, 2) if pd.notna(quantity) else np.nan

    rows.append([order_id, date, item, quantity, status, customer, region, revenue])

orders_df = pd.DataFrame(rows, columns=[
    "Order ID", "Date", "Item", "Quantity", "Status", "Customer", "Region", "Revenue"
])

# Inject some messiness: missing customers/regions, exact duplicates, blank rows
for idx in random.sample(range(len(orders_df)), 15):
    orders_df.loc[idx, "Customer"] = np.nan
for idx in random.sample(range(len(orders_df)), 10):
    orders_df.loc[idx, "Region"] = np.nan

duplicate_rows = orders_df.sample(8, random_state=1)
orders_df = pd.concat([orders_df, duplicate_rows], ignore_index=True)

blank_row = pd.DataFrame([[np.nan] * len(orders_df.columns)], columns=orders_df.columns)
orders_df = pd.concat([orders_df, blank_row, blank_row], ignore_index=True)

orders_df = orders_df.sample(frac=1, random_state=7).reset_index(drop=True)  # shuffle

# Inventory sheet
inventory_rows = []
for item in items:
    current_stock = random.randint(20, 300)
    reorder_level = random.randint(30, 100)
    inventory_rows.append([item, current_stock, reorder_level])

inventory_df = pd.DataFrame(inventory_rows, columns=["Item", "Current Stock", "Reorder Level"])

with pd.ExcelWriter("sample_supply_chain_data.xlsx", engine="openpyxl") as writer:
    orders_df.to_excel(writer, sheet_name="Orders", index=False)
    inventory_df.to_excel(writer, sheet_name="Inventory", index=False)

print("Sample dataset generated: sample_supply_chain_data.xlsx")
print(f"Orders sheet: {len(orders_df)} rows (intentionally messy)")
print(f"Inventory sheet: {len(inventory_df)} rows")

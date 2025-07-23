import pandas as pd

# --- STEP 1: Load and Transform previous.csv ---
previous = pd.read_csv(
    r"previous.csv",
    encoding='utf-8-sig',  # or 'latin1'
    on_bad_lines='skip'
)

# Define required columns for previous.csv (as in Power BI)
required_previous_columns = {
    "TCGplayer Id": 'Int64',
    "Product Line": 'string',
    "Set Name": 'string',
    "Product Name": 'string',
    "Title": 'string',
    "Number": 'string',
    "Rarity": 'string',
    "Condition": 'string',
    "TCG Market Price": 'float64',
    "TCG Direct Low": 'float64',
    "TCG Low Price With Shipping": 'float64',
    "TCG Low Price": 'float64',
    "Total Quantity": 'Int64',
    "Add to Quantity": 'Int64',
    "Old Marketplace Price": 'float64',
    "My Store Reserve Quantity": 'Int64',
    "Old My Store Price": 'float64',
    "Photo URL": 'string',
    "Old Qty": 'Int64',
    "Base Price": 'float64',
    "TCG Marketplace Price": 'float64',
    "My Store Price": 'float64',
    "Old Multiplier": 'float64',
    "Multiplier": 'float64',
    "Diff": 'float64'
}

# Add missing columns with default values
for col, dtype in required_previous_columns.items():
    if col not in previous.columns:
        if dtype == 'float64':
            previous[col] = float('nan')
        elif dtype == 'Int64':
            previous[col] = pd.NA
        else:
            previous[col] = ''

# Convert column types
for col, dtype in required_previous_columns.items():
    try:
        if dtype == 'Int64':
            previous[col] = pd.to_numeric(previous[col], errors='coerce').astype('Int64')
        elif dtype == 'float64':
            previous[col] = pd.to_numeric(previous[col], errors='coerce')
        elif dtype == 'string':
            previous[col] = previous[col].astype(str)
    except Exception:
        previous[col] = float('nan')

# Load current.csv with safe encoding
current = pd.read_csv(
    r"current.csv",
    encoding='utf-8-sig',  # or 'latin1'
    on_bad_lines='skip'
)

# Rename columns (like Power BI)
if "My Store Price" in current.columns:
    current = current.rename(columns={"My Store Price": "Old My Store Price"})
else:
    current["Old My Store Price"] = float('nan')  # Default if missing

if "TCG Marketplace Price" in current.columns:
    current = current.rename(columns={"TCG Marketplace Price": "Old Marketplace Price"})
else:
    current["Old Marketplace Price"] = float('nan')

# Filter rows (like Power BI)
current = current[current["Condition"] != "Unopened"]
current = current[current["TCG Market Price"].notna()]

# Ensure TCGplayer Id is numeric
current["TCGplayer Id"] = pd.to_numeric(current["TCGplayer Id"], errors='coerce').astype('Int64')

# --- STEP 3: Merge and Apply Pricing Logic ---
merged = pd.merge(
    current,
    previous[["TCGplayer Id", "Old Multiplier"]],
    on="TCGplayer Id",
    how="left"
)

# Fill missing Old Multiplier with default value (like Power BI)
merged["Old Multiplier"] = merged["Old Multiplier"].fillna(1.2)

# --- BASE PRICE (updated to use TCG Market Price) ---
def calculate_base_price(row):
    market = row["TCG Market Price"]
    low = row["TCG Low Price"]
    if pd.notna(market) and pd.notna(low):
        return round(min(market, low), 2)
    elif pd.notna(low):
        return round(low, 2)
    elif pd.notna(market):
        return round(market, 2)
    else:
        return 50000.00

merged["Base Price"] = merged.apply(calculate_base_price, axis=1)

# --- MULTIPLIER ---
def calculate_multiplier(row):
    old_qty = row.get("Old Qty", 0)
    new_qty = row.get("Total Quantity", 0)
    old_mult = row.get("Old Multiplier", 1.2)

    if old_qty == 0:
        return 1.2
    elif old_qty > 0 and new_qty == 0:
        return 1.2
    elif old_qty < new_qty:
        return round(old_mult + 0.01, 2)
    elif old_mult - 0.05 > 1:
        return round(old_mult - 0.05, 2)
    else:
        return round(old_mult - 0.01, 2)

merged["Multiplier"] = merged.apply(calculate_multiplier, axis=1)

# --- MY STORE PRICE ---
def calculate_store_price(row):
    market_price = row["TCG Market Price"]
    base = row["Base Price"]
    mult = row["Multiplier"]
    qty = row["Total Quantity"]

    raw_price = round(market_price if pd.notna(market_price) else base * mult, 2)
    bump = 0.25
    if qty >= 40:
        bump = 0.05
    elif qty >= 20:
        bump = 0.15
    return raw_price + max(0, bump - raw_price)

merged["My Store Price"] = merged.apply(calculate_store_price, axis=1)

# --- DIFF ---
# Handle missing values in "Old My Store Price" gracefully
merged["Old My Store Price"] = merged["Old My Store Price"].fillna(0.0)
merged["Diff"] = merged["My Store Price"] - merged["Old My Store Price"]

# --- Export Final DataFrame ---
merged.to_csv("updated_pricing.csv", index=False)

# Optional: Print column names for debugging
print("Final Columns:", merged.columns.tolist())
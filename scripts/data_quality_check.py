import pandas as pd
from pathlib import Path

# Project raw data directory
DATA_DIR = Path("data/raw")

# Main datasets
FILES = [
    "olist_customers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_products_dataset.csv",
    "product_category_name_translation.csv"
]

for file in FILES:
    print("\n" + "=" * 60)
    print(f"DATA QUALITY REPORT: {file}")
    print("=" * 60)

    file_path = DATA_DIR / file
    df = pd.read_csv(file_path)

    # 1. Dataset dimensions
    print("\n1. Dataset Information")
    print("Rows:", df.shape[0])
    print("Columns:", df.shape[1])

    # 2. Missing values
    print("\n2. Missing Values")
    missing = df.isnull().sum()
    print(missing[missing > 0] if missing.sum() > 0 else "No missing values")

    # 3. Duplicate rows
    print("\n3. Duplicate Rows")
    print("Duplicates:", df.duplicated().sum())

    # 4. Data types
    print("\n4. Data Types")
    print(df.dtypes)

print("\n" + "=" * 60)
print("DATA QUALITY CHECK COMPLETED")
print("=" * 60)

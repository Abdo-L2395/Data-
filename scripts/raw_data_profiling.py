
import pandas as pd
from pathlib import Path

# ==========================================
# 1. PROJECT PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(exist_ok=True)

FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv"
}

# Store all findings here
findings = []


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def add_finding(dataset, check, column, count, examples=""):
    findings.append({
        "dataset": dataset,
        "check": check,
        "column": column,
        "issue_count": int(count),
        "examples": str(examples)
    })


def read_dataset(filename):
    path = RAW_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Read as strings to preserve original raw values
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def check_numeric(df, dataset, column, minimum=None):
    values = df[column].astype(str).str.strip()
    non_empty = values != ""

    converted = pd.to_numeric(values, errors="coerce")

    invalid = non_empty & converted.isna()

    add_finding(
        dataset, "Invalid numeric values", column,
        invalid.sum(), values[invalid].head(5).tolist()
    )

    if minimum is not None:
        below_minimum = converted.notna() & (converted < minimum)

        add_finding(
            dataset, f"Values below {minimum}", column,
            below_minimum.sum(),
            values[below_minimum].head(5).tolist()
        )


def check_dates(df, dataset, columns):
    for column in columns:
        values = df[column].astype(str).str.strip()
        non_empty = values != ""

        converted = pd.to_datetime(
            values,
            errors="coerce",
            utc=True
        )

        invalid = non_empty & converted.isna()

        add_finding(
            dataset, "Invalid date values", column,
            invalid.sum(), values[invalid].head(5).tolist()
        )


# ==========================================
# 3. PROFILE EACH DATASET
# ==========================================

datasets = {}

for dataset, filename in FILES.items():

    print(f"\nProfiling: {filename}")

    df = read_dataset(filename)
    datasets[dataset] = df

    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    # Missing values
    for column in df.columns:
        missing = df[column].astype(str).str.strip().eq("")

        add_finding(
            dataset, "Missing values", column,
            missing.sum()
        )

    # Complete duplicate rows
    duplicates = df.duplicated()

    add_finding(
        dataset, "Duplicate rows", "ALL_COLUMNS",
        duplicates.sum()
    )


# ==========================================
# 4. PRIMARY KEY CHECKS
# ==========================================

primary_keys = {
    "customers": ["customer_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "products": ["product_id"],
    "category_translation": ["product_category_name"]
}

for dataset, columns in primary_keys.items():

    df = datasets[dataset]

    missing_key = df[columns].apply(
        lambda col: col.astype(str).str.strip().eq("")
    ).any(axis=1)

    add_finding(
        dataset, "Missing primary key",
        ", ".join(columns), missing_key.sum()
    )

    duplicate_key = df.duplicated(subset=columns, keep=False)

    add_finding(
        dataset, "Duplicate primary key",
        ", ".join(columns), duplicate_key.sum(),
        df.loc[duplicate_key, columns].head(5).to_dict("records")
    )


# ==========================================
# 5. NUMERIC VALIDATION
# ==========================================

numeric_rules = {
    "order_items": {
        "price": 0,
        "freight_value": 0
    },
    "products": {
        "product_name_lenght": 0,
        "product_description_lenght": 0,
        "product_photos_qty": 0,
        "product_weight_g": 1,
        "product_length_cm": 1,
        "product_height_cm": 1,
        "product_width_cm": 1
    }
}

for dataset, rules in numeric_rules.items():

    df = datasets[dataset]

    for column, minimum in rules.items():

        if column in df.columns:
            check_numeric(
                df, dataset, column, minimum
            )


# ==========================================
# 6. DATE VALIDATION
# ==========================================

date_columns = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]
}

for dataset, columns in date_columns.items():

    df = datasets[dataset]

    check_dates(
        df, dataset,
        [col for col in columns if col in df.columns]
    )


# ==========================================
# 7. ORDER STATUS VALIDATION
# ==========================================

valid_statuses = {
    "created",
    "approved",
    "invoiced",
    "processing",
    "shipped",
    "delivered",
    "canceled",
    "unavailable"
}

orders = datasets["orders"]

if "order_status" in orders.columns:

    status = orders["order_status"].str.strip()

    invalid = (
        (status != "") &
        (~status.isin(valid_statuses))
    )

    add_finding(
        "orders", "Unknown order status",
        "order_status", invalid.sum(),
        status[invalid].head(5).tolist()
    )


# ==========================================
# 8. RELATIONSHIP VALIDATION
# ==========================================

customers = datasets["customers"]
orders = datasets["orders"]
items = datasets["order_items"]
products = datasets["products"]

customer_ids = set(customers["customer_id"])
order_ids = set(orders["order_id"])
product_ids = set(products["product_id"])

# Orders -> Customers
invalid_customers = (
    orders["customer_id"].str.strip() != ""
) & (~orders["customer_id"].isin(customer_ids))

add_finding(
    "orders", "Customer ID not found",
    "customer_id", invalid_customers.sum(),
    orders.loc[invalid_customers, "customer_id"].head(5).tolist()
)

# Order items -> Orders
invalid_orders = (
    items["order_id"].str.strip() != ""
) & (~items["order_id"].isin(order_ids))

add_finding(
    "order_items", "Order ID not found",
    "order_id", invalid_orders.sum(),
    items.loc[invalid_orders, "order_id"].head(5).tolist()
)

# Order items -> Products
invalid_products = (
    items["product_id"].str.strip() != ""
) & (~items["product_id"].isin(product_ids))

add_finding(
    "order_items", "Product ID not found",
    "product_id", invalid_products.sum(),
    items.loc[invalid_products, "product_id"].head(5).tolist()
)


# ==========================================
# 9. SAVE REPORTS
# ==========================================

report = pd.DataFrame(findings)

details_path = REPORT_DIR / "raw_data_profiling_details.csv"
summary_path = REPORT_DIR / "raw_data_profiling_summary.txt"

report.to_csv(details_path, index=False)

with open(summary_path, "w", encoding="utf-8") as file:

    file.write("RAW DATA PROFILING REPORT\n")
    file.write("=" * 60 + "\n\n")

    for dataset, df in datasets.items():

        file.write(f"DATASET: {dataset}\n")
        file.write("-" * 40 + "\n")
        file.write(f"Rows: {len(df)}\n")
        file.write(f"Columns: {len(df.columns)}\n\n")

        dataset_findings = report[
            report["dataset"] == dataset
        ]

        for _, row in dataset_findings.iterrows():

            if row["issue_count"] > 0:
                file.write(
                    f'{row["check"]} | '
                    f'{row["column"]} | '
                    f'Count: {row["issue_count"]}\n'
                )

        file.write("\n")

    file.write("=" * 60 + "\n")
    file.write("PROFILING COMPLETED\n")

print("\n" + "=" * 60)
print("RAW DATA PROFILING COMPLETED")
print("=" * 60)

print("\nReports saved:")
print(details_path)
print(summary_path)

print("\nTotal findings:", len(report))
print(
    "Checks with issues:",
    (report["issue_count"] > 0).sum()
)

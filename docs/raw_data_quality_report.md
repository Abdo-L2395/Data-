# Raw Data Quality Profiling Report

## 1. Project Information

**Project:** E-Commerce Order & Delivery Analytics Pipeline

**Phase:** Phase 2 – Data Ingestion, Raw Storage & Containerization

**Data Source:** Olist Brazilian E-Commerce Dataset

**Profiling Scope:** Five selected original CSV files stored in `data/raw/`.

## 2. Profiling Objective

The objective of this profiling process is to identify data quality issues in the original, unmodified datasets before any cleaning or transformation.

The profiling process checks:

- Missing values
- Duplicate rows
- Duplicate primary keys
- Invalid numeric values
- Invalid dates
- Unknown order statuses
- Referential integrity between related datasets

**Important:** The profiling process is read-only. No original CSV files were modified.

## 3. Datasets Overview

| Dataset | Rows | Columns |
|---|---:|---:|
| Customers | 99,441 | 5 |
| Orders | 99,441 | 8 |
| Order Items | 112,650 | 7 |
| Products | 32,951 | 9 |
| Category Translation | 71 | 2 |
| **Total** | **344,554** | |

## 4. Identified Data Quality Issues

### 4.1 Orders Dataset

Missing date values were identified:

| Column | Missing Values |
|---|---:|
| order_approved_at | 160 |
| order_delivered_carrier_date | 1,783 |
| order_delivered_customer_date | 2,965 |

Missing dates were further analyzed by order status.

**Missing order_approved_at:**
- Canceled: 141
- Delivered: 14
- Created: 5

**Missing order_delivered_carrier_date:**
- Unavailable: 609
- Canceled: 550
- Invoiced: 314
- Processing: 301
- Created: 5
- Approved: 2
- Delivered: 2

**Missing order_delivered_customer_date:**
- Shipped: 1,107
- Canceled: 619
- Unavailable: 609
- Invoiced: 314
- Processing: 301
- Delivered: 8
- Created: 5
- Approved: 2

Some missing dates may be expected depending on the order status. However, missing delivery-related dates in delivered orders require further investigation.

### 4.2 Products Dataset

Missing descriptive information was identified in 610 products.

| Column | Missing Values |
|---|---:|
| product_category_name | 610 |
| product_name_lenght | 610 |
| product_description_lenght | 610 |
| product_photos_qty | 610 |

All four columns are missing in the same 610 product records.

Additional missing physical information:

| Column | Missing Values |
|---|---:|
| product_weight_g | 2 |
| product_length_cm | 2 |
| product_height_cm | 2 |
| product_width_cm | 2 |

The two products with missing physical information overlap with the descriptive missing group in one record.

Therefore:

- Products with at least one missing value: 611
- Products with missing descriptive information: 610
- Products with missing physical information: 2
- Overlap between these groups: 1

Four additional products have a weight of zero.

These four products do not have missing values.

**Total distinct products flagged for missing values or zero weight: 615.**

Zero weight is flagged for investigation rather than automatically classified as an invalid record.

## 5. Other Dataset Results

### Customers
- 99,441 rows.
- No issues detected by the implemented profiling checks.

### Order Items
- 112,650 rows.
- No issues detected by the implemented profiling checks.

### Category Translation
- 71 rows.
- No missing values detected.
- No duplicate rows detected.

## 6. Duplicate and Integrity Checks

The profiling script includes checks for:

- Duplicate complete rows.
- Duplicate primary keys.
- Missing primary keys.
- Invalid numeric values.
- Invalid dates.
- Unknown order statuses.
- Missing customer, order, and product references.

The current report did not identify issues in these checks beyond the missing values and zero-weight records documented above.

## 7. Conclusion

The profiling process successfully analyzed the five selected original datasets, containing 344,554 records in total.

The main identified issues are:

1. Missing order timestamps.
2. Missing product descriptive information.
3. Missing product physical information.
4. Four products with zero weight.

The original raw files were preserved without modification.

These findings will be used to document data quality limitations and guide any future preprocessing decisions.

## 8. Generated Profiling Artifacts

- `reports/raw_data_profiling_details.csv`
- `reports/raw_data_profiling_summary.txt`
- `scripts/raw_data_profiling.py`

**Profiling Status:** Completed for the implemented checks.

**Note:** The results represent the checks implemented in the profiling script and do not guarantee that every possible data quality issue has been detected.

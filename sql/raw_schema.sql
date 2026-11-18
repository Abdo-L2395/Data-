
-- =====================================================
-- RAW DATA SCHEMA
-- E-Commerce Order & Delivery Analytics Pipeline
-- =====================================================

-- 1. Create separate schema for original source data
CREATE SCHEMA IF NOT EXISTS raw;


-- =====================================================
-- 2. INGESTION BATCHES
-- Tracks every ingestion execution
-- =====================================================

CREATE TABLE IF NOT EXISTS raw.ingestion_batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_file TEXT NOT NULL,
    file_sha256 CHAR(64) NOT NULL,

    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'failed')),

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    rows_read BIGINT DEFAULT 0,
    rows_loaded BIGINT DEFAULT 0,

    error_message TEXT
);


-- Prevent loading the same successful file version twice
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_successful_ingestion_file
ON raw.ingestion_batches (source_file, file_sha256)
WHERE status = 'success';


-- =====================================================
-- 3. CUSTOMERS
-- =====================================================

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id TEXT,
    customer_unique_id TEXT,
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT,

    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    ingestion_batch_id UUID NOT NULL
        REFERENCES raw.ingestion_batches(batch_id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (ingestion_batch_id, source_row_number)
);


-- =====================================================
-- 4. ORDERS
-- =====================================================

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id TEXT,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_approved_at TEXT,
    order_delivered_carrier_date TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT,

    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    ingestion_batch_id UUID NOT NULL
        REFERENCES raw.ingestion_batches(batch_id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (ingestion_batch_id, source_row_number)
);


-- =====================================================
-- 5. ORDER ITEMS
-- =====================================================

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id TEXT,
    order_item_id TEXT,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TEXT,
    price TEXT,
    freight_value TEXT,

    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    ingestion_batch_id UUID NOT NULL
        REFERENCES raw.ingestion_batches(batch_id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (ingestion_batch_id, source_row_number)
);


-- =====================================================
-- 6. PRODUCTS
-- =====================================================

CREATE TABLE IF NOT EXISTS raw.products (
    product_id TEXT,
    product_category_name TEXT,
    product_name_lenght TEXT,
    product_description_lenght TEXT,
    product_photos_qty TEXT,
    product_weight_g TEXT,
    product_length_cm TEXT,
    product_height_cm TEXT,
    product_width_cm TEXT,

    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    ingestion_batch_id UUID NOT NULL
        REFERENCES raw.ingestion_batches(batch_id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (ingestion_batch_id, source_row_number)
);


-- =====================================================
-- 7. CATEGORY TRANSLATION
-- =====================================================

CREATE TABLE IF NOT EXISTS raw.category_translation (
    product_category_name TEXT,
    product_category_name_english TEXT,

    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    ingestion_batch_id UUID NOT NULL
        REFERENCES raw.ingestion_batches(batch_id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (ingestion_batch_id, source_row_number)
);

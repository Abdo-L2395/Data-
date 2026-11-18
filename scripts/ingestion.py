
import csv
import os
import hashlib
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


# =====================================================
# 1. CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "ecommerce_db"),
    "user": os.getenv("DB_USER", "ecommerce_user"),
    "password": os.getenv("DB_PASSWORD"),
}

BATCH_SIZE = 5000

FILES = {
    "olist_customers_dataset.csv": "customers",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_products_dataset.csv": "products",
    "product_category_name_translation.csv": "category_translation",
}


# =====================================================
# 2. LOGGING CONFIGURATION
# =====================================================

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "ingestion.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# =====================================================
# 3. FILE HASHING
# =====================================================

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of the original CSV file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


# =====================================================
# 4. CHECK PREVIOUS INGESTION
# =====================================================

def already_ingested(connection, filename, file_hash):
    """Check whether this exact file version succeeded before."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT batch_id
            FROM raw.ingestion_batches
            WHERE source_file = %s
              AND file_sha256 = %s
              AND status = 'success'
            LIMIT 1;
            """,
            (filename, file_hash)
        )

        return cursor.fetchone() is not None


# =====================================================
# 5. CREATE INGESTION BATCH
# =====================================================

def create_batch(connection, filename, file_hash):
    """Create a new record to track this ingestion attempt."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO raw.ingestion_batches (
                source_file,
                file_sha256,
                status
            )
            VALUES (%s, %s, 'running')
            RETURNING batch_id;
            """,
            (filename, file_hash)
        )

        batch_id = cursor.fetchone()[0]

    connection.commit()
    return batch_id


# =====================================================
# 6. LOAD ONE CSV FILE
# =====================================================

def load_file(connection, file_path, table_name, batch_id):
    """Load original CSV values into the corresponding raw table."""

    filename = file_path.name
    rows_read = 0
    rows_loaded = 0

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)

        headers = next(reader, None)

        if headers is None:
            raise ValueError("CSV file is empty or has no header.")

        # Validate CSV columns against the expected raw table.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'raw'
                  AND table_name = %s
                  AND ordinal_position <= %s
                ORDER BY ordinal_position;
                """,
                (table_name, len(headers))
            )

            expected_headers = [
                row[0] for row in cursor.fetchall()
            ]

        if headers != expected_headers:
            raise ValueError(
                f"CSV headers do not match raw.{table_name}. "
                f"Expected: {expected_headers}, Got: {headers}"
            )

        columns = headers + [
            "source_file",
            "source_row_number",
            "ingestion_batch_id"
        ]

        column_sql = ", ".join(
            f'"{column}"' for column in columns
        )

        insert_sql = (
            f"INSERT INTO raw.{table_name} ({column_sql}) VALUES %s"
        )

        batch = []

        with connection.cursor() as cursor:

            for row_number, row in enumerate(reader, start=1):

                if len(row) != len(headers):
                    raise ValueError(
                        f"Invalid column count at data row {row_number}"
                    )

                rows_read += 1

                values = tuple(row) + (
                    filename,
                    row_number,
                    batch_id
                )

                batch.append(values)

                if len(batch) >= BATCH_SIZE:
                    execute_values(
                        cursor,
                        insert_sql,
                        batch,
                        page_size=BATCH_SIZE
                    )

                    rows_loaded += len(batch)
                    batch.clear()

            # Load the remaining rows.
            if batch:
                execute_values(
                    cursor,
                    insert_sql,
                    batch,
                    page_size=BATCH_SIZE
                )

                rows_loaded += len(batch)

    return rows_read, rows_loaded


# =====================================================
# 7. PROCESS ONE FILE
# =====================================================

def process_file(connection, filename, table_name):
    """Handle hashing, batch tracking, loading and logging."""

    file_path = RAW_DIR / filename

    if not file_path.is_file():
        raise FileNotFoundError(f"Missing source file: {file_path}")

    file_hash = calculate_file_hash(file_path)

    if already_ingested(connection, filename, file_hash):
        logger.info(
            "SKIPPED | %s | This exact file version was already loaded.",
            filename
        )
        return

    batch_id = create_batch(
        connection,
        filename,
        file_hash
    )

    logger.info("STARTED | %s | Batch: %s", filename, batch_id)

    try:
        rows_read, rows_loaded = load_file(
            connection,
            file_path,
            table_name,
            batch_id
        )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE raw.ingestion_batches
                SET status = 'success',
                    completed_at = NOW(),
                    rows_read = %s,
                    rows_loaded = %s
                WHERE batch_id = %s;
                """,
                (rows_read, rows_loaded, batch_id)
            )

        # Commit the loaded rows and success status together.
        connection.commit()

        logger.info(
            "SUCCESS | %s | Read: %s | Loaded: %s",
            filename,
            rows_read,
            rows_loaded
        )

    except Exception as error:
        connection.rollback()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE raw.ingestion_batches
                SET status = 'failed',
                    completed_at = NOW(),
                    error_message = %s
                WHERE batch_id = %s;
                """,
                (str(error)[:4000], batch_id)
            )

        connection.commit()

        logger.exception("FAILED | %s", filename)
        raise


# =====================================================
# 8. MAIN PIPELINE
# =====================================================

def main():

    connection = None

    try:
        if not DB_CONFIG["password"]:
            raise ValueError(
                "DB_PASSWORD environment variable is required."
            )

        logger.info("INGESTION PIPELINE STARTED")

        connection = psycopg2.connect(**DB_CONFIG)

        for filename, table_name in FILES.items():
            process_file(
                connection,
                filename,
                table_name
            )

        logger.info("INGESTION PIPELINE COMPLETED")

    except Exception:
        logger.exception("INGESTION PIPELINE FAILED")
        raise

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()

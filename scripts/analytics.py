import pandas as pd
import psycopg2
import matplotlib.pyplot as plt

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ecommerce_db",
    "user": "ecommerce_user",
    "password": "ecommerce123"
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def sales_performance():
    query = """
        SELECT
            COUNT(DISTINCT o.order_id) AS delivered_orders,
            ROUND(SUM(oi.price), 2) AS total_revenue,
            ROUND(
                SUM(oi.price) / COUNT(DISTINCT o.order_id),
                2
            ) AS average_order_value
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered';
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nSales Performance")
    print(df.to_string(index=False))

def monthly_sales():
    query = """
        SELECT
            TO_CHAR(
                DATE_TRUNC('month', o.order_purchase_timestamp),
                'YYYY-MM'
            ) AS sales_month,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.price), 2) AS monthly_revenue
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY DATE_TRUNC('month', o.order_purchase_timestamp)
        ORDER BY DATE_TRUNC('month', o.order_purchase_timestamp);
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nMonthly Sales")
    print(df.to_string(index=False))   
    plt.figure(figsize=(12, 6))
    plt.plot(df["sales_month"], df["monthly_revenue"], marker="o")
    plt.title("Monthly Sales Revenue")
    plt.xlabel("Month")
    plt.ylabel("Revenue (BRL)")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("dashboard/monthly_sales.png", dpi=300, bbox_inches="tight")

def top_categories_by_revenue():
    query = """
        SELECT
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name
            ) AS category,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.price), 2) AS total_revenue
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        JOIN products p
            ON oi.product_id = p.product_id
        LEFT JOIN category_translation ct
            ON p.product_category_name = ct.product_category_name
        WHERE o.order_status = 'delivered'
        GROUP BY category
        ORDER BY total_revenue DESC
        LIMIT 10;
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nTop 10 Product Categories by Revenue")
    print(df.to_string(index=False))  
    plt.figure(figsize=(12, 6))
    plt.barh(df["category"], df["total_revenue"])
    plt.title("Top 10 Product Categories by Revenue")
    plt.xlabel("Revenue (BRL)")
    plt.ylabel("Product Category")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig("dashboard/top_categories.png", dpi=300, bbox_inches="tight")  

def delivery_performance():
    query = """
        SELECT
            COUNT(*) AS analyzed_deliveries,
            ROUND(
                AVG(
                    EXTRACT(EPOCH FROM (
                        order_delivered_customer_date - order_purchase_timestamp
                    )) / 86400
                )::numeric,
                2
            ) AS avg_delivery_days,
            COUNT(*) FILTER (
                WHERE order_delivered_customer_date::DATE > order_estimated_delivery_date
            ) AS late_deliveries,
            COUNT(*) FILTER (
                WHERE order_delivered_customer_date::DATE <= order_estimated_delivery_date
            ) AS on_time_or_early,
            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE order_delivered_customer_date::DATE > order_estimated_delivery_date
                ) / COUNT(*),
                2
            ) AS late_percentage
        FROM orders
        WHERE order_status = 'delivered'
          AND order_delivered_customer_date IS NOT NULL;
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nDelivery Performance")
    print(df.to_string(index=False))    
    plt.figure(figsize=(8, 6))

    plt.bar(
    ["Late Deliveries", "On Time / Early"],
    [
        df["late_deliveries"].iloc[0],
        df["on_time_or_early"].iloc[0]
    ]
    )

    plt.title("Delivery Performance")
    plt.ylabel("Number of Orders")
    plt.tight_layout()

    plt.savefig(
    "dashboard/delivery_performance.png",
    dpi=300,
    bbox_inches="tight")
def geographical_sales():
    query = """
        SELECT
            c.customer_state AS state,
            COUNT(DISTINCT o.order_id) AS total_orders,
            COUNT(DISTINCT c.customer_unique_id) AS total_customers,
            ROUND(SUM(oi.price), 2) AS total_revenue
        FROM orders o
        JOIN customers c
            ON o.customer_id = c.customer_id
        JOIN order_items oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_state
        ORDER BY total_revenue DESC
        LIMIT 10;
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nGeographical Sales by State")
    print(df.to_string(index=False)) 
    plt.figure(figsize=(12, 6))

    plt.barh(df["state"], df["total_revenue"])

    plt.title("Top 10 States by Revenue")
    plt.xlabel("Revenue (BRL)")
    plt.ylabel("State")

    plt.gca().invert_yaxis()
    plt.tight_layout()

    plt.savefig(
    "dashboard/geographical_sales.png",
    dpi=300,
    bbox_inches="tight")   
def order_status_distribution():
    query = """
        SELECT
            order_status,
            COUNT(*) AS total_orders,
            ROUND(
                100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
                2
            ) AS percentage
        FROM orders
        GROUP BY order_status
        ORDER BY total_orders DESC;
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nOrder Status Distribution")
    print(df.to_string(index=False))
    plt.figure(figsize=(10, 6))

    plt.bar(
    df["order_status"],
    df["total_orders"]
     )

    plt.title("Order Status Distribution")
    plt.xlabel("Order Status")
    plt.ylabel("Number of Orders")

    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(
    "dashboard/order_status_distribution.png",
    dpi=300,
    bbox_inches="tight")

def repeat_customer_analysis():
    query = """
        WITH customer_orders AS (
            SELECT
                c.customer_unique_id,
                COUNT(DISTINCT o.order_id) AS order_count
            FROM customers c
            JOIN orders o
                ON c.customer_id = o.customer_id
            WHERE o.order_status = 'delivered'
            GROUP BY c.customer_unique_id
        )
        SELECT
            COUNT(*) AS total_customers,
            COUNT(*) FILTER (
                WHERE order_count > 1
            ) AS repeat_customers,
            COUNT(*) FILTER (
                WHERE order_count = 1
            ) AS one_time_customers,
            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE order_count > 1
                ) / COUNT(*),
                2
            ) AS repeat_customer_percentage
        FROM customer_orders;
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nRepeat Customer Analysis")
    print(df.to_string(index=False))
    labels = ["One-Time Customers", "Repeat Customers"]

    values = [
    df["one_time_customers"].iloc[0],
    df["repeat_customers"].iloc[0]
     ]

    plt.figure(figsize=(8, 8))

    plt.pie(
    values,
    labels=labels,
    autopct="%1.1f%%",
    startangle=90
     )

    plt.title("One-Time vs Repeat Customers")
    plt.tight_layout()

    plt.savefig(
    "dashboard/repeat_customer_analysis.png",
    dpi=300,
    bbox_inches="tight"
     )
def average_order_value_by_state():
    query = """
        SELECT
            c.customer_state AS state,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.price), 2) AS total_revenue,
            ROUND(
                SUM(oi.price) / COUNT(DISTINCT o.order_id),
                2
            ) AS average_order_value
        FROM orders o
        JOIN customers c
            ON o.customer_id = c.customer_id
        JOIN order_items oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_state
        ORDER BY average_order_value DESC
        LIMIT 10;
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nAverage Order Value by State")
    print(df.to_string(index=False))
    plt.figure(figsize=(12, 6))

    plt.barh(df["state"], df["average_order_value"])

    plt.title("Top 10 States by Average Order Value")
    plt.xlabel("Average Order Value (BRL)")
    plt.ylabel("State")

    plt.gca().invert_yaxis()
    plt.tight_layout()

    plt.savefig(
    "dashboard/average_order_value_by_state.png",
    dpi=300,
    bbox_inches="tight" )

def top_customers():
    query = """
        SELECT
            c.customer_unique_id,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.price)::numeric, 2) AS total_spend
        FROM customers c
        JOIN orders o
            ON c.customer_id = o.customer_id
        JOIN order_items oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_unique_id
        ORDER BY total_spend DESC
        LIMIT 10;
    """

    with get_connection() as connection:
        df = pd.read_sql_query(query, connection)

    print("\nTop 10 Customers by Revenue")
    print(df.to_string(index=False))
    plt.figure(figsize=(12, 6))

    plt.barh(
    df["customer_unique_id"],
    df["total_spend"]
     )

    plt.title("Top 10 Customers by Total Spend")
    plt.xlabel("Total Spend (BRL)")
    plt.ylabel("Customer ID")

    plt.gca().invert_yaxis()
    plt.tight_layout()

    plt.savefig(
    "dashboard/top_customers.png",
    dpi=300,
    bbox_inches="tight")

if __name__ == "__main__":
    sales_performance()
    monthly_sales()
    top_categories_by_revenue()
    delivery_performance()
    geographical_sales()
    order_status_distribution()
    repeat_customer_analysis()
    average_order_value_by_state()
    top_customers() 

import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
from decimal import Decimal

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="E-Commerce Analytics Dashboard",
    page_icon="🛒",
    layout="wide"
)

# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ecommerce_db",
    "user": "ecommerce_user",
    "password": "ecommerce123"
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def fetch_df(query, params=None):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        df = pd.DataFrame(rows, columns=columns)

        # Convert Decimal values to numeric values for Plotly
        for column in df.columns:
            if len(df) > 0 and isinstance(df[column].iloc[0], Decimal):
                df[column] = df[column].astype(float)

        return df

    finally:
        conn.close()


# ==========================================
# 3. DASHBOARD HEADER
# ==========================================

st.title("🛒 E-Commerce Order & Delivery Analytics")
st.markdown(
    "### Business Intelligence Dashboard"
)
st.caption(
    "Explore sales performance, customer behavior, "
    "product categories, and delivery insights."
)

st.divider()


# ==========================================
# 4. LOAD FILTER OPTIONS
# ==========================================

try:
    date_info = fetch_df("""
        SELECT
            MIN(order_purchase_timestamp)::date AS min_date,
            MAX(order_purchase_timestamp)::date AS max_date
        FROM orders
    """)

    states_df = fetch_df("""
        SELECT DISTINCT customer_state
        FROM customers
        ORDER BY customer_state
    """)

    statuses_df = fetch_df("""
        SELECT DISTINCT order_status
        FROM orders
        ORDER BY order_status
    """)

except Exception as error:
    st.error(f"Database connection failed: {error}")
    st.stop()


min_date = date_info.loc[0, "min_date"]
max_date = date_info.loc[0, "max_date"]

all_states = states_df["customer_state"].tolist()
all_statuses = statuses_df["order_status"].tolist()


# ==========================================
# 5. SIDEBAR FILTERS
# ==========================================

st.sidebar.title("🔎 Dashboard Filters")

selected_dates = st.sidebar.date_input(
    "Purchase Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
    st.warning("Please select a start date and an end date.")
    st.stop()

start_date, end_date = selected_dates

if start_date > end_date:
    st.warning("Start date must be before end date.")
    st.stop()

selected_states = st.sidebar.multiselect(
    "Customer State",
    options=all_states,
    default=all_states
)

selected_statuses = st.sidebar.multiselect(
    "Order Status",
    options=all_statuses,
    default=all_statuses
)

if not selected_states or not selected_statuses:
    st.warning("Select at least one state and one order status.")
    st.stop()

st.sidebar.divider()
st.sidebar.caption("Data source: Olist E-Commerce Dataset")
st.sidebar.caption("Database: PostgreSQL")


# ==========================================
# 6. COMMON FILTER
# ==========================================

FILTER_CTE = """
WITH filtered_orders AS (
    SELECT
        o.order_id,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        c.customer_unique_id,
        c.customer_state
    FROM orders o
    JOIN customers c
        ON o.customer_id = c.customer_id
    WHERE
        o.order_purchase_timestamp::date BETWEEN %s AND %s
        AND c.customer_state = ANY(%s)
        AND o.order_status = ANY(%s)
)
"""

params = (
    start_date,
    end_date,
    selected_states,
    selected_statuses
)


# ==========================================
# 7. KEY PERFORMANCE INDICATORS
# ==========================================

kpi_query = FILTER_CTE + """
, delivered_orders AS (
    SELECT *
    FROM filtered_orders
    WHERE order_status = 'delivered'
),
order_revenue AS (
    SELECT
        d.order_id,
        SUM(oi.price) AS revenue
    FROM delivered_orders d
    JOIN order_items oi
        ON d.order_id = oi.order_id
    GROUP BY d.order_id
)
SELECT
    (SELECT COUNT(*) FROM filtered_orders) AS total_orders,

    COALESCE(
        (SELECT SUM(revenue) FROM order_revenue),
        0
    ) AS total_revenue,

    COALESCE(
        (SELECT AVG(revenue) FROM order_revenue),
        0
    ) AS average_order_value,

    COALESCE(
        (
            SELECT
                100.0 * COUNT(*) FILTER (
                    WHERE order_delivered_customer_date::date
                    > order_estimated_delivery_date::date
                )
                / NULLIF(COUNT(*), 0)
            FROM delivered_orders
            WHERE
                order_delivered_customer_date IS NOT NULL
                AND order_estimated_delivery_date IS NOT NULL
        ),
        0
    ) AS late_delivery_rate
"""

try:
    kpis = fetch_df(kpi_query, params).iloc[0]

except Exception as error:
    st.error(f"Could not load dashboard metrics: {error}")
    st.stop()


# ==========================================
# 8. DISPLAY KPI CARDS
# ==========================================

st.subheader("📊 Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Orders",
    f"{int(kpis['total_orders']):,}"
)

col2.metric(
    "Total Revenue",
    f"R$ {float(kpis['total_revenue']):,.2f}"
)

col3.metric(
    "Average Order Value",
    f"R$ {float(kpis['average_order_value']):,.2f}"
)

col4.metric(
    "Late Delivery Rate",
    f"{float(kpis['late_delivery_rate']):.2f}%"
)

st.divider()


# ==========================================
# 9. MONTHLY SALES REVENUE
# ==========================================

st.subheader("📈 Monthly Sales Revenue")

monthly_query = FILTER_CTE + """
SELECT
    DATE_TRUNC('month', f.order_purchase_timestamp)::date AS month,
    SUM(oi.price) AS revenue
FROM filtered_orders f
JOIN order_items oi
    ON f.order_id = oi.order_id
WHERE f.order_status = 'delivered'
GROUP BY month
ORDER BY month
"""

monthly_df = fetch_df(monthly_query, params)

if not monthly_df.empty:
    monthly_df["month"] = pd.to_datetime(monthly_df["month"])

    fig_monthly = px.line(
        monthly_df,
        x="month",
        y="revenue",
        markers=True,
        title="Monthly Revenue",
        labels={
            "month": "Month",
            "revenue": "Revenue (BRL)"
        }
    )

    fig_monthly.update_layout(
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_monthly,
        use_container_width=True
    )
else:
    st.info("No monthly sales data for the selected filters.")


st.divider()


# ==========================================
# 10. TOP PRODUCT CATEGORIES
# ==========================================

st.subheader("🏆 Top Product Categories by Revenue")

category_query = FILTER_CTE + """
SELECT
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name,
        'Unknown'
    ) AS category,
    SUM(oi.price) AS revenue
FROM filtered_orders f
JOIN order_items oi
    ON f.order_id = oi.order_id
JOIN products p
    ON oi.product_id = p.product_id
LEFT JOIN category_translation ct
    ON p.product_category_name = ct.product_category_name
WHERE f.order_status = 'delivered'
GROUP BY category
ORDER BY revenue DESC
LIMIT 10
"""

category_df = fetch_df(category_query, params)

if not category_df.empty:
    fig_category = px.bar(
        category_df.sort_values("revenue"),
        x="revenue",
        y="category",
        orientation="h",
        title="Top 10 Categories by Revenue",
        labels={
            "revenue": "Revenue (BRL)",
            "category": "Product Category"
        }
    )

    st.plotly_chart(
        fig_category,
        use_container_width=True
    )
else:
    st.info("No category data for the selected filters.")


st.divider()


# ==========================================
# 11. ORDER STATUS DISTRIBUTION
# ==========================================

st.subheader("📦 Order Status Distribution")

status_query = FILTER_CTE + """
SELECT
    order_status,
    COUNT(*) AS total_orders
FROM filtered_orders
GROUP BY order_status
ORDER BY total_orders DESC
"""

status_df = fetch_df(status_query, params)

if not status_df.empty:
    fig_status = px.pie(
        status_df,
        names="order_status",
        values="total_orders",
        hole=0.45,
        title="Orders by Status"
    )

    st.plotly_chart(
        fig_status,
        use_container_width=True
    )
else:
    st.info("No order status data for the selected filters.")


st.divider()


# ==========================================
# 12. DELIVERY PERFORMANCE
# ==========================================

st.subheader("🚚 Delivery Performance")

delivery_query = FILTER_CTE + """
SELECT
    COUNT(*) FILTER (
        WHERE order_delivered_customer_date::date
        > order_estimated_delivery_date::date
    ) AS late_deliveries,

    COUNT(*) FILTER (
        WHERE order_delivered_customer_date::date
        <= order_estimated_delivery_date::date
    ) AS on_time_or_early

FROM filtered_orders
WHERE
    order_status = 'delivered'
    AND order_delivered_customer_date IS NOT NULL
    AND order_estimated_delivery_date IS NOT NULL
"""

delivery_df = fetch_df(delivery_query, params)

delivery_chart_df = pd.DataFrame({
    "Delivery Result": ["Late", "On Time or Early"],
    "Orders": [
        int(delivery_df.loc[0, "late_deliveries"]),
        int(delivery_df.loc[0, "on_time_or_early"])
    ]
})

fig_delivery = px.bar(
    delivery_chart_df,
    x="Delivery Result",
    y="Orders",
    color="Delivery Result",
    title="Delivery Results"
)

st.plotly_chart(
    fig_delivery,
    use_container_width=True
)


st.divider()


# ==========================================
# 13. SALES BY STATE
# ==========================================

st.subheader("🌎 Sales by Customer State")

state_sales_query = FILTER_CTE + """
SELECT
    f.customer_state,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(oi.price) AS revenue
FROM filtered_orders f
JOIN order_items oi
    ON f.order_id = oi.order_id
WHERE f.order_status = 'delivered'
GROUP BY f.customer_state
ORDER BY revenue DESC
"""

state_sales_df = fetch_df(state_sales_query, params)

if not state_sales_df.empty:
    fig_state_sales = px.bar(
        state_sales_df,
        x="customer_state",
        y="revenue",
        title="Revenue by State",
        labels={
            "customer_state": "State",
            "revenue": "Revenue (BRL)"
        },
        hover_data=["total_orders"]
    )

    st.plotly_chart(
        fig_state_sales,
        use_container_width=True
    )
else:
    st.info("No geographical sales data for the selected filters.")


st.divider()


# ==========================================
# 14. AVERAGE ORDER VALUE BY STATE
# ==========================================

st.subheader("💰 Average Order Value by State")

aov_query = FILTER_CTE + """
, order_revenue AS (
    SELECT
        f.order_id,
        f.customer_state,
        SUM(oi.price) AS revenue
    FROM filtered_orders f
    JOIN order_items oi
        ON f.order_id = oi.order_id
    WHERE f.order_status = 'delivered'
    GROUP BY f.order_id, f.customer_state
)
SELECT
    customer_state,
    COUNT(*) AS total_orders,
    SUM(revenue) AS total_revenue,
    AVG(revenue) AS average_order_value
FROM order_revenue
GROUP BY customer_state
ORDER BY average_order_value DESC
"""

aov_df = fetch_df(aov_query, params)

if not aov_df.empty:
    fig_aov = px.bar(
        aov_df,
        x="customer_state",
        y="average_order_value",
        title="Average Order Value by State",
        labels={
            "customer_state": "State",
            "average_order_value": "Average Order Value (BRL)"
        },
        hover_data=["total_orders", "total_revenue"]
    )

    st.plotly_chart(
        fig_aov,
        use_container_width=True
    )
else:
    st.info("No AOV data for the selected filters.")


st.divider()


# ==========================================
# 15. REPEAT CUSTOMER ANALYSIS
# ==========================================

st.subheader("👥 Customer Purchase Frequency")

repeat_query = FILTER_CTE + """
, customer_orders AS (
    SELECT
        customer_unique_id,
        COUNT(DISTINCT order_id) AS order_count
    FROM filtered_orders
    WHERE order_status = 'delivered'
    GROUP BY customer_unique_id
)
SELECT
    COUNT(*) FILTER (
        WHERE order_count = 1
    ) AS one_time_customers,

    COUNT(*) FILTER (
        WHERE order_count > 1
    ) AS repeat_customers

FROM customer_orders
"""

repeat_df = fetch_df(repeat_query, params)

repeat_chart_df = pd.DataFrame({
    "Customer Type": [
        "One-Time Customers",
        "Repeat Customers"
    ],
    "Customers": [
        int(repeat_df.loc[0, "one_time_customers"]),
        int(repeat_df.loc[0, "repeat_customers"])
    ]
})

fig_repeat = px.pie(
    repeat_chart_df,
    names="Customer Type",
    values="Customers",
    hole=0.45,
    title="One-Time vs Repeat Customers"
)

st.plotly_chart(
    fig_repeat,
    use_container_width=True
)


st.divider()


# ==========================================
# 16. TOP 10 CUSTOMERS
# ==========================================

st.subheader("⭐ Top 10 Customers by Spending")

top_customers_query = FILTER_CTE + """
SELECT
    f.customer_unique_id,
    SUM(oi.price) AS total_spending,
    COUNT(DISTINCT f.order_id) AS total_orders
FROM filtered_orders f
JOIN order_items oi
    ON f.order_id = oi.order_id
WHERE f.order_status = 'delivered'
GROUP BY f.customer_unique_id
ORDER BY total_spending DESC
LIMIT 10
"""

top_customers_df = fetch_df(
    top_customers_query,
    params
)

if not top_customers_df.empty:
    top_customers_df["customer_label"] = (
        top_customers_df["customer_unique_id"].str[:10]
    )

    fig_customers = px.bar(
        top_customers_df.sort_values("total_spending"),
        x="total_spending",
        y="customer_label",
        orientation="h",
        title="Top 10 Customers by Spending",
        labels={
            "total_spending": "Total Spending (BRL)",
            "customer_label": "Customer ID"
        },
        hover_data=["total_orders"]
    )

    st.plotly_chart(
        fig_customers,
        use_container_width=True
    )
else:
    st.info("No customer spending data for the selected filters.")


# ==========================================
# 17. FOOTER
# ==========================================

st.divider()

st.caption(
    "E-Commerce Order & Delivery Analytics | "
    "Powered by PostgreSQL, Python, Streamlit & Plotly"
)

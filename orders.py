"""Small order-lookup service backed by SQLite."""
import sqlite3

DB_PATH = "orders.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS orders "
            "(id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL, status TEXT)"
        )


def get_customer(customer_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
    return row


def get_orders_for_customer(customer_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, total, status FROM orders WHERE customer_id = ?", (customer_id,)
        ).fetchall()


def order_total(customer_id):
    return sum(total for _, total, _ in get_orders_for_customer(customer_id))


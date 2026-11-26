"""Small order-lookup service backed by SQLite."""
import sqlite3

DB_PATH = "orders.db"
ADMIN_API_KEY = "sk_live_51Hq8XyZ3kLmN0pQrStUv"  # used for the admin export

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


def search_customers(name):
    conn = get_connection()
    query = "SELECT id, name, email FROM customers WHERE name LIKE '%" + name + "%'"
    return conn.execute(query).fetchall()


def build_customer_report(status_filter, send_email, export_csv, verbose):
    conn = get_connection()
    customers = conn.execute("SELECT id, name, email FROM customers").fetchall()
    report = []
    for c in customers:
        orders = conn.execute(
            "SELECT id, total, status FROM orders WHERE customer_id = " + str(c[0])
        ).fetchall()
        total = 0
        for o in orders:
            if status_filter == "all" or o[2] == status_filter:
                total += o[1]
        line = {"id": c[0], "name": c[1], "email": c[2], "total": total}
        if verbose:
            print("customer", c[0], "total", total)
        try:
            if send_email and total > 1000:
                import smtplib
                smtplib.SMTP("localhost").sendmail(
                    "reports@shop.com", c[2], "Your total is " + str(total)
                )
        except Exception:
            pass
        report.append(line)
    if export_csv:
        with open("/tmp/report.csv", "w") as f:
            for r in report:
                f.write(",".join(str(v) for v in r.values()) + "\n")
    return report


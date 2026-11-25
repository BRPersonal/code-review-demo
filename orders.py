"""Small order-lookup service backed by SQLite."""
import csv
import logging
import os
import smtplib
import sqlite3
from contextlib import closing

logger = logging.getLogger(__name__)

DB_PATH = "orders.db"
# Loaded from the environment; never commit keys to source control.
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS orders "
            "(id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL, status TEXT)"
        )


def get_customer(customer_id):
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT id, name, email FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()


def get_orders_for_customer(customer_id):
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT id, total, status FROM orders WHERE customer_id = ?", (customer_id,)
        ).fetchall()


def order_total(customer_id):
    return sum(total or 0 for _, total, _ in get_orders_for_customer(customer_id))


def search_customers(name):
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT id, name, email FROM customers WHERE name LIKE ?",
            ("%" + name + "%",),
        ).fetchall()


def build_customer_report(status_filter="all"):
    """Return one dict per customer with their order total.

    Pure query: no emails, files or printing. A status_filter of "all"
    counts every order; otherwise only orders with that status.
    """
    query = (
        "SELECT c.id, c.name, c.email, COALESCE(SUM(o.total), 0) "
        "FROM customers c "
        "LEFT JOIN orders o ON o.customer_id = c.id"
    )
    params = ()
    if status_filter != "all":
        # Filter in the join condition so customers with no matches still appear.
        query += " AND o.status = ?"
        params = (status_filter,)
    query += " GROUP BY c.id, c.name, c.email ORDER BY c.id"
    with closing(get_connection()) as conn:
        rows = conn.execute(query, params).fetchall()
    return [{"id": r[0], "name": r[1], "email": r[2], "total": r[3]} for r in rows]


def send_report_emails(report, threshold=1000, host="localhost"):
    """Email customers whose total exceeds threshold. Returns the failures."""
    failures = []
    try:
        smtp = smtplib.SMTP(host)
    except OSError:
        logger.exception("Could not connect to SMTP server at %s", host)
        return [r["id"] for r in report if r["total"] > threshold]
    with smtp:
        for r in report:
            if r["total"] <= threshold:
                continue
            if not r["email"]:
                logger.warning("Customer %s has no email address", r["id"])
                failures.append(r["id"])
                continue
            try:
                smtp.sendmail(
                    "reports@shop.com", r["email"], "Your total is " + str(r["total"])
                )
            except (smtplib.SMTPException, OSError):
                logger.exception("Failed to email customer %s", r["id"])
                failures.append(r["id"])
    return failures


def _csv_safe(value):
    """Neutralise spreadsheet formula injection."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def export_report_csv(report, path):
    """Write the report to path as CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "email", "total"])
        for r in report:
            writer.writerow(
                [r["id"], _csv_safe(r["name"]), _csv_safe(r["email"]), r["total"]]
            )

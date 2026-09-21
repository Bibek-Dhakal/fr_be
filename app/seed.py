import sqlite3
import random
from datetime import datetime, timedelta

def seed_db() -> None:
    """Drops, creates, and seeds the orders and pdf_reports tables in report.db."""
    with sqlite3.connect("report.db") as conn:
        cursor = conn.cursor()
        
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT,
                product TEXT,
                amount REAL,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pdf_reports (
                id TEXT PRIMARY KEY,
                date TEXT,
                status TEXT,
                file TEXT,
                created_at TEXT
            )
        """)
        
        products = ["Widget A", "Widget B", "Super Widget", "Mega Widget", "Widget Pro"]
        customers = [f"Customer {i}" for i in range(1, 21)]
        
        for _ in range(200):
            customer = random.choice(customers)
            product = random.choice(products)
            amount = round(random.uniform(5.0, 200.0), 2)
            days_ago = random.randint(0, 30)
            created_at = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                "INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)",
                (customer, product, amount, created_at)
            )
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        print(f"Seeded {count} orders in report.db")

if __name__ == "__main__":
    seed_db()
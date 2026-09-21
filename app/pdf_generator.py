import sqlite3
import os
from datetime import datetime
from typing import Any
from playwright.async_api import async_playwright

def get_report_data() -> dict[str, Any]:
    """Aggregates data from SQLite report.db."""
    with sqlite3.connect("report.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        total_orders = cursor.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        total_revenue = cursor.execute("SELECT SUM(amount) FROM orders").fetchone()[0] or 0
        
        top_products = cursor.execute("""
            SELECT product, SUM(amount) as rev 
            FROM orders 
            GROUP BY product 
            ORDER BY rev DESC 
            LIMIT 5
        """).fetchall()
        
        daily_orders = cursor.execute("""
            SELECT date(created_at) as d, COUNT(*) as c
            FROM orders
            WHERE date(created_at) >= date('now', '-7 days')
            GROUP BY d
            ORDER BY d
        """).fetchall()

        all_orders = cursor.execute("""
            SELECT id, customer, product, amount, created_at 
            FROM orders 
            ORDER BY created_at DESC
        """).fetchall()

        return {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "top_products": [dict(r) for r in top_products],
            "daily_orders": [dict(r) for r in daily_orders],
            "all_orders": [dict(r) for r in all_orders]
        }

async def render_pdf(data: dict[str, Any], output_path: str) -> None:
    """Takes aggregated dict data and writes a fully rendered A4 PDF using headless Chromium."""
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
            th {{ background-color: #eee; }}
            tr {{ break-inside: avoid; }}
            h1, h2 {{ color: #333; }}
            .summary {{ display: flex; gap: 20px; margin-bottom: 20px; }}
            .summary-box {{ padding: 15px; border: 1px solid #ccc; border-radius: 5px; flex: 1; background: #fafafa; }}
        </style>
    </head>
    <body>
        <h1>Sales Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="summary">
            <div class="summary-box">
                <h2>Total Orders</h2>
                <p>{data['total_orders']}</p>
            </div>
            <div class="summary-box">
                <h2>Total Revenue</h2>
                <p>${data['total_revenue']}</p>
            </div>
        </div>

        <h2>Top 5 Products</h2>
        <table>
            <thead>
                <tr><th>Product</th><th>Revenue</th></tr>
            </thead>
            <tbody>
                {"".join(f"<tr><td>{p['product']}</td><td>${round(p['rev'], 2)}</td></tr>" for p in data['top_products'])}
            </tbody>
        </table>

        <h2>All Orders Log</h2>
        <table>
            <thead>
                <tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr>
            </thead>
            <tbody>
                {"".join(f"<tr><td>{o['id']}</td><td>{o['customer']}</td><td>{o['product']}</td><td>${o['amount']}</td><td>{o['created_at']}</td></tr>" for o in data['all_orders'])}
            </tbody>
        </table>
    </body>
    </html>
    """
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html)
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()
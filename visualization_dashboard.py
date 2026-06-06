from pathlib import Path
from html import escape
import json
import math

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent
RAW_DATA_PATH = ROOT_DIR / "data" / "raw_dataset.xlsx"
OUTPUT_DIR = ROOT_DIR / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"
DASHBOARD_PATH = OUTPUT_DIR / "visualization_dashboard.html"
REPORT_PATH = OUTPUT_DIR / "visualization_report.md"
SUMMARY_PATH = OUTPUT_DIR / "dashboard_summary.json"


def load_dataset() -> pd.DataFrame:
    df = pd.read_excel(RAW_DATA_PATH, sheet_name="Sheet1")
    df.columns = [column.strip() for column in df.columns]

    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for column in ["Quantity", "UnitPrice", "ItemsInCart", "TotalPrice"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["CouponCode"] = df["CouponCode"].fillna("NO_COUPON")
    df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
    return df


def summarize(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    monthly = (
        df.groupby("YearMonth")
        .agg(
            OrderCount=("OrderID", "count"),
            TotalRevenue=("TotalPrice", "sum"),
            AverageOrderValue=("TotalPrice", "mean"),
            UnitsSold=("Quantity", "sum"),
        )
        .reset_index()
    )
    monthly["TotalRevenue"] = monthly["TotalRevenue"].round(2)
    monthly["AverageOrderValue"] = monthly["AverageOrderValue"].round(2)

    product = (
        df.groupby("Product")
        .agg(
            OrderCount=("OrderID", "count"),
            UnitsSold=("Quantity", "sum"),
            TotalRevenue=("TotalPrice", "sum"),
            AverageOrderValue=("TotalPrice", "mean"),
        )
        .sort_values("TotalRevenue", ascending=False)
        .reset_index()
    )
    product["TotalRevenue"] = product["TotalRevenue"].round(2)
    product["AverageOrderValue"] = product["AverageOrderValue"].round(2)

    payment = (
        df.groupby("PaymentMethod")
        .agg(OrderCount=("OrderID", "count"), TotalRevenue=("TotalPrice", "sum"))
        .sort_values("OrderCount", ascending=False)
        .reset_index()
    )
    payment["TotalRevenue"] = payment["TotalRevenue"].round(2)

    status = (
        df.groupby("OrderStatus")
        .agg(OrderCount=("OrderID", "count"), TotalRevenue=("TotalPrice", "sum"))
        .sort_values("OrderCount", ascending=False)
        .reset_index()
    )
    status["TotalRevenue"] = status["TotalRevenue"].round(2)

    referral = (
        df.groupby("ReferralSource")
        .agg(OrderCount=("OrderID", "count"), TotalRevenue=("TotalPrice", "sum"))
        .sort_values("TotalRevenue", ascending=False)
        .reset_index()
    )
    referral["TotalRevenue"] = referral["TotalRevenue"].round(2)

    return {
        "monthly": monthly,
        "product": product,
        "payment": payment,
        "status": status,
        "referral": referral,
    }


def money(value: float) -> str:
    return f"${value:,.2f}"


def svg_text(x: float, y: float, text: str, size: int = 12, anchor: str = "middle", color: str = "#334155") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{color}">{escape(str(text))}</text>'


def write_svg(path: Path, width: int, height: int, body: str) -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<rect width="100%" height="100%" rx="0" fill="#ffffff"/>
{body}
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    return svg


def line_chart(labels: list[str], values: list[float], title: str, path: Path) -> str:
    width, height = 980, 380
    left, right, top, bottom = 70, 35, 55, 75
    plot_w, plot_h = width - left - right, height - top - bottom
    min_v, max_v = min(values), max(values)
    span = max(max_v - min_v, 1)
    points = []
    for i, value in enumerate(values):
        x = left + (plot_w * i / max(len(values) - 1, 1))
        y = top + plot_h - ((value - min_v) / span * plot_h)
        points.append((x, y))

    path_d = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))
    label_step = max(len(labels) // 7, 1)
    x_labels = "\n".join(
        svg_text(points[i][0], height - 36, label, 10)
        for i, label in enumerate(labels)
        if i % label_step == 0 or i == len(labels) - 1
    )
    circles = "\n".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#0f766e"/>' for x, y in points)
    body = f"""
{svg_text(width / 2, 28, title, 18, color="#0f172a")}
<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#cbd5e1"/>
<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#cbd5e1"/>
{svg_text(15, top + 8, f'{max_v:,.0f}', 11, 'start')}
{svg_text(15, top + plot_h, f'{min_v:,.0f}', 11, 'start')}
<path d="{path_d}" fill="none" stroke="#0f766e" stroke-width="3"/>
{circles}
{x_labels}
"""
    return write_svg(path, width, height, body)


def horizontal_bar(labels: list[str], values: list[float], title: str, path: Path, color: str = "#2563eb") -> str:
    width, height = 850, 410
    left, right, top, bottom = 120, 70, 55, 35
    plot_w, plot_h = width - left - right, height - top - bottom
    max_v = max(values) or 1
    gap = 12
    bar_h = (plot_h - gap * (len(values) - 1)) / len(values)
    parts = [svg_text(width / 2, 28, title, 18, color="#0f172a")]
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * (bar_h + gap)
        bar_w = value / max_v * plot_w
        parts.append(svg_text(left - 10, y + bar_h * 0.65, label, 12, "end"))
        parts.append(f'<rect x="{left}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}"/>')
        parts.append(svg_text(left + bar_w + 8, y + bar_h * 0.65, f"{value:,.0f}", 11, "start"))
    return write_svg(path, width, height, "\n".join(parts))


def vertical_bar(labels: list[str], values: list[int], title: str, path: Path) -> str:
    width, height = 760, 380
    left, right, top, bottom = 60, 30, 55, 70
    plot_w, plot_h = width - left - right, height - top - bottom
    max_v = max(values) or 1
    slot = plot_w / len(values)
    bar_w = slot * 0.62
    parts = [
        svg_text(width / 2, 28, title, 18, color="#0f172a"),
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#cbd5e1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#cbd5e1"/>',
    ]
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + i * slot + (slot - bar_w) / 2
        bar_h = value / max_v * plot_h
        y = top + plot_h - bar_h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="#7c3aed"/>')
        parts.append(svg_text(x + bar_w / 2, y - 6, value, 11))
        parts.append(svg_text(x + bar_w / 2, height - 34, label, 11))
    return write_svg(path, width, height, "\n".join(parts))


def donut_chart(labels: list[str], values: list[int], title: str, path: Path) -> str:
    width, height = 760, 410
    cx, cy, radius = 245, 220, 125
    total = sum(values)
    colors = ["#0f766e", "#2563eb", "#7c3aed", "#ea580c", "#be123c", "#64748b"]
    angle = -90
    parts = [svg_text(width / 2, 28, title, 18, color="#0f172a")]
    for i, (label, value) in enumerate(zip(labels, values)):
        sweep = 360 * value / total
        start = math.radians(angle)
        end = math.radians(angle + sweep)
        x1, y1 = cx + radius * math.cos(start), cy + radius * math.sin(start)
        x2, y2 = cx + radius * math.cos(end), cy + radius * math.sin(end)
        large = 1 if sweep > 180 else 0
        color = colors[i % len(colors)]
        d = f"M {cx} {cy} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large} 1 {x2:.1f} {y2:.1f} Z"
        parts.append(f'<path d="{d}" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
        angle += sweep
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="64" fill="#ffffff"/>')
    parts.append(svg_text(cx, cy, f"{total:,}", 22, color="#0f172a"))
    parts.append(svg_text(cx, cy + 24, "orders", 12))
    for i, (label, value) in enumerate(zip(labels, values)):
        y = 105 + i * 42
        color = colors[i % len(colors)]
        pct = value / total * 100
        parts.append(f'<rect x="465" y="{y - 13}" width="16" height="16" fill="{color}"/>')
        parts.append(svg_text(492, y, f"{label}: {value:,} ({pct:.1f}%)", 13, "start"))
    return write_svg(path, width, height, "\n".join(parts))


def html_table(df: pd.DataFrame, max_rows: int = 8) -> str:
    rows = []
    for _, row in df.head(max_rows).iterrows():
        cells = "".join(f"<td>{escape(str(row[column]))}</td>" for column in df.columns)
        rows.append(f"<tr>{cells}</tr>")
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in df.columns)
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_outputs(df: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in summaries.items():
        table.to_csv(OUTPUT_DIR / f"{name}_summary.csv", index=False)

    monthly = summaries["monthly"]
    product = summaries["product"]
    payment = summaries["payment"]
    status = summaries["status"]
    referral = summaries["referral"]

    charts = {
        "monthly": line_chart(monthly["YearMonth"].tolist(), monthly["TotalRevenue"].tolist(), "Monthly Revenue Trend", CHART_DIR / "monthly_revenue_trend.svg"),
        "product": horizontal_bar(product["Product"].tolist(), product["TotalRevenue"].tolist(), "Revenue by Product", CHART_DIR / "revenue_by_product.svg"),
        "status": donut_chart(status["OrderStatus"].tolist(), status["OrderCount"].tolist(), "Order Status Share", CHART_DIR / "order_status_share.svg"),
        "payment": vertical_bar(payment["PaymentMethod"].tolist(), payment["OrderCount"].tolist(), "Orders by Payment Method", CHART_DIR / "orders_by_payment_method.svg"),
        "referral": horizontal_bar(referral["ReferralSource"].tolist(), referral["TotalRevenue"].tolist(), "Revenue by Referral Source", CHART_DIR / "revenue_by_referral_source.svg", "#0f766e"),
    }

    best_month = monthly.loc[monthly["TotalRevenue"].idxmax()].to_dict()
    summary = {
        "rows": int(len(df)),
        "columns": int(len(df.columns) - 1),
        "date_start": str(df["Date"].min().date()),
        "date_end": str(df["Date"].max().date()),
        "total_revenue": round(float(df["TotalPrice"].sum()), 2),
        "total_orders": int(len(df)),
        "total_units_sold": int(df["Quantity"].sum()),
        "average_order_value": round(float(df["TotalPrice"].mean()), 2),
        "top_product": str(product.iloc[0]["Product"]),
        "top_product_revenue": float(product.iloc[0]["TotalRevenue"]),
        "top_payment_method": str(payment.iloc[0]["PaymentMethod"]),
        "top_referral_source": str(referral.iloc[0]["ReferralSource"]),
        "best_month": best_month,
        "chart_count": len(charts),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_dashboard(summary, summaries, charts)
    write_report(summary)
    return summary


def write_dashboard(summary: dict, summaries: dict[str, pd.DataFrame], charts: dict[str, str]) -> None:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Project 4 Data Visualization Dashboard</title>
  <style>
    :root {{
      --ink: #0f172a;
      --muted: #64748b;
      --line: #d8e0ea;
      --panel: #ffffff;
      --bg: #f6f8fb;
      --accent: #0f766e;
      --accent-2: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.45;
    }}
    header {{
      background: #0f172a;
      color: #ffffff;
      padding: 28px 36px;
    }}
    header h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    header p {{
      margin: 0;
      color: #cbd5e1;
      font-size: 15px;
    }}
    main {{
      width: min(1220px, calc(100vw - 32px));
      margin: 22px auto 36px;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .kpi, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .kpi span {{
      color: var(--muted);
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 8px;
    }}
    .kpi strong {{
      display: block;
      font-size: 24px;
      white-space: nowrap;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 14px;
      align-items: start;
    }}
    .full {{ grid-column: 1 / -1; }}
    .panel h2 {{
      margin: 0 0 12px;
      font-size: 17px;
    }}
    .insights {{
      margin: 0;
      padding-left: 18px;
      color: #334155;
    }}
    .insights li {{ margin: 8px 0; }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: left;
      white-space: nowrap;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .03em;
    }}
    @media (max-width: 900px) {{
      .kpis, .grid {{ grid-template-columns: 1fr; }}
      header {{ padding: 24px 18px; }}
      main {{ width: min(100vw - 20px, 1220px); }}
      .kpi strong {{ font-size: 21px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Data Visualization Dashboard</h1>
    <p>DecodeLabs Project 4 | Ecommerce order performance from {summary["date_start"]} to {summary["date_end"]}</p>
  </header>
  <main>
    <section class="kpis">
      <div class="kpi"><span>Total Revenue</span><strong>{money(summary["total_revenue"])}</strong></div>
      <div class="kpi"><span>Total Orders</span><strong>{summary["total_orders"]:,}</strong></div>
      <div class="kpi"><span>Average Order Value</span><strong>{money(summary["average_order_value"])}</strong></div>
      <div class="kpi"><span>Units Sold</span><strong>{summary["total_units_sold"]:,}</strong></div>
    </section>
    <section class="grid">
      <div class="panel full"><h2>Revenue Trend</h2>{charts["monthly"]}</div>
      <div class="panel"><h2>Product Revenue</h2>{charts["product"]}</div>
      <div class="panel"><h2>Key Insights</h2>
        <ol class="insights">
          <li><strong>{summary["top_product"]}</strong> is the top product by revenue at {money(summary["top_product_revenue"])}.</li>
          <li><strong>{summary["best_month"]["YearMonth"]}</strong> is the strongest revenue month at {money(summary["best_month"]["TotalRevenue"])}.</li>
          <li><strong>{summary["top_payment_method"]}</strong> is the most used payment method.</li>
          <li><strong>{summary["top_referral_source"]}</strong> is the strongest referral source by revenue.</li>
        </ol>
      </div>
      <div class="panel"><h2>Order Status Share</h2>{charts["status"]}</div>
      <div class="panel"><h2>Payment Methods</h2>{charts["payment"]}</div>
      <div class="panel full"><h2>Referral Source Revenue</h2>{charts["referral"]}</div>
      <div class="panel full"><h2>Product Summary</h2>{html_table(summaries["product"])}</div>
    </section>
  </main>
</body>
</html>
"""
    DASHBOARD_PATH.write_text(html, encoding="utf-8")


def write_report(summary: dict) -> None:
    report = f"""# Data Visualization Report

## Project

DecodeLabs Data Analytics Project 4: Data Visualization.

## Goal

Create visual representations of ecommerce order data to communicate insights clearly.

## Visuals Created

| Visual | Purpose |
| --- | --- |
| KPI cards | Show total revenue, orders, average order value, and units sold |
| Line chart | Show monthly revenue trend over time |
| Horizontal bar chart | Compare product revenue clearly |
| Donut chart | Show order status share |
| Vertical bar chart | Compare payment method order counts |
| Horizontal bar chart | Compare referral source revenue |

## Key Insights

1. Total revenue is {money(summary["total_revenue"])} across {summary["total_orders"]:,} orders.
2. Average order value is {money(summary["average_order_value"])}.
3. `{summary["top_product"]}` is the highest revenue product with {money(summary["top_product_revenue"])}.
4. `{summary["best_month"]["YearMonth"]}` is the strongest month with {money(summary["best_month"]["TotalRevenue"])} revenue.
5. `{summary["top_payment_method"]}` is the most used payment method.
6. `{summary["top_referral_source"]}` is the highest revenue referral source.

## Requirement Coverage

- Created multiple charts: line, bar, donut, and KPI cards.
- Chose visuals based on the question each chart answers.
- Highlighted key business insights in the dashboard and this report.

## Main Deliverable

Open `outputs/visualization_dashboard.html` to view the dashboard.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    df = load_dataset()
    summaries = summarize(df)
    summary = build_outputs(df, summaries)
    print("Project 4 data visualization complete.")
    print(f"Dashboard: {DASHBOARD_PATH}")
    print(f"Report: {REPORT_PATH}")
    print(f"Charts: {CHART_DIR}")
    print(f"Charts generated: {summary['chart_count']}")


if __name__ == "__main__":
    main()

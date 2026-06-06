# DecodeLabs Data Analytics Project 4

## Data Visualization

This project creates visual representations of ecommerce order data to communicate insights clearly. It includes a static HTML dashboard, SVG charts, summary tables, and a short visualization report.

## Project Requirements

- Create charts such as bar, line, and pie/donut charts.
- Choose appropriate visuals for the data.
- Highlight key insights.

## Dataset

The raw dataset is stored at:

`data/raw_dataset.xlsx`

## Tools Used

- Python
- Pandas
- Excel
- HTML/CSS
- SVG charts

## Visuals Created

1. KPI cards for revenue, orders, average order value, and units sold.
2. Line chart for monthly revenue trend.
3. Horizontal bar chart for revenue by product.
4. Donut chart for order status share.
5. Vertical bar chart for payment method order count.
6. Horizontal bar chart for revenue by referral source.

## How to Run

Install the required Python packages:

```bash
pip install pandas openpyxl
```

Run the dashboard builder:

```bash
python visualization_dashboard.py
```

## Output Files

Generated files are saved in the `outputs` folder:

- `visualization_dashboard.html`
- `visualization_report.md`
- `dashboard_summary.json`
- `monthly_summary.csv`
- `product_summary.csv`
- `payment_summary.csv`
- `status_summary.csv`
- `referral_summary.csv`
- `charts/*.svg`

## Main Deliverable

Open this file in a browser:

`outputs/visualization_dashboard.html`

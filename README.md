# Corporate Financial Modeling Pro

**Corporate Financial Modeling Pro** is a Python-based interactive financial planning and valuation application built with **Streamlit**, **Pandas**, and **NumPy**. It provides a structured environment for building multi-year corporate projections, monthly budgets, forecast-versus-actual analysis, debt and cash flow tracking, simplified balance sheet views, discounted cash flow valuation, sensitivity analysis, and automated expense allocation.

The tool is designed for users who need a practical and extensible financial model that goes beyond basic spreadsheets, while still remaining accessible through an intuitive web interface.

---

## Overview

This application allows users to define a company’s financial assumptions, project operating performance over a selected time horizon, analyze free cash flow generation, estimate enterprise and equity value through a DCF framework, and export the full model to Excel.

In addition to long-term financial modeling, the application includes operational budgeting features such as monthly seasonality-based allocation, editable forecast-versus-actual comparisons, and automatic expense bucket distribution for predefined spending categories.

---

## Key Features

- **Multi-year annual financial model**
  - Revenue growth projections
  - Cost of goods sold
  - Operating expense modeling
  - EBITDA, EBIT, EBT, taxes, and net income
  - Free cash flow generation

- **Scenario analysis**
  - Base
  - Upside
  - Downside

- **Debt and cash management**
  - Opening and closing debt balances
  - Interest expense
  - Debt amortization
  - Opening and ending cash tracking

- **Simplified balance sheet logic**
  - Net working capital
  - Net PP&E
  - Total assets
  - Equity

- **DCF valuation**
  - Discounted free cash flow
  - Terminal value
  - Enterprise value
  - Equity value
  - Implied value per share

- **Monthly budgeting**
  - Seasonality-based distribution of annual metrics
  - Editable monthly weights
  - Revenue, EBITDA, and FCF monthly views

- **Forecast vs actual analysis**
  - Editable actuals table
  - Variance by metric and month
  - Aggregate variance summaries

- **Expense allocation engine**
  - Configurable expense buckets
  - Optional automatic normalization to 100%
  - Allocation by category and amount

- **Excel export**
  - Full model export to a structured multi-sheet workbook

- **Interactive dashboard**
  - KPI cards
  - Line charts
  - Bar charts
  - Tabbed navigation for model exploration

---

## Technology Stack

- **Python**
- **Streamlit**
- **Pandas**
- **NumPy**
- **openpyxl**

---

## Financial Modules Included

### 1. Annual Projection Engine
The annual model is driven by a centralized input structure using a `dataclass`, allowing the application to capture core operating, capital, tax, debt, and valuation assumptions in a clean and reusable way.

The annual model includes:

- Revenue forecast
- Gross profit
- Operating expense build-up
- EBITDA and EBIT
- Interest and tax calculations
- Net income
- NOPAT
- Capex
- Net working capital
- Delta NWC
- Free cash flow

### 2. Debt and Liquidity Tracking
The model tracks:

- Opening debt
- Annual debt amortization
- Closing debt
- Interest expense
- Opening cash
- Ending cash

This makes the model more useful for practical planning scenarios where leverage and liquidity materially affect valuation and operating flexibility.

### 3. Simplified Balance Sheet
The application derives a simplified balance sheet using:

- Ending cash
- Net working capital
- Net PP&E
- Total assets
- Debt
- Equity

### 4. DCF Valuation and Sensitivity Analysis
The valuation layer discounts projected free cash flows using a user-defined WACC and estimates terminal value using a perpetual growth approach. The application then derives:

- Enterprise value
- Equity value
- Value per share

A sensitivity matrix is also generated across a grid of WACC and terminal growth assumptions.

### 5. Monthly Budgeting and Variance Analysis
Users can select a year from the annual model and convert it into a monthly budget using configurable seasonality weights. The app also creates a default actuals table and allows the user to edit real results directly in the interface, producing:

- Metric-level variances
- Variance percentages
- Forecast vs actual comparisons by month

### 6. Automated Expense Allocation
The tool includes a dedicated expense allocation module where a total amount can be distributed across categories such as payroll, operations, marketing, technology, administration, rent and utilities, logistics, taxes, and reserves.

---

## Default Expense Categories

The application currently includes the following predefined buckets:

- Payroll
- Operations
- Marketing
- Technology
- Administration
- Rent and Utilities
- Logistics
- Taxes
- Reserve

These buckets can be adjusted directly in the sidebar through percentage sliders.

---

## Exported Excel Workbook

The generated Excel file contains the following sheets:

- `00_Control`
- `01_Assumptions`
- `02_Annual_Model`
- `03_Monthly_Budget`
- `04_Expense_Buckets`
- `05_Forecast_vs_Actual`
- `06_DCF_Sensitivity`
- `07_Summary`

---

## Installation

Clone the repository and install the required dependencies.

```bash
git clone https://github.com/your-username/your-repository.git
cd your-repository
pip install -r requirements.txt
```

A minimal `requirements.txt` may include:

```txt
streamlit
pandas
numpy
openpyxl
```

---

## Running the Application

Launch the Streamlit app with:

```bash
streamlit run app.py
```

Replace `app.py` with the actual filename used in your project.

---

## How to Use

1. Open the sidebar and enter the company control settings:
   - Company name
   - Currency
   - Start year
   - Projection horizon
   - Scenario

2. Define operating assumptions:
   - Revenue
   - Growth rate
   - COGS
   - Sales expense
   - Marketing
   - Administration
   - R&D
   - Depreciation
   - Tax rate
   - Capex
   - Net working capital

3. Define capital structure assumptions:
   - Initial cash
   - Initial debt
   - Interest rate
   - Debt amortization

4. Define valuation assumptions:
   - WACC
   - Terminal growth
   - Shares outstanding

5. Configure the expense allocation section:
   - Total amount to distribute
   - Bucket percentages
   - Optional automatic normalization

6. Select a projected year for monthly budgeting and forecast-versus-actual analysis.

7. Review the outputs across the application tabs:
   - Summary
   - Annual Model
   - Monthly Budget
   - Forecast vs Actual
   - Expense Buckets
   - DCF Sensitivity

8. Export the complete model to Excel.

---

## Application Structure

The application is organized around a set of cached helper functions that keep the interface responsive and the modeling logic modular. Key functions include:

- `build_annual_model()`
- `build_monthly_budget()`
- `build_expense_buckets()`
- `default_actuals_from_budget()`
- `build_variance_table()`
- `build_sensitivity_table()`
- `build_summary()`
- `export_excel()`

---

## Design Philosophy

This project was built with the following principles in mind:

- **Practicality**: useful in real business planning and valuation scenarios
- **Transparency**: calculations remain structured and inspectable
- **Interactivity**: assumptions can be modified in real time
- **Extensibility**: the codebase can be expanded with new scenarios, dashboards, metrics, and export formats
- **Accessibility**: financial modeling capabilities are exposed through a simple browser-based interface

---

## Potential Enhancements

Future versions could include:

- Multi-company comparison mode
- Additional valuation methods
- Working capital detail by component
- Advanced debt schedules
- Budget approval workflows
- Authentication and multi-user access
- Database-backed storage
- PDF reporting
- Scenario persistence
- API integration for live financial data

---

## Use Cases

This project can be adapted for:

- Corporate finance teams
- FP&A workflows
- Startup planning
- Internal budgeting
- Valuation exercises
- Business case development
- Financial modeling portfolios
- Python and Streamlit project demonstrations

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
---

## Author

**Emilio Barradas Martínez**  
Software Developer | Systems Integration | APIs | Automation | DevOps / Cloud

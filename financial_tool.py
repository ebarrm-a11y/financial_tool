import io
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="Herramienta Financiera Corporativa", layout="wide")


SCENARIO_PRESETS = {
    "Base": {"growth_delta": 0.0, "margin_delta": 0.0, "wacc_delta": 0.0},
    "Upside": {"growth_delta": 0.03, "margin_delta": -0.02, "wacc_delta": -0.01},
    "Downside": {"growth_delta": -0.03, "margin_delta": 0.02, "wacc_delta": 0.015},
}


def pct(value: float) -> str:
    return f"{value:.1%}"


def money(value: float, currency: str) -> str:
    return f"{currency} {value:,.0f}"


@dataclass
class ModelInputs:
    company_name: str
    currency: str
    start_year: int
    horizon: int
    scenario: str
    revenue_0: float
    growth_rate: float
    cogs_pct: float
    sales_pct: float
    marketing_pct: float
    admin_pct: float
    rd_pct: float
    depreciation_pct: float
    tax_rate: float
    capex_pct: float
    nwc_pct: float
    initial_cash: float
    initial_debt: float
    wacc: float
    terminal_growth: float
    shares_outstanding: float
    expense_total: float
    expense_percentages: Dict[str, float]


DEFAULT_BUCKETS = {
    "Nómina": 0.25,
    "Operación": 0.20,
    "Marketing": 0.10,
    "Tecnología": 0.10,
    "Administración": 0.10,
    "Renta/Servicios": 0.10,
    "Impuestos": 0.10,
    "Reserva": 0.05,
}


@st.cache_data(show_spinner=False)
def build_projection(inputs: ModelInputs) -> pd.DataFrame:
    scenario_adj = SCENARIO_PRESETS[inputs.scenario]
    years = list(range(inputs.start_year, inputs.start_year + inputs.horizon + 1))

    growth_rate = max(-0.95, inputs.growth_rate + scenario_adj["growth_delta"])
    cogs_pct = min(0.99, max(0.0, inputs.cogs_pct + scenario_adj["margin_delta"]))
    sales_pct = min(0.99, max(0.0, inputs.sales_pct + scenario_adj["margin_delta"] / 2))
    marketing_pct = min(0.99, max(0.0, inputs.marketing_pct + scenario_adj["margin_delta"] / 2))
    admin_pct = min(0.99, max(0.0, inputs.admin_pct + scenario_adj["margin_delta"] / 2))
    rd_pct = min(0.99, max(0.0, inputs.rd_pct + scenario_adj["margin_delta"] / 2))
    wacc = max(0.001, inputs.wacc + scenario_adj["wacc_delta"])

    revenue = [inputs.revenue_0]
    for _ in range(inputs.horizon):
        revenue.append(revenue[-1] * (1 + growth_rate))

    df = pd.DataFrame({"Year": years, "Revenue": revenue})
    df["Growth"] = df["Revenue"].pct_change().fillna(0.0)
    df["COGS"] = df["Revenue"] * cogs_pct
    df["Gross Profit"] = df["Revenue"] - df["COGS"]
    df["Sales"] = df["Revenue"] * sales_pct
    df["Marketing"] = df["Revenue"] * marketing_pct
    df["Admin"] = df["Revenue"] * admin_pct
    df["R&D"] = df["Revenue"] * rd_pct
    df["OPEX"] = df[["Sales", "Marketing", "Admin", "R&D"]].sum(axis=1)
    df["EBITDA"] = df["Gross Profit"] - df["OPEX"]
    df["Depreciation"] = df["Revenue"] * inputs.depreciation_pct
    df["EBIT"] = df["EBITDA"] - df["Depreciation"]
    df["Taxes"] = np.where(df["EBIT"] > 0, df["EBIT"] * inputs.tax_rate, 0.0)
    df["NOPAT"] = df["EBIT"] - df["Taxes"]
    df["Capex"] = df["Revenue"] * inputs.capex_pct
    df["NWC"] = df["Revenue"] * inputs.nwc_pct
    df["Delta NWC"] = df["NWC"].diff().fillna(df["NWC"])
    df["FCF"] = df["NOPAT"] + df["Depreciation"] - df["Capex"] - df["Delta NWC"]
    df["Gross Margin"] = np.where(df["Revenue"] != 0, df["Gross Profit"] / df["Revenue"], 0.0)
    df["EBITDA Margin"] = np.where(df["Revenue"] != 0, df["EBITDA"] / df["Revenue"], 0.0)
    df["EBIT Margin"] = np.where(df["Revenue"] != 0, df["EBIT"] / df["Revenue"], 0.0)
    df["FCF Margin"] = np.where(df["Revenue"] != 0, df["FCF"] / df["Revenue"], 0.0)

    periods = np.arange(0, len(df))
    df["Discount Factor"] = 1 / ((1 + wacc) ** periods)
    df["PV of FCF"] = df["FCF"] * df["Discount Factor"]

    terminal_fcf = df.iloc[-1]["FCF"] * (1 + inputs.terminal_growth)
    terminal_value = terminal_fcf / max(0.001, (wacc - inputs.terminal_growth))
    pv_terminal = terminal_value * df.iloc[-1]["Discount Factor"]
    enterprise_value = df["PV of FCF"].sum() + pv_terminal
    equity_value = enterprise_value + inputs.initial_cash - inputs.initial_debt
    value_per_share = equity_value / inputs.shares_outstanding if inputs.shares_outstanding > 0 else np.nan

    df.attrs["wacc"] = wacc
    df.attrs["terminal_value"] = terminal_value
    df.attrs["pv_terminal"] = pv_terminal
    df.attrs["enterprise_value"] = enterprise_value
    df.attrs["equity_value"] = equity_value
    df.attrs["value_per_share"] = value_per_share

    return df


@st.cache_data(show_spinner=False)
def build_expense_buckets(total_amount: float, percentages: Dict[str, float]) -> pd.DataFrame:
    bucket_df = pd.DataFrame(
        {
            "Category": list(percentages.keys()),
            "Percentage": list(percentages.values()),
        }
    )
    bucket_df["Amount"] = total_amount * bucket_df["Percentage"]
    return bucket_df


@st.cache_data(show_spinner=False)
def export_excel(control_df: pd.DataFrame, assumptions_df: pd.DataFrame, projection_df: pd.DataFrame, expense_df: pd.DataFrame, summary_df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        control_df.to_excel(writer, sheet_name="00_Control", index=False)
        assumptions_df.to_excel(writer, sheet_name="01_Inputs", index=False)
        projection_df.to_excel(writer, sheet_name="02_Projection", index=False)
        projection_df[[
            "Year",
            "Revenue",
            "EBITDA",
            "EBIT",
            "Taxes",
            "Depreciation",
            "Capex",
            "Delta NWC",
            "FCF",
            "PV of FCF",
        ]].to_excel(writer, sheet_name="03_CashFlow", index=False)
        expense_df.to_excel(writer, sheet_name="04_Expense_Buckets", index=False)
        summary_df.to_excel(writer, sheet_name="05_Dashboard", index=False)
    output.seek(0)
    return output.getvalue()


st.title("Herramienta Financiera Corporativa")
st.caption("Modelo financiero en Python con proyecciones, escenarios, DCF, apartados automáticos de gasto y exportación a Excel.")

with st.sidebar:
    st.header("Control")
    company_name = st.text_input("Empresa", value="Mi Empresa")
    currency = st.selectbox("Moneda", ["MXN", "USD", "EUR"], index=0)
    start_year = st.number_input("Año inicial", min_value=2020, max_value=2100, value=2026, step=1)
    horizon = st.slider("Horizonte (años)", min_value=3, max_value=15, value=10)
    scenario = st.selectbox("Escenario", list(SCENARIO_PRESETS.keys()), index=0)

    st.header("Supuestos operativos")
    revenue_0 = st.number_input("Ingresos FY0", min_value=0.0, value=50_000_000.0, step=1_000_000.0, format="%.2f")
    growth_rate = st.slider("Crecimiento anual", min_value=-0.2, max_value=0.5, value=0.12, step=0.01)
    cogs_pct = st.slider("COGS % ventas", min_value=0.0, max_value=0.95, value=0.45, step=0.01)
    sales_pct = st.slider("Ventas % ventas", min_value=0.0, max_value=0.40, value=0.08, step=0.01)
    marketing_pct = st.slider("Marketing % ventas", min_value=0.0, max_value=0.30, value=0.06, step=0.01)
    admin_pct = st.slider("Administración % ventas", min_value=0.0, max_value=0.30, value=0.07, step=0.01)
    rd_pct = st.slider("I+D % ventas", min_value=0.0, max_value=0.30, value=0.04, step=0.01)
    depreciation_pct = st.slider("Depreciación % ventas", min_value=0.0, max_value=0.20, value=0.03, step=0.005)
    tax_rate = st.slider("Tasa fiscal", min_value=0.0, max_value=0.50, value=0.30, step=0.01)
    capex_pct = st.slider("Capex % ventas", min_value=0.0, max_value=0.30, value=0.05, step=0.01)
    nwc_pct = st.slider("NWC % ventas", min_value=0.0, max_value=0.40, value=0.10, step=0.01)

    st.header("Valuación")
    initial_cash = st.number_input("Caja inicial", min_value=0.0, value=5_000_000.0, step=500_000.0, format="%.2f")
    initial_debt = st.number_input("Deuda inicial", min_value=0.0, value=12_000_000.0, step=500_000.0, format="%.2f")
    wacc = st.slider("WACC", min_value=0.01, max_value=0.30, value=0.12, step=0.005)
    terminal_growth = st.slider("Crecimiento terminal", min_value=0.0, max_value=0.08, value=0.03, step=0.005)
    shares_outstanding = st.number_input("Acciones en circulación", min_value=0.0, value=1_000_000.0, step=100_000.0, format="%.2f")

    st.header("Apartados de gasto")
    expense_total = st.number_input("Monto total a repartir", min_value=0.0, value=1_000_000.0, step=50_000.0, format="%.2f")
    expense_percentages: Dict[str, float] = {}
    for category, default_value in DEFAULT_BUCKETS.items():
        expense_percentages[category] = st.slider(f"{category} %", min_value=0.0, max_value=1.0, value=float(default_value), step=0.01)

inputs = ModelInputs(
    company_name=company_name,
    currency=currency,
    start_year=int(start_year),
    horizon=int(horizon),
    scenario=scenario,
    revenue_0=float(revenue_0),
    growth_rate=float(growth_rate),
    cogs_pct=float(cogs_pct),
    sales_pct=float(sales_pct),
    marketing_pct=float(marketing_pct),
    admin_pct=float(admin_pct),
    rd_pct=float(rd_pct),
    depreciation_pct=float(depreciation_pct),
    tax_rate=float(tax_rate),
    capex_pct=float(capex_pct),
    nwc_pct=float(nwc_pct),
    initial_cash=float(initial_cash),
    initial_debt=float(initial_debt),
    wacc=float(wacc),
    terminal_growth=float(terminal_growth),
    shares_outstanding=float(shares_outstanding),
    expense_total=float(expense_total),
    expense_percentages=expense_percentages,
)

projection_df = build_projection(inputs)
expense_df = build_expense_buckets(inputs.expense_total, inputs.expense_percentages)
expense_sum = expense_df["Percentage"].sum()

control_df = pd.DataFrame(
    {
        "Field": ["Empresa", "Moneda", "Año inicial", "Horizonte", "Escenario", "Caja inicial", "Deuda inicial"],
        "Value": [
            inputs.company_name,
            inputs.currency,
            inputs.start_year,
            inputs.horizon,
            inputs.scenario,
            inputs.initial_cash,
            inputs.initial_debt,
        ],
    }
)

assumptions_df = pd.DataFrame(
    {
        "Assumption": [
            "Revenue FY0",
            "Growth rate",
            "COGS %",
            "Sales %",
            "Marketing %",
            "Admin %",
            "R&D %",
            "Depreciation %",
            "Tax rate",
            "Capex %",
            "NWC %",
            "WACC",
            "Terminal growth",
            "Shares outstanding",
        ],
        "Value": [
            inputs.revenue_0,
            inputs.growth_rate,
            inputs.cogs_pct,
            inputs.sales_pct,
            inputs.marketing_pct,
            inputs.admin_pct,
            inputs.rd_pct,
            inputs.depreciation_pct,
            inputs.tax_rate,
            inputs.capex_pct,
            inputs.nwc_pct,
            inputs.wacc,
            inputs.terminal_growth,
            inputs.shares_outstanding,
        ],
    }
)

summary_df = pd.DataFrame(
    {
        "Metric": [
            "WACC ajustado",
            "Terminal Value",
            "PV Terminal Value",
            "Enterprise Value",
            "Equity Value",
            "Value per Share",
            "Expense % Sum",
        ],
        "Value": [
            projection_df.attrs["wacc"],
            projection_df.attrs["terminal_value"],
            projection_df.attrs["pv_terminal"],
            projection_df.attrs["enterprise_value"],
            projection_df.attrs["equity_value"],
            projection_df.attrs["value_per_share"],
            expense_sum,
        ],
    }
)

excel_data = export_excel(control_df, assumptions_df, projection_df, expense_df, summary_df)

last_row = projection_df.iloc[-1]
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Ingresos último año", money(last_row["Revenue"], currency))
col2.metric("EBITDA último año", money(last_row["EBITDA"], currency), pct(last_row["EBITDA Margin"]))
col3.metric("FCF último año", money(last_row["FCF"], currency), pct(last_row["FCF Margin"]))
col4.metric("Enterprise Value", money(projection_df.attrs["enterprise_value"], currency))
col5.metric("Equity Value / Acción", money(projection_df.attrs["value_per_share"], currency) if pd.notna(projection_df.attrs["value_per_share"]) else "N/A")

if not np.isclose(expense_sum, 1.0, atol=0.001):
    st.warning(f"Los porcentajes de apartados suman {expense_sum:.1%}. Ajusta hasta llegar a 100%.")
else:
    st.success("Los apartados de gasto suman exactamente 100%.")

projection_tab, cashflow_tab, expense_tab, dashboard_tab, export_tab = st.tabs(
    ["Proyección", "Flujo de caja", "Apartados de gasto", "Dashboard", "Exportar"]
)

with projection_tab:
    show_projection = projection_df[[
        "Year",
        "Revenue",
        "Growth",
        "COGS",
        "Gross Profit",
        "Sales",
        "Marketing",
        "Admin",
        "R&D",
        "OPEX",
        "EBITDA",
        "Depreciation",
        "EBIT",
        "Taxes",
        "NOPAT",
        "Gross Margin",
        "EBITDA Margin",
        "EBIT Margin",
    ]].copy()
    st.dataframe(show_projection, use_container_width=True)

with cashflow_tab:
    show_cashflow = projection_df[[
        "Year",
        "Revenue",
        "Capex",
        "NWC",
        "Delta NWC",
        "Depreciation",
        "NOPAT",
        "FCF",
        "Discount Factor",
        "PV of FCF",
    ]].copy()
    st.dataframe(show_cashflow, use_container_width=True)

with expense_tab:
    expense_display = expense_df.copy()
    expense_display["Percentage"] = expense_display["Percentage"].map(lambda x: f"{x:.1%}")
    st.dataframe(expense_display, use_container_width=True)
    st.bar_chart(expense_df.set_index("Category")["Amount"])

with dashboard_tab:
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.subheader("Ingresos y EBITDA")
        st.line_chart(projection_df.set_index("Year")[["Revenue", "EBITDA"]])
        st.subheader("FCF")
        st.bar_chart(projection_df.set_index("Year")[["FCF"]])
    with chart_right:
        st.subheader("Márgenes")
        st.line_chart(projection_df.set_index("Year")[["Gross Margin", "EBITDA Margin", "EBIT Margin", "FCF Margin"]])
        st.subheader("Composición OPEX")
        opex_mix = projection_df.iloc[-1][["Sales", "Marketing", "Admin", "R&D"]]
        st.bar_chart(opex_mix)

    valuation_col1, valuation_col2, valuation_col3 = st.columns(3)
    valuation_col1.metric("WACC ajustado", pct(projection_df.attrs["wacc"]))
    valuation_col2.metric("Terminal Value", money(projection_df.attrs["terminal_value"], currency))
    valuation_col3.metric("PV Terminal Value", money(projection_df.attrs["pv_terminal"], currency))

with export_tab:
    st.subheader("Descarga")
    st.download_button(
        label="Descargar Excel del modelo",
        data=excel_data,
        file_name=f"modelo_financiero_{company_name.lower().replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.code("streamlit run financial_tool.py", language="bash")
    st.caption("Recomendado para análisis interactivo, escenarios y exportación a Excel.")

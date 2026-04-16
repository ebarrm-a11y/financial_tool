import io
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Herramienta Financiera Corporativa Pro", layout="wide")

SCENARIO_PRESETS = {
    "Base": {"growth_delta": 0.00, "cost_delta": 0.00, "wacc_delta": 0.000},
    "Upside": {"growth_delta": 0.03, "cost_delta": -0.02, "wacc_delta": -0.010},
    "Downside": {"growth_delta": -0.03, "cost_delta": 0.02, "wacc_delta": 0.015},
}

DEFAULT_BUCKETS = {
    "Nómina": 0.24,
    "Operación": 0.16,
    "Marketing": 0.10,
    "Tecnología": 0.10,
    "Administración": 0.10,
    "Renta y servicios": 0.08,
    "Logística": 0.07,
    "Impuestos": 0.10,
    "Reserva": 0.05,
}

DEFAULT_MONTH_WEIGHTS = np.array([0.07, 0.07, 0.08, 0.08, 0.08, 0.08, 0.09, 0.09, 0.09, 0.10, 0.08, 0.09])
DEFAULT_MONTH_WEIGHTS = DEFAULT_MONTH_WEIGHTS / DEFAULT_MONTH_WEIGHTS.sum()
MONTHS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
]


def pct(value: float) -> str:
    return f"{value:.1%}"


def money(value: float, currency: str) -> str:
    return f"{currency} {value:,.0f}"


@dataclass
class CorporateInputs:
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
    interest_rate: float
    amortization_pct: float
    wacc: float
    terminal_growth: float
    shares_outstanding: float
    expense_total: float
    expense_percentages: Dict[str, float]


@st.cache_data(show_spinner=False)
def normalize_weights(weights: List[float]) -> np.ndarray:
    arr = np.array(weights, dtype=float)
    total = arr.sum()
    if total <= 0:
        return DEFAULT_MONTH_WEIGHTS.copy()
    return arr / total


@st.cache_data(show_spinner=False)
def build_annual_model(inputs: CorporateInputs) -> pd.DataFrame:
    adj = SCENARIO_PRESETS[inputs.scenario]
    years = list(range(inputs.start_year, inputs.start_year + inputs.horizon + 1))

    growth_rate = max(-0.90, inputs.growth_rate + adj["growth_delta"])
    cogs_pct = min(0.99, max(0.0, inputs.cogs_pct + adj["cost_delta"]))
    sales_pct = min(0.99, max(0.0, inputs.sales_pct + adj["cost_delta"] / 3))
    marketing_pct = min(0.99, max(0.0, inputs.marketing_pct + adj["cost_delta"] / 3))
    admin_pct = min(0.99, max(0.0, inputs.admin_pct + adj["cost_delta"] / 3))
    rd_pct = min(0.99, max(0.0, inputs.rd_pct + adj["cost_delta"] / 3))
    wacc = max(0.001, inputs.wacc + adj["wacc_delta"])

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

    opening_debt = []
    debt_amort = []
    closing_debt = []
    debt_balance = inputs.initial_debt
    for i in range(len(df)):
        opening_debt.append(debt_balance)
        amort = min(debt_balance, debt_balance * inputs.amortization_pct if i > 0 else 0.0)
        debt_amort.append(amort)
        debt_balance = max(0.0, debt_balance - amort)
        closing_debt.append(debt_balance)

    df["Opening Debt"] = opening_debt
    df["Interest Expense"] = df["Opening Debt"] * inputs.interest_rate
    df["EBT"] = df["EBIT"] - df["Interest Expense"]
    df["Taxes"] = np.where(df["EBT"] > 0, df["EBT"] * inputs.tax_rate, 0.0)
    df["Net Income"] = df["EBT"] - df["Taxes"]
    df["NOPAT"] = np.where(df["EBIT"] > 0, df["EBIT"] * (1 - inputs.tax_rate), df["EBIT"])
    df["Capex"] = df["Revenue"] * inputs.capex_pct
    df["NWC"] = df["Revenue"] * inputs.nwc_pct
    df["Delta NWC"] = df["NWC"].diff().fillna(df["NWC"])
    df["FCF"] = df["NOPAT"] + df["Depreciation"] - df["Capex"] - df["Delta NWC"]
    df["Debt Amortization"] = debt_amort
    df["Closing Debt"] = closing_debt

    ending_cash = []
    cash_balance = inputs.initial_cash
    for i, row in df.iterrows():
        financing_outflow = row["Interest Expense"] + row["Debt Amortization"]
        cash_balance = cash_balance + row["FCF"] - financing_outflow
        ending_cash.append(cash_balance)
    df["Ending Cash"] = ending_cash
    df["Opening Cash"] = [inputs.initial_cash] + ending_cash[:-1]

    net_ppe = []
    ppe_balance = 0.0
    for _, row in df.iterrows():
        ppe_balance = ppe_balance + row["Capex"] - row["Depreciation"]
        net_ppe.append(max(0.0, ppe_balance))
    df["Net PP&E"] = net_ppe

    df["Total Assets"] = df["Ending Cash"] + df["NWC"] + df["Net PP&E"]
    df["Equity"] = df["Total Assets"] - df["Closing Debt"]

    df["Gross Margin"] = np.where(df["Revenue"] != 0, df["Gross Profit"] / df["Revenue"], 0.0)
    df["EBITDA Margin"] = np.where(df["Revenue"] != 0, df["EBITDA"] / df["Revenue"], 0.0)
    df["EBIT Margin"] = np.where(df["Revenue"] != 0, df["EBIT"] / df["Revenue"], 0.0)
    df["Net Margin"] = np.where(df["Revenue"] != 0, df["Net Income"] / df["Revenue"], 0.0)
    df["FCF Margin"] = np.where(df["Revenue"] != 0, df["FCF"] / df["Revenue"], 0.0)

    periods = np.arange(0, len(df))
    df["Discount Factor"] = 1 / ((1 + wacc) ** periods)
    df["PV of FCF"] = df["FCF"] * df["Discount Factor"]

    terminal_fcf = df.iloc[-1]["FCF"] * (1 + inputs.terminal_growth)
    terminal_value = terminal_fcf / max(0.001, (wacc - inputs.terminal_growth))
    pv_terminal = terminal_value * df.iloc[-1]["Discount Factor"]
    enterprise_value = df["PV of FCF"].sum() + pv_terminal
    equity_value = enterprise_value + df.iloc[-1]["Ending Cash"] - df.iloc[-1]["Closing Debt"]
    value_per_share = equity_value / inputs.shares_outstanding if inputs.shares_outstanding > 0 else np.nan

    df.attrs["effective_wacc"] = wacc
    df.attrs["terminal_value"] = terminal_value
    df.attrs["pv_terminal"] = pv_terminal
    df.attrs["enterprise_value"] = enterprise_value
    df.attrs["equity_value"] = equity_value
    df.attrs["value_per_share"] = value_per_share

    return df


@st.cache_data(show_spinner=False)
def build_monthly_budget(year_value: int, annual_row: pd.Series, month_weights: List[float]) -> pd.DataFrame:
    weights = normalize_weights(month_weights)
    df = pd.DataFrame({"Mes": MONTHS, "Peso": weights})
    for metric in [
        "Revenue", "COGS", "Gross Profit", "Sales", "Marketing", "Admin", "R&D",
        "OPEX", "EBITDA", "Depreciation", "EBIT", "Taxes", "Net Income", "Capex", "FCF"
    ]:
        df[metric] = annual_row[metric] * df["Peso"]
    df.insert(0, "Año", year_value)
    return df


@st.cache_data(show_spinner=False)
def build_expense_buckets(total_amount: float, percentages: Dict[str, float], normalize: bool) -> pd.DataFrame:
    data = pd.DataFrame({
        "Category": list(percentages.keys()),
        "Percentage": list(percentages.values()),
    })
    if normalize and data["Percentage"].sum() > 0:
        data["Percentage"] = data["Percentage"] / data["Percentage"].sum()
    data["Amount"] = total_amount * data["Percentage"]
    return data


@st.cache_data(show_spinner=False)
def default_actuals_from_budget(monthly_budget: pd.DataFrame) -> pd.DataFrame:
    actuals = monthly_budget[["Mes", "Revenue", "COGS", "OPEX", "EBITDA", "Capex", "FCF"]].copy()
    actuals["Revenue"] *= 0.97
    actuals["COGS"] *= 1.01
    actuals["OPEX"] *= 1.03
    actuals["EBITDA"] = actuals["Revenue"] - actuals["COGS"] - actuals["OPEX"]
    actuals["Capex"] *= 0.95
    actuals["FCF"] = actuals["EBITDA"] - actuals["Capex"]
    return actuals.round(2)


@st.cache_data(show_spinner=False)
def build_variance_table(monthly_budget: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    forecast = monthly_budget[["Mes", "Revenue", "COGS", "OPEX", "EBITDA", "Capex", "FCF"]].copy()
    merged = forecast.merge(actuals, on="Mes", suffixes=("_Forecast", "_Actual"))
    rows = []
    for metric in ["Revenue", "COGS", "OPEX", "EBITDA", "Capex", "FCF"]:
        temp = pd.DataFrame({
            "Mes": merged["Mes"],
            "Metric": metric,
            "Forecast": merged[f"{metric}_Forecast"],
            "Actual": merged[f"{metric}_Actual"],
        })
        temp["Variance"] = temp["Actual"] - temp["Forecast"]
        temp["Variance %"] = np.where(temp["Forecast"] != 0, temp["Variance"] / temp["Forecast"], 0.0)
        rows.append(temp)
    return pd.concat(rows, ignore_index=True)


@st.cache_data(show_spinner=False)
def dcf_value_from_last_row(last_row: pd.Series, wacc: float, terminal_growth: float) -> float:
    terminal_fcf = last_row["FCF"] * (1 + terminal_growth)
    terminal_value = terminal_fcf / max(0.001, wacc - terminal_growth)
    return terminal_value


@st.cache_data(show_spinner=False)
def build_sensitivity_table(annual_df: pd.DataFrame, effective_wacc: float, terminal_growth: float) -> pd.DataFrame:
    wacc_grid = np.round(np.linspace(max(0.03, effective_wacc - 0.02), effective_wacc + 0.02, 5), 4)
    tg_grid = np.round(np.linspace(max(0.0, terminal_growth - 0.02), terminal_growth + 0.02, 5), 4)
    last_row = annual_df.iloc[-1]
    pv_fcf_sum = annual_df["PV of FCF"].sum()
    terminal_discount_factor = annual_df.iloc[-1]["Discount Factor"]

    data = []
    for tg in tg_grid:
        row = []
        for w in wacc_grid:
            tv = dcf_value_from_last_row(last_row, w, tg)
            ev = pv_fcf_sum + tv * terminal_discount_factor
            row.append(ev)
        data.append(row)

    sensitivity = pd.DataFrame(data, index=[f"g={x:.1%}" for x in tg_grid], columns=[f"WACC={x:.1%}" for x in wacc_grid])
    return sensitivity


@st.cache_data(show_spinner=False)
def build_summary(annual_df: pd.DataFrame, currency: str) -> pd.DataFrame:
    first_row = annual_df.iloc[0]
    last_row = annual_df.iloc[-1]
    revenue_cagr = (last_row["Revenue"] / first_row["Revenue"]) ** (1 / max(1, len(annual_df) - 1)) - 1 if first_row["Revenue"] > 0 else 0.0
    summary = pd.DataFrame({
        "KPI": [
            "Ingresos FY0",
            "Ingresos último año",
            "Revenue CAGR",
            "EBITDA margen último año",
            "Margen neto último año",
            "FCF último año",
            "Caja final",
            "Deuda final",
            "Enterprise Value",
            "Equity Value",
            "Valor por acción",
        ],
        "Valor": [
            money(first_row["Revenue"], currency),
            money(last_row["Revenue"], currency),
            pct(revenue_cagr),
            pct(last_row["EBITDA Margin"]),
            pct(last_row["Net Margin"]),
            money(last_row["FCF"], currency),
            money(last_row["Ending Cash"], currency),
            money(last_row["Closing Debt"], currency),
            money(annual_df.attrs["enterprise_value"], currency),
            money(annual_df.attrs["equity_value"], currency),
            money(annual_df.attrs["value_per_share"], currency),
        ],
    })
    return summary


@st.cache_data(show_spinner=False)
def export_excel(control_df: pd.DataFrame, assumptions_df: pd.DataFrame, annual_df: pd.DataFrame, monthly_df: pd.DataFrame, expense_df: pd.DataFrame, variance_df: pd.DataFrame, sensitivity_df: pd.DataFrame, summary_df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        control_df.to_excel(writer, sheet_name="00_Control", index=False)
        assumptions_df.to_excel(writer, sheet_name="01_Assumptions", index=False)
        annual_df.to_excel(writer, sheet_name="02_Annual_Model", index=False)
        monthly_df.to_excel(writer, sheet_name="03_Monthly_Budget", index=False)
        expense_df.to_excel(writer, sheet_name="04_Expense_Buckets", index=False)
        variance_df.to_excel(writer, sheet_name="05_Forecast_vs_Actual", index=False)
        sensitivity_df.to_excel(writer, sheet_name="06_DCF_Sensitivity")
        summary_df.to_excel(writer, sheet_name="07_Summary", index=False)
    output.seek(0)
    return output.getvalue()


st.title("Herramienta Financiera Corporativa Pro")
st.caption("Modelo financiero corporativo en Python con proyección anual, presupuesto mensual, forecast vs actual, deuda, balance simplificado, DCF y apartados automáticos de gasto.")

with st.sidebar:
    st.header("Control")
    company_name = st.text_input("Empresa", value="Mi Empresa")
    currency = st.selectbox("Moneda", ["MXN", "USD", "EUR"], index=0)
    start_year = st.number_input("Año inicial", min_value=2020, max_value=2100, value=2026, step=1)
    horizon = st.slider("Horizonte (años)", min_value=3, max_value=15, value=10)
    scenario = st.selectbox("Escenario", list(SCENARIO_PRESETS.keys()), index=0)

    st.header("Operación")
    revenue_0 = st.number_input("Ingresos FY0", min_value=0.0, value=50_000_000.0, step=1_000_000.0, format="%.2f")
    growth_rate = st.slider("Crecimiento anual", min_value=-0.20, max_value=0.50, value=0.12, step=0.01)
    cogs_pct = st.slider("COGS % ventas", min_value=0.0, max_value=0.95, value=0.45, step=0.01)
    sales_pct = st.slider("Ventas % ventas", min_value=0.0, max_value=0.40, value=0.08, step=0.01)
    marketing_pct = st.slider("Marketing % ventas", min_value=0.0, max_value=0.30, value=0.06, step=0.01)
    admin_pct = st.slider("Administración % ventas", min_value=0.0, max_value=0.30, value=0.07, step=0.01)
    rd_pct = st.slider("I+D % ventas", min_value=0.0, max_value=0.30, value=0.04, step=0.01)
    depreciation_pct = st.slider("Depreciación % ventas", min_value=0.0, max_value=0.20, value=0.03, step=0.005)
    tax_rate = st.slider("Tasa fiscal", min_value=0.0, max_value=0.50, value=0.30, step=0.01)
    capex_pct = st.slider("Capex % ventas", min_value=0.0, max_value=0.30, value=0.05, step=0.01)
    nwc_pct = st.slider("NWC % ventas", min_value=0.0, max_value=0.40, value=0.10, step=0.01)

    st.header("Capital y deuda")
    initial_cash = st.number_input("Caja inicial", min_value=0.0, value=5_000_000.0, step=500_000.0, format="%.2f")
    initial_debt = st.number_input("Deuda inicial", min_value=0.0, value=12_000_000.0, step=500_000.0, format="%.2f")
    interest_rate = st.slider("Tasa de interés deuda", min_value=0.0, max_value=0.30, value=0.10, step=0.005)
    amortization_pct = st.slider("Amortización anual deuda", min_value=0.0, max_value=0.50, value=0.10, step=0.01)

    st.header("Valuación")
    wacc = st.slider("WACC", min_value=0.01, max_value=0.30, value=0.12, step=0.005)
    terminal_growth = st.slider("Crecimiento terminal", min_value=0.0, max_value=0.08, value=0.03, step=0.005)
    shares_outstanding = st.number_input("Acciones en circulación", min_value=0.0, value=1_000_000.0, step=100_000.0, format="%.2f")

    st.header("Apartados de gasto")
    expense_total = st.number_input("Monto total a repartir", min_value=0.0, value=1_000_000.0, step=50_000.0, format="%.2f")
    normalize_buckets = st.checkbox("Normalizar % automáticamente a 100%", value=True)
    expense_percentages: Dict[str, float] = {}
    for category, default_value in DEFAULT_BUCKETS.items():
        expense_percentages[category] = st.slider(f"{category} %", min_value=0.0, max_value=1.0, value=float(default_value), step=0.01)

inputs = CorporateInputs(
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
    interest_rate=float(interest_rate),
    amortization_pct=float(amortization_pct),
    wacc=float(wacc),
    terminal_growth=float(terminal_growth),
    shares_outstanding=float(shares_outstanding),
    expense_total=float(expense_total),
    expense_percentages=expense_percentages,
)

annual_df = build_annual_model(inputs)
expense_df = build_expense_buckets(inputs.expense_total, inputs.expense_percentages, normalize_buckets)
expense_sum = expense_df["Percentage"].sum()
summary_df = build_summary(annual_df, inputs.currency)

selected_budget_year = st.selectbox("Año para presupuesto mensual y forecast vs actual", annual_df["Year"].tolist(), index=1 if len(annual_df) > 1 else 0)
selected_row = annual_df.loc[annual_df["Year"] == selected_budget_year].iloc[0]

with st.expander("Editar estacionalidad mensual", expanded=False):
    seasonality_df = pd.DataFrame({"Mes": MONTHS, "Peso": DEFAULT_MONTH_WEIGHTS})
    edited_seasonality = st.data_editor(seasonality_df, hide_index=True, num_rows="fixed", use_container_width=True)

monthly_df = build_monthly_budget(int(selected_budget_year), selected_row, edited_seasonality["Peso"].tolist())

st.subheader("Forecast vs actual")
default_actuals = default_actuals_from_budget(monthly_df)
actuals_df = st.data_editor(default_actuals, hide_index=True, use_container_width=True, num_rows="fixed")
variance_df = build_variance_table(monthly_df, actuals_df)
sensitivity_df = build_sensitivity_table(annual_df, annual_df.attrs["effective_wacc"], inputs.terminal_growth)

control_df = pd.DataFrame({
    "Campo": ["Empresa", "Moneda", "Año inicial", "Horizonte", "Escenario", "Caja inicial", "Deuda inicial"],
    "Valor": [inputs.company_name, inputs.currency, inputs.start_year, inputs.horizon, inputs.scenario, inputs.initial_cash, inputs.initial_debt],
})

assumptions_df = pd.DataFrame({
    "Supuesto": [
        "Crecimiento anual", "COGS %", "Ventas %", "Marketing %", "Administración %", "I+D %",
        "Depreciación %", "Tasa fiscal", "Capex %", "NWC %", "Interés deuda", "Amortización deuda",
        "WACC", "Crecimiento terminal", "Acciones"
    ],
    "Valor": [
        inputs.growth_rate, inputs.cogs_pct, inputs.sales_pct, inputs.marketing_pct, inputs.admin_pct, inputs.rd_pct,
        inputs.depreciation_pct, inputs.tax_rate, inputs.capex_pct, inputs.nwc_pct, inputs.interest_rate, inputs.amortization_pct,
        inputs.wacc, inputs.terminal_growth, inputs.shares_outstanding
    ],
})

k1, k2, k3, k4, k5 = st.columns(5)
last_row = annual_df.iloc[-1]
k1.metric("Ingresos último año", money(last_row["Revenue"], currency))
k2.metric("EBITDA margen", pct(last_row["EBITDA Margin"]))
k3.metric("FCF último año", money(last_row["FCF"], currency))
k4.metric("Equity Value", money(annual_df.attrs["equity_value"], currency))
k5.metric("Valor por acción", money(annual_df.attrs["value_per_share"], currency))

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Resumen", "Modelo anual", "Presupuesto mensual", "Forecast vs actual", "Apartados de gasto", "Sensibilidad DCF"
])

with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    with c2:
        chart_df = annual_df.set_index("Year")[["Revenue", "EBITDA", "Net Income", "FCF"]]
        st.line_chart(chart_df)
    c3, c4 = st.columns([1, 1])
    with c3:
        st.line_chart(annual_df.set_index("Year")[["Ending Cash", "Closing Debt", "Equity"]])
    with c4:
        margin_df = annual_df.set_index("Year")[["Gross Margin", "EBITDA Margin", "Net Margin", "FCF Margin"]]
        st.line_chart(margin_df)

with tab2:
    view = st.radio("Vista", ["P&L", "Cash Flow", "Balance simplificado", "Completo"], horizontal=True)
    if view == "P&L":
        cols = ["Year", "Revenue", "Growth", "COGS", "Gross Profit", "Sales", "Marketing", "Admin", "R&D", "OPEX", "EBITDA", "Depreciation", "EBIT", "Interest Expense", "EBT", "Taxes", "Net Income"]
    elif view == "Cash Flow":
        cols = ["Year", "NOPAT", "Depreciation", "Capex", "Delta NWC", "FCF", "Interest Expense", "Debt Amortization", "Opening Cash", "Ending Cash"]
    elif view == "Balance simplificado":
        cols = ["Year", "Ending Cash", "NWC", "Net PP&E", "Total Assets", "Closing Debt", "Equity"]
    else:
        cols = annual_df.columns.tolist()
    st.dataframe(annual_df[cols], use_container_width=True, hide_index=True)

with tab3:
    st.write(f"Presupuesto mensual para {selected_budget_year}")
    st.dataframe(monthly_df, use_container_width=True, hide_index=True)
    st.bar_chart(monthly_df.set_index("Mes")[["Revenue", "EBITDA", "FCF"]])

with tab4:
    st.write(f"Comparación forecast vs actual para {selected_budget_year}")
    c1, c2 = st.columns([1, 2])
    with c1:
        variance_summary = variance_df.groupby("Metric", as_index=False).agg({"Forecast": "sum", "Actual": "sum", "Variance": "sum"})
        variance_summary["Variance %"] = np.where(variance_summary["Forecast"] != 0, variance_summary["Variance"] / variance_summary["Forecast"], 0.0)
        st.dataframe(variance_summary, use_container_width=True, hide_index=True)
    with c2:
        revenue_compare = monthly_df[["Mes", "Revenue"]].merge(actuals_df[["Mes", "Revenue"]], on="Mes", suffixes=(" Forecast", " Actual"))
        st.line_chart(revenue_compare.set_index("Mes"))
    st.dataframe(variance_df, use_container_width=True, hide_index=True)

with tab5:
    st.dataframe(expense_df, use_container_width=True, hide_index=True)
    total_pct_label = pct(expense_sum)
    total_amt_label = money(expense_df["Amount"].sum(), currency)
    if abs(expense_sum - 1.0) < 0.001:
        st.success(f"Los apartados suman {total_pct_label} y distribuyen {total_amt_label}.")
    else:
        st.warning(f"Los porcentajes suman {total_pct_label}. {'Se normalizaron automáticamente.' if normalize_buckets else 'Activa la normalización o ajústalos a 100%.'}")
    st.bar_chart(expense_df.set_index("Category")[["Amount"]])

with tab6:
    st.write("Sensibilidad de Enterprise Value por WACC y crecimiento terminal")
    st.dataframe(sensitivity_df.style.format("{:,.0f}"), use_container_width=True)

excel_bytes = export_excel(control_df, assumptions_df, annual_df, monthly_df, expense_df, variance_df, sensitivity_df, summary_df)
st.download_button(
    label="Descargar modelo en Excel",
    data=excel_bytes,
    file_name="modelo_financiero_corporativo_pro.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

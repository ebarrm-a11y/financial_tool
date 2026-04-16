# Herramienta Financiera Corporativa en Python

## Qué incluye
- Proyección financiera de largo plazo (3 a 15 años)
- Escenarios Base, Upside y Downside
- Estado de resultados proyectado
- Flujo de caja libre proyectado
- Valuación DCF (Enterprise Value, Equity Value, valor por acción)
- Apartados automáticos de gasto a partir de un monto total
- Dashboard con KPIs y gráficos
- Exportación a Excel

## Cómo ejecutarla
```bash
pip install -r requirements.txt
streamlit run financial_tool.py
```

## Archivo principal
- `financial_tool.py`

## Qué puedes ajustar
- Ingresos base
- Crecimiento anual
- COGS
- Gastos operativos por categoría
- Depreciación
- Impuestos
- Capex
- Capital de trabajo
- Caja y deuda inicial
- WACC y crecimiento terminal
- Acciones en circulación
- Porcentajes de apartados de gasto

## Salidas principales
- Revenue
- Gross Profit
- EBITDA
- EBIT
- NOPAT
- FCF
- EV / Equity Value
- Valor por acción
- Distribución automática de gasto por categorías

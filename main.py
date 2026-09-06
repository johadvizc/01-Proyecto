import streamlit as st 
import pandas as pd 
import plotly.express as px 

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Analítico de Decisiones",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# FUNCIÓN DE CARGA Y MANEJO DE DATOS
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='latin1')
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Error al cargar el archivo seleccionado: {e}")
            return None
    else:
        # Fallback dataset local
        try:
            df = pd.read_csv("Sample - Superstore.csv", encoding='latin1')
        except FileNotFoundError:
            st.warning("Por favor, sube un archivo CSV o XLSX en la barra lateral para continuar.")
            return None
    return df

# -----------------------------------------------------------------------------
# COMPONENTE DE CARGA DINÁMICA
# -----------------------------------------------------------------------------
st.sidebar.title("📂 Configuración y Datos")
uploaded_file = st.sidebar.file_uploader(
    "Cargar dataset (CSV o XLSX)", 
    type=["csv", "xlsx"]
)

df_raw = load_data(uploaded_file)

if df_raw is not None and not df_raw.empty:
    df = df_raw.copy()
    
    # Detección y formato de columna de fecha
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'fecha' in c.lower()]
    date_col = date_cols[0] if date_cols else None
    
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df = df.sort_values(by=date_col)

    st.title("📊 Dashboard Ejecutivo e Interactivo de Ventas")
    st.markdown("---")

    # -------------------------------------------------------------------------
    # FILTROS DINÁMICOS EN SIDEBAR
    # -------------------------------------------------------------------------
    st.sidebar.header("🔍 Filtros Dinámicos")

    # Filtro 1: Rango de Fechas
    if date_col:
        min_date = df[date_col].min().date()
        max_date = df[date_col].max().date()
        date_range = st.sidebar.date_input(
            "Rango de Fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_d, end_d = date_range
            df = df[(df[date_col].dt.date >= start_d) & (df[date_col].dt.date <= end_d)]

    # Filtro 2: Categoría Principal
    cat_col = 'Category' if 'Category' in df.columns else (df.select_dtypes(include=['object']).columns[0] if len(df.select_dtypes(include=['object']).columns) > 0 else None)
    if cat_col:
        categories = ["Todas"] + sorted(df[cat_col].dropna().astype(str).unique().tolist())
        selected_cat = st.sidebar.selectbox(f"Categoría ({cat_col})", categories)
        if selected_cat != "Todas":
            df = df[df[cat_col] == selected_cat]

    # Filtro 3: Región / Segmento
    reg_col = 'Region' if 'Region' in df.columns else ('Segment' if 'Segment' in df.columns else None)
    if reg_col:
        regions = ["Todas"] + sorted(df[reg_col].dropna().astype(str).unique().tolist())
        selected_reg = st.sidebar.multiselect(f"Región ({reg_col})", options=regions, default=[])
        if selected_reg and "Todas" not in selected_reg:
            df = df[df[reg_col].isin(selected_reg)]

    # -------------------------------------------------------------------------
    # MÉTRICAS CLAVE (6 KPIs)
    # -------------------------------------------------------------------------
    st.subheader("📌 Indicadores Clave de Rendimiento (KPIs)")
    
    sales_col = 'Sales' if 'Sales' in df.columns else (df.select_dtypes(include=['float64', 'int64']).columns[0] if len(df.select_dtypes(include=['float64', 'int64']).columns) > 0 else None)
    profit_col = 'Profit' if 'Profit' in df.columns else (df.select_dtypes(include=['float64', 'int64']).columns[1] if len(df.select_dtypes(include=['float64', 'int64']).columns) > 1 else None)
    qty_col = 'Quantity' if 'Quantity' in df.columns else None
    disc_col = 'Discount' if 'Discount' in df.columns else None
    order_col = 'Order ID' if 'Order ID' in df.columns else None

    # Cálculos numéricos
    val_sales = df[sales_col].sum() if sales_col else 0
    val_profit = df[profit_col].sum() if profit_col else 0
    val_orders = df[order_col].nunique() if order_col else len(df)
    val_qty = df[qty_col].sum() if qty_col else 0
    val_margin = (val_profit / val_sales * 100) if val_sales != 0 else 0
    val_disc = (df[disc_col].mean() * 100) if disc_col else 0

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    kpi1.metric("Ventas Totales", f"${val_sales:,.2f}")
    kpi2.metric("Ganancia Total", f"${val_profit:,.2f}")
    kpi3.metric("Total Pedidos", f"{val_orders:,}")
    kpi4.metric("Unidades Vendidas", f"{val_qty:,}")
    kpi5.metric("Margen Ganancia", f"{val_margin:.2f}%")
    kpi6.metric("Descuento Prom.", f"{val_disc:.2f}%")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # VISUALIZACIONES GRÁFICAS INTERACTIVAS (PLOTLY)
    # -------------------------------------------------------------------------
    st.subheader("📈 Análisis Gráfico e Interactivo")

    g1, g2 = st.columns(2)

    with g1:
        # Gráfico 1: Tendencia Mensual de Ventas y Ganancias
        if date_col and sales_col:
            df_trend = df.set_index(date_col).resample('M')[[sales_col, profit_col] if profit_col else [sales_col]].sum().reset_index()
            fig1 = px.line(
                df_trend, 
                x=date_col, 
                y=[sales_col, profit_col] if profit_col else [sales_col],
                title="1. Evolución Temporal de Ventas y Ganancias",
                labels={'value': 'Monto ($)', 'variable': 'Métrica', date_col: 'Fecha'},
                template="plotly_white"
            )
            fig1.update_layout(hovermode="x unified")
            st.plotly_chart(fig1, use_container_width=True)

    with g2:
        # Gráfico 2: Ventas por Subcategoría
        subcat_col = 'Sub-Category' if 'Sub-Category' in df.columns else cat_col
        if subcat_col and sales_col:
            df_sub = df.groupby(subcat_col)[sales_col].sum().reset_index().sort_values(by=sales_col, ascending=True)
            fig2 = px.bar(
                df_sub, 
                x=sales_col, 
                y=subcat_col, 
                orientation='h',
                title=f"2. Ventas Totales por {subcat_col}",
                labels={sales_col: 'Ventas ($)', subcat_col: 'Subcategoría'},
                color=sales_col,
                color_continuous_scale="Viridis",
                template="plotly_white"
            )
            st.plotly_chart(fig2, use_container_width=True)

    g3, g4 = st.columns(2)

    with g3:
        # Gráfico 3: Distribución por Segmento de Cliente
        seg_col = 'Segment' if 'Segment' in df.columns else reg_col
        if seg_col and sales_col:
            fig3 = px.pie(
                df, 
                names=seg_col, 
                values=sales_col, 
                hole=0.4,
                title=f"3. Participación de Ventas por {seg_col}",
                color_discrete_sequence=px.colors.qualitative.Set2,
                template="plotly_white"
            )
            st.plotly_chart(fig3, use_container_width=True)

    with g4:
        # Gráfico 4: Dispersión Ventas vs Ganancia por Registro
        if sales_col and profit_col:
            fig4 = px.scatter(
                df, 
                x=sales_col, 
                y=profit_col, 
                color=cat_col if cat_col else None,
                size=qty_col if qty_col else None,
                hover_data=['Product Name'] if 'Product Name' in df.columns else None,
                title="4. Relación Ventas vs. Ganancia por Producto",
                labels={sales_col: 'Ventas ($)', profit_col: 'Ganancia ($)'},
                template="plotly_white"
            )
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # TABLA COMPLETA Y EXPORTACIÓN
    # -------------------------------------------------------------------------
    st.subheader("📋 Explorer de Datos Filtrados y Exportación")
    
    st.dataframe(df, use_container_width=True, height=350)

    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Datos Filtrados en CSV",
        data=csv_data,
        file_name="datos" \
        "_filtrados_superstore.csv",
        mime="text/csv"
    )

else:
    st.info("Sube un archivo `.csv` o `.xlsx` desde el panel lateral para iniciar el análisis.")
import io
import re
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ---- CONFIGURACIÓN GENERAL ----
st.set_page_config(page_title="Dashboard Inventario", layout="wide")
st.markdown("<h2 style='text-align:center;color:#2E86C1;'>📦 Dashboard Inventario – WayUP</h2>", unsafe_allow_html=True)

# ---- ARCHIVOS DESDE ONEDRIVE ----
ARCHIVOS = {
    "inventario.xlsx": "https://warehousing-my.sharepoint.com/:x:/g/personal/dflores_warehousing_cl/Ee1usbdQDZhDme2vsa2hYXwBZdFLHdeg65l-wmCii__fHw?e=J4rrv2",
}

archivo_sel = st.selectbox("📁 Selecciona archivo", list(ARCHIVOS.keys()))
base_url = ARCHIVOS[archivo_sel]
DOWNLOAD_URL = base_url + ("&download=1" if "?" in base_url else "?download=1")

if st.button("🔄 Actualizar datos"):
    st.rerun()

# ---- FUNCIONES AUXILIARES ----
def limpiar(col): return re.sub(r"\s+", "", col).lower()

def col_cantidad(df):
    for c in df.columns:
        x = limpiar(c)
        if x == "cantidad": return c
    for c in df.columns:
        x = limpiar(c)
        if "cantidad" in x and "contar" not in x: return c
    return None

def col_contar(df):
    for c in df.columns:
        x = limpiar(c)
        if "cantidad" in x and "contar" in x: return c
    return None

def col_producto(df):
    for c in df.columns:
        x = limpiar(c)
        if "cod" in x and "producto" in x: return c
    return None

# ---- DESCARGA EXCEL ----
try:
    resp = requests.get(DOWNLOAD_URL)
    df = pd.read_excel(io.BytesIO(resp.content))
except Exception as e:
    st.error(f"❌ Error descargando: {e}")
    st.stop()

df.columns = [c.strip() for c in df.columns]

c_cant = col_cantidad(df)
c_cont = col_contar(df)

df[c_cant] = pd.to_numeric(df[c_cant], errors="coerce").fillna(0)
df[c_cont] = pd.to_numeric(df[c_cont], errors="coerce").fillna(0)

df["Dif_calc"] = df[c_cont] - df[c_cant]

# ---- CÁLCULOS ----
tot_sist = df[c_cant].sum()
tot_cont = df[c_cont].sum()
pct_avance = (tot_cont / tot_sist * 100) if tot_sist else 0
pct_dif = (df["Dif_calc"].sum() / tot_sist * 100) if tot_sist else 0

# ---- KPIS ----
col_kpi = st.columns(5)
col_kpi[0].metric("Sistema", f"{tot_sist:,.0f}")
col_kpi[1].metric("Contado", f"{tot_cont:,.0f}")
col_kpi[2].metric("Diferencias", f"{df['Dif_calc'].sum():,.0f}")
col_kpi[3].metric("% Dif.", f"{pct_dif:.2f}%")
col_kpi[4].metric("% Avance", f"{pct_avance:.2f}%")

st.progress(min(pct_avance/100, 1.0))

# ---- GRÁFICOS DISTRIBUIDOS (2 COLUMNAS) ----
col_g1, col_g2 = st.columns(2)

# --- 1) ANILLO DE AVANCE GENERAL ---
with col_g1:
    st.markdown("### 🎯 Avance General")
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(
        [pct_avance, 100 - pct_avance],
        colors=["#2ECC71", "#E5E7E9"],
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.3},
    )
    ax.text(0, 0, f"{pct_avance:.1f}%", ha="center", va="center", fontsize=20, color="#2ECC71")
    ax.set(aspect="equal")
    st.pyplot(fig)

# --- 2) TORTA POR CONTADOR ---
with col_g2:
    st.markdown("### 🧍 Avance por Contador")
    if "Contador" in df.columns:
        grp = df.groupby("Contador").agg(
            sist=(c_cant, "sum"),
            cont=(c_cont, "sum")
        )
        grp["pct"] = grp["cont"] / grp["sist"] * 100

        cont_sel = st.selectbox("Selecciona Contador", grp.index)
        pct = grp.loc[cont_sel, "pct"]

        fig2, ax2 = plt.subplots(figsize=(4, 4))
        ax2.pie(
            [pct, 100 - pct],
            labels=[f"{pct:.1f}% contado", ""],
            colors=["#3498DB", "#E5E7E9"],
            startangle=90,
            wedgeprops={"width": 0.4},
        )
        ax2.set(aspect="equal")
        st.pyplot(fig2)
    else:
        st.info("No existe columna 'Contador'.")

# ---- TOP DIFERENCIAS (15 PRODUCTOS) ----
st.markdown("### 🔎 Top 15 Productos con Mayor Diferencia (Barras horizontales)")

c_prod = col_producto(df)
if c_prod:
    dif = df.groupby(c_prod)["Dif_calc"].sum().abs().sort_values(ascending=False).head(15)

    fig3, ax3 = plt.subplots(figsize=(10, 6))
    ax3.barh(dif.index, dif.values, color="#F39C12")
    ax3.invert_yaxis()
    ax3.set_xlabel("Diferencia Absoluta")
    ax3.set_title("Top 15 productos con mayor diferencia")
    st.pyplot(fig3)

# ---- FILTROS Y TABLA ----
with st.expander("Filtros"):
    contadores = df["Contador"].unique() if "Contador" in df.columns else []
    clientes = df["Cliente"].unique() if "Cliente" in df.columns else []
    ubicaciones = df["Ubicación"].unique() if "Ubicación" in df.columns else []

    sel_cont = st.multiselect("Contador", contadores)
    sel_cli = st.multiselect("Cliente", clientes)
    sel_ubi = st.multiselect("Ubicación", ubicaciones)

df_f = df.copy()
if sel_cont: df_f = df_f[df_f["Contador"].isin(sel_cont)]
if sel_cli: df_f = df_f[df_f["Cliente"].isin(sel_cli)]
if sel_ubi: df_f = df_f[df_f["Ubicación"].isin(sel_ubi)]

st.markdown("### 📄 Detalle Inventario")
st.dataframe(df_f.fillna(""), use_container_width=True)


import pandas as pd
import streamlit as st
import re

st.set_page_config(page_title="Dashboard Inventario", layout="wide")
st.title("📦 Dashboard Inventario – WayUP (OneDrive local)")

# 👉 AJUSTA ESTA RUTA A TU PC
RUTA_ARCHIVO = RUTA_ARCHIVO = r"C:\Users\dflores\OneDrive - Warehousing Valle Grande SA\Prueba\REPORTE INVENTARIO 25-11-2025.xlsx" 
st.caption(f"Origen de datos: {RUTA_ARCHIVO}")

# Botón para recargar datos
if st.button("🔄 Actualizar datos"):
    st.rerun()

def limpiar_nombre(col):
    return re.sub(r"\s+", "", col).lower()

def buscar_cantidad(df):
    for col in df.columns:
        c = limpiar_nombre(col)
        if c == "cantidad":
            return col
    for col in df.columns:
        c = limpiar_nombre(col)
        if "cantidad" in c and "contar" not in c:
            return col
    return None

def buscar_cantidad_contar(df):
    for col in df.columns:
        c = limpiar_nombre(col)
        if c in ["cantidadacontar", "cantidadaacontar"]:
            return col
        if "cantidad" in c and "contar" in c:
            return col
    return None

# Leer archivo desde OneDrive local
try:
    df = pd.read_excel(RUTA_ARCHIVO)
except FileNotFoundError:
    st.error("❌ No encuentro el archivo. Revisa la ruta y que OneDrive esté sincronizado.")
    st.stop()

df.columns = [c.strip() for c in df.columns]

col_cant = buscar_cantidad(df)
col_cont = buscar_cantidad_contar(df)

if not col_cant or not col_cont:
    st.error("⚠️ No se detectaron columnas 'Cantidad' o 'Cantidad a contar'.")
    st.write("Columnas detectadas:", list(df.columns))
    st.stop()

df[col_cant] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0)
df[col_cont] = pd.to_numeric(df[col_cont], errors="coerce").fillna(0)
df["Dif_calc"] = df[col_cont] - df[col_cant]

tot_sist = df[col_cant].sum()
tot_cont = df[col_cont].sum()
tot_dif = df["Dif_calc"].sum()
pct_avance = (tot_cont / tot_sist * 100) if tot_sist else 0
pct_dif = (tot_dif / tot_sist * 100) if tot_sist else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cantidad sistema", f"{tot_sist:,.0f}")
c2.metric("Cantidad contada", f"{tot_cont:,.0f}")
c3.metric("Diferencia total", f"{tot_dif:,.0f}")
c4.metric("% diferencia", f"{pct_dif:.2f}%")

st.progress(min(pct_avance / 100, 1.0))
st.caption(f"Avance de conteo: {pct_avance:.2f}%")

with st.expander("Filtros"):
    cont_vals = df["Contador"].unique() if "Contador" in df.columns else []
    cli_vals = df["Cliente"].unique() if "Cliente" in df.columns else []
    ubic_vals = df["Ubicación"].unique() if "Ubicación" in df.columns else []
    cont = st.multiselect("Contador", cont_vals)
    cli = st.multiselect("Cliente", cli_vals)
    ubic = st.multiselect("Ubicación", ubic_vals)

df_f = df.copy()
if cont and "Contador" in df_f.columns:
    df_f = df_f[df_f["Contador"].isin(cont)]
if cli and "Cliente" in df_f.columns:
    df_f = df_f[df_f["Cliente"].isin(cli)]
if ubic and "Ubicación" in df_f.columns:
    df_f = df_f[df_f["Ubicación"].isin(ubic)]

st.subheader("Detalle inventario")
st.dataframe(df_f, use_container_width=True)


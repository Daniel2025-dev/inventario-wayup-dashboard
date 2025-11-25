import os
import pandas as pd
import streamlit as st
import re

st.set_page_config(page_title="Dashboard Inventario", layout="wide")
st.title("📦 Dashboard Inventario – WayUP (OneDrive local)")

# 🔧 AJUSTA TU RUTA AQUÍ (cópiala con "Copiar como ruta de acceso")
RUTA_ARCHIVO = r"C:\Users\dflores\OneDrive - Warehousing Valle Grande SA\Prueba\inventario.xlsx"

# Mostrar la ruta en pantalla
st.caption(f"📁 Origen de datos: `{RUTA_ARCHIVO}`")

# Mostrar si Python ve el archivo
archivo_existe = os.path.exists(RUTA_ARCHIVO)
st.write("🔎 ¿El archivo existe según Python?: **", archivo_existe, "**")

# Botón para recargar datos
if st.button("🔄 Actualizar datos"):
    st.rerun()


# ------------------------------
#   FUNCIONES PARA DETECTAR COLUMNAS
# ------------------------------

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


# ------------------------------
#   CARGA DEL ARCHIVO
# ------------------------------

if not archivo_existe:
    st.error("❌ **El archivo NO existe.** Revisa la ruta exacta o que OneDrive esté sincronizado.")
    st.stop()

try:
    df = pd.read_excel(RUTA_ARCHIVO)
except Exception as e:
    st.error(f"❌ Error leyendo el archivo: {e}")
    st.stop()


# ------------------------------
#   PROCESAMIENTO
# ------------------------------

df.columns = [c.strip() for c in df.columns]

col_cant = buscar_cantidad(df)
col_cont = buscar_cantidad_contar(df)

if not col_cant or not col_cont:
    st.error("⚠️ No se detectaron las columnas 'Cantidad' o 'Cantidad a contar'.")
    st.write("Columnas encontradas:", list(df.columns))
    st.stop()

df[col_cant] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0)
df[col_cont] = pd.to_numeric(df[col_cont], errors="coerce").fillna(0)
df["Dif_calc"] = df[col_cont] - df[col_cant]

tot_sist = df[col_cant].sum()
tot_cont = df[col_cont].sum()
tot_dif = df["Dif_calc"].sum()
pct_avance = (tot_cont / tot_sist * 100) if tot_sist else 0
pct_dif = (tot_dif / tot_sist * 100) if tot_sist else 0


# ------------------------------
#   DASHBOARD
# ------------------------------

c1, c2


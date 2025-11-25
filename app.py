import io
import re
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Dashboard Inventario", layout="wide")
st.title("📦 Dashboard Inventario – WayUP (OneDrive link)")

# 1) MÚLTIPLES ARCHIVOS EN ONEDRIVE (EDITA ESTE DICCIONARIO)
ARCHIVOS = {
    "inventario.xlsx": "https://warehousing-my.sharepoint.com/:x:/g/personal/dflores_warehousing_cl/Ee1usbdQDZhDme2vsa2hYXwBZdFLHdeg65l-wmCii__fHw?e=J4rrv2",
    # agrega más:
    # "inventario2.xlsx": "https://TU_OTRO_LINK",
}

archivo_sel = st.selectbox("📁 Selecciona archivo de inventario", list(ARCHIVOS.keys()))
base_url = ARCHIVOS[archivo_sel]

# Asegurar URL de descarga
if "download=1" in base_url:
    DOWNLOAD_URL = base_url
else:
    DOWNLOAD_URL = base_url + ("&download=1" if "?" in base_url else "?download=1")

st.caption(f"Origen de datos: OneDrive/SharePoint – {archivo_sel}")

if st.button("🔄 Actualizar datos"):
    st.rerun()


# ---------- FUNCIONES AUXILIARES ----------

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

def buscar_producto(df):
    for col in df.columns:
        c = limpiar_nombre(col)
        if "cod" in c and "producto" in c:
            return col
    return None


# ---------- DESCARGA DESDE ONEDRIVE ----------

try:
    resp = requests.get(DOWNLOAD_URL)
    if resp.status_code != 200:
        st.error(f"❌ Error descargando desde OneDrive (status {resp.status_code}). "
                 "Revisa permisos o el link del archivo seleccionado.")
        st.stop()
    df = pd.read_excel(io.BytesIO(resp.content))
except Exception as e:
    st.error(f"❌ Error leyendo el Excel desde OneDrive: {e}")
    st.stop()

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

# ---------- KPI PRINCIPALES ----------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Cantidad sistema", f"{tot_sist:,.0f}")
c2.metric("Cantidad contada", f"{tot_cont:,.0f}")
c3.metric("Diferencia total", f"{tot_dif:,.0f}")
c4.metric("% diferencia", f"{pct_dif:.2f}%")
c5.metric("% avance conteo", f"{pct_avance:.2f}%")

st.progress(min(pct_avance / 100, 1.0))
st.caption(f"📊 Avance general de conteo: **{pct_avance:.2f}%**")


# ---------- 3) GRÁFICOS DE AVANCE ----------

st.subheader("📈 Avance de conteo")

# 3.a) Gráfico de ANILLO general (avance vs pendiente)
st.markdown("**Avance general (gráfico de anillo)**")
pct_g = max(0, min(pct_avance, 100))
restante = 100 - pct_g

fig1, ax1 = plt.subplots()
ax1.pie(
    [pct_g, restante],
    labels=[f"{pct_g:.1f}% avance", ""],
    startangle=90,
    counterclock=False,
    wedgeprops=dict(width=0.3)
)
ax1.set(aspect="equal")
st.pyplot(fig1)

# 3.b) Gráfico de TORTA por contador (avance de un contador)
if "Contador" in df.columns:
    st.markdown("**Avance por contador (selecciona un contador)**")
    grp = df.groupby("Contador").agg(
        cantidad_sistema=(col_cant, "sum"),
        cantidad_contada=(col_cont, "sum")
    ).reset_index()
    grp["avance_pct"] = grp.apply(
        lambda x: (x["cantidad_contada"] / x["cantidad_sistema"] * 100)
        if x["cantidad_sistema"] else 0,
        axis=1
    )

    cont_sel = st.selectbox("Selecciona contador para ver su avance", grp["Contador"])
    fila = grp[grp["Contador"] == cont_sel].iloc[0]
    pct_c = max(0, min(fila["avance_pct"], 100))
    restante_c = 100 - pct_c

    fig2, ax2 = plt.subplots()
    ax2.pie(
        [pct_c, restante_c],
        labels=[f"{pct_c:.1f}% contado", f"{restante_c:.1f}% pendiente"],
        startangle=90,
        counterclock=False
    )
    ax2.set(aspect="equal")
    st.pyplot(fig2)

    st.dataframe(grp, use_container_width=True)
else:
    st.info("No existe la columna 'Contador' para graficar avance por contador.")


# ---------- 5) TOP DIFERENCIAS POR PRODUCTO ----------

st.subheader("📊 Top diferencias por producto")

col_prod = buscar_producto(df)
if col_prod:
    dif_prod = df.groupby(col_prod)["Dif_calc"].sum().reset_index()
    dif_prod["abs_dif"] = dif_prod["Dif_calc"].abs()
    dif_top = dif_prod.sort_values("abs_dif", ascending=False).head(10).set_index(col_prod)
    st.markdown("**Top 10 productos por diferencia absoluta (sobrante/faltante)**")
    st.bar_chart(dif_top[["Dif_calc"]])
    st.dataframe(dif_top, use_container_width=True)
else:
    st.info("No se encontró columna de código de producto para análisis de diferencias.")


# ---------- FILTROS Y DETALLE ----------

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

st.subheader("📄 Detalle inventario")
df_f_display = df_f.fillna("")   # 4) columnas vacías en vez de None
st.dataframe(df_f_display, use_container_width=True)


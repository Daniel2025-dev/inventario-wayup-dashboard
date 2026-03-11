import io
import os
import re
import unicodedata

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Herramienta de Inventario conteo fisico - WayUP",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "table_expanded" not in st.session_state:
    st.session_state["table_expanded"] = False


st.markdown(
    """
<style>
.main {background-color:#f3f4f7;}
[data-testid="stAppViewContainer"] > .main {
  background:linear-gradient(135deg,#f3f4f7 0%,#e9edf2 100%);
}
.block-container{padding-top:1.5rem;padding-bottom:1.5rem;max-width:1300px;}
h2{font-family:"Segoe UI",sans-serif;color:#1f2937;}
[data-testid="stMetric"]{
  background:#fff;padding:0.8rem;border-radius:0.9rem;
  box-shadow:0 2px 6px rgba(15,23,42,.08);
}
.stTabs [role="tab"]{padding:.5rem 1rem;border-radius:999px;border:1px solid transparent;}
.stTabs [role="tab"][aria-selected="true"]{background:#fff;border-color:#d1d5db;}
.toolbar-card{
  background:#ffffff;
  border:1px solid #dbe2ea;
  border-radius:14px;
  padding:.7rem .75rem;
  margin:.75rem 0;
  box-shadow:0 2px 10px rgba(15,23,42,.05);
}
.toolbar-label{
  font-size:.85rem;
  color:#475569;
  margin-bottom:.4rem;
  font-weight:600;
}
#MainMenu{visibility:hidden;} footer{visibility:hidden;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<h2 style='text-align:center;'>Herramienta de Inventario conteo fisico - WayUP</h2>",
    unsafe_allow_html=True,
)

INDEX_FILE = "inventarios_index.csv"


def normalize_text(value):
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", "", text)


def find_column(df, predicate):
    for column in df.columns:
        normalized = normalize_text(column)
        if predicate(normalized):
            return column
    return None


def col_cantidad(df):
    exact = find_column(df, lambda name: name == "cantidad")
    if exact:
        return exact
    return find_column(df, lambda name: "cantidad" in name and "contar" not in name)


def col_contar(df):
    return find_column(df, lambda name: "cantidad" in name and "contar" in name)


def col_producto(df):
    return find_column(df, lambda name: "cod" in name and "producto" in name)


def col_named(df, target):
    normalized_target = normalize_text(target)
    return find_column(df, lambda name: name == normalized_target)


def flatten_columns(columns):
    if isinstance(columns, pd.MultiIndex):
        flattened = []
        for group in columns:
            values = [str(item) for item in group if str(item) and str(item) != "nan"]
            flattened.append(" ".join(values).strip())
        return flattened
    return [str(column) for column in columns]


def detect_and_read_excel(content):
    try:
        dataframe = pd.read_excel(io.BytesIO(content))
    except Exception:
        text = content.decode("utf-8", errors="replace")
        return pd.read_csv(io.StringIO(text))

    dataframe.columns = flatten_columns(dataframe.columns)

    if col_cantidad(dataframe) and col_contar(dataframe):
        return dataframe

    try:
        raw = pd.read_excel(io.BytesIO(content), header=None)
    except Exception:
        return dataframe

    max_check = min(6, len(raw))
    for row_index in range(max_check):
        row = raw.iloc[row_index].astype(str).fillna("").tolist()
        cleaned = [normalize_text(cell) for cell in row]
        if any(("cantidad" in cell) or ("cod" in cell and "producto" in cell) for cell in cleaned):
            try:
                retry = pd.read_excel(io.BytesIO(content), header=row_index)
                retry.columns = flatten_columns(retry.columns)
                return retry
            except Exception:
                continue

    return dataframe


def to_excel_bytes(dataframe, sheet_name):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


def highlight_differences(row):
    difference = row.get("Dif_calc", 0)
    try:
        has_difference = abs(float(difference)) > 0
    except (TypeError, ValueError):
        has_difference = False
    color = "background-color: #fff7cd" if has_difference else ""
    return [color] * len(row)


def render_inventory_table(dataframe, height):
    styled = dataframe.style.apply(highlight_differences, axis=1)
    st.dataframe(styled, height=height, use_container_width=True)


if os.path.exists(INDEX_FILE):
    df_idx = pd.read_csv(INDEX_FILE)
else:
    df_idx = pd.DataFrame(
        {
            "Nombre": ["inventario.xlsx"],
            "URL": [
                "https://warehousing-my.sharepoint.com/:x:/g/personal/dflores_warehousing_cl/Ee1usbdQDZhDme2vsa2hYXwBZdFLHdeg65l-wmCii__fHw?e=J4rrv2"
            ],
        }
    )
    df_idx.to_csv(INDEX_FILE, index=False)


with st.sidebar:
    st.subheader("Gestionar inventarios")
    nuevo_nombre = st.text_input("Nombre inventario")
    nueva_url = st.text_input("URL OneDrive del Excel")
    if st.button("Guardar inventario"):
        if nuevo_nombre and nueva_url:
            df_idx = pd.concat(
                [df_idx, pd.DataFrame({"Nombre": [nuevo_nombre], "URL": [nueva_url]})],
                ignore_index=True,
            )
            df_idx.to_csv(INDEX_FILE, index=False)
            st.success("Inventario guardado. Recarga la pagina para verlo en la lista.")
        else:
            st.warning("Completa Nombre y URL.")


c_top1, c_top2 = st.columns([2, 1])
with c_top1:
    nombre_sel = st.selectbox("Archivo de inventario", df_idx["Nombre"])
with c_top2:
    if st.button("Actualizar datos"):
        st.rerun()


fila_sel = df_idx[df_idx["Nombre"] == nombre_sel].iloc[0]
base_url = fila_sel["URL"]
download_url = (
    base_url
    if "download=1" in base_url
    else base_url + ("&download=1" if "?" in base_url else "?download=1")
)

st.caption(f"Fuente: {nombre_sel}")


df = None
try:
    response = requests.get(download_url, timeout=30)
    response.raise_for_status()
    df = detect_and_read_excel(response.content)
except requests.exceptions.RequestException as exc:
    st.error(f"Error descargando inventario: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"Error leyendo inventario: {exc}")
    st.stop()

if df is None:
    st.error("No se pudo leer el inventario.")
    raise SystemExit(1)


df.columns = [str(column).strip() for column in df.columns]
c_cant = col_cantidad(df)
c_cont = col_contar(df)
if not c_cant or not c_cont:
    st.error("No se detectan columnas 'Cantidad' o 'Cantidad a contar'.")
    st.write("Columnas:", list(df.columns))
    st.stop()

contador_col = col_named(df, "Contador")
cliente_col = col_named(df, "Cliente")
ubicacion_col = col_named(df, "Ubicacion")

df[c_cant] = pd.to_numeric(df[c_cant], errors="coerce").fillna(0)
df[c_cont] = pd.to_numeric(df[c_cont], errors="coerce")
df["Dif_calc"] = df.apply(
    lambda row: (row[c_cont] - row[c_cant]) if pd.notna(row[c_cont]) else 0,
    axis=1,
)
df["Diferencias"] = df["Dif_calc"].astype(int)

tot_sist = df[c_cant].sum()
tot_cont = df[c_cont].sum(skipna=True)
tot_dif = df["Dif_calc"].sum()
pct_avance = (tot_cont / tot_sist * 100) if tot_sist else 0
pct_dif = (tot_dif / tot_sist * 100) if tot_sist else 0


k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Sistema", f"{tot_sist:,.0f}")
k2.metric("Contado", f"{tot_cont:,.0f}")
k3.metric("Dif. total", f"{tot_dif:,.0f}")
k4.metric("% Dif.", f"{pct_dif:.2f}%")
k5.metric("% Avance", f"{pct_avance:.2f}%")
st.progress(min(pct_avance / 100, 1.0))
st.markdown("---")


tab_resumen, tab_detalle = st.tabs(["Vision general", "Detalle y filtros"])

with tab_resumen:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Avance general")
        pct_general = max(0, min(pct_avance, 100))
        fig, ax = plt.subplots(figsize=(3.5, 3.5))
        ax.pie(
            [pct_general, 100 - pct_general],
            colors=["#22c55e", "#e5e7eb"],
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.32},
        )
        ax.text(
            0,
            0,
            f"{pct_general:.1f}%",
            ha="center",
            va="center",
            fontsize=18,
            color="#16a34a",
            fontweight="bold",
        )
        ax.set(aspect="equal")
        plt.tight_layout()
        st.pyplot(fig)

    with c2:
        st.markdown("#### Avance por contador")
        if contador_col:
            grp = df.groupby(contador_col).agg(sist=(c_cant, "sum"), cont=(c_cont, "sum"))
            grp["pct"] = grp.apply(
                lambda row: (row["cont"] / row["sist"] * 100) if row["sist"] else 0,
                axis=1,
            )
            contador_sel = st.selectbox("Selecciona contador", grp.index)
            pct_contador = grp.loc[contador_sel, "pct"]
            fig2, ax2 = plt.subplots(figsize=(3.5, 3.5))
            ax2.pie(
                [pct_contador, 100 - pct_contador],
                colors=["#3b82f6", "#e5e7eb"],
                startangle=90,
                counterclock=False,
                wedgeprops={"width": 0.4},
            )
            ax2.text(
                0,
                0,
                f"{pct_contador:.1f}%",
                ha="center",
                va="center",
                fontsize=18,
                color="#1d4ed8",
                fontweight="bold",
            )
            ax2.set(aspect="equal")
            plt.tight_layout()
            st.pyplot(fig2)
        else:
            st.info("No existe columna 'Contador'.")

    st.markdown("---")
    st.markdown("#### Top 15 productos con mayor diferencia absoluta")
    producto_col = col_producto(df)
    if producto_col:
        dif = df.groupby(producto_col)["Dif_calc"].sum()
        dif_abs = dif.abs().sort_values(ascending=False).head(15)
        fig3, ax3 = plt.subplots(figsize=(7, 4))
        cmap = plt.get_cmap("tab20")
        colors = [cmap(index) for index in range(len(dif_abs))]
        ax3.barh(dif_abs.index, dif_abs.values, color=colors)
        ax3.invert_yaxis()
        ax3.set_xlabel("Diferencia absoluta")
        ax3.set_ylabel("Producto")
        ax3.grid(axis="x", linestyle="--", alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig3)
    else:
        st.info("No se encontro columna de codigo de producto.")


with tab_detalle:
    with st.expander("Filtros"):
        contadores = df[contador_col].dropna().unique() if contador_col else []
        clientes = df[cliente_col].dropna().unique() if cliente_col else []
        ubicaciones = df[ubicacion_col].dropna().unique() if ubicacion_col else []
        filtro_contador = st.multiselect("Contador", contadores)
        filtro_cliente = st.multiselect("Cliente", clientes)
        filtro_ubicacion = st.multiselect("Ubicacion", ubicaciones)

    df_f = df.copy()
    if filtro_contador and contador_col:
        df_f = df_f[df_f[contador_col].isin(filtro_contador)]
    if filtro_cliente and cliente_col:
        df_f = df_f[df_f[cliente_col].isin(filtro_cliente)]
    if filtro_ubicacion and ubicacion_col:
        df_f = df_f[df_f[ubicacion_col].isin(filtro_ubicacion)]

    st.markdown("#### Detalle de inventario")

    df_display = df_f.fillna("")
    dif_only = df_f[df_f["Dif_calc"].abs() != 0]

    c1, c2 = st.columns([1, 1])
    with c1:
        st.download_button(
            "Exportar todo (XLSX)",
            data=to_excel_bytes(df_display, "Detalle"),
            file_name="inventario_detalle.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with c2:
        st.download_button(
            "Exportar diferencias (XLSX)",
            data=to_excel_bytes(dif_only, "Diferencias"),
            file_name="inventario_diferencias.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.markdown(
        "<div class='toolbar-card'><div class='toolbar-label'>Vista de tabla</div>",
        unsafe_allow_html=True,
    )
    c_ctrl, _ = st.columns([0.22, 0.78])
    with c_ctrl:
        if st.session_state.get("table_expanded", False):
            if st.button("Minimizar tabla", key="minimize_table", use_container_width=True):
                st.session_state["table_expanded"] = False
        else:
            if st.button("Ampliar tabla", key="maximize_table", use_container_width=True):
                st.session_state["table_expanded"] = True
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("table_expanded", False):
        st.markdown("#### Vista ampliada - Tabla")
        render_inventory_table(df_display, height=700)
        st.stop()

    render_inventory_table(df_display, height=350)

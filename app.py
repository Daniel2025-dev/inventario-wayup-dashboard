import io, re, os, requests, pandas as pd, streamlit as st, sys
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Sistema de Conteo de Inventario Físico con Tablet - WayUP",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- CSS -----------------
st.markdown("""
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
#MainMenu{visibility:hidden;} footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>📦 Dashboard Inventario – WayUP</h2>",
            unsafe_allow_html=True)

INDEX_FILE = "inventarios_index.csv"

# --------- cargar / inicializar índice local de inventarios ----------
if os.path.exists(INDEX_FILE):
    df_idx = pd.read_csv(INDEX_FILE)
else:
    # iniciar índice vacío; el usuario podrá pegar la URL y cargarla directamente
    df_idx = pd.DataFrame(columns=["Nombre", "URL"])
    df_idx.to_csv(INDEX_FILE, index=False)

# --------- sidebar: gestión de inventarios ----------
with st.sidebar:
    st.subheader("📁 Gestionar inventarios")
    nuevo_nombre = st.text_input("Nombre inventario")
    nueva_url = st.text_input("URL OneDrive del Excel")
    if st.button("➕ Guardar inventario"):
        if nuevo_nombre and nueva_url:
            df_idx = pd.concat(
                [df_idx, pd.DataFrame({"Nombre":[nuevo_nombre], "URL":[nueva_url]})],
                ignore_index=True
            )
            df_idx.to_csv(INDEX_FILE, index=False)
            st.success("Inventario guardado. Recarga la página para verlo en la lista.")
        else:
            st.warning("Completa Nombre y URL.")

# --------- selección de inventario ----------
c_top1, c_top2 = st.columns([2,1])
with c_top1:
    if not df_idx.empty:
        nombre_sel = st.selectbox("Archivo de inventario", df_idx["Nombre"])
    else:
        nombre_sel = None
with c_top2:
    if st.button("🔄 Actualizar datos"):
        st.rerun()

if df_idx.empty:
    # permitir carga directa por URL cuando no hay inventarios guardados
    url_direct = st.text_input("Pega la URL del archivo en OneDrive/SharePoint")
    if not url_direct:
        st.info("No hay inventarios guardados. Pega la URL del archivo en la caja de texto y presiona 'Cargar'.")
        if st.button("Cargar desde URL"):
            st.warning("Pega primero la URL.")
        st.stop()
    if st.button("Cargar desde URL"):
        base_url = url_direct
    else:
        st.stop()
    DOWNLOAD_URL = base_url if "download=1" in base_url else base_url + ("&download=1" if "?" in base_url else "?download=1")
    st.caption(f"🔗 Fuente: {base_url}")
else:
    fila_sel = df_idx[df_idx["Nombre"] == nombre_sel].iloc[0]
    base_url = fila_sel["URL"]
    DOWNLOAD_URL = base_url if "download=1" in base_url else \
                   base_url + ("&download=1" if "?" in base_url else "?download=1")
    st.caption(f"🔗 Fuente: {nombre_sel}")

# ----------------- funciones aux -----------------
def limpiar(c): return re.sub(r"\s+","",c).lower()
def col_cantidad(df):
    for c in df.columns:
        x=limpiar(c)
        if x=="cantidad": return c
    for c in df.columns:
        x=limpiar(c)
        if "cantidad" in x and "contar" not in x: return c
    return None
def col_contar(df):
    for c in df.columns:
        x=limpiar(c)
        if "cantidad" in x and "contar" in x: return c
    return None
def col_producto(df):
    for c in df.columns:
        x=limpiar(c)
        if "cod" in x and "producto" in x: return c
    return None

# ----------------- descargar inventario -----------------
def _flatten_cols(cols):
    if isinstance(cols, pd.MultiIndex):
        return [" ".join([str(x) for x in t if str(x) and str(x) != "nan"]).strip() for t in cols]
    return [str(c) for c in cols]

def _detect_and_read_excel(content):
    # intenta leer como excel (hoja por defecto). Si las cabeceras están en otra fila,
    # busca dentro de las primeras filas una que contenga palabras clave como 'cantidad'.
    try:
        df_try = pd.read_excel(io.BytesIO(content))
    except Exception:
        # intenta como csv por si acaso
        try:
            s = content.decode("utf-8", errors="replace")
            return pd.read_csv(io.StringIO(s))
        except Exception as e:
            raise

    # normalizar columnas multiindex
    df_try.columns = _flatten_cols(df_try.columns)

    # si no detectamos columnas clave, buscar fila de encabezado dentro de las primeras 6 filas
    def _has_key_cols(dframe):
        return (col_cantidad(dframe) is not None) and (col_contar(dframe) is not None)

    if _has_key_cols(df_try):
        return df_try

    # leer sin header para inspeccionar filas
    try:
        raw = pd.read_excel(io.BytesIO(content), header=None)
    except Exception:
        return df_try

    max_check = min(6, len(raw))
    for r in range(max_check):
        row = raw.iloc[r].astype(str).fillna("").tolist()
        cleaned = [re.sub(r"\s+","",str(x)).lower() for x in row]
        # si alguna celda de la fila contiene 'cantidad' o 'codproducto' etc.
        if any(("cantidad" in c) or ("cod" in c and "producto" in c) for c in cleaned):
            # relectura usando esa fila como header
            try:
                df_new = pd.read_excel(io.BytesIO(content), header=r)
                df_new.columns = _flatten_cols(df_new.columns)
                return df_new
            except Exception:
                continue

    return df_try

df = None
try:
    resp = requests.get(DOWNLOAD_URL, timeout=30)
    resp.raise_for_status()
    df = _detect_and_read_excel(resp.content)
except requests.exceptions.RequestException as e:
    st.error(f"❌ Error descargando inventario: {e}")
    st.stop()
    raise SystemExit(1)
except Exception as e:
    st.error(f"❌ Error leyendo inventario: {e}")
    st.stop()
    raise SystemExit(1)

# asegurar que tenemos un DataFrame válido
if df is None:
    st.error("❌ No se pudo leer el inventario.")
    raise SystemExit(1)

# limpiar y normalizar nombres de columna
df.columns = [c.strip() for c in df.columns]
# ---- Alias y UI de mapeo de columnas ----
CANONICAL = [
    "Cliente","Cliente Nombre","Cod. Producto","Descripción","Familia",
    "Contenedor","Lote","Tratamiento","F. Expiración","fecha recepcion",
    "UDM","Cantidad","Cantidad a contar","Diferencias","Cant. Reservada",
    "pedido","Ubicación","Etiqueta","Contador"
]

ALIASES = {
    # clave: lista de variantes
    "cantidad":["cant","cantidad","cantidad_sistema","sistema","stock"],
    "cantidad_a_contar":["cantidadacontar","cantidad_a_contar","contado","cantidad contar","cantidad_a_contar","cantidad_a_contar"],
    "cod_producto":["codproducto","cod. producto","cod producto","codigo producto","codigo_producto"],
    "contador":["contador","contadores","user","person"]
}

def _auto_map(df):
    # intenta mapear usando heurísticas
    mapping = {}
    for c in df.columns:
        key = limpiar(c)
        if key in ("cantidad", "cant") and "cantidad" in key:
            mapping[c] = "Cantidad"
        if "cantidad" in key and "contar" in key:
            mapping[c] = "Cantidad a contar"
        if "cod" in key and "producto" in key:
            mapping[c] = "Cod. Producto"
        if "contador" in key:
            mapping[c] = "Contador"
        if "cliente"==key or key.startswith("cliente"):
            mapping[c] = "Cliente"
        if "ubicacion" in key or "ubicación" in key:
            mapping[c] = "Ubicación"
    return mapping

# mostrar UI para confirmar/ajustar mapeo
with st.expander("🔧 Ver / ajustar mapeo de columnas detectado", expanded=False):
    auto = _auto_map(df)
    cols_opts = ["(no asignar)"] + list(df.columns)
    user_map = {}
    for canon in ["Cantidad","Cantidad a contar","Cod. Producto","Contador","Cliente","Ubicación"]:
        default = "(no asignar)"
        # buscar predeterminado en auto
        for k,v in auto.items():
            if v==canon:
                default = k
                break
        sel = st.selectbox(f"Columna para '{canon}'", cols_opts, index=cols_opts.index(default) if default in cols_opts else 0)
        if sel != "(no asignar)":
            user_map[sel] = canon

    if st.button("✔️ Aplicar mapeo"):
        if user_map:
            df = df.rename(columns=user_map)
            st.success("Mapeo aplicado.")
        else:
            st.info("No se aplicaron cambios.")

# volver a detectar columnas clave
c_cant = col_cantidad(df)
c_cont = col_contar(df)
if not c_cant or not c_cont:
    st.error("No se detectan columnas 'Cantidad' o 'Cantidad a contar'. Revisa el mapeo de columnas.")
    st.write("Columnas detectadas:", list(df.columns)); st.stop()

df[c_cant] = pd.to_numeric(df[c_cant], errors="coerce").fillna(0)
df[c_cont] = pd.to_numeric(df[c_cont], errors="coerce")  # NaN si vacío

# diferencias solo si Cantidad a contar NO es nulo
df["Dif_calc"] = df.apply(
    lambda x: (x[c_cont] - x[c_cant]) if pd.notna(x[c_cont]) else 0,
    axis=1
)
df["Diferencias"] = df["Dif_calc"].astype(int)

tot_sist = df[c_cant].sum()
tot_cont = df[c_cont].sum(skipna=True)
tot_dif = df["Dif_calc"].sum()
pct_avance = (tot_cont/tot_sist*100) if tot_sist else 0
pct_dif = (tot_dif/tot_sist*100) if tot_sist else 0

# ----------------- KPIs -----------------
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Sistema", f"{tot_sist:,.0f}")
k2.metric("Contado", f"{tot_cont:,.0f}")
k3.metric("Dif. total", f"{tot_dif:,.0f}")
k4.metric("% Dif.", f"{pct_dif:.2f}%")
k5.metric("% Avance", f"{pct_avance:.2f}%")
st.progress(min(pct_avance/100,1.0))
st.markdown("---")

tab_resumen, tab_detalle = st.tabs(["📊 Visión general","📄 Detalle & filtros"])

with tab_resumen:
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("#### 🎯 Avance general")
        pct_g = max(0,min(pct_avance,100))
        fig,ax = plt.subplots(figsize=(3.5,3.5))
        ax.pie([pct_g,100-pct_g],colors=["#22c55e","#e5e7eb"],
               startangle=90,counterclock=False,
               wedgeprops={"width":0.32})
        ax.text(0,0,f"{pct_g:.1f}%",ha="center",va="center",
                fontsize=18,color="#16a34a",fontweight="bold")
        ax.set(aspect="equal"); plt.tight_layout(); st.pyplot(fig)
    with c2:
        st.markdown("#### 🧍 Avance por contador")
        if "Contador" in df.columns:
            grp = df.groupby("Contador").agg(
                sist=(c_cant,"sum"),
                cont=(c_cont,"sum")
            )
            grp["pct"] = grp.apply(
                lambda x:(x["cont"]/x["sist"]*100) if x["sist"] else 0,axis=1
            )
            cont_sel = st.selectbox("Selecciona contador", grp.index)
            pct_c = grp.loc[cont_sel,"pct"]
            fig2,ax2 = plt.subplots(figsize=(3.5,3.5))
            ax2.pie([pct_c,100-pct_c],colors=["#3b82f6","#e5e7eb"],
                    startangle=90,counterclock=False,
                    wedgeprops={"width":0.4})
            ax2.text(0,0,f"{pct_c:.1f}%",ha="center",va="center",
                     fontsize=18,color="#1d4ed8",fontweight="bold")
            ax2.set(aspect="equal"); plt.tight_layout(); st.pyplot(fig2)
        else:
            st.info("No existe columna 'Contador'.")

    st.markdown("---")
    st.markdown("#### 🔎 Top 15 productos con mayor diferencia absoluta")
    c_prod = col_producto(df)
    if c_prod:
        dif = df.groupby(c_prod)["Dif_calc"].sum()
        dif_abs = dif.abs().sort_values(ascending=False).head(15)
        fig3,ax3 = plt.subplots(figsize=(7,4))
        cmap = plt.get_cmap("tab20")
        colors = [cmap(i) for i in range(len(dif_abs))]
        ax3.barh(dif_abs.index,dif_abs.values,color=colors)
        ax3.invert_yaxis()
        ax3.set_xlabel("Diferencia absoluta")
        ax3.set_ylabel("Producto")
        ax3.grid(axis="x",linestyle="--",alpha=0.3)
        plt.tight_layout(); st.pyplot(fig3)
    else:
        st.info("No se encontró columna de código de producto.")

with tab_detalle:
    with st.expander("Filtros"):
        conts = df["Contador"].dropna().unique() if "Contador" in df.columns else []
        clis = df["Cliente"].dropna().unique() if "Cliente" in df.columns else []
        ubis = df["Ubicación"].dropna().unique() if "Ubicación" in df.columns else []
        f_cont = st.multiselect("Contador", conts)
        f_cli = st.multiselect("Cliente", clis)
        f_ubi = st.multiselect("Ubicación", ubis)

    df_f = df.copy()
    if f_cont and "Contador" in df_f.columns:
        df_f = df_f[df_f["Contador"].isin(f_cont)]
    if f_cli and "Cliente" in df_f.columns:
        df_f = df_f[df_f["Cliente"].isin(f_cli)]
    if f_ubi and "Ubicación" in df_f.columns:
        df_f = df_f[df_f["Ubicación"].isin(f_ubi)]

    st.markdown("#### 📄 Detalle de inventario")

    # ---- Validaciones y resaltado ----
    # flags
    df_f = df_f.copy()
    df_f["_flag_diferencia"] = df_f["Dif_calc"].abs() > 0
    df_f["_flag_negativa"] = df_f["Dif_calc"] < 0
    # duplicados por producto si existe
    prod_col = col_producto(df_f)
    if prod_col:
        df_f["_dup_producto"] = df_f.duplicated(subset=[prod_col], keep=False)
    else:
        df_f["_dup_producto"] = False

    # mostrar botones de exportación
    dif_only = df_f[df_f["Dif_calc"].abs() != 0]
    csv_all = df_f.to_csv(index=False).encode("utf-8")
    csv_dif = dif_only.to_csv(index=False).encode("utf-8")
    to_xlsx = lambda dfx: _to_excel_bytes(dfx)

    cexp1, cexp2 = st.columns([1,1])
    with cexp1:
        st.download_button("Exportar todo (CSV)", data=csv_all, file_name="inventario_detalle.csv", mime="text/csv")
    with cexp2:
        st.download_button("Exportar diferencias (CSV)", data=csv_dif, file_name="inventario_diferencias.csv", mime="text/csv")

    # helper para excel
    def _to_excel_bytes(dfx):
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            dfx.to_excel(writer, index=False, sheet_name="Hoja1")
        return bio.getvalue()

    cexp3, cexp4 = st.columns([1,1])
    with cexp3:
        st.download_button("Exportar todo (XLSX)", data=to_xlsx(df_f), file_name="inventario_detalle.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with cexp4:
        st.download_button("Exportar diferencias (XLSX)", data=to_xlsx(dif_only), file_name="inventario_diferencias.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # estilo para resaltar
    def highlight_rows(row):
        styles = ["" for _ in row.index]
        if row.get("_flag_diferencia", False):
            # resaltar fila entera en amarillo claro
            return ["background-color: #fff7cd" for _ in row.index]
        return styles

    # preparar DataFrame para visualización: quitar columnas internas y reemplazar NaN/None por cadena vacía
    vis_cols = [c for c in df_f.columns if not c.startswith("_flag_")]
    df_display = df_f[vis_cols].fillna("")

    # crear Styler a partir del DataFrame limpio
    sty = df_display.style
    # aplicar highlight a filas con diferencia (usar la columna original en df_f)
    sty = sty.apply(lambda r: ["background-color: #fff7cd" if abs(df_f.loc[r.name, "Dif_calc"])>0 else "" for _ in r.index], axis=1)
    # color para valores numéricos negativos
    sty = sty.applymap(lambda v: "color: red" if isinstance(v, (int, float)) and v < 0 else "")

    st.write(sty)


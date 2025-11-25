import pandas as pd
import streamlit as st

st.set_page_config(page_title="Dashboard Inventario", layout="wide")
st.title("📦 Dashboard Inventario – WayUP")

file = st.file_uploader("Sube el Excel de inventario", type=["xlsx", "xls"])

if file is not None:
    df = pd.read_excel(file)
    df.columns = [c.strip() for c in df.columns]

    for col in ["Cantidad", "Cantidad a contar", "Diferencias"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # (supuesto) Dif = Cantidad a contar - Cantidad
    df["Dif_calc"] = df["Cantidad a contar"] - df["Cantidad"]

    tot_sist = df["Cantidad"].sum()
    tot_cont = df["Cantidad a contar"].sum()
    tot_dif = df["Dif_calc"].sum()

    pct_avance = (tot_cont / tot_sist * 100) if tot_sist else 0
    pct_dif = (tot_dif / tot_sist * 100) if tot_sist else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cantidad sistema", f"{tot_sist:,.0f}")
    c2.metric("Cantidad contada", f"{tot_cont:,.0f}")
    c3.metric("Diferencia total", f"{tot_dif:,.0f}")
    c4.metric("% diferencia", f"{pct_dif:.2f}%")

    st.progress(min(pct_avance/100, 1))
    st.caption(f"Avance de conteo: {pct_avance:.2f}%")

    with st.expander("Filtros"):
        cont = st.multiselect("Contador", df["Contador"].unique())
        cli = st.multiselect("Cliente", df["Cliente"].unique())
        ubic = st.multiselect("Ubicación", df["Ubicación"].unique())

    df_f = df.copy()
    if cont: df_f = df_f[df_f["Contador"].isin(cont)]
    if cli: df_f = df_f[df_f["Cliente"].isin(cli)]
    if ubic: df_f = df_f[df_f["Ubicación"].isin(ubic)]

    st.subheader("Detalle inventario")
    st.dataframe(df_f, use_container_width=True)
else:
    st.info("Sube el archivo Excel exportado desde WayUP.")

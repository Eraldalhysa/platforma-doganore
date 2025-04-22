
import streamlit as st
import pandas as pd
import altair as alt

# Ngarko të dhënat
df = pd.read_csv("te_dhena_doganore_simuluara.csv")

st.set_page_config(page_title="Të dhëna doganore - Shqip", layout="wide")

st.title("📊 Platforma e të Dhënave mbi Importet dhe Eksportet Doganore")

# Sidebar - Filtrim
st.sidebar.header("🔍 Filtrim")
vit = st.sidebar.selectbox("Zgjidh vitin", sorted(df["Viti"].unique()))
lloji = st.sidebar.selectbox("Zgjidh llojin", ["Import", "Eksport"])
kategoria = st.sidebar.multiselect("Zgjidh kategoritë", options=df["Kategoria"].unique(), default=df["Kategoria"].unique())

# Filtrim sipas përzgjedhjeve
df_filtered = df[(df["Viti"] == vit) & (df["Lloji"] == lloji) & (df["Kategoria"].isin(kategoria))]

# Grafik i volumit mujor
st.subheader("📈 Volumi mujor i {}-eve për vitin {}".format(lloji.lower(), vit))
chart = alt.Chart(df_filtered).mark_line(point=True).encode(
    x=alt.X("Muaji:O", title="Muaji"),
    y=alt.Y("Sasia (kg):Q", title="Sasia (kg)", scale=alt.Scale(zero=False)),
    color="Kategoria:N",
    tooltip=["Kategoria", "Muaji", "Sasia (kg)", "Vlera (€)"]
).properties(width=800, height=400)
st.altair_chart(chart, use_container_width=True)

# Tabela e të dhënave
st.subheader("📋 Tabela e të dhënave")
st.dataframe(df_filtered, use_container_width=True)

# Shkarkimi i të dhënave
st.download_button("📥 Shkarko të dhënat në CSV", data=df_filtered.to_csv(index=False), file_name="te_dhena_filtruara.csv", mime="text/csv")

import streamlit as st
import pandas as pd
import altair as alt

# Funksion për të lexuar CSV me encoding të ndryshëm
def load_csv(file_path):
    encodings = ["utf-8", "latin1", "ISO-8859-1", "cp1252"]
    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except Exception as e:
            st.write(f"⚠️ Nuk funksionoi me encoding: {enc}")
    st.error("❌ Nuk u arrit të lexohet CSV-ja me asnjë encoding të njohur.")
    return pd.DataFrame()

# Ngarko të dhënat
df = load_csv("te_dhena_doganore_simuluara.csv")

if not df.empty:
    st.set_page_config(page_title="Të dhëna doganore - Shqip", layout="wide")

    st.title("📊 Platforma e të Dhënave mbi Importet dhe Eksportet Doganore")

    # Sidebar - Filtrim
    st.sidebar.header("🔍 Filtrim")
    vit = st.sidebar.selectbox("Zgjidh vitin", sorted(df["Viti"].unique()))
    lloji = st.sidebar.selectbox("Zgjidh llojin", ["Import", "Eksport"])
    kategoria = st.sidebar.multiselect("Zgjidh kategoritë", options=df["Kategoria"].unique(), default=df["Kategoria"].unique())

    # Filtrim sipas përzgjedhjeve
    df_filtered = df[(df["Viti"] == vit) & (df["Lloji"] == lloji) & (df["Kategoria"].isin(kategoria))]

    # Grafik i volumit mujor (line chart)
    st.subheader(f"📈 Volumi mujor i {lloji.lower()}-eve për vitin {vit}")
    chart_line = alt.Chart(df_filtered).mark_line(point=True).encode(
        x=alt.X("Muaji:O", title="Muaji"),
        y=alt.Y("Sasia (kg):Q", title="Sasia (kg)", scale=alt.Scale(zero=False)),
        color="Kategoria:N",
        tooltip=["Kategoria", "Muaji", "Sasia (kg)", "Vlera (€)"]
    ).properties(width=800, height=400)
    st.altair_chart(chart_line, use_container_width=True)

    # Grafik në formë kolone (bar chart)
    chart_bar = alt.Chart(df_filtered).mark_bar().encode(
        x=alt.X("Muaji:O", title="Muaji"),
        y=alt.Y("Sasia (kg):Q", title="Sasia (kg)", scale=alt.Scale(zero=False)),
        color="Kategoria:N",
        tooltip=["Kategoria", "Muaji", "Sasia (kg)", "Vlera (€)"]
    ).properties(width=800, height=400)
    st.altair_chart(chart_bar, use_container_width=True)

    # Tabela e të dhënave
    st.subheader("📋 Tabela e të dhënave")
    st.dataframe(df_filtered, use_container_width=True)

    # Shkarkimi i të dhënave
    st.download_button(
        "📥 Shkarko të dhënat në CSV", 
        data=df_filtered.to_csv(index=False), 
        file_name="te_dhena_filtruara.csv", 
        mime="text/csv"
    )

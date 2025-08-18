import streamlit as st
import pandas as pd
import altair as alt

# Funksion për të lexuar CSV me encoding të ndryshëm
def load_csv(file_path):
    encodings = ["utf-8", "latin1", "ISO-8859-1", "cp1252"]
    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except Exception:
            continue
    st.error("❌ Nuk u arrit të lexohet CSV-ja me asnjë encoding të njohur.")
    return pd.DataFrame()

# Ngarko të dhënat
df = load_csv("te_dhena_doganore_simuluara.csv")

if not df.empty:
    st.set_page_config(page_title="Të dhëna doganore - Shqip", layout="wide")

    st.title("📊 Platforma e të Dhënave mbi Importet dhe Eksportet Doganore")

    # ✅ Pastrimi i kolonave
    df["Muaji"] = pd.to_numeric(df["Muaji"], errors="coerce").fillna(0).astype(int)
    df["Sasia (kg)"] = pd.to_numeric(df["Sasia (kg)"], errors="coerce")
    df["Vlera (€)"] = pd.to_numeric(df["Vlera (€)"], errors="coerce")

    # ✅ Konvertimi i muajve në shqip
    muajt_shqip = {
        1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
        7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
    }
    df["Muaji"] = df["Muaji"].map(muajt_shqip)

    # Sidebar - Filtrim
    st.sidebar.header("🔍 Filtrim")
    vit = st.sidebar.selectbox("Zgjidh vitin", sorted(df["Viti"].unique()))
    lloji = st.sidebar.selectbox("Zgjidh llojin", ["Import", "Eksport"])
    kategoria = st.sidebar.multiselect("Zgjidh kategoritë", options=df["Kategoria"].unique(), default=df["Kategoria"].unique())

    # Filtrim sipas përzgjedhjeve
    df_filtered = df[(df["Viti"] == vit) & (df["Lloji"] == lloji) & (df["Kategoria"].isin(kategoria))]

    if df_filtered.empty:
        st.warning("⚠️ Nuk ka të dhëna për këtë filtër.")
    else:
        # Grafik i volumit mujor (line chart)
        st.subheader(f"📈 Volumi mujor i {lloji.lower()}-eve për vitin {vit}")
        chart_line = alt.Chart(df_filtered).mark_line(point=True).encode(
            x=alt.X("Muaji:N", title="Muaji", sort=list(muajt_shqip.values())),
            y=alt.Y("Sasia (kg):Q", title="Sasia (kg)", scale=alt.Scale(zero=False)),
            color="Kategoria:N",
            tooltip=["Kategoria", "Muaji", "Sasia (kg)", "Vlera (€)"]
        ).properties(width=800, height=400)
        st.altair_chart(chart_line, use_container_width=True)

        # Grafik në formë kolone (bar chart)
        chart_bar = alt.Chart(df_filtered).mark_bar().encode(
            x=alt.X("Muaji:N", title="Muaji", sort=list(muajt_shqip.values())),
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

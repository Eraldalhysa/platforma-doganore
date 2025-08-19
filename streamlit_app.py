import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Analiza Doganore", layout="wide")

st.title("📊 Pesha % sipas Kodit Doganor (Import vs Eksport)")

# Ngarkimi i të dhënave
uploaded_file = st.file_uploader("Ngarko skedarin CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Kontrollojmë që kolonat ekzistojnë
    required_cols = ["Viti", "Kodi_doganor", "Lloji", "Vlera"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"❌ Duhet të ketë kolonat: {required_cols}")
    else:
        # Zgjedh vitin
        year = st.selectbox("Zgjidh vitin", sorted(df["Viti"].unique(), reverse=True))

        # Filtro sipas vitit
        df_year = df[df["Viti"] == year]

        # Zgjedh Import ose Eksport
        trade_type = st.radio("Zgjidh tipin", ["Import", "Eksport"])
        df_filtered = df_year[df_year["Lloji"] == trade_type]

        if df_filtered.empty:
            st.warning("⚠️ Nuk ka të dhëna për këtë vit dhe tip.")
        else:
            # Grupimi sipas kodit doganor
            grouped = df_filtered.groupby("Kodi_doganor")["Vlera"].sum()

            # Shfaq tabelën
            st.dataframe(grouped.reset_index().sort_values("Vlera", ascending=False))

            # Vizato byrekun
            fig, ax = plt.subplots(figsize=(7, 7))
            ax.pie(grouped, labels=grouped.index, autopct='%1.1f%%', startangle=90)
            ax.set_title(f"Pesha % sipas Kodit Doganor ({trade_type}, {year})")
            st.pyplot(fig)
else:
    st.info("ℹ️ Ngarko një CSV me kolonat: Viti, Kodi_doganor, Lloji, Vlera")


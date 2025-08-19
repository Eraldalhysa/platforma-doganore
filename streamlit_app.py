import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# =========================
# TITULLI
# =========================
st.set_page_config(page_title="Analiza Doganore", layout="wide")
st.title("📊 Analiza e Importeve dhe Eksporteve sipas Kodit Doganor")

# =========================
# UPLOAD FILE
# =========================
uploaded_file = st.file_uploader("Ngarko file-in (Excel ose CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # Lexim file sipas formatit
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Kontrollo kolonat e domosdoshme
    required_cols = ["Viti", "Kodi_doganor", "Import", "Eksport"]
    if not all(col in df.columns for col in required_cols):
        st.error("❌ File duhet të ketë kolonat: Viti, Kodi_doganor, Import, Eksport")
    else:
        # =========================
        # ZGJEDHJA E VITIT
        # =========================
        vitet = sorted(df["Viti"].unique())
        viti = st.selectbox("Zgjidh vitin", vitet)
        df_viti = df[df["Viti"] == viti]

        # =========================
        # AGREGIM SIPAS KODIT DOGANOR
        # =========================
        grupi = df_viti.groupby("Kodi_doganor")[["Import", "Eksport"]].sum()
        grupi["% Import"] = 100 * grupi["Import"] / grupi["Import"].sum()
        grupi["% Eksport"] = 100 * grupi["Eksport"] / grupi["Eksport"].sum()

        # =========================
        # SHFAQJA E GRAFIKËVE
        # =========================
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Importet sipas Kodit Doganor")
            fig1, ax1 = plt.subplots(figsize=(6, 6))
            ax1.pie(
                grupi["Import"], 
                labels=grupi.index, 
                autopct="%.1f%%", 
                startangle=90
            )
            ax1.set_title(f"Pesha % e Importeve ({viti})")
            st.pyplot(fig1)

        with col2:
            st.subheader("Eksportet sipas Kodit Doganor")
            fig2, ax2 = plt.subplots(figsize=(6, 6))
            ax2.pie(
                grupi["Eksport"], 
                labels=grupi.index, 
                autopct="%.1f%%", 
                startangle=90
            )
            ax2.set_title(f"Pesha % e Eksporteve ({viti})")
            st.pyplot(fig2)

        # =========================
        # TABELA
        # =========================
        st.subheader("📑 Tabela me totalet dhe %")
        st.dataframe(grupi)

        # =========================
        # SHKARKIMI NE EXCEL
        # =========================
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=True, sheet_name="Raporti")
            return output.getvalue()

        excel_bytes = to_excel(grupi)
        st.download_button(
            label="⬇️ Shkarko raportin në Excel",
            data=excel_bytes,
            file_name=f"raporti_doganor_{viti}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

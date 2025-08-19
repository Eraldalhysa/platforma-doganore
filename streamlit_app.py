import streamlit as st
import pandas as pd
import altair as alt

# -------------------------
# Funksion për të lexuar CSV me encoding të ndryshëm
# -------------------------
def load_csv(file_path):
    encodings = ["utf-8", "latin1", "ISO-8859-1", "cp1252"]
    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except Exception:
            continue
    st.error("❌ Nuk u arrit të lexohet CSV-ja me asnjë encoding të njohur.")
    return pd.DataFrame()

# -------------------------
# Ngarko të dhënat
# -------------------------
df = load_csv("te_dhena_doganore_simuluara.csv")

if not df.empty:
    st.set_page_config(page_title="Të dhëna doganore - Shqip", layout="wide")
    st.title("📊 Platforma e të Dhënave mbi Importet dhe Eksportet Doganore")

    # Normalizimi i emrave të kolonave
    df = df.rename(columns=lambda x: x.strip())
    df = df.rename(columns={
        "Vlera (lekë)": "Vlera",
        "Vlera (€)": "Vlera",
        "Value": "Vlera",
        "Sasia": "Sasia (kg)"
    })

    # Pastrimi i kolonave numerike
    for col in ["Muaji", "Sasia (kg)", "Vlera"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Konvertimi i muajve në shqip
    muajt_shqip = {
        1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
        7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
    }
    if "Muaji" in df.columns:
        df["Muaji"] = df["Muaji"].map(muajt_shqip)
        df["Muaji"] = df["Muaji"].fillna("Pa të dhëna")

    # -------------------------
    # Sidebar - Filtrim
    # -------------------------
    st.sidebar.header("🔍 Filtrim")
    vit = st.sidebar.selectbox("Zgjidh vitin", sorted(df["Viti"].dropna().unique())) if "Viti" in df.columns else None
    lloji = st.sidebar.selectbox("Zgjidh llojin", ["Import", "Eksport"])
    
    if "Kategoria" in df.columns:
        default_kategori = df["Kategoria"].dropna().unique()[:3]  # 2-3 produkte default
        kategoria = st.sidebar.multiselect(
            "Zgjidh kategoritë",
            options=df["Kategoria"].dropna().unique(),
            default=default_kategori
        )
    else:
        kategoria = []

    # Filtrim sipas përzgjedhjeve
    df_filtered = df.copy()
    if vit is not None and "Viti" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Viti"] == vit]
    if "Lloji" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Lloji"] == lloji]
    if kategoria and "Kategoria" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Kategoria"].isin(kategoria)]

    if df_filtered.empty:
        st.warning("⚠️ Nuk ka të dhëna për këtë filtër.")
    else:
        # Siguro vlerat numerike pa NaN
        df_filtered["Sasia (kg)"] = df_filtered["Sasia (kg)"].fillna(0)
        if "Vlera" in df_filtered.columns:
            df_filtered["Vlera"] = df_filtered["Vlera"].fillna(0)

        # Renditja e muajve për grafikun mujor
        muaj_order = [m for m in muajt_shqip.values() if "Muaji" in df_filtered.columns and m in df_filtered["Muaji"].unique()]

        # --- Grafik mujor (line chart) ---
        if "Muaji" in df_filtered.columns:
            st.subheader(f"📈 Volumi mujor i {lloji.lower()}-eve për vitin {vit}")
            chart_line = alt.Chart(df_filtered).mark_line(point=True).encode(
                x=alt.X("Muaji:N", title="Muaji", sort=muaj_order),
                y=alt.Y("Sasia (kg):Q", title="Sasia (kg)", scale=alt.Scale(zero=False)),
                color="Kategoria:N" if "Kategoria" in df_filtered.columns else alt.value("blue"),
                tooltip=["Kategoria", "Muaji", "Sasia (kg)", "Vlera"]
                if "Kategoria" in df_filtered.columns and "Vlera" in df_filtered.columns
                else ["Muaji", "Sasia (kg)"]
            ).properties(width=800, height=400)
            st.altair_chart(chart_line, use_container_width=True)

        # --- Grafik vjetor i ndarë për Import dhe Eksport ---
        if "Lloji" in df.columns and "Kategoria" in df.columns and "Viti" in df.columns:
            st.subheader("📊 Volumi vjetor sipas kategorive (2024 vs 2025)")
            for lloji_temp in ["Import", "Eksport"]:
                st.markdown(f"#### {lloji_temp}")
                df_vjetor = df[df["Lloji"] == lloji_temp].copy()
                if kategoria:
                    df_vjetor = df_vjetor[df_vjetor["Kategoria"].isin(kategoria)]
                df_vjetor["Sasia (kg)"] = df_vjetor["Sasia (kg)"].fillna(0)

                df_vjetor_sum = df_vjetor.groupby(["Kategoria", "Viti"], as_index=False)["Sasia (kg)"].sum()
                kategoria_order = df_vjetor_sum.groupby("Kategoria")["Sasia (kg)"].sum().sort_values(ascending=False).index.tolist()

                chart_bar = alt.Chart(df_vjetor_sum).mark_bar().encode(
                    x=alt.X("Kategoria:N", title="Kategoria", sort=kategoria_order),
                    y=alt.Y("Sasia (kg):Q", title="Sasia totale (kg)", scale=alt.Scale(zero=False)),
                    color=alt.Color("Viti:N", title="Viti"),
                    xOffset=alt.XOffset("Viti:N"),
                    tooltip=["Viti", "Kategoria", "Sasia (kg)"]
                ).properties(width=700, height=400)
                st.altair_chart(chart_bar, use_container_width=True)

        # --- Grafik krahasues Import vs Eksport për një vit të zgjedhur ---
        if "Viti" in df.columns and "Lloji" in df.columns and "Kategoria" in df.columns:
            st.subheader(f"📦 Import vs Eksport sipas kategorive për vitin {vit}")
            df_year = df[df["Viti"] == vit].copy()
            if kategoria:
                df_year = df_year[df_year["Kategoria"].isin(kategoria)]
            df_year["Sasia (kg)"] = df_year["Sasia (kg)"].fillna(0)

            df_year_sum = df_year.groupby(["Kategoria", "Lloji"], as_index=False)["Sasia (kg)"].sum()
            kategoria_order_year = df_year_sum.groupby("Kategoria")["Sasia (kg)"].sum().sort_values(ascending=False).index.tolist()

            chart_import_export = alt.Chart(df_year_sum).mark_bar().encode(
                x=alt.X("Kategoria:N", title="Kategoria", sort=kategoria_order_year),
                y=alt.Y("Sasia (kg):Q", title="Sasia totale (kg)", scale=alt.Scale(zero=False)),
                color=alt.Color("Lloji:N", title="Lloji"),
                xOffset=alt.XOffset("Lloji:N"),
                tooltip=["Kategoria", "Lloji", "Sasia (kg)"]
            ).properties(width=700, height=400)
            st.altair_chart(chart_import_export, use_container_width=True)

        # -------------------------
        # 🟢 GRAFIK BYREK: Pesha % sipas "Kodi doganor"
        # -------------------------
        # Gjej kolonën e kodit doganor nëse ekziston me emër të ndryshëm
        possible_hs_cols = [
            "Kodi doganor", "Kodi_doganor", "KodiDoganor",
            "Kodi HS", "HS Code", "HS_Code", "HS", "Kodi"
        ]
        hs_col = next((c for c in possible_hs_cols if c in df.columns), None)

        st.subheader("🥧 Pesha % sipas kodit doganor (Import vs Eksport)")

        if hs_col is None:
            st.info("ℹ️ Nuk u gjet kolona e kodit doganor (p.sh. 'Kodi doganor', 'HS Code'). Shto një kolonë me kodet për të parë byrekun.")
        else:
            # Të dhënat e vitit të zgjedhur
            df_year_hs = df[df["Viti"] == vit].copy()
            # Pastrim bazë
            df_year_hs["Sasia (kg)"] = df_year_hs["Sasia (kg)"].fillna(0)
            df_year_hs[hs_col] = df_year_hs[hs_col].fillna("Pa kod")

            # Agregim sipas kodi + lloji
            agg = df_year_hs.groupby([hs_col, "Lloji"], as_index=False)["Sasia (kg)"].sum()
            # Llogaritja e % brenda secilit Lloji (Import/Eksport)
            agg["Perc"] = agg.groupby("Lloji")["Sasia (kg)"].apply(lambda x: (x / x.sum()) * 100)

            # Dy kolona për dy byrekë
            c1, c2 = st.columns(2)

            # Import
            if (agg["Lloji"] == "Import").any():
                pie_import = alt.Chart(agg[agg["Lloji"] == "Import"]).mark_arc().encode(
                    theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                    color=alt.Color(f"{hs_col}:N", title="Kodi doganor"),
                    tooltip=[hs_col, alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                             alt.Tooltip("Sasia (kg):Q", title="Sasia (kg)", format=",.0f")]
                ).properties(title=f"Import - {vit}", width=400, height=400)
                c1.altair_chart(pie_import, use_container_width=True)
            else:
                c1.info(f"Nuk ka të dhëna Import për vitin {vit}.")

            # Eksport
            if (agg["Lloji"] == "Eksport").any():
                pie_export = alt.Chart(agg[agg["Lloji"] == "Eksport"]).mark_arc().encode(
                    theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                    color=alt.Color(f"{hs_col}:N", title="Kodi doganor"),
                    tooltip=[hs_col, alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                             alt.Tooltip("Sasia (kg):Q", title="Sasia (kg)", format=",.0f")]
                ).properties(title=f"Eksport - {vit}", width=400, height=400)
                c2.altair_chart(pie_export, use_container_width=True)
            else:
                c2.info(f"Nuk ka të dhëna Eksport për vitin {vit}.")

        # --- Tabela ---
        st.subheader("📋 Tabela e të dhënave")
        st.dataframe(df_filtered, use_container_width=True)

        # --- Shkarkim CSV ---
        st.download_button(
            "📥 Shkarko të dhënat në CSV",
            data=df_filtered.to_csv(index=False),
            file_name="te_dhena_filtruara.csv",
            mime="text/csv"
        )

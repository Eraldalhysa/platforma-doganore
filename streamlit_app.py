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
        default_kategori = df["Kategoria"].dropna().unique()[:3]
        kategoria = st.sidebar.multiselect(
            "Zgjidh kategoritë",
            options=df["Kategoria"].dropna().unique(),
            default=default_kategori
        )
    else:
        kategoria = []

    # --- Zgjedh kolonen e kodit doganor nga sidebar ---
    possible_hs_cols = [
        "Kodi doganor", "Kodi_doganor", "KodiDoganor",
        "Kodi HS", "HS Code", "HS_Code", "HS",
        "Kodi", "Kodi i mallrave", "HS6", "HS8", "Nomenklatura"
    ]
    lower_to_orig = {c.lower(): c for c in df.columns}
    candidates_found = []
    for cand in possible_hs_cols:
        if cand.lower() in lower_to_orig:
            candidates_found.append(lower_to_orig[cand.lower()])
    if not candidates_found:
        candidates_found = [c for c in df.columns if df[c].dtype == "object" or df[c].nunique() > 5]
    hs_col = st.sidebar.selectbox(
        "Kolona e kodit doganor (HS)",
        options=["(asnjë)"] + candidates_found,
        index=0 if not candidates_found else 1
    )
    if hs_col == "(asnjë)":
        hs_col = None

    # -------------------------
    # Filtrim sipas përzgjedhjeve
    # -------------------------
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
        df_filtered["Sasia (kg)"] = df_filtered["Sasia (kg)"].fillna(0)
        if "Vlera" in df_filtered.columns:
            df_filtered["Vlera"] = df_filtered["Vlera"].fillna(0)

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

        # --- Grafik vjetor (Import/Eksport) ---
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

               # --- Grafik krahasues Import vs Eksport ---
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
        # 🟢 GRAFIK BYREK – vlerë vjetore sipas KATEGORIVE (Import veç / Eksport veç)
        # -------------------------
        st.subheader("🥧 Pesha % sipas Kategorive (Import vs Eksport, bazë vjetore)")

        if all(col in df.columns for col in ["Viti", "Lloji", "Kategoria", "Vlera"]):
            # Vetëm VITI i zgjedhur (vjetor)
            df_year_cat = df[df["Viti"] == vit].copy()
            df_year_cat["Vlera"] = pd.to_numeric(df_year_cat["Vlera"], errors="coerce").fillna(0)
            df_year_cat["Kategoria"] = df_year_cat["Kategoria"].astype(str).str.strip().replace({"": "Pa kategori"})

            # Respekto filtrin nga sidebar (nëse janë përzgjedhur kategori)
            if kategoria:
                df_year_cat = df_year_cat[df_year_cat["Kategoria"].isin(kategoria)]

            # Agregim vjetor sipas Kategorisë dhe Llojit (Import/Eksport)
            agg_cat = df_year_cat.groupby(["Kategoria", "Lloji"], as_index=False)["Vlera"].sum()

            # Llogarit peshat % brenda secilit lloj
            def add_percent(df_lloji):
                total = df_lloji["Vlera"].sum()
                df_lloji = df_lloji.copy()
                df_lloji["Perc"] = (df_lloji["Vlera"] / total * 100) if total > 0 else 0
                return df_lloji

            imp = add_percent(agg_cat[agg_cat["Lloji"] == "Import"])
            eksp = add_percent(agg_cat[agg_cat["Lloji"] == "Eksport"])

            # Ngjyra konsistente mes dy byrekëve
            shared_domain = list(pd.concat([imp["Kategoria"], eksp["Kategoria"]]).drop_duplicates())
            color_scale = alt.Scale(domain=shared_domain)

            c1, c2 = st.columns(2)

            # Import
            if not imp.empty and imp["Vlera"].sum() > 0:
                pie_imp = alt.Chart(imp).mark_arc().encode(
                    theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                    color=alt.Color("Kategoria:N", title="Kategoria", scale=color_scale),
                    tooltip=[
                        alt.Tooltip("Kategoria:N", title="Kategoria"),
                        alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                        alt.Tooltip("Vlera:Q", title="Vlera", format=",.0f"),
                    ],
                ).properties(title=f"Import – {vit} (bazuar në VLERË)", width=420, height=420)
                c1.altair_chart(pie_imp, use_container_width=True)
            else:
                c1.info(f"Nuk ka të dhëna për Import në {vit}.")

            # Eksport
            if not eksp.empty and eksp["Vlera"].sum() > 0:
                pie_eks = alt.Chart(eksp).mark_arc().encode(
                    theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                    color=alt.Color("Kategoria:N", title="Kategoria", scale=color_scale),
                    tooltip=[
                        alt.Tooltip("Kategoria:N", title="Kategoria"),
                        alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                        alt.Tooltip("Vlera:Q", title="Vlera", format=",.0f"),
                    ],
                ).properties(title=f"Eksport – {vit} (bazuar në VLERË)", width=420, height=420)
                c2.altair_chart(pie_eks, use_container_width=True)
            else:
                c2.info(f"Nuk ka të dhëna për Eksport në {vit}.")
        else:
            st.info("ℹ️ Duhet të ekzistojnë kolonat: 'Viti', 'Lloji', 'Kategoria', 'Vlera'.")

        # -------------------------
        # 📋 Tabela dhe Shkarkim  (KUJDES: ky bllok është në të njëjtin indent si grafiqet më sipër)
        # -------------------------
        st.subheader("📋 Tabela e të dhënave")
        st.dataframe(df_filtered, use_container_width=True)

        st.download_button(
            "📥 Shkarko të dhënat në CSV",
            data=df_filtered.to_csv(index=False),
            file_name="te_dhena_filtruara.csv",
            mime="text/csv"
        )

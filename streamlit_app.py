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

        # -------------------------
        # 🟢 GRAFIK BYREK sipas kodit doganor (HS) — vetëm në bazë vjetore
        # -------------------------
        st.subheader("🥧 Pesha % sipas Kodit Doganor (Import vs Eksport)")

        if hs_col is None:
            st.info("ℹ️ Zgjidh një kolonë për kodet doganore (HS) nga sidebar që të shfaqet byreku.")
        else:
            # Zgjedh bazën e peshës: Sasia ose Vlera
            metrika = st.radio("Baza e peshës për %", ["Sasia (kg)", "Vlera"], horizontal=True)
            top_n = st.slider("Shfaq Top N kode (pjesa tjetër grup 'Të tjerët')", 3, 25, 10)

            # Merr të dhënat vetëm për vitin e zgjedhur
            df_year_hs = df[df["Viti"] == vit].copy()
            if metrika not in df_year_hs.columns:
                df_year_hs[metrika] = 0
            df_year_hs[metrika] = pd.to_numeric(df_year_hs[metrika], errors="coerce").fillna(0)
            df_year_hs[hs_col] = df_year_hs[hs_col].fillna("Pa kod").astype(str).str.strip()

            # Grupim sipas vitit, kodit doganor dhe tipit (Import/Eksport)
            agg = df_year_hs.groupby([hs_col, "Lloji"], as_index=False)[metrika].sum()
            agg.rename(columns={metrika: "Vlere"}, inplace=True)

            # Funksion për Top N + "Të tjerët"
            def topn_per_lloji(df_lloji, top_n):
                df_lloji = df_lloji.sort_values("Vlere", ascending=False)
                if len(df_lloji) > top_n:
                    top = df_lloji.head(top_n)
                    others_val = df_lloji["Vlere"].iloc[top_n:].sum()
                    others = pd.DataFrame({hs_col: ["Të tjerët"], "Lloji": [df_lloji["Lloji"].iloc[0]], "Vlere": [others_val]})
                    return pd.concat([top, others], ignore_index=True)
                return df_lloji

            agg_import = topn_per_lloji(agg[agg["Lloji"] == "Import"].copy(), top_n)
            agg_export = topn_per_lloji(agg[agg["Lloji"] == "Eksport"].copy(), top_n)

            for d in (agg_import, agg_export):
                total = d["Vlere"].sum()
                d["Perc"] = (d["Vlere"] / total * 100) if total > 0 else 0

            c1, c2 = st.columns(2)
            if not agg_import.empty and agg_import["Vlere"].sum() > 0:
                pie_import = alt.Chart(agg_import).mark_arc().encode(
                    theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                    color=alt.Color(f"{hs_col}:N", title="Kodi doganor"),
                    tooltip=[hs_col, alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                             alt.Tooltip("Vlere:Q", title=metrika, format=",.0f")]
                ).properties(title=f"Import - {vit} (baza: {metrika})", width=420, height=420)
                c1.altair_chart(pie_import, use_container_width=True)
            else:
                c1.info(f"Nuk ka të dhëna Import për vitin {vit}.")

            if not agg_export.empty and agg_export["Vlere"].sum() > 0:
                pie_export = alt.Chart(agg_export).mark_arc().encode(
                    theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                    color=alt.Color(f"{hs_col}:N", title="Kodi doganor"),
                    tooltip=[hs_col, alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                             alt.Tooltip("Vlere:Q", title=metrika, format=",.0f")]
                ).properties(title=f"Eksport - {vit} (baza: {metrika})", width=420, height=420)
                c2.altair_chart(pie_export, use_container_width=True)
            else:
                c2.info(f"Nuk ka të dhëna Eksport për vitin {vit}.")



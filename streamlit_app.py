import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import StringIO

# ──────────────────────────────────────────────────────────────────────────────
# Konfigurimi i faqes (duhet para çdo thirrje tjetër të Streamlit)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Të dhëna doganore - Shqip", layout="wide")
st.title("📊 Platforma e të Dhënave mbi Importet dhe Eksportet Doganore")

# ──────────────────────────────────────────────────────────────────────────────
# Funksione utilitare
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_csv_robust(buf_or_path):
    """Lexon CSV me disa encoding dhe pastron numrat me formate të ndryshme."""
    if buf_or_path is None:
        return pd.DataFrame()
    encodings = ["utf-8", "latin1", "ISO-8859-1", "cp1252"]
    last_err = None
    for enc in encodings:
        try:
            if isinstance(buf_or_path, (str, bytes)):
                df = pd.read_csv(buf_or_path, encoding=enc)
            else:
                # file-like (nga uploader)
                df = pd.read_csv(buf_or_path, encoding=enc)
            return df
        except Exception as e:
            last_err = e
            continue
    st.error(f"❌ Nuk u arrit të lexohet CSV-ja me asnjë encoding të njohur. {last_err}")
    return pd.DataFrame()

def coerce_number(s):
    """Kthen string me simbole/ndarës në numra (p.sh. '1.234,56 €' → 1234.56)."""
    if pd.isna(s):
        return np.nan
    if isinstance(s, (int, float, np.number)):
        return s
    s = str(s)
    # Hiq simbolet e valutës/tekste
    s = s.replace("€", "").replace("Lek", "").replace("lekë", "").replace("LEK", "")
    s = s.replace("\xa0", " ").strip()
    # Nëse ka si formë '1.234,56' → zëvendëso pikën si mijëshe dhe presjen si decimale
    if s.count(",") == 1 and s.count(".") >= 1 and s.rfind(",") > s.rfind("."):
        s = s.replace(".", "").replace(",", ".")
    else:
        # Hiq mijëshet e zakonshme
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return pd.to_numeric(s, errors="coerce")

muajt_shqip_map = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
    7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
}

# ──────────────────────────────────────────────────────────────────────────────
# Burimi i të dhënave: file path fiks ose uploader
# ──────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 2])
with col_left:
    st.markdown("**Ngarko CSV (opsionale)** nëse do të zëvendësosh skedarin default.")
    up = st.file_uploader("Zgjidh CSV", type=["csv"], key="uploader", help="Në mungesë, përdoret skedari lokal.")
with col_right:
    default_path = "te_dhena_doganore_simuluara.csv"
    st.caption(f"📁 Skedari default: `{default_path}`")

df = load_csv_robust(up if up is not None else default_path)

if df.empty:
    st.info("Ngarko një CSV ose sigurohu që skedari default ekziston në rrugën e aplikacionit.")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Normalizim kolonash dhe tipash
# ──────────────────────────────────────────────────────────────────────────────
df = df.rename(columns=lambda x: str(x).strip())

# Alias për kolonat e mundshme
aliases = {
    "Vlera": ["Vlera (lekë)", "Vlera (€)", "Value", "Vlere", "Amount", "Value (€)"],
    "Sasia (kg)": ["Sasia", "Sasi", "Quantity", "Sasia (kg)"],
    "Muaji": ["Muaji", "Month", "Muaj"],
    "Viti": ["Viti", "Year"],
    "Lloji": ["Lloji", "Type", "Tipi", "Import/Eksport"],
    "Kategoria": ["Kategoria", "Kategori", "Category"],
}
# Gjej kolonën e parë ekzistuese për çdo emër kanonik
for canon, alts in aliases.items():
    for a in alts:
        if a in df.columns:
            if canon != a:
                df[canon] = df[a]
            break

# Detekto kolonën e kodit HS
possible_hs = [
    "Kodi doganor", "Kodi_doganor", "KodiDoganor", "Kodi HS", "HS Code", "HS_Code", "HS",
    "Kodi", "Kodi i mallrave", "HS6", "HS8", "Nomenklatura"
]
hs_col_found = None
for c in df.columns:
    if str(c).strip() in possible_hs:
        hs_col_found = c
        break

# Pastrim numerik për kolonat kryesore
if "Vlera" in df.columns:
    df["Vlera"] = df["Vlera"].map(coerce_number)
if "Sasia (kg)" in df.columns:
    df["Sasia (kg)"] = df["Sasia (kg)"].map(coerce_number)

# Muajt në shqip
if "Muaji" in df.columns:
    # nëse është numër → map; nëse tekst p.sh. '01' → në numër
    mtmp = pd.to_numeric(df["Muaji"], errors="coerce")
    df["Muaji"] = mtmp.map(muajt_shqip_map).fillna(df["Muaji"].astype(str).str.strip())
    df["Muaji"] = df["Muaji"].replace({"": "Pa të dhëna"})


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar – Filtra
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtrim")

# Metrikë për grafikët: Vlera ose Sasia
metric_opts = []
if "Vlera" in df.columns: metric_opts.append("Vlera")
if "Sasia (kg)" in df.columns: metric_opts.append("Sasia (kg)")
metric = st.sidebar.selectbox("Metrika për grafikë", metric_opts or ["(asnjë)"])

vit = None
if "Viti" in df.columns and df["Viti"].notna().any():
    vite_unq = sorted(pd.to_numeric(df["Viti"], errors="coerce").dropna().unique())
    vit = st.sidebar.selectbox("Zgjidh vitin", vite_unq) if len(vite_unq) else None

if "Lloji" in df.columns:
    lloji = st.sidebar.selectbox("Zgjidh llojin", sorted(df["Lloji"].dropna().unique()))
else:
    lloji = st.sidebar.selectbox("Zgjidh llojin", ["Import", "Eksport"])

if "Kategoria" in df.columns:
    kategorite = df["Kategoria"].dropna().astype(str).unique().tolist()
    default_kategori = kategorite[:3]
    kategoria = st.sidebar.multiselect("Zgjidh kategoritë", options=kategorite, default=default_kategori)
else:
    kategoria = []

# HS column selector (nëse u gjet, ofro filtër + listë)
hs_col = None
if hs_col_found is not None:
    hs_col = st.sidebar.selectbox("Kolona e kodit doganor (HS)", [hs_col_found])
    # filtër opsional sipas HS
    hs_values = df[hs_col].dropna().astype(str).unique().tolist()
    hs_pick = st.sidebar.multiselect("Filtro sipas HS (opsionale)", options=hs_values, default=[])
else:
    hs_pick = []

# ──────────────────────────────────────────────────────────────────────────────
# Zbatimi i filtrave
# ──────────────────────────────────────────────────────────────────────────────
df_f = df.copy()
if vit is not None and "Viti" in df_f.columns:
    df_f = df_f[pd.to_numeric(df_f["Viti"], errors="coerce") == vit]
if "Lloji" in df_f.columns:
    df_f = df_f[df_f["Lloji"] == lloji]
if kategoria and "Kategoria" in df_f.columns:
    df_f = df_f[df_f["Kategoria"].astype(str).isin(kategoria)]
if hs_pick and hs_col:
    df_f = df_f[df_f[hs_col].astype(str).isin(hs_pick)]

if df_f.empty:
    st.warning("⚠️ Nuk ka të dhëna për këtë filtër.")
    st.stop()

# Siguro vlera numerike pa NaN
for c in ["Vlera", "Sasia (kg)"]:
    if c in df_f.columns:
        df_f[c] = pd.to_numeric(df_f[c], errors="coerce").fillna(0)

# ──────────────────────────────────────────────────────────────────────────────
# KPI-të
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("🔎 Përmbledhje")
k1, k2, k3, k4 = st.columns(4)
with k1:
    if "Vlera" in df_f.columns:
        st.metric("Totali i vlerës", f"{df_f['Vlera'].sum():,.0f}")
    else:
        st.metric("Totali i vlerës", "—")
with k2:
    if "Sasia (kg)" in df_f.columns:
        st.metric("Totali i sasisë (kg)", f"{df_f['Sasia (kg)'].sum():,.0f}")
    else:
        st.metric("Totali i sasisë (kg)", "—")
with k3:
    st.metric("Nr. transaksioneve", f"{len(df_f):,}")
with k4:
    if "Vlera" in df_f.columns:
        avg = df_f["Vlera"].mean()
        st.metric("Mesatarja për rresht", f"{avg:,.0f}")
    else:
        st.metric("Mesatarja për rresht", "—")

# ──────────────────────────────────────────────────────────────────────────────
# Grafik mujor (line) – nëse ka muaj
# ──────────────────────────────────────────────────────────────────────────────
if "Muaji" in df_f.columns and metric in df_f.columns:
    st.subheader(f"📈 Volumi mujor i {lloji.lower()}-eve për vitin {vit if vit else '(të zgjedhurin)'}")
    muaj_order = [m for m in muajt_shqip_map.values() if m in df_f["Muaji"].unique()]

    color_enc = "Kategoria:N" if "Kategoria" in df_f.columns else alt.value("steelblue")
    tooltips = []
    if "Kategoria" in df_f.columns: tooltips.append("Kategoria")
    tooltips += ["Muaji", alt.Tooltip(f"{metric}:Q", format=",.0f")]
    if metric != "Vlera" and "Vlera" in df_f.columns:
        tooltips.append(alt.Tooltip("Vlera:Q", title="Vlera", format=",.0f"))

    chart_line = (
        alt.Chart(df_f)
        .mark_line(point=True)
        .encode(
            x=alt.X("Muaji:N", title="Muaji", sort=muaj_order),
            y=alt.Y(f"{metric}:Q", title=metric, scale=alt.Scale(zero=False)),
            color=color_enc,
            tooltip=tooltips,
        )
        .properties(height=420)
    )
    st.altair_chart(chart_line, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# Volumi vjetor sipas kategorive (për të gjitha vitet e pranishme)
# ──────────────────────────────────────────────────────────────────────────────
if all(c in df.columns for c in ["Lloji", "Kategoria", "Viti"]) and metric in df.columns:
    st.subheader("📊 Volumi vjetor sipas kategorive")
    for lloji_temp in sorted(df["Lloji"].dropna().unique()):
        st.markdown(f"#### {lloji_temp}")
        df_v = df[df["Lloji"] == lloji_temp].copy()
        if kategoria:
            df_v = df_v[df_v["Kategoria"].astype(str).isin(kategoria)]
        df_v[metric] = pd.to_numeric(df_v[metric], errors="coerce").fillna(0)

        df_v_sum = df_v.groupby(["Kategoria", "Viti"], as_index=False)[metric].sum()
        kategoria_order = (
            df_v_sum.groupby("Kategoria")[metric].sum().sort_values(ascending=False).index.tolist()
        )

        chart_bar = (
            alt.Chart(df_v_sum)
            .mark_bar()
            .encode(
                x=alt.X("Kategoria:N", title="Kategoria", sort=kategoria_order),
                y=alt.Y(f"{metric}:Q", title=f"Totali {metric}", scale=alt.Scale(zero=False)),
                color=alt.Color("Viti:N", title="Viti"),
                xOffset=alt.XOffset("Viti:N"),
                tooltip=["Viti", "Kategoria", alt.Tooltip(f"{metric}:Q", format=",.0f")],
            )
            .properties(height=420)
        )
        st.altair_chart(chart_bar, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# Import vs Eksport për vitin e zgjedhur
# ──────────────────────────────────────────────────────────────────────────────
if vit is not None and all(c in df.columns for c in ["Viti", "Lloji", "Kategoria"]) and metric in df.columns:
    st.subheader(f"📦 Import vs Eksport sipas kategorive për vitin {vit}")
    df_year = df[pd.to_numeric(df["Viti"], errors="coerce") == vit].copy()
    if kategoria:
        df_year = df_year[df_year["Kategoria"].astype(str).isin(kategoria)]
    df_year[metric] = pd.to_numeric(df_year[metric], errors="coerce").fillna(0)

    df_year_sum = df_year.groupby(["Kategoria", "Lloji"], as_index=False)[metric].sum()
    kategoria_order_year = (
        df_year_sum.groupby("Kategoria")[metric].sum().sort_values(ascending=False).index.tolist()
    )

    chart_ie = (
        alt.Chart(df_year_sum)
        .mark_bar()
        .encode(
            x=alt.X("Kategoria:N", title="Kategoria", sort=kategoria_order_year),
            y=alt.Y(f"{metric}:Q", title=f"Totali {metric}", scale=alt.Scale(zero=False)),
            color=alt.Color("Lloji:N", title="Lloji"),
            xOffset=alt.XOffset("Lloji:N"),
            tooltip=["Kategoria", "Lloji", alt.Tooltip(f"{metric}:Q", format=",.0f")],
        )
        .properties(height=420)
    )
    st.altair_chart(chart_ie, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# Pie charts: Pesha % sipas Kategorive (Import vs Eksport, bazuar në VLERË)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("🥧 Pesha % sipas Kategorive (Import vs Eksport, bazë vjetore)")
if all(col in df.columns for col in ["Viti", "Lloji", "Kategoria", "Vlera"]) and vit is not None:
    df_year_cat = df[pd.to_numeric(df["Viti"], errors="coerce") == vit].copy()
    df_year_cat["Vlera"] = pd.to_numeric(df_year_cat["Vlera"], errors="coerce").fillna(0)
    df_year_cat["Kategoria"] = df_year_cat["Kategoria"].astype(str).str.strip().replace({"": "Pa kategori"})

    if kategoria:
        df_year_cat = df_year_cat[df_year_cat["Kategoria"].isin(kategoria)]

    agg_cat = df_year_cat.groupby(["Kategoria", "Lloji"], as_index=False)["Vlera"].sum()

    def add_percent(df_lloji):
        total = df_lloji["Vlera"].sum()
        df_lloji = df_lloji.copy()
        df_lloji["Perc"] = (df_lloji["Vlera"] / total * 100) if total > 0 else 0
        return df_lloji

    imp = add_percent(agg_cat[agg_cat["Lloji"] == "Import"])
    eksp = add_percent(agg_cat[agg_cat["Lloji"] == "Eksport"])

    shared_domain = list(pd.concat([imp["Kategoria"], eksp["Kategoria"]]).drop_duplicates())
    color_scale = alt.Scale(domain=shared_domain)

    c1, c2 = st.columns(2)
    if not imp.empty and imp["Vlera"].sum() > 0:
        pie_imp = (
            alt.Chart(imp)
            .mark_arc()
            .encode(
                theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                color=alt.Color("Kategoria:N", title="Kategoria", scale=color_scale),
                tooltip=[
                    alt.Tooltip("Kategoria:N", title="Kategoria"),
                    alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                    alt.Tooltip("Vlera:Q", title="Vlera", format=",.0f"),
                ],
            )
            .properties(title=f"Import – {vit} (bazuar në VLERË)", width=420, height=420)
        )
        c1.altair_chart(pie_imp, use_container_width=True)
    else:
        c1.info(f"Nuk ka të dhëna për Import në {vit}.")

    if not eksp.empty and eksp["Vlera"].sum() > 0:
        pie_eks = (
            alt.Chart(eksp)
            .mark_arc()
            .encode(
                theta=alt.Theta("Perc:Q", title="Pesha (%)"),
                color=alt.Color("Kategoria:N", title="Kategoria", scale=color_scale),
                tooltip=[
                    alt.Tooltip("Kategoria:N", title="Kategoria"),
                    alt.Tooltip("Perc:Q", title="Pesha (%)", format=".2f"),
                    alt.Tooltip("Vlera:Q", title="Vlera", format=",.0f"),
                ],
            )
            .properties(title=f"Eksport – {vit} (bazuar në VLERË)", width=420, height=420)
        )
        c2.altair_chart(pie_eks, use_container_width=True)
    else:
        c2.info(f"Nuk ka të dhëna për Eksport në {vit}.")
else:
    st.info("ℹ️ Për byrekët nevojiten kolonat: 'Viti', 'Lloji', 'Kategoria', 'Vlera' dhe një vit i përzgjedhur.")

# ──────────────────────────────────────────────────────────────────────────────
# 🔎 Top HS sipas metrikës (nëse ekziston kolona HS)
# ──────────────────────────────────────────────────────────────────────────────
if hs_col and metric in df_f.columns:
    st.subheader(f"🔢 Top 15 HS sipas {metric}")
    df_hs = df_f.dropna(subset=[hs_col]).copy()
    grp = df_hs.groupby(hs_col, as_index=False)[metric].sum().sort_values(metric, ascending=False).head(15)
    hs_chart = (
        alt.Chart(grp)
        .mark_bar()
        .encode(
            x=alt.X(f"{metric}:Q", title=f"Totali {metric}", scale=alt.Scale(zero=True)),
            y=alt.Y(f"{hs_col}:N", sort="-x", title="Kodi HS"),
            tooltip=[hs_col, alt.Tooltip(f"{metric}:Q", format=",.0f")],
        )
        .properties(height=520)
    )
    st.altair_chart(hs_chart, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# Tabela & Shkarkim
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("📋 Tabela e të dhënave")
st.dataframe(df_f, use_container_width=True)

st.download_button(
    "📥 Shkarko të dhënat në CSV",
    data=df_f.to_csv(index=False),
    file_name="te_dhena_filtruara.csv",
    mime="text/csv"
)

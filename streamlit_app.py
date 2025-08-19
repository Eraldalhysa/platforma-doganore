import pandas as pd
from caas_jupyter_tools import display_dataframe_to_user

path = "/mnt/data/te_dhena_doganore_simuluara.csv"

# Lexo CSV me autodetektim encoding
encodings = ["utf-8", "latin1", "ISO-8859-1", "cp1252"]
df = None
for enc in encodings:
    try:
        df = pd.read_csv(path, encoding=enc)
        break
    except Exception as e:
        last_err = str(e)

if df is None:
    print("Nuk u lexua dot skedari:", last_err)
else:
    # Shfaq kolonat dhe 10 rreshtat e parë
    print("Kolonat:", list(df.columns))
    display_dataframe_to_user("Mostra e të dhënave (10 rreshta)", df.head(10))

    # Përpiqu të standardizosh emrat kryesorë pa ndryshuar datasetin origjinal
    cols_lower = {c.lower().strip(): c for c in df.columns}
    # Kandidatë për kolona
    year_col = next((cols_lower[k] for k in cols_lower if k in ["viti","year"]), None)
    type_col = next((cols_lower[k] for k in cols_lower if k in ["lloji","type"]), None)
    value_col = next((cols_lower[k] for k in cols_lower if k in ["vlera","value","vlera (€)","vlera (lekë)"]), None)
    hs_col = next((cols_lower[k] for k in cols_lower if k in ["kodi_doganor","kodi doganor","hs_code","hs code","kodi","hs"]), None)

    print("Detektim kolonash -> Viti:", year_col, "| Lloji:", type_col, "| Vlera:", value_col, "| Kodi HS:", hs_col)

    # Nëse i kemi këto kolona, kalkulo shpërndarjen për vitin më të fundit si provë
    if all([year_col, type_col, value_col, hs_col]):
        # Pastro vlerat numerike
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
        # Gjej vitin më të fundit
        latest_year = int(pd.to_numeric(df[year_col], errors="coerce").dropna().max())
        out = {}
        for trade_type in ["Import","Eksport","Importe","Eksporte","Import/Export"]:
            if trade_type in df[type_col].astype(str).unique():
                sub = df[(df[year_col]==latest_year) & (df[type_col]==trade_type)]
                if not sub.empty:
                    grouped = sub.groupby(hs_col)[value_col].sum().sort_values(ascending=False)
                    out[trade_type] = grouped

        # Përgatit raport tabelor
        tables = {}
        for k,v in out.items():
            perc = (v / v.sum() * 100).round(2).rename("Pesha (%)")
            tab = pd.concat([v.rename("Vlera"), perc], axis=1).reset_index().rename(columns={hs_col:"Kodi HS"})
            tables[k] = tab

        # Shfaq tabelat si preview
        for k,tab in tables.items():
            display_dataframe_to_user(f"Shpërndarja {k} sipas Kodi HS për vitin {latest_year}", tab)

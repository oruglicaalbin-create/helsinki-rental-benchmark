"""Turn the raw json-stat2 responses into tidy long CSVs in data/processed/.

Uses the most recent raw file for each table. Output columns use English names.
Run from the project root:  .venv\\Scripts\\python.exe src\\02_clean.py
"""
import itertools
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"


def latest(name):
    files = sorted(RAW.glob(f"{name}_data_*.json"))
    if not files:
        raise FileNotFoundError(f"No raw file for {name}. Run 01_fetch_statfin.py first.")
    return files[-1]


def jsonstat_to_df(path):
    """Expand a json-stat2 dataset into one row per cell, with code and label per dimension."""
    js = json.loads(path.read_text(encoding="utf-8"))
    dims = js["id"]
    cats = []
    for d in dims:
        cat = js["dimension"][d]["category"]
        codes = sorted(cat["index"], key=cat["index"].get)
        cats.append([(c, cat["label"][c]) for c in codes])
    rows = []
    for combo, val in zip(itertools.product(*cats), js["value"]):
        row = {}
        for d, (code, label) in zip(dims, combo):
            row[d] = code
            row[d + "_label"] = label
        row["value"] = val
        rows.append(row)
    return pd.DataFrame(rows)


SIZE_EN = {"Yksiöt": "Studio", "Kaksiot": "One-bedroom", "Kolmiot+": "Two-bedroom+",
           "Yhteensä": "All"}


def clean_postcodes():
    df = jsonstat_to_df(latest("13eb"))
    df = df.rename(columns={"Vuosineljännes": "quarter", "Postinumero": "postcode",
                            "Huoneluku_label": "size_fi"})
    lab = df["Postinumero_label"].str.extract(r"^\d{5}\s+(.*?)\s*\((.*?)\s*\)\s*$")
    df["area_name"] = lab[0].str.strip()
    df["municipality"] = lab[1].str.strip()
    df["size"] = df["size_fi"].map(SIZE_EN)
    df["measure"] = df["Tiedot"].map({"lkm_ptno": "n_obs", "keskivuokra": "rent_eur_m2"})
    wide = (df.pivot_table(index=["postcode", "area_name", "municipality", "quarter", "size"],
                           columns="measure", values="value", aggfunc="first")
              .reset_index())
    wide.columns.name = None
    return wide[["postcode", "area_name", "municipality", "quarter", "size",
                 "rent_eur_m2", "n_obs"]]


def clean_11x4():
    df = jsonstat_to_df(latest("11x4"))
    measures = {"ketj_Tor": "index_2015", "neljmuut": "index_qoq_pct", "vmuut": "index_yoy_pct",
                "lkm": "n_index", "keskivuokra": "rent_eur_m2", "lkm_khinta": "n_rent",
                "keskivuokra_uudet": "rent_new_eur_m2", "lkm_khinta_uudet": "n_rent_new"}
    fin = {"2": "All", "1": "Free-market", "0": "ARA (state-subsidised)"}
    df = pd.DataFrame({
        "quarter": df["Vuosineljännes"],
        "area_code": df["Alue"],
        "area": df["Alue_label"],
        "size": df["Huoneluku_label"].map(SIZE_EN),
        "financing": df["Rahoitusmuoto"].map(fin),
        "measure": df["Tiedot"].map(measures),
        "value": df["value"],
    })
    return df


def clean_15fa():
    df = jsonstat_to_df(latest("15fa"))
    measures = {"asvu2025": "index_2025", "asvu2025_nm": "index_qoq_pct",
                "asvu2025_vm": "index_yoy_pct", "asvu_keskineliovuokra": "rent_eur_m2",
                "asvu_keskineliovuokra_lkm": "n_rent",
                "asvu_keskineliovuokra_u": "rent_new_eur_m2",
                "asvu_keskineliovuokra_u_lkm": "n_rent_new"}
    fin = {"SSS": "All", "1": "Free-market", "2": "ARA (state-subsidised)"}
    # Area codes in 15fa use "_" (091_1), 11x4 uses "-" (091-1). Harmonise to "-".
    df = pd.DataFrame({
        "quarter": df["timeperiod_q"],
        "area_code": df["alue_44_20260101"].str.replace("_", "-").replace({"SSS": "ksu"}),
        "area": df["alue_44_20260101_label"].str.replace(r"^MK\d\d ", "", regex=True),
        "size": df["huoneluku_5_20260101_label"].map(SIZE_EN),
        "financing": df["rahoitus_2_20260101"].map(fin),
        "measure": df["contentscode"].map(measures),
        "value": df["value"],
    })
    return df


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pc = clean_postcodes()
    pc.to_csv(OUT / "postcode_rents_2015_2025.csv", index=False, encoding="utf-8-sig")
    print(f"postcode_rents: {len(pc)} rows, {pc.postcode.nunique()} postcodes")

    a = clean_11x4()
    a.to_csv(OUT / "area_rents_11x4_2015_2025.csv", index=False, encoding="utf-8-sig")
    b = clean_15fa()
    b.to_csv(OUT / "area_rents_15fa_2025_latest.csv", index=False, encoding="utf-8-sig")
    print(f"11x4: {len(a)} rows, quarters {a.quarter.min()}-{a.quarter.max()}")
    print(f"15fa: {len(b)} rows, quarters {b.quarter.min()}-{b.quarter.max()}")


if __name__ == "__main__":
    main()

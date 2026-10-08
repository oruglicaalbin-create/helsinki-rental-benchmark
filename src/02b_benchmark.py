"""Build the rent benchmark tables from the clean CSVs.

Outputs (data/processed/):
  benchmark_postcodes.csv   one row per selected postcode x flat size: latest EUR/m2, y/y and 5-year change
  benchmark_timeseries.csv  long quarterly series for the selected postcodes (feeds the Excel pivot)
  benchmark_areas.csv       official rent index and EUR/m2 for Helsinki, zones, Espoo, Vantaa
  current_rents_15fa.csv    latest EUR/m2 incl. new tenancies by area and size (anchor for the lease-up model)

Run from the project root:  .venv\\Scripts\\python.exe src\\02b_benchmark.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

MIN_OBS = 30          # minimum observations per cell, in every quarter a figure uses
# The archived table runs to 2025Q4, but 2025Q3-Q4 show a level shift that coincides with the
# switch to the new 2025=100 method (see notes/assumptions_and_sources.md). 2025Q2 is the last
# quarter on the old, consistent basis, so it is the benchmark quarter. 2025Q4 is kept as a
# separate column for transparency.
LATEST = "2025Q2"
PREV_Q = "2025Q1"
YEAR_AGO = "2024Q2"
FIVE_Y_AGO = "2020Q2"
REPORTED_LAST = "2025Q4"

# Chosen for data coverage (>= 2 flat sizes passing MIN_OBS where possible) and a spread
# from the inner city to the suburbs and newer development areas. See notes/assumptions_and_sources.md.
SELECTED = {
    # Helsinki, inner city
    "00180": "Helsinki", "00250": "Helsinki", "00530": "Helsinki", "00500": "Helsinki",
    "00200": "Helsinki", "00510": "Helsinki",
    # Helsinki, middle ring
    "00520": "Helsinki", "00320": "Helsinki", "00640": "Helsinki", "00840": "Helsinki",
    # Helsinki, outer suburbs
    "00420": "Helsinki", "00920": "Helsinki", "00940": "Helsinki", "00970": "Helsinki",
    # Espoo and Vantaa for comparison
    "02650": "Espoo", "02600": "Espoo", "01300": "Vantaa", "01700": "Vantaa",
}
SIZES = ["Studio", "One-bedroom", "Two-bedroom+"]


def pct(a, b):
    return (a / b - 1) * 100


def postcode_benchmark(pc):
    sel = pc[pc.postcode.isin(SELECTED)].copy()
    names = sel.groupby("postcode")[["area_name", "municipality"]].first()
    rent = sel.pivot_table(index=["postcode", "size"], columns="quarter", values="rent_eur_m2")
    nobs = sel.pivot_table(index=["postcode", "size"], columns="quarter", values="n_obs")
    idx = pd.MultiIndex.from_product([list(SELECTED), SIZES], names=["postcode", "size"])
    rent, nobs = rent.reindex(idx), nobs.reindex(idx)

    def ok(*qs):
        return pd.concat([nobs[q] >= MIN_OBS for q in qs], axis=1).all(axis=1)

    out = pd.DataFrame(index=idx)
    out["rent_latest"] = rent[LATEST].where(ok(LATEST))
    out["n_latest"] = nobs[LATEST]
    out["rent_prev_q"] = rent[PREV_Q].where(ok(PREV_Q))
    out["rent_year_ago"] = rent[YEAR_AGO].where(ok(YEAR_AGO))
    out["rent_5y_ago"] = rent[FIVE_Y_AGO].where(ok(FIVE_Y_AGO))
    out["rent_2025Q4_reported"] = rent[REPORTED_LAST].where(ok(REPORTED_LAST))
    out["chg_yoy_pct"] = pct(rent[LATEST], rent[YEAR_AGO]).where(ok(LATEST, YEAR_AGO))
    out["chg_5y_pct"] = pct(rent[LATEST], rent[FIVE_Y_AGO]).where(ok(LATEST, FIVE_Y_AGO))
    out["chg_5y_cagr_pct"] = ((rent[LATEST] / rent[FIVE_Y_AGO]) ** (1 / 5) - 1).mul(100) \
        .where(ok(LATEST, FIVE_Y_AGO))

    def flag(r):
        if pd.isna(r.n_latest):
            return "masked by Statistics Finland"
        if r.n_latest < MIN_OBS:
            return f"below {MIN_OBS} obs"
        # A cell can have a latest rent but a missing change, if the comparison quarter is masked
        # or below the minimum. Flag both changes, so a blank never appears without a reason.
        gaps = []
        if pd.isna(r.chg_yoy_pct):
            gaps.append(f"1y change: below {MIN_OBS} obs or masked in {YEAR_AGO}")
        if pd.isna(r.chg_5y_pct):
            gaps.append(f"5y change: below {MIN_OBS} obs or masked in {FIVE_Y_AGO}")
        return "; ".join(gaps)
    out["flag"] = out.apply(flag, axis=1)
    out = out.reset_index().merge(names, left_on="postcode", right_index=True)
    out["area_label"] = out.postcode + " " + out.area_name
    cols = ["postcode", "area_name", "area_label", "municipality", "size", "rent_latest", "n_latest",
            "rent_prev_q", "rent_year_ago", "rent_5y_ago", "chg_yoy_pct", "chg_5y_pct",
            "chg_5y_cagr_pct", "rent_2025Q4_reported", "flag"]
    return out[cols].round(2)


def area_benchmark(a):
    """Official quality-adjusted index (2015=100) plus EUR/m2, free-market, by area and size."""
    f = a[(a.financing == "Free-market") & (a.area_code.isin(
        ["pks", "091", "091-1", "091-2", "091-3", "091-4", "049", "092"]))]
    w = f.pivot_table(index=["area_code", "area", "size", "quarter"], columns="measure",
                      values="value").reset_index()
    w.columns.name = None
    return w


def main():
    pc = pd.read_csv(PROC / "postcode_rents_2015_2025.csv", dtype={"postcode": str})
    bm = postcode_benchmark(pc)
    bm.to_csv(PROC / "benchmark_postcodes.csv", index=False, encoding="utf-8-sig")

    ts = pc[pc.postcode.isin(SELECTED)].copy()
    ts["area_label"] = ts.postcode + " " + ts.area_name
    ts["year"] = ts.quarter.str[:4].astype(int)
    ts["meets_min_obs"] = ts.n_obs >= MIN_OBS
    ts.to_csv(PROC / "benchmark_timeseries.csv", index=False, encoding="utf-8-sig")

    a = pd.read_csv(PROC / "area_rents_11x4_2015_2025.csv", dtype={"area_code": str})
    area_benchmark(a).to_csv(PROC / "benchmark_areas.csv", index=False, encoding="utf-8-sig")

    b = pd.read_csv(PROC / "area_rents_15fa_2025_latest.csv", dtype={"area_code": str})
    cur = b[b.financing == "Free-market"].pivot_table(
        index=["area_code", "area", "size", "quarter"], columns="measure", values="value").reset_index()
    cur.columns.name = None
    cur.to_csv(PROC / "current_rents_15fa.csv", index=False, encoding="utf-8-sig")

    # Diagnostic: median postcode q/q change, shows the 2025Q4 level shift
    r = pc.pivot_table(index=["postcode", "size"], columns="quarter", values="rent_eur_m2")
    qs = list(r.columns)
    med = pd.Series({q: pct(r[q], r[p]).median() for p, q in zip(qs, qs[1:])}).round(2)
    med.rename("median_qoq_pct").to_csv(PROC / "diag_postcode_median_qoq.csv", encoding="utf-8-sig")

    print(bm.to_string())


if __name__ == "__main__":
    main()

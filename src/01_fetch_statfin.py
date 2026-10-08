"""Fetch rents of dwellings data from the Statistics Finland PxWeb API.

Source: Statistics Finland, rents of dwellings (CC BY 4.0).
Every raw response and the table metadata are saved untouched to data/raw/
with the fetch date in the file name, so results can be reproduced.

Run from the project root:  .venv\\Scripts\\python.exe src\\01_fetch_statfin.py
"""
import datetime as dt
import json
import time
from pathlib import Path

import requests

BASE = "https://pxdata.stat.fi/PxWeb/api/v1/fi"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
TODAY = dt.date.today().isoformat()

# Capital region municipalities. Postal codes are labelled e.g. "00530 Kallio (Helsinki )".
PKS_MUNICIPALITIES = ["(Helsinki )", "(Espoo )", "(Kauniainen )", "(Vantaa )"]

# Capital region area codes in the area-level tables (codes differ between tables).
AREAS_11X4 = ["pks", "091", "091-1", "091-2", "091-3", "091-4",
              "049", "049-1", "049-2", "049-3", "092", "092-1", "092-2", "ksu"]
AREAS_15FA = ["pks", "091", "091_1", "091_2", "091_3", "091_4",
              "049", "049_1", "049_2", "049_3", "092", "092_1", "092_2", "092_3", "SSS"]

TABLES = {
    # Free-market average rent EUR/m2 by postal code, 2015Q1-2025Q4 (archived table)
    "13eb": "StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px",
    # Rent index 2015=100 and average EUR/m2 by area, 2015Q1-2025Q4 (archived table)
    "11x4": "StatFin_Passiivi/asvu/statfinpas_asvu_pxt_11x4_2025q4.px",
    # Current table: rent index 2025=100 and average EUR/m2 by area, 2025Q1-latest
    "15fa": "StatFin/asvu/15fa.px",
}


def get_json(url, payload=None, tries=4):
    for i in range(tries):
        try:
            r = (requests.post(url, json=payload, timeout=60) if payload
                 else requests.get(url, timeout=60))
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if i == tries - 1:
                raise
            print(f"  retry {i + 1} after error: {e}")
            time.sleep(3 * (i + 1))


def all_values(meta, code):
    return next(v for v in meta["variables"] if v["code"] == code)["values"]


def save(obj, name):
    path = RAW / f"{name}_{TODAY}.json"
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  saved {path.name}")


def build_query(meta, selections):
    """Select the given values for listed variables and all values for the rest."""
    query = []
    for v in meta["variables"]:
        values = selections.get(v["code"], v["values"])
        query.append({"code": v["code"], "selection": {"filter": "item", "values": values}})
    return {"query": query, "response": {"format": "json-stat2"}}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for key, path in TABLES.items():
        url = f"{BASE}/{path}"
        print(f"Table {key}")
        meta = get_json(url)
        save(meta, f"{key}_metadata")

        if key == "13eb":
            post = next(v for v in meta["variables"] if v["code"] == "Postinumero")
            codes = [c for c, t in zip(post["values"], post["valueTexts"])
                     if any(m in t for m in PKS_MUNICIPALITIES)]
            print(f"  {len(codes)} capital-region postal codes")
            sel = {"Postinumero": codes}
        elif key == "11x4":
            sel = {"Alue": AREAS_11X4}
        else:
            sel = {"alue_44_20260101": AREAS_15FA}

        data = get_json(url, build_query(meta, sel))
        save(data, f"{key}_data")
        time.sleep(1)  # be polite to the API


if __name__ == "__main__":
    main()

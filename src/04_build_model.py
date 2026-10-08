"""Build output/Helsinki_Rental_Benchmark.xlsx with real Excel formulas.

Part 1 sheets (this version): About, Benchmark summary, Benchmark data, Area trend,
Current rents, Sources. The lease-up model sheets are added in Part 3.

Run from the project root after 02_clean.py and 02b_benchmark.py:
    .venv\\Scripts\\python.exe src\\04_build_model.py
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd

import leaseup_sheets as lu
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
PROC = ROOT / "data" / "processed"
OUT = ROOT / "output" / "Helsinki_Rental_Benchmark.xlsx"

# Reuse the area list and quarter choices from the benchmark script, so there is one source of truth.
_spec = importlib.util.spec_from_file_location("bm", ROOT / "src" / "02b_benchmark.py")
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)

SIZES = ["Studio", "One-bedroom", "Two-bedroom+"]
SIZE_COLOURS = {"Studio": "2A78D6", "One-bedroom": "EB6834", "Two-bedroom+": "1BAF7A"}

# Styles
H1 = Font(bold=True, size=14)
H2 = Font(bold=True, size=11)
BOLD = Font(bold=True)
MUTED = Font(italic=True, color="595959", size=9)
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")   # yellow = input you can change
HEAD_FILL = PatternFill("solid", fgColor="D9E1F2")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

SOURCE_TXT = "Source: Statistics Finland, rents of dwellings (CC BY 4.0)"


def header_row(ws, row, values, start_col=1):
    for i, v in enumerate(values):
        c = ws.cell(row=row, column=start_col + i, value=v)
        c.font = BOLD
        c.fill = HEAD_FILL
        c.border = BOX
        c.alignment = CENTER


def no_overlap(ch):
    """Stop the title and legend being drawn on top of the plot area."""
    from openpyxl.chart.layout import Layout, ManualLayout
    ch.title.overlay = False
    ch.legend.overlay = False
    ch.layout = Layout(manualLayout=ManualLayout(yMode="edge", xMode="edge", x=0.0, y=0.12, h=0.86, w=1.0))


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


# ---------------------------------------------------------------- Benchmark data
def sheet_benchmark_data(wb):
    ws = wb.create_sheet("Benchmark data")
    pc = pd.read_csv(PROC / "postcode_rents_2015_2025.csv", dtype={"postcode": str})
    pc["area_label"] = pc.postcode + " " + pc.area_name
    pc["year"] = pc.quarter.str[:4].astype(int)
    pc["in_benchmark"] = pc.postcode.isin(bm.SELECTED).map({True: "Yes", False: "No"})
    pc = pc.sort_values(["postcode", "size", "quarter"])
    cols = ["postcode", "area_label", "municipality", "in_benchmark", "quarter", "year",
            "size", "rent_eur_m2", "n_obs"]
    ws.append(cols)
    for r in pc[cols].itertuples(index=False):
        ws.append(list(r))
    n = len(pc) + 1
    tab = Table(displayName="RentData", ref=f"A1:I{n}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(tab)
    for row in ws.iter_rows(min_row=2, min_col=8, max_col=8):
        row[0].number_format = "0.00"
    ws.freeze_panes = "A2"
    widths(ws, {"A": 10, "B": 36, "C": 13, "D": 13, "E": 10, "F": 7, "G": 14, "H": 12, "I": 9})
    ws["K1"] = "Free-market average rent EUR/m2 by postal code, all capital-region postcodes."
    ws["K2"] = "Cells Statistics Finland masks (under 20 obs or many rental-company flats) have no row."
    ws["K3"] = SOURCE_TXT + ", table 13eb."
    for c in ("K1", "K2", "K3"):
        ws[c].font = MUTED
    return n


# ---------------------------------------------------------------- Benchmark summary
def sheet_benchmark_summary(wb, n_data):
    ws = wb.create_sheet("Benchmark summary", 1)
    ws["A1"] = "Free-market rent benchmark, EUR/m2 per month, by postal area and flat size"
    ws["A1"].font = H1

    ws["A3"], ws["B3"] = "Benchmark quarter", bm.LATEST
    ws["A4"], ws["B4"] = "Minimum observations", bm.MIN_OBS
    ws["A5"], ws["B5"] = "Year-ago quarter", '=(LEFT(B3,4)-1)&RIGHT(B3,2)'
    ws["A6"], ws["B6"] = "Five-years-ago quarter", '=(LEFT(B3,4)-5)&RIGHT(B3,2)'
    for c in ("B3", "B4"):
        ws[c].fill = INPUT_FILL
        ws[c].border = BOX
    for c in ("A3", "A4", "A5", "A6"):
        ws[c].font = BOLD
    ws["C3"] = "Yellow cells are inputs. 2025Q2 is the last quarter before the 2025Q3-Q4 method shift."
    ws["C4"] = "A figure is shown only if every quarter it uses has at least this many observations."
    ws["C3"].font = ws["C4"].font = MUTED

    quarters = sorted(pd.read_csv(PROC / "postcode_rents_2015_2025.csv").quarter.unique())
    ws["Z1"] = "Quarter list"
    for i, q in enumerate(quarters, start=2):
        ws.cell(row=i, column=26, value=q)
    dv = DataValidation(type="list", formula1=f"=$Z$2:$Z${len(quarters) + 1}", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("B3")
    ws.column_dimensions["Z"].hidden = True

    # Header: two rows. Row 8 = flat size groups, row 9 = measures
    top, sub = 8, 9
    ws.cell(row=top, column=1, value="Postal area")
    ws.cell(row=top, column=2, value="Municipality")
    ws.merge_cells(start_row=top, start_column=1, end_row=sub, end_column=1)
    ws.merge_cells(start_row=top, start_column=2, end_row=sub, end_column=2)
    measures = ["EUR/m2", "Obs (n)", "y/y %", "5-year %"]
    for k, size in enumerate(SIZES):
        c0 = 3 + k * 4
        ws.cell(row=top, column=c0, value=size)
        ws.merge_cells(start_row=top, start_column=c0, end_row=top, end_column=c0 + 3)
        for j, m in enumerate(measures):
            ws.cell(row=sub, column=c0 + j, value=m)
    for r in (top, sub):
        for c in range(1, 15):
            cell = ws.cell(row=r, column=c)
            cell.font, cell.fill, cell.border, cell.alignment = BOLD, HEAD_FILL, BOX, CENTER

    pc = pd.read_csv(PROC / "postcode_rents_2015_2025.csv", dtype={"postcode": str})
    labels = pc.drop_duplicates("postcode").set_index("postcode")
    D = "'Benchmark data'!"
    rng = lambda col: f"{D}${col}$2:${col}${n_data}"  # noqa: E731
    AREA, Q, SIZE, RENT, NOBS = rng("B"), rng("E"), rng("G"), rng("H"), rng("I")

    first = sub + 1
    for i, pcode in enumerate(bm.SELECTED):
        r = first + i
        ws.cell(row=r, column=1, value=f"{pcode} {labels.loc[pcode, 'area_name']}")
        ws.cell(row=r, column=2, value=labels.loc[pcode, "municipality"])
        for k, size in enumerate(SIZES):
            c0 = 3 + k * 4
            a, s = f"$A{r}", f'"{size}"'
            n_q = f"SUMIFS({NOBS},{AREA},{a},{SIZE},{s},{Q},$B$3)"
            n_y = f"SUMIFS({NOBS},{AREA},{a},{SIZE},{s},{Q},$B$5)"
            n_5 = f"SUMIFS({NOBS},{AREA},{a},{SIZE},{s},{Q},$B$6)"
            r_q = f"SUMIFS({RENT},{AREA},{a},{SIZE},{s},{Q},$B$3)"
            r_y = f"SUMIFS({RENT},{AREA},{a},{SIZE},{s},{Q},$B$5)"
            r_5 = f"SUMIFS({RENT},{AREA},{a},{SIZE},{s},{Q},$B$6)"
            # Each (area, size, quarter) has at most one row, so SUMIFS returns that row's value.
            ws.cell(row=r, column=c0, value=f'=IF({n_q}>=$B$4,{r_q},"n/a")')
            ws.cell(row=r, column=c0 + 1, value=f'=IF({n_q}=0,"masked",{n_q})')
            ws.cell(row=r, column=c0 + 2,
                    value=f'=IF(AND({n_q}>=$B$4,{n_y}>=$B$4),{r_q}/{r_y}-1,"n/a")')
            ws.cell(row=r, column=c0 + 3,
                    value=f'=IF(AND({n_q}>=$B$4,{n_5}>=$B$4),{r_q}/{r_5}-1,"n/a")')
            ws.cell(row=r, column=c0).number_format = "0.00"
            ws.cell(row=r, column=c0 + 1).number_format = "0"
            ws.cell(row=r, column=c0 + 2).number_format = "+0.0%;-0.0%;0.0%"
            ws.cell(row=r, column=c0 + 3).number_format = "+0.0%;-0.0%;0.0%"
        for c in range(1, 15):
            ws.cell(row=r, column=c).border = BOX
            if c > 2:
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="right")
    last = first + len(bm.SELECTED) - 1

    note = last + 2
    notes = [
        '"n/a" = fewer observations than the minimum in a quarter the figure needs. '
        '"masked" = Statistics Finland does not publish the cell (under 20 obs, or many rental-company flats).',
        "Averages cover all existing free-market tenancies, not only new leases, so they understate "
        "the rent a newly built building gets. Use the Current rents sheet for new tenancies.",
        "Average EUR/m2 is not quality-adjusted. Changes can reflect a different mix of flats, not only "
        "rent growth. Statistics Finland's index (Area trend sheet) is the quality-adjusted measure.",
        SOURCE_TXT + ", table 13eb (postal code data ends 2025Q4).",
    ]
    for i, t in enumerate(notes):
        ws.cell(row=note + i, column=1, value=t).font = MUTED

    # Chart helper: numeric or #N/A, so masked cells are gaps in the chart rather than zeros.
    hc = 16
    ws.cell(row=sub, column=hc, value="Chart helper")
    for k, size in enumerate(SIZES):
        ws.cell(row=sub, column=hc + 1 + k, value=size)
    for r in range(first, last + 1):
        ws.cell(row=r, column=hc, value=f"=A{r}")
        for k in range(3):
            src = f"{get_column_letter(3 + k * 4)}{r}"
            ws.cell(row=r, column=hc + 1 + k, value=f"=IF(ISNUMBER({src}),{src},NA())")
    for c in range(hc, hc + 4):
        ws.column_dimensions[get_column_letter(c)].hidden = True

    ch = BarChart()
    ch.type = "bar"
    ch.grouping = "clustered"
    ch.title = "Free-market rent by postal area, EUR/m2 per month"
    ch.y_axis.scaling.min = 0
    ch.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill="E0E0E0"))
    ch.x_axis.scaling.orientation = "maxMin"   # first area at the top
    ch.y_axis.crosses = "max"                  # keeps the value axis at the bottom
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.gapWidth = 60
    data = Reference(ws, min_col=hc + 1, max_col=hc + 3, min_row=sub, max_row=last)
    cats = Reference(ws, min_col=hc, min_row=first, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    for s, size in zip(ch.series, SIZES):
        s.graphicalProperties.solidFill = SIZE_COLOURS[size]
        s.graphicalProperties.line.noFill = True
    ch.legend.position = "t"
    ch.visible_cells_only = False   # helper columns are hidden, plot them anyway
    ch.height, ch.width = 14, 22
    no_overlap(ch)
    ws.add_chart(ch, f"A{note + len(notes) + 1}")

    widths(ws, {"A": 32, "B": 13})
    for c in range(3, 15):
        ws.column_dimensions[get_column_letter(c)].width = 9.5
    ws.freeze_panes = f"C{first}"
    return ws


# ---------------------------------------------------------------- Area trend
def sheet_area_trend(wb):
    ws = wb.create_sheet("Area trend")
    a = pd.read_csv(PROC / "benchmark_areas.csv", dtype={"area_code": str})
    a = a[(a["size"] == "All") & (a.quarter <= bm.LATEST)]
    areas = [("091-1", "Helsinki 1"), ("091-2", "Helsinki 2"), ("091-3", "Helsinki 3"),
             ("091-4", "Helsinki 4"), ("091", "Helsinki"), ("049", "Espoo-Kauniainen"),
             ("092", "Vantaa")]
    ws["A1"] = "Free-market rent index (2015=100, quality-adjusted) by area, all flat sizes"
    ws["A1"].font = H1
    ws["A2"] = ("Helsinki 1-4 are Statistics Finland's price zones: 1 = most expensive (central), "
                "4 = least expensive. Series stops at " + bm.LATEST + " (method shift after that).")
    ws["A2"].font = MUTED
    header_row(ws, 4, ["Quarter"] + [n for _, n in areas])
    piv = a.pivot_table(index="quarter", columns="area_code", values="index_2015")
    for i, (q, row) in enumerate(piv.iterrows(), start=5):
        ws.cell(row=i, column=1, value=q)
        for j, (code, _) in enumerate(areas, start=2):
            ws.cell(row=i, column=j, value=float(row[code])).number_format = "0.0"
    last = 4 + len(piv)

    # EUR/m2 block for reference (not quality-adjusted)
    c0 = len(areas) + 3
    ws.cell(row=3, column=c0, value="Average EUR/m2 (not quality-adjusted)").font = H2
    header_row(ws, 4, ["Quarter"] + [n for _, n in areas], start_col=c0)
    piv2 = a.pivot_table(index="quarter", columns="area_code", values="rent_eur_m2")
    for i, (q, row) in enumerate(piv2.iterrows(), start=5):
        ws.cell(row=i, column=c0, value=q)
        for j, (code, _) in enumerate(areas, start=1):
            ws.cell(row=i, column=c0 + j, value=float(row[code])).number_format = "0.00"

    # 5-year and 1-year index change, formulas
    r = last + 2
    ws.cell(row=r, column=1, value="Index change").font = H2
    ws.cell(row=r + 1, column=1, value="1 year")
    ws.cell(row=r + 2, column=1, value="5 years")
    for j in range(2, len(areas) + 2):
        col = get_column_letter(j)
        ws.cell(row=r + 1, column=j, value=f"={col}{last}/{col}{last - 4}-1").number_format = "+0.0%;-0.0%"
        ws.cell(row=r + 2, column=j, value=f"={col}{last}/{col}{last - 20}-1").number_format = "+0.0%;-0.0%"
    ws.cell(row=r + 3, column=1, value=f"{SOURCE_TXT}, table 11x4.").font = MUTED

    ch = LineChart()
    ch.title = "Rent index by Helsinki price zone (2015=100)"
    ch.y_axis.scaling.min = 98
    ch.y_axis.number_format = "0"
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill="E0E0E0"))
    ch.add_data(Reference(ws, min_col=2, max_col=5, min_row=4, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=last))
    for s, col in zip(ch.series, ["2A78D6", "EB6834", "1BAF7A", "4A3AA7"]):
        s.graphicalProperties.line.solidFill = col
        s.graphicalProperties.line.width = 22000
        s.smooth = False
    ch.x_axis.tickLblSkip = 4
    ch.legend.position = "t"
    ch.height, ch.width = 10, 20
    no_overlap(ch)
    ws.add_chart(ch, f"A{r + 5}")
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions[get_column_letter(c0)].width = 10
    ws.freeze_panes = "B5"


# ---------------------------------------------------------------- Current rents (15fa)
def sheet_current(wb):
    ws = wb.create_sheet("Current rents")
    c = pd.read_csv(PROC / "current_rents_15fa.csv", dtype={"area_code": str})
    latest_q = c.quarter.max()
    ws["A1"] = f"Current free-market rents, {latest_q}, EUR/m2 per month (new 2025=100 method)"
    ws["A1"].font = H1
    ws["A2"] = ("'New tenancies' = leases that started, or asking rents listed, in the quarter. "
                "This is the anchor for a newly built building's rent.")
    ws["A2"].font = MUTED
    header_row(ws, 4, ["Area", "Flat size", "All tenancies EUR/m2", "Obs (n)",
                       "New tenancies EUR/m2", "Obs new (n)", "New vs all"])
    order = ["091", "091-1", "091-2", "091-3", "091-4", "049", "049-1", "049-2", "049-3",
             "092", "092-1", "092-2", "092-3", "pks", "ksu"]
    cur = c[c.quarter == latest_q].copy()
    cur["o"] = cur.area_code.map({k: i for i, k in enumerate(order)})
    cur["s"] = cur["size"].map({"All": 0, "Studio": 1, "One-bedroom": 2, "Two-bedroom+": 3})
    cur = cur.sort_values(["o", "s"])
    r = 5
    where = {}
    for row in cur.itertuples():
        where[(row.area_code, row.size)] = r
        area = row.area if row.area_code != "ksu" else "Whole country"
        vals = [area, row.size, row.rent_eur_m2, row.n_rent, row.rent_new_eur_m2, row.n_rent_new]
        for j, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=j, value=v)
            cell.border = BOX
        ws.cell(row=r, column=3).number_format = "0.00"
        ws.cell(row=r, column=5).number_format = "0.00"
        ws.cell(row=r, column=4).number_format = "#,##0"
        ws.cell(row=r, column=6).number_format = "#,##0"
        ws.cell(row=r, column=7, value=f"=E{r}/C{r}-1").number_format = "+0.0%;-0.0%;0.0%"
        ws.cell(row=r, column=7).border = BOX
        if row.size == "All":
            for j in range(1, 8):
                ws.cell(row=r, column=j).font = BOLD
        r += 1
    ws.cell(row=r + 1, column=1, value=f"{SOURCE_TXT}, table 15fa ({latest_q}).").font = MUTED
    ws.cell(row=r + 2, column=1, value=(
        "Not comparable with the 2015-2025 tables: 15fa uses arithmetic means and includes asking "
        "rents, the archived tables use geometric means.")).font = MUTED
    widths(ws, {"A": 24, "B": 14, "C": 12, "D": 10, "E": 12, "F": 11, "G": 10})
    ws.freeze_panes = "A5"
    return where


# ---------------------------------------------------------------- Sources and About
def sheet_sources(wb):
    ws = wb.create_sheet("Sources")
    ws["A1"] = "Sources"
    ws["A1"].font = H1
    header_row(ws, 3, ["Table", "Content", "Used for", "API URL", "Fetched"])
    rows = [
        ("13eb (archived)", "Free-market average rent EUR/m2 by postal code, 2015Q1-2025Q4",
         "Benchmark summary, Benchmark data",
         "https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px"),
        ("11x4 (archived)", "Rent index 2015=100 and average EUR/m2 by area, 2015Q1-2025Q4",
         "Area trend, rent forecast",
         "https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_11x4_2025q4.px"),
        ("15fa (current)", "Rent index 2025=100 and average EUR/m2 incl. new tenancies, 2025Q1-2026Q2",
         "Current rents, lease-up model rent anchor",
         "https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin/asvu/15fa.px"),
    ]
    fetched = sorted((ROOT / "data" / "raw").glob("13eb_data_*.json"))[-1].stem.split("_")[-1]
    for i, row in enumerate(rows, start=4):
        for j, v in enumerate(list(row) + [fetched], start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment, c.border = WRAP, BOX
    ws["A8"] = "All data: Statistics Finland, rents of dwellings, licensed CC BY 4.0. Documentation: https://stat.fi/tilasto/asvu"
    ws["A9"] = "Full list of assumptions and data checks: notes/assumptions_and_sources.md in the project repository."
    ws["A8"].font = ws["A9"].font = MUTED
    widths(ws, {"A": 16, "B": 44, "C": 30, "D": 60, "E": 11})


def sheet_about(wb):
    ws = wb.active
    ws.title = "About"
    lines = [
        ("Helsinki rental market benchmark and lease-up model", H1),
        ("", None),
        ("Question 1: what is the market rent for free-market flats in Helsinki-area postal codes?", None),
        ("Question 2: how much does lease-up speed matter for a new building's first-year income?", None),
        ("", None),
        ("Sheets", H2),
        ("Inputs: every assumption of the lease-up model, with its source. HYPOTHETICAL building of 70 flats in Helsinki zone 2.", None),
        ("Lease-up model: month-by-month occupancy, rent, incentives, operating costs and NOI for three letting speeds.", None),
        ("Sensitivity: year-1 NOI for lease-up time x rent level, breakeven rent cut, and the cost after year 1.", None),
        ("Charts: occupancy curves, cumulative NOI and year-1 NOI by scenario.", None),
        ("Benchmark summary: EUR/m2, y/y and 5-year change for 18 postal areas by flat size. Formula-driven.", None),
        ("Benchmark data: quarterly postal-code data, 2015-2025, as an Excel table. Source for the pivot table.", None),
        ("Area trend: Statistics Finland's quality-adjusted rent index by Helsinki price zone.", None),
        ("Current rents: latest quarter, incl. EUR/m2 for new tenancies.", None),
        ("Sources: tables, API links and fetch dates.", None),
        ("", None),
        ("Colour code: yellow cells are inputs you can change. Everything else is a formula or source data.", None),
        ("Built with Python (openpyxl) and Claude Code. Data: Statistics Finland, rents of dwellings, CC BY 4.0.", MUTED),
    ]
    for i, (t, f) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=t)
        if f:
            c.font = f
    ws.column_dimensions["A"].width = 110


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    sheet_about(wb)
    n_data = sheet_benchmark_data(wb)
    sheet_benchmark_summary(wb, n_data)
    sheet_area_trend(wb)
    rent_rows = sheet_current(wb)
    sheet_sources(wb)
    # Part 3: lease-up model, placed right after About
    lu.sheet_inputs(wb, rent_rows, 1)
    model_ws, starts, s_row = lu.sheet_model(wb, 2)
    lu.sheet_sensitivity(wb, 3)
    lu.sheet_charts(wb, model_ws, starts, s_row, 4)
    wb.save(OUT)
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()

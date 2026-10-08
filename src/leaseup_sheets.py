"""Lease-up model sheets for Helsinki_Rental_Benchmark.xlsx (Part 3).

Imported by 04_build_model.py. Every model cell is an Excel formula that refers back to the
Inputs sheet through named ranges, so changing an input updates the whole workbook.

Model logic (monthly, months 1-12):
  occupancy(m)   = Stab_occ * MIN(1, m / T)            linear lease-up over T months
  new leases(m)  = (occupancy(m) - occupancy(m-1)) * Units
  gross rent(m)  = GPR * occupancy(m) * growth(m)       GPR = rent if every flat were let
  incentives(m)  = -new leases(m) * GPR / Units * growth(m) * Free_months * Incentive_on
  opex(m)        = -Opex_m2 * Total_m2                   paid on all flats, let or vacant
  NOI(m)         = gross rent + incentives + opex
"""
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

H1 = Font(bold=True, size=14)
H2 = Font(bold=True, size=11)
BOLD = Font(bold=True)
MUTED = Font(italic=True, color="595959", size=9)
RED = Font(bold=True, color="C00000")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
HEAD_FILL = PatternFill("solid", fgColor="D9E1F2")
KEY_FILL = PatternFill("solid", fgColor="E2EFDA")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
TOPLINE = Border(top=Side(style="thin", color="000000"))
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
WRAP = Alignment(wrap_text=True, vertical="top")

EUR = '#,##0;-#,##0;"-"'
EUR2 = '#,##0.00'
PCT1 = '0.0%'
SCEN_COLOURS = ["2A78D6", "EB6834", "1BAF7A"]

FLATS = [  # type, number, m2, size key used on the Current rents sheet
    ("Studio", 28, 26, "Studio"),
    ("One-bedroom", 28, 40, "One-bedroom"),
    ("Two-bedroom+", 14, 60, "Two-bedroom+"),
]
ZONE = "091-2"


def name(wb, nm, ref):
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


def inp(cell, value, fmt=None):
    cell.value = value
    cell.fill = INPUT_FILL
    cell.border = BOX
    if fmt:
        cell.number_format = fmt


def heads(ws, row, values, col=1):
    for i, v in enumerate(values):
        c = ws.cell(row=row, column=col + i, value=v)
        c.font, c.fill, c.border, c.alignment = BOLD, HEAD_FILL, BOX, CENTER


def no_overlap(ch):
    from openpyxl.chart.layout import Layout, ManualLayout
    ch.title.overlay = False
    ch.legend.overlay = False
    ch.layout = Layout(manualLayout=ManualLayout(yMode="edge", xMode="edge", x=0.0, y=0.12, h=0.86, w=1.0))


# ------------------------------------------------------------------ Inputs
def sheet_inputs(wb, rent_rows, pos):
    ws = wb.create_sheet("Inputs", pos)
    ws["A1"] = "Inputs: hypothetical new build-to-rent building, Helsinki price zone 2"
    ws["A1"].font = H1
    ws["A2"] = ("HYPOTHETICAL BUILDING. Not a valuation of any real property or fund. "
                "Yellow cells are inputs. Every other number is a formula.")
    ws["A2"].font = RED

    heads(ws, 4, ["Flat type", "Number of flats", "Size, m2", "Market rent, EUR/m2/month",
                  "Rent per flat, EUR/month", "Rent if all let, EUR/month", "Source"])
    for i, (label, n, m2, key) in enumerate(FLATS):
        r = 5 + i
        ws.cell(row=r, column=1, value=label).border = BOX
        inp(ws.cell(row=r, column=2), n, "0")
        inp(ws.cell(row=r, column=3), m2, "0")
        c = ws.cell(row=r, column=4, value=f"='Current rents'!E{rent_rows[(ZONE, key)]}")
        c.number_format, c.border = EUR2, BOX
        c = ws.cell(row=r, column=5, value=f"=C{r}*D{r}*(1+Rent_adj)")
        c.number_format, c.border = EUR, BOX
        c = ws.cell(row=r, column=6, value=f"=B{r}*E{r}")
        c.number_format, c.border = EUR, BOX
        ws.cell(row=r, column=7, value=("Rent: Statistics Finland 15fa, new tenancies, Helsinki zone 2, "
                                        "latest quarter (linked). Size: assumption within Rakli-Taaleri "
                                        "2026 typical range")).alignment = WRAP
    ws["A8"] = "Total"
    ws["B8"] = "=SUM(B5:B7)"
    ws["C8"] = "=SUMPRODUCT(B5:B7,C5:C7)"
    ws["D8"] = "=SUMPRODUCT(B5:B7,C5:C7,D5:D7)/C8"
    ws["F8"] = "=SUM(F5:F7)"
    ws["G8"] = "C8 = total lettable m2. D8 = average market rent per m2, weighted by area."
    for c in ("A8", "B8", "C8", "D8", "F8"):
        ws[c].font, ws[c].border = BOLD, TOPLINE
    ws["C8"].number_format, ws["D8"].number_format, ws["F8"].number_format = "#,##0", EUR2, EUR
    ws["G8"].font = MUTED
    name(wb, "Units", "Inputs!$B$8")
    name(wb, "Total_m2", "Inputs!$C$8")
    name(wb, "GPR", "Inputs!$F$8")

    heads(ws, 10, ["Assumption", "Value", "Unit", "Basis and source"])
    params = [
        ("Rent_adj", "Rent level vs market", 0.0, "%", PCT1,
         "Base case = market (0%). Negative = discount to let faster."),
        ("Rent_growth", "Rent growth during year one", 0.0, "% per year", PCT1,
         "Base 0%. Part 2 forecast: ARIMA drift +2.1%/yr overstated growth, actual 2025Q2-2026Q2 was -0.2%."),
        ("Stab_occ", "Stabilised occupancy", 0.97, "% of flats", PCT1,
         "Assumption. Kojamo valuation uses 97.5% (10-yr avg, capital region, 31.12.2025). Market now 93.4% (KTI, Dec 2025)."),
        ("LeaseUp_A", "Lease-up time, scenario A", 3, "months", "0", "Assumption: months until stabilised occupancy."),
        ("LeaseUp_B", "Lease-up time, scenario B", 6, "months", "0", "Assumption."),
        ("LeaseUp_C", "Lease-up time, scenario C", 9, "months", "0", "Assumption."),
        ("Free_months", "Free rent per new lease", 1, "months", "0",
         "Assumption. JLL Q1 2026: incentives 'remain widely used', no size given."),
        ("Incentive_on", "Incentive switch", 1, "1 = on, 0 = off", "0", "Set to 0 to remove the free month."),
        ("Opex_m2", "Operating costs", 6.0, "EUR/m2/month", EUR2,
         "Assumption, paid on all flats. Kojamo 6.75 (incl. repairs, older stock), Statistics Finland 6.17 (housing companies 2025)."),
        ("Yield_val", "Valuation yield", 0.043, "%", "0.00%",
         "Prime residential yield 4.3% (Catella Q3 2025 via Rakli-Taaleri, JLL Q1 2026). Kojamo capital region 4.22%."),
    ]
    for i, (nm, label, val, unit, fmt, src) in enumerate(params):
        r = 11 + i
        ws.cell(row=r, column=1, value=label).border = BOX
        inp(ws.cell(row=r, column=2), val, fmt)
        ws.cell(row=r, column=3, value=unit).border = BOX
        c = ws.cell(row=r, column=4, value=src)
        c.alignment, c.border = WRAP, BOX
        name(wb, nm, f"Inputs!$B${r}")

    r0 = 11 + len(params) + 1
    ws.cell(row=r0, column=1, value="Stabilised year (all flats let at stabilised occupancy)").font = H2
    derived = [
        ("GPR_annual", "Rent if every flat were let, per year", "=GPR*12", EUR),
        ("Stab_gross", "Gross rent at stabilised occupancy, per year", "=GPR_annual*Stab_occ", EUR),
        ("Opex_annual", "Operating costs, per year", "=Opex_m2*Total_m2*12", EUR),
        ("Stab_NOI", "Stabilised NOI, per year", "=Stab_gross-Opex_annual", EUR),
        (None, "NOI margin", "=Stab_NOI/Stab_gross", PCT1),
        ("Value_ind", "Indicative value = stabilised NOI / yield", "=Stab_NOI/Yield_val", EUR),
        (None, "Indicative value per m2", "=Value_ind/Total_m2", EUR),
    ]
    for i, (nm, label, f, fmt) in enumerate(derived):
        r = r0 + 1 + i
        ws.cell(row=r, column=1, value=label).border = BOX
        c = ws.cell(row=r, column=2, value=f)
        c.number_format, c.border = fmt, BOX
        if nm:
            name(wb, nm, f"Inputs!$B${r}")
        if nm == "Stab_NOI":
            ws.cell(row=r, column=1).font = BOLD
            c.font = BOLD
    r1 = r0 + len(derived) + 2
    notes = [
        "NOI = net operating income: rent received minus the owner's operating costs, before financing and tax.",
        "Occupancy = share of flats let. Lease-up = the period after completion when the empty building fills with tenants.",
        "Yield = NOI / value. A 4.3% yield means investors pay about 23 times the annual NOI (1 / 0.043).",
        "The value line is a simple check, not a valuation. A real appraisal uses a 10-year cash flow.",
    ]
    for i, t in enumerate(notes):
        ws.cell(row=r1 + i, column=1, value=t).font = MUTED
    for col, w in {"A": 44, "B": 14, "C": 16, "D": 24, "E": 16, "F": 18, "G": 60}.items():
        ws.column_dimensions[col].width = w
    ws.column_dimensions["D"].width = 24
    for r in range(11, 11 + len(params)):
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=7)
        ws.row_dimensions[r].height = 30
    ws.merge_cells(start_row=10, start_column=4, end_row=10, end_column=7)
    for r in range(5, 8):
        ws.row_dimensions[r].height = 30
    return ws


# ------------------------------------------------------------------ Lease-up model
ROWS = ["Occupancy", "Let flats", "New leases", "Rent growth factor", "Gross rental income",
        "Leasing incentives", "Operating costs", "NOI", "Cumulative NOI"]


def sheet_model(wb, pos):
    ws = wb.create_sheet("Lease-up model", pos)
    ws["A1"] = "Lease-up model: first 12 months after completion, three letting speeds"
    ws["A1"].font = H1
    ws["A2"] = "Hypothetical building. EUR. Costs are negative. All cells are formulas linked to Inputs."
    ws["A2"].font = MUTED
    first_c, last_c = 3, 14
    tot_c = 15
    ws.cell(row=4, column=1, value="Month").font = BOLD
    for m in range(1, 13):
        c = ws.cell(row=4, column=first_c + m - 1, value=m)
        c.font, c.fill, c.alignment, c.border = BOLD, HEAD_FILL, CENTER, BOX
    c = ws.cell(row=4, column=tot_c, value="Year 1")
    c.font, c.fill, c.alignment, c.border = BOLD, HEAD_FILL, CENTER, BOX
    ws.cell(row=4, column=2, value="Lease-up months").font = BOLD

    starts = {}
    r = 6
    for k, (key, label) in enumerate([("LeaseUp_A", "A"), ("LeaseUp_B", "B"), ("LeaseUp_C", "C")]):
        starts[label] = r
        hc = ws.cell(row=r, column=1, value=f'="Scenario {label}: stabilised after "&{key}&" months"')
        hc.font = Font(bold=True, size=11, color=SCEN_COLOURS[k])
        ws.cell(row=r, column=2, value=f"={key}").number_format = "0"
        ws.cell(row=r, column=2).font = BOLD
        rr = {nm: r + 1 + i for i, nm in enumerate(ROWS)}
        T = f"$B${r}"
        for i, nm in enumerate(ROWS):
            ws.cell(row=rr[nm], column=1, value=nm)
        for m in range(1, 13):
            col = first_c + m - 1
            L, P = get_column_letter(col), get_column_letter(col - 1)
            mcell = f"{L}$4"
            f = {
                "Occupancy": f"=Stab_occ*MIN(1,{mcell}/{T})",
                "Let flats": f"={L}{rr['Occupancy']}*Units",
                "New leases": (f"={L}{rr['Let flats']}" if m == 1 else f"={L}{rr['Let flats']}-{P}{rr['Let flats']}"),
                "Rent growth factor": f"=(1+Rent_growth)^(({mcell}-1)/12)",
                "Gross rental income": f"=GPR*{L}{rr['Occupancy']}*{L}{rr['Rent growth factor']}",
                "Leasing incentives": (f"=-{L}{rr['New leases']}*GPR/Units*{L}{rr['Rent growth factor']}"
                                       f"*Free_months*Incentive_on"),
                "Operating costs": "=-Opex_m2*Total_m2",
                "NOI": f"={L}{rr['Gross rental income']}+{L}{rr['Leasing incentives']}+{L}{rr['Operating costs']}",
                "Cumulative NOI": (f"={L}{rr['NOI']}" if m == 1 else f"={P}{rr['Cumulative NOI']}+{L}{rr['NOI']}"),
            }
            for nm, formula in f.items():
                c = ws.cell(row=rr[nm], column=col, value=formula)
                c.number_format = {"Occupancy": PCT1, "Let flats": "0.0", "New leases": "0.0",
                                   "Rent growth factor": "0.0000"}.get(nm, EUR)
        TL = lambda nm: f"{get_column_letter(first_c)}{rr[nm]}:{get_column_letter(last_c)}{rr[nm]}"  # noqa: E731
        totals = {"Occupancy": f"=AVERAGE({TL('Occupancy')})", "New leases": f"=SUM({TL('New leases')})",
                  "Gross rental income": f"=SUM({TL('Gross rental income')})",
                  "Leasing incentives": f"=SUM({TL('Leasing incentives')})",
                  "Operating costs": f"=SUM({TL('Operating costs')})", "NOI": f"=SUM({TL('NOI')})"}
        for nm, formula in totals.items():
            c = ws.cell(row=rr[nm], column=tot_c, value=formula)
            c.number_format = PCT1 if nm == "Occupancy" else ("0.0" if nm == "New leases" else EUR)
            c.font = BOLD
        for col in range(1, tot_c + 1):
            ws.cell(row=rr["NOI"], column=col).font = BOLD
            ws.cell(row=rr["NOI"], column=col).border = TOPLINE
        r = rr["Cumulative NOI"] + 2

    # Summary
    s = r + 1
    ws.cell(row=s - 1, column=1, value="Summary, year 1").font = H2
    heads(ws, s, ["Scenario", "Lease-up months", "Average occupancy", "Gross rental income",
                  "Leasing incentives", "Operating costs", "Year-1 NOI", "Year-1 NOI as % of stabilised NOI",
                  "NOI lost vs scenario A"])
    for k, lab in enumerate(["A", "B", "C"]):
        r = s + 1 + k
        b = starts[lab]
        occ, gri, inc, opx, noi = (b + 1, b + 5, b + 6, b + 7, b + 8)
        Tc = get_column_letter(tot_c)
        vals = [f"Scenario {lab}", f"=B{b}", f"={Tc}{occ}", f"={Tc}{gri}", f"={Tc}{inc}", f"={Tc}{opx}",
                f"={Tc}{noi}", f"=G{r}/Stab_NOI", f"=G{s + 1}-G{r}"]
        for j, v in enumerate(vals):
            c = ws.cell(row=r, column=1 + j, value=v)
            c.border = BOX
            c.number_format = ["@", "0", PCT1, EUR, EUR, EUR, EUR, PCT1, EUR][j]
        ws.cell(row=r, column=1).font = Font(bold=True, color=SCEN_COLOURS[k])
    ws.cell(row=s + 4, column=1, value="Stabilised NOI per year (from Inputs)").border = BOX
    c = ws.cell(row=s + 4, column=7, value="=Stab_NOI")
    c.number_format, c.border = EUR, BOX

    k0 = s + 6
    ws.cell(row=k0, column=1, value="Key output").font = H2
    key = [
        ('="First-year NOI lost by letting in "&LeaseUp_C&" months instead of "&LeaseUp_A&", EUR"', f"=I{s + 3}", EUR),
        ('="Same, as % of stabilised annual NOI"', f"=I{s + 3}/Stab_NOI", PCT1),
        ('="First-year NOI lost by letting in "&LeaseUp_B&" months instead of "&LeaseUp_A&", EUR"', f"=I{s + 2}", EUR),
        ('="Each extra month of lease-up costs about, EUR"', f"=I{s + 3}/(LeaseUp_C-LeaseUp_A)", EUR),
    ]
    for i, (lab, f, fmt) in enumerate(key):
        r = k0 + 1 + i
        ws.cell(row=r, column=1, value=lab).border = BOX
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        c = ws.cell(row=r, column=7, value=f)
        c.number_format, c.font, c.fill, c.border = fmt, BOLD, KEY_FILL, BOX
    name(wb, "Lost_C_vs_A", f"'Lease-up model'!$G${k0 + 1}")
    name(wb, "NOI_B", f"'Lease-up model'!$G${s + 2}")
    ws.cell(row=k0 + 6, column=1, value=(
        "Why slow letting hurts: operating costs are paid on every flat from month 1, but rent comes only "
        "from let flats. The free-month incentive costs the same in total in every scenario, because the same "
        "number of leases is signed in year 1. Only its timing differs.")).font = MUTED

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 10
    for col in range(first_c, tot_c + 1):
        ws.column_dimensions[get_column_letter(col)].width = 11.5
    ws.column_dimensions[get_column_letter(tot_c)].width = 13
    ws.freeze_panes = "C5"
    return ws, starts, s


# ------------------------------------------------------------------ Sensitivity
def sheet_sensitivity(wb, pos):
    ws = wb.create_sheet("Sensitivity", pos)
    ws["A1"] = "Sensitivity: lease-up speed vs rent level"
    ws["A1"].font = H1
    ws["A2"] = ("Question: is it better to cut rent and fill faster, or hold rent and fill slower? "
                "Yellow cells are inputs. Other inputs come from the Inputs sheet.")
    ws["A2"].font = MUTED

    Ts = [3, 6, 9, 12]
    rs = [-0.10, -0.05, 0.0, 0.05]

    # Helper block (rows 40+): occupancy and new leases per lease-up time, month by month
    hb = 60
    ws.cell(row=hb - 1, column=1, value="Helper: occupancy by month for each lease-up time (same formula as the Lease-up model)").font = H2
    heads(ws, hb, ["Month", "Growth factor"] + [f"Occ, T col {i + 1}" for i in range(4)]
          + [f"New, T col {i + 1}" for i in range(4)])
    for m in range(1, 13):
        r = hb + m
        ws.cell(row=r, column=1, value=m)
        ws.cell(row=r, column=2, value=f"=(1+Rent_growth)^((A{r}-1)/12)").number_format = "0.0000"
        for j in range(4):
            Tref = f"{get_column_letter(2 + j)}$6"
            oc = ws.cell(row=r, column=3 + j, value=f"=Stab_occ*MIN(1,$A{r}/{Tref})")
            oc.number_format = PCT1
            O = get_column_letter(3 + j)
            nf = f"={O}{r}" if m == 1 else f"={O}{r}-{O}{r - 1}"
            ws.cell(row=r, column=7 + j, value=nf).number_format = PCT1
    sr = hb + 13
    ws.cell(row=sr, column=1, value="Sum, weighted by growth")
    for j in range(4):
        O, N = get_column_letter(3 + j), get_column_letter(7 + j)
        ws.cell(row=sr, column=3 + j, value=f"=SUMPRODUCT({O}{hb + 1}:{O}{hb + 12},$B${hb + 1}:$B${hb + 12})").number_format = "0.000"
        ws.cell(row=sr, column=7 + j, value=f"=SUMPRODUCT({N}{hb + 1}:{N}{hb + 12},$B${hb + 1}:$B${hb + 12})").number_format = "0.000"
    ws.cell(row=sr + 1, column=1, value="Market rent income factor A(T)")
    for j in range(4):
        O, N = get_column_letter(3 + j), get_column_letter(7 + j)
        ws.cell(row=sr + 1, column=3 + j, value=f"=GPR*({O}{sr}-Free_months*Incentive_on*{N}{sr})").number_format = EUR
    ws.cell(row=sr + 2, column=1, value=(
        "A(T) = year-1 rent minus incentives at market rent and lease-up time T. Year-1 NOI at rent level r = "
        "(1+r) x A(T) - annual operating costs. Rent level here replaces the Inputs rent adjustment.")).font = MUTED
    AT = {j: f"${get_column_letter(3 + j)}${sr + 1}" for j in range(4)}

    # Table 1: year-1 NOI
    t1 = 5
    ws.cell(row=t1 - 1, column=1, value="Table 1. Year-1 NOI, EUR").font = H2
    ws.cell(row=t1, column=1, value="Lease-up months →").font = BOLD
    for j, T in enumerate(Ts):
        inp(ws.cell(row=t1 + 1, column=2 + j), T, "0")
    ws.cell(row=t1 + 1, column=1, value="Rent vs market ↓").font = BOLD
    for i, rv in enumerate(rs):
        r = t1 + 2 + i
        inp(ws.cell(row=r, column=1), rv, '+0%;-0%;0%')
        for j in range(4):
            c = ws.cell(row=r, column=2 + j, value=f"=(1+$A{r})*{AT[j]}-Opex_annual")
            c.number_format, c.border = EUR, BOX
    t1_rows = list(range(t1 + 2, t1 + 2 + len(rs)))
    # base cell: market rent (0%) row, 6 months = second lease-up column (C)
    base = f"$C${t1_rows[2]}"

    # Table 2: difference vs base
    t2 = t1 + 8
    ws.cell(row=t2 - 1, column=1, value="Table 2. Year-1 NOI vs base case (6 months, market rent), EUR").font = H2
    for j in range(4):
        c = ws.cell(row=t2, column=2 + j, value=f"={get_column_letter(2 + j)}{t1 + 1}")
        c.font, c.fill, c.border, c.number_format = BOLD, HEAD_FILL, BOX, '0" months"'
    for i in range(len(rs)):
        r = t2 + 1 + i
        c = ws.cell(row=r, column=1, value=f"=A{t1_rows[i]}")
        c.number_format, c.font = '+0%;-0%;0%', BOLD
        for j in range(4):
            c = ws.cell(row=r, column=2 + j, value=f"={get_column_letter(2 + j)}{t1_rows[i]}-{base}")
            c.number_format, c.border = '+#,##0;-#,##0;0', BOX

    # Table 3: breakeven rent cut
    t3 = t2 + 7
    ws.cell(row=t3 - 1, column=1, value="Table 3. Breakeven: the largest rent cut that still pays off in year 1").font = H2
    ws.cell(row=t3, column=1, value="Fill in (rows) instead of (columns)").font = BOLD
    for j in range(4):
        c = ws.cell(row=t3, column=2 + j, value=f"={get_column_letter(2 + j)}{t1 + 1}")
        c.font, c.fill, c.border, c.number_format = BOLD, HEAD_FILL, BOX, '0" months"'
    for i in range(4):
        r = t3 + 1 + i
        c = ws.cell(row=r, column=1, value=f"={get_column_letter(2 + i)}{t1 + 1}")
        c.number_format, c.font = '0" months"', BOLD
        for j in range(4):
            if j > i:
                f = f"={AT[j]}/{AT[i]}-1"
                c = ws.cell(row=r, column=2 + j, value=f)
                c.number_format = '0.0%'
            else:
                c = ws.cell(row=r, column=2 + j, value="-")
                c.alignment = Alignment(horizontal="center")
            c.border = BOX
    ws.cell(row=t3 + 5, column=1, value=(
        "Read: to let in 3 months instead of 6, you can cut rent by up to this % and still earn the same "
        "year-1 NOI. Operating costs cancel out because they are the same in both cases.")).font = MUTED

    # Table 4: after year one
    t4 = t3 + 8
    ws.cell(row=t4 - 1, column=1, value="Table 4. The catch: a lower rent keeps costing after year 1").font = H2
    ex = [("Fill in (months)", 3, "0"), ("instead of (months)", 6, "0"), ("by cutting rent by", -0.05, '+0.0%;-0.0%')]
    for i, (lab, v, fmt) in enumerate(ex):
        ws.cell(row=t4 + i, column=1, value=lab).border = BOX
        inp(ws.cell(row=t4 + i, column=2), v, fmt)
    fT, sT, cut = f"$B${t4}", f"$B${t4 + 1}", f"$B${t4 + 2}"
    # A(T) lookup by matching T in the table-1 header
    hdr = f"$B${t1 + 1}:$E${t1 + 1}"
    arow = f"$C${sr + 1}:$F${sr + 1}"
    outs = [
        ("Year-1 NOI, faster with rent cut", f"=(1+{cut})*INDEX({arow},MATCH({fT},{hdr},0))-Opex_annual", EUR),
        ("Year-1 NOI, slower at market rent", f"=INDEX({arow},MATCH({sT},{hdr},0))-Opex_annual", EUR),
        ("Year-1 gain from cutting rent", f"=B{t4 + 3}-B{t4 + 4}", '+#,##0;-#,##0;0'),
        ("Rent lost per month after year 1, while the discounted leases run", f"=-{cut}*Stab_gross/12", EUR),
        ("Months after year 1 until the gain is used up", f'=IF(B{t4 + 5}<=0,"no gain",B{t4 + 5}/B{t4 + 6})', "0.0"),
        ("Value effect if the cut were permanent (NOI change / yield)", f"={cut}*Stab_gross/Yield_val", '+#,##0;-#,##0;0'),
    ]
    for i, (lab, f, fmt) in enumerate(outs):
        r = t4 + 3 + i
        ws.cell(row=r, column=1, value=lab).border = BOX
        c = ws.cell(row=r, column=2, value=f)
        c.number_format, c.border = fmt, BOX
        if i in (2, 4, 5):
            c.font, c.fill = BOLD, KEY_FILL
    ws.cell(row=t4 + 10, column=1, value=(
        "Finnish leases usually run until further notice with an annual rent increase clause, so a discount "
        "given at signing can last as long as the tenant stays. How long that is was not measured here.")).font = MUTED

    # Table 5: yield
    t5 = t4 + 13
    ws.cell(row=t5 - 1, column=1, value="Table 5. Indicative value at different yields, EUR").font = H2
    for j, y in enumerate([0.040, 0.043, 0.045, 0.050]):
        inp(ws.cell(row=t5, column=2 + j), y, "0.00%")
        c = ws.cell(row=t5 + 1, column=2 + j, value=f"=Stab_NOI/{get_column_letter(2 + j)}{t5}")
        c.number_format, c.border = EUR, BOX
    ws.cell(row=t5, column=1, value="Yield").font = BOLD
    ws.cell(row=t5 + 1, column=1, value="Value = stabilised NOI / yield").font = BOLD
    ws.cell(row=t5 + 2, column=1, value="Range: prime 4.3% (Catella, JLL). Kojamo capital region 4.22%. 5.0% for a weaker market.").font = MUTED

    ws.cell(row=t1, column=7, value="Check: base cell equals Lease-up model scenario B").font = MUTED
    ws.cell(row=t1 + 1, column=7, value=f'=IF(AND(LeaseUp_B=6,Rent_adj=0),IF(ABS({base}-NOI_B)<0.01,"OK","MISMATCH"),"n/a: inputs changed")')

    ws.column_dimensions["A"].width = 58
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 14
    return ws, {"t1": t1, "t1_rows": t1_rows, "t4": t4}


# ------------------------------------------------------------------ Charts
def sheet_charts(wb, model_ws, starts, s_row, pos):
    ws = wb.create_sheet("Charts", pos)
    ws["A1"] = "Lease-up charts (hypothetical building)"
    ws["A1"].font = H1

    def line(title, row_offset, fmt, anchor, ymin=None, ymax=None):
        ch = LineChart()
        ch.title = title
        ch.x_axis.title = "Month after completion"
        ch.y_axis.number_format = fmt
        ch.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill="E0E0E0"))
        ch.x_axis.delete = False
        ch.y_axis.delete = False
        if ymin is not None:
            ch.y_axis.scaling.min = ymin
        if ymax is not None:
            ch.y_axis.scaling.max = ymax
        ch.x_axis.tickLblPos = "low"   # month labels below negative values
        for k, lab in enumerate(["A", "B", "C"]):
            r = starts[lab] + row_offset
            data = Reference(model_ws, min_col=3, max_col=14, min_row=r, max_row=r)
            ch.add_data(data, from_rows=True, titles_from_data=False)
            s = ch.series[-1]
            from openpyxl.chart.series import SeriesLabel
            from openpyxl.chart.data_source import StrRef
            s.tx = SeriesLabel(strRef=StrRef(f"'Lease-up model'!$A${starts[lab]}"))
            s.graphicalProperties.line.solidFill = SCEN_COLOURS[k]
            s.graphicalProperties.line.width = 28000
            s.smooth = False
        ch.set_categories(Reference(model_ws, min_col=3, max_col=14, min_row=4, max_row=4))
        ch.legend.position = "t"
        ch.height, ch.width = 9.5, 17
        no_overlap(ch)
        ws.add_chart(ch, anchor)

    line("Occupancy by month", 1, "0%", "A3", ymin=0, ymax=1)
    line("Cumulative NOI, EUR", 9, "#,##0", "A23")

    bc = BarChart()
    bc.type = "col"
    bc.title = "Year-1 NOI by scenario, EUR"
    bc.y_axis.number_format = "#,##0"
    bc.y_axis.scaling.min = 0
    bc.x_axis.delete = False
    bc.y_axis.delete = False
    bc.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill="E0E0E0"))
    bc.add_data(Reference(model_ws, min_col=7, min_row=s_row, max_row=s_row + 3), titles_from_data=True)
    bc.set_categories(Reference(model_ws, min_col=1, min_row=s_row + 1, max_row=s_row + 3))
    bc.series[0].graphicalProperties.solidFill = "2A78D6"
    bc.series[0].graphicalProperties.line.noFill = True
    bc.legend = None
    bc.gapWidth = 80
    bc.height, bc.width = 9.5, 12
    bc.title.overlay = False
    ws.add_chart(bc, "L3")
    ws["L22"] = "Source: Lease-up model sheet. All figures for a hypothetical building."
    ws["L22"].font = MUTED
    return ws

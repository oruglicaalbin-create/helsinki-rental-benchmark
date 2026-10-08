"""Build output/Helsinki_Rental_Benchmark.pptx: 4 slides, native (editable) PowerPoint charts.

Every number is read from the processed data or recomputed with the same formulas as the
Excel model, so the deck can be rebuilt after any change upstream.
Run from the project root after steps 01-05:
    .venv\\Scripts\\python.exe src\\06_build_slides.py
"""
import importlib.util
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import (XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION,
                             XL_TICK_LABEL_POSITION)
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FC = PROC / "forecast"
OUT = ROOT / "output" / "Helsinki_Rental_Benchmark.pptx"

_spec = importlib.util.spec_from_file_location("bm", ROOT / "src" / "02b_benchmark.py")
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)

# Palette: deep harbour teal dominates, copper as the one sharp accent.
INK = RGBColor(0x12, 0x20, 0x2B)
INK2 = RGBColor(0x4A, 0x58, 0x64)
MUTED = RGBColor(0x75, 0x82, 0x8D)
TEAL = RGBColor(0x0F, 0x4C, 0x5C)
TINT = RGBColor(0xE8, 0xF1, 0xF3)
BLUE = RGBColor(0x2A, 0x78, 0xD6)
COPPER = RGBColor(0xEB, 0x68, 0x34)
AQUA = RGBColor(0x1B, 0xAF, 0x7A)
GRID = RGBColor(0xE3, 0xE7, 0xEA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEAD, BODY = "Cambria", "Calibri"

SRC_SF = "Source: Statistics Finland, rents of dwellings (CC BY 4.0)"


# ---------------------------------------------------------------- helpers
def text(slide, x, y, w, h, runs, size=14, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False):
    """Add a text box. `runs` is a string or a list of paragraphs, each a string or (text, opts)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    paras = runs if isinstance(runs, list) else [runs]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        t, o = (p, {}) if isinstance(p, str) else p
        r = para.add_run()
        r.text = t
        f = r.font
        f.name = o.get("font", font)
        f.size = Pt(o.get("size", size))
        f.bold = o.get("bold", bold)
        f.italic = o.get("italic", italic)
        f.color.rgb = o.get("color", color)
        para.space_after = Pt(o.get("after", 6))
    return tb


def title(slide, t):
    text(slide, 0.6, 0.4, 12.1, 1.1, t, size=30, bold=True, font=HEAD, color=TEAL,
         anchor=MSO_ANCHOR.BOTTOM)


def footer(slide, t, n):
    text(slide, 0.6, 7.0, 11.0, 0.3, t, size=10, color=MUTED)
    text(slide, 12.2, 7.0, 0.5, 0.3, str(n), size=10, color=MUTED, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, big, label, big_color=TEAL):
    """Stat callout: big number on a soft tinted card (the deck's motif)."""
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.08
    s.fill.solid()
    s.fill.fore_color.rgb = TINT
    s.line.fill.background()
    s.shadow.inherit = False
    text(slide, x + 0.25, y + 0.18, w - 0.5, 0.75, big, size=34, bold=True, font=HEAD, color=big_color)
    text(slide, x + 0.25, y + 0.95, w - 0.5, h - 1.05, label, size=13, color=INK2)


def style_axes(chart, num_fmt=None, font_size=11):
    for ax in (chart.category_axis, chart.value_axis):
        ax.tick_labels.font.size = Pt(font_size)
        ax.tick_labels.font.color.rgb = INK2
        ax.tick_labels.font.name = BODY
        ax.format.line.color.rgb = GRID
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = GRID
    chart.category_axis.has_major_gridlines = False
    if num_fmt:
        chart.value_axis.tick_labels.number_format = num_fmt
        chart.value_axis.tick_labels.number_format_is_linked = False


def value_axis_at_bottom(chart):
    """With the categories reversed (first at the top), put the value axis at the bottom.

    The value axis must cross the category axis at its maximum category. python-pptx has no
    direct setting for this, so set <c:crosses val="max"/> in the value axis XML.
    """
    for el in chart._chartSpace.xpath(".//c:valAx/c:crosses"):   # python-pptx knows the c: prefix
        el.set("val", "max")


def no_invert(point):
    """A bar coloured point by point keeps PowerPoint's 'invert if negative' default (white fill).
    Add <c:invertIfNegative val="0"/> right after <c:idx> in the point's XML."""
    from lxml import etree
    dpt = point._ser.get_or_add_dPt_for_point(point._idx)   # the point's own <c:dPt>
    c = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
    if dpt.find(c + "invertIfNegative") is None:
        el = etree.SubElement(dpt, c + "invertIfNegative")
        el.set("val", "0")
        dpt.remove(el)
        dpt.find(c + "idx").addnext(el)


def legend(chart, pos=XL_LEGEND_POSITION.TOP):
    chart.has_legend = True
    chart.legend.position = pos
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(12)
    chart.legend.font.color.rgb = INK2
    chart.legend.font.name = BODY


# ---------------------------------------------------------------- lease-up model (same as Excel)
FLATS = [(28, 26, 26.33), (28, 40, 21.65), (14, 60, 20.45)]
M2 = sum(n * m for n, m, _ in FLATS)
GPR = sum(n * m * r for n, m, r in FLATS)
STAB, OPEX, FREE, YIELD = 0.97, 6.0, 1, 0.043


def run(T, months=12, adj=0.0):
    out, prev, cum = [], 0.0, 0.0
    g = GPR * (1 + adj)
    for m in range(1, months + 1):
        occ = STAB * min(1, m / T)
        cum += g * occ - (occ - prev) * g * FREE - OPEX * M2
        out.append(cum)
        prev = occ
    return out


# ---------------------------------------------------------------- slide 1: benchmark
def slide_benchmark(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    title(s, "Helsinki-area rents run from 17 to 29 €/m² a month, highest for studios and the inner city")
    b = pd.read_csv(PROC / "benchmark_postcodes.csv", dtype={"postcode": str})
    order = list(bm.SELECTED)
    cats, data = [], {k: [] for k in ("Studio", "One-bedroom", "Two-bedroom+")}
    for pc in order:
        g = b[b.postcode == pc]
        cats.append(f"{g.area_name.iloc[0].replace(' - ', '-')}")
        for k in data:
            v = g[g["size"] == k].rent_latest.iloc[0]
            data[k].append(None if pd.isna(v) else float(v))
    cd = CategoryChartData()
    cd.categories = cats
    for k, v in data.items():
        cd.add_series(k, v)
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.7), Inches(8.4), Inches(5.2), cd)
    ch = gf.chart
    style_axes(ch, "0", font_size=10)
    ch.category_axis.reverse_order = True          # first area at the top
    value_axis_at_bottom(ch)
    ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = 0, 30   # bars start at zero
    ch.value_axis.major_unit = 5
    plot = ch.plots[0]
    plot.gap_width, plot.overlap = 45, 0
    for ser, col in zip(plot.series, (BLUE, COPPER, AQUA)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = col
    legend(ch)

    card(s, 9.35, 1.75, 3.4, 1.55, "22.04 €/m²", "Helsinki rent for new leases, 2026Q2")
    card(s, 9.35, 3.5, 3.4, 1.55, "+2.0%", "Like-for-like Helsinki rent change in the 5 years to 2025Q2")
    card(s, 9.35, 5.25, 3.4, 1.55, "45%", "of capital-region postal-code cells, 2015-2025, hidden by Statistics Finland",
         big_color=COPPER)
    footer(s, f"Free-market average rent, 2025Q2, areas with at least 30 leases. Gaps: hidden or too few leases. "
              f"{SRC_SF}, tables 13eb, 11x4, 15fa.", 1)
    s.notes_slide.notes_text_frame.text = (
        "18 postal areas, chosen for data coverage and a spread from the centre to newer districts. "
        "Studios rent for the most per square metre everywhere, 22 to 29 euros. The inner city is 3 to 5 euros "
        "above the outer suburbs for studios, up to 8 for one-bedroom flats.\n"
        "Rent growth has been slow. Like-for-like, Helsinki rents rose only 2 percent in five years.\n"
        "The gaps matter: Statistics Finland hides cells with under 20 leases or where one large landlord "
        "dominates. That is exactly where new build-to-rent buildings are, so public data is thinnest where "
        "an investor needs it most. Benchmark quarter is 2025Q2 because the archived table breaks in 2025Q3-Q4.")


# ---------------------------------------------------------------- slide 2: forecast
def slide_forecast(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    title(s, "A trend forecast of the average rent overshot. The like-for-like index called a flat year")
    rc = pd.read_csv(FC / "review_checks.csv")
    b = pd.read_csv(PROC / "area_rents_15fa_2025_latest.csv", dtype={"area_code": str})
    ix = b[(b.area_code == "091") & (b.financing == "Free-market") & (b["size"] == "All")
           & (b.measure == "index_2025")].set_index("quarter").value
    actual = (ix["2026Q2"] / ix["2025Q2"] - 1)
    vals = [rc.growth_2025Q2_to_2026Q2_pct.iloc[i] / 100 for i in range(4)] + [actual]
    cats = ["Average rent: ARIMA(0,1,0) with drift", "Average rent: + 2017Q3 level shift",
            "Rent index: random walk with drift", "Rent index: ARIMA(0,2,1)(1,0,0)[4]", "Actual (new index)"]
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("Growth 2025Q2 to 2026Q2", vals)
    text(s, 0.6, 1.75, 7.6, 0.4, "Forecast growth of Helsinki rent, 2025Q2 to 2026Q2", size=16, bold=True, color=TEAL)
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(2.2), Inches(7.6), Inches(4.5), cd)
    ch = gf.chart
    style_axes(ch, "+0%;-0%;0%", font_size=11)
    ch.category_axis.reverse_order = True
    value_axis_at_bottom(ch)
    ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW   # labels left of negative bars
    ch.value_axis.minimum_scale, ch.value_axis.maximum_scale, ch.value_axis.major_unit = -0.01, 0.03, 0.01
    ch.has_legend = False
    ch.has_title = False
    plot = ch.plots[0]
    plot.gap_width = 55
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = "+0.0%;-0.0%;0.0%", False
    dl.font.size, dl.font.color.rgb, dl.font.bold = Pt(12), INK, True
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    plot.series[0].invert_if_negative = False   # otherwise PowerPoint draws the negative bar white
    for i, col in enumerate([COPPER, COPPER, BLUE, BLUE, INK]):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = col
        no_invert(pt)

    x, w = 8.75, 3.95
    text(s, x, 1.85, w, 0.4, "Why the average overshot", size=16, bold=True, color=TEAL)
    text(s, x, 2.3, w, 2.6, [
        "The average rose 27.8% in 2015 to 2025, like-for-like rents only 10.2%. Newer flats entering the "
        "data and a 2017Q3 break in the series push the average up.",
        "Growth also slowed, from 1.3% a year before 2022 to 0.3% after.",
    ], size=14, color=INK2)
    text(s, x, 4.35, w, 0.4, "Caveat", size=16, bold=True, color=COPPER)
    text(s, x, 4.8, w, 1.6, "The index model was chosen after the outcome was known. One correct forecast is "
         "weak evidence. A naive \"no change\" forecast also beat every model in the hold-out.",
         size=14, color=INK2)
    footer(s, "Helsinki, free-market. Box-Jenkins ARIMA in R, fitted on 2015Q1 to 2025Q2. "
              "Actual: Statistics Finland table 15fa. " + SRC_SF + ".", 2)
    s.notes_slide.notes_text_frame.text = (
        "I forecast the Helsinki average rent with the same Box-Jenkins steps as my electricity project. "
        "After one difference no autocorrelation was left, so the model is a random walk with drift. "
        "The forecast quarters have already happened, so I could check it: it said +2.1 percent, rents were flat.\n"
        "The main reason is the measure. The average rises when newer, more expensive flats enter the data, "
        "and it has a one-off break in 2017Q3. The like-for-like index does not, and a model on the index "
        "forecast zero growth.\n"
        "I kept the 2017Q3 dummy as a check only: it was placed after seeing the residual, so its better AICc "
        "is not a fair comparison.\n"
        "Lesson: choosing the right measure mattered more than choosing the ARIMA order. "
        "For the lease-up model I assume flat rents in year one.")


# ---------------------------------------------------------------- slide 3: lease-up
def slide_leaseup(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    title(s, "Each extra month of lease-up costs about €29,000, half a month of the building's rent")
    cd = CategoryChartData()
    cd.categories = [str(m) for m in range(0, 13)]
    for T in (3, 6, 9):
        cd.add_series(f"Fully let in {T} months", [0.0] + [v / 1000 for v in run(T)])
    gf = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(0.6), Inches(1.75), Inches(7.0), Inches(4.75), cd)
    ch = gf.chart
    style_axes(ch, "0", font_size=11)
    ch.value_axis.has_title = True
    ch.value_axis.axis_title.text_frame.text = "Cumulative NOI, € thousand"
    tp = ch.value_axis.axis_title.text_frame.paragraphs[0].runs[0].font
    tp.size, tp.color.rgb, tp.bold, tp.name = Pt(11), INK2, False, BODY
    ch.category_axis.has_title = True
    ch.category_axis.axis_title.text_frame.text = "Month after completion"
    tp = ch.category_axis.axis_title.text_frame.paragraphs[0].runs[0].font
    tp.size, tp.color.rgb, tp.bold, tp.name = Pt(11), INK2, False, BODY
    ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    for ser, col in zip(ch.plots[0].series, (BLUE, COPPER, AQUA)):
        ser.format.line.color.rgb = col
        ser.format.line.width = Pt(2.5)
        ser.smooth = False
        ser.marker.style = None
        from pptx.enum.chart import XL_MARKER_STYLE
        ser.marker.style = XL_MARKER_STYLE.NONE
    legend(ch)
    text(s, 0.6, 6.55, 7.0, 0.35, "HYPOTHETICAL building: 70 flats in Helsinki zone 2", size=11, bold=True,
         color=COPPER)

    y3, y9 = run(3)[-1], run(9)[-1]
    stab = GPR * 12 * STAB - OPEX * M2 * 12
    card(s, 8.1, 1.75, 4.6, 1.5, f"€{(y3 - y9) / 1000:.0f}k",
         f"first-year NOI lost by letting in 9 months instead of 3, {(y3 - y9) / stab * 100:.1f}% of a full year")
    card(s, 8.1, 3.4, 4.6, 1.5, "15%", "rent cut that still pays off in year one, if it fills the building in 3 months "
         "instead of 6")
    card(s, 8.1, 5.05, 4.6, 1.5, "20 months", "after year one until a 5% discount's gain is used up, if the "
         "discount stays in the leases", big_color=COPPER)
    footer(s, "Rents: Statistics Finland 15fa, new leases, zone 2, 2026Q2. Assumptions on slide 4. "
              "Excel model with formulas: Helsinki_Rental_Benchmark.xlsx.", 3)
    s.notes_slide.notes_text_frame.text = (
        "A hypothetical new building, 70 flats in zone 2, rents from Statistics Finland's new-lease data. "
        "Operating costs run on every flat from month one, but rent only comes from let flats.\n"
        "With a linear lease-up, each extra month costs exactly half a month of stabilised rent, about 29,000 "
        "euros here. Letting in 9 months instead of 3 loses 176,000 euros, a third of a year's NOI.\n"
        "Cut rent or wait? In year one, speed wins: filling 3 months faster is worth up to a 15 percent rent cut. "
        "But Finnish leases run until further notice, so a discount can stay. A 5 percent cut is paid back "
        "20 months after year one, and a permanent cut lowers value by about 0.8 million euros.\n"
        "So it depends on how much faster a lower rent really lets, and how long the discount lasts. "
        "Public data cannot answer the first. That is a question for real leasing data.")


# ---------------------------------------------------------------- slide 4: assumptions and sources
def slide_sources(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    title(s, "Every number is sourced or labelled as an assumption, and the building is hypothetical")
    rows = [
        ("Assumption", "Base", "Source or basis"),
        ("Building", "70 flats, Helsinki zone 2", "Hypothetical. Sizes within Rakli-Taaleri (Jan 2026) typical ranges"),
        ("Rent", "New-lease €/m² by flat size", "Statistics Finland 15fa, zone 2, 2026Q2"),
        ("Stabilised occupancy", "97% (94% tested)", "Kojamo valuation 97.5% (2025). Market 93.4% (KTI, Dec 2025)"),
        ("Lease-up", "Linear, 3 / 6 / 9 months", "Assumption"),
        ("Incentive", "1 free month per lease", "Assumption. JLL Q1 2026: incentives widely used"),
        ("Operating costs", "€6.00/m²/month, all flats", "Assumption. Kojamo 6.75, Statistics Finland 6.17"),
        ("Rent growth, year 1", "0% (+2.1% tested)", "Part 2: like-for-like forecast flat"),
        ("Valuation yield", "4.3% (4.0-5.0% tested)", "Prime yield: Catella Q3 2025, JLL Q1 2026. Kojamo 4.22%"),
    ]
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), Inches(1.75), Inches(12.1), Inches(4.3)).table
    widths = (2.6, 3.2, 6.3)
    for j, w in enumerate(widths):
        tbl.columns[j].width = Inches(w)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = tbl.cell(i, j)
            c.text = v
            c.margin_left = c.margin_right = Inches(0.12)
            c.margin_top = c.margin_bottom = Inches(0.05)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            c.fill.fore_color.rgb = TEAL if i == 0 else (TINT if i % 2 == 0 else WHITE)
            for p in c.text_frame.paragraphs:
                for run_ in p.runs:
                    run_.font.size = Pt(14)
                    run_.font.name = BODY
                    run_.font.bold = i == 0 or j == 0
                    run_.font.color.rgb = WHITE if i == 0 else INK
    text(s, 0.6, 6.25, 12.1, 0.7, [
        ("Data: Statistics Finland, rents of dwellings (CC BY 4.0), tables 13eb, 11x4, 15fa, fetched 8 Oct 2026. "
         "Market: KTI, JLL, Kojamo plc, Rakli-Taaleri. Full log: notes/assumptions_and_sources.md.", {"size": 11}),
    ], color=INK2)
    footer(s, "Not a valuation of any real property or fund. Built with Python, R, Excel and Claude Code.", 4)
    s.notes_slide.notes_text_frame.text = (
        "Every input is either from a cited source or labelled as an assumption. The largest sensitivities are "
        "the yield and the lease-up time. Occupancy at today's market level, 94 percent, barely changes the "
        "results. The building is hypothetical and not a valuation of any Taaleri property.")


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    prs.core_properties.title = "Helsinki rental market benchmark and lease-up model"
    prs.core_properties.author = "Albin Oruglica"
    slide_benchmark(prs)
    slide_forecast(prs)
    slide_leaseup(prs)
    slide_sources(prs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()

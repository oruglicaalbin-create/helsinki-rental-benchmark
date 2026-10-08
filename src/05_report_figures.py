"""Make the charts used in the README and slides from the processed data.

Writes PDF (vector) and PNG versions to output/charts/report_*.
Run from the project root after steps 01-04 and the R forecast:
    .venv\\Scripts\\python.exe src\\05_report_figures.py
"""
import importlib.util
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FC = PROC / "forecast"
OUT = ROOT / "output" / "charts"
OUT.mkdir(parents=True, exist_ok=True)

_spec = importlib.util.spec_from_file_location("bm", ROOT / "src" / "02b_benchmark.py")
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, BAR = "#12202b", "#4a5864", "#e3e7ea", "#b8c3cb"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "legend.frameon": False, "figure.dpi": 150, "savefig.bbox": "tight",
})


def save(fig, name):
    fig.savefig(OUT / f"report_{name}.pdf")
    fig.savefig(OUT / f"report_{name}.png", dpi=200)
    plt.close(fig)
    print("saved", name)


# 1. Benchmark dot plot
def fig_benchmark():
    b = pd.read_csv(PROC / "benchmark_postcodes.csv", dtype={"postcode": str})
    order = list(bm.SELECTED)
    labels = []
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    for i, pc in enumerate(order):
        g = b[b.postcode == pc]
        labels.append(f"{pc} {g.area_name.iloc[0].replace(' - ', '-')}")
        for size, col in zip(["Studio", "One-bedroom", "Two-bedroom+"], [BLUE, ORANGE, AQUA]):
            r = g[g["size"] == size].iloc[0]
            if pd.notna(r.rent_latest):
                ax.scatter(r.rent_latest, i, s=34, color=col, alpha=1 if r.n_latest >= 100 else 0.45,
                           edgecolor="white", linewidth=0.8, zorder=3)
    for y in (5.5, 9.5, 13.5, 15.5):
        ax.axhline(y, color=INK2, lw=0.5, ls=":")
    ax.set_yticks(range(len(order)), labels)
    ax.invert_yaxis()
    ax.set_xlim(15, 30)
    ax.set_xlabel("EUR/m2 per month, 2025Q2")
    ax.grid(axis="y", visible=False)
    from matplotlib.lines import Line2D
    proxies = [Line2D([], [], marker="o", ls="", color=c, markersize=6, label=lab)
               for lab, c in [("Studio", BLUE), ("One-bedroom", ORANGE), ("Two-bedroom+", AQUA)]]
    ax.legend(handles=proxies, loc="lower left", ncol=3, bbox_to_anchor=(0, 1.0))
    save(fig, "benchmark")


# 2. Zone index
def fig_zones():
    a = pd.read_csv(PROC / "benchmark_areas.csv", dtype={"area_code": str})
    a = a[(a["size"] == "All") & (a.quarter <= "2025Q2")]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for code, lab, col in [("091-1", "Zone 1", BLUE), ("091-2", "Zone 2", ORANGE),
                           ("091-3", "Zone 3", AQUA), ("091-4", "Zone 4", YELLOW)]:
        s = a[a.area_code == code].sort_values("quarter")
        ax.plot(range(len(s)), s.index_2015, color=col, lw=1.8, label=lab)
        ax.text(len(s) - 0.5, s.index_2015.iloc[-1], f" {lab} {s.index_2015.iloc[-1]:.1f}", va="center",
                fontsize=7.5, color=INK2)
    q = sorted(a.quarter.unique())
    ax.set_xticks(range(0, len(q), 4), [x[:4] for x in q[::4]])
    ax.axhline(100, color=INK2, lw=0.6, ls="--")
    ax.set_ylabel("Index, 2015 = 100")
    ax.set_xlim(-1, len(q) + 6)
    save(fig, "zones")


# 3. Method break
def fig_break():
    d = pd.read_csv(PROC / "diag_postcode_median_qoq.csv")
    d.columns = ["q", "v"]
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    cols = [ORANGE if q == "2025Q4" else BAR for q in d.q]
    ax.bar(range(len(d)), d.v, color=cols, width=0.8)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks([i for i, q in enumerate(d.q) if q.endswith("Q1")][::2],
                  [q[:4] for q in d.q if q.endswith("Q1")][::2])
    ax.set_ylabel("Median q/q change, %")
    ax.annotate("2025Q4: -1.8%", (len(d) - 1, d.v.iloc[-1]), xytext=(len(d) - 12, -1.6),
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6), fontsize=8)
    save(fig, "break")


# 4. Forecast
def fig_forecast():
    s = pd.read_csv(FC / "series_fitted.csv")
    f = pd.read_csv(FC / "forecast_4q.csv")
    b = pd.read_csv(PROC / "area_rents_15fa_2025_latest.csv", dtype={"area_code": str})
    ix = b[(b.area_code == "091") & (b.financing == "Free-market") & (b["size"] == "All")
           & (b.measure == "index_2025") & (b.quarter >= "2025Q2")].sort_values("quarter")
    n = len(s)
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ax.plot(range(n), s.actual, color=BLUE, lw=1.8, label="Actual (old table, 11x4)")
    xf = [n - 1] + list(range(n, n + 4))
    last = s.actual.iloc[-1]
    ax.fill_between(xf, [last] + list(f.lo95), [last] + list(f.hi95), color=ORANGE, alpha=0.15, lw=0,
                    label="95% interval")
    ax.fill_between(xf, [last] + list(f.lo80), [last] + list(f.hi80), color=ORANGE, alpha=0.3, lw=0,
                    label="80% interval")
    ax.plot(xf, [last] + list(f.forecast), color=ORANGE, lw=1.8, ls="--", label="Forecast")
    imp = last * ix.value.values / ix.value.values[0]
    ax.scatter(range(n, n + 4), imp[1:], color=INK, s=18, zorder=4, label="Actual growth (new table 15fa)")
    q = list(s.quarter) + list(f.quarter)
    ax.set_xticks(range(0, len(q), 4), [x[:4] for x in q[::4]])
    ax.set_ylabel("EUR/m2 per month")
    ax.legend(loc="upper left", fontsize=7.5)
    save(fig, "forecast")


# 4b. Index forecast (like-for-like), compared with the new table's index growth
def fig_forecast_index():
    a = pd.read_csv(PROC / "area_rents_11x4_2015_2025.csv", dtype={"area_code": str})
    s = a[(a.area_code == "091") & (a.financing == "Free-market") & (a["size"] == "All")
          & (a.measure == "index_2015") & (a.quarter <= "2025Q2")].sort_values("quarter")
    f = pd.read_csv(FC / "index_forecast_4q.csv")
    b = pd.read_csv(PROC / "area_rents_15fa_2025_latest.csv", dtype={"area_code": str})
    ix = b[(b.area_code == "091") & (b.financing == "Free-market") & (b["size"] == "All")
           & (b.measure == "index_2025") & (b.quarter >= "2025Q2")].sort_values("quarter")
    n = len(s)
    last = s.value.iloc[-1]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.plot(range(n), s.value, color=BLUE, lw=1.8, label="Rent index, old table (2015 = 100)")
    xf = [n - 1] + list(range(n, n + 4))
    ax.fill_between(xf, [last] + list(f.lo95), [last] + list(f.hi95), color=ORANGE, alpha=0.15, lw=0,
                    label="95% interval")
    ax.plot(xf, [last] + list(f.forecast), color=ORANGE, lw=1.8, ls="--", label="Forecast, ARIMA(0,2,1)(1,0,0)[4]")
    imp = last * ix.value.values / ix.value.values[0]
    ax.scatter(range(n, n + 4), imp[1:], color=INK, s=18, zorder=4, label="Growth of new index (2025 = 100)")
    q = list(s.quarter) + list(f.quarter)
    ax.set_xticks(range(0, len(q), 4), [x[:4] for x in q[::4]])
    ax.set_ylabel("Index, 2015 = 100")
    ax.legend(loc="upper left", fontsize=7.5)
    save(fig, "forecast_index")


# 5. ACF panels
def fig_acf():
    a = pd.read_csv(FC / "acf_pacf_diff.csv")
    r = pd.read_csv(FC / "residual_acf.csv")
    fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.3), sharey=True)
    for ax, (vals, ci, title) in zip(axes, [(a.acf, a.ci95[0], "ACF, first difference"),
                                            (a.pacf, a.ci95[0], "PACF, first difference"),
                                            (r.acf, r.ci95[0], "ACF, model residuals")]):
        ax.bar(a.lag, vals, color=BLUE, width=0.45)
        for c in (ci, -ci):
            ax.axhline(c, color=ORANGE, ls="--", lw=0.9)
        ax.axhline(0, color=INK2, lw=0.6)
        ax.set_title(title, fontsize=8.5, color=INK)
        ax.set_xticks([1, 4, 8, 12])
        ax.set_ylim(-0.5, 0.5)
        ax.set_xlabel("Lag (quarters)")
    save(fig, "acf")


# 6. Validation
def fig_validation():
    s = pd.read_csv(FC / "series_fitted.csv")
    v = pd.read_csv(FC / "validation_holdout.csv")
    s = s[s.quarter >= "2022Q1"].reset_index(drop=True)
    n = len(s)
    c0 = n - 5
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    ax.axvspan(c0, n - 1, color="#e2eef3", alpha=0.8, lw=0)
    ax.text(c0 + 0.1, 23.55, "held out", fontsize=7.5, color=INK2)
    xs = [c0] + list(range(c0 + 1, n))
    base = s.actual.iloc[c0]
    ax.fill_between(xs, [base] + list(v.lo95), [base] + list(v.hi95), color=ORANGE, alpha=0.15, lw=0,
                    label="Model 95% interval")
    ax.plot(range(n), s.actual, color=BLUE, lw=1.8, marker="o", ms=3, label="Actual")
    ax.plot(xs, [base] + list(v.arima), color=ORANGE, lw=1.6, ls="--", marker="o", ms=3,
            label="Model (MAPE 0.96%)")
    ax.plot(xs, [base] + list(v.naive), color=AQUA, lw=1.6, ls=":", marker="o", ms=3,
            label="Naive, last value (MAPE 0.46%)")
    ax.set_xticks(range(0, n, 2), s.quarter[::2], fontsize=7.5)
    ax.set_ylim(21.4, 23.8)
    ax.set_ylabel("EUR/m2 per month")
    ax.legend(loc="upper left", fontsize=7.5)
    save(fig, "validation")


# 7-8. Lease-up model (same formulas as the Excel sheet)
FLATS = [(28, 26, 26.33), (28, 40, 21.65), (14, 60, 20.45)]
UNITS = sum(f[0] for f in FLATS)
M2 = sum(f[0] * f[1] for f in FLATS)
GPR = sum(n * m * r for n, m, r in FLATS)
STAB, OPEX, FREE = 0.97, 6.0, 1


def run(T, months=12, adj=0.0):
    rows, prev, cum = [], 0.0, 0.0
    g = GPR * (1 + adj)
    for m in range(1, months + 1):
        occ = STAB * min(1, m / T)
        noi = g * occ - (occ - prev) * g * FREE - OPEX * M2
        cum += noi
        rows.append((m, occ, noi, cum))
        prev = occ
    return pd.DataFrame(rows, columns=["m", "occ", "noi", "cum"])


def fig_leaseup():
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7))
    for T, col in [(3, BLUE), (6, ORANGE), (9, AQUA)]:
        d = run(T)
        axes[0].plot([0] + list(d.m), [0] + list(d.occ * 100), color=col, lw=1.8, label=f"{T} months")
        axes[1].plot([0] + list(d.m), [0] + list(d.cum / 1000), color=col, lw=1.8, label=f"{T} months")
        axes[1].text(12.2, d.cum.iloc[-1] / 1000, f"{d.cum.iloc[-1] / 1000:.0f}k", va="center", fontsize=7.5)
    axes[0].set_ylim(0, 100)
    axes[0].set_ylabel("Occupancy, %")
    axes[1].set_ylabel("Cumulative NOI, EUR thousand")
    axes[1].axhline(0, color=INK2, lw=0.6)
    for ax in axes:
        ax.set_xlabel("Month after completion")
        ax.set_xticks([0, 3, 6, 9, 12])
    axes[0].legend(loc="lower right", fontsize=7.5)
    save(fig, "leaseup")


def fig_payback():
    cut = 0.05
    fast, slow = run(3, 48, -cut), run(6, 48, 0)
    diff = fast.cum - slow.cum
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.axvspan(0, 12, color="#e2eef3", alpha=0.8, lw=0)
    ax.text(0.4, diff.max() / 1000 * 0.92, "year 1", fontsize=7.5, color=INK2)
    ax.plot([0] + list(fast.m), [0] + list(diff / 1000), color=BLUE, lw=1.8)
    ax.axhline(0, color=INK2, lw=0.6)
    cross = int(fast.m[(diff <= 0) & (fast.m > 12)].iloc[0])
    ax.axvline(cross, color=ORANGE, ls="--", lw=1)
    ax.text(cross + 0.6, diff.max() / 1000 * 0.6, f"gain used up\nin month {cross}", fontsize=7.5, color=INK2)
    ax.set_xlabel("Month after completion")
    ax.set_ylabel("Extra cumulative NOI, EUR k")
    ax.set_xticks([0, 12, 24, 36, 48])
    save(fig, "payback")


if __name__ == "__main__":
    fig_benchmark()
    fig_zones()
    fig_break()
    fig_forecast()
    fig_forecast_index()
    fig_acf()
    fig_validation()
    fig_leaseup()
    fig_payback()

# Assumptions and sources

Running log. Every number in the outputs either comes from a source listed here or is an assumption listed here.

## Data sources

| What | Source | URL | Checked |
|---|---|---|---|
| Free-market average rent EUR/m2 by postal code, 2015Q1-2025Q4 (table 13eb, archived) | Statistics Finland, rents of dwellings, CC BY 4.0 | https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px | 2026-10-08 |
| Rent index 2015=100 and average EUR/m2 by area, 2015Q1-2025Q4 (table 11x4, archived) | Statistics Finland, rents of dwellings, CC BY 4.0 | https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_11x4_2025q4.px | 2026-10-08 |
| Rent index 2025=100 and average EUR/m2 incl. new tenancies, 2025Q1-2026Q2 (table 15fa, current) | Statistics Finland, rents of dwellings, CC BY 4.0 | https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin/asvu/15fa.px | 2026-10-08 |
| Statistics documentation | Statistics Finland | https://stat.fi/tilasto/dokumentaatio/asvu | 2026-10-08 |

Raw API responses are in `data/raw/` with the fetch date in the file name. Table 13eb and 11x4 were last updated 2026-01-15, table 15fa on 2026-07-16 (from the API response).

## Data findings that shape the method

### 1. The old and new tables are not comparable in EUR/m2
The brief assumed EUR/m2 could be compared across the archived tables and the current table. It cannot. The table notes say:

- **11x4 and 13eb (archived):** average rents are weighted **geometric** means. A "new tenancy" is a lease that started within six months of the end of the reference period.
- **15fa (current):** average rents are weighted **arithmetic** means. A "new tenancy" is a lease that started in the reference period **or a rent that appeared in asking-rent data** (listings). The area classification is also new (base year 2025) and "ARA" is now "state-supported".

The 2025 overlap shows the gap. Free-market, all flat sizes, Helsinki:

| Quarter | 11x4 EUR/m2 | 15fa EUR/m2 | 11x4 new tenancies | 15fa new tenancies |
|---|---|---|---|---|
| 2025Q1 | 22.31 | 21.36 | 22.39 | 21.87 |
| 2025Q2 | 22.43 | 21.37 | 22.26 | 22.04 |
| 2025Q3 | 22.67 | 21.34 | 22.22 | 21.99 |
| 2025Q4 | 21.42 | 21.20 | 21.75 | 21.80 |

**Decision:** never splice EUR/m2 or the index across the two tables. Long series (benchmark changes, forecast) use the archived tables only. The current level (lease-up model rent anchor) uses 15fa only.

### 2. 2025Q3 and 2025Q4 in the archived tables show a level shift
- Helsinki free-market EUR/m2 in 11x4 falls from 22.67 (2025Q3) to 21.42 (2025Q4), -5.5% in one quarter. 15fa shows the same quarter as flat (index 99.9 to 100.0).
- Across all capital-region postcodes, the median quarter-on-quarter change in 2025Q4 is -1.8%. For one-bedroom flats it is -8.2% and for two-bedroom+ -6.5%. Normal quarters are between -0.7% and +1.9% (all sizes).
- In 2025Q3 the Helsinki observation count jumps from 30,861 to 38,256, while the number of one-bedroom observations published at postcode level halves (more cells masked).
- Even the quality-adjusted index falls 1.3% y/y in 2025Q4, which 15fa does not show.

This is consistent with the archived tables' last two quarters being produced during the switch to the new data and method. It is not a market crash.

**Decision:** the benchmark quarter is **2025Q2**, the last quarter on the old, consistent basis. Year-on-year change is 2025Q2 vs 2024Q2, five-year change 2025Q2 vs 2020Q2. The reported 2025Q4 value is kept in `benchmark_postcodes.csv` as a separate column. The quarter can be changed in the Excel summary (yellow cell).

### 3. Statistics Finland masks cells
The 13eb table note says: data is masked if there are fewer than 20 observations, or if the share of rental housing companies in the postal code area is large. Many two-bedroom+ cells and some whole areas (for example Itä-Pasila one-bedroom, Kalasatama) are masked. Areas dominated by large institutional landlords, which is where new build-to-rent buildings tend to be, are the most likely to be hidden. This is a real limitation of public postcode data.

### 4. Average EUR/m2 is not quality-adjusted
The table notes say average rents do not account for quality differences between dwellings and "are therefore not suitable for examining rent changes". The postcode y/y and 5-year changes can reflect a different mix of flats, not only rent growth. Example: Kamppi-Ruoholahti two-bedroom+ shows +40% over five years on 43 observations, which is likely a mix effect. The quality-adjusted measure is the rent index (Area trend sheet), but it exists only at zone level, not postcode level.

## Benchmark choices

| Choice | Value | Reason |
|---|---|---|
| Financing type | Free-market (vapaarahoitteinen) only | Build-to-rent funds let at market rent. ARA flats have regulated, cost-based rents. |
| Minimum observations | 30 per cell, in every quarter a figure uses | Statistics Finland already masks under 20. 30 adds a margin. Editable in the Excel summary. |
| Benchmark quarter | 2025Q2 | See finding 2. |
| Changes | y/y vs 2024Q2, 5-year vs 2020Q2, simple % change on EUR/m2 | Same quarter a year earlier removes seasonality. |
| Areas | 14 Helsinki + 2 Espoo + 2 Vantaa postal codes (list below) | Chosen for data coverage and a spread from the inner city to the suburbs and newer development areas. |

Selected postal areas:

- **Helsinki inner city:** 00180 Kamppi-Ruoholahti, 00250 Taka-Töölö, 00530 Kallio, 00500 Sörnäinen, 00200 Lauttasaari, 00510 Etu-Vallila-Alppila
- **Helsinki middle ring:** 00520 Itä-Pasila, 00320 Etelä-Haaga, 00640 Oulunkylä-Patola, 00840 Laajasalo
- **Helsinki outer suburbs:** 00420 Kannelmäki, 00920 Myllypuro, 00940 Kontula-Vesala, 00970 Mellunmäki
- **Espoo:** 02650 Pohjois-Leppävaara, 02600 Etelä-Leppävaara
- **Vantaa:** 01300 Tikkurila, 01700 Kivistö

Not available: Kalasatama does not appear in the capital-region postcode data. Jätkäsaari (00220) appears in only 3 cells. Itä-Pasila, Etelä-Leppävaara and Tikkurila have studio data only.

Helsinki 1-4 are Statistics Finland's price zones, based on old-dwelling price levels and location by postal code. 1 is the most expensive.

## Workbook checks
- `04_build_model.py` writes formulas, not values, in the Benchmark summary (SUMIFS over the Benchmark data table). The file was recalculated in Excel on 2026-10-08 and all 54 rent, y/y and 5-year cells matched the Python results in `benchmark_postcodes.csv`, with 0 errors.

## Forecast (Part 2), `src/03_forecast.R`

| Choice | Value | Reason |
|---|---|---|
| Series | Helsinki (091), free-market, all flat sizes, average EUR/m2, table 11x4 | Matches the benchmark unit. |
| Period | 2015Q1-2025Q2, 42 quarters | 2025Q3-Q4 left out (finding 2). Not extended with 15fa (finding 1). |
| Software | R 4.6.1, forecast 9.0.2, tseries | Matches Albin's CV and the electricity project. |
| Model selection | Grid over ARIMA(p,1,q)(P,0,Q)[4], p,q 0-2, P,Q 0-1, with and without drift, 72 models, ML estimation, lowest AICc | Box-Jenkins. d = 1 from ADF and KPSS. No seasonal difference (nsdiffs = 0). |
| Validation | Hold out 2024Q3-2025Q2, fit on 2015Q1-2024Q2, MAPE vs naive, drift and seasonal naive benchmarks | Ex-post validation as in the electricity project. |

Results (run 2026-10-08):
- Stationarity: level has a unit root (ADF p = 0.91, KPSS p < 0.01). First difference is stationary (ADF p = 0.018, KPSS p = 0.073).
- ACF and PACF of the first difference: no lag outside the 95% band (largest |ACF| = 0.24 at lag 3, band 0.31).
- Chosen model: **ARIMA(0,1,0) with drift**, a random walk with drift. Drift = 0.119 EUR/m2 per quarter (s.e. 0.033). auto.arima picks the same model.
- Residuals: Ljung-Box p = 0.56 (8 lags) and 0.58 (12 lags), so no autocorrelation left. Not normal (Shapiro-Wilk p < 0.001), mainly because of the 2017Q3 jump (+1.00 EUR/m2 in a quarter while the quality-adjusted index rose 0.2%), a sample-mix effect. Bootstrapped intervals were computed as a check and are close to the normal ones.
- Validation MAPE: model 0.96%, naive 0.46%, seasonal naive 0.85%. **The naive forecast beats the model**, because growth slowed in the hold-out period. All four actuals were inside the model's 95% interval.
- Forecast 2025Q3-2026Q2: 22.55, 22.67, 22.79, 22.91 EUR/m2. 2026Q2 95% interval 22.07-23.74. Implied growth +2.1% over the year.
- What happened: the new table (15fa) shows the Helsinki free-market index at -0.2% from 2025Q2 to 2026Q2, and average EUR/m2 at -0.1%. The outcome is inside the 95% interval but well below the point forecast.
- Growth slowed: average quarterly growth was 0.77% in 2015Q1-2021Q4 and 0.27% in 2022Q1-2025Q2. Drift estimated on 2022Q1-2025Q2 only is 0.071 EUR/m2 per quarter.
- For comparison, auto.arima on the quality-adjusted index picks ARIMA(0,2,1)(1,0,0)[4]. A second difference means the trend itself is changing, which matches the slowdown.

**Conclusion used in Part 3:** a model on past averages extrapolates the 2015-2021 growth. For a first-year income model, the base case assumes **no rent growth** during the first year, and the forecast drift is an upside sensitivity only.

## Lease-up model (Part 3) sources, checked 2026-10-08

| Figure | Value | Source | Notes |
|---|---|---|---|
| Typical flat sizes in Finnish rental buildings | Studio 23-28 m2, one-bedroom 35-45 m2, two-bedroom 55-70 m2 | Rakli-Taaleri joint paper "Residential Market in Finland", January 2026, p. 5. https://taaleri.com/wp-content/uploads/2026/01/Taaleri-Real-Estate-x-Rakli_Residential-Market-in-Finland.pdf | Same paper: "In private rental buildings, most apartments are small studios or one-bedroom apartments." |
| Residential prime yield, Helsinki metropolitan area | 4.3%, Q3 2025 | Rakli-Taaleri paper, p. 3, footnote 6 attributes it to **Catella** (not KTI) | |
| Residential prime yield, Helsinki | 4.30%, Q1 2026 | JLL, Finland Residential Market Dynamics Q1 2026, published 12 May 2026. https://www.jll.com/en-us/insights/market-dynamics/finland-residential | JLL also says "incentives remain widely used". |
| Valuation yield requirement, capital region | 4.22% (cash flow, weighted), exit cap rate 4.37%, 31 Dec 2025 | Kojamo plc (Lumo), Financial Statements Release 2025, p. 32, "Average valuation parameters". https://yritys.lumo.fi/wp-content/uploads/2026/02/financial-statements-release-2025.pdf | Yield requirement for net rental income. Kojamo's portfolio is mostly older than a new build. |
| Market rent in Kojamo's valuation, capital region | 20.52 EUR/m2/month | Kojamo, same table | Sense check for the Statistics Finland rents. |
| Maintenance, repairs and modernisation in Kojamo's valuation, capital region | 6.75 EUR/m2/month | Kojamo, same table | Includes modernisation provisions, which Kojamo sets at only 0.25 EUR/m2/month for buildings 0-10 years old (p. 33). |
| 10-year average financial occupancy in Kojamo's valuation, capital region | 97.5% | Kojamo, same table | Long-run stabilised assumption. |
| Kojamo actual financial occupancy 2025 | 94.8% (2024: 91.5%) | Kojamo, same release, p. 1 | |
| Residential occupancy, Helsinki metropolitan area | 93.8% Q3 2025 (91.3% a year earlier) | Rakli-Taaleri paper, p. 3, footnote 3: KTI | |
| Residential occupancy, Helsinki metropolitan area | 93.4% December 2025. Rents -0.9% in 2025 | KTI, The Finnish Property Market 2026 flyer, p. 3. https://kti.fi/wp-content/uploads/2026/03/The-Finnish-Property-Market-2026-Flyer.pdf | KTI shows the prime yield only as a chart, no exact figure. |
| Housing company running costs (hoitokulut), apartment blocks | 6.17 EUR/m2/month in 2025, all Finland, all building ages | Statistics Finland, Asunto-osakeyhtiöiden talous 2025, published 16.6.2026. https://stat.fi/fi/julkaisu/cmfdwvwdn4lbd07w62s8blgig | Owner-occupied housing companies, average age much older than a new build. |
| New-tenancy rent, Helsinki zone 2, 2026Q2 | Studio 26.33, one-bedroom 21.65, two-bedroom+ 20.45 EUR/m2/month | Statistics Finland table 15fa | Rent anchor. "Kaksiot" (two rooms) = one-bedroom, "Kolmiot+" = two-bedroom+. |

## Lease-up model assumptions

| Assumption | Base value | Range tested | Basis |
|---|---|---|---|
| Location | Helsinki price zone 2 | | Albin's choice, 2026-10-08 |
| Flats | 70: 28 studios x 26 m2, 28 one-bedroom x 40 m2, 14 two-bedroom x 60 m2 = 2,688 m2 | | Assumption. Sizes inside the Rakli-Taaleri ranges, mix weighted to small flats as the paper describes |
| Rent | 15fa zone 2 new-tenancy EUR/m2 by flat size, no new-build premium | -10% to +5% | Statistics Finland. A new building may get a premium, but no public source measures it, so 0% |
| Rent growth in year one | 0% | +2.1% (ARIMA drift) | Part 2 finding, Albin's choice |
| Stabilised occupancy | 97% | input | Kojamo's long-run 97.5% valuation assumption, rounded down. Current market occupancy is lower (93.4%, KTI) |
| Lease-up shape | Linear from 0 to stabilised occupancy over 3, 6 or 9 months | 3, 6, 9, 12 months | Assumption. Simplest shape to explain. Leases start at the start of a month |
| Leasing incentive | 1 month free rent per lease signed during lease-up, switchable | 0 or 1 | Assumption. JLL notes incentives "remain widely used" but gives no size |
| Operating costs | 6.00 EUR/m2/month on all flats, let or vacant | 5.00 to 7.00 | Assumption. Below Kojamo's 6.75 (older stock incl. repairs) and Statistics Finland's 6.17 (housing companies, all ages), because a new building has few repairs |
| Valuation yield | 4.3% | 4.0% to 5.0% | Prime yield 4.3% (Catella Q3 2025, JLL Q1 2026). Kojamo capital region 4.22% |
| Tenant turnover in year one | Not modelled | | Stabilised occupancy below 100% stands in for normal vacancy |

## Lease-up model results (base case, recalculated in Excel 2026-10-08)

Every model cell was recalculated in Excel and matched an independent Python calculation. An input-change test (operating costs 7.00, scenario C 12 months) updated all outputs correctly.

| Output | Value |
|---|---|
| Lettable area | 2,688 m2, average market rent 22.54 EUR/m2/month |
| Rent if all 70 flats were let | 60,594 EUR/month, 727,131 EUR/year |
| Stabilised NOI (97% occupancy, opex 6.00) | 511,781 EUR/year, NOI margin 72.6% |
| Indicative value at 4.3% yield | 11.90 M EUR, 4,428 EUR/m2. Range 10.24 M (5.0%) to 12.79 M (4.0%) |
| Year-1 NOI, 3 / 6 / 9 months | 394,228 / 306,064 / 217,899 EUR (77.0% / 59.8% / 42.6% of stabilised NOI) |
| **NOI lost by letting in 9 months instead of 3** | **176,329 EUR = 34.5% of stabilised annual NOI** |
| Cost per extra month of lease-up | about 29,400 EUR |
| Breakeven rent cut, year 1 only | 3 instead of 6 months: 15.0%. 3 instead of 9: 30.0%. 6 instead of 9: 17.6% |
| Example: cut rent 5% to let in 3 instead of 6 months | +58,776 EUR in year 1. Costs 2,939 EUR/month after that, so the gain is used up 20 months after year 1. If the cut were permanent, value falls by 0.82 M EUR (-6.9%) |

What the numbers say: in year one, letting speed matters more than rent level. Filling 3 months faster is worth up to a 15% rent cut. But the cut only pays off if it is temporary. A discount that stays in the lease for more than about 20 months after year one costs more than it gained, and a permanent cut lowers value far more than the year-one gain. So the answer depends on how long the discount lasts and whether a cut actually speeds up letting. **The model cannot tell how much faster a lower rent fills a building.** No public data was found on that, so the model shows how much faster letting would need to be to justify a cut, not whether it would be.

## Review corrections (2026-10-08)

An external review of the first write-up raised six points. Checked against the data:

- **Growth measure.** The "3.1%/yr before 2022, 1.1%/yr after" figures were from the average EUR/m2, which includes mix effects. Like-for-like (index, 11x4, Helsinki free-market): **1.29%/yr 2015Q1-2021Q4, 0.31%/yr 2021Q4-2025Q2**. Average 2015Q1-2025Q2 +27.8% vs index +10.2%. Use the index for any statement about rent growth.
- **2017Q3 jump.** Drift without it: 0.097 (vs 0.119). Model with a 2017Q3 level-shift dummy forecasts +1.73% to 2026Q2 (95% -1.09 to +4.55), hold-out MAPE 0.69%.
- **Problem 1 cause.** AM >= GM for the same data, so the mean type cannot explain why 15fa is lower. Statistics Finland change notice 28.4.2026 (https://stat.fi/fi/dokumentaatio/muutoksia-tilastoissa/cmob4bsxkz38k07vx3h7pehqw): water fees no longer counted as rent (Eurostat recommendation), index weights updated to current building stock, data checks updated. Documentation (https://stat.fi/fi/tilasto/dokumentaatio/asvu): data now Kela housing allowance register + rental companies + rental listing site asking rents. Correction to the 2025Q3 release issued 16.1.2026 (https://stat.fi/fi/dokumentaatio/muutoksia-tilastoissa/cmkghl8lzhszu07ulejy7ae7c). Size of each effect not published.
- **Like-for-like forecast** (`data/processed/forecast/review_checks.csv`, `index_model_diagnostics.csv`): Helsinki index needs d = 2 (KPSS p = 0.012 and ADF p = 0.40 on the first difference). auto.arima: ARIMA(0,2,1)(1,0,0)[4], ma1 -0.88, sar1 0.44. Ljung-Box p 0.29 / 0.13, Shapiro p 0.052. Forecast 2025Q2-2026Q2 +0.02% (95% -0.96 to +1.01). Actual new index -0.2%. Index random walk with drift: +0.91% (95% -0.02 to +1.83). Hold-out MAPE: ARIMA 0.34%, naive 0.02%. Model chosen after the outcome was known.
- **Occupancy.** 94% case: stabilised NOI 489,967, value 11.39 M, NOI lost 9 vs 3 months 170,876 (34.9%), 28,479 per extra month.
- **Rent growth +2.1%** in year one adds 6,627 / 6,168 / 5,401 EUR (3/6/9 months), about 2%. The workbook's growth factor applies to all let flats, which slightly overstates in-year growth.
- **Payback formula 1.5/r - 10** holds only for 3 instead of 6 months and assumes the speed-up happens. Not a general finding.

## Walkthrough and Stage 5 (2026-10-09)

Albin replayed the project step by step (`C:\Users\orugl\helsinki-rental-walkthrough`, `DECISIONS.md`). All 20 decisions kept the original choice. Five issues were found and handled:

- **N1** `02b_benchmark.py`: a missing 1-year change now gets a flag (Kontula studios: "1y change: below 30 obs or masked in 2024Q2").
- **N2** Residual sd 0.252 (2015Q2-2021Q4) vs 0.082 (2022Q1-2025Q2), F = 9.43, p = 0.0001. With the 2017Q3 shift removed: 0.186 vs 0.082, p = 0.003. Model on 2022Q1-2025Q2 only: drift 0.071, +1.26% to 2026Q2, 95% -0.01 to +2.54%. Actual -0.1% falls just outside. Saved in `data/processed/forecast/variance_break.csv`.
- **N3** The 2017Q3 jump is **not** a mix effect (correcting the review note above): the average jumps in every area (whole country +3.7%, Helsinki +5.3%, zone 1 +8.4%, Helsinki one-bedroom +7.7%), the index moves -0.3% to +0.5%, and observation counts fall (Helsinki -2.2%, zone 1 one-bedroom -11.4%). Statistics Finland's 2017Q3 quality description (https://stat.fi/til/asvu/2017/03/asvu_2017_03_2017-11-16_laa_001_fi.html): quarterly average rents were re-anchored yearly to the annual statistic's averages. 2015-2018 were later recalculated. Described as a break in the average series, cause unconfirmed.
- **N4 / D10** The level-shift model has AICc -28.53 vs -7.19. It is **not** used as the main model: AICc compares fairly only when candidates are fixed before looking at the data, and the dummy was placed on the largest residual after seeing it. Kept as a check (+1.73%, MAPE 0.69%). The script keeps the shift column in the grid with `shift = FALSE` and a comment.
- **N5** Index hold-out now re-estimated on the training quarters: MAPE 0.36% (was 0.34%). Same model chosen.

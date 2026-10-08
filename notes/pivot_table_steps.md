# Build the pivot table yourself (about 5 minutes)

openpyxl cannot create real Excel pivot tables, so the workbook has a formula-based summary instead. These steps build the same view as a real pivot table, using the `RentData` table on the **Benchmark data** sheet.

1. Open `output/Helsinki_Rental_Benchmark.xlsx` and go to **Benchmark data**.
2. Click any cell inside the table (for example A2).
3. **Insert > PivotTable > From Table/Range.** The range should already say `RentData`. Choose **New Worksheet** and click **OK**.
4. Rename the new sheet `Benchmark pivot` (double-click the tab).
5. In the PivotTable Fields pane, drag:
   - `in_benchmark` to **Filters**
   - `quarter` to **Filters**
   - `area_label` to **Rows**
   - `size` to **Columns**
   - `rent_eur_m2` to **Values**
6. In the Values box, click **Sum of rent_eur_m2 > Value Field Settings**, choose **Average** and click **Number Format > Number, 2 decimals**. Each area, size and quarter has only one row, so the average is just that value. Average is still the safer choice if you later remove the quarter filter.
7. Set the filters at the top of the pivot: `in_benchmark` = **Yes**, `quarter` = **2025Q2**.
8. Optional: drag `n_obs` into **Values** as well (Sum), to see the sample size next to each rent.
9. Optional: with the pivot selected, **PivotTable Analyze > PivotChart > Bar** gives a chart that updates with the filters.

**Check:** Kallio studio should show 27.13 and Kamppi-Ruoholahti one-bedroom 25.10, the same as in **Benchmark summary**.

Things to try in an interview demo:
- Change the `quarter` filter to 2020Q2 to see five years ago.
- Move `quarter` to Rows and `area_label` to Filters to get the time series for one area.
- Set `in_benchmark` to All to see all 115 capital-region postcodes.

Note: the pivot does not apply the 30-observation rule. The summary sheet does. If you show the pivot, also show `n_obs`.

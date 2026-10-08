# Rent forecast for Helsinki, free-market average EUR/m2, Box-Jenkins ARIMA.
#
# Series: Statistics Finland table 11x4, Helsinki (091), free-market, all flat sizes,
# 2015Q1-2025Q2 (42 quarters). 2025Q3-Q4 are left out because of the method shift
# documented in notes/assumptions_and_sources.md.
#
# Steps: 1 plot, 2 stationarity, 3 ACF/PACF, 4 candidate models, 5 compare AICc,
# 6 residual diagnostics, 7 ex-post validation (hold out last 4 quarters, MAPE),
# then a 4-quarter forecast with a 95% interval.
#
# Run from the project root:
#   "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" src\03_forecast.R

suppressPackageStartupMessages({
  library(forecast)
  library(tseries)
})
set.seed(1)

root <- normalizePath(".")
out_dir <- file.path(root, "data", "processed", "forecast")
chart_dir <- file.path(root, "output", "charts")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(chart_dir, showWarnings = FALSE, recursive = TRUE)

LAST_Q <- "2025Q2"
H <- 4

# ------------------------------------------------------------------ data
a <- read.csv(file.path(root, "data", "processed", "area_rents_11x4_2015_2025.csv"),
              colClasses = c(area_code = "character"), encoding = "UTF-8")
s <- a[a$area_code == "091" & a$financing == "Free-market" & a$size == "All" &
         a$measure == "rent_eur_m2" & a$quarter <= LAST_Q, ]
s <- s[order(s$quarter), ]
y <- ts(s$value, start = c(2015, 1), frequency = 4)
quarters <- s$quarter
cat("Series:", length(y), "quarters,", quarters[1], "to", tail(quarters, 1), "\n")

qlab <- function(t) paste0(floor(t + 1e-9), "Q", round((t - floor(t + 1e-9)) * 4) + 1)

png_open <- function(name, w = 1600, h = 900) {
  png(file.path(chart_dir, name), width = w, height = h, res = 200)
  par(mar = c(4, 4.5, 2.5, 1), family = "sans", las = 1, cex.axis = 0.85)
}

# ------------------------------------------------------------------ 1 plot
png_open("fc_01_series.png")
plot(y, type = "o", pch = 16, cex = 0.6, col = "#2a78d6", lwd = 2,
     ylab = "EUR/m2 per month", xlab = "", main = "Helsinki free-market average rent, 2015Q1-2025Q2")
grid(col = "#e8ecef", lty = 1)
dev.off()

# ------------------------------------------------------------------ 2 stationarity
adf_level <- adf.test(y)
kpss_level <- kpss.test(y, null = "Level")
kpss_trend <- kpss.test(y, null = "Trend")
dy <- diff(y)
adf_diff <- adf.test(dy)
kpss_diff <- kpss.test(dy, null = "Level")
nd <- ndiffs(y, test = "kpss")
nsd <- nsdiffs(y)
stat <- data.frame(
  test = c("ADF, level", "KPSS level-stationary, level", "KPSS trend-stationary, level",
           "ADF, first difference", "KPSS level-stationary, first difference"),
  null_hypothesis = c("unit root", "stationary", "trend-stationary", "unit root", "stationary"),
  statistic = round(c(adf_level$statistic, kpss_level$statistic, kpss_trend$statistic,
                      adf_diff$statistic, kpss_diff$statistic), 3),
  p_value = round(c(adf_level$p.value, kpss_level$p.value, kpss_trend$p.value,
                    adf_diff$p.value, kpss_diff$p.value), 3)
)
write.csv(stat, file.path(out_dir, "stationarity_tests.csv"), row.names = FALSE)
cat("\nStationarity tests\n"); print(stat)
cat("ndiffs (KPSS):", nd, " nsdiffs (seasonal):", nsd, "\n")
# Note: tseries truncates p-values to [0.01, 0.1] for KPSS and [0.01, 0.99] for ADF.

# ------------------------------------------------------------------ 3 ACF / PACF
lag_max <- 12
ci <- qnorm(0.975) / sqrt(length(dy))
acf_v <- acf(dy, lag.max = lag_max, plot = FALSE)$acf[-1]
pacf_v <- pacf(dy, lag.max = lag_max, plot = FALSE)$acf
acf_df <- data.frame(lag = 1:lag_max, acf = round(acf_v, 4), pacf = round(as.numeric(pacf_v), 4),
                     ci95 = round(ci, 4))
write.csv(acf_df, file.path(out_dir, "acf_pacf_diff.csv"), row.names = FALSE)
png_open("fc_02_acf_pacf.png", 1800, 800)
par(mfrow = c(1, 2))
Acf(dy, lag.max = lag_max, main = "ACF, first difference")
Pacf(dy, lag.max = lag_max, main = "PACF, first difference")
dev.off()
cat("\nACF/PACF of first difference (95% band +/-", round(ci, 3), ")\n"); print(acf_df)

# ------------------------------------------------------------------ 4-5 candidate models, AICc
# 2017Q3 level shift: NOT in the candidate set (decision D10). AICc only ranks models fairly when the
# candidates are fixed before looking at the data. This dummy was placed on the largest residual
# after seeing it, so it would win on AICc almost by construction, and the cause of the jump is
# unconfirmed. It is fitted separately below as a robustness check. The shift column is kept so the
# check can reuse the same code: set shift = c(FALSE, TRUE) to see what the grid would pick.
step <- as.numeric(time(y) >= 2017.5)          # 0 before 2017Q3, 1 from 2017Q3 on
grid <- expand.grid(p = 0:2, q = 0:2, P = 0:1, Q = 0:1, drift = c(TRUE, FALSE), shift = FALSE)
fit_one <- function(x, g) {
  tryCatch(Arima(x, order = c(g$p, 1, g$q), seasonal = list(order = c(g$P, 0, g$Q), period = 4),
                 include.drift = g$drift, xreg = if (g$shift) step[seq_along(x)] else NULL,
                 method = "ML"),
           error = function(e) NULL)
}
res <- list()
for (i in seq_len(nrow(grid))) {
  g <- grid[i, ]
  f <- fit_one(y, g)
  if (is.null(f)) next
  lb <- Box.test(residuals(f), lag = 8, type = "Ljung-Box", fitdf = g$p + g$q + g$P + g$Q)
  res[[length(res) + 1]] <- data.frame(
    model = sprintf("ARIMA(%d,1,%d)(%d,0,%d)[4]%s%s", g$p, g$q, g$P, g$Q, ifelse(g$drift, " with drift", ""),
                    ifelse(g$shift, " + 2017Q3 shift", "")),
    p = g$p, q = g$q, P = g$P, Q = g$Q, drift = g$drift, shift = g$shift, n_params = length(coef(f)),
    AIC = round(f$aic, 2), AICc = round(f$aicc, 2), BIC = round(f$bic, 2),
    ljung_box_p = round(lb$p.value, 3))
}
cand <- do.call(rbind, res)
cand <- cand[order(cand$AICc), ]
write.csv(cand, file.path(out_dir, "candidate_models.csv"), row.names = FALSE)
cat("\nTop 10 candidates by AICc\n"); print(head(cand, 10), row.names = FALSE)

best <- cand[1, ]
spec <- list(order = c(best$p, 1, best$q), seasonal = c(best$P, 0, best$Q), drift = best$drift,
             shift = best$shift)
cat("\nChosen:", best$model, "\n")

auto <- auto.arima(y, d = 1, stepwise = FALSE, approximation = FALSE)
cat("auto.arima cross-check:", as.character(auto), " AICc", round(auto$aicc, 2), "\n")

fit_spec <- function(x) Arima(x, order = spec$order,
                              seasonal = list(order = spec$seasonal, period = 4),
                              include.drift = spec$drift,
                              xreg = if (spec$shift) step[seq_along(x)] else NULL, method = "ML")
# Future values of the shift dummy: the break has already happened, so it stays at 1.
fut_x <- function(h) if (spec$shift) rep(1, h) else NULL
fit <- fit_spec(y)
coefs <- data.frame(term = names(coef(fit)), estimate = round(coef(fit), 4),
                    std_error = round(sqrt(diag(fit$var.coef)), 4))
coefs$t_value <- round(coefs$estimate / coefs$std_error, 2)
write.csv(coefs, file.path(out_dir, "chosen_model_coefficients.csv"), row.names = FALSE)
cat("\nCoefficients\n"); print(coefs, row.names = FALSE)

# ------------------------------------------------------------------ 6 residual diagnostics
r <- residuals(fit)
k <- sum(spec$order[c(1, 3)]) + sum(spec$seasonal[c(1, 3)])   # ARMA terms only
lb8 <- Box.test(r, lag = 8, type = "Ljung-Box", fitdf = k)
lb12 <- Box.test(r, lag = 12, type = "Ljung-Box", fitdf = k)
sw <- shapiro.test(r)
r_acf <- acf(r, lag.max = lag_max, plot = FALSE)$acf[-1]
diag_df <- data.frame(
  check = c("Ljung-Box, 8 lags", "Ljung-Box, 12 lags", "Shapiro-Wilk normality", "Residual mean",
            "Residual std dev"),
  value = round(c(lb8$statistic, lb12$statistic, sw$statistic, mean(r), sd(r)), 4),
  p_value = round(c(lb8$p.value, lb12$p.value, sw$p.value, NA, NA), 4))
write.csv(diag_df, file.path(out_dir, "residual_diagnostics.csv"), row.names = FALSE)
write.csv(data.frame(quarter = quarters, residual = round(as.numeric(r), 4)),
          file.path(out_dir, "residuals.csv"), row.names = FALSE)
write.csv(data.frame(lag = 1:lag_max, acf = round(r_acf, 4), ci95 = round(qnorm(0.975) / sqrt(length(r)), 4)),
          file.path(out_dir, "residual_acf.csv"), row.names = FALSE)
cat("\nResidual diagnostics\n"); print(diag_df, row.names = FALSE)
png_open("fc_03_residuals.png", 1800, 1100)
layout(matrix(c(1, 1, 2, 3), 2, byrow = TRUE))
plot(r, type = "h", lwd = 3, col = "#2a78d6", ylab = "Residual", xlab = "", main = "Residuals")
abline(h = 0, col = "grey50")
Acf(r, lag.max = lag_max, main = "Residual ACF")
hist(r, breaks = 12, col = "#b8c3cb", border = "white", main = "Residual histogram", xlab = "")
dev.off()

# ------------------------------------------------------------------ 7 ex-post validation
n <- length(y)
train <- window(y, end = time(y)[n - H])
test <- window(y, start = time(y)[n - H + 1])
fit_tr <- fit_spec(train)
fc_tr <- forecast(fit_tr, h = H, level = 95, xreg = fut_x(H))
mape <- function(a, f) mean(abs((a - f) / a)) * 100
bench_naive <- naive(train, h = H)
bench_drift <- rwf(train, h = H, drift = TRUE)
bench_snaive <- snaive(train, h = H)
val <- data.frame(
  quarter = quarters[(n - H + 1):n],
  actual = as.numeric(test),
  arima = round(as.numeric(fc_tr$mean), 3),
  lo95 = round(as.numeric(fc_tr$lower), 3),
  hi95 = round(as.numeric(fc_tr$upper), 3),
  naive = round(as.numeric(bench_naive$mean), 3),
  drift = round(as.numeric(bench_drift$mean), 3))
val$inside_95 <- val$actual >= val$lo95 & val$actual <= val$hi95
write.csv(val, file.path(out_dir, "validation_holdout.csv"), row.names = FALSE)
val_sum <- data.frame(
  method = c(paste("Chosen model:", best$model), "Naive (last value)", "Random walk with drift",
             "Seasonal naive"),
  MAPE_pct = round(c(mape(test, fc_tr$mean), mape(test, bench_naive$mean),
                     mape(test, bench_drift$mean), mape(test, bench_snaive$mean)), 2),
  RMSE = round(c(sqrt(mean((test - fc_tr$mean)^2)), sqrt(mean((test - bench_naive$mean)^2)),
                 sqrt(mean((test - bench_drift$mean)^2)), sqrt(mean((test - bench_snaive$mean)^2))), 3))
write.csv(val_sum, file.path(out_dir, "validation_summary.csv"), row.names = FALSE)
cat("\nHold-out validation, train", quarters[1], "-", quarters[n - H], ", test", quarters[n - H + 1], "-",
    quarters[n], "\n"); print(val, row.names = FALSE); print(val_sum, row.names = FALSE)

# ------------------------------------------------------------------ forecast
fc <- forecast(fit, h = H, level = c(80, 95), xreg = fut_x(H))
fq <- qlab(as.numeric(time(fc$mean)))
fc_df <- data.frame(quarter = fq, forecast = round(as.numeric(fc$mean), 3),
                    lo80 = round(fc$lower[, 1], 3), hi80 = round(fc$upper[, 1], 3),
                    lo95 = round(fc$lower[, 2], 3), hi95 = round(fc$upper[, 2], 3))
fc_df$growth_vs_2025Q2_pct <- round((fc_df$forecast / tail(as.numeric(y), 1) - 1) * 100, 2)
write.csv(fc_df, file.path(out_dir, "forecast_4q.csv"), row.names = FALSE)
write.csv(data.frame(quarter = quarters, actual = as.numeric(y), fitted = round(as.numeric(fitted(fit)), 3)),
          file.path(out_dir, "series_fitted.csv"), row.names = FALSE)
cat("\nForecast\n"); print(fc_df, row.names = FALSE)

png_open("fc_04_forecast.png")
plot(fc, main = paste("Forecast,", best$model), ylab = "EUR/m2 per month", xlab = "",
     fcol = "#eb6834", shadecols = c("#f7c7b2", "#fbe3d8"), col = "#2a78d6", lwd = 2)
grid(col = "#e8ecef", lty = 1)
dev.off()

# ------------------------------------------------------------------ check against what happened
# The forecast quarters 2025Q3-2026Q2 are already published, but only in the new table (15fa),
# whose levels are not comparable. Its growth rates are, roughly: compare 2026Q2 vs 2025Q2.
b <- read.csv(file.path(root, "data", "processed", "area_rents_15fa_2025_latest.csv"),
              colClasses = c(area_code = "character"), encoding = "UTF-8")
pick <- function(m, q) b$value[b$area_code == "091" & b$financing == "Free-market" & b$size == "All" &
                                 b$measure == m & b$quarter == q]
g_new_index <- (pick("index_2025", "2026Q2") / pick("index_2025", "2025Q2") - 1) * 100
g_new_eur <- (pick("rent_eur_m2", "2026Q2") / pick("rent_eur_m2", "2025Q2") - 1) * 100
g_fc <- tail(fc_df$growth_vs_2025Q2_pct, 1)
g_lo <- (tail(fc_df$lo95, 1) / tail(as.numeric(y), 1) - 1) * 100
g_hi <- (tail(fc_df$hi95, 1) / tail(as.numeric(y), 1) - 1) * 100
check <- data.frame(
  measure = c("Forecast growth 2025Q2 to 2026Q2 (old basis)", "Forecast 95% interval, low",
              "Forecast 95% interval, high", "Actual: new-table index 2025=100",
              "Actual: new-table average EUR/m2"),
  growth_pct = round(c(g_fc, g_lo, g_hi, g_new_index, g_new_eur), 2))
write.csv(check, file.path(out_dir, "check_vs_new_table.csv"), row.names = FALSE)
cat("\nCheck against what happened\n"); print(check, row.names = FALSE)

writeLines(c(paste("chosen_model:", best$model),
             paste("auto_arima:", as.character(auto)),
             paste("n_obs:", length(y)),
             paste("R:", R.version.string),
             paste("forecast package:", as.character(packageVersion("forecast")))),
           file.path(out_dir, "model_info.txt"))

# ------------------------------------------------------------------ robustness checks
# a) Residuals are not normal (Shapiro-Wilk), so also compute bootstrapped intervals.
fc_boot <- forecast(fit, h = H, level = 95, bootstrap = TRUE, npaths = 5000, xreg = fut_x(H))
# b) Growth has slowed since 2022: estimate the drift on 2022Q1-2025Q2 only.
y_recent <- window(y, start = c(2022, 1))
fit_recent <- Arima(y_recent, order = c(0, 1, 0), include.drift = TRUE, method = "ML")
# c) Same procedure on the quality-adjusted rent index (2015=100).
si <- a[a$area_code == "091" & a$financing == "Free-market" & a$size == "All" &
          a$measure == "index_2015" & a$quarter <= LAST_Q, ]
yi <- ts(si$value[order(si$quarter)], start = c(2015, 1), frequency = 4)
auto_i <- auto.arima(yi, stepwise = FALSE, approximation = FALSE)
# d) Largest residuals
top_r <- head(order(abs(r), decreasing = TRUE), 3)

rob <- data.frame(
  item = c("Drift per quarter, full sample 2015Q1-2025Q2 (EUR/m2)",
           "Drift per quarter, 2022Q1-2025Q2 only (EUR/m2)",
           "Drift std error, 2022Q1-2025Q2",
           "Forecast 2026Q2 with recent drift (EUR/m2)",
           "Bootstrap 95% interval 2026Q2, low", "Bootstrap 95% interval 2026Q2, high",
           paste("Index model (auto.arima):", as.character(auto_i)),
           paste0("Largest residuals: ", paste(quarters[top_r], collapse = ", "))),
  value = c(round(coef(fit)["drift"], 4), round(coef(fit_recent)["drift"], 4),
            round(sqrt(fit_recent$var.coef[1, 1]), 4),
            round(tail(as.numeric(forecast(fit_recent, h = H)$mean), 1), 3),
            round(tail(as.numeric(fc_boot$lower), 1), 3), round(tail(as.numeric(fc_boot$upper), 1), 3),
            round(auto_i$aicc, 2), paste(round(r[top_r], 3), collapse = ", ")))
write.csv(rob, file.path(out_dir, "robustness.csv"), row.names = FALSE)
cat("\nRobustness\n"); print(rob, row.names = FALSE)

# ------------------------------------------------------------------ review checks
# e) Robustness check (D10): the chosen model plus a 2017Q3 level-shift dummy.
fit_v1 <- Arima(y, order = c(0, 1, 0), include.drift = TRUE, xreg = step, method = "ML")
fc_v1 <- forecast(fit_v1, h = H, level = 95, xreg = rep(1, H))
fc_v1_tr <- forecast(Arima(train, order = c(0, 1, 0), include.drift = TRUE, xreg = step[1:(n - H)],
                           method = "ML"), h = H, xreg = rep(1, H))
# f) Forecast the quality-adjusted index (like-for-like rent change), so the check against the
#    new table compares index growth with index growth.
fit_i_rw <- Arima(yi, order = c(0, 1, 0), include.drift = TRUE, method = "ML")
train_i <- window(yi, end = time(yi)[n - H]); test_i <- window(yi, start = time(yi)[n - H + 1])
mape_i <- function(f) round(mape(test_i, forecast(f, h = H)$mean), 2)
# Hold-out refits re-estimate the coefficients on the training quarters only (note N5). Passing
# model = auto_i would reuse coefficients estimated with the test quarters included.
ord_i <- arimaorder(auto_i)
refit_i_train <- function() Arima(train_i, order = ord_i[1:3],
                                  seasonal = list(order = ord_i[4:6], period = 4), method = "ML")
fc_i_rw <- forecast(fit_i_rw, h = H, level = 95)
fc_i_auto <- forecast(auto_i, h = H, level = 95)
fc_main <- forecast(fit, h = H, level = 95, xreg = fut_x(H))
g <- function(fc, base) round((tail(as.numeric(fc$mean), 1) / base - 1) * 100, 2)
gl <- function(fc, base) round((tail(as.numeric(fc$lower), 1) / base - 1) * 100, 2)
gu <- function(fc, base) round((tail(as.numeric(fc$upper), 1) / base - 1) * 100, 2)
yb <- tail(as.numeric(y), 1); ib <- tail(as.numeric(yi), 1)
rev <- data.frame(
  model = c(paste("Average EUR/m2, chosen:", best$model),
            "Average EUR/m2, check: ARIMA(0,1,0) with drift + 2017Q3 level shift",
            "Index: random walk with drift",
            paste("Index:", as.character(auto_i))),
  drift_per_quarter = c(round(coef(fit)["drift"], 4), round(coef(fit_v1)["drift"], 4),
                        round(coef(fit_i_rw)["drift"], 4), NA),
  growth_2025Q2_to_2026Q2_pct = c(g(fc_main, yb), g(fc_v1, yb), g(fc_i_rw, ib), g(fc_i_auto, ib)),
  lo95_pct = c(gl(fc_main, yb), gl(fc_v1, yb), gl(fc_i_rw, ib), gl(fc_i_auto, ib)),
  hi95_pct = c(gu(fc_main, yb), gu(fc_v1, yb), gu(fc_i_rw, ib), gu(fc_i_auto, ib)),
  holdout_MAPE_pct = c(round(mape(test, fc_tr$mean), 2), round(mape(test, fc_v1_tr$mean), 2),
                       mape_i(Arima(train_i, order = c(0, 1, 0), include.drift = TRUE, method = "ML")),
                       mape_i(refit_i_train())),
  AICc = c(round(fit$aicc, 2), round(fit_v1$aicc, 2), round(fit_i_rw$aicc, 2), round(auto_i$aicc, 2)))
naive_i <- round(mape(test_i, naive(train_i, h = H)$mean), 2)
write.csv(rev, file.path(out_dir, "review_checks.csv"), row.names = FALSE)
cat("\nReview checks (actual 2025Q2-2026Q2: new-table index -0.2%, average -0.1%)\n")
print(rev, row.names = FALSE)
cat("Index hold-out MAPE, naive:", naive_i, "\n")
# Index model diagnostics and forecast, saved for the report
k_i <- length(coef(auto_i))
idx_diag <- data.frame(
  check = c("ndiffs KPSS", "KPSS p, first difference", "ADF p, first difference", "ADF p, second difference",
            "Ljung-Box p, 8 lags", "Ljung-Box p, 12 lags", "Shapiro-Wilk p", "AICc",
            "Hold-out MAPE % (ARIMA)", "Hold-out MAPE % (naive)"),
  value = round(c(ndiffs(yi, test = "kpss"), kpss.test(diff(yi))$p.value, adf.test(diff(yi))$p.value,
                  adf.test(diff(diff(yi)))$p.value,
                  Box.test(residuals(auto_i), lag = 8, type = "Ljung-Box", fitdf = k_i)$p.value,
                  Box.test(residuals(auto_i), lag = 12, type = "Ljung-Box", fitdf = k_i)$p.value,
                  shapiro.test(residuals(auto_i))$p.value, auto_i$aicc,
                  mape_i(refit_i_train()), naive_i), 4))
write.csv(idx_diag, file.path(out_dir, "index_model_diagnostics.csv"), row.names = FALSE)
fci <- forecast(auto_i, h = H, level = c(80, 95))
write.csv(data.frame(quarter = fq, forecast = round(as.numeric(fci$mean), 3),
                     lo80 = round(fci$lower[, 1], 3), hi80 = round(fci$upper[, 1], 3),
                     lo95 = round(fci$lower[, 2], 3), hi95 = round(fci$upper[, 2], 3)),
          file.path(out_dir, "index_forecast_4q.csv"), row.names = FALSE)
write.csv(data.frame(term = names(coef(auto_i)), estimate = round(coef(auto_i), 4),
                     std_error = round(sqrt(diag(auto_i$var.coef)), 4)),
          file.path(out_dir, "index_model_coefficients.csv"), row.names = FALSE)
cat("\nIndex model diagnostics\n"); print(idx_diag, row.names = FALSE)

# ------------------------------------------------------------------ variance break (note N2)
# The residual spread is much smaller after 2021 than before. The forecast interval uses the
# full-sample spread, so it reflects the volatile early years more than today's market.
qr <- quarters[-1]; rr <- as.numeric(residuals(fit))[-1]     # first residual is the start-up value
e_early <- rr[qr <= "2021Q4"]; e_late <- rr[qr >= "2022Q1"]
vt <- var.test(e_early, e_late)
# Check: the same model type estimated on 2022Q1-2025Q2 only (no 2017Q3 shift needed there),
# so both its drift and its spread come from the recent market.
y_rec <- window(y, start = c(2022, 1))
fit_rec <- Arima(y_rec, order = c(0, 1, 0), include.drift = TRUE, method = "ML")
fc_rec <- forecast(fit_rec, h = H, level = 95)
vb <- data.frame(
  item = c("Residual std dev 2015Q2-2021Q4", "Residual std dev 2022Q1-2025Q2",
           "F ratio (early / late variance)", "F-test p-value",
           "Recent-sample model: drift per quarter", "Recent-sample model: growth to 2026Q2 %",
           "Recent-sample model: 95% low %", "Recent-sample model: 95% high %"),
  value = round(c(sd(e_early), sd(e_late), var(e_early) / var(e_late), vt$p.value,
                  coef(fit_rec)["drift"], g(fc_rec, yb), gl(fc_rec, yb), gu(fc_rec, yb)), 4))
write.csv(vb, file.path(out_dir, "variance_break.csv"), row.names = FALSE)
cat("
Variance break
"); print(vb, row.names = FALSE)

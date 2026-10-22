# VIX-Conditioned Short-Term Reversal on S&P 500 Stocks

Quantitative strategy research capstone (Imperial College Business School).

**Question.** Does a weekly, sector-adjusted equity reversal strategy earn more after elevated VIX, and does sizing positions on lagged VIX improve after-cost performance?

**Result (out of sample, 2018 to October 2026, run once).** Not supported. The unconditional strategy returns -6.9% a year after 5 bps costs (Sharpe -0.40); the VIX rule returns -5.1% a year (Sharpe -0.23), a difference that is not statistically significant (t = 0.85). A rule using realised volatility instead of VIX did at least as well, so VIX added no information beyond volatility scaling. Gross of costs the strategy earned about 2% a year (Sharpe 0.11). The full write-up is in `report.md`.

## Contents

| Path | What it is |
|---|---|
| `report.md` | The written report: hypothesis, methodology, results, pitfall checklist, efficiency and risk touchpoints, reflection |
| `notebook.ipynb` | Data loading, cleaning, strategy, backtest, mechanism test, conditional rule, out-of-sample test. Runs top to bottom |
| `data_pipeline.py` | Downloads prices, VIX and S&P 500 constituents and builds the snapshot in `data/` |
| `data/` | Downloaded snapshot: `prices.csv.gz`, `sectors.csv`, `vix.csv`, `dropped_tickers.csv`, `pipeline_log.txt` |
| `design_choices.md` | Design fixed before any backtest (commit `042ce5c`) |
| `results/test_results.csv` | Out-of-sample summary tables written by the notebook |
| `requirements.txt` | Python dependencies |

## How to run

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Open `notebook.ipynb` and run all cells. The notebook reads the snapshot in `data/`, so it needs no internet connection and no API keys.

To rebuild the snapshot from the source (requires internet; results will differ slightly if Yahoo Finance data has been revised):

```
python data_pipeline.py --refresh
```

## Data and limitations

- Prices and the VIX index come from Yahoo Finance via `yfinance`. The constituent list and GICS sectors are scraped from Wikipedia. The snapshot is included for coursework reproducibility only; check Yahoo's terms before redistributing it.
- The universe is today's S&P 500, so it contains survivorship bias, and sector labels are not point-in-time. See Section 5 of the report.
- Costs are a flat 5 bps per side (10 bps stress test); borrow costs and market impact are not modelled.

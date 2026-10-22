"""
Data pipeline: S&P 500 constituents + sectors, adjusted daily prices, VIX.

Run once to build the snapshot in data/ :
    python data_pipeline.py --refresh

Afterwards the notebook should just call load_snapshot(), so it still runs
if yfinance is slow or rate-limited.

Known limitation (document it in the report): the constituent list is TODAY's
S&P 500, so companies that were delisted/acquired/bankrupt during the sample are
missing (survivorship bias), and sector labels are current, not historical.

Dropped tickers are logged with a REASON:
  - "download failed": Yahoo returned nothing (network timeout etc.). These are
    retried; any that still fail are reported loudly so you can re-run.
  - "short history": the stock genuinely has too little data (IPO'd late).
"""
import argparse
import io
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

DATA = Path("data")
START, END = "2004-01-01", "2026-10-21"   # fixed end date => reproducible snapshot
BATCH = 25                                 # small batches are gentler on Yahoo
TIMEOUT = 30                               # seconds per request (default 10 was too short)
RETRY_ROUNDS = 3
# Only drop tickers that are almost empty. Late IPOs are KEPT: their early days stay NaN
# and the strategy simply skips them. (Requiring a long history would filter the universe
# using information that was not known at the time = look-ahead in universe construction.)
MAX_MISSING_FRAC = 0.95


def get_constituents() -> pd.DataFrame:
    """Current S&P 500 members and GICS sectors, scraped from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    table = pd.read_html(io.StringIO(html))[0]
    out = table[["Symbol", "GICS Sector"]].copy()
    out.columns = ["ticker", "sector"]
    out["ticker"] = out["ticker"].str.replace(".", "-", regex=False)  # BRK.B -> BRK-B
    return out


def fetch(tickers):
    """One yfinance call. threads=False avoids the parallel timeouts."""
    df = yf.download(tickers, start=START, end=END, auto_adjust=True,
                     progress=False, threads=False, timeout=TIMEOUT)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0])
    return df


def download_prices(tickers, log):
    """Download adjusted closes in small batches, then retry every ticker that came back empty."""
    frames = []
    for i in range(0, len(tickers), BATCH):
        batch = tickers[i:i + BATCH]
        try:
            frames.append(fetch(batch))
        except Exception as e:
            log.append(f"batch {i} raised {type(e).__name__}: {e}")
        print(f"downloaded batch {i // BATCH + 1}/{-(-len(tickers) // BATCH)}", flush=True)
    prices = pd.concat(frames, axis=1)
    prices = prices.loc[:, ~prices.columns.duplicated()].reindex(columns=tickers)

    # yfinance often swallows errors and returns an all-NaN column: retry those one by one.
    for rnd in range(1, RETRY_ROUNDS + 1):
        failed = [t for t in tickers if prices[t].isna().all()]
        if not failed:
            break
        print(f"retry round {rnd}: {len(failed)} tickers returned nothing", flush=True)
        time.sleep(10)
        for t in failed:
            try:
                s = fetch([t])
                if t in s.columns:
                    prices[t] = s[t].reindex(prices.index)
            except Exception as e:
                log.append(f"retry {rnd} {t} raised {type(e).__name__}: {e}")
            time.sleep(1)
    return prices


def clean(prices: pd.DataFrame, log):
    """Drop unusable tickers WITH a reason; never forward-fill silently."""
    prices = prices.sort_index().dropna(how="all")
    dropped = []
    empty = [t for t in prices.columns if prices[t].isna().all()]
    for t in empty:
        dropped.append((t, "download failed (no data at all)", 1.0))
    rest = prices.drop(columns=empty)
    miss = rest.isna().mean()
    sparse = miss[miss > MAX_MISSING_FRAC]
    for t, f in sparse.items():
        dropped.append((t, "short history / many missing days", float(f)))
    prices = rest.drop(columns=sparse.index)
    for t, why, f in dropped:
        log.append(f"dropped {t}: {why} ({f:.1%} missing)")
    log.append(f"final prices shape: {prices.shape}, "
               f"{prices.index.min().date()} to {prices.index.max().date()}")
    return prices, pd.DataFrame(dropped, columns=["ticker", "reason", "frac_missing"])


def build_snapshot():
    DATA.mkdir(exist_ok=True)
    log = []
    cons = get_constituents()
    prices, dropped = clean(download_prices(cons["ticker"].tolist(), log), log)
    cons = cons[cons["ticker"].isin(prices.columns)]
    vix = yf.download("^VIX", start=START, end=END, auto_adjust=True,
                      progress=False, threads=False, timeout=TIMEOUT)["Close"]
    if isinstance(vix, pd.DataFrame):
        vix = vix.iloc[:, 0]
    vix.name = "VIX"

    prices.to_csv(DATA / "prices.csv.gz")
    cons.to_csv(DATA / "sectors.csv", index=False)
    vix.to_csv(DATA / "vix.csv")
    dropped.to_csv(DATA / "dropped_tickers.csv", index=False)
    (DATA / "pipeline_log.txt").write_text("\n".join(log))

    failed = dropped[dropped["reason"].str.startswith("download failed")]
    print("\n=== SUMMARY ===")
    print("prices:", prices.shape, "| VIX rows:", len(vix))
    print("dropped for short history:", len(dropped) - len(failed))
    print("dropped because DOWNLOAD FAILED:", len(failed))
    if len(failed):
        print("  ->", failed["ticker"].tolist())
        print("  Re-run `python data_pipeline.py --refresh` (try a different network if it persists).")
    return prices, cons, vix


def load_snapshot():
    prices = pd.read_csv(DATA / "prices.csv.gz", index_col=0, parse_dates=True)
    sectors = pd.read_csv(DATA / "sectors.csv")
    vix = pd.read_csv(DATA / "vix.csv", index_col=0, parse_dates=True).iloc[:, 0]
    return prices, sectors, vix


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download everything")
    args = ap.parse_args()
    if args.refresh or not (DATA / "prices.csv.gz").exists():
        build_snapshot()
    else:
        p, s, v = load_snapshot()
        print("snapshot loaded:", p.shape, len(s), len(v))

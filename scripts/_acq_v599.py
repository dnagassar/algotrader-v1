import json, time, sys
from pathlib import Path
sys.path.insert(0, "src")
from algotrader.execution.perp_funding_refresh_adapter import (
    PerpFundingRefreshConfig, run_perp_funding_refresh, APPROVED_PERP_SYMBOLS)

ROOT = Path("runs/v5_99_funding_carry_detector")
ACQ = ROOT / "data_acquisition"; CAN = ROOT / "canonical"; CAN.mkdir(parents=True, exist_ok=True)
START = 1577836800000   # 2020-01-01
END   = 1785542400000   # 2026-07-31
DAY = 86400000

def page(sym, series, a, b):
    cfg = PerpFundingRefreshConfig(symbol=sym, series=series, output_root=ACQ,
        mode="live_market_data_fetch", start_ms=a, end_ms=b, limit=1000,
        live_market_data_fetch_authorized=True)
    rec = run_perp_funding_refresh(cfg)
    return json.loads(Path(rec["raw_response_path"]).read_text(encoding="utf-8"))

for sym in APPROVED_PERP_SYMBOLS:
    # funding: hourly, ~31-day cap per request
    out, cur = {}, START
    while cur < END:
        nxt = min(cur + 30*DAY, END)
        d = page(sym, "funding", cur, nxt).get("result", [])
        for r in d: out[int(r["timestamp"])] = (float(r["interest_1h"]), float(r["index_price"]))
        cur = nxt; time.sleep(0.12)
    (CAN / f"{sym.lower()}_funding.json").write_text(
        json.dumps({str(k): v for k, v in sorted(out.items())}, separators=(",",":")), encoding="utf-8")
    print(f"{sym} funding rows={len(out)}", flush=True)

    # perp closes: hourly bars, ~40-day chunks
    closes, cur = {}, START
    while cur < END:
        nxt = min(cur + 40*DAY, END)
        r = page(sym, "perp_kline", cur, nxt)
        res = r.get("result", {})
        ticks, cl = res.get("ticks", []), res.get("close", [])
        for t_, c_ in zip(ticks, cl): closes[int(t_)] = float(c_)
        cur = nxt; time.sleep(0.12)
    (CAN / f"{sym.lower()}_perp_close.json").write_text(
        json.dumps({str(k): v for k, v in sorted(closes.items())}, separators=(",",":")), encoding="utf-8")
    print(f"{sym} perp closes={len(closes)}", flush=True)
print("ACQUISITION_COMPLETE", flush=True)

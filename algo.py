"""
Chartink CE/PE scanners -> best setup -> Angel One stock options (intraday buy)

ஓட்டும் முறை:
    python algo.py                 # காலை 9:20க்குள் start பண்ணுங்க
    python algo.py --test-scanner  # scanner லிஸ்ட் மட்டும் பார்க்க (trade இல்லை)
"""
import csv
import datetime as dt
import json
import logging
import os
import re
import sys
import time

import pyotp
import requests
from SmartApi import SmartConnect

import config as C

TODAY = dt.date.today()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.FileHandler(f"algo_{TODAY}.log", encoding="utf-8"),
              logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("algo")


# ---------------- helpers ----------------
def now():
    return dt.datetime.now()


def at(hms):
    h, m, s = map(int, hms.split(":"))
    return now().replace(hour=h, minute=m, second=s, microsecond=0)


def wait_until(t: dt.datetime):
    while now() < t:
        time.sleep(min(5, max(0.5, (t - now()).total_seconds())))


START = dt.datetime.now()


def square_off_at():
    t = at(C.SQUARE_OFF_TIME)
    if C.MAX_RUNTIME_MIN:
        t = min(t, START + dt.timedelta(minutes=C.MAX_RUNTIME_MIN))
    return t


def tick(p, size=0.05):
    return round(round(p / size) * size, 2)


# ---------------- Chartink ----------------
def fetch_chartink(clause):
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    page = s.get("https://chartink.com/screener/", timeout=15).text
    m = re.search(r'name="csrf-token" content="([^"]+)"', page)
    if not m:
        raise RuntimeError("Chartink CSRF token கிடைக்கவில்லை")
    r = s.post("https://chartink.com/screener/process", data={"scan_clause": clause},
               headers={"x-csrf-token": m.group(1), "Referer": "https://chartink.com/screener/"},
               timeout=15)
    r.raise_for_status()
    js = r.json()
    if js.get("scan_error"):
        raise RuntimeError(f"Chartink clause error: {js['scan_error']}")
    return js.get("data", [])


# ---------------- Angel One ----------------
def login():
    api = SmartConnect(api_key=C.API_KEY)
    res = api.generateSession(C.CLIENT_CODE, C.MPIN, pyotp.TOTP(C.TOTP_SECRET).now())
    if not res or not res.get("status"):
        raise RuntimeError(f"Login தோல்வி: {res}")
    log.info("Angel One login OK")
    return api


def load_master():
    cache = f"scrip_{TODAY}.json"
    if os.path.exists(cache):
        data = json.load(open(cache))
    else:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data = requests.get(url, timeout=90).json()
        json.dump(data, open(cache, "w"))
    eq, opts = {}, {}
    for d in data:
        seg, sym = d.get("exch_seg"), d.get("symbol", "")
        if seg == "NSE" and sym.endswith("-EQ"):
            eq[sym[:-3]] = d["token"]
        elif seg == "NFO" and d.get("instrumenttype") == "OPTSTK":
            opts.setdefault(d["name"], []).append({
                "symbol": sym, "token": d["token"], "type": sym[-2:],
                "strike": float(d["strike"]) / 100, "lot": int(float(d["lotsize"])),
                "expiry": dt.datetime.strptime(d["expiry"], "%d%b%Y").date(),
            })
    log.info(f"Scrip master: {len(eq)} equities, {len(opts)} option underlyings")
    return eq, opts


def ltp(api, exch, sym, token):
    return float(api.ltpData(exch, sym, token)["data"]["ltp"])


def last_closed_15m(api, token):
    """இன்றைய கடைசியாக முடிந்த 15-min candle: [ts, o, h, l, c, v]"""
    res = api.getCandleData({"exchange": "NSE", "symboltoken": token, "interval": "FIFTEEN_MINUTE",
                             "fromdate": f"{TODAY} 09:15", "todate": now().strftime("%Y-%m-%d %H:%M")})
    time.sleep(0.4)
    closed = []
    for c in (res or {}).get("data") or []:
        start = dt.datetime.strptime(c[0][:16], "%Y-%m-%dT%H:%M")
        if start + dt.timedelta(minutes=15) <= now():
            closed.append(c)
    return closed[-1] if closed else None


def pick_option(opts, name, spot, side):
    chain = [o for o in opts.get(name, []) if o["type"] == side]
    expiries = sorted({o["expiry"] for o in chain if (o["expiry"] - TODAY).days >= C.MIN_DAYS_TO_EXPIRY})
    if not expiries:
        return None
    chain = sorted([o for o in chain if o["expiry"] == expiries[0]], key=lambda o: o["strike"])
    i = min(range(len(chain)), key=lambda k: abs(chain[k]["strike"] - spot))
    i = i - C.STRIKE_OFFSET if side == "CE" else i + C.STRIKE_OFFSET   # ITM பக்கம் நகர்த்தல்
    return chain[max(0, min(i, len(chain) - 1))]


def order(api, opt, side, qty, price, kind="LIMIT", trigger=0.0):
    p = {"variety": "STOPLOSS" if kind == "STOPLOSS_LIMIT" else "NORMAL",
         "tradingsymbol": opt["symbol"], "symboltoken": opt["token"], "exchange": "NFO",
         "transactiontype": side, "ordertype": kind, "producttype": "INTRADAY",
         "duration": "DAY", "price": str(tick(price)), "triggerprice": str(tick(trigger)),
         "quantity": str(qty)}
    if C.PAPER_TRADE:
        log.info(f"[PAPER] {side} {qty} {opt['symbol']} {kind} @ {tick(price)} trig {tick(trigger)}")
        return f"PAPER-{time.time()}"
    oid = api.placeOrder(p)
    log.info(f"ORDER {side} {qty} {opt['symbol']} {kind} @ {tick(price)} -> {oid}")
    return oid


def status(api, oid):
    if str(oid).startswith("PAPER"):
        return "open"
    for o in (api.orderBook() or {}).get("data") or []:
        if o.get("orderid") == oid:
            return o.get("status", "")
    return ""


def cancel(api, oid):
    if not str(oid).startswith("PAPER"):
        try:
            api.cancelOrder(oid, "STOPLOSS")
        except Exception as e:
            log.warning(f"SL cancel error: {e}")


def journal(row):
    path = "trade_journal.csv"
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


# ---------------- Setup evaluation ----------------
def evaluate(api, eq, side, row):
    sym = row["nsecode"]
    tok = eq.get(sym)
    if not tok:
        return None
    c = last_closed_15m(api, tok)
    if not c:
        return None
    spot = ltp(api, "NSE", f"{sym}-EQ", tok)
    if side == "CE":
        sl_u = c[3]
        risk = spot - sl_u
    else:
        sl_u = c[2]
        risk = sl_u - spot
    if risk <= 0:
        return None
    risk_pct = risk / spot * 100
    if risk_pct > C.MAX_UNDERLYING_SL_PCT:
        log.info(f"skip {sym} {side}: SL {risk_pct:.2f}% அதிகம்")
        return None
    # score: அன்றைய நகர்வு வலிமை + tight SL + volume
    score = abs(float(row.get("per_chg", 0) or 0)) + (C.MAX_UNDERLYING_SL_PCT - risk_pct) * 2 \
        + min(float(row.get("volume", 0) or 0) / 5e6, 2)
    return {"sym": sym, "token": tok, "side": side, "spot": spot, "sl_u": sl_u,
            "risk": risk, "risk_pct": risk_pct, "score": score}


# ---------------- Trade management ----------------
def trade(api, opts, s):
    sym, side = s["sym"], s["side"]
    opt = pick_option(opts, sym, s["spot"], side)
    if not opt:
        log.info(f"{sym}: option contract கிடைக்கவில்லை")
        return False
    prem = ltp(api, "NFO", opt["symbol"], opt["token"])
    lots = min(C.MAX_LOTS, int(C.MAX_PREMIUM_CAPITAL // (prem * opt["lot"])))
    if lots < 1:
        log.info(f"{opt['symbol']}: 1 lot = ₹{prem * opt['lot']:.0f}, capital limit மீறுகிறது. skip")
        return False
    qty = lots * opt["lot"]
    dirn = 1 if side == "CE" else -1
    tgt_u = s["spot"] + dirn * C.RR_RATIO * s["risk"]
    sl_u = s["sl_u"]

    order(api, opt, "BUY", qty, prem * (1 + C.LIMIT_BUFFER_PCT / 100))
    entry_prem = prem
    hard_trig = entry_prem * (1 - C.PREMIUM_HARD_SL_PCT / 100)
    sl_oid = order(api, opt, "SELL", qty, hard_trig * 0.97, "STOPLOSS_LIMIT", hard_trig)
    log.info(f"TRADE {opt['symbol']} x{qty} @ ~{entry_prem} | {sym} spot {s['spot']} "
             f"SL {sl_u:.2f} target {tgt_u:.2f} | premium hard SL {hard_trig:.2f}")

    moved_be, reason, exit_prem = False, None, None
    while True:
        time.sleep(C.POLL_SECONDS)
        try:
            u = ltp(api, "NSE", f"{sym}-EQ", s["token"])
            p = ltp(api, "NFO", opt["symbol"], opt["token"])
        except Exception as e:
            log.warning(f"LTP error: {e}")
            continue

        if (not C.PAPER_TRADE and status(api, sl_oid) == "complete") or (C.PAPER_TRADE and p <= hard_trig):
            reason, exit_prem = "PREMIUM_SL", hard_trig
            break
        if dirn * (u - sl_u) <= 0:
            reason = "BREAKEVEN" if moved_be else "SL"
        elif dirn * (u - tgt_u) >= 0:
            reason = "TARGET"
        elif now() >= square_off_at():
            reason = "TIME"
        if reason:
            cancel(api, sl_oid)
            order(api, opt, "SELL", qty, p * (1 - C.LIMIT_BUFFER_PCT / 100))
            exit_prem = p
            break
        if C.BREAKEVEN_AT_R and not moved_be and dirn * (u - s["spot"]) >= C.BREAKEVEN_AT_R * s["risk"]:
            sl_u, moved_be = s["spot"], True
            log.info(f"{sym}: 1R வந்தது, SL entry-க்கு நகர்த்தப்பட்டது ({sl_u})")

    pnl = round((exit_prem - entry_prem) * qty, 2)
    log.info(f"EXIT {opt['symbol']} @ {exit_prem} ({reason})  P&L ≈ ₹{pnl}")
    journal({"date": str(TODAY), "underlying": sym, "side": side, "option": opt["symbol"],
             "qty": qty, "entry_prem": entry_prem, "exit_prem": exit_prem, "reason": reason,
             "spot_entry": s["spot"], "spot_sl": s["sl_u"], "spot_target": round(tgt_u, 2),
             "pnl": pnl, "paper": C.PAPER_TRADE})
    return True


# ---------------- Main ----------------
def scan_all():
    out = []
    for side, clause in (("CE", C.CE_SCAN_CLAUSE), ("PE", C.PE_SCAN_CLAUSE)):
        if not clause:
            continue
        try:
            rows = fetch_chartink(clause)
        except Exception as e:
            log.warning(f"{side} scanner error: {e}")
            continue
        log.info(f"{side} scanner: {[r['nsecode'] for r in rows]}")
        out += [(side, r) for r in rows]
    return out


def main():
    log.info(f"Algo start | PAPER_TRADE={C.PAPER_TRADE} | square off by {square_off_at():%H:%M}")
    api = login()
    eq, opts = load_master()
    trades, done = 0, set()

    for t in C.SCAN_TIMES:
        if trades >= C.MAX_TRADES_DAY:
            break
        if now() > at(t) + dt.timedelta(minutes=10):
            continue
        wait_until(at(t))
        setups = []
        for side, row in scan_all():
            if row["nsecode"] in done:
                continue
            try:
                s = evaluate(api, eq, side, row)
            except Exception as e:
                log.warning(f"{row['nsecode']} evaluate error: {e}")
                continue
            if s:
                setups.append(s)
        if not setups:
            log.info(f"{t}: பொருந்தும் setup இல்லை")
            continue
        setups.sort(key=lambda x: x["score"], reverse=True)
        log.info("RANKING: " + ", ".join(f"{x['sym']}-{x['side']}({x['score']:.1f})" for x in setups))
        for best in setups:
            if trade(api, opts, best):
                trades += 1
                done.add(best["sym"])
                break

    log.info("இன்றைய algo முடிந்தது.")


if __name__ == "__main__":
    if "--test-scanner" in sys.argv:
        for side, r in scan_all():
            print(side, r["nsecode"], r.get("close"), r.get("per_chg"))
        sys.exit()
    try:
        main()
    except KeyboardInterrupt:
        log.warning("கைமுறையாக நிறுத்தப்பட்டது — Angel One-ல open position இருக்கான்னு உடனே பாருங்க!")

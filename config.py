# ============================================================
#  config.py  —  CE / PE Stock Options Algo (Angel One)
# ============================================================
import os

# ---- Angel One SmartAPI login (environment variables) ----
API_KEY     = os.getenv("ANGEL_API_KEY", "")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE", "")
MPIN        = os.getenv("ANGEL_MPIN", "")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "").replace(" ", "").strip().upper()

# ---- True = உண்மையான order போகாது. 2-3 வாரம் இப்படி ஓட்டிப் பாருங்க ----
PAPER_TRADE = True

# ------------------------------------------------------------
# Scanner clauses — உங்க screenshot-லிருந்து நான் மறு-உருவாக்கியது.
# துல்லியமாக இருக்க: Chartink-ல "Stock passes all of the below filters"
# பக்கத்தில் இருக்கும் ஆரஞ்சு copy icon-ஐ தட்டி, உண்மையான clause-ஐ இங்கே paste பண்ணுங்க.
# {33489} = Chartink-ல futures (F&O) segment
# ------------------------------------------------------------

# CE scanner — "FINAL SCANER MASTER VERSION" (bullish)
CE_SCAN_CLAUSE = (
    "( {33489} ( weekly close > weekly sma( weekly close , 20 ) "
    "and weekly rsi( 14 ) > 60 "
    "and latest close > latest ema( latest close , 200 ) "
    "and latest ema( latest close , 20 ) > latest ema( latest close , 50 ) "
    "and latest close > 1 day ago high "
    "and [0] 15 minute close > [0] 15 minute vwap "
    "and [0] 15 minute close > [0] 15 minute ema( [0] 15 minute close , 20 ) "
    "and [0] 15 minute rsi( 14 ) > 60 "
    "and [0] 15 minute volume > [0] 15 minute sma( [0] 15 minute volume , 10 ) * 1.8 ) )"
)

# PE scanner — "DOW EARANGUM" (bearish: முதல் முறையாக நேற்றைய low-ஐ உடைக்கும் 15-min candle)
PE_SCAN_CLAUSE = (
    "( {33489} ( [0] 15 minute close < 1 day ago low "
    "and [-1] 15 minute close >= 1 day ago low "
    "and [0] 15 minute close < [0] 15 minute open "
    "and [0] 15 minute volume > [0] 15 minute sma( [0] 15 minute volume , 20 ) * 3 "
    "and [0] 15 minute close < [0] 15 minute vwap "
    "and [0] 15 minute rsi( 14 ) < 40 "
    "and latest close > 50 "
    "and latest volume > 500000 "
    "and market cap > 1000 ) )"
)

# ---- Scan நேரங்கள்: ஒவ்வொரு 15-min candle முடிந்த பிறகு (candle முடியும் முன் scan பண்ணினா repaint ஆகும்) ----
SCAN_TIMES = ["09:30:20", "09:45:20", "10:00:20", "10:15:20", "10:30:20",
              "10:45:20", "11:00:20", "11:15:20", "11:30:20"]
SQUARE_OFF_TIME = "15:10:00"
# GitHub Actions-ல ஒரு job 6 மணி நேரம் மட்டுமே ஓடும். அதனால start ஆன நேரத்திலிருந்து
# இத்தனை நிமிடத்துக்குள் கட்டாயம் square off (0 = இந்த வரம்பு இல்லை, laptop-க்கு)
MAX_RUNTIME_MIN = int(os.getenv("MAX_RUNTIME_MIN", "0"))

# ---- Option தேர்வு ----
STRIKE_OFFSET       = 0     # 0 = ATM, 1 = ஒரு strike ITM (delta அதிகம், decay குறைவு)
MIN_DAYS_TO_EXPIRY  = 4     # expiry-க்கு 4 நாளுக்குக் குறைவா இருந்தா அடுத்த மாத contract
MAX_LOTS            = 1
MAX_PREMIUM_CAPITAL = 40000 # ஒரு trade-க்கு அதிகபட்ச premium செலவு (₹). அதுக்கு மேல்னா skip

# ---- Risk (underlying ஸ்டாக் விலையை வைத்து) ----
# CE: SL = signal 15-min candle low   |  PE: SL = signal 15-min candle high
MAX_UNDERLYING_SL_PCT = 1.2   # ஸ்டாக்கில் SL தூரம் இதைவிட அதிகம்னா skip
RR_RATIO              = 2.0   # Target = 2 × risk (ஸ்டாக் விலையில்)
BREAKEVEN_AT_R        = 1.0   # 1R வந்ததும் SL-ஐ entry-க்கு நகர்த்தும்
PREMIUM_HARD_SL_PCT   = 35    # Premium 35% விழுந்தால் எப்படியும் exit (broker-ல SL order)

MAX_TRADES_DAY   = 2
LIMIT_BUFFER_PCT = 1.0   # Options-க்கு market order பதிலா LTP ± 1% limit order
POLL_SECONDS     = 3

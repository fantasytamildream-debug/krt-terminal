# ============================================================
#  config.py  —  CE / PE Stock Options Algo (Angel One)
# ============================================================
import os

# ---- Angel One SmartAPI login (environment variables) ----
API_KEY     = os.getenv("ANGEL_API_KEY", "").strip()
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE", "").strip().upper()
MPIN        = os.getenv("ANGEL_MPIN", "").strip()
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "").replace(" ", "").strip().upper()

# ---- True = உண்மையான order போகாது. 2-3 வாரம் இப்படி ஓட்டிப் பாருங்க ----
PAPER_TRADE = True

# ------------------------------------------------------------
# Scanner clauses — screenshot-லிருந்து மறு-உருவாக்கியது.
# துல்லியமாக இருக்க: Chartink-ல ஆரஞ்சு copy icon-ஐ தட்டி உண்மையான clause-ஐ paste பண்ணுங்க.
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

# PE scanner — "DOW EARANGUM" (bearish)
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

# ---- Scan நேரங்கள்: ஒவ்வொரு 15-min candle முடிந்த பிறகு ----
SCAN_TIMES = ["09:30:20", "09:45:20", "10:00:20", "10:15:20", "10:30:20",
              "10:45:20", "11:00:20", "11:15:20", "11:30:20"]
SQUARE_OFF_TIME = "15:10:00"
# GitHub Actions 6 மணி நேர வரம்பு: start-லிருந்து இத்தனை நிமிடத்துக்குள் square off
MAX_RUNTIME_MIN = int(os.getenv("MAX_RUNTIME_MIN", "0"))

# ---- Option தேர்வு ----
STRIKE_OFFSET       = 0     # 0 = ATM, 1 = ஒரு strike ITM
MIN_DAYS_TO_EXPIRY  = 4     # expiry-க்கு 4 நாளுக்குக் குறைவுன்னா அடுத்த மாத contract
MAX_LOTS            = 1
MAX_PREMIUM_CAPITAL = 40000 # ஒரு trade-க்கு அதிகபட்ச premium (₹)

# ---- Risk (ஸ்டாக் விலையை வைத்து) ----
MAX_UNDERLYING_SL_PCT = 1.2   # SL தூரம் இதைவிட அதிகம்னா skip
RR_RATIO              = 2.0   # Target = 2 × risk
BREAKEVEN_AT_R        = 1.0   # 1R வந்ததும் SL-ஐ entry-க்கு நகர்த்தும்
PREMIUM_HARD_SL_PCT   = 35    # Premium 35% விழுந்தால் exit

MAX_TRADES_DAY   = 2
LIMIT_BUFFER_PCT = 1.0
POLL_SECONDS     = 3

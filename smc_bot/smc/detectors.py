from typing import List, Tuple, Literal, Optional

# Candle: (datetime, open, high, low, close)
Candle = Tuple           # (datetime, open, high, low, close)
Side   = Literal["bull", "bear"]

def swing_points(prices: List[Candle], look_back: int = 3):
    n = len(prices)
    hi = [False] * n
    lo = [False] * n
    for i in range(look_back, n - look_back):
        h = prices[i][2]  # high at [2]
        l = prices[i][3]  # low at [3]
        if all(h > prices[j][2] for j in range(i - look_back, i + look_back + 1) if j != i):
            hi[i] = True
        if all(l < prices[j][3] for j in range(i - look_back, i + look_back + 1) if j != i):
            lo[i] = True
    return hi, lo

def detect_bos(prices: List[Candle], look_back: int = 3) -> bool:
    if len(prices) < look_back * 2 + 1:
        return False
    highs, _ = swing_points(prices, look_back)
    try:
        idx = len(highs) - 1 - highs[::-1].index(True)
    except ValueError:
        return False
    # close > last swing high
    return prices[-1][4] > prices[idx][2]

def detect_choch(prices: List[Candle], look_back: int = 3) -> bool:
    if len(prices) < look_back + 4:
        return False
    current_close = prices[-1][4]
    window = prices[-(look_back + 3):-1]
    for candle in window:
        if current_close < candle[3] and candle[3] > current_close:
            return True
    return False

def detect_orderblock(prices: List[Candle], side: Side, depth: int = 20) -> Optional[Tuple[int, float, float]]:
    if len(prices) < 2:
        return None
    search_start = max(0, len(prices) - depth - 1)
    rng = range(len(prices) - 2, search_start - 1, -1)
    if side == "bear":
        for i in rng:
            up_body   = prices[i][4] > prices[i][1]   # close > open (bullish)
            nxt_down  = prices[i + 1][4] < prices[i + 1][1]
            engulf    = prices[i + 1][4] < prices[i][3]
            if up_body and nxt_down and engulf:
                return i, prices[i][1], prices[i][4]  # open, close
    else:  # bull
        for i in rng:
            dn_body   = prices[i][4] < prices[i][1]
            nxt_up    = prices[i + 1][4] > prices[i + 1][1]
            engulf    = prices[i + 1][4] > prices[i][2]
            if dn_body and nxt_up and engulf:
                return i, prices[i][1], prices[i][4]
    return None

def detect_fvg(prices: List[Candle], lookback: int = 10):
    # FVG: fair value gap between candle i and i+2
    for i in range(len(prices) - lookback - 2, len(prices) - 2):
        h0, l0 = prices[i][2], prices[i][3]
        h2, l2 = prices[i + 2][2], prices[i + 2][3]
        if h0 < l2:
            return {"side": "bear", "upper": l2, "lower": h0, "idx": i}
        if l0 > h2:
            return {"side": "bull", "upper": l0, "lower": h2, "idx": i}
    return None

def get_session(hour):
    if 12 <= hour < 20:
        return "ny"
    elif 7 <= hour < 12:
        return "london"
    else:
        return "asia"

def session_high_low(candles: List[Candle], session="asia"):
    # candles: [(datetime, open, high, low, close), ...]
    hours = [c[0].hour if hasattr(c[0], "hour") else int(str(c[0])[11:13]) for c in candles]
    if session == "asia":
        idx = [i for i, h in enumerate(hours) if 0 <= h < 7 or 21 <= h <= 23]
    elif session == "london":
        idx = [i for i, h in enumerate(hours) if 7 <= h < 12]
    else:
        idx = [i for i, h in enumerate(hours) if 12 <= h < 20]
    if not idx:
        return None, None
    high = max(candles[i][2] for i in idx)  # high
    low = min(candles[i][3] for i in idx)   # low
    return high, low

def liquidity_sweep(prices: List[Candle], side: Side, window=30, asian_levels=None):
    recent = prices[-window:]
    high_prev = max(c[2] for c in recent[:-1])
    low_prev  = min(c[3] for c in recent[:-1])
    last_high = recent[-1][2]
    last_low  = recent[-1][3]
    sweep = ((side == "bull" and last_high > high_prev) or
             (side == "bear" and last_low < low_prev))
    if asian_levels:
        asia_hi, asia_lo = asian_levels
        if side == "bull" and asia_hi is not None and last_high > asia_hi:
            sweep = True
        if side == "bear" and asia_lo is not None and last_low < asia_lo:
            sweep = True
    return sweep

def premium_discount_zone(candles: List[Candle]):
    closes = [c[4] for c in candles]
    swing_hi = max(closes)
    swing_lo = min(closes)
    eq = (swing_hi + swing_lo) / 2
    return swing_hi, swing_lo, eq

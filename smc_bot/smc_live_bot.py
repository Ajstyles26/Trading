import MetaTrader5 as mt5
import pandas as pd
import time
import datetime

# ========== PARAMETERS ==========
SYMBOL = "XAUUSD"
M15_BARS = 100
M5_BARS = 100
MAX_DAILY_LOSS = 20000      # Max daily loss in $
DAILY_PROFIT_TARGET = 60000 # Daily profit target in $

# ======= Risk Tools =======
class DailyRiskManager:
    def __init__(self, max_loss=20000, profit_target=60000):
        self.max_loss = max_loss
        self.profit_target = profit_target
        self._reset_day()
    def _reset_day(self):
        self.day = datetime.date.today()
        self.day_pnl = 0
    def update_pnl(self, profit):
        if datetime.date.today() != self.day:
            self._reset_day()
        self.day_pnl += profit
    def can_trade(self):
        if self.day_pnl <= -abs(self.max_loss):
            print(f"Max daily loss hit: ${self.day_pnl:.2f}")
            return False
        if self.day_pnl >= self.profit_target:
            print(f"Daily profit target reached: ${self.day_pnl:.2f}")
            return False
        return True

def calc_dynamic_lot(equity, profit_target, daily_pnl, entry, stop, pip_value=10, min_lot=0.01, max_lot=2.0):
    # Adjust risk to reach profit target in as few trades as possible
    to_target = profit_target - daily_pnl
    if to_target <= 0:
        return 0.0
    stop_pips = abs(entry - stop) / 0.1  # 0.1 = 10 pips for gold (adjust if needed)
    if stop_pips * pip_value == 0:
        return min_lot
    lot = to_target / (stop_pips * pip_value * 2)  # risk half (since RR is 1:2, reward is twice risk)
    lot = max(min_lot, min(lot, max_lot))
    return round(lot, 2)

def round_price(price, symbol=SYMBOL):
    info = mt5.symbol_info(symbol)
    if info is None:
        return round(price, 2)
    digits = info.digits
    return round(price, digits)

def fix_sl_tp_rr(entry, sl, order_type, min_stop_distance, symbol, rr_ratio=2):
    """
    1:2 risk-reward (reward is always exactly twice the risk).
    Ensures SL/TP are on correct side and min_stop_distance away.
    """
    info = mt5.symbol_info(symbol)
    digits = info.digits if info else 2
    increment = min_stop_distance * 1.2 if min_stop_distance > 0 else 0.50

    if order_type == mt5.ORDER_TYPE_BUY:
        # SL below entry, TP above
        if sl is None or sl >= entry:
            sl = entry - increment
        if entry - sl < increment:
            sl = entry - increment
        risk = entry - sl
        tp = entry + risk * rr_ratio
    else:
        # SL above entry, TP below
        if sl is None or sl <= entry:
            sl = entry + increment
        if sl - entry < increment:
            sl = entry + increment
        risk = sl - entry
        tp = entry - risk * rr_ratio

    # Enforce minimum distance between sl/tp and entry
    sl = round(sl, digits)
    tp = round(tp, digits)

    # Never allow SL and TP to be equal
    if abs(sl - tp) < increment:
        if order_type == mt5.ORDER_TYPE_BUY:
            tp = sl + increment * rr_ratio
        else:
            sl = tp + increment * rr_ratio

    return sl, tp

# ========== SMC STRATEGY CORE ==========
from smc.SMCStrategyCore import SMCStrategyCore  # Use your own SMCStrategyCore class here

smc_core = SMCStrategyCore(
    lot_size=0.1,         # Default; dynamic lot overrides
    look_back=2,
    max_retests=8,
    atr_thresh=0.01,
    session_only=False
)
risk_manager = DailyRiskManager(max_loss=MAX_DAILY_LOSS, profit_target=DAILY_PROFIT_TARGET)

if not mt5.initialize():
    print("Failed to initialize MT5:", mt5.last_error())
    exit()
print("Connected to MetaTrader 5 Demo!")

def get_candles(symbol, timeframe, count):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    return [
        (pd.to_datetime(r['time'], unit='s'), r['open'], r['high'], r['low'], r['close'])
        for r in rates
    ]

def get_equity():
    info = mt5.account_info()
    return info.equity if info else 10000

def get_last_closed_trade_profit(symbol):
    now = datetime.datetime.now()
    deals = mt5.history_deals_get(now - datetime.timedelta(days=1), now, group=symbol)
    profits = [d.profit for d in deals if d.symbol == symbol and d.entry == 1]  # entry==1: closed
    if profits:
        return profits[-1]
    return 0

last_time = None
while True:
    equity = get_equity()
    if not risk_manager.can_trade():
        print("No trading today due to risk/profit limit.")
        time.sleep(300)
        continue

    candles_m15 = get_candles(SYMBOL, mt5.TIMEFRAME_M15, M15_BARS)
    candles_m5 = get_candles(SYMBOL, mt5.TIMEFRAME_M5, M5_BARS)
    closes = [c[4] for c in candles_m5]
    if len(closes) < 14:
        print("Waiting for more data...")
        time.sleep(60)
        continue
    atr = pd.Series(closes).rolling(14).std().iloc[-1]

    now = candles_m5[-1][0]
    if last_time == now:
        time.sleep(10)
        continue
    last_time = now
    hour = now.hour

    signal = smc_core.on_new_candles(
        candles_m15, [], candles_m5,
        atr_value=atr,
        atr_thresh=0.3,
        valid_hours=(7, 20),
        look_back=2,
        hour=hour
    )
    print(f"{now} | Signal: {signal}")

    positions = mt5.positions_get(symbol=SYMBOL)
    if signal.get("signal") in ["long", "short"] and not positions:
        entry = signal.get("entry")
        stop = signal.get("stop")
        if not entry or not stop:
            print("Missing entry/stop for dynamic lot calc, skipping trade.")
            time.sleep(60)
            continue

        info = mt5.symbol_info(SYMBOL)
        min_stop_distance = info.trade_stops_level * info.point if info else 0.5
        order_type = mt5.ORDER_TYPE_BUY if signal["signal"] == "long" else mt5.ORDER_TYPE_SELL

        sl, tp = fix_sl_tp_rr(entry, stop, order_type, min_stop_distance, SYMBOL, rr_ratio=2)

        lot = calc_dynamic_lot(equity, risk_manager.profit_target, risk_manager.day_pnl, entry, sl)
        if lot <= 0.0:
            print("Lot size zero: not trading.")
            time.sleep(60)
            continue

        tick = mt5.symbol_info_tick(SYMBOL)
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 202405,
            "comment": f"SMC Live {signal['signal'].upper()}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(request)
        print(f"{signal['signal'].upper()} Order Result:", res)

        time.sleep(30)
        profit = get_last_closed_trade_profit(SYMBOL)
        if profit != 0:
            risk_manager.update_pnl(profit)
            print(f"Updated daily PnL: ${risk_manager.day_pnl:.2f}")

    time.sleep(60)

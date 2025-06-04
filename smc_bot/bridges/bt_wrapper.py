import backtrader as bt
from smc.SMCStrategyCore import SMCStrategyCore

class SMCBacktraderWrapper(bt.Strategy):
    params = (
        ("lot_size", 0.02),
        ("look_back", 1),
        ("max_retests", 999),
        ("atr_thresh", 0.01),
        ("print_signals", True),
        ("trailing_atr_mult", 1.0),
        ("trade_start_hour", 0),
        ("trade_end_hour", 24),
    )

    def __init__(self):
        self.core = SMCStrategyCore(
            lot_size=self.p.lot_size,
            look_back=self.p.look_back,
            max_retests=self.p.max_retests,
            atr_thresh=self.p.atr_thresh,
            session_only=False,    # set True to restrict to main session
        )
        self.data_htf = self.datas[0]
        self.data_mtf = self.datas[1]
        self.data_ltf = self.datas[2]
        self.atr = bt.indicators.ATR(self.data_ltf, period=14)

        self.order = None
        self.entry_price = None
        self.sl = None
        self.target = None
        self.zone_type = None
        self.trades = []

    def notify_order(self, order):
        if order.status in [order.Completed]:
            trade_type = "buy" if order.isbuy() else "sell"
            self.trades.append({
                "datetime": self.data_ltf.datetime.datetime(0),
                "type": trade_type,
                "price": order.executed.price,
                "size": order.executed.size
            })
            self.entry_price = order.executed.price

    def next(self):
        dt = self.data_ltf.datetime.datetime(0)
        hour = dt.hour
        # You can override hour detection if your data is missing it

        def get_candles(data, length=50):
            # (open, high, low, close) as floats
            return [
               (data.datetime.datetime(-i), float(data.open[-i]), float(data.high[-i]), float(data.low[-i]), float(data.close[-i]))
        for i in reversed(range(length))
        ]
            
            

        candles_htf = get_candles(self.data_htf)
        candles_mtf = get_candles(self.data_mtf)
        candles_ltf = get_candles(self.data_ltf)
        atr_val = self.atr[0]

        signal = self.core.on_new_candles(
            candles_htf, candles_mtf, candles_ltf, atr_value=atr_val,
            atr_thresh=self.p.atr_thresh,
            valid_hours=(self.p.trade_start_hour, self.p.trade_end_hour),
            htf_source="htf",
            look_back=self.p.look_back,
            hour=hour
        )

        if self.p.print_signals:
            print(dt, signal)

        if not self.position:
            if signal["signal"] == "long":
                self.order = self.buy(size=1)
                self.entry_price = signal.get("entry", None)
                self.sl = signal.get("stop", None)
                self.target = signal.get("target", None)
                self.zone_type = signal.get("zone_type", None)
            elif signal["signal"] == "short":
                self.order = self.sell(size=1)
                self.entry_price = signal.get("entry", None)
                self.sl = signal.get("stop", None)
                self.target = signal.get("target", None)
                self.zone_type = signal.get("zone_type", None)
        else:
            # ATR trailing stop only (adjust if you want break-even, etc)
            if self.position.size > 0:
                new_stop = max(self.sl, self.data_ltf.close[0] - self.atr[0] * self.p.trailing_atr_mult)
                if new_stop > self.sl:
                    self.sl = new_stop
                if self.data_ltf.close[0] < self.sl:
                    self.close()
            elif self.position.size < 0:
                new_stop = min(self.sl, self.data_ltf.close[0] + self.atr[0] * self.p.trailing_atr_mult)
                if new_stop < self.sl:
                    self.sl = new_stop
                if self.data_ltf.close[0] > self.sl:
                    self.close()

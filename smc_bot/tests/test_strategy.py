from smc.strategy import SMCStrategyCore
from smc.detectors import Candle

def test_strategy_signal():
    # Fake 30m/15m uptrend, bullish 5m OB
    c_30 = [(1, 1.1, 0.9, 1.05), (1.05, 1.2, 1, 1.18), (1.18, 1.25, 1.15, 1.24)]
    c_15 = [(1, 1.1, 0.95, 1.06), (1.06, 1.16, 1.02, 1.13), (1.13, 1.22, 1.11, 1.20)]
    c_5 = [
        (10,11.5,9.5,11.2),   # green OB
        (11.2,11.3,8,8.5)
    ]
    strat = SMCStrategyCore()
    signal = strat.on_new_candles(c_30, c_15, c_5)
    assert signal["signal"] in ("long", "flat")

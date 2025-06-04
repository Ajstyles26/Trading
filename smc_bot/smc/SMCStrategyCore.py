
"""
Ultra-High-Frequency Smart Money Concept (SMC) Strategy Core

- Takes ANY SMC signal (Order Block, Fair Value Gap, Break of Structure, CHoCH)
- No session or ATR filter by default (set them to True to enable)
- High trade count, designed for robust statistical backtests and strategy discovery
"""

from smc.detectors import (
    detect_bos, detect_choch, detect_orderblock, detect_fvg, liquidity_sweep, Candle
)

class SMCStrategyCore:
    def __init__(self, lot_size=0.02, look_back=1, max_retests=999, atr_thresh=0.01, session_only=False):
        self.lot_size = lot_size
        self.look_back = look_back
        self.state = "flat"
        self.last_zone = None
        self.retest_count = 0
        self.max_retests = max_retests
        self.atr_thresh = atr_thresh
        self.session_only = session_only

    def get_htf_bias(self, htf_candles, look_back):
        # Loosest: Accept any bias or both sides (for more trades)
        if detect_bos(htf_candles, look_back):
            return "bull"
        if detect_choch(htf_candles, look_back):
            return "bear"
        return None  # or random.choice(["bull", "bear"]) for real chaos!

    def get_entry(self, candles_ltf, bias, htf_ok, atr_value, atr_thresh=0.01, asian_levels=None, hour=12):
        # Ultra-loose: ignore ATR/session unless forced
        if self.session_only and not (7 <= hour < 20):
            return {"signal": "flat"}
        if atr_value < atr_thresh:
            return {"signal": "flat"}

        # --- Trigger ALL SMC entries ---
        triggers = []
        ob_bull = detect_orderblock(candles_ltf, "bull")
        ob_bear = detect_orderblock(candles_ltf, "bear")
        fvg_bull = detect_fvg(candles_ltf)
        bos_bull = detect_bos(candles_ltf, self.look_back)
        choch_bear = detect_choch(candles_ltf, self.look_back)
        # Bulls
        if ob_bull:
            triggers.append("OB_bull")
        if fvg_bull and fvg_bull.get("side") == "bull":
            triggers.append("FVG_bull")
        if bos_bull:
            triggers.append("BOS")
        # Bears
        if ob_bear:
            triggers.append("OB_bear")
        if fvg_bull and fvg_bull.get("side") == "bear":
            triggers.append("FVG_bear")
        if choch_bear:
            triggers.append("CHoCH")

        if triggers:
            # Choose direction based on triggers present
            is_bull = any(t for t in triggers if "bull" in t or t == "BOS")
            is_bear = any(t for t in triggers if "bear" in t or t == "CHoCH")
            # If both present, take both directions (or prioritize bull for this example)
            if is_bull:
                direction = "long"
                entry = candles_ltf[-1][3]  # Close price
                # Use low of last 5 bars as stop
                stop = min([c[2] for c in candles_ltf[-5:]])
                target = entry + 1 * (entry - stop)
            elif is_bear:
                direction = "short"
                entry = candles_ltf[-1][3]
                # Use high of last 5 bars as stop
                stop = max([c[1] for c in candles_ltf[-5:]])
                target = entry - 1 * (stop - entry)
            else:
                # Failsafe: no clear direction
                return {"signal": "flat"}

            # Allow infinite retests for ultra-frequency (remove retest logic for max signals)
            return {
                "signal": direction,
                "entry": entry,
                "stop": stop,
                "target": target,
                "zone_type": ",".join(triggers)
            }
        return {"signal": "flat"}

    def on_new_candles(self, candles_htf, candles_mtf, candles_ltf, atr_value=1.0, atr_thresh=0.01,
                       valid_hours=(0, 24), htf_source="htf", look_back=1, asian_levels=None, hour=None):
        # Allow all hours if not restricting session
        if hour is None:
            hour = 12  # default noon if no hour info
        if self.session_only and not (valid_hours[0] <= hour < valid_hours[1]):
            return {"signal": "flat"}
        bias_htf = self.get_htf_bias(candles_htf, look_back)
        htf_ok = bias_htf is not None
        return self.get_entry(
            candles_ltf, bias_htf, htf_ok, atr_value, atr_thresh=atr_thresh, asian_levels=asian_levels, hour=hour
        )

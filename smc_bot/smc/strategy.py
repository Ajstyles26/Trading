# from smc.detectors import (
#     detect_bos, detect_choch, detect_orderblock, detect_fvg, liquidity_sweep,
#     Candle, session_high_low, premium_discount_zone
# )

# class SMCStrategyCore:
#     def __init__(self, lot_size=0.02, atr_mult=1.5, look_back=2, entry_combo="OB", max_retests=2, session_only=True):
#         self.lot_size = lot_size
#         self.atr_mult = atr_mult
#         self.look_back = look_back
#         self.entry_combo = entry_combo
#         self.max_retests = max_retests
#         self.session_only = session_only
#         self.state = "flat"
#         self.last_zone = None
#         self.retest_count = 0

#     def get_htf_bias(self, htf_candles, look_back):
#         if detect_bos(htf_candles, look_back):
#             return "bull"
#         if detect_choch(htf_candles, look_back):
#             return "bear"
#         return None

#     def price_retest_zone(self, last_close, zone):
#         return zone["lower"] <= last_close <= zone["upper"]

#     def get_entry(self, candles_ltf, bias, htf_ok, atr_value, atr_thresh=1.0, asian_levels=None, hour=12):
#         # 1. Session filter
#         if self.session_only and not (7 <= hour < 20):  # London/NY only
#             return {"signal": "flat"}
#         # 2. Premium/Discount: Buy in discount, sell in premium
#         hi, lo, eq = premium_discount_zone(candles_ltf[-50:])
#         last_close = candles_ltf[-1][3]
#         if (bias == "bull" and last_close > eq) or (bias == "bear" and last_close < eq):
#             return {"signal": "flat"}
#         # 3. ATR filter
#         if atr_value < atr_thresh:
#             return {"signal": "flat"}
#         # 4. Liquidity sweep (Asian session or swing sweep)
#         if not liquidity_sweep(candles_ltf, bias, window=30, asian_levels=asian_levels):
#             return {"signal": "flat"}
#         # 5. Entry zone: OB, FVG, or confluence
#         zone = None
#         if self.entry_combo == "OB":
#             ob = detect_orderblock(candles_ltf, bias)
#             if ob:
#                 idx, ob_open, ob_close = ob
#                 zone = {"type": "OB", "side": bias, "upper": max(ob_open, ob_close), "lower": min(ob_open, ob_close), "idx": idx}
#         elif self.entry_combo == "FVG":
#             fvg = detect_fvg(candles_ltf)
#             if fvg and fvg["side"] == bias:
#                 zone = {"type": "FVG", "side": bias, "upper": fvg["upper"], "lower": fvg["lower"], "idx": fvg["idx"]}
#         elif self.entry_combo == "OB+FVG":
#             ob = detect_orderblock(candles_ltf, bias)
#             fvg = detect_fvg(candles_ltf)
#             if ob and fvg and fvg["side"] == bias:
#                 zone = {"type": "OB+FVG", "side": bias, "upper": max(ob[1], fvg["upper"]), "lower": min(ob[2], fvg["lower"]), "idx": min(ob[0], fvg["idx"])}
#         if zone:
#             self.last_zone = zone
#             self.retest_count = 0
#         # 6. Retest logic
#         if self.last_zone and self.price_retest_zone(last_close, self.last_zone):
#             self.retest_count += 1
#             if self.retest_count > self.max_retests:
#                 self.last_zone = None
#                 return {"signal": "flat"}
#             entry = last_close
#             if bias == "bull":
#                 stop = self.last_zone["lower"]
#                 target = entry + 2 * (entry - stop)
#             else:
#                 stop = self.last_zone["upper"]
#                 target = entry - 2 * (stop - entry)
#             return {
#                 "signal": "long" if bias == "bull" else "short",
#                 "entry": entry, "stop": stop, "target": target,
#                 "zone_type": self.last_zone["type"]
#             }
#         return {"signal": "flat"}

#     def on_new_candles(self, candles_htf, candles_mtf, candles_ltf, atr_value=1.0, atr_thresh=1.0,
#                        valid_hours=(7, 20), htf_source="htf", look_back=2):
#         # -- Extract hour --
#         hour = None
#         if hasattr(candles_ltf[-1], "hour"):
#             hour = candles_ltf[-1].hour
#         elif len(candles_ltf[-1]) > 1 and isinstance(candles_ltf[-1][1], str):
#             try:
#                 hour = int(candles_ltf[-1][1].split(":")[0])
#             except Exception:
#                 hour = 12  # fallback
#         # -- Asian session high/low for liquidity --
#         asian_hi, asian_lo = session_high_low(candles_ltf[-200:], session="asia")
#         # -- HTF bias --
#         bias_htf = self.get_htf_bias(candles_htf, look_back)
#         htf_ok = bias_htf is not None
#         return self.get_entry(
#             candles_ltf, bias_htf, htf_ok, atr_value, atr_thresh=atr_thresh,
#             asian_levels=(asian_hi, asian_lo), hour=hour
#         )

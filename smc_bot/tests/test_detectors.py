from smc.detectors import (
    detect_bos, detect_choch, detect_orderblock,
    detect_fvg, liquidity_sweep, Candle
)

# --- Fixtures
def make_bos_sequence() -> list[Candle]:
    return [
        (1,1.1,0.9,1),(1,1.2,0.95,1.1),(1.1,1.25,1,1.2),
        (1.2,1.22,1.05,1.1),(1.1,1.18,1,1.05),(1.05,1.15,1.02,1.08),
        (1.08,1.30,1.07,1.28)
    ]

def make_choch_sequence() -> list[Candle]:
    return [
        (1.2,1.25,1.18,1.24),(1.24,1.26,1.22,1.25),(1.25,1.27,1.23,1.26),
        (1.26,1.24,1.20,1.22),(1.22,1.23,1.19,1.21),(1.21,1.22,1.18,1.19)
    ]

def make_ob_sequence() -> list[Candle]:
    return [
        (10,11.5,9.5,11.2),          # green candle (open 10, close 11.2)
        (11.2,11.3,8,8.5)            # big red dump → bearish OB at idx 0
    ]

def make_fvg_sequence() -> list[Candle]:
    return [
        (10,11,9,10.5),(10.5,11.2,9.8,10.8),(10.8,11.5,10.7,11.4),
        (11.4,12.5,11.6,12.0)
    ]

def make_liq_sequence() -> list[Candle]:
    seq = [(19,20,18,19.5)]*29
    seq.append((19.5,21,18,20.5))  # grab of prior high
    return seq

# --- Tests
def test_bos():   assert detect_bos(make_bos_sequence(), look_back=2)
def test_choch(): assert detect_choch(make_choch_sequence(), look_back=1)

def test_orderblock():
    ob = detect_orderblock(make_ob_sequence(), "bear")
    assert ob and ob[0] == 0 and ob[1] < ob[2]  # idx 0, green body

def test_fvg():
    gap = detect_fvg(make_fvg_sequence(), lookback=4)
    assert gap and gap["side"] == "bull"

def test_liquidity():
    assert liquidity_sweep(make_liq_sequence(), "bull", window=30)

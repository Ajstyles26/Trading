import backtrader as bt
import pandas as pd
from bridges.bt_wrapper import SMCBacktraderWrapper

symbols = [
    {
        "name": "EURUSD",
        "htf": "data/EURUSD_H1_bt.csv",
        "mtf": "data/EURUSD_M30_bt.csv",
        "ltf": "data/EURUSD_M15_bt.csv",
        "log": "trade_log_eurusd.csv",
        "htf_compr": 60, "mtf_compr": 30, "ltf_compr": 15,
    },
    {
        "name": "XAUUSD",
        "htf": "data/XAUUSD_30m_bt.csv",
        "mtf": "data/XAUUSD_15m_bt.csv",
        "ltf": "data/XAUUSD_5m_bt.csv",
        "log": "trade_log_xauusd.csv",
        "htf_compr": 30, "mtf_compr": 15, "ltf_compr": 5,
    },
]

results = []

for sym in symbols:
    print(f"\nRunning backtest for {sym['name']} ...")
    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(10000)
    cerebro.broker.setcommission(commission=0.0)

    data_htf = bt.feeds.GenericCSVData(
        dataname=sym["htf"],
        timeframe=bt.TimeFrame.Minutes,
        compression=sym["htf_compr"],
        dtformat="%Y.%m.%d",
        tmformat="%H:%M:%S",
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=-1,
        openinterest=-1,
        separator=','
    )
    data_mtf = bt.feeds.GenericCSVData(
        dataname=sym["mtf"],
        timeframe=bt.TimeFrame.Minutes,
        compression=sym["mtf_compr"],
        dtformat="%Y.%m.%d",
        tmformat="%H:%M:%S",
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=-1,
        openinterest=-1,
        separator=','
    )
    data_ltf = bt.feeds.GenericCSVData(
        dataname=sym["ltf"],
        timeframe=bt.TimeFrame.Minutes,
        compression=sym["ltf_compr"],
        dtformat="%Y.%m.%d",
        tmformat="%H:%M:%S",
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=-1,
        openinterest=-1,
        separator=','
    )

    cerebro.adddata(data_htf)
    cerebro.adddata(data_mtf)
    cerebro.adddata(data_ltf)

    # Loosen the filters for more signals, especially for EURUSD
    cerebro.addstrategy(
    SMCBacktraderWrapper,
    lot_size=0.02,
    look_back=2,
    max_retests=8,
    trailing_atr_mult=1.0,
    atr_thresh=0.3,
    print_signals=True
)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    results_list = cerebro.run()
    strat = results_list[0]
    analyzer = strat.analyzers.trades.get_analysis()

    # Defensive get (works with all bt versions)
    total_closed = analyzer.get('total', {}).get('closed', 0) if hasattr(analyzer, 'get') else getattr(analyzer.total, 'closed', 0)
    won = analyzer.get('won', {}).get('total', 0) if hasattr(analyzer, 'get') else getattr(analyzer.won, 'total', 0)
    lost = analyzer.get('lost', {}).get('total', 0) if hasattr(analyzer, 'get') else getattr(analyzer.lost, 'total', 0)
    win_rate = (won / total_closed) * 100 if total_closed else 0
    final_equity = cerebro.broker.getvalue()

    print(f"{sym['name']} - Final Portfolio Value: {final_equity:.2f}")
    print(f"{sym['name']} - Total trades: {total_closed}, Win rate: {win_rate:.2f} %")

    # Export trade log for each symbol
    trades = getattr(strat, 'trades', [])
    if trades:
        pd.DataFrame(trades).to_csv(sym["log"], index=False)
        print(f"Trade log exported as {sym['log']}")

    results.append({
        "Symbol": sym["name"],
        "Final Equity": final_equity,
        "Total Trades": total_closed,
        "Won": won,
        "Lost": lost,
        "Win Rate (%)": f"{win_rate:.2f}"
    })

# --- Output comparison table ---
print("\n=== PERFORMANCE COMPARISON ===")
df_results = pd.DataFrame(results)
print(df_results.to_string(index=False))
df_results.to_csv("performance_comparison.csv", index=False)
print("Comparison table exported as performance_comparison.csv")

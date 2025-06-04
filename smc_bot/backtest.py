import backtrader as bt
import pandas as pd
from bridges.bt_wrapper import SMCBacktraderWrapper

def run_backtest(optimize=False):
    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(10000)
    cerebro.broker.setcommission(commission=0.0)

    # -- Data feeds --
    data_htf = bt.feeds.GenericCSVData(
        dataname="data/EURUSD_H1_bt.csv",
        timeframe=bt.TimeFrame.Minutes,
        compression=60,
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
        dataname="data/EURUSD_M30_bt.csv",
        timeframe=bt.TimeFrame.Minutes,
        compression=30,
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
        dataname="data/EURUSD_M15_bt.csv",
        timeframe=bt.TimeFrame.Minutes,
        compression=15,
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

    # -- Strategy: optimize or run once --
    if optimize:
        cerebro.optstrategy(
            SMCBacktraderWrapper,
            lot_size=[0.02],
            look_back=[2, 3, 4],
            entry_combo=["OB", "FVG", "OB+LS", "OB+CHoCH"],
            max_retests=[1, 2, 999],
            trailing_atr_mult=[1.0, 1.5, 2.0],
            atr_thresh=[0.8, 1.0, 1.5],
            print_signals=[False]
        )
    else:
        cerebro.addstrategy(
            SMCBacktraderWrapper,
            lot_size=0.02,
            look_back=2,
            entry_combo="OB+LS",    # Change to test: "OB", "FVG", "OB+LS", "OB+CHoCH"
            max_retests=2,
            trailing_atr_mult=1.0,
            atr_thresh=1.0,
            print_signals=True
        )

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # -- Print win/loss, export trade log --
    reslist = results if optimize else [results]
    all_trades = []
    for run in reslist:
        strat = run[0] if isinstance(run, list) else run
        analyzer = strat.analyzers.trades.get_analysis()
        total_closed = analyzer.total.closed if hasattr(analyzer.total, 'closed') else 0
        won = analyzer.won.total if hasattr(analyzer.won, 'total') else 0
        lost = analyzer.lost.total if hasattr(analyzer.lost, 'total') else 0
        win_rate = (won / total_closed) * 100 if total_closed else 0

        print(f"\nTotal trades: {total_closed}")
        print(f"Won trades: {won}")
        print(f"Lost trades: {lost}")
        print(f"Win rate: {win_rate:.2f} %")

        # Export trade log
        all_trades.extend(getattr(strat, 'trades', []))
    if all_trades:
        df = pd.DataFrame(all_trades)
        df.to_csv("trade_log.csv", index=False)
        print("Trade log exported as trade_log.csv")

    try:
        cerebro.plot(style='candlestick', volume=False)
    except Exception as e:
        print("Plotting error (safe to ignore):", e)

if __name__ == "__main__":
    run_backtest(optimize=True)

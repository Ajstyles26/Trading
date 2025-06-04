import pandas as pd
import mplfinance as mpf

def plot_trades(price_csv, trade_csv, title):
    df = pd.read_csv(price_csv)
    df['Datetime'] = pd.to_datetime(df['DATE'] + ' ' + df['TIME'])
    df.set_index('Datetime', inplace=True)
    df = df[['OPEN', 'HIGH', 'LOW', 'CLOSE']].astype(float)
    df.columns = ['Open', 'High', 'Low', 'Close']

    trades = pd.read_csv(trade_csv)
    trades['Datetime'] = pd.to_datetime(trades['datetime'])
    trades = trades[trades['Datetime'].between(df.index.min(), df.index.max())]

    buy_idx, sell_idx = [], []
    for _, row in trades.iterrows():
        idx = df.index.get_indexer([row['Datetime']], method='nearest')[0]
        if row['type'] == 'buy':
            buy_idx.append(idx)
        elif row['type'] == 'sell':
            sell_idx.append(idx)

    apds = []
    if buy_idx:
        apds.append(mpf.make_addplot([row if i in buy_idx else None for i, row in enumerate(df['Low'])],
                                     type='scatter', markersize=80, marker='^', color='g'))
    if sell_idx:
        apds.append(mpf.make_addplot([row if i in sell_idx else None for i, row in enumerate(df['High'])],
                                     type='scatter', markersize=80, marker='v', color='r'))

    mpf.plot(
        df,
        type='candle',
        addplot=apds,
        style='yahoo',
        title=title,
        ylabel='Price',
        figsize=(18, 8),
        volume=False,
        show_nontrading=False
    )

# --------- Plot EURUSD -----------
plot_trades('data/EURUSD_M15_bt.csv', 'trade_log_eurusd.csv', 'EURUSD M15 SMC Bot')

# --------- Plot XAUUSD -----------
plot_trades('data/XAUUSD_M15_bt.csv', 'trade_log_xauusd.csv', 'XAUUSD M15 SMC Bot')

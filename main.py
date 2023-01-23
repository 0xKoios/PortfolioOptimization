import ccxt
import json
import pandas as pd
from riskfolio import HCPortfolio
from datetime import datetime


with open('config.json') as file:
    config = json.load(file)


def fetch_historical_candles():
    exchange = ccxt.binance()
    list_price_data = []
    for asset in config['assets']:
        symbol = asset + config['quote']
        historical_candles = exchange.fetch_ohlcv(symbol=symbol, timeframe='1d', limit=1000)
        df = pd.DataFrame(historical_candles, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = df['date'] / 1000
        df['date'] = pd.to_datetime(df['date'], unit='s')
        df['date'] = df['date'].dt.tz_localize('utc').dt.tz_convert('Asia/Bangkok')
        df['date'] = df['date'].dt.strftime('%Y-%d-%m')
        df.rename(columns={"close": asset}, inplace=True)
        df.drop(df.tail(1).index, inplace=True)
        df.set_index('date', inplace=True)
        list_price_data.append(df[asset])
    df = pd.concat(list_price_data, axis=1, sort=True)
    return df


def create_dataframe_price_index(df):
    list_price_index = []
    for sector in config['weights'].keys():
        # Create DataFrame Weight by sector
        weight = list(config['weights'][sector].values())
        index = config['weights'][sector].keys()
        df_weight = pd.DataFrame({'weight': weight}, index=index)

        # Calculate DataFrame Price by sector
        price = df_weight.T.values * df[df_weight.T.columns].values
        columns = df_weight.T.columns
        df_sector_price = pd.DataFrame(price, columns=columns)
        df[sector] = df_sector_price.sum(axis=1).to_list()
        list_price_index.append(df[[sector]])
    df_price_index = pd.concat(list_price_index, axis=1, sort=True)
    return df_price_index


def hierarchical_risk_parity(df_price_index):
    returns_from_prices = df_price_index.pct_change().dropna(how="all")
    port = HCPortfolio(returns_from_prices)
    # Estimate optimal portfolio:
    model = 'HRP'  # Could be HRP or HERC
    correlation = 'pearson'  # Correlation matrix used to group assets in clusters
    rm = 'MV'  # Risk measure used, this time will be variance
    rf = 0  # Risk-free rate
    linkage = 'single'  # Linkage method used to build clusters
    max_k = 10  # Max number of clusters used in two difference gap statistic
    leaf_order = True  # Consider optimal order of leafs in dendrogram
    weights = port.optimization(
        model=model,
        correlation=correlation,
        rm=rm,
        rf=rf,
        linkage=linkage,
        max_k=max_k,
        leaf_order=False
    )
    weights = weights.sort_values(by="weights", ascending=False, axis=0)
    return weights


def main():
    df = fetch_historical_candles()
    df.dropna(inplace=True)
    df_price_index = create_dataframe_price_index(df)
    hrp_weights = hierarchical_risk_parity(df_price_index)
    list_weights_df = []
    for sector in config['weights'].keys():
        weight = list(config['weights'][sector].values())
        index = config['weights'][sector].keys()
        df_weight_sector = pd.DataFrame({'weight': weight}, index=index)
        list_weights_df.append(df_weight_sector['weight'] * hrp_weights.T[sector]['weights'])
    df_weights = pd.concat(list_weights_df, axis=0).T.to_frame()
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df_weights.to_csv(f'weights/{date}.csv')


if __name__ == '__main__':
    main()

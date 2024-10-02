import yfinance as yf
from Ashare import get_price
import pandas as pd
import datetime
import numpy as np

def get_us_stock_data(ticker, start_date, end_date):
    """
    获取美股数据
    :param ticker: 股票代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: DataFrame 包含股票数据
    """
    try:
        ticker_data = yf.Ticker(ticker)
        ticker_df = ticker_data.history(period='1d', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        ticker_df.reset_index(inplace=True)
        ticker_df.rename(columns={'Date': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        ticker_df.set_index('time', inplace=True)
        return ticker_df
    except Exception as e:
        print(f"获取美股数据时发生错误: {str(e)}")
        return None

def get_cn_stock_data(code, end_date, count):
    """
    获取A股数据
    :param code: 股票代码
    :param end_date: 结束日期
    :param count: 获取的天数
    :return: DataFrame 包含股票数据
    """
    try:
        df = get_price(code, end_date=end_date.strftime('%Y-%m-%d'), count=count, frequency='1d')
        return df
    except Exception as e:
        print(f"获取A股数据时发生错误: {str(e)}")
        return None

def get_stock_data(stock_code, is_us_stock, months_back):
    """
    根据股票代码和市场类型获取股票数据
    :param stock_code: 股票代码
    :param is_us_stock: 是否为美股
    :param months_back: 回溯的月数
    :return: DataFrame 包含股票数据
    """
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30*months_back)
    
    if is_us_stock:
        return get_us_stock_data(stock_code, start_date, end_date)
    else:
        return get_cn_stock_data(stock_code, end_date, months_back*30)

def analyze_stock_data(df, short_window, long_window, initial_investment):
    """
    分析股票数据
    :param df: DataFrame 包含股票数据
    :param short_window: 短期移动平均线窗口
    :param long_window: 长期移动平均线窗口
    :param initial_investment: 初始投资金额
    :return: DataFrame 包含分析结果
    """
    df['Short_MA'] = df['close'].rolling(window=short_window).mean()
    df['Long_MA'] = df['close'].rolling(window=long_window).mean()

    # 计算移动平均线的斜率
    df['Short_MA_Slope'] = df['Short_MA'].diff()
    df['Long_MA_Slope'] = df['Long_MA'].diff()

    df['Signal'] = 0
    df['Signal'][short_window:] = np.where(df['Short_MA'][short_window:] > df['Long_MA'][short_window:], 1, 0)
    df['Position'] = df['Signal'].diff()

    df['Quantity'] = 0
    df['Cash'] = initial_investment
    df['Holdings'] = 0

    for i in range(1, len(df)):
        # 定义基础数量和交易数量限制
        base_quantity = df['Cash'].iloc[i-1] // df['close'].iloc[i]
        min_quantity = max(1, int(base_quantity * 0.1))  # 最小交易数量设为基本数量的10%
        max_quantity = min(int(base_quantity * 1.5), base_quantity)  # 最大交易数量设为基本数量的150%

        if df['Position'].iloc[i] == 1:  # Buy signal
            # 根据斜率调整交易数量
            short_slope = df['Short_MA_Slope'].iloc[i]
            long_slope = df['Long_MA_Slope'].iloc[i]
            if pd.notna(short_slope) and pd.notna(long_slope) and long_slope != 0:
                trend_strength = short_slope / long_slope
                if trend_strength > 0:
                    quantity_to_buy = int(base_quantity * min(trend_strength, 1))  # 确保趋势强度不超过1
                    quantity_to_buy = max(min(quantity_to_buy, max_quantity), min_quantity)  # 确保交易数量在范围内
                else:
                    quantity_to_buy = min_quantity  # 如果趋势强度<=0，设置为最小交易数量
            else:
                quantity_to_buy = min_quantity  # 如果斜率计算异常，设置为最小交易数量
            
            df['Quantity'].iloc[i] = quantity_to_buy
            df['Cash'].iloc[i] = df['Cash'].iloc[i-1] - quantity_to_buy * df['close'].iloc[i]
            df['Holdings'].iloc[i] = df['Holdings'].iloc[i-1] + quantity_to_buy
        elif df['Position'].iloc[i] == -1:  # Sell signal
            quantity_to_sell = df['Holdings'].iloc[i-1]
            df['Quantity'].iloc[i] = -quantity_to_sell
            df['Cash'].iloc[i] = df['Cash'].iloc[i-1] + quantity_to_sell * df['close'].iloc[i]
            df['Holdings'].iloc[i] = 0
        else:
            df['Cash'].iloc[i] = df['Cash'].iloc[i-1]
            df['Holdings'].iloc[i] = df['Holdings'].iloc[i-1]

    df['Total Value'] = df['Cash'] + df['Holdings'] * df['close']
    
    return df
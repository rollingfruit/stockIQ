import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import json
from fuzzywuzzy import process
from stock_data_api import get_stock_data, analyze_stock_data

# 加载股票数据
with open('./stocks_chinese_comp/Ashare.json', 'r', encoding='utf-8') as f:
    cn_stock_dict = json.load(f)

with open('./stocks_chinese_comp/USshare.json', 'r', encoding='utf-8') as f:
    us_stock_dict = json.load(f)

# 界面初始化
st.write("# 股票量化分析看板")
st.write("这个应用程序通过量化分析来验证投资选择。")

# 用户交互
st.sidebar.header("参数设置")

# 选择股票市场
market = st.sidebar.radio("选择股票市场", ["美股", "A股"])

# 统一的股票选择逻辑
def select_stock(stock_dict):
    search_term = st.sidebar.text_input("搜索股票", "")
    if search_term:
        matches = process.extract(search_term, stock_dict.values(), limit=5)
        selected_stock_name = st.sidebar.selectbox("选择股票", [m[0] for m in matches])
        selected_stock = [k for k, v in stock_dict.items() if v == selected_stock_name][0]
    else:
        selected_stock = st.sidebar.selectbox("选择股票", list(stock_dict.keys()), format_func=lambda x: stock_dict[x])
    return selected_stock, stock_dict[selected_stock]

if market == "美股":
    selected_stock, stock_name = select_stock(us_stock_dict)
    is_us_stock = True
else:
    selected_stock, stock_name = select_stock(cn_stock_dict)
    is_us_stock = False

months_back = st.sidebar.slider("回顾月数", 1, 100, 12)
short_window = st.sidebar.slider("短期移动平均线窗口", 5, 50, 20)
long_window = st.sidebar.slider("长期移动平均线窗口", 50, 200, 100)
initial_investment = 10000

# 股票数据获取
df = get_stock_data(selected_stock, is_us_stock, months_back)

if df is not None:
    # 分析股票数据
    df = analyze_stock_data(df, short_window, long_window, initial_investment)

    # 绘图
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                        subplot_titles=(f"{stock_name}股价和移动平均线", "投资组合价值"), 
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=df.index, y=df['close'], name="收盘价"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Short_MA'], name=f"{short_window}日均线"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Long_MA'], name=f"{long_window}日均线"), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['Total Value'], name="投资组合总值"), row=2, col=1)

    fig.update_layout(height=800, title_text=f"{stock_name}股票分析图表")
    st.plotly_chart(fig, use_container_width=True)

    # 买卖时机展示
    trade_signals = df[(df['Position'] != 0) & (df['Quantity'] != 0)].copy()
    trade_signals['交易类型'] = trade_signals['Position'].map({1: '买入', -1: '卖出'})
    trade_signals['交易价格'] = trade_signals['close']
    trade_signals['交易数量'] = trade_signals['Quantity'].abs()

    st.write("## 交易信号汇总")
    st.table(trade_signals[['交易类型', '交易价格', '交易数量']])

    # 最终回报计算
    final_value = df['Total Value'].iloc[-1]
    total_return = (final_value - initial_investment) / initial_investment * 100

    st.write(f"## 投资回报")
    st.write(f"初始投资: ${initial_investment:.2f}")
    st.write(f"最终价值: ${final_value:.2f}")
    st.write(f"总回报率: {total_return:.2f}%")

else:
    st.error("无法获取股票数据，请检查股票代码或网络连接。")
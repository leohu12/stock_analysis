# -*- coding: utf-8 -*-
"""
K线图可视化模块
使用 mplfinance 生成专业K线图
支持：
- 日K线图（含均线、成交量、MACD副图）
- 保存为 PNG 图片
- 命令行一键导出

安装依赖:
    pip install mplfinance matplotlib
"""

import os
import pandas as pd
from datetime import datetime


def _prepare_kline_data(kline_df):
    """
    将K线数据格式化为 mplfinance 需要的格式
    mplfinance 需要列名: Open, High, Low, Close, Volume
    索引为日期
    """
    df = kline_df.copy()

    # 标准化列名
    col_map = {
        "开盘": "Open", "open": "Open",
        "最高": "High", "high": "High",
        "最低": "Low", "low": "Low",
        "收盘": "Close", "close": "Close",
        "成交量": "Volume", "volume": "Volume",
    }
    for old, new in col_map.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    # 确保有日期索引
    if "日期" in df.columns:
        df["Date"] = pd.to_datetime(df["日期"])
        df.set_index("Date", inplace=True)
    elif "date" in df.columns:
        df["Date"] = pd.to_datetime(df["date"])
        df.set_index("Date", inplace=True)

    # 确保必要列存在
    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"缺少必要列: {col}")

    return df[required + [c for c in df.columns if c not in required]]


def plot_kline(kline_df, stock_code="", stock_name="", save_path=None, show=False,
               ma_periods=(5, 10, 20, 60), add_macd=True, add_volume=True,
               style="binance", figsize=(14, 10)):
    """
    绘制K线图并保存/显示

    参数:
        kline_df: K线DataFrame
        stock_code: 股票代码
        stock_name: 股票名称
        save_path: 保存路径 (如 'chart.png')，None则自动命名
        show: 是否显示图表 (命令行模式下建议 False)
        ma_periods: 要显示的均线周期
        add_macd: 是否添加MACD副图
        add_volume: 是否添加成交量副图
        style: 图表风格 ('binance', 'yahoo', 'charles', 'mike')
        figsize: 图片尺寸

    返回:
        save_path: 实际保存的路径
    """
    try:
        import mplfinance as mpf
    except ImportError:
        print("[Chart] 缺少 mplfinance，请运行: pip install mplfinance")
        return None

    df = _prepare_kline_data(kline_df)

    # 只取最近的数据绘制（避免图表太密集）
    plot_df = df.tail(120)  # 默认显示最近120根K线

    # 计算均线
    adds = []
    ma_colors = ['orange', 'blue', 'purple', 'red']
    for i, p in enumerate(ma_periods):
        if len(plot_df) >= p:
            plot_df[f"MA{p}"] = plot_df["Close"].rolling(window=p).mean()
            adds.append(mpf.make_addplot(plot_df[f"MA{p}"], color=ma_colors[i % len(ma_colors)], width=0.8))

    # 构建面板配置
    panels = []
    panel_ratios = [3]  # K线主图占比

    # 成交量面板
    if add_volume:
        panels.append("volume")
        panel_ratios.append(1)

    # MACD面板
    if add_macd and len(plot_df) >= 26:
        exp1 = plot_df["Close"].ewm(span=12, adjust=False).mean()
        exp2 = plot_df["Close"].ewm(span=26, adjust=False).mean()
        plot_df["DIF"] = exp1 - exp2
        plot_df["DEA"] = plot_df["DIF"].ewm(span=9, adjust=False).mean()
        plot_df["MACD"] = 2 * (plot_df["DIF"] - plot_df["DEA"])

        adds.append(mpf.make_addplot(plot_df["DIF"], panel=len(panel_ratios), color="blue", width=0.8))
        adds.append(mpf.make_addplot(plot_df["DEA"], panel=len(panel_ratios), color="orange", width=0.8))
        adds.append(mpf.make_addplot(plot_df["MACD"], type="bar", panel=len(panel_ratios),
                                     color="dimgray", alpha=0.5, width=0.8))
        panels.append(None)
        panel_ratios.append(1)

    # 标题
    title = f"{stock_name} ({stock_code})" if stock_name else (stock_code or "K线图")

    # 自动保存路径
    if save_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        code_str = stock_code if stock_code else "stock"
        save_path = f"{code_str}_kline_{timestamp}.png"

    # 确保目录存在
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)

    # 绘图
    kwargs = {
        "type": "candle",
        "style": style,
        "title": title,
        "ylabel": "价格",
        "volume": add_volume,
        "addplot": adds,
        "figscale": 1.2,
        "figsize": figsize,
        "savefig": save_path,
    }

    if panels:
        kwargs["panel_ratios"] = panel_ratios

    mpf.plot(plot_df, **kwargs)

    if show:
        mpf.show()

    return os.path.abspath(save_path)


def plot_kline_simple(kline_df, stock_code="", save_dir="."):
    """
    简化版K线图绘制（一键保存）
    返回保存的文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(save_dir, f"{stock_code}_kline_{timestamp}.png")
    return plot_kline(kline_df, stock_code=stock_code, save_path=save_path, show=False)

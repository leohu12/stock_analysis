# -*- coding: utf-8 -*-
"""
技术指标计算模块
纯Python实现，无需TA-Lib，兼容通达信/同花顺算法
"""

import pandas as pd
import numpy as np


def calc_ma(df, periods=[5, 10, 20, 30, 60, 120, 250]):
    """计算移动平均线"""
    for p in periods:
        df[f"MA{p}"] = df["收盘"].rolling(window=p).mean().round(2)
    return df


def calc_ema(series, span):
    """计算指数移动平均"""
    return series.ewm(span=span, adjust=False).mean()


def calc_macd(df, fast=12, slow=26, signal=9):
    """
    计算MACD指标
    DIF = EMA12 - EMA26
    DEA = EMA(DIF, 9)
    MACD = 2 * (DIF - DEA)
    """
    close = df["收盘"]
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    df["DIF"] = (ema_fast - ema_slow).round(3)
    df["DEA"] = calc_ema(df["DIF"], signal).round(3)
    df["MACD"] = (2 * (df["DIF"] - df["DEA"])).round(3)
    return df


def calc_kdj(df, n=9, m1=3, m2=3):
    """
    计算KDJ指标
    RSV = (C - Ln) / (Hn - Ln) * 100
    K = SMA(RSV, m1)
    D = SMA(K, m2)
    J = 3K - 2D
    """
    low_list = df["最低"].rolling(window=n, min_periods=1).min()
    high_list = df["最高"].rolling(window=n, min_periods=1).max()
    rsv = (df["收盘"] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50)

    # SMA算法: SMA(X, N, M) = (M*X + (N-M)*Y') / N
    k_values = []
    d_values = []
    k = 50.0
    d = 50.0
    for r in rsv:
        k = (m1 * r + (n - m1) * k) / n
        d = (m2 * k + (n - m2) * d) / n
        k_values.append(round(k, 2))
        d_values.append(round(d, 2))

    df["K"] = k_values
    df["D"] = d_values
    df["J"] = (3 * df["K"] - 2 * df["D"]).round(2)
    return df


def calc_rsi(df, periods=[6, 12, 24]):
    """
    计算RSI指标
    RSI = SMA(MAX(C-C', 0), N, 1) / SMA(ABS(C-C'), N, 1) * 100
    """
    close = df["收盘"]
    delta = close.diff()

    for p in periods:
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1.0 / p, min_periods=p, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / p, min_periods=p, adjust=False).mean()

        rs = avg_gain / avg_loss
        df[f"RSI{p}"] = (100 - 100 / (1 + rs)).round(2)

    return df


def calc_boll(df, period=20, std_mult=2):
    """
    计算布林带指标
    MID = MA(C, 20)
    UPPER = MID + 2*STD
    LOWER = MID - 2*STD
    """
    df["BOLL_MID"] = df["收盘"].rolling(window=period).mean().round(2)
    std = df["收盘"].rolling(window=period).std()
    df["BOLL_UP"] = (df["BOLL_MID"] + std_mult * std).round(2)
    df["BOLL_LOW"] = (df["BOLL_MID"] - std_mult * std).round(2)
    return df


def calc_vol_ma(df, periods=[5, 10]):
    """计算成交量均线"""
    for p in periods:
        df[f"VOL_MA{p}"] = df["成交量"].rolling(window=p).mean().round(0)
    return df


def calc_wr(df, n=14):
    """
    计算威廉指标 WR
    WR = (HHV(H, N) - C) / (HHV(H, N) - LLV(L, N)) * 100
    """
    hhv = df["最高"].rolling(window=n).max()
    llv = df["最低"].rolling(window=n).min()
    df["WR"] = ((hhv - df["收盘"]) / (hhv - llv) * 100).round(2)
    return df


def calc_cci(df, n=14):
    """
    计算CCI指标
    TP = (H + L + C) / 3
    CCI = (TP - MA(TP, N)) / (0.015 * AVEDEV(TP, N))
    """
    tp = (df["最高"] + df["最低"] + df["收盘"]) / 3
    ma_tp = tp.rolling(window=n).mean()
    # 平均绝对偏差
    mad = tp.rolling(window=n).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df["CCI"] = ((tp - ma_tp) / (0.015 * mad)).round(2)
    return df


def calc_obv(df):
    """
    计算OBV能量潮指标
    """
    obv = [0]
    for i in range(1, len(df)):
        if df["收盘"].iloc[i] > df["收盘"].iloc[i - 1]:
            obv.append(obv[-1] + df["成交量"].iloc[i])
        elif df["收盘"].iloc[i] < df["收盘"].iloc[i - 1]:
            obv.append(obv[-1] - df["成交量"].iloc[i])
        else:
            obv.append(obv[-1])
    df["OBV"] = obv
    df["OBV_MA"] = pd.Series(obv).rolling(window=20).mean().values
    return df


def calc_atr(df, n=14):
    """
    计算ATR真实波幅
    TR = MAX(H-L, |H-C'|, |L-C'|)
    ATR = MA(TR, N)
    """
    high = df["最高"]
    low = df["最低"]
    close = df["收盘"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["TR"] = tr
    df["ATR"] = tr.rolling(window=n).mean().round(2)
    return df


def calc_supertrend(df, period=10, multiplier=3):
    """
    计算SuperTrend指标
    """
    hl2 = (df["最高"] + df["最低"]) / 2
    atr = df["ATR"] if "ATR" in df.columns else calc_atr(df, period)["ATR"]

    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    supertrend = [True]  # True = 上涨趋势
    first_lb = lower_band.iloc[0]
    st_values = [first_lb if pd.notna(first_lb) else hl2.iloc[0]]

    for i in range(1, len(df)):
        atr_val = atr.iloc[i]
        if pd.isna(atr_val) or atr_val == 0:
            supertrend.append(supertrend[-1])
            st_values.append(st_values[-1])
            continue
        lb = lower_band.iloc[i]
        ub = upper_band.iloc[i]
        if pd.isna(lb) or pd.isna(ub):
            supertrend.append(supertrend[-1])
            st_values.append(st_values[-1])
            continue
        if supertrend[-1]:
            st = max(lb, st_values[-1]) if lb > st_values[-1] else st_values[-1]
            if df["收盘"].iloc[i] < st:
                supertrend.append(False)
                st_values.append(ub)
            else:
                supertrend.append(True)
                st_values.append(st)
        else:
            st = min(ub, st_values[-1]) if ub < st_values[-1] else st_values[-1]
            if df["收盘"].iloc[i] > st:
                supertrend.append(True)
                st_values.append(lb)
            else:
                supertrend.append(False)
                st_values.append(st)

    df["ST"] = st_values
    df["ST_Dir"] = supertrend  # True=多头, False=空头
    return df


def calc_all_indicators(df):
    """计算所有技术指标"""
    df = calc_ma(df)
    df = calc_macd(df)
    df = calc_kdj(df)
    df = calc_rsi(df)
    df = calc_boll(df)
    df = calc_vol_ma(df)
    df = calc_wr(df)
    df = calc_cci(df)
    df = calc_obv(df)
    df = calc_atr(df)
    df = calc_supertrend(df)
    return df


# ==================== 买卖信号判断 ====================

def analyze_signals(df):
    """
    综合分析买卖信号
    返回每行的信号列表
    """
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]
        row_signals = []

        # MACD信号
        if i >= 1:
            prev = df.iloc[i - 1]
            if prev["DIF"] <= prev["DEA"] and row["DIF"] > row["DEA"]:
                row_signals.append("🟢 MACD金叉")
            elif prev["DIF"] >= prev["DEA"] and row["DIF"] < row["DEA"]:
                row_signals.append("🔴 MACD死叉")
            if row["MACD"] > 0 and prev["MACD"] <= 0:
                row_signals.append("🟢 MACD红柱")
            elif row["MACD"] < 0 and prev["MACD"] >= 0:
                row_signals.append("🔴 MACD绿柱")

        # KDJ信号
        if pd.notna(row["K"]) and pd.notna(row["D"]):
            if i >= 1:
                prev = df.iloc[i - 1]
                if prev["K"] <= prev["D"] and row["K"] > row["D"]:
                    row_signals.append("🟢 KDJ金叉")
                elif prev["K"] >= prev["D"] and row["K"] < row["D"]:
                    row_signals.append("🔴 KDJ死叉")
            if row["K"] < 20 and row["D"] < 20:
                row_signals.append("🟢 KDJ超卖")
            elif row["K"] > 80 and row["D"] > 80:
                row_signals.append("🔴 KDJ超买")

        # RSI信号
        if "RSI6" in df.columns and pd.notna(row.get("RSI6")):
            if row["RSI6"] < 20:
                row_signals.append("🟢 RSI6超卖")
            elif row["RSI6"] > 80:
                row_signals.append("🔴 RSI6超买")

        # 布林带信号
        if pd.notna(row.get("BOLL_LOW")) and pd.notna(row.get("BOLL_UP")):
            if row["收盘"] <= row["BOLL_LOW"]:
                row_signals.append("🟢 触及布林下轨")
            elif row["收盘"] >= row["BOLL_UP"]:
                row_signals.append("🔴 触及布林上轨")

        # WR信号
        if pd.notna(row.get("WR")):
            if row["WR"] < 20:
                row_signals.append("🔴 WR超买")
            elif row["WR"] > 80:
                row_signals.append("🟢 WR超卖")

        # CCI信号
        if pd.notna(row.get("CCI")):
            if row["CCI"] > 100:
                row_signals.append("🔴 CCI超买")
            elif row["CCI"] < -100:
                row_signals.append("🟢 CCI超卖")

        # SuperTrend信号
        if "ST_Dir" in df.columns:
            if i >= 1 and df.iloc[i - 1]["ST_Dir"] != row["ST_Dir"]:
                if row["ST_Dir"]:
                    row_signals.append("🟢 SuperTrend转多")
                else:
                    row_signals.append("🔴 SuperTrend转空")

        # 均线信号
        if pd.notna(row.get("MA5")) and pd.notna(row.get("MA20")):
            if row["MA5"] > row["MA10"] > row["MA20"] > row["MA30"] if pd.notna(row.get("MA10")) and pd.notna(row.get("MA30")) else False:
                row_signals.append("🟢 均线多头排列")
            elif row["MA5"] < row["MA10"] < row["MA20"] < row["MA30"] if pd.notna(row.get("MA10")) and pd.notna(row.get("MA30")) else False:
                row_signals.append("🔴 均线空头排列")

        # 放量信号
        if pd.notna(row.get("VOL_MA5")):
            if row["成交量"] > row["VOL_MA5"] * 2:
                if row["涨跌幅"] > 0:
                    row_signals.append("🟢 放量大涨")
                else:
                    row_signals.append("🔴 放量大跌")

        signals.append(row_signals)

    df["信号"] = signals
    return df


def generate_analysis_summary(df):
    """生成综合分析摘要"""
    if df.empty:
        return "无数据"

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    summary_parts = []

    # 趋势判断
    if pd.notna(latest.get("MA5")) and pd.notna(latest.get("MA20")):
        if latest["MA5"] > latest["MA20"]:
            summary_parts.append("📈 短期趋势偏多")
        else:
            summary_parts.append("📉 短期趋势偏空")

    if pd.notna(latest.get("MA60")):
        if latest["收盘"] > latest["MA60"]:
            summary_parts.append("📈 中期趋势偏多")
        else:
            summary_parts.append("📉 中期趋势偏空")

    # MACD判断
    if pd.notna(latest.get("DIF")) and pd.notna(latest.get("DEA")):
        if latest["DIF"] > latest["DEA"] and latest["DIF"] > 0:
            summary_parts.append("💪 MACD多头强势")
        elif latest["DIF"] > latest["DEA"]:
            summary_parts.append("🔄 MACD多头弱势")
        elif latest["DIF"] < latest["DEA"] and latest["DIF"] < 0:
            summary_parts.append("⚠️ MACD空头强势")
        else:
            summary_parts.append("🔄 MACD空头弱势")

    # KDJ判断
    if pd.notna(latest.get("K")) and pd.notna(latest.get("D")):
        if latest["K"] > 80:
            summary_parts.append("⚠️ KDJ高位超买区")
        elif latest["K"] < 20:
            summary_parts.append("💡 KDJ低位超卖区")
        if latest["K"] > latest["D"]:
            summary_parts.append("🟢 KDJ多头")
        else:
            summary_parts.append("🔴 KDJ空头")

    # RSI判断
    if pd.notna(latest.get("RSI6")):
        if latest["RSI6"] > 80:
            summary_parts.append("⚠️ RSI严重超买")
        elif latest["RSI6"] > 70:
            summary_parts.append("⚠️ RSI超买")
        elif latest["RSI6"] < 20:
            summary_parts.append("💡 RSI严重超卖")
        elif latest["RSI6"] < 30:
            summary_parts.append("💡 RSI超卖")

    # 布林带判断
    if pd.notna(latest.get("BOLL_MID")):
        boll_pos = (latest["收盘"] - latest["BOLL_LOW"]) / (latest["BOLL_UP"] - latest["BOLL_LOW"]) * 100
        if boll_pos > 90:
            summary_parts.append("⚠️ 布林带上轨附近")
        elif boll_pos < 10:
            summary_parts.append("💡 布林带下轨附近")
        else:
            summary_parts.append(f"📊 布林带位置: {boll_pos:.0f}%")

    # 统计最近信号
    recent_signals = latest.get("信号", [])
    buy_signals = sum(1 for s in recent_signals if "🟢" in s)
    sell_signals = sum(1 for s in recent_signals if "🔴" in s)

    if buy_signals >= 3:
        summary_parts.append(f"🚀 多重买入信号({buy_signals}个)")
    elif sell_signals >= 3:
        summary_parts.append(f"⛔ 多重卖出信号({sell_signals}个)")

    return "\n".join(summary_parts)

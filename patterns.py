# -*- coding: utf-8 -*-
"""
K线形态识别模块
识别经典K线形态，生成买卖信号
"""

import pandas as pd
import numpy as np


def identify_patterns(df):
    """识别K线形态"""
    patterns = []
    for i in range(len(df)):
        row_patterns = []

        if i >= 2:
            # 锤子线
            if _is_hammer(df, i):
                row_patterns.append("🔨 锤子线(看涨)")
            # 倒锤子线
            if _is_inverted_hammer(df, i):
                row_patterns.append("🔨 倒锤子线(看涨)")
            # 吞没形态
            if _is_engulfing(df, i):
                row_patterns.append("🔥 吞没形态")
            # 十字星
            if _is_doji(df, i):
                row_patterns.append("✝️ 十字星(变盘)")
            # 早晨之星
            if _is_morning_star(df, i):
                row_patterns.append("🌅 早晨之星(强烈看涨)")
            # 黄昏之星
            if _is_evening_star(df, i):
                row_patterns.append("🌇 黄昏之星(强烈看跌)")
            # 三只乌鸦
            if _is_three_black_crows(df, i):
                row_patterns.append("🐦 三只乌鸦(看跌)")
            # 三个白兵
            if _is_three_white_soldiers(df, i):
                row_patterns.append("⚔️ 三个白兵(看涨)")
            # 射击之星
            if _is_shooting_star(df, i):
                row_patterns.append("⭐ 射击之星(看跌)")
            # 上吊线
            if _is_hanging_man(df, i):
                row_patterns.append("💀 上吊线(看跌)")
            # 红三兵
            if _is_red_three_soldiers(df, i):
                row_patterns.append("🔴 红三兵(看涨)")
            # 乌云盖顶
            if _is_dark_cloud_cover(df, i):
                row_patterns.append("☁️ 乌云盖顶(看跌)")
            # 刺透形态
            if _is_piercing_pattern(df, i):
                row_patterns.append("🗡️ 刺透形态(看涨)")
            # 孕线形态
            if _is_harami(df, i):
                row_patterns.append("🤰 孕线(变盘)")

        patterns.append(row_patterns)

    df["K线形态"] = patterns
    return df


def _body_size(df, i):
    """实体大小"""
    return abs(df["收盘"].iloc[i] - df["开盘"].iloc[i])


def _upper_shadow(df, i):
    """上影线"""
    return df["最高"].iloc[i] - max(df["收盘"].iloc[i], df["开盘"].iloc[i])


def _lower_shadow(df, i):
    """下影线"""
    return min(df["收盘"].iloc[i], df["开盘"].iloc[i]) - df["最低"].iloc[i]


def _is_bullish(df, i):
    return df["收盘"].iloc[i] > df["开盘"].iloc[i]


def _is_bearish(df, i):
    return df["收盘"].iloc[i] < df["开盘"].iloc[i]


def _is_hammer(df, i):
    """锤子线：小实体+长下影线+短上影线，在下跌趋势中出现"""
    body = _body_size(df, i)
    lower = _lower_shadow(df, i)
    upper = _upper_shadow(df, i)
    total = df["最高"].iloc[i] - df["最低"].iloc[i]
    if total == 0:
        return False
    return lower >= body * 2 and upper <= body * 0.5 and body > 0


def _is_inverted_hammer(df, i):
    """倒锤子线"""
    body = _body_size(df, i)
    upper = _upper_shadow(df, i)
    lower = _lower_shadow(df, i)
    total = df["最高"].iloc[i] - df["最低"].iloc[i]
    if total == 0:
        return False
    return upper >= body * 2 and lower <= body * 0.5 and body > 0


def _is_engulfing(df, i):
    """吞没形态"""
    prev_body = _body_size(df, i - 1)
    curr_body = _body_size(df, i)
    if prev_body == 0 or curr_body == 0:
        return False
    prev_bull = _is_bullish(df, i - 1)
    curr_bull = _is_bullish(df, i)
    if prev_bull and not curr_bull:
        # 看跌吞没
        return (df["开盘"].iloc[i] > df["收盘"].iloc[i - 1] and
                df["收盘"].iloc[i] < df["开盘"].iloc[i - 1])
    elif not prev_bull and curr_bull:
        # 看涨吞没
        return (df["开盘"].iloc[i] < df["收盘"].iloc[i - 1] and
                df["收盘"].iloc[i] > df["开盘"].iloc[i - 1])
    return False


def _is_doji(df, i):
    """十字星"""
    body = _body_size(df, i)
    total = df["最高"].iloc[i] - df["最低"].iloc[i]
    if total == 0:
        return False
    return body / total < 0.05


def _is_morning_star(df, i):
    """早晨之星：大跌+小实体+大涨"""
    if i < 2:
        return False
    first_bear = _is_bearish(df, i - 2) and (df["收盘"].iloc[i - 2] - df["开盘"].iloc[i - 2]) < -0.01 * df["开盘"].iloc[i - 2]
    second_small = _body_size(df, i - 1) < _body_size(df, i - 2) * 0.3
    third_bull = _is_bullish(df, i) and (df["收盘"].iloc[i] - df["开盘"].iloc[i]) > 0.01 * df["开盘"].iloc[i]
    return first_bear and second_small and third_bull


def _is_evening_star(df, i):
    """黄昏之星"""
    if i < 2:
        return False
    first_bull = _is_bullish(df, i - 2) and (df["收盘"].iloc[i - 2] - df["开盘"].iloc[i - 2]) > 0.01 * df["开盘"].iloc[i - 2]
    second_small = _body_size(df, i - 1) < _body_size(df, i - 2) * 0.3
    third_bear = _is_bearish(df, i) and (df["收盘"].iloc[i] - df["开盘"].iloc[i]) < -0.01 * df["开盘"].iloc[i]
    return first_bull and second_small and third_bear


def _is_three_black_crows(df, i):
    """三只乌鸦：连续三根阴线"""
    if i < 2:
        return False
    return (all(_is_bearish(df, i - j) for j in range(3)) and
            df["收盘"].iloc[i] < df["收盘"].iloc[i - 1] < df["收盘"].iloc[i - 2])


def _is_three_white_soldiers(df, i):
    """三个白兵：连续三根阳线"""
    if i < 2:
        return False
    return (all(_is_bullish(df, i - j) for j in range(3)) and
            df["收盘"].iloc[i] > df["收盘"].iloc[i - 1] > df["收盘"].iloc[i - 2])


def _is_shooting_star(df, i):
    """射击之星：长上影线+小实体"""
    body = _body_size(df, i)
    upper = _upper_shadow(df, i)
    lower = _lower_shadow(df, i)
    total = df["最高"].iloc[i] - df["最低"].iloc[i]
    if total == 0:
        return False
    return upper >= body * 2 and lower <= body * 0.3 and body > 0


def _is_hanging_man(df, i):
    """上吊线"""
    body = _body_size(df, i)
    lower = _lower_shadow(df, i)
    upper = _upper_shadow(df, i)
    total = df["最高"].iloc[i] - df["最低"].iloc[i]
    if total == 0:
        return False
    return lower >= body * 2 and upper <= body * 0.3 and body > 0


def _is_red_three_soldiers(df, i):
    """红三兵"""
    if i < 2:
        return False
    return (all(_is_bullish(df, i - j) for j in range(3)) and
            all(df["收盘"].iloc[i - j] > df["开盘"].iloc[i - j] for j in range(3)) and
            df["收盘"].iloc[i] > df["收盘"].iloc[i - 1] > df["收盘"].iloc[i - 2])


def _is_dark_cloud_cover(df, i):
    """乌云盖顶"""
    if i < 1:
        return False
    prev_close = df["收盘"].iloc[i - 1]
    curr_open = df["开盘"].iloc[i]
    curr_close = df["收盘"].iloc[i]
    return (_is_bullish(df, i - 1) and _is_bearish(df, i) and
            curr_open > prev_close and
            curr_close < (prev_close + curr_open) / 2)


def _is_piercing_pattern(df, i):
    """刺透形态"""
    if i < 1:
        return False
    prev_close = df["收盘"].iloc[i - 1]
    prev_open = df["开盘"].iloc[i - 1]
    curr_open = df["开盘"].iloc[i]
    curr_close = df["收盘"].iloc[i]
    return (_is_bearish(df, i - 1) and _is_bullish(df, i) and
            curr_open < prev_close and
            curr_close > (prev_close + prev_open) / 2)


def _is_harami(df, i):
    """孕线形态"""
    if i < 1:
        return False
    prev_body_high = max(df["开盘"].iloc[i - 1], df["收盘"].iloc[i - 1])
    prev_body_low = min(df["开盘"].iloc[i - 1], df["收盘"].iloc[i - 1])
    curr_body_high = max(df["开盘"].iloc[i], df["收盘"].iloc[i])
    curr_body_low = min(df["开盘"].iloc[i], df["收盘"].iloc[i])
    return curr_body_high < prev_body_high and curr_body_low > prev_body_low

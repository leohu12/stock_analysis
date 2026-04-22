# -*- coding: utf-8 -*-
"""
终端可视化模块
在命令行中渲染K线图、指标图、表格等
"""

import os
import sys
import math
import pandas as pd
import numpy as np
from datetime import datetime


# ==================== 颜色控制 ====================

class Color:
    """终端颜色"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @staticmethod
    def disable():
        """禁用颜色"""
        Color.RESET = ""
        Color.BOLD = ""
        Color.DIM = ""
        Color.RED = ""
        Color.GREEN = ""
        Color.YELLOW = ""
        Color.BLUE = ""
        Color.MAGENTA = ""
        Color.CYAN = ""
        Color.WHITE = ""
        Color.BG_RED = ""
        Color.BG_GREEN = ""
        Color.BG_YELLOW = ""
        Color.BG_BLUE = ""


def check_color_support():
    """检测终端颜色支持"""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        Color.disable()


check_color_support()


# ==================== 表格渲染 ====================

def print_table(df, title="", max_rows=20, max_col_width=15):
    """打印格式化表格"""
    if df.empty:
        print(f"{Color.YELLOW}  暂无数据{Color.RESET}")
        return

    # 限制行数
    display_df = df.head(max_rows).copy()

    # 转换列为字符串并截断
    for col in display_df.columns:
        display_df[col] = display_df[col].apply(lambda x: _format_cell(x, max_col_width))

    # 计算列宽
    col_widths = {}
    for col in display_df.columns:
        header_len = _display_width(str(col))
        max_data_len = display_df[col].apply(lambda x: _display_width(str(x))).max()
        col_widths[col] = min(max(header_len, max_data_len) + 2, max_col_width + 2)

    # 打印标题
    if title:
        total_width = sum(col_widths.values()) + len(col_widths) + 1
        print(f"\n{Color.BOLD}{Color.CYAN}{'═' * total_width}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}  {title}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'═' * total_width}{Color.RESET}")

    # 打印表头
    header = "│"
    for col in display_df.columns:
        w = col_widths[col]
        header += f"{Color.BOLD}{Color.WHITE} {str(col):^{w - 2}} {Color.RESET}│"
    print(header)

    # 分隔线
    sep = "├"
    for col in display_df.columns:
        sep += "─" * col_widths[col] + "┤"
    print(sep)

    # 打印数据行
    for _, row in display_df.iterrows():
        line = "│"
        for col in display_df.columns:
            w = col_widths[col]
            val = str(row[col])
            # 根据值着色
            color = _get_cell_color(col, val)
            line += f"{color} {val:^{w - 2}} {Color.RESET}│"
        print(line)

    # 底部
    bottom = "└"
    for col in display_df.columns:
        bottom += "─" * col_widths[col] + "┘"
    print(bottom)

    if len(df) > max_rows:
        print(f"{Color.DIM}  ... 共 {len(df)} 条记录，仅显示前 {max_rows} 条{Color.RESET}")


def _format_cell(value, max_width):
    """格式化单元格"""
    if pd.isna(value) or value is None:
        return "-"
    s = str(value)
    # 截断过长内容
    if _display_width(s) > max_width:
        return s[:max_width - 2] + ".."
    return s


def _display_width(text):
    """计算显示宽度（中文占2个字符）"""
    width = 0
    for ch in str(text):
        if '\u4e00' <= ch <= '\u9fff' or ch in '，。、；：？！""''（）【】':
            width += 2
        else:
            width += 1
    return width


def _get_cell_color(col_name, value):
    """根据列名和值返回颜色"""
    if value == "-":
        return Color.DIM
    try:
        num = float(value.replace("%", "").replace(",", ""))
    except (ValueError, TypeError):
        return Color.RESET

    if any(k in col_name for k in ["涨跌幅", "涨跌额", "涨幅", "涨速"]):
        return Color.RED if num > 0 else Color.GREEN if num < 0 else Color.RESET
    if "跌" in col_name and "涨停" not in col_name:
        return Color.RED if num > 0 else Color.GREEN if num < 0 else Color.RESET
    if any(k in col_name for k in ["净流入", "流入"]):
        return Color.RED if num > 0 else Color.GREEN if num < 0 else Color.RESET
    return Color.RESET


# ==================== K线图渲染 ====================

def print_kline_chart(df, height=20, width=80):
    """在终端中渲染K线图"""
    if df.empty or len(df) < 5:
        print(f"{Color.YELLOW}  数据不足，无法绘制K线图{Color.RESET}")
        return

    # 取最近的数据
    display_df = df.tail(min(width, len(df))).copy().reset_index(drop=True)

    # 计算价格范围
    price_min = display_df["最低"].min()
    price_max = display_df["最高"].max()
    price_range = price_max - price_min
    if price_range == 0:
        price_range = price_max * 0.02

    # 添加上下边距
    price_min -= price_range * 0.05
    price_max += price_range * 0.05
    price_range = price_max - price_min

    # 获取终端宽度
    term_width = os.get_terminal_size().columns if sys.stdout.isatty() else 100
    chart_width = min(term_width - 30, width)

    # 每根K线的宽度（字符）
    candle_width = max(1, chart_width // len(display_df))

    print(f"\n{Color.BOLD}  K线图 - {display_df['名称'].iloc[0] if '名称' in display_df.columns else ''}"
          f" ({display_df['日期'].iloc[-1]}){Color.RESET}")
    print(f"  最高: {Color.RED}{price_max:.2f}{Color.RESET}  最低: {Color.GREEN}{price_min:.2f}{Color.RESET}")

    # 价格刻度
    print(f"  {price_max:>10.2f} ┤")

    # 渲染K线
    for row_idx in range(height):
        current_price = price_max - (row_idx / height) * price_range
        line = f"  {current_price:>10.2f} │"

        for _, candle in display_df.iterrows():
            o, c, h, l = candle["开盘"], candle["收盘"], candle["最高"], candle["最低"]
            is_up = c >= o

            if current_price > h:
                line += " " * candle_width
            elif current_price < l:
                line += " " * candle_width
            elif current_price >= max(o, c) and current_price <= h:
                # 上影线
                color = Color.RED if is_up else Color.GREEN
                line += f"{color}{'│' if candle_width == 1 else '┃'}{Color.RESET}"
                if candle_width > 1:
                    line += " " * (candle_width - 1)
            elif current_price >= min(o, c) and current_price < max(o, c):
                # 实体
                color = Color.RED if is_up else Color.GREEN
                fill = "█" if candle_width == 1 else "██"
                line += f"{color}{fill}{Color.RESET}"
                if candle_width > 1:
                    line += " " * (candle_width - 2)
            elif current_price >= l and current_price < min(o, c):
                # 下影线
                color = Color.RED if is_up else Color.GREEN
                line += f"{color}{'│' if candle_width == 1 else '┃'}{Color.RESET}"
                if candle_width > 1:
                    line += " " * (candle_width - 1)

        print(line)

    print(f"  {price_min:>10.2f} ┤")

    # 日期轴
    date_line = " " * 14 + "└"
    for i in range(len(display_df)):
        date_line += "─" * candle_width
    date_line += "┘"
    print(date_line)

    # 显示关键日期
    step = max(1, len(display_df) // 6)
    date_labels = " " * 14
    for i in range(0, len(display_df), step):
        date_str = str(display_df["日期"].iloc[i])[:5]
        pos = i * candle_width + candle_width // 2
        date_labels = date_labels[:pos] + date_str + date_labels[pos + 5:]
    print(f"{Color.DIM}{date_labels}{Color.RESET}")


# ==================== 指标图渲染 ====================

def print_indicator_chart(df, indicator_name="MACD", height=10, width=80):
    """渲染技术指标图"""
    if df.empty:
        return

    display_df = df.tail(min(width, len(df))).copy().reset_index(drop=True)

    if indicator_name == "MACD":
        _print_macd_chart(display_df, height)
    elif indicator_name == "KDJ":
        _print_kdj_chart(display_df, height)
    elif indicator_name == "RSI":
        _print_rsi_chart(display_df, height)
    elif indicator_name == "VOL":
        _print_volume_chart(display_df, height)


def _print_macd_chart(df, height):
    """MACD指标图"""
    if "MACD" not in df.columns:
        return

    print(f"\n{Color.BOLD}  MACD指标{Color.RESET}")

    dif = df["DIF"].fillna(0)
    dea = df["DEA"].fillna(0)
    macd = df["MACD"].fillna(0)

    max_val = max(abs(dif).max(), abs(dea).max(), abs(macd).max(), 0.01)

    for row_idx in range(height):
        current_val = max_val - (row_idx / height) * 2 * max_val
        line = f"  {current_val:>+10.2f} │"

        for _, row in df.iterrows():
            d, e, m = row.get("DIF", 0) or 0, row.get("DEA", 0) or 0, row.get("MACD", 0) or 0

            if abs(m) > max_val * 0.01:
                bar_height = int(abs(m) / max_val * (height / 2))
                bar_row_from_zero = int((max_val - 0) / (2 * max_val) * height)
                if m > 0 and row_idx >= bar_row_from_zero - bar_height and row_idx < bar_row_from_zero:
                    line += f"{Color.RED}▓{Color.RESET}"
                elif m < 0 and row_idx >= bar_row_from_zero and row_idx < bar_row_from_zero + bar_height:
                    line += f"{Color.GREEN}▓{Color.RESET}"
                else:
                    line += " "
            elif abs(current_val - d) < max_val / height:
                line += f"{Color.YELLOW}●{Color.RESET}"
            elif abs(current_val - e) < max_val / height:
                line += f"{Color.CYAN}●{Color.RESET}"
            else:
                line += " "

        print(line)

    print(f"  {'0':>10} ┼{'─' * min(80, len(df))}")
    print(f"  {Color.YELLOW}● DIF{Color.RESET}  {Color.CYAN}● DEA{Color.RESET}  "
          f"{Color.RED}▓ MACD红柱{Color.RESET}  {Color.GREEN}▓ MACD绿柱{Color.RESET}")


def _print_kdj_chart(df, height):
    """KDJ指标图"""
    if "K" not in df.columns:
        return

    print(f"\n{Color.BOLD}  KDJ指标{Color.RESET}")

    k = df["K"].fillna(50)
    d = df["D"].fillna(50)
    j = df["J"].fillna(50)

    max_val = max(k.max(), d.max(), j.max(), 100)
    min_val = min(k.min(), d.min(), j.min(), 0)

    for row_idx in range(height):
        current_val = max_val - (row_idx / height) * (max_val - min_val)
        line = f"  {current_val:>6.1f} │"

        for _, row in df.iterrows():
            kv, dv, jv = row.get("K", 50), row.get("D", 50), row.get("J", 50)
            if pd.isna(kv):
                kv = 50
            if pd.isna(dv):
                dv = 50
            if pd.isna(jv):
                jv = 50

            step = (max_val - min_val) / height
            if abs(current_val - kv) < step:
                line += f"{Color.YELLOW}K{Color.RESET}"
            elif abs(current_val - dv) < step:
                line += f"{Color.CYAN}D{Color.RESET}"
            elif abs(current_val - jv) < step:
                line += f"{Color.MAGENTA}J{Color.RESET}"
            else:
                line += " "

        print(line)

    # 超买超卖线
    eighty_pos = int((max_val - 80) / (max_val - min_val) * height)
    twenty_pos = int((max_val - 20) / (max_val - min_val) * height)
    print(f"  {'':>6}   ┼{'─' * min(80, len(df))}")
    print(f"  {Color.YELLOW}K{Color.RESET}  {Color.CYAN}D{Color.RESET}  "
          f"{Color.MAGENTA}J{Color.RESET}  {Color.RED}80超买{Color.RESET}  {Color.GREEN}20超卖{Color.RESET}")


def _print_rsi_chart(df, height):
    """RSI指标图"""
    if "RSI6" not in df.columns:
        return

    print(f"\n{Color.BOLD}  RSI指标{Color.RESET}")

    max_val = 100
    min_val = 0

    for row_idx in range(height):
        current_val = max_val - (row_idx / height) * (max_val - min_val)
        line = f"  {current_val:>6.1f} │"

        for _, row in df.iterrows():
            rsi6 = row.get("RSI6", 50) or 50
            rsi12 = row.get("RSI12", 50) or 50
            rsi24 = row.get("RSI24", 50) or 50

            step = (max_val - min_val) / height
            if abs(current_val - rsi6) < step:
                line += f"{Color.YELLOW}6{Color.RESET}"
            elif abs(current_val - rsi12) < step:
                line += f"{Color.CYAN}2{Color.RESET}"
            elif abs(current_val - rsi24) < step:
                line += f"{Color.MAGENTA}4{Color.RESET}"
            else:
                line += " "

        print(line)

    print(f"  {'':>6}   ┼{'─' * min(80, len(df))}")
    print(f"  {Color.YELLOW}RSI6{Color.RESET}  {Color.CYAN}RSI12{Color.RESET}  "
          f"{Color.MAGENTA}RSI24{Color.RESET}  {Color.RED}70超买{Color.RESET}  {Color.GREEN}30超卖{Color.RESET}")


def _print_volume_chart(df, height):
    """成交量柱状图"""
    if "成交量" not in df.columns:
        return

    print(f"\n{Color.BOLD}  成交量{Color.RESET}")

    vol = df["成交量"].fillna(0)
    max_vol = vol.max() if vol.max() > 0 else 1

    for row_idx in range(height):
        threshold = max_vol * (1 - row_idx / height)
        line = f"  {threshold / 10000:>10.0f}万 │"

        for _, row in df.iterrows():
            v = row.get("成交量", 0) or 0
            is_up = row.get("收盘", 0) >= row.get("开盘", 0)
            if v >= threshold:
                color = Color.RED if is_up else Color.GREEN
                line += f"{color}▓{Color.RESET}"
            else:
                line += " "

        print(line)

    print(f"  {'0':>10}万 ┼{'─' * min(80, len(df))}")


# ==================== 资金流向图 ====================

def print_money_flow_chart(df, height=15):
    """资金流向柱状图"""
    if df.empty or "主力净流入" not in df.columns:
        return

    print(f"\n{Color.BOLD}  资金流向（万元）{Color.RESET}")

    flow = df["主力净流入"].fillna(0)
    max_val = max(abs(flow).max(), 0.01)

    for row_idx in range(height):
        current_val = max_val - (row_idx / height) * 2 * max_val
        line = f"  {current_val / 10000:>+10.0f} │"

        for _, row in df.iterrows():
            v = row.get("主力净流入", 0) or 0
            if v > 0 and current_val > 0 and current_val <= v:
                line += f"{Color.RED}▓{Color.RESET}"
            elif v < 0 and current_val < 0 and current_val >= v:
                line += f"{Color.GREEN}▓{Color.RESET}"
            else:
                line += " "

        print(line)

    print(f"  {'0':>+10.0f} ┼{'─' * min(80, len(df))}")
    print(f"  {Color.RED}▓ 主力净流入{Color.RESET}  {Color.GREEN}▓ 主力净流出{Color.RESET}")


# ==================== 市场概览 ====================

def print_market_overview(overview, limit_stats):
    """打印市场概览"""
    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  📊 A股市场概览{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")

    if overview:
        for name, info in overview.items():
            price = info.get("最新价", 0)
            change = info.get("涨跌幅", 0)
            amount = info.get("成交额", 0)
            color = Color.RED if change > 0 else Color.GREEN if change < 0 else Color.RESET
            sign = "+" if change > 0 else ""
            print(f"  {Color.BOLD}{name:>6}{Color.RESET}  "
                  f"{color}{price:.2f}{Color.RESET}  "
                  f"{color}{sign}{change:.2f}%{Color.RESET}  "
                  f"成交额: {amount / 1e8:.0f}亿")

    if limit_stats:
        print(f"\n  {Color.RED}涨停: {limit_stats.get('涨停数', 0)}只{Color.RESET}  "
              f"{Color.GREEN}跌停: {limit_stats.get('跌停数', 0)}只{Color.RESET}")


# ==================== 个股详情 ====================

def print_stock_detail(df, quote_df=None):
    """打印个股详情"""
    if df.empty:
        return

    latest = df.iloc[-1]
    name = latest.get("名称", "")
    date = latest.get("日期", "")

    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  📈 {name} ({date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else date}){Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")

    change = latest.get("涨跌幅", 0)
    color = Color.RED if change > 0 else Color.GREEN if change < 0 else Color.RESET
    sign = "+" if change > 0 else ""

    print(f"  开盘: {latest['开盘']:.2f}  收盘: {color}{latest['收盘']:.2f}{Color.RESET}")
    print(f"  最高: {Color.RED}{latest['最高']:.2f}{Color.RESET}  最低: {Color.GREEN}{latest['最低']:.2f}{Color.RESET}")
    print(f"  涨跌幅: {color}{sign}{change:.2f}%{Color.RESET}  振幅: {latest.get('振幅', 0):.2f}%")
    print(f"  成交量: {latest['成交量'] / 10000:.0f}万手  成交额: {latest['成交额'] / 1e8:.2f}亿")
    print(f"  换手率: {latest.get('换手率', 0):.2f}%")

    # 均线数据
    ma_cols = [c for c in df.columns if c.startswith("MA") and c != "MACD"]
    if ma_cols:
        ma_info = []
        for col in sorted(ma_cols, key=lambda x: int(x[2:])):
            val = latest.get(col)
            if pd.notna(val):
                ma_info.append(f"{col}={val:.2f}")
        if ma_info:
            print(f"  均线: {'  '.join(ma_info)}")

    # 技术指标
    print(f"\n{Color.BOLD}  技术指标:{Color.RESET}")
    if pd.notna(latest.get("DIF")):
        print(f"  MACD: DIF={latest['DIF']:.3f}  DEA={latest['DEA']:.3f}  MACD={latest['MACD']:.3f}")
    if pd.notna(latest.get("K")):
        print(f"  KDJ:  K={latest['K']:.2f}  D={latest['D']:.2f}  J={latest['J']:.2f}")
    if pd.notna(latest.get("RSI6")):
        print(f"  RSI:  RSI6={latest['RSI6']:.2f}  RSI12={latest.get('RSI12', 0):.2f}  RSI24={latest.get('RSI24', 0):.2f}")
    if pd.notna(latest.get("BOLL_MID")):
        print(f"  BOLL: 上轨={latest['BOLL_UP']:.2f}  中轨={latest['BOLL_MID']:.2f}  下轨={latest['BOLL_LOW']:.2f}")
    if pd.notna(latest.get("WR")):
        print(f"  WR:   {latest['WR']:.2f}")
    if pd.notna(latest.get("CCI")):
        print(f"  CCI:  {latest['CCI']:.2f}")
    if pd.notna(latest.get("ATR")):
        print(f"  ATR:  {latest['ATR']:.2f}")
    if "ST_Dir" in df.columns:
        st_dir = "多头" if latest.get("ST_Dir") else "空头"
        st_val = latest.get("ST", 0)
        print(f"  SuperTrend: {st_dir} ({st_val:.2f})")

    # 信号
    signals = latest.get("信号", [])
    if signals:
        print(f"\n{Color.BOLD}  今日信号:{Color.RESET}")
        for s in signals:
            print(f"    {s}")

    # K线形态
    patterns = latest.get("K线形态", [])
    if patterns:
        print(f"\n{Color.BOLD}  K线形态:{Color.RESET}")
        for p in patterns:
            print(f"    {p}")


# ==================== 进度条 ====================

def print_progress(current, total, prefix=""):
    """打印进度条"""
    percent = current / total * 100
    bar_len = 30
    filled = int(bar_len * current / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(f"\r  {prefix} [{bar}] {percent:.0f}% ({current}/{total})")
    sys.stdout.flush()
    if current == total:
        print()


# ==================== 横向柱状图 ====================

def print_horizontal_bar(data_dict, title="", max_items=15, bar_width=30):
    """打印横向柱状图"""
    if not data_dict:
        return

    print(f"\n{Color.BOLD}{Color.CYAN}  {title}{Color.RESET}")
    print(f"  {'─' * (bar_width + 25)}")

    sorted_items = sorted(data_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:max_items]
    max_val = max(abs(v) for _, v in sorted_items) if sorted_items else 1

    for name, value in sorted_items:
        color = Color.RED if value > 0 else Color.GREEN
        sign = "+" if value > 0 else ""
        bar_len = int(abs(value) / max_val * bar_width)
        bar = "▓" * bar_len

        name_display = name[:8].ljust(8)
        print(f"  {name_display} {color}{bar}{Color.RESET} {color}{sign}{value:.2f}{Color.RESET}")

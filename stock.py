# -*- coding: utf-8 -*-
"""
A股股票分析工具 - 命令行版
参考 https://github.com/myhhub/stock
数据来源：东方财富网公开API（无需API Key）

功能：
1. 实时行情监控
2. 个股深度分析（K线、技术指标、形态识别、买卖信号）
3. 智能选股（MACD金叉、KDJ金叉、放量突破、均线多头、RSI超卖、布林下轨、多重信号）
4. 板块分析（行业/概念板块涨跌、资金流向）
5. 资金流向分析

使用方法：
    python stock.py              # 进入交互式菜单
    python stock.py 600519       # 直接分析贵州茅台
    python stock.py search 茅台  # 搜索股票
"""

import sys
import os
import io
import time

# Windows 终端 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 启动时清除代理环境变量（防止VPN/代理软件干扰国内API访问）
for _k in ['http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','all_proxy','ALL_PROXY']:
    os.environ.pop(_k, None)

# 添加模块路径（确保在任何目录下运行都能正确导入）
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from fetcher import fetcher, sina_fetcher
from indicators import calc_all_indicators, analyze_signals, generate_analysis_summary
from patterns import identify_patterns
from screener import screener
from watchlist import show_watchlist_menu, list_stocks
from display import (
    print_table, print_kline_chart, print_indicator_chart,
    print_money_flow_chart, print_market_overview, print_stock_detail,
    print_progress, print_horizontal_bar, Color
)
from backtest import run_backtest, print_backtest_report, list_strategies
from chart import plot_kline_simple
import akshare_data as akdata


# ==================== 功能函数 ====================

def show_market_overview():
    """显示市场概览"""
    print(f"\n{Color.BOLD}正在获取市场数据...{Color.RESET}")
    try:
        overview = fetcher.get_market_overview()
        limit_stats = fetcher.get_limit_stats()
        print_market_overview(overview, limit_stats)

        # 涨跌分布
        print(f"\n{Color.BOLD}  涨跌幅分布:{Color.RESET}")
        all_stocks = fetcher.get_all_stocks()
        if not all_stocks.empty:
            up = len(all_stocks[all_stocks["涨跌幅"] > 0])
            down = len(all_stocks[all_stocks["涨跌幅"] < 0])
            flat = len(all_stocks[all_stocks["涨跌幅"] == 0])
            total = len(all_stocks)
            print(f"  上涨: {Color.RED}{up}{Color.RESET}  "
                  f"下跌: {Color.GREEN}{down}{Color.RESET}  "
                  f"平盘: {flat}  共: {total}")

            # 涨幅榜
            print(f"\n{Color.BOLD}  涨幅榜 TOP10:{Color.RESET}")
            top = all_stocks.nlargest(10, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
            top["成交额"] = top["成交额"].apply(lambda x: f"{x / 1e8:.1f}亿" if pd.notna(x) else "-")
            print_table(top, max_rows=10)

            # 跌幅榜
            print(f"\n{Color.BOLD}  跌幅榜 TOP10:{Color.RESET}")
            bottom = all_stocks.nsmallest(10, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
            bottom["成交额"] = bottom["成交额"].apply(lambda x: f"{x / 1e8:.1f}亿" if pd.notna(x) else "-")
            print_table(bottom, max_rows=10)

            # 成交额榜
            print(f"\n{Color.BOLD}  成交额榜 TOP10:{Color.RESET}")
            vol_top = all_stocks.nlargest(10, "成交额")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
            vol_top["成交额"] = vol_top["成交额"].apply(lambda x: f"{x / 1e8:.1f}亿" if pd.notna(x) else "-")
            print_table(vol_top, max_rows=10)

    except Exception as e:
        print(f"{Color.RED}  获取数据失败: {e}{Color.RESET}")


def analyze_stock(stock_code, days=120):
    """分析个股（通俗易懂版）"""
    import pandas as pd
    print(f"\n{Color.BOLD}正在分析 {stock_code}...{Color.RESET}")

    try:
        # 先获取实时行情（获取股票名称和实时数据）
        realtime = fetcher.get_realtime_quote(stock_code)
        if realtime.empty:
            print(f"{Color.RED}  未找到该股票数据，请检查代码是否正确{Color.RESET}")
            return
        
        rt = realtime.iloc[0]
        stock_name = rt.get('名称', stock_code)
        
        # 获取K线数据
        kline = fetcher.get_kline(stock_code, count=days)
        if kline.empty:
            print(f"{Color.RED}  未找到该股票数据，请检查代码是否正确{Color.RESET}")
            return

        # 计算所有指标（后台计算，不展示）
        kline = calc_all_indicators(kline)
        kline = analyze_signals(kline)
        kline = identify_patterns(kline)

        # ===== 1. 基本信息 =====
        latest = kline.iloc[-1]
        date = latest.get("日期", "")
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)

        change = latest.get("涨跌幅", 0)
        if change == 0:
            change = rt.get('涨跌幅', 0)
        
        color = Color.RED if change > 0 else Color.GREEN if change < 0 else Color.RESET
        sign = "+" if change > 0 else ""

        print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}  {stock_name} ({stock_code})  {date_str}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")

        # 使用实时行情数据
        current_price = rt.get('最新价', latest['收盘'])
        high_price = rt.get('最高', latest['最高'])
        low_price = rt.get('最低', latest['最低'])
        volume = rt.get('成交量', latest['成交量'])  # 单位：手
        turnover = rt.get('成交额', 0)  # 单位：元
        turnover_rate = rt.get('换手率', 0)
        
        # 成交量格式化：显示为 XX万手（东方财富接口返回的是手）
        if volume >= 10000:
            vol_str = f"{volume/10000:.0f}万手"
        else:
            vol_str = f"{volume}手"
        
        print(f"\n  💰 当前价格: {color}{current_price:.2f}元{Color.RESET}  "
              f"{color}{sign}{change:.2f}%{Color.RESET}")
        print(f"  📊 今日区间: {low_price:.2f} ~ {high_price:.2f}元  "
              f"振幅 {rt.get('振幅', 0):.1f}%")
        print(f"  🔄 成交量: {vol_str}  成交额: {turnover / 1e8:.2f}亿  "
              f"换手: {turnover_rate:.1f}%")

        # ===== 2. 大白话分析 =====
        print(f"\n{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")
        print(f"{Color.BOLD}  📋 这只股票现在怎么样？{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")

        # 趋势判断
        print(f"\n  【趋势】")
        if pd.notna(latest.get("MA5")) and pd.notna(latest.get("MA20")):
            if latest["收盘"] > latest["MA5"] > latest["MA20"]:
                print(f"  ✅ 短期趋势向好，股价在均线上方运行")
            elif latest["收盘"] < latest["MA5"] < latest["MA20"]:
                print(f"  ❌ 短期趋势走弱，股价在均线下方运行")
            else:
                print(f"  ⚠️ 短期趋势不明朗，股价在均线附近震荡")

        if pd.notna(latest.get("MA60")):
            if latest["收盘"] > latest["MA60"]:
                print(f"  ✅ 中期趋势偏多（站上60日均线）")
            else:
                print(f"  ❌ 中期趋势偏空（跌破60日均线）")

        # 买卖信号统计
        signals = latest.get("信号", [])
        buy_signals = [s for s in signals if "🟢" in s]
        sell_signals = [s for s in signals if "🔴" in s]

        print(f"\n  【信号】")
        if buy_signals:
            for s in buy_signals:
                plain = _signal_to_plain(s)
                print(f"  🟢 {plain}")
        if sell_signals:
            for s in sell_signals:
                plain = _signal_to_plain(s)
                print(f"  🔴 {plain}")
        if not buy_signals and not sell_signals:
            print(f"  ⚪ 暂无明显买卖信号，建议观望")

        # K线形态
        patterns = latest.get("K线形态", [])
        if patterns:
            print(f"\n  【K线形态】")
            for p in patterns:
                plain = _pattern_to_plain(p)
                print(f"  📊 {plain}")

        # ===== 3. 综合建议 =====
        print(f"\n{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")
        print(f"{Color.BOLD}  💡 综合建议{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")

        score = _calc_score(latest, buy_signals, sell_signals)

        # 计算建议价格
        support, resistance, buy_price, sell_price = _calc_price_levels(latest)

        print(f"\n  📍 关键价位:")
        print(f"     支撑位（下方防线）: {Color.GREEN}{support:.2f}元{Color.RESET}")
        print(f"     压力位（上方阻力）: {Color.RED}{resistance:.2f}元{Color.RESET}")
        print(f"     建议买入价: {Color.GREEN}{buy_price:.2f}元{Color.RESET}（接近支撑位时考虑）")
        print(f"     建议卖出价: {Color.RED}{sell_price:.2f}元{Color.RESET}（接近压力位时考虑）")
        print(f"     止损价: {Color.YELLOW}{support * 0.97:.2f}元{Color.RESET}（跌破此价坚决止损）")

        print(f"\n  📊 综合评分: {score}/10", end="")
        if score >= 7:
            print(f"  {Color.RED}{Color.BOLD}🚀 多头信号较强{Color.RESET}")
            print(f"  多个指标同时发出买入信号，短期可能有机会")
            print(f"  → 可在 {Color.GREEN}{buy_price:.2f}元{Color.RESET} 附近分批买入")
            print(f"  → 目标价 {Color.RED}{sell_price:.2f}元{Color.RESET}，止损 {Color.YELLOW}{support * 0.97:.2f}元{Color.RESET}")
        elif score >= 5:
            print(f"  {Color.YELLOW}{Color.BOLD}⚖️ 信号偏多但不算强{Color.RESET}")
            print(f"  可以关注，但建议等更明确的信号再入场")
            print(f"  → 回调到 {Color.GREEN}{buy_price:.2f}元{Color.RESET} 附近可轻仓试探")
        elif score >= 3:
            print(f"  {Color.YELLOW}{Color.BOLD}⚠️ 信号偏空{Color.RESET}")
            print(f"  卖出信号多于买入信号，建议谨慎操作")
            print(f"  → 持仓者可在反弹到 {Color.RED}{sell_price:.2f}元{Color.RESET} 附近减仓")
            print(f"  → 空仓者继续观望，不要急于抄底")
        else:
            print(f"  {Color.GREEN}{Color.BOLD}⛔ 空头信号较强{Color.RESET}")
            print(f"  多个指标发出卖出/危险信号，短期风险较大")
            print(f"  → 建议回避，不要急于抄底")
            print(f"  → 如果持仓，建议尽快减仓止损")

        # 风险提示
        print(f"\n  {Color.DIM}⚠️ 以上分析仅供参考，不构成投资建议{Color.RESET}")
        print(f"  {Color.DIM}⚠️ 股市有风险，投资需谨慎{Color.RESET}")

        # ===== 4. 资金流向 =====
        print(f"\n{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")
        print(f"{Color.BOLD}  💸 资金动向（主力资金在干嘛）{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")
        try:
            money_flow = fetcher.get_money_flow(stock_code)
            if not money_flow.empty:
                recent5 = money_flow.tail(5)
                inflow_days = len(recent5[recent5["主力净流入"] > 0])
                outflow_days = 5 - inflow_days
                total_flow = recent5["主力净流入"].sum()

                if total_flow > 0:
                    print(f"\n  🟢 近5日主力资金{Color.RED}净流入 {total_flow/10000:.0f}万元{Color.RESET}")
                    print(f"     其中{inflow_days}天流入，{outflow_days}天流出")
                    print(f"     → 主力在{Color.RED}买入{Color.RESET}，资金面偏积极")
                else:
                    print(f"\n  🔴 近5日主力资金{Color.GREEN}净流出 {abs(total_flow)/10000:.0f}万元{Color.RESET}")
                    print(f"     其中{inflow_days}天流入，{outflow_days}天流出")
                    print(f"     → 主力在{Color.GREEN}卖出{Color.RESET}，资金面偏消极")

                # 每日明细
                print(f"\n  近5日明细:")
                for _, row in recent5.iterrows():
                    d = str(row["日期"])[:10]
                    v = float(row["主力净流入"])
                    if v > 0:
                        print(f"    {d}  {Color.RED}主力流入 +{v/10000:.0f}万{Color.RESET}")
                    else:
                        print(f"    {d}  {Color.GREEN}主力流出 {v/10000:.0f}万{Color.RESET}")
            else:
                print(f"\n  {Color.DIM}资金流向数据暂不可用{Color.RESET}")
        except Exception:
            print(f"\n  {Color.DIM}资金流向数据暂不可用{Color.RESET}")

        # ===== 5. 盘口数据（五档） =====
        print(f"\n{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")
        print(f"{Color.BOLD}  📊 盘口挂单（谁在买、谁在卖）{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'─' * 50}{Color.RESET}")
        _show_depth_inline(stock_code)

    except Exception as e:
        print(f"{Color.RED}  分析失败: {e}{Color.RESET}")


def _signal_to_plain(signal):
    """把技术信号翻译成大白话"""
    mapping = {
        "MACD金叉": "MACD金叉 → 快线向上穿过慢线，短期可能上涨",
        "MACD死叉": "MACD死叉 → 快线向下穿过慢线，短期可能下跌",
        "MACD红柱": "MACD转红 → 动能由弱转强",
        "MACD绿柱": "MACD转绿 → 动能由强转弱",
        "KDJ金叉": "KDJ金叉 → 短线超卖后反弹信号",
        "KDJ死叉": "KDJ死叉 → 短线超买后回调信号",
        "KDJ超卖": "KDJ超卖 → 股价短期跌幅较大，可能反弹",
        "KDJ超买": "KDJ超买 → 股价短期涨幅较大，可能回调",
        "RSI6超卖": "RSI超卖 → 股价跌过头了，可能反弹",
        "RSI6超买": "RSI超买 → 股价涨过头了，可能回调",
        "触及布林下轨": "触及布林下轨 → 股价跌到通道下沿，可能支撑反弹",
        "触及布林上轨": "触及布林上轨 → 股价涨到通道上沿，可能压力回调",
        "WR超买": "WR超买 → 短期涨幅过大",
        "WR超卖": "WR超卖 → 短期跌幅过大",
        "CCI超买": "CCI超买 → 股价异常偏强，注意回调",
        "CCI超卖": "CCI超卖 → 股价异常偏弱，可能反弹",
        "SuperTrend转多": "趋势指标转多 → 上涨趋势可能确立",
        "SuperTrend转空": "趋势指标转空 → 下跌趋势可能确立",
        "均线多头排列": "均线多头排列 → 短中长期趋势全部向上，强势",
        "均线空头排列": "均线空头排列 → 短中长期趋势全部向下，弱势",
        "放量大涨": "放量大涨 → 资金大量买入，上涨有力",
        "放量大跌": "放量大跌 → 资金大量卖出，下跌有力",
    }
    for key, plain in mapping.items():
        if key in signal:
            return plain
    return signal.replace("🟢 ", "").replace("🔴 ", "")


def _pattern_to_plain(pattern):
    """把K线形态翻译成大白话"""
    mapping = {
        "锤子线(看涨)": "锤子线 → 下影线很长，下方有支撑，可能反弹",
        "倒锤子线(看涨)": "倒锤子线 → 上影线较长，多方尝试反攻",
        "吞没形态": "吞没形态 → 今日K线完全包住昨日，趋势可能反转",
        "十字星(变盘)": "十字星 → 多空力量均衡，可能即将变盘",
        "早晨之星(强烈看涨)": "早晨之星 → 跌势中出现的见底信号，强烈看涨",
        "黄昏之星(强烈看跌)": "黄昏之星 → 涨势中出现的见顶信号，强烈看跌",
        "三只乌鸦(看跌)": "三只乌鸦 → 连续3天下跌，空头力量强",
        "三个白兵(看涨)": "三个白兵 → 连续3天上涨，多头力量强",
        "射击之星(看跌)": "射击之星 → 涨势中冲高回落，上方压力大",
        "上吊线(看跌)": "上吊线 → 高位出现长下影线，可能见顶",
        "红三兵(看涨)": "红三兵 → 连续3根阳线，上涨势头好",
        "乌云盖顶(看跌)": "乌云盖顶 → 阴线深入阳线内部，上涨受阻",
        "刺透形态(看涨)": "刺透形态 → 阳线深入阴线内部，下跌可能结束",
        "孕线(变盘)": "孕线 → 今日K线缩在昨日内部，变盘在即",
    }
    for key, plain in mapping.items():
        if key in pattern:
            return plain
    return pattern


def _calc_score(latest, buy_signals, sell_signals):
    """计算综合评分（0-10）"""
    score = 5  # 基准分

    # 趋势得分
    if pd.notna(latest.get("MA5")) and pd.notna(latest.get("MA20")):
        if latest["收盘"] > latest["MA5"] > latest["MA20"]:
            score += 1
        elif latest["收盘"] < latest["MA5"] < latest["MA20"]:
            score -= 1

    if pd.notna(latest.get("MA60")):
        if latest["收盘"] > latest["MA60"]:
            score += 0.5
        else:
            score -= 0.5

    # 信号得分
    score += len(buy_signals) * 0.5
    score -= len(sell_signals) * 0.5

    return max(0, min(10, round(score)))


def _calc_price_levels(latest):
    """
    计算关键价位：支撑位、压力位、建议买入价、建议卖出价
    基于布林带、均线、近期高低点综合计算
    """
    price = latest["收盘"]

    # 支撑位 = 布林下轨 和 MA20 和 近期低点 取最低
    supports = []
    if pd.notna(latest.get("BOLL_LOW")):
        supports.append(latest["BOLL_LOW"])
    if pd.notna(latest.get("MA20")):
        supports.append(latest["MA20"])
    if pd.notna(latest.get("MA60")):
        supports.append(latest["MA60"])
    support = min(supports) if supports else price * 0.95

    # 压力位 = 布林上轨 和 近期高点
    resistances = []
    if pd.notna(latest.get("BOLL_UP")):
        resistances.append(latest["BOLL_UP"])
    if pd.notna(latest.get("MA120")):
        resistances.append(latest["MA120"])
    if pd.notna(latest.get("MA250")):
        resistances.append(latest["MA250"])
    resistance = max(resistances) if resistances else price * 1.05

    # 建议买入价 = 支撑位附近（留一点空间）
    buy_price = round(support * 1.01, 2)

    # 建议卖出价 = 压力位附近（留一点空间）
    sell_price = round(resistance * 0.99, 2)

    # 确保买入价 < 当前价 < 卖出价
    if buy_price >= price:
        buy_price = round(price * 0.97, 2)
    if sell_price <= price:
        sell_price = round(price * 1.05, 2)

    return round(support, 2), round(resistance, 2), buy_price, sell_price


def _show_depth_inline(stock_code):
    """在个股分析中内联展示盘口（新浪五档）"""
    try:
        depth = sina_fetcher.get_depth5(stock_code)
        if depth and depth.get("买盘"):
            _print_depth(depth)
            return
    except Exception:
        pass

    print(f"  {Color.DIM}盘口数据暂不可用{Color.RESET}")


def _print_depth(depth):
    """打印五档盘口表格"""
    name = depth.get("名称", "")
    price = depth.get("最新价", 0)
    print(f"\n  {Color.BOLD}{name}  现价 {price:.2f}{Color.RESET}")

    sells = depth.get("卖盘", [])[::-1]  # 卖盘倒序显示（卖5在上）
    buys = depth.get("买盘", [])

    print(f"\n  {Color.DIM}{'档位':>4}  {'卖价':>8}  {'卖量':>8}  │  {'买价':>8}  {'买量':>8}{Color.RESET}")
    print(f"  {Color.DIM}{'─'*52}{Color.RESET}")

    for i in range(5, 0, -1):
        s = next((x for x in sells if x["档"] == i), None)
        b = next((x for x in buys if x["档"] == i), None)

        s_price = s["价"] if s else 0
        s_vol = s["量"] if s else 0
        b_price = b["价"] if b else 0
        b_vol = b["量"] if b else 0

        s_color = Color.GREEN if s_price > 0 else Color.DIM
        b_color = Color.RED if b_price > 0 else Color.DIM

        print(f"  {'卖' + str(i):>4}  {s_color}{s_price:>8.2f}{Color.RESET}  {s_vol:>8,}  │  "
              f"{b_color}{b_price:>8.2f}{Color.RESET}  {b_vol:>8,}")

    # 计算买卖力量对比
    buy_total = sum(b["价"] * b["量"] for b in buys if b["价"] > 0)
    sell_total = sum(s["价"] * s["量"] for s in sells if s["价"] > 0)
    total = buy_total + sell_total
    if total > 0:
        buy_ratio = buy_total / total * 100
        print(f"\n  {Color.DIM}买盘金额占比: {Color.RED}{buy_ratio:.1f}%{Color.DIM}  "
              f"卖盘金额占比: {Color.GREEN}{100-buy_ratio:.1f}%{Color.RESET}")
        if buy_ratio > 60:
            print(f"  {Color.RED}→ 买盘力量占优，下方承接较强{Color.RESET}")
        elif buy_ratio < 40:
            print(f"  {Color.GREEN}→ 卖盘力量占优，上方抛压较大{Color.RESET}")
        else:
            print(f"  {Color.YELLOW}→ 买卖力量均衡{Color.RESET}")


def show_depth(stock_code):
    """单独查看某只股票的五档盘口"""
    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  📊 {stock_code} 盘口分析{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    _show_depth_inline(stock_code)


def search_stock(keyword):
    """搜索股票"""
    print(f"\n{Color.BOLD}正在搜索 '{keyword}'...{Color.RESET}")
    try:
        results = fetcher.search_stock(keyword)
        if results:
            print_table(pd.DataFrame(results), title=f"搜索结果: {keyword}")
        else:
            print(f"{Color.YELLOW}  未找到匹配的股票{Color.RESET}")
    except Exception as e:
        print(f"{Color.RED}  搜索失败: {e}{Color.RESET}")


def show_stock_selection():
    """智能选股菜单"""
    import pandas as pd

    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  🔍 智能选股{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"  0. [实时快速扫描] 不依赖K线指标，盘中用")
    print(f"  1. MACD金叉选股")
    print(f"  2. KDJ金叉选股")
    print(f"  3. 放量突破选股")
    print(f"  4. 均线多头排列选股")
    print(f"  5. RSI超卖选股")
    print(f"  6. 触及布林下轨选股")
    print(f"  7. 多重信号选股（2个以上买入信号）")
    print(f"  8. 潜力股筛选（低价+主力买入）")
    print(f"  9. 返回主菜单")
    print()

    choice = input(f"  {Color.BOLD}请选择 (0-9): {Color.RESET}").strip()

    try:
        result = pd.DataFrame()
        
        # 实时快速扫描（不需要K线数据）
        if choice == "0":
            from screener import screen_realtime_simple
            result = screen_realtime_simple()
            
            # 显示结果（简洁格式）
            if not result.empty:
                print(f"\n{Color.BOLD}{Color.CYAN}{'='*55}{Color.RESET}")
                print(f"{Color.BOLD}{Color.CYAN}  实时选股结果 (共 {len(result)} 只){Color.RESET}")
                print(f"{Color.BOLD}{Color.CYAN}{'='*55}{Color.RESET}\n")
                print_table(result, title="", max_rows=30)
                print(f"\n  {Color.DIM}注：建议买入价仅供参考，非承诺价格{Color.RESET}")
            return
        
        # 以下是需要K线数据的选股方式
        print(f"\n{Color.BOLD}正在获取全市场股票列表...{Color.RESET}")
        all_stocks = fetcher.get_all_stocks()
        if all_stocks.empty:
            print(f"{Color.RED}  获取股票列表失败{Color.RESET}")
            return

        # 过滤ST、退市、停牌
        all_stocks = all_stocks[~all_stocks["名称"].str.contains("ST|退", na=False)]
        all_stocks = all_stocks[all_stocks["最新价"] > 0]
        # 过滤创业板（300/301开头）和科创板（688开头）
        all_stocks = all_stocks[~all_stocks["代码"].str.startswith(("300", "301", "688"))]
        
        print(f"  过滤后剩余 {len(all_stocks)} 只股票\n")

        if choice == "1":
            result = screener.screen_macd_golden_cross(all_stocks)
        elif choice == "2":
            result = screener.screen_kdj_golden_cross(all_stocks)
        elif choice == "3":
            result = screener.screen_volume_breakout(all_stocks)
        elif choice == "4":
            result = screener.screen_ma_bullish(all_stocks)
        elif choice == "5":
            result = screener.screen_oversold_rsi(all_stocks)
        elif choice == "6":
            result = screener.screen_boll_lower(all_stocks)
        elif choice == "7":
            # 多重信号选股可以加价格过滤
            max_price = input(f"  {Color.BOLD}最高价格上限 (直接回车跳过，如 50): {Color.RESET}").strip()
            stocks_to_scan = all_stocks
            if max_price:
                max_price_val = float(max_price)
                # 只保留价格有效的股票（>0 且 <= 限制价）
                stocks_to_scan = all_stocks[
                    (all_stocks["最新价"].notna()) & 
                    (all_stocks["最新价"] > 0) & 
                    (all_stocks["最新价"] <= max_price_val)
                ]
                print(f"  价格限制: ≤ {max_price} 元，剩余 {len(stocks_to_scan)} 只待扫描")
            
            result = screener.multi_signal_screen(stocks_to_scan)
        elif choice == "8":
            # 潜力股筛选：低价 + 主力买入
            max_price_input = input(f"  {Color.BOLD}最高价格上限 (如 50，直接回车不限制): {Color.RESET}").strip()
            max_price_val = float(max_price_input) if max_price_input else None
            if max_price_val:
                all_stocks = all_stocks[
                    (all_stocks["最新价"].notna()) &
                    (all_stocks["最新价"] > 0) &
                    (all_stocks["最新价"] <= max_price_val)
                ]
                print(f"  价格限制: ≤ {max_price_val} 元，剩余 {len(all_stocks)} 只待扫描")
            
            result = screener.screen_potential_stocks(all_stocks, max_price=max_price_val)
        elif choice == "9":
            return
        else:
            print(f"{Color.YELLOW}  无效选择{Color.RESET}")
            return

        if result.empty:
            print(f"\n{Color.YELLOW}  未找到符合条件的股票{Color.RESET}")
        else:
            # 格式化显示
            display_cols = [c for c in result.columns if c not in ["信号详情"]]
            print_table(result[display_cols], title=f"选股结果 ({len(result)}只)")

            # 如果有信号详情，显示前5只
            if "信号详情" in result.columns:
                print(f"\n{Color.BOLD}  信号详情 (前5只):{Color.RESET}")
                for _, row in result.head(5).iterrows():
                    print(f"  {Color.BOLD}{row['代码']} {row['名称']}{Color.RESET}")
                    print(f"    {row.get('信号详情', '')}")

    except Exception as e:
        print(f"{Color.RED}  选股失败: {e}{Color.RESET}")
        import traceback
        traceback.print_exc()


def show_sector_analysis():
    """板块分析"""
    import pandas as pd

    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  🏭 板块分析{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"  1. 行业板块涨跌")
    print(f"  2. 概念板块涨跌")
    print(f"  3. 行业板块资金流向")
    print(f"  4. 概念板块资金流向")
    print(f"  5. 查看板块内个股")
    print(f"  6. 返回主菜单")
    print()

    choice = input(f"  {Color.BOLD}请选择 (1-6): {Color.RESET}").strip()

    try:
        if choice == "1":
            print(f"\n{Color.BOLD}正在获取行业板块数据...{Color.RESET}")
            df = fetcher.get_sector_list("industry")
            if not df.empty:
                print_table(df[["名称", "涨跌幅", "涨跌额", "换手率", "领涨股", "上涨家数", "下跌家数"]],
                           title="行业板块涨跌", max_rows=30)
        elif choice == "2":
            print(f"\n{Color.BOLD}正在获取概念板块数据...{Color.RESET}")
            df = fetcher.get_sector_list("concept")
            if not df.empty:
                print_table(df[["名称", "涨跌幅", "涨跌额", "换手率", "领涨股", "上涨家数", "下跌家数"]],
                           title="概念板块涨跌", max_rows=30)
        elif choice == "3":
            print(f"\n{Color.BOLD}正在获取行业资金流向...{Color.RESET}")
            df = fetcher.get_sector_money_flow("industry")
            if not df.empty:
                for col in ["主力净流入", "超大单净流入", "5日主力净流入", "10日主力净流入"]:
                    df[col] = df[col].apply(lambda x: f"{x / 1e8:.2f}亿" if pd.notna(x) else "-")
                print_table(df, title="行业板块资金流向", max_rows=30)
        elif choice == "4":
            print(f"\n{Color.BOLD}正在获取概念资金流向...{Color.RESET}")
            df = fetcher.get_sector_money_flow("concept")
            if not df.empty:
                for col in ["主力净流入", "超大单净流入", "5日主力净流入", "10日主力净流入"]:
                    df[col] = df[col].apply(lambda x: f"{x / 1e8:.2f}亿" if pd.notna(x) else "-")
                print_table(df, title="概念板块资金流向", max_rows=30)
        elif choice == "5":
            sector_code = input(f"  {Color.BOLD}请输入板块代码: {Color.RESET}").strip()
            sector_type = input(f"  {Color.BOLD}板块类型 (1.行业 2.概念): {Color.RESET}").strip()
            st = "industry" if sector_type != "2" else "concept"
            print(f"\n{Color.BOLD}正在获取板块个股...{Color.RESET}")
            df = fetcher.get_sector_stocks(sector_code, st)
            if not df.empty:
                print_table(df[["代码", "名称", "最新价", "涨跌幅", "成交额"]], title=f"板块个股", max_rows=30)
        elif choice == "6":
            return
        else:
            print(f"{Color.YELLOW}  无效选择{Color.RESET}")

    except Exception as e:
        print(f"{Color.RED}  板块分析失败: {e}{Color.RESET}")


def show_quick_screen():
    """快速选股（基础条件筛选）"""
    import pandas as pd

    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  ⚡ 快速筛选{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")

    try:
        print(f"\n{Color.BOLD}正在获取全市场股票列表...{Color.RESET}")
        all_stocks = fetcher.get_all_stocks()
        if all_stocks.empty:
            print(f"{Color.RED}  获取股票列表失败{Color.RESET}")
            return

        # 过滤ST
        all_stocks = all_stocks[~all_stocks["名称"].str.contains("ST|退", na=False)]
        all_stocks = all_stocks[all_stocks["最新价"] > 0]

        print(f"  当前共 {len(all_stocks)} 只股票")
        print(f"\n  设置筛选条件 (直接回车跳过):")

        min_price = input(f"  最低价格 (如 5): ").strip()
        max_price = input(f"  最高价格 (如 100): ").strip()
        min_change = input(f"  最低涨跌幅% (如 3): ").strip()
        max_change = input(f"  最高涨跌幅% (如 10): ").strip()
        min_turnover = input(f"  最低换手率% (如 3): ").strip()
        min_volume_ratio = input(f"  最低量比 (如 1.5): ").strip()
        min_cap = input(f"  最小市值(亿) (如 50): ").strip()
        max_cap = input(f"  最大市值(亿) (如 500): ").strip()

        result = all_stocks.copy()

        if min_price:
            result = screener.screen_by_price_range(result, min_price=float(min_price))
        if max_price:
            result = screener.screen_by_price_range(result, max_price=float(max_price))
        if min_price and max_price:
            result = screener.screen_by_price_range(result, float(min_price), float(max_price))
        if min_change:
            result = screener.screen_by_change(result, min_change=float(min_change))
        if max_change:
            result = screener.screen_by_change(result, max_change=float(max_change))
        if min_turnover:
            result = screener.screen_by_turnover(result, min_turnover=float(min_turnover))
        if min_volume_ratio:
            result = screener.screen_by_volume_ratio(result, min_ratio=float(min_volume_ratio))
        if min_cap or max_cap:
            result = screener.screen_by_market_cap(
                result,
                min_cap=float(min_cap) if min_cap else None,
                max_cap=float(max_cap) if max_cap else None
            )

        if result.empty:
            print(f"\n{Color.YELLOW}  没有符合条件的股票{Color.RESET}")
        else:
            display = result[["代码", "名称", "最新价", "涨跌幅", "换手率", "量比", "成交额"]].copy()
            display["成交额"] = display["成交额"].apply(lambda x: f"{x / 1e8:.1f}亿" if pd.notna(x) else "-")
            print_table(display, title=f"筛选结果 ({len(result)}只)", max_rows=30)

    except ValueError:
        print(f"{Color.RED}  输入格式错误，请输入数字{Color.RESET}")
    except Exception as e:
        print(f"{Color.RED}  筛选失败: {e}{Color.RESET}")


# ==================== 回测功能 ====================

def show_backtest_menu():
    """策略回测菜单"""
    print(f"\n{Color.BOLD}{Color.CYAN}{'═'*50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  📊 策略回测{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═'*50}{Color.RESET}")

    strategies = list_strategies()
    for i, (key, desc) in enumerate(strategies, 1):
        print(f"  {i}. {desc}")
    print(f"  0. 返回主菜单")
    print()

    choice = input(f"  {Color.BOLD}请选择策略 (0-{len(strategies)}): {Color.RESET}").strip()
    if choice == "0":
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(strategies):
            print(f"{Color.YELLOW}  无效选择{Color.RESET}")
            return
        strategy_key, strategy_desc = strategies[idx]
    except ValueError:
        print(f"{Color.YELLOW}  输入无效{Color.RESET}")
        return

    code = input(f"  {Color.BOLD}请输入股票代码 (如 600519): {Color.RESET}").strip()
    if not code:
        return

    days_input = input(f"  {Color.BOLD}回测周期天数 (默认500): {Color.RESET}").strip()
    days = int(days_input) if days_input.isdigit() else 500

    capital_input = input(f"  {Color.BOLD}初始资金 (默认100000): {Color.RESET}").strip()
    capital = float(capital_input) if capital_input else 100000

    print(f"\n  {Color.DIM}正在获取 {code} 的历史数据...{Color.RESET}")
    try:
        kline = fetcher.get_kline(code, count=days)
        if kline.empty:
            print(f"{Color.RED}  未找到该股票数据{Color.RESET}")
            return

        print(f"  {Color.DIM}正在运行回测: {strategy_desc}...{Color.RESET}")
        result = run_backtest(code, kline, strategy_name=strategy_key,
                              initial_capital=capital, position_pct=1.0, stop_loss_pct=0.05)
        print_backtest_report(result)
    except Exception as e:
        print(f"{Color.RED}  回测失败: {e}{Color.RESET}")


def show_chart_export():
    """K线图导出"""
    print(f"\n{Color.BOLD}{Color.CYAN}{'═'*50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  📈 K线图导出{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═'*50}{Color.RESET}")

    code = input(f"  {Color.BOLD}请输入股票代码 (如 600519): {Color.RESET}").strip()
    if not code:
        return

    print(f"  {Color.DIM}正在获取K线数据...{Color.RESET}")
    try:
        kline = fetcher.get_kline(code, count=120)
        if kline.empty:
            print(f"{Color.RED}  未找到数据{Color.RESET}")
            return

        # 尝试获取名称
        name = code
        try:
            rt = fetcher.get_realtime_quote(code)
            if not rt.empty:
                name = rt.iloc[0].get("名称", code)
        except Exception:
            pass

        save_dir = input(f"  {Color.BOLD}保存目录 (默认当前目录，直接回车): {Color.RESET}").strip() or "."

        print(f"  {Color.DIM}正在生成K线图...{Color.RESET}")
        path = plot_kline_simple(kline, stock_code=code, save_dir=save_dir)
        if path:
            print(f"\n  {Color.GREEN}✅ K线图已保存: {path}{Color.RESET}")
        else:
            print(f"\n  {Color.YELLOW}⚠️ 图表生成失败，请检查是否安装了 mplfinance:{Color.RESET}")
            print(f"  {Color.DIM}   pip install mplfinance matplotlib{Color.RESET}")
    except Exception as e:
        print(f"{Color.RED}  导出失败: {e}{Color.RESET}")


def show_akshare_data():
    """AKShare 补充数据菜单"""
    print(f"\n{Color.BOLD}{Color.CYAN}{'═'*50}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  🔍 AKShare 补充数据{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═'*50}{Color.RESET}")
    print(f"  1. 龙虎榜数据")
    print(f"  2. 融资融券汇总")
    print(f"  3. 个股融资融券")
    print(f"  4. 大宗交易")
    print(f"  5. 新股数据")
    print(f"  6. 股东增减持")
    print(f"  7. 机构持仓")
    print(f"  8. 机构推荐")
    print(f"  0. 返回主菜单")
    print()

    choice = input(f"  {Color.BOLD}请选择 (0-8): {Color.RESET}").strip()

    try:
        if choice == "1":
            print(f"\n  {Color.DIM}正在获取龙虎榜数据...{Color.RESET}")
            df = akdata.get_dragon_tiger_list()
            if not df.empty:
                print_table(df.head(20), title="龙虎榜数据", max_rows=20)
            else:
                msg = getattr(df, "_error_msg", "暂无数据")
                print(f"  {Color.YELLOW}{msg}{Color.RESET}")
        elif choice == "2":
            print(f"\n  {Color.DIM}正在获取融资融券汇总...{Color.RESET}")
            df = akdata.get_margin_trading()
            if not df.empty:
                print_table(df.head(15), title="融资融券汇总", max_rows=15)
            else:
                msg = getattr(df, "_error_msg", "暂无数据")
                print(f"  {Color.YELLOW}{msg}{Color.RESET}")
        elif choice == "3":
            code = input(f"  {Color.BOLD}请输入股票代码: {Color.RESET}").strip()
            if code:
                print(f"\n  {Color.DIM}正在获取 {code} 融资融券数据...{Color.RESET}")
                df = akdata.get_margin_trading(stock_code=code)
                if not df.empty:
                    print_table(df.tail(10), title=f"{code} 融资融券", max_rows=10)
                else:
                    msg = getattr(df, "_error_msg", "暂无数据")
                    print(f"  {Color.YELLOW}{msg}{Color.RESET}")
        elif choice == "4":
            print(f"\n  {Color.DIM}正在获取大宗交易...{Color.RESET}")
            df = akdata.get_block_trade()
            if not df.empty:
                print_table(df.head(15), title="大宗交易", max_rows=15)
            else:
                msg = getattr(df, "_error_msg", "暂无数据")
                print(f"  {Color.YELLOW}{msg}{Color.RESET}")
        elif choice == "5":
            print(f"\n  {Color.DIM}正在获取新股数据...{Color.RESET}")
            df = akdata.get_new_stock_list()
            if not df.empty:
                print_table(df.head(15), title="新股数据", max_rows=15)
            else:
                msg = getattr(df, "_error_msg", "暂无数据")
                print(f"  {Color.YELLOW}{msg}{Color.RESET}")
        elif choice == "6":
            code = input(f"  {Color.BOLD}请输入股票代码: {Color.RESET}").strip()
            if code:
                print(f"\n  {Color.DIM}正在获取 {code} 股东增减持...{Color.RESET}")
                df = akdata.get_holder_change(code)
                if not df.empty:
                    print_table(df.head(10), title=f"{code} 股东增减持", max_rows=10)
                else:
                    msg = getattr(df, "_error_msg", "暂无数据")
                    print(f"  {Color.YELLOW}{msg}{Color.RESET}")
        elif choice == "7":
            code = input(f"  {Color.BOLD}请输入股票代码: {Color.RESET}").strip()
            if code:
                print(f"\n  {Color.DIM}正在获取 {code} 机构持仓...{Color.RESET}")
                df = akdata.get_institutional_holdings(code)
                if not df.empty:
                    print_table(df.head(10), title=f"{code} 机构持仓", max_rows=10)
                else:
                    msg = getattr(df, "_error_msg", "暂无数据")
                    print(f"  {Color.YELLOW}{msg}{Color.RESET}")
        elif choice == "8":
            print(f"\n  {Color.DIM}正在获取机构推荐池...{Color.RESET}")
            df = akdata.get_institutional_recommend()
            if not df.empty:
                print_table(df.head(15), title="机构推荐/评级", max_rows=15)
            else:
                msg = getattr(df, "_error_msg", "暂无数据")
                print(f"  {Color.YELLOW}{msg}{Color.RESET}")
    except Exception as e:
        print(f"{Color.RED}  获取失败: {e}{Color.RESET}")


# ==================== 主菜单 ====================

def print_banner():
    """打印启动横幅"""
    banner = f"""
{Color.CYAN}{Color.BOLD}
╔══════════════════════════════════════════════╗
║                                              ║
║        📈 A股股票分析工具 v1.0              ║
║        数据来源: 东方财富网 (免费)           ║
║        无需API Key · 终端可视化              ║
║                                              ║
╚══════════════════════════════════════════════╝
{Color.RESET}"""
    print(banner)


def print_menu():
    """打印主菜单"""
    print(f"""
{Color.BOLD}  ┌─────────────────────────────┐
  │         主菜单              │
  ├─────────────────────────────┤
  │  1. 📊 市场概览             │
  │  2. 📈 个股分析             │
  │  3. ⭐ 自选股管理           │
  │  4. 🔍 智能选股             │
  │  5. ⚡ 快速筛选             │
  │  6. 🏭 板块分析             │
  │  7. 🔎 搜索股票             │
  │  8. 📊 盘口分析(五档)       │
  │  9. 📊 策略回测             │
  │  10. 📈 K线图导出           │
  │  11. 🔍 AKShare补充数据     │
  │  0. 退出                   │
  └─────────────────────────────┘{Color.RESET}
""")


def analyze_multiple_stocks(codes):
    """同时分析多只股票（简洁同屏版）"""
    import pandas as pd
    
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*60}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  多股同屏分析 ({len(codes)} 只){Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'='*60}{Color.RESET}\n")
    
    # 批量获取股票名称
    stock_names = {}
    try:
        quotes = fetcher.get_realtime_quote(codes)
        if not quotes.empty:
            for _, row in quotes.iterrows():
                stock_names[row['代码']] = row['名称']
    except Exception:
        pass
    
    results = []
    total = len(codes)
    
    for i, code in enumerate(codes, 1):
        code = code.strip()
        if not code:
            continue
        
        # 显示进度
        print(f"\r  {Color.DIM}正在获取 {i}/{total}: {code}...{Color.RESET}", end="", flush=True)
        
        try:
            kline = fetcher.get_kline(code, count=120, timeout=10)
            if kline.empty:
                print(f"\r  {Color.YELLOW}{code}: 未找到数据{Color.RESET}" + " " * 20)
                continue
            
            kline = calc_all_indicators(kline)
            kline = analyze_signals(kline)
            latest = kline.iloc[-1]
            
            # 使用实时行情获取的名称
            name = stock_names.get(code, code)
            price = latest["收盘"]
            change = latest.get("涨跌幅", 0)
            signals = latest.get("信号", [])
            buy_signals = [s for s in signals if "🟢" in s]
            sell_signals = [s for s in signals if "🔴" in s]
            
            # 计算关键价位
            support, resistance, buy_price, sell_price = _calc_price_levels(latest)
            
            # 计算上涨空间
            up_space = ((sell_price - price) / price) * 100 if price > 0 else 0
            
            # 评分
            score = _calc_score(latest, buy_signals, sell_signals)
            
            color = Color.RED if change > 0 else Color.GREEN if change < 0 else Color.RESET
            sign = "+" if change > 0 else ""
            
            # 判断是否涨停
            is_limit_up = abs(change) >= 9.9
            
            results.append({
                "代码": code,
                "名称": name[:6],
                "现价": f"{price:.2f}",
                "涨幅": f"{color}{sign}{change:.2f}%{Color.RESET}",
                "评分": f"{score:.0f}",
                "买点": f"{Color.GREEN}{buy_price:.2f}{Color.RESET}" if not is_limit_up else "-",
                "卖点": f"{Color.RED}{sell_price:.2f}{Color.RESET}" if not is_limit_up else f"{Color.RED}{sell_price:.2f}{Color.RESET}",
                "空间": f"{Color.RED}+{up_space:.0f}%{Color.RESET}" if up_space > 0 else f"{Color.GREEN}{up_space:.0f}%{Color.RESET}",
                "信号": f"买{len(buy_signals)}" if buy_signals else ("卖" if sell_signals else "中性"),
            })
            print(f"\r  {Color.GREEN}[OK] {code} {name[:6]} 加载成功{Color.RESET}" + " " * 20)
        except Exception as e:
            print(f"\r  {Color.YELLOW}{code}: 获取失败 ({str(e)[:20]}){Color.RESET}" + " " * 20)
            continue
    
    # 清除进度行
    print("\r" + " " * 60 + "\r", end="")
    
    if results:
        # 打印表格
        print(f"{Color.BOLD}  {'代码':<8} {'名称':<6} {'现价':>7} {'涨幅':>8} {'评分':>4} {'买点':>7} {'卖点':>7} {'空间':>6} 信号{Color.RESET}")
        print(f"  {Color.DIM}{'─'*65}{Color.RESET}")
        for r in results:
            print(f"  {r['代码']:<8} {r['名称']:<6} {r['现价']:>7} {r['涨幅']:>16} {r['评分']:>4} {r['买点']:>13} {r['卖点']:>11} {r['空间']:>8} {r['信号']}")
        
        print(f"\n  {Color.DIM}买点=建议买入价，卖点=目标卖出价，空间=潜在上涨空间{Color.RESET}")
        print(f"  {Color.DIM}涨停股买点显示'-'，建议关注次日机会{Color.RESET}")
    else:
        print(f"\n  {Color.YELLOW}没有获取到任何数据{Color.RESET}")


def main():
    """主函数"""
    print_banner()

    # 如果命令行直接传入股票代码
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() in ("w", "watch", "自选"):
            # 分析自选股
            stocks = list_stocks()
            if stocks:
                analyze_multiple_stocks(stocks)
            else:
                print(f"\n  {Color.YELLOW}自选列表为空，请先添加自选股{Color.RESET}")
                print(f"  {Color.DIM}运行 python stock.py 后选择 3.自选股管理 添加{Color.RESET}")
        elif arg.lower() == "search" and len(sys.argv) > 2:
            search_stock(sys.argv[2])
        elif arg.lower() == "market":
            show_market_overview()
        elif arg.lower() == "depth" and len(sys.argv) > 2:
            show_depth(sys.argv[2])
        elif arg.lower() == "chart" and len(sys.argv) > 2:
            # 命令行导出K线图
            code = sys.argv[2]
            save_dir = sys.argv[3] if len(sys.argv) > 3 else "."
            try:
                kline = fetcher.get_kline(code, count=120)
                if not kline.empty:
                    path = plot_kline_simple(kline, stock_code=code, save_dir=save_dir)
                    if path:
                        print(f"K线图已保存: {path}")
                    else:
                        print("图表生成失败，请安装: pip install mplfinance")
                else:
                    print("未找到数据")
            except Exception as e:
                print(f"导出失败: {e}")
        elif arg.lower() == "backtest" and len(sys.argv) > 3:
            # 命令行回测: python stock.py backtest 600519 macd_cross
            code = sys.argv[2]
            strategy = sys.argv[3]
            days = int(sys.argv[4]) if len(sys.argv) > 4 else 500
            try:
                kline = fetcher.get_kline(code, count=days)
                if not kline.empty:
                    result = run_backtest(code, kline, strategy_name=strategy)
                    print_backtest_report(result)
                else:
                    print("未找到数据")
            except Exception as e:
                print(f"回测失败: {e}")
        elif "," in arg:
            # 多股票同屏分析
            codes = [c.strip() for c in arg.split(",") if c.strip()]
            analyze_multiple_stocks(codes)
        else:
            analyze_stock(arg)
        return

    # 交互式菜单
    while True:
        print_menu()
        choice = input(f"  {Color.BOLD}请选择功能 (0-11): {Color.RESET}").strip()

        if choice == "0":
            print(f"\n{Color.CYAN}  再见！祝投资顺利！👋{Color.RESET}\n")
            break
        elif choice == "1":
            show_market_overview()
        elif choice == "2":
            code = input(f"\n  {Color.BOLD}请输入股票代码 (如 600519，多个用逗号分隔): {Color.RESET}").strip()
            if code:
                if "," in code:
                    codes = [c.strip() for c in code.split(",") if c.strip()]
                    analyze_multiple_stocks(codes)
                else:
                    analyze_stock(code)
        elif choice == "3":
            # 自选股管理
            watchlist_stocks = show_watchlist_menu()
            if watchlist_stocks:
                # 用户选择了"分析我的自选股"
                analyze_multiple_stocks(watchlist_stocks)
        elif choice == "4":
            show_stock_selection()
        elif choice == "5":
            show_quick_screen()
        elif choice == "6":
            show_sector_analysis()
        elif choice == "7":
            keyword = input(f"\n  {Color.BOLD}请输入搜索关键词 (代码或名称): {Color.RESET}").strip()
            if keyword:
                search_stock(keyword)
        elif choice == "8":
            code = input(f"\n  {Color.BOLD}请输入股票代码查看盘口 (如 600519): {Color.RESET}").strip()
            if code:
                show_depth(code)
        elif choice == "9":
            show_backtest_menu()
        elif choice == "10":
            show_chart_export()
        elif choice == "11":
            show_akshare_data()
        else:
            print(f"{Color.YELLOW}  无效选择，请重新输入{Color.RESET}")

        input(f"\n  {Color.DIM}按回车键继续...{Color.RESET}")


if __name__ == "__main__":
    import pandas as pd
    main()

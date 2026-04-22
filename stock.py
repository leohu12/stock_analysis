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
import time

# 启动时清除代理环境变量（防止VPN/代理软件干扰国内API访问）
for _k in ['http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','all_proxy','ALL_PROXY']:
    os.environ.pop(_k, None)

# 添加模块路径（确保在任何目录下运行都能正确导入）
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from fetcher import fetcher
from indicators import calc_all_indicators, analyze_signals, generate_analysis_summary
from patterns import identify_patterns
from screener import screener
from display import (
    print_table, print_kline_chart, print_indicator_chart,
    print_money_flow_chart, print_market_overview, print_stock_detail,
    print_progress, print_horizontal_bar, Color
)


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
        name = latest.get("名称", stock_code)
        date = latest.get("日期", "")
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)

        change = latest.get("涨跌幅", 0)
        color = Color.RED if change > 0 else Color.GREEN if change < 0 else Color.RESET
        sign = "+" if change > 0 else ""

        print(f"\n{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}  {name} ({stock_code})  {date_str}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'═' * 50}{Color.RESET}")

        print(f"\n  💰 当前价格: {color}{latest['收盘']:.2f}元{Color.RESET}  "
              f"{color}{sign}{change:.2f}%{Color.RESET}")
        print(f"  📊 今日区间: {latest['最低']:.2f} ~ {latest['最高']:.2f}元  "
              f"振幅 {latest.get('振幅', 0):.1f}%")
        print(f"  🔄 成交量: {latest['成交量'] / 10000:.0f}万手  "
              f"成交额: {latest['成交额'] / 1e8:.2f}亿  "
              f"换手: {latest.get('换手率', 0):.1f}%")

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
    print(f"  1. MACD金叉选股")
    print(f"  2. KDJ金叉选股")
    print(f"  3. 放量突破选股")
    print(f"  4. 均线多头排列选股")
    print(f"  5. RSI超卖选股")
    print(f"  6. 触及布林下轨选股")
    print(f"  7. 多重信号选股（2个以上买入信号）")
    print(f"  8. 返回主菜单")
    print()

    choice = input(f"  {Color.BOLD}请选择 (1-8): {Color.RESET}").strip()

    try:
        print(f"\n{Color.BOLD}正在获取全市场股票列表...{Color.RESET}")
        all_stocks = fetcher.get_all_stocks()
        if all_stocks.empty:
            print(f"{Color.RED}  获取股票列表失败{Color.RESET}")
            return

        # 过滤ST和停牌
        all_stocks = all_stocks[~all_stocks["名称"].str.contains("ST|退", na=False)]
        all_stocks = all_stocks[all_stocks["最新价"] > 0]

        result = pd.DataFrame()
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
                stocks_to_scan = all_stocks[all_stocks["最新价"] <= float(max_price)]
                print(f"  价格限制: ≤ {max_price} 元，剩余 {len(stocks_to_scan)} 只待扫描")
            
            result = screener.multi_signal_screen(stocks_to_scan)
        elif choice == "8":
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
  │  3. 🔍 智能选股             │
  │  4. ⚡ 快速筛选             │
  │  5. 🏭 板块分析             │
  │  6. 🔎 搜索股票             │
  │  0. 退出                   │
  └─────────────────────────────┘{Color.RESET}
""")


def main():
    """主函数"""
    print_banner()

    # 如果命令行直接传入股票代码
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == "search" and len(sys.argv) > 2:
            search_stock(sys.argv[2])
        elif arg.lower() == "market":
            show_market_overview()
        else:
            analyze_stock(arg)
        return

    # 交互式菜单
    while True:
        print_menu()
        choice = input(f"  {Color.BOLD}请选择功能 (0-6): {Color.RESET}").strip()

        if choice == "0":
            print(f"\n{Color.CYAN}  再见！祝投资顺利！👋{Color.RESET}\n")
            break
        elif choice == "1":
            show_market_overview()
        elif choice == "2":
            code = input(f"\n  {Color.BOLD}请输入股票代码 (如 600519): {Color.RESET}").strip()
            if code:
                analyze_stock(code)
        elif choice == "3":
            show_stock_selection()
        elif choice == "4":
            show_quick_screen()
        elif choice == "5":
            show_sector_analysis()
        elif choice == "6":
            keyword = input(f"\n  {Color.BOLD}请输入搜索关键词 (代码或名称): {Color.RESET}").strip()
            if keyword:
                search_stock(keyword)
        else:
            print(f"{Color.YELLOW}  无效选择，请重新输入{Color.RESET}")

        input(f"\n  {Color.DIM}按回车键继续...{Color.RESET}")


if __name__ == "__main__":
    import pandas as pd
    main()

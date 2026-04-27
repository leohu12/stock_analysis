# -*- coding: utf-8 -*-
"""
简化策略回测模块
无需 Backtrader，纯 Python + Pandas 实现
输入策略规则 → 输出回测报告

支持的策略：
- MACD金叉买入 / 死叉卖出
- KDJ金叉买入 / 死叉卖出
- 均线多头排列买入 / 空头排列卖出
- 布林带下轨买入 / 上轨卖出
- SuperTrend 转多买入 / 转空卖出
- RSI超卖买入 / 超买卖出
- 自定义组合策略
"""

import pandas as pd
import numpy as np
from datetime import datetime
from indicators import calc_all_indicators
from display import Color


def run_backtest(stock_code, kline_df, strategy_name="macd_cross", initial_capital=100000, position_pct=1.0, stop_loss_pct=0.05):
    """
    运行策略回测

    参数:
        stock_code: 股票代码
        kline_df: K线DataFrame (必须含 开盘,收盘,最高,最低,成交量)
        strategy_name: 策略名称
        initial_capital: 初始资金
        position_pct: 每次仓位比例 (0~1)
        stop_loss_pct: 止损比例

    返回:
        dict: 回测结果
    """
    if kline_df.empty or len(kline_df) < 30:
        return {"success": False, "error": "K线数据不足"}

    df = kline_df.copy()
    df = calc_all_indicators(df)

    # 根据策略生成买卖信号
    df = _generate_signals(df, strategy_name)

    # 模拟交易
    trades, equity_curve = _simulate_trades(df, initial_capital, position_pct, stop_loss_pct)

    # 计算统计指标
    stats = _calc_stats(trades, equity_curve, initial_capital, df)
    stats["stock_code"] = stock_code
    stats["strategy"] = strategy_name
    stats["trades"] = trades
    stats["equity_curve"] = equity_curve

    return stats


def _generate_signals(df, strategy_name):
    """根据策略名称生成买卖信号列"""
    df = df.copy()
    df["buy_signal"] = False
    df["sell_signal"] = False

    n = len(df)

    if strategy_name == "macd_cross":
        for i in range(1, n):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            if prev["DIF"] <= prev["DEA"] and curr["DIF"] > curr["DEA"]:
                df.iloc[i, df.columns.get_loc("buy_signal")] = True
            elif prev["DIF"] >= prev["DEA"] and curr["DIF"] < curr["DEA"]:
                df.iloc[i, df.columns.get_loc("sell_signal")] = True

    elif strategy_name == "kdj_cross":
        for i in range(1, n):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            if prev["K"] <= prev["D"] and curr["K"] > curr["D"] and curr["K"] < 50:
                df.iloc[i, df.columns.get_loc("buy_signal")] = True
            elif prev["K"] >= prev["D"] and curr["K"] < curr["D"] and curr["K"] > 50:
                df.iloc[i, df.columns.get_loc("sell_signal")] = True

    elif strategy_name == "ma_bull_bear":
        for i in range(1, n):
            curr = df.iloc[i]
            # 多头排列: MA5 > MA10 > MA20
            if curr["MA5"] > curr["MA10"] > curr["MA20"]:
                df.iloc[i, df.columns.get_loc("buy_signal")] = True
            elif curr["MA5"] < curr["MA10"] < curr["MA20"]:
                df.iloc[i, df.columns.get_loc("sell_signal")] = True

    elif strategy_name == "boll_bounce":
        for i in range(1, n):
            curr = df.iloc[i]
            if curr["收盘"] <= curr["BOLL_LOW"]:
                df.iloc[i, df.columns.get_loc("buy_signal")] = True
            elif curr["收盘"] >= curr["BOLL_UP"]:
                df.iloc[i, df.columns.get_loc("sell_signal")] = True

    elif strategy_name == "supertrend":
        for i in range(1, n):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            if not prev["ST_Dir"] and curr["ST_Dir"]:
                df.iloc[i, df.columns.get_loc("buy_signal")] = True
            elif prev["ST_Dir"] and not curr["ST_Dir"]:
                df.iloc[i, df.columns.get_loc("sell_signal")] = True

    elif strategy_name == "rsi_extreme":
        for i in range(1, n):
            curr = df.iloc[i]
            if curr["RSI6"] < 20:
                df.iloc[i, df.columns.get_loc("buy_signal")] = True
            elif curr["RSI6"] > 80:
                df.iloc[i, df.columns.get_loc("sell_signal")] = True

    elif strategy_name == "multi_signal":
        # 多重信号: 2个以上买入信号才买入
        for i in range(5, n):
            curr = df.iloc[i]
            buy_count = 0
            sell_count = 0

            # MACD金叉
            if i >= 1:
                prev = df.iloc[i - 1]
                if prev["DIF"] <= prev["DEA"] and curr["DIF"] > curr["DEA"]:
                    buy_count += 1
                if prev["DIF"] >= prev["DEA"] and curr["DIF"] < curr["DEA"]:
                    sell_count += 1

            # KDJ金叉
            if i >= 1:
                if prev["K"] <= prev["D"] and curr["K"] > curr["D"]:
                    buy_count += 1
                if prev["K"] >= prev["D"] and curr["K"] < curr["D"]:
                    sell_count += 1

            # RSI
            if curr["RSI6"] < 30:
                buy_count += 1
            elif curr["RSI6"] > 70:
                sell_count += 1

            # 布林带
            if curr["收盘"] <= curr["BOLL_LOW"]:
                buy_count += 1
            elif curr["收盘"] >= curr["BOLL_UP"]:
                sell_count += 1

            if buy_count >= 2:
                df.iloc[i, df.columns.get_loc("buy_signal")] = True
            if sell_count >= 2:
                df.iloc[i, df.columns.get_loc("sell_signal")] = True

    return df


def _simulate_trades(df, initial_capital, position_pct, stop_loss_pct):
    """
    模拟交易
    返回: (trades列表, 权益曲线DataFrame)
    """
    capital = initial_capital
    position = 0  # 持仓股数
    trades = []
    equity_values = []
    in_position = False
    entry_price = 0
    entry_date = None

    for i in range(len(df)):
        row = df.iloc[i]
        date = row.get("日期", i)
        price = row["收盘"]
        high = row["最高"]

        # 当前市值
        current_value = capital + position * price
        equity_values.append({"date": date, "equity": current_value})

        if not in_position:
            # 空仓，检查买入信号
            if row["buy_signal"]:
                # 买入
                invest = capital * position_pct
                if invest > 0 and price > 0:
                    shares = int(invest / price)
                    if shares > 0:
                        cost = shares * price
                        capital -= cost
                        position = shares
                        in_position = True
                        entry_price = price
                        entry_date = date
                        trades.append({
                            "type": "买入", "date": date, "price": price,
                            "shares": shares, "amount": cost,
                            "capital_after": capital
                        })
        else:
            # 持仓，检查止损或卖出信号
            # 止损检查
            stop_price = entry_price * (1 - stop_loss_pct)
            if low := row.get("最低", price):
                if low <= stop_price:
                    # 止损卖出
                    revenue = position * stop_price
                    capital += revenue
                    pnl = revenue - (position * entry_price)
                    pnl_pct = (stop_price - entry_price) / entry_price * 100
                    trades.append({
                        "type": "止损", "date": date, "price": stop_price,
                        "shares": position, "amount": revenue,
                        "pnl": pnl, "pnl_pct": pnl_pct,
                        "capital_after": capital, "hold_days": _days_between(entry_date, date)
                    })
                    position = 0
                    in_position = False
                    continue

            # 卖出信号
            if row["sell_signal"]:
                revenue = position * price
                capital += revenue
                pnl = revenue - (position * entry_price)
                pnl_pct = (price - entry_price) / entry_price * 100
                trades.append({
                    "type": "卖出", "date": date, "price": price,
                    "shares": position, "amount": revenue,
                    "pnl": pnl, "pnl_pct": pnl_pct,
                    "capital_after": capital, "hold_days": _days_between(entry_date, date)
                })
                position = 0
                in_position = False

    # 最后一天如果还持仓，按收盘价平仓
    if in_position and position > 0:
        last = df.iloc[-1]
        price = last["收盘"]
        date = last.get("日期", len(df) - 1)
        revenue = position * price
        capital += revenue
        pnl = revenue - (position * entry_price)
        pnl_pct = (price - entry_price) / entry_price * 100
        trades.append({
            "type": "平仓", "date": date, "price": price,
            "shares": position, "amount": revenue,
            "pnl": pnl, "pnl_pct": pnl_pct,
            "capital_after": capital, "hold_days": _days_between(entry_date, date)
        })

    equity_df = pd.DataFrame(equity_values)
    return trades, equity_df


def _calc_stats(trades, equity_df, initial_capital, df):
    """计算回测统计指标"""
    completed_trades = [t for t in trades if t["type"] in ("卖出", "止损", "平仓")]

    if not completed_trades:
        return {
            "success": True,
            "total_return": 0,
            "total_return_pct": 0,
            "annual_return": 0,
            "max_drawdown": 0,
            "max_drawdown_pct": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0,
            "avg_profit": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "total_trades": 0,
            "avg_hold_days": 0,
            "final_capital": initial_capital,
            "trades": trades,
        }

    # 总收益
    final_capital = completed_trades[-1]["capital_after"] if completed_trades else initial_capital
    total_return = final_capital - initial_capital
    total_return_pct = total_return / initial_capital * 100

    # 年化收益
    if len(df) > 1 and "日期" in df.columns:
        try:
            start = pd.to_datetime(df["日期"].iloc[0])
            end = pd.to_datetime(df["日期"].iloc[-1])
            years = max((end - start).days / 365, 0.01)
            annual_return = ((final_capital / initial_capital) ** (1 / years) - 1) * 100
        except Exception:
            annual_return = total_return_pct
    else:
        annual_return = total_return_pct

    # 最大回撤
    max_drawdown = 0
    max_drawdown_pct = 0
    peak = initial_capital
    for _, row in equity_df.iterrows():
        val = row["equity"]
        if val > peak:
            peak = val
        dd = peak - val
        dd_pct = dd / peak * 100 if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd
            max_drawdown_pct = dd_pct

    # 胜率
    profits = [t["pnl"] for t in completed_trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in completed_trades if t["pnl"] <= 0]
    win_count = len(profits)
    loss_count = len(losses)
    win_rate = win_count / len(completed_trades) * 100 if completed_trades else 0

    avg_profit = np.mean(profits) if profits else 0
    avg_loss = np.mean(losses) if losses else 0

    # 盈亏比
    total_profit = sum(profits)
    total_loss = abs(sum(losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    # 平均持仓天数
    hold_days = [t.get("hold_days", 0) for t in completed_trades]
    avg_hold_days = np.mean(hold_days) if hold_days else 0

    return {
        "success": True,
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2),
        "annual_return": round(annual_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 1),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "total_trades": len(completed_trades),
        "avg_hold_days": round(avg_hold_days, 1),
        "final_capital": round(final_capital, 2),
        "trades": trades,
    }


def _days_between(d1, d2):
    """计算两个日期之间的天数"""
    try:
        if isinstance(d1, str):
            d1 = pd.to_datetime(d1)
        if isinstance(d2, str):
            d2 = pd.to_datetime(d2)
        return max((d2 - d1).days, 1)
    except Exception:
        return 1


def print_backtest_report(result):
    """打印回测报告"""
    if not result.get("success"):
        print(f"{Color.RED}回测失败: {result.get('error', '未知错误')}{Color.RESET}")
        return

    code = result["stock_code"]
    strategy = result["strategy"]

    print(f"\n{Color.BOLD}{Color.CYAN}{'═'*60}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  📊 回测报告: {code} | 策略: {strategy}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═'*60}{Color.RESET}")

    # 核心指标
    ret_color = Color.RED if result["total_return"] > 0 else Color.GREEN
    print(f"\n  {Color.BOLD}核心指标:{Color.RESET}")
    print(f"    总收益率:     {ret_color}{result['total_return_pct']:+.2f}%{Color.RESET}")
    print(f"    年化收益率:   {ret_color}{result['annual_return']:+.2f}%{Color.RESET}")
    print(f"    最大回撤:     {Color.GREEN}{result['max_drawdown_pct']:.2f}%{Color.RESET}")
    print(f"    最终资金:     {result['final_capital']:.2f}")

    # 交易统计
    print(f"\n  {Color.BOLD}交易统计:{Color.RESET}")
    print(f"    总交易次数:   {result['total_trades']}")
    win_color = Color.RED if result['win_rate'] >= 50 else Color.GREEN
    print(f"    盈利次数:     {Color.RED}{result['win_count']}{Color.RESET}")
    print(f"    亏损次数:     {Color.GREEN}{result['loss_count']}{Color.RESET}")
    print(f"    胜率:         {win_color}{result['win_rate']:.1f}%{Color.RESET}")
    print(f"    盈亏比:       {result['profit_factor']:.2f}")
    print(f"    平均盈利:     {Color.RED}+{result['avg_profit']:.2f}{Color.RESET}")
    print(f"    平均亏损:     {Color.GREEN}{result['avg_loss']:.2f}{Color.RESET}")
    print(f"    平均持仓天数: {result['avg_hold_days']:.1f}天")

    # 交易明细
    trades = result.get("trades", [])
    if trades:
        print(f"\n  {Color.BOLD}交易明细:{Color.RESET}")
        print(f"  {'类型':<6} {'日期':<12} {'价格':>8} {'数量':>8} {'盈亏':>10} {'盈亏%':>8}")
        print(f"  {Color.DIM}{'─'*60}{Color.RESET}")
        for t in trades:
            ttype = t["type"]
            date = str(t["date"])[:10]
            price = t["price"]
            shares = t.get("shares", 0)
            if ttype == "买入":
                print(f"  {Color.GREEN}{ttype:<6}{Color.RESET} {date:<12} {price:>8.2f} {shares:>8} {'—':>10} {'—':>8}")
            else:
                pnl = t.get("pnl", 0)
                pnl_pct = t.get("pnl_pct", 0)
                pnl_color = Color.RED if pnl > 0 else Color.GREEN
                print(f"  {Color.RED if ttype=='卖出' else Color.YELLOW}{ttype:<6}{Color.RESET} "
                      f"{date:<12} {price:>8.2f} {shares:>8} "
                      f"{pnl_color}{pnl:>+9.2f}{Color.RESET} {pnl_color}{pnl_pct:>+7.2f}%{Color.RESET}")


def list_strategies():
    """返回所有可用策略列表"""
    return [
        ("macd_cross", "MACD金叉买入/死叉卖出"),
        ("kdj_cross", "KDJ金叉买入/死叉卖出"),
        ("ma_bull_bear", "均线多头排列买入/空头排列卖出"),
        ("boll_bounce", "布林带下轨买入/上轨卖出"),
        ("supertrend", "SuperTrend转多买入/转空卖出"),
        ("rsi_extreme", "RSI超卖买入/超买卖出"),
        ("multi_signal", "多重信号组合(2个以上信号)"),
    ]

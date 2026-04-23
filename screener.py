# -*- coding: utf-8 -*-
"""
智能选股模块
基于技术指标和策略条件筛选股票
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from fetcher import fetcher
from indicators import calc_all_indicators, analyze_signals
from display import Color

# 进度文件目录
PROGRESS_DIR = os.path.join(os.path.dirname(__file__), ".scan_progress")


def check_esc_key(stopped_event):
    """检测 ESC 键是否被按下（Windows）"""
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\x1b':  # ESC 键
                if not stopped_event.is_set():
                    stopped_event.set()
                    print(f"\n  {Color.YELLOW}用户按 ESC 中断，正在保存进度...{Color.RESET}")


class ScanProgress:
    """扫描进度管理器"""
    
    def __init__(self, strategy_name):
        self.strategy_name = strategy_name
        self.file_path = os.path.join(PROGRESS_DIR, f"{strategy_name}.json")
    
    def load(self):
        """加载上次扫描位置"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("scanned_codes", [])
            except Exception:
                pass
        return []
    
    def save(self, scanned_codes):
        """保存扫描位置"""
        os.makedirs(PROGRESS_DIR, exist_ok=True)
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "scanned_codes": scanned_codes,
                }, f, ensure_ascii=False)
        except Exception:
            pass
    
    def clear(self):
        """清除进度，重新开始"""
        if os.path.exists(self.file_path):
            os.remove(self.file_path)


class StockScreener:
    """智能选股器"""

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    # ==================== 基础筛选 ====================

    def screen_by_price_range(self, df, min_price=0, max_price=1000):
        """按价格区间筛选"""
        mask = (df["最新价"] >= min_price) & (df["最新价"] <= max_price)
        return df[mask]

    def screen_by_change(self, df, min_change=None, max_change=None):
        """按涨跌幅筛选"""
        mask = pd.Series(True, index=df.index)
        if min_change is not None:
            mask &= df["涨跌幅"] >= min_change
        if max_change is not None:
            mask &= df["涨跌幅"] <= max_change
        return df[mask]

    def screen_by_turnover(self, df, min_turnover=None, max_turnover=None):
        """按换手率筛选"""
        mask = pd.Series(True, index=df.index)
        if min_turnover is not None:
            mask &= df["换手率"] >= min_turnover
        if max_turnover is not None:
            mask &= df["换手率"] <= max_turnover
        return df[mask]

    def screen_by_volume_ratio(self, df, min_ratio=None):
        """按量比筛选"""
        if min_ratio is not None:
            return df[df["量比"] >= min_ratio]
        return df

    def screen_by_market_cap(self, df, min_cap=None, max_cap=None):
        """按市值筛选（亿元）"""
        mask = pd.Series(True, index=df.index)
        if min_cap is not None:
            mask &= df["总市值"] >= min_cap * 1e8
        if max_cap is not None:
            mask &= df["总市值"] <= max_cap * 1e8
        return df[mask]

    # ==================== 技术指标选股 ====================

    def screen_macd_golden_cross(self, df, top_n=50):
        """MACD金叉选股"""
        results = []
        codes = df["代码"].tolist()[:500]  # 限制数量避免过慢
        print(f"  正在扫描MACD金叉 (前{len(codes)}只)...")

        def check(code):
            try:
                kline = fetcher.get_kline(code, count=60)
                if kline.empty or len(kline) < 30:
                    return None
                kline = calc_all_indicators(kline)
                kline = analyze_signals(kline)
                latest = kline.iloc[-1]
                signals = latest.get("信号", [])
                if any("MACD金叉" in s for s in signals):
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "DIF": latest.get("DIF", 0),
                        "DEA": latest.get("DEA", 0),
                        "信号": ", ".join(signals),
                    }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check, code): code for code in codes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return pd.DataFrame(results).head(top_n) if results else pd.DataFrame()

    def screen_kdj_golden_cross(self, df, top_n=50):
        """KDJ金叉选股"""
        results = []
        codes = df["代码"].tolist()[:500]
        print(f"  正在扫描KDJ金叉 (前{len(codes)}只)...")

        def check(code):
            try:
                kline = fetcher.get_kline(code, count=60)
                if kline.empty or len(kline) < 30:
                    return None
                kline = calc_all_indicators(kline)
                kline = analyze_signals(kline)
                latest = kline.iloc[-1]
                signals = latest.get("信号", [])
                if any("KDJ金叉" in s for s in signals):
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "K": latest.get("K", 0),
                        "D": latest.get("D", 0),
                        "J": latest.get("J", 0),
                        "信号": ", ".join(signals),
                    }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check, code): code for code in codes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return pd.DataFrame(results).head(top_n) if results else pd.DataFrame()

    def screen_volume_breakout(self, df, top_n=50):
        """放量突破选股：成交量 > 2倍均量 且 涨幅 > 3%"""
        results = []
        codes = df["代码"].tolist()[:500]
        print(f"  正在扫描放量突破 (前{len(codes)}只)...")

        def check(code):
            try:
                kline = fetcher.get_kline(code, count=30)
                if kline.empty or len(kline) < 10:
                    return None
                kline = calc_all_indicators(kline)
                latest = kline.iloc[-1]
                if (pd.notna(latest.get("VOL_MA5")) and
                    latest["成交量"] > latest["VOL_MA5"] * 2 and
                    latest["涨跌幅"] > 3):
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "成交量(万)": round(latest["成交量"] / 10000, 0),
                        "量比": latest["成交量"] / latest["VOL_MA5"] if pd.notna(latest.get("VOL_MA5")) and latest["VOL_MA5"] > 0 else 0,
                    }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check, code): code for code in codes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return pd.DataFrame(results).head(top_n) if results else pd.DataFrame()

    def screen_ma_bullish(self, df, top_n=50):
        """均线多头排列选股：MA5 > MA10 > MA20 > MA60"""
        results = []
        codes = df["代码"].tolist()[:500]
        print(f"  正在扫描均线多头排列 (前{len(codes)}只)...")

        def check(code):
            try:
                kline = fetcher.get_kline(code, count=120)
                if kline.empty or len(kline) < 65:
                    return None
                kline = calc_all_indicators(kline)
                latest = kline.iloc[-1]
                if (pd.notna(latest.get("MA5")) and pd.notna(latest.get("MA10")) and
                    pd.notna(latest.get("MA20")) and pd.notna(latest.get("MA60")) and
                    latest["MA5"] > latest["MA10"] > latest["MA20"] > latest["MA60"]):
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "MA5": latest["MA5"],
                        "MA10": latest["MA10"],
                        "MA20": latest["MA20"],
                        "MA60": latest["MA60"],
                    }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check, code): code for code in codes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return pd.DataFrame(results).head(top_n) if results else pd.DataFrame()

    def screen_oversold_rsi(self, df, top_n=50):
        """RSI超卖选股：RSI6 < 30"""
        results = []
        codes = df["代码"].tolist()[:500]
        print(f"  正在扫描RSI超卖 (前{len(codes)}只)...")

        def check(code):
            try:
                kline = fetcher.get_kline(code, count=60)
                if kline.empty or len(kline) < 30:
                    return None
                kline = calc_all_indicators(kline)
                latest = kline.iloc[-1]
                if pd.notna(latest.get("RSI6")) and latest["RSI6"] < 30:
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "RSI6": latest["RSI6"],
                        "RSI12": latest.get("RSI12", 0),
                        "RSI24": latest.get("RSI24", 0),
                    }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check, code): code for code in codes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return pd.DataFrame(results).head(top_n) if results else pd.DataFrame()

    def screen_boll_lower(self, df, top_n=50):
        """触及布林下轨选股"""
        results = []
        codes = df["代码"].tolist()[:500]
        print(f"  正在扫描布林下轨 (前{len(codes)}只)...")

        def check(code):
            try:
                kline = fetcher.get_kline(code, count=30)
                if kline.empty or len(kline) < 20:
                    return None
                kline = calc_all_indicators(kline)
                latest = kline.iloc[-1]
                if (pd.notna(latest.get("BOLL_LOW")) and
                    latest["收盘"] <= latest["BOLL_LOW"]):
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "收盘价": latest["收盘"],
                        "布林下轨": latest["BOLL_LOW"],
                        "布林中轨": latest["BOLL_MID"],
                    }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check, code): code for code in codes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return pd.DataFrame(results).head(top_n) if results else pd.DataFrame()

    # ==================== 综合选股 ====================

    def multi_signal_screen(self, df, top_n=30, max_scan=10000):
        """多重信号选股：同时出现2个以上买入信号"""
        import signal
        import threading
        
        results = []
        all_codes = df["代码"].tolist()
        
        # 断点续扫：加载上次进度
        progress = ScanProgress("multi_signal")
        scanned_codes = progress.load()
        
        # 如果有进度，询问用户
        if scanned_codes:
            print(f"\n  {Color.CYAN}发现上次扫描进度，共已扫描 {len(scanned_codes)} 只{Color.RESET}")
            choice = input(f"  1. 继续扫描  2. 重新开始 (默认1): ").strip() or "1"
            if choice == "2":
                scanned_codes = []
                progress.clear()
                print(f"  已重置进度，重新开始扫描")
            else:
                print(f"  继续从上次位置扫描")
        else:
            scanned_codes = []
        
        # 过滤掉已扫描的股票
        codes_to_scan = [c for c in all_codes if c not in scanned_codes][:max_scan]
        total = len(codes_to_scan)
        
        if total == 0:
            print(f"  {Color.YELLOW}所有股票都已扫描过，请选择「重新开始」{Color.RESET}")
            return pd.DataFrame()
        
        stopped = threading.Event()
        
        print(f"  本次扫描 {total} 只，按 ESC 可中断...")
        
        def check(code):
            if stopped.is_set():
                return None
            try:
                kline = fetcher.get_kline(code, count=60)
                if kline.empty or len(kline) < 30:
                    return None
                kline = calc_all_indicators(kline)
                kline = analyze_signals(kline)
                latest = kline.iloc[-1]
                signals = latest.get("信号", [])
                buy_count = sum(1 for s in signals if "🟢" in s)
                sell_count = sum(1 for s in signals if "🔴" in s)
                if buy_count >= 2 and sell_count < buy_count:
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "买入信号数": buy_count,
                        "卖出信号数": sell_count,
                        "信号详情": ", ".join(signals),
                    }
            except Exception:
                pass
            return None

        completed = 0
        found_count = 0
        batch_scanned = []  # 本次扫描的代码
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check, code): code for code in codes_to_scan}
            print(f"  已扫描 0/{total} 只...", end="\r")
            for future in as_completed(futures):
                if stopped.is_set():
                    future.cancel()
                    continue
                # 检测 ESC 键
                check_esc_key(stopped)
                if stopped.is_set():
                    future.cancel()
                    continue
                code = futures[future]
                completed += 1
                batch_scanned.append(code)
                result = future.result()
                if result:
                    results.append(result)
                    found_count += 1
                print(f"  已扫描 {completed}/{total} 只... 找到 {found_count} 只", end="\r")
                
                # 每扫描20只保存一次进度
                if len(batch_scanned) % 20 == 0:
                    progress.save(scanned_codes + batch_scanned)
        
        # 最终保存进度
        progress.save(scanned_codes + batch_scanned)
        
        # 恢复信号处理
        signal.signal(signal.SIGINT, original_handler)
        
        total_scanned = len(scanned_codes) + len(batch_scanned)
        if stopped.is_set():
            print(f"\n  {Color.YELLOW}扫描被中断，已保存进度 ({total_scanned}只已扫描)，找到 {len(results)} 只符合条件{Color.RESET}")
        else:
            print(f"\n  扫描完成 (共 {total_scanned} 只)，找到 {len(results)} 只符合条件")
        
        result_df = pd.DataFrame(results)
        if not result_df.empty:
            result_df = result_df.sort_values("买入信号数", ascending=False)
        return result_df.head(top_n) if not result_df.empty else pd.DataFrame()

    def screen_potential_stocks(self, df, top_n=30, max_scan=10000, max_price=None):
        """
        潜力股筛选：价格偏低 + 主力资金持续买入
        条件：
        1. 价格在布林中轨以下（股价相对不高）
        2. 近5日主力资金净流入为正
        3. RSI 在 30-60 之间（不是超买也不是超卖）
        
        Args:
            df: 股票DataFrame
            top_n: 返回结果数量
            max_scan: 最大扫描数量
            max_price: 价格上限（可选）
        """
        import signal
        import threading
        
        # 如果有价格上限，先过滤
        if max_price is not None:
            df = df[df["最新价"].notna() & (df["最新价"] > 0) & (df["最新价"] <= max_price)]
        
        results = []
        all_codes = df["代码"].tolist()
        
        # 断点续扫：加载上次进度
        progress = ScanProgress("potential_stocks")
        scanned_codes = progress.load()
        
        # 如果有进度，询问用户
        if scanned_codes:
            print(f"\n  {Color.CYAN}发现上次扫描进度，共已扫描 {len(scanned_codes)} 只{Color.RESET}")
            choice = input(f"  1. 继续扫描  2. 重新开始 (默认1): ").strip() or "1"
            if choice == "2":
                scanned_codes = []
                progress.clear()
                print(f"  已重置进度，重新开始扫描")
            else:
                print(f"  继续从上次位置扫描")
        else:
            scanned_codes = []
        
        # 过滤掉已扫描的股票
        codes_to_scan = [c for c in all_codes if c not in scanned_codes][:max_scan]
        total = len(codes_to_scan)
        
        if total == 0:
            print(f"  {Color.YELLOW}所有股票都已扫描过，请选择「重新开始」{Color.RESET}")
            return pd.DataFrame()
        
        stopped = threading.Event()
        
        print(f"  本次扫描 {total} 只，按 ESC 可中断...")
        
        def check(code):
            if stopped.is_set():
                return None
            try:
                # 获取K线数据和资金流向
                kline = fetcher.get_kline(code, count=60)
                if kline.empty or len(kline) < 30:
                    return None
                money_flow = fetcher.get_money_flow(code)
                
                kline = calc_all_indicators(kline)
                latest = kline.iloc[-1]
                
                # 条件1: 价格在布林中轨以下
                price_in_lower_half = False
                if pd.notna(latest.get("BOLL_MID")) and pd.notna(latest.get("BOLL_LOW")):
                    boll_mid = latest["BOLL_MID"]
                    boll_low = latest["BOLL_LOW"]
                    price = latest["收盘"]
                    # 价格在布林下轨和中轨之间
                    if boll_low <= price <= boll_mid:
                        price_in_lower_half = True
                    # 或者价格刚刚从下方回升（突破布林下轨）
                    elif price > boll_low and price < boll_low * 1.03:
                        price_in_lower_half = True
                
                # 条件2: 近5日主力资金净流入为正
                main_inflow_positive = False
                main_inflow_amount = 0
                if not money_flow.empty and len(money_flow) >= 3:
                    recent_flows = money_flow.tail(5)
                    main_inflow_amount = recent_flows["主力净流入"].sum()
                    inflow_days = len(recent_flows[recent_flows["主力净流入"] > 0])
                    if main_inflow_amount > 0 and inflow_days >= 2:
                        main_inflow_positive = True
                
                # 条件3: RSI 在 30-60 之间
                rsi_ok = False
                if pd.notna(latest.get("RSI6")):
                    rsi = latest["RSI6"]
                    if 25 <= rsi <= 60:  # 放宽到25-60
                        rsi_ok = True
                
                # 获取当前涨跌幅
                current_change = latest.get("涨跌幅", 0)
                if pd.isna(current_change):
                    current_change = 0
                is_limit_up = current_change >= 9.0
                
                # 计算建议买入价（支撑位附近）
                support = latest.get("BOLL_LOW", latest["收盘"] * 0.97)
                if pd.isna(support):
                    support = latest["收盘"] * 0.97
                # 如果是涨停股，建议买入价设为涨停价
                if is_limit_up:
                    suggest_buy = round(latest["收盘"], 2)
                else:
                    # 正常股：建议在回调到布林下轨或MA20时买入
                    ma20 = latest.get("MA20", support)
                    if pd.isna(ma20):
                        ma20 = support
                    suggest_buy = round(min(support, ma20) * 1.005, 2)  # 略高于支撑
                
                # 综合评分：满足2个条件以上
                score = 0
                reasons = []
                if price_in_lower_half:
                    score += 1
                    reasons.append("价格低位")
                if main_inflow_positive:
                    score += 2  # 主力买入权重更高
                    reasons.append(f"主力净流入{main_inflow_amount/10000:.0f}万")
                if rsi_ok:
                    score += 1
                    reasons.append(f"RSI适中")
                
                if score >= 2:
                    return {
                        "代码": code,
                        "名称": df[df["代码"] == code]["名称"].values[0] if code in df["代码"].values else "",
                        "最新价": df[df["代码"] == code]["最新价"].values[0] if code in df["代码"].values else 0,
                        "涨跌幅": df[df["代码"] == code]["涨跌幅"].values[0] if code in df["代码"].values else 0,
                        "综合评分": score,
                        "入选原因": "/".join(reasons),
                        "RSI6": round(latest.get("RSI6", 0), 1) if pd.notna(latest.get("RSI6")) else None,
                        "建议买入价": suggest_buy,
                        "布林位置": f"{latest['收盘']:.2f}" if pd.notna(latest.get("BOLL_MID")) else "-",
                    }
            except Exception:
                pass
            return None

        completed = 0
        found_count = 0
        batch_scanned = []  # 本次扫描的代码
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check, code): code for code in codes_to_scan}
            print(f"  已扫描 0/{total} 只...", end="\r")
            for future in as_completed(futures):
                if stopped.is_set():
                    future.cancel()
                    continue
                # 检测 ESC 键
                check_esc_key(stopped)
                if stopped.is_set():
                    future.cancel()
                    continue
                code = futures[future]
                completed += 1
                batch_scanned.append(code)
                result = future.result()
                if result:
                    results.append(result)
                    found_count += 1
                print(f"  已扫描 {completed}/{total} 只... 找到 {found_count} 只", end="\r")
                
                # 每扫描20只保存一次进度
                if len(batch_scanned) % 20 == 0:
                    progress.save(scanned_codes + batch_scanned)
        
        # 最终保存进度
        progress.save(scanned_codes + batch_scanned)
        
        total_scanned = len(scanned_codes) + len(batch_scanned)
        if stopped.is_set():
            print(f"\n  {Color.YELLOW}扫描被中断，已保存进度 ({total_scanned}只已扫描)，找到 {len(results)} 只符合条件{Color.RESET}")
        else:
            print(f"\n  扫描完成 (共 {total_scanned} 只)，找到 {len(results)} 只符合条件")
        
        result_df = pd.DataFrame(results)
        if not result_df.empty:
            result_df = result_df.sort_values("综合评分", ascending=False)
        return result_df.head(top_n) if not result_df.empty else pd.DataFrame()


screener = StockScreener()


# ==================== 实时扫描（不依赖历史K线） ====================

# 预设场景配置
SCREEN_SCENARIOS = {
    "1": {
        "name": "追热点（今天涨得猛的）",
        "min_change": 5,
        "min_turnover": 5,
        "min_volume_ratio": 2,
        "include_limit_up": True,
        "max_price": 100,
    },
    "2": {
        "name": "找补涨（还没大涨但开始放量）",
        "min_change": 1,
        "min_turnover": 3,
        "min_volume_ratio": 3,
        "include_limit_up": False,  # 不包含涨停
        "max_price": 50,
    },
    "3": {
        "name": "低价埋伏（低价股 + 放量）",
        "min_change": 2,
        "min_turnover": 5,
        "min_volume_ratio": 2,
        "include_limit_up": False,  # 排除涨停，找还没涨停但要启动的
        "max_price": 20,
    },
    "4": {
        "name": "小市值（盘子小，弹性大）",
        "min_change": 3,
        "min_turnover": 5,
        "min_volume_ratio": 2,
        "include_limit_up": False,  # 排除涨停
        "max_price": 100,
        "prefer_small_cap": True,
    },
}


def screen_realtime_simple():
    """
    简单的实时扫描（预设场景，普通人都能看懂）
    """
    print(f"\n{'='*60}")
    print(f"{Color.CYAN}[实时选股]{Color.RESET} - 找今天值得关注的好股票")
    print(f"{'='*60}")
    print()
    print(f"  {Color.BOLD}你想找什么样的股票？{Color.RESET}")
    print()
    for key, scenario in SCREEN_SCENARIOS.items():
        print(f"  {key}. {scenario['name']}")
    print()
    print(f"  0. 自定义条件")
    print(f"  q. 取消")
    print()
    
    choice = input(f"  {Color.BOLD}请选择 (1-4, 0自定义, q取消): {Color.RESET}").strip().lower()
    
    if choice == 'q' or choice == '':
        print("  取消操作")
        return pd.DataFrame()
    
    # 使用预设场景
    if choice in SCREEN_SCENARIOS:
        scenario = SCREEN_SCENARIOS[choice]
        return screen_realtime(
            top_n=30,
            min_price=1,
            max_price=scenario.get("max_price", 100),
            min_change=scenario["min_change"],
            min_turnover=scenario["min_turnover"],
            min_volume_ratio=scenario["min_volume_ratio"],
            include_limit_up=scenario["include_limit_up"],
            prefer_small_cap=scenario.get("prefer_small_cap", False)
        )
    
    # 自定义
    if choice == "0":
        return screen_realtime_custom()
    
    print(f"{Color.YELLOW}  无效选择{Color.RESET}")
    return pd.DataFrame()


def screen_realtime_custom():
    """
    自定义实时扫描
    """
    print(f"\n{Color.BOLD}[自定义筛选条件]{Color.RESET}")
    print("(直接回车使用推荐值)")
    print()
    
    # 价格
    max_price_input = input(f"  最高价格 (回车推荐50元以内): ").strip()
    max_price = float(max_price_input) if max_price_input else 50
    
    # 涨幅
    print(f"  {Color.DIM}(涨幅越高说明越强势，但也可能追高){Color.RESET}")
    change_input = input(f"  涨幅要求 (回车推荐3%以上): ").strip()
    min_change = float(change_input) if change_input else 3
    
    # 成交量
    print(f"  {Color.DIM}(量比>2说明今天比平时成交活跃){Color.RESET}")
    vol_input = input(f"  成交量放大 (回车推荐2倍以上): ").strip()
    min_volume_ratio = float(vol_input) if vol_input else 2
    
    # 换手率
    print(f"  {Color.DIM}(换手率>5%说明交易活跃){Color.RESET}")
    turnover_input = input(f"  交易活跃度 (回车推荐5%以上): ").strip()
    min_turnover = float(turnover_input) if turnover_input else 5
    
    # 涨停
    include_limit = input(f"  包含涨停股? (y/n，回车默认y): ").strip().lower()
    include_limit_up = include_limit != "n"
    
    return screen_realtime(
        top_n=30,
        min_price=1,
        max_price=max_price,
        min_change=min_change,
        min_turnover=min_turnover,
        min_volume_ratio=min_volume_ratio,
        include_limit_up=include_limit_up,
        prefer_small_cap=False
    )


def screen_realtime(top_n=30, min_price=1, max_price=1000, 
                    min_change=3, min_turnover=1, min_volume_ratio=1.5,
                    include_limit_up=True, prefer_small_cap=False):
    """
    实时扫描潜力股（基于量价信号，不依赖历史K线指标）
    
    参数:
        top_n: 返回前N只
        min_price: 最低价格
        max_price: 最高价格
        min_change: 最小涨跌幅（%）
        min_turnover: 最小换手率（%）
        min_volume_ratio: 最小量比
        include_limit_up: 是否包含涨停股
        prefer_small_cap: 偏好小市值
    """
    print(f"\n{'='*60}")
    print(f"{Color.CYAN}[正在扫描...]{Color.RESET}")
    print(f"{'='*60}\n")
    
    # 第一步：获取全市场实时数据
    print(f"  {Color.YELLOW}正在获取实时行情...{Color.RESET}")
    try:
        df = fetcher.get_all_stocks()
        if df.empty:
            print(f"  {Color.RED}获取数据失败，请检查网络连接{Color.RESET}")
            return pd.DataFrame()
        print(f"  获取到 {len(df)} 只股票\n")
        
        # 过滤ST、退市、停牌
        df = df[~df["名称"].str.contains("ST|退", na=False)]
        df = df[df["最新价"] > 0]
        
        # 过滤创业板(300/301)和科创板(688)
        df = df[~df["代码"].str.startswith(("300", "301", "688"))]
        print(f"  过滤ST和创业板/科创板后: {len(df)} 只\n")
    except Exception as e:
        print(f"  {Color.RED}获取数据失败: {e}{Color.RESET}")
        return pd.DataFrame()
    
    # 第二步：基础条件过滤
    df_filtered = df.copy()
    
    # 价格过滤
    df_filtered = df_filtered[
        (df_filtered["最新价"] >= min_price) & 
        (df_filtered["最新价"] <= max_price)
    ]
    
    # 换手率过滤
    df_filtered = df_filtered[df_filtered["换手率"] >= min_turnover]
    
    # 量比过滤
    df_filtered = df_filtered[df_filtered["量比"] >= min_volume_ratio]
    
    # 涨幅过滤
    if include_limit_up:
        df_filtered = df_filtered[df_filtered["涨跌幅"] >= min_change]
    else:
        df_filtered = df_filtered[
            (df_filtered["涨跌幅"] >= min_change) & 
            (df_filtered["涨跌幅"] < 9.9)  # 排除涨停
        ]
    
    print(f"  基础条件过滤后: {len(df_filtered)} 只")
    
    if df_filtered.empty:
        print(f"\n  {Color.YELLOW}没有找到符合条件的股票{Color.RESET}")
        return pd.DataFrame()
    
    # 第三步：多维度评分
    results = []
    for _, row in df_filtered.iterrows():
        try:
            score = 0
            
            change = row["涨跌幅"]
            turnover = row["换手率"]
            volume_ratio = row["量比"]
            amplitude = row["振幅"] if pd.notna(row.get("振幅")) else 0
            price = row["最新价"]
            
            # 涨幅评分
            if change >= 9.5:
                score += 3
            elif change >= 7:
                score += 2
            elif change >= 5:
                score += 1
            else:
                score += 0.5
            
            # 量比评分（放量程度）
            if volume_ratio >= 5:
                score += 2
            elif volume_ratio >= 3:
                score += 1.5
            elif volume_ratio >= 2:
                score += 1
            
            # 换手率评分
            if turnover >= 10:
                score += 1.5
            elif turnover >= 5:
                score += 1
            
            # 振幅评分
            if amplitude >= 8:
                score += 1
            
            # 低价股加分（炒作空间大）
            if price <= 10:
                score += 0.5
            
            # 计算流通市值（亿）
            mkt_cap = row.get("流通市值", 0)
            if pd.notna(mkt_cap) and mkt_cap > 0:
                mkt_cap_yi = mkt_cap / 1e8
            else:
                mkt_cap_yi = 0
            
            # 小市值加分（弹性大）
            if 0 < mkt_cap_yi < 50:
                score += 1
            elif mkt_cap_yi < 100:
                score += 0.5
            
            # 计算建议买入价（基于当前价格回调2-5%）
            is_limit_up = change >= 9.5
            if is_limit_up:
                # 涨停股：建议关注次日机会
                suggest_buy = "-"
            else:
                # 正常股：建议回调2-5%时买入
                if change >= 5:
                    # 涨多了，回调风险大，等跌3-5%再买
                    suggest_buy = round(price * 0.97, 2)
                else:
                    # 涨幅适中，可以考虑回调2%买入
                    suggest_buy = round(price * 0.98, 2)
            
            results.append({
                "代码": row["代码"],
                "名称": row["名称"],
                "评分": round(score, 1),
                "现价": round(price, 2),
                "涨幅": f"{change:+.2f}%",
                "建议买入价": suggest_buy,
            })
        except Exception:
            continue
    
    # 排序并返回
    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values("评分", ascending=False)
        result_df = result_df.head(top_n).reset_index(drop=True)
    
    return result_df


if __name__ == "__main__":
    # 测试实时扫描
    print("\n" + "="*60)
    print("测试实时扫描功能")
    print("="*60 + "\n")
    
    result = screen_realtime(
        top_n=20,
        min_price=1,
        max_price=50,
        min_change=3,
        min_turnover=1,
        min_volume_ratio=2,
        include_limit_up=True
    )
    
    if not result.empty:
        print("\n筛选结果:")
        print(result.to_string())
    else:
        print("\n未找到符合条件的股票")

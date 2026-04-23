# -*- coding: utf-8 -*-
"""
智能选股模块
基于技术指标和策略条件筛选股票
"""

import os
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

    def multi_signal_screen(self, df, top_n=30, max_scan=500):
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
        
        # Ctrl+C 中断处理
        def signal_handler(sig, frame):
            if not stopped.is_set():
                stopped.set()
                print(f"\n  {Color.YELLOW}用户中断，正在保存进度...{Color.RESET}")
        original_handler = signal.signal(signal.SIGINT, signal_handler)
        
        print(f"  本次扫描 {total} 只，按 Ctrl+C 可中断...")
        
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
                code = futures[future]
                completed += 1
                batch_scanned.append(code)
                result = future.result()
                if result:
                    results.append(result)
                    found_count += 1
                print(f"  已扫描 {completed}/{total} 只... 找到 {found_count} 只", end="\r")
                
                # 每扫描50只保存一次进度
                if len(batch_scanned) % 50 == 0:
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

    def screen_potential_stocks(self, df, top_n=30, max_scan=500):
        """
        潜力股筛选：价格偏低 + 主力资金持续买入
        条件：
        1. 价格在布林中轨以下（股价相对不高）
        2. 近5日主力资金净流入为正
        3. RSI 在 30-60 之间（不是超买也不是超卖）
        """
        import signal
        import threading
        
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
        
        def signal_handler(sig, frame):
            if not stopped.is_set():
                stopped.set()
                print(f"\n  {Color.YELLOW}用户中断，正在保存进度...{Color.RESET}")
        original_handler = signal.signal(signal.SIGINT, signal_handler)
        
        print(f"  本次扫描 {total} 只，按 Ctrl+C 可中断...")
        
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
                code = futures[future]
                completed += 1
                batch_scanned.append(code)
                result = future.result()
                if result:
                    results.append(result)
                    found_count += 1
                print(f"  已扫描 {completed}/{total} 只... 找到 {found_count} 只", end="\r")
                
                # 每扫描50只保存一次进度
                if len(batch_scanned) % 50 == 0:
                    progress.save(scanned_codes + batch_scanned)
        
        # 最终保存进度
        progress.save(scanned_codes + batch_scanned)
        
        signal.signal(signal.SIGINT, original_handler)
        
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

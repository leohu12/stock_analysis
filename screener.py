# -*- coding: utf-8 -*-
"""
智能选股模块
基于技术指标和策略条件筛选股票
"""

import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from fetcher import fetcher
from indicators import calc_all_indicators, analyze_signals


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

    def multi_signal_screen(self, df, top_n=30):
        """多重信号选股：同时出现2个以上买入信号"""
        results = []
        codes = df["代码"].tolist()[:300]
        print(f"  正在扫描多重信号 (前{len(codes)}只)...")

        def check(code):
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

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(check, code): code for code in codes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        result_df = pd.DataFrame(results)
        if not result_df.empty:
            result_df = result_df.sort_values("买入信号数", ascending=False)
        return result_df.head(top_n) if not result_df.empty else pd.DataFrame()


screener = StockScreener()

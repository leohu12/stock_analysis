#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级选股模块 - 资金异动、量比异动、高股息率、业绩预告、北向资金、融资融券
"""
import pandas as pd
from datetime import datetime, timedelta

from display import Color


def _check_akshare():
    """检查AKShare是否已安装"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        return None


def _check_neodata():
    """检查NeoData是否可用"""
    try:
        from neodata_client import query_neodata
        return True
    except ImportError:
        return False


def _format_money(val):
    """格式化资金金额"""
    if abs(val) >= 1e8:
        return f"{val/1e8:.2f}亿"
    elif abs(val) >= 1e4:
        return f"{val/1e4:.0f}万"
    return f"{val:.0f}"


# ==================== 1. 资金异动选股 ====================

def screen_main_inflow(days=5, top_n=30, min_net_inflow=5000):
    """
    主力资金异动选股 - 近N日主力连续净流入

    参数:
        days: 统计天数，默认5日
        top_n: 返回前N只，默认30
        min_net_inflow: 最小主力净流入额(万元)，默认5000万
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    indicator_map = {
        3: "3日",
        5: "5日",
        10: "10日",
        20: "20日",
    }
    indicator = indicator_map.get(days, f"{days}日")

    print(f"\n  {Color.YELLOW}正在获取{indicator}主力资金排名...{Color.RESET}")

    try:
        df = ak.stock_individual_fund_flow_rank(indicator=indicator)
        if df is None or df.empty:
            print(f"  {Color.YELLOW}暂无数据{Color.RESET}")
            return pd.DataFrame()

        # 找主力净流入列
        inflow_col = None
        pct_col = None
        for col in df.columns:
            if "主力净流入" in col and "净额" in col and "占比" not in col:
                inflow_col = col
            if "主力净流入" in col and "净占比" in col:
                pct_col = col

        if inflow_col is None:
            print(f"  {Color.YELLOW}数据格式变化，无法解析{Color.RESET}")
            return pd.DataFrame()

        # 过滤ST和创业板/科创板
        df = df[~df["名称"].str.contains("ST|退", na=False)]

        # 按净流入排序
        df[inflow_col] = pd.to_numeric(df[inflow_col], errors="coerce")
        if pct_col:
            df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce")
        df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")
        df["今日涨跌幅"] = pd.to_numeric(df["今日涨跌幅"], errors="coerce")

        df = df.sort_values(inflow_col, ascending=False)

        # 格式化
        result = df.head(top_n).copy()
        result["主力净流入"] = result[inflow_col].apply(lambda x: _format_money(x))
        if pct_col:
            result["净占比"] = result[pct_col].round(2).astype(str) + "%"

        cols = ["代码", "名称", "最新价", "今日涨跌幅"]
        if pct_col:
            cols.append("净占比")
        cols.append("主力净流入")
        result = result[[c for c in cols if c in result.columns]]

        # 重命名列
        rename = {"今日涨跌幅": "涨跌幅"}
        result = result.rename(columns=rename)
        if "涨跌幅" in result.columns:
            result["涨跌幅"] = result["涨跌幅"].round(2).astype(str) + "%"

        print(f"  {Color.GREEN}找到 {len(result)} 只主力资金净流入股票{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


def screen_main_outflow(days=5, top_n=30, min_net_outflow=5000):
    """
    主力资金异动选股 - 近N日主力连续净流出（警惕）

    参数:
        days: 统计天数，默认5日
        top_n: 返回前N只，默认30
        min_net_outflow: 最小主力净流出额(万元)，默认5000万
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    indicator_map = {3: "3日", 5: "5日", 10: "10日", 20: "20日"}
    indicator = indicator_map.get(days, f"{days}日")

    print(f"\n  {Color.YELLOW}正在获取{indicator}主力资金净流出排名...{Color.RESET}")

    try:
        df = ak.stock_individual_fund_flow_rank(indicator=indicator)
        if df is None or df.empty:
            print(f"  {Color.YELLOW}暂无数据{Color.RESET}")
            return pd.DataFrame()

        inflow_col = None
        pct_col = None
        for col in df.columns:
            if "主力净流入" in col and "净额" in col and "占比" not in col:
                inflow_col = col
            if "主力净流入" in col and "净占比" in col:
                pct_col = col

        if inflow_col is None:
            return pd.DataFrame()

        df[inflow_col] = pd.to_numeric(df[inflow_col], errors="coerce")
        if pct_col:
            df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce")
        df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")
        df["今日涨跌幅"] = pd.to_numeric(df["今日涨跌幅"], errors="coerce")

        # 净流出 = 负值，取绝对值最大的
        df_out = df[df[inflow_col] < 0].copy()
        df_out["流出金额"] = -df_out[inflow_col]
        df_out = df_out.sort_values("流出金额", ascending=False)

        df_out = df_out[~df_out["名称"].str.contains("ST|退", na=False)]

        result = df_out.head(top_n).copy()
        result["主力净流出"] = result[inflow_col].apply(lambda x: _format_money(x))
        if pct_col:
            result["净占比"] = result[pct_col].round(2).astype(str) + "%"

        cols = ["代码", "名称", "最新价", "今日涨跌幅"]
        if pct_col:
            cols.append("净占比")
        cols.append("主力净流出")
        result = result[[c for c in cols if c in result.columns]]

        rename = {"今日涨跌幅": "涨跌幅"}
        result = result.rename(columns=rename)
        if "涨跌幅" in result.columns:
            result["涨跌幅"] = result["涨跌幅"].round(2).astype(str) + "%"

        print(f"  {Color.GREEN}找到 {len(result)} 只主力资金净流出股票{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


# ==================== 2. 量比/换手率异动 ====================

def screen_volume_surge(top_n=30, min_volume_ratio=3, min_turnover=3):
    """
    量比/换手率异动选股 - 放量+活跃

    参数:
        top_n: 返回前N只，默认30
        min_volume_ratio: 最小量比，默认3
        min_turnover: 最小换手率(%)，默认3
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    print(f"\n  {Color.YELLOW}正在获取量比异动排名...{Color.RESET}")

    try:
        df = ak.stock_individual_fund_flow_rank(indicator="今日")
        if df is None or df.empty:
            return pd.DataFrame()

        # 找量比和换手率列
        vr_col = None
        for col in df.columns:
            if "量比" in col:
                vr_col = col
                break

        df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")
        df["今日涨跌幅"] = pd.to_numeric(df["今日涨跌幅"], errors="coerce")
        if vr_col:
            df[vr_col] = pd.to_numeric(df[vr_col], errors="coerce")

        # 过滤ST
        df = df[~df["名称"].str.contains("ST|退", na=False)]

        # 按量比排序
        if vr_col:
            df = df.sort_values(vr_col, ascending=False)
        else:
            df = df.sort_values("今日涨跌幅", ascending=False)

        result = df.head(top_n * 2).copy()  # 多取一些再过滤

        # 应用筛选条件
        if vr_col:
            result = result[result[vr_col] >= min_volume_ratio]
        result = result.head(top_n)

        # 格式化
        cols = ["代码", "名称", "最新价", "今日涨跌幅"]
        if vr_col:
            cols.append(vr_col)
        result = result[[c for c in cols if c in result.columns]].copy()

        rename = {"今日涨跌幅": "涨跌幅"}
        result = result.rename(columns=rename)
        if "涨跌幅" in result.columns:
            result["涨跌幅"] = result["涨跌幅"].round(2).astype(str) + "%"
        if vr_col and vr_col in result.columns:
            result[vr_col] = result[vr_col].round(2)

        print(f"  {Color.GREEN}找到 {len(result)} 只量比≥{min_volume_ratio}的异动股{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


def screen_turnover_leaders(top_n=30, min_turnover=10):
    """
    换手率排行榜 - 最活跃股票

    参数:
        top_n: 返回前N只，默认30
        min_turnover: 最小换手率(%)，默认10
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    print(f"\n  {Color.YELLOW}正在获取换手率排行榜...{Color.RESET}")

    try:
        # 使用东方财富换手率排行榜
        df = ak.stock_turnover_rate_em(indicator="全部", top=top_n * 3)
        if df is None or df.empty:
            return pd.DataFrame()

        # 找关键列
        turnover_col = None
        for col in df.columns:
            if "换手率" in col:
                turnover_col = col
                break

        df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")
        if turnover_col:
            df[turnover_col] = pd.to_numeric(df[turnover_col], errors="coerce")

        # 过滤ST和停牌
        df = df[~df["名称"].str.contains("ST|退", na=False)]
        df = df[df["最新价"] > 0]

        # 排序
        if turnover_col:
            df = df.sort_values(turnover_col, ascending=False)

        result = df.head(top_n).copy()

        cols = ["代码", "名称", "最新价"]
        if turnover_col:
            cols.append(turnover_col)
        result = result[[c for c in cols if c in result.columns]].copy()

        if turnover_col and turnover_col in result.columns:
            result[turnover_col] = result[turnover_col].round(2).astype(str) + "%"

        print(f"  {Color.GREEN}找到 {len(result)} 只换手率≥{min_turnover}%的活跃股{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


# ==================== 3. 高股息率筛选 ====================

def screen_high_dividend(top_n=30, min_dividend=3, max_price=100):
    """
    高股息率价值股筛选

    参数:
        top_n: 返回前N只，默认30
        min_dividend: 最小股息率(%)，默认3
        max_price: 最高价格，默认100
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    print(f"\n  {Color.YELLOW}正在获取高股息率股票...{Color.RESET}")

    try:
        # 使用东方财富股息率排行榜
        df = ak.stock_dividend_rate_em()
        if df is None or df.empty:
            return pd.DataFrame()

        # 找股息率列
        div_col = None
        for col in df.columns:
            if "股息率" in str(col):
                div_col = col
                break

        if div_col is None:
            # 尝试其他列
            for col in df.columns:
                if any(k in str(col) for k in ["率", "yield", "Yield"]):
                    div_col = col
                    break

        if div_col is None:
            print(f"  {Color.YELLOW}无法找到股息率列，数据列: {list(df.columns)}{Color.RESET}")
            return pd.DataFrame()

        df[div_col] = pd.to_numeric(df[div_col], errors="coerce")
        df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")

        # 过滤
        df = df[~df["名称"].str.contains("ST|退", na=False)]
        df = df[df["最新价"] > 0]
        df = df[df["最新价"] <= max_price]
        df = df[df[div_col] >= min_dividend]
        df = df.sort_values(div_col, ascending=False)

        result = df.head(top_n).copy()

        cols = ["代码", "名称", "最新价"]
        if div_col:
            cols.append(div_col)
        result = result[[c for c in cols if c in result.columns]].copy()

        if div_col and div_col in result.columns:
            result[div_col] = result[div_col].round(2).astype(str) + "%"

        rename = {div_col: "股息率"} if div_col else {}
        result = result.rename(columns=rename)

        print(f"  {Color.GREEN}找到 {len(result)} 只股息率≥{min_dividend}%的价值股{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


# ==================== 4. 北向资金 ====================

def get_north_money_flow():
    """
    获取沪深港通北向资金流向

    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    print(f"\n  {Color.YELLOW}正在获取北向资金数据...{Color.RESET}")

    try:
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df is None or df.empty:
            return pd.DataFrame()

        # 只取北向（沪股通+深股通）
        df_north = df[df["资金方向"] == "北向"].copy()
        df_north["成交净买额"] = pd.to_numeric(df_north["成交净买额"], errors="coerce")
        df_north["资金净流入"] = pd.to_numeric(df_north["资金净流入"], errors="coerce")

        df_north = df_north.sort_values("成交净买额", ascending=False)

        result = df_north[["交易日", "板块", "成交净买额", "资金净流入", "上涨数", "下跌数", "相关指数", "指数涨跌幅"]].copy()
        result["成交净买额"] = result["成交净买额"].apply(lambda x: _format_money(x))
        result["资金净流入"] = result["资金净流入"].apply(lambda x: _format_money(x))
        result["指数涨跌幅"] = result["指数涨跌幅"].round(2).astype(str) + "%"

        print(f"  {Color.GREEN}北向资金数据获取成功{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


def get_north_top_stocks(indicator="今日", top_n=30):
    """
    获取北向资金持股排行榜

    参数:
        indicator: 统计周期，"今日"或"近5日"等
        top_n: 返回前N只
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    indicator_map = {
        "今日": "北向资金",
        "3日": "北向3日",
        "5日": "北向5日",
        "10日": "北向10日",
        "1月": "北向1月",
    }
    symbol = indicator_map.get(indicator, "北向资金")

    print(f"\n  {Color.YELLOW}正在获取北向资金持股排行({indicator})...{Color.RESET}")

    try:
        df = ak.stock_hsgt_hold_stock_em(symbol=symbol)
        if df is None or df.empty:
            print(f"  {Color.YELLOW}暂无数据{Color.RESET}")
            return pd.DataFrame()

        # 找关键列
        holding_col = None
        pct_col = None
        for col in df.columns:
            if "持股" in str(col) and "市值" not in str(col) and "比例" not in str(col):
                holding_col = col
            if "占" in str(col) and "比" in str(col):
                pct_col = col

        df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")
        if holding_col:
            df[holding_col] = pd.to_numeric(df[holding_col], errors="coerce")
        if pct_col:
            df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce")

        df = df.sort_values(holding_col if holding_col else df.columns[0], ascending=False)
        result = df.head(top_n).copy()

        cols = ["代码", "名称", "最新价"]
        if holding_col:
            cols.append(holding_col)
        if pct_col:
            cols.append(pct_col)
        result = result[[c for c in cols if c in result.columns]].copy()

        if holding_col and holding_col in result.columns:
            result[holding_col] = result[holding_col].apply(lambda x: _format_money(x))
        if pct_col and pct_col in result.columns:
            result[pct_col] = result[pct_col].round(4).astype(str) + "%"

        rename = {holding_col: "北向持股", pct_col: "占比"} if holding_col else {}
        result = result.rename(columns=rename)

        print(f"  {Color.GREEN}找到 {len(result)} 只北向资金重仓股{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


# ==================== 5. 融资融券 ====================

def get_margin_trading_summary():
    """
    获取全市场融资融券汇总数据

    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    print(f"\n  {Color.YELLOW}正在获取融资融券数据...{Color.RESET}")

    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")

        df = ak.stock_margin_sse(start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            print(f"  {Color.YELLOW}暂无融资融券数据{Color.RESET}")
            return pd.DataFrame()

        print(f"  {Color.GREEN}融资融券数据获取成功，共 {len(df)} 条记录{Color.RESET}")
        return df

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


def get_margin_top_stocks(top_n=30, min_margin_balance=1e8):
    """
    获取融资余额排行榜（杠杆资金活跃度）

    参数:
        top_n: 返回前N只
        min_margin_balance: 最小融资余额(元)，默认1亿
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    print(f"\n  {Color.YELLOW}正在获取融资余额排行...{Color.RESET}")

    try:
        end_date = datetime.now().strftime("%Y%m%d")

        # 上交所融资融券明细
        df = ak.stock_margin_detail_sse(date=end_date)
        if df is None or df.empty:
            print(f"  {Color.YELLOW}暂无数据{Color.RESET}")
            return pd.DataFrame()

        # 找融资余额列
        balance_col = None
        for col in df.columns:
            if "融资余额" in str(col):
                balance_col = col
                break

        if balance_col is None:
            print(f"  {Color.YELLOW}无法找到融资余额列{Color.RESET}")
            return pd.DataFrame()

        df[balance_col] = pd.to_numeric(df[balance_col], errors="coerce")
        df = df[df[balance_col] >= min_margin_balance]
        df = df.sort_values(balance_col, ascending=False)

        result = df.head(top_n).copy()

        # 找代码列
        code_col = None
        name_col = None
        for col in df.columns:
            if "代码" in str(col):
                code_col = col
            if "简称" in str(col) or "名称" in str(col):
                name_col = col

        cols = [code_col, name_col, balance_col]
        result = result[[c for c in cols if c and c in result.columns]].copy()
        result = result.rename(columns={balance_col: "融资余额(元)"})
        result["融资余额(元)"] = result["融资余额(元)"].apply(lambda x: _format_money(x))

        print(f"  {Color.GREEN}找到 {len(result)} 只融资余额较大的股票{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


# ==================== 6. 业绩预告/研报 ====================

def get_profit_forecast(top_n=30, days=30):
    """
    获取近期业绩预告/研报评级

    参数:
        top_n: 返回前N只
        days: 最近多少天，默认30
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    print(f"\n  {Color.YELLOW}正在获取近期研报评级...{Color.RESET}")

    try:
        df = ak.stock_rank_forecast_cninfo()
        if df is None or df.empty:
            print(f"  {Color.YELLOW}暂无研报数据{Color.RESET}")
            return pd.DataFrame()

        # 转换日期
        df["发布日期"] = pd.to_datetime(df["发布日期"], errors="coerce")
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df["发布日期"] >= cutoff]

        df = df.sort_values("发布日期", ascending=False)
        df = df[~df["证券简称"].str.contains("ST|退", na=False)]

        result = df.head(top_n).copy()
        result["发布日期"] = result["发布日期"].dt.strftime("%Y-%m-%d")

        cols = ["证券代码", "证券简称", "发布日期", "研究机构简称", "投资评级", "目标价格-上限", "目标价格-下限"]
        result = result[[c for c in cols if c in result.columns]].copy()
        result = result.rename(columns={
            "证券代码": "代码",
            "证券简称": "名称",
            "研究机构简称": "机构",
            "目标价格-上限": "目标价上限",
            "目标价格-下限": "目标价下限",
        })

        print(f"  {Color.GREEN}找到 {len(result)} 条近期研报{Color.RESET}")
        return result.reset_index(drop=True)

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


# ==================== 7. 筹码分布 ====================

def get_chip_distribution(stock_code):
    """
    获取个股筹码分布（成本分布）

    参数:
        stock_code: 股票代码，如 '600519'
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        print(f"  {Color.RED}需要安装AKShare: pip install akshare{Color.RESET}")
        return pd.DataFrame()

    stock_code = str(stock_code).zfill(6)
    print(f"\n  {Color.YELLOW}正在获取筹码分布数据...{Color.RESET}")

    try:
        # 东方财富筹码分布
        df = ak.stock_chip_distribution_em(symbol=stock_code)
        if df is None or df.empty:
            print(f"  {Color.YELLOW}暂无筹码数据{Color.RESET}")
            return pd.DataFrame()

        print(f"  {Color.GREEN}筹码分布数据获取成功{Color.RESET}")
        return df

    except Exception as e:
        print(f"  {Color.RED}获取失败: {e}{Color.RESET}")
        return pd.DataFrame()


# ==================== 一键综合选股 ====================

def screen_all_in_one():
    """
    综合选股 - 整合所有高级筛选条件
    """
    print(f"\n{Color.CYAN}{'='*60}{Color.RESET}")
    print(f"{Color.CYAN}[综合选股]{Color.RESET} - 多维度筛选潜力股")
    print(f"{Color.CYAN}{'='*60}{Color.RESET}")
    print()
    print("  请选择筛选维度:")
    print()
    print("  1. 资金异动 - 主力连续净流入（5日）")
    print("  2. 资金异动 - 主力连续净流出（警惕）")
    print("  3. 量比异动 - 放量活跃股")
    print("  4. 换手率排行 - 最活跃股票")
    print("  5. 高股息率 - 价值投资（股息>3%）")
    print("  6. 北向资金 - 外资重仓股")
    print("  7. 融资余额 - 杠杆资金活跃股")
    print("  8. 研报评级 - 机构看好（近30天）")
    print()
    print("  9. 查看北向资金流向")
    print("  0. 返回")
    print()

    choice = input(f"  {Color.BOLD}请选择 (0-9): {Color.RESET}").strip()

    if choice == "1":
        df = screen_main_inflow(days=5, top_n=30)
        return df
    elif choice == "2":
        df = screen_main_outflow(days=5, top_n=30)
        return df
    elif choice == "3":
        df = screen_volume_surge(top_n=30, min_volume_ratio=3)
        return df
    elif choice == "4":
        df = screen_turnover_leaders(top_n=30, min_turnover=10)
        return df
    elif choice == "5":
        df = screen_high_dividend(top_n=30, min_dividend=3)
        return df
    elif choice == "6":
        df = get_north_top_stocks(indicator="今日", top_n=30)
        return df
    elif choice == "7":
        df = get_margin_top_stocks(top_n=30)
        return df
    elif choice == "8":
        df = get_profit_forecast(top_n=30, days=30)
        return df
    elif choice == "9":
        df = get_north_money_flow()
        return df
    else:
        return pd.DataFrame()


if __name__ == "__main__":
    print("=== 测试高级选股功能 ===")
    screen_all_in_one()

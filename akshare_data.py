# -*- coding: utf-8 -*-
"""
AKShare 补充数据模块
提供东方财富API未覆盖的数据：
- 龙虎榜数据
- 融资融券数据
- 大宗交易
- 新股数据
- 股东增减持
- 机构持仓
- 机构推荐

安装依赖:
    pip install akshare

注意：AKShare 数据来源于公开网站爬虫，接口可能随网站改版而变化
"""

import pandas as pd
from datetime import datetime, timedelta


def _check_akshare():
    """检查AKShare是否已安装"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        return None


def _stock_exchange(code):
    """判断股票交易所: sh=上交所, sz=深交所"""
    code = str(code).strip()
    if code.startswith(("6", "9", "5")):
        return "sh"
    elif code.startswith(("0", "3", "2", "8")):
        return "sz"
    return "sh"


def _error_df(msg):
    """返回带错误信息的空DataFrame"""
    df = pd.DataFrame()
    df._error_msg = msg
    return df


# ==================== 龙虎榜 ====================

def get_dragon_tiger_list(trade_date=None):
    """
    获取龙虎榜数据（新浪财经）

    参数:
        trade_date: 日期字符串 YYYYMMDD，默认前一天
    返回: DataFrame
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    if trade_date is None:
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    try:
        # stock_lhb_detail_daily_sina(date="YYYYMMDD")
        df = ak.stock_lhb_detail_daily_sina(date=trade_date)
        return df
    except Exception as e:
        return _error_df(f"龙虎榜获取失败: {e}")


def get_top_institutions(trade_date=None):
    """
    获取龙虎榜机构席位明细（新浪财经）

    参数:
        trade_date: 日期字符串 YYYYMMDD，默认前一天
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    if trade_date is None:
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    try:
        # 东方财富龙虎榜-机构买卖
        df = ak.stock_lhb_detail_em(start_date=trade_date, end_date=trade_date)
        return df
    except Exception as e:
        return _error_df(f"机构席位获取失败: {e}")


# ==================== 融资融券 ====================

def get_margin_trading(stock_code=None):
    """
    获取融资融券数据

    参数:
        stock_code: 股票代码，如 '600519'。
                   注意：akshare 个股融资融券接口只支持上交所/深交所单独查询，
                   汇总接口只返回全市场数据，不支持按个股筛选。
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")

        if stock_code:
            # 个股融资融券（上交所用汇总接口，传入股票代码过滤）
            ex = _stock_exchange(stock_code)
            if ex == "sh":
                df = ak.stock_margin_detail_sse(date=end_date)
                if not df.empty and "股票代码" in df.columns:
                    df = df[df["股票代码"] == stock_code]
            else:
                df = ak.stock_margin_detail_szse(date=end_date)
                if not df.empty and "股票代码" in df.columns:
                    df = df[df["股票代码"] == stock_code]
        else:
            # 全市场汇总（上交所）
            df = ak.stock_margin_sse(start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        return _error_df(f"融资融券获取失败: {e}")


# ==================== 大宗交易 ====================

def get_block_trade(symbol=None, start_date=None, end_date=None):
    """
    获取大宗交易数据（东方财富）

    参数:
        symbol: 股票代码，如 '600519'。不传则返回全部
        start_date: 开始日期 YYYYMMDD，默认30天前
        end_date: 结束日期 YYYYMMDD，默认今天
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

    try:
        # stock_dzjy_mrmx(symbol, start_date, end_date)
        # symbol 留空则查全部
        sym = symbol if symbol else ""
        df = ak.stock_dzjy_mrmx(symbol=sym, start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        return _error_df(f"大宗交易获取失败: {e}")


# ==================== 新股数据 ====================

def get_new_stock_list():
    """
    获取新股/次新股数据（近期A股新股列表，东方财富）
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        # stock_zh_a_new_em() - 东方财富A股新股
        df = ak.stock_zh_a_new_em()
        return df
    except Exception as e:
        return _error_df(f"新股数据获取失败: {e}")


# ==================== 股东增减持 ====================

def get_holder_change(stock_code):
    """
    获取股东增减持数据（同花顺）

    参数:
        stock_code: 股票代码，如 '600452'
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        # stock_shareholder_change_ths(symbol)
        df = ak.stock_shareholder_change_ths(symbol=stock_code)
        return df
    except Exception as e:
        return _error_df(f"股东增减持获取失败: {e}")


# ==================== 机构持仓 ====================

def get_institutional_holdings(stock_code, quarter=None):
    """
    获取个股机构持仓数据（新浪财经机构持股）

    参数:
        stock_code: 股票代码，如 '600519'
        quarter: 季度字符串，如 '20241'（2024年第1季度），
                 默认使用最近季度
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    if quarter is None:
        now = datetime.now()
        quarter = f"{now.year}{(now.month - 1) // 3 + 1}"

    try:
        # stock_institute_hold_detail(stock, quarter)
        df = ak.stock_institute_hold_detail(stock=stock_code, quarter=quarter)
        return df
    except Exception as e:
        return _error_df(f"机构持仓获取失败: {e}")


# ==================== 机构推荐/评级 ====================

def get_institutional_recommend():
    """
    获取机构推荐池（机构投资评级一览）
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        df = ak.stock_institute_recommend()
        return df
    except Exception as e:
        return _error_df(f"机构推荐获取失败: {e}")

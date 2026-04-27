# -*- coding: utf-8 -*-
"""
AKShare 补充数据模块
提供东方财富API未覆盖的数据：
- 龙虎榜数据
- 融资融券数据
- 大宗交易
- 新股数据
- 股东增减持

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


def get_dragon_tiger_list(trade_date=None):
    """
    获取龙虎榜数据
    返回: DataFrame [代码, 名称, 上榜原因, 收盘价, 涨跌幅, 龙虎榜成交额, 龙虎榜净买额]
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        if trade_date is None:
            trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        # 龙虎榜每日详情
        df = ak.stock_lhb_detail_daily_sina(start_date=trade_date, end_date=trade_date)
        if df.empty:
            return df
        # 标准化列名
        rename_map = {}
        for col in df.columns:
            if "代码" in col:
                rename_map[col] = "代码"
            elif "名称" in col:
                rename_map[col] = "名称"
            elif "原因" in col or "上榜" in col:
                rename_map[col] = "上榜原因"
            elif "净买额" in col or "净买入" in col:
                rename_map[col] = "净买额"
        df.rename(columns=rename_map, inplace=True, errors="ignore")
        return df
    except Exception as e:
        return _error_df(f"龙虎榜获取失败: {e}")


def get_margin_trading(stock_code=None):
    """
    获取融资融券数据
    如果传入 stock_code，返回该股的融资融券明细
    否则返回最近的市场融资融券汇总
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        if stock_code:
            # 个股融资融券
            df = ak.stock_margin_detail_em(symbol=stock_code)
        else:
            # 市场融资融券汇总（最近30天）
            df = ak.stock_margin_em()
        return df
    except Exception as e:
        return _error_df(f"融资融券获取失败: {e}")


def get_block_trade(trade_date=None):
    """
    获取大宗交易数据
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y%m%d")
        df = ak.stock_dzjy_mrmx(symbol=trade_date)
        return df
    except Exception as e:
        return _error_df(f"大宗交易获取失败: {e}")


def get_new_stock_list():
    """
    获取新股数据（最近上市的新股列表）
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        df = ak.stock_new_em()
        return df
    except Exception as e:
        return _error_df(f"新股数据获取失败: {e}")


def get_holder_change(stock_code):
    """
    获取股东增减持数据
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        df = ak.stock_gdzc_em(symbol=stock_code)
        return df
    except Exception as e:
        return _error_df(f"股东增减持获取失败: {e}")


def get_institutional_holdings(stock_code):
    """
    获取机构持仓数据（基金持仓、北向资金等）
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        df = ak.stock_institute_hold_detail(symbol=stock_code)
        return df
    except Exception as e:
        return _error_df(f"机构持仓获取失败: {e}")


def get_top_institutions(trade_date=None):
    """
    获取龙虎榜机构专用席位数据
    """
    ak = _check_akshare()
    if ak is None:
        return _error_df("AKShare未安装: pip install akshare")

    try:
        if trade_date is None:
            trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        df = ak.stock_lhb_jgmm_detail_em(start_date=trade_date, end_date=trade_date)
        return df
    except Exception as e:
        return _error_df(f"龙虎榜机构数据获取失败: {e}")


def _error_df(msg):
    """返回带错误信息的空DataFrame"""
    df = pd.DataFrame()
    df._error_msg = msg
    return df

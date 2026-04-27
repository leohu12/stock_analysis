# -*- coding: utf-8 -*-
"""
东方财富网数据获取模块
通过东方财富网公开API获取A股数据，无需API Key
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import numpy as np
import time
import random
import os
import json
import urllib3
from datetime import datetime, timedelta

# 启动时清除所有代理环境变量（防止VPN/代理软件干扰）
for _proxy_key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                    'all_proxy', 'ALL_PROXY', 'socks_proxy', 'SOCKS_PROXY']:
    os.environ.pop(_proxy_key, None)

# 关闭SSL不安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class EastMoneyFetcher:
    """东方财富网数据获取器"""

    def __init__(self):
        self.session = requests.Session()
        # 强制不走代理（东方财富是国内网站）
        self.session.trust_env = False
        self.session.proxies = {"http": None, "https": None}

        # 模拟真实浏览器请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Referer': 'https://quote.eastmoney.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            # 'Accept-Encoding': 'gzip, deflate',  # requests 会自动处理
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        })

        # 配置连接池和重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=5,
            pool_maxsize=10,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.timeout = 15

    def _get(self, url, params=None, retries=2, timeout=15):
        """带重试的GET请求"""
        last_err = None
        for i in range(retries):
            try:
                resp = self.session.get(
                    url, params=params, timeout=timeout,
                    verify=False, allow_redirects=True
                )
                resp.raise_for_status()
                resp.encoding = 'utf-8'
                resp_text = resp.text.strip()
                if not resp_text:
                    raise ValueError(f"API返回空响应: {url}")
                return json.loads(resp_text)
            except Exception as e:
                last_err = e
                if i < retries - 1:
                    time.sleep(1)
        raise last_err

    def _post(self, url, data=None, retries=3):
        """带重试的POST请求"""
        last_err = None
        for i in range(retries):
            try:
                resp = self.session.post(
                    url, data=data, timeout=self.timeout,
                    verify=False, allow_redirects=True
                )
                resp.raise_for_status()
                resp.encoding = 'utf-8'
                return resp.json()
            except Exception as e:
                last_err = e
                if i < retries - 1:
                    wait = (i + 1) * 2
                    time.sleep(wait)
        raise last_err

    # ==================== 实时行情 ====================

    def get_realtime_quote(self, stock_codes=None):
        """
        获取实时行情数据
        stock_codes: 股票代码列表，如 ['600519', '000001']，None则获取全部沪深A股
                      也支持单个代码字符串 '600519'
        """
        if stock_codes:
            # 支持单个代码字符串或列表
            if isinstance(stock_codes, str):
                stock_codes = [stock_codes]
            
            # 单只或多只股票查询
            secids = []
            for code in stock_codes:
                secid = self._code_to_secid(code)
                if secid:
                    secids.append(secid)
            fields = "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f22,f23"
            url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
            params = {
                "fltt": 2,
                "fields": fields,
                "secids": ",".join(secids),
                "ut": "fa5fd1943c7b386f172d6893dbbd1d0c"
            }
            data = self._get(url, params)
            if data and data.get("data") and data["data"].get("diff"):
                return self._parse_quote_list(data["data"]["diff"])
        return pd.DataFrame()

    def get_all_stocks(self, max_stocks=10000):
        """获取全部A股列表和实时行情（分页获取）"""
        all_records = []
        page_size = 500
        page = 1
        
        while len(all_records) < max_stocks:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f11,f62,f128,f136,f115,f152,f124,f107,f104,f105",
            }
            try:
                data = self._get(url, params)
                if not (data and data.get("data") and data["data"].get("diff")):
                    break
                diff = data["data"]["diff"]
                records = self._parse_stock_list(diff)
                if records.empty:
                    break
                all_records.extend(records.to_dict('records'))
                # 如果实际返回数量少于请求的page_size，说明是最后一页
                actual_count = len(diff)
                if actual_count < page_size:
                    break
                page += 1
                if page > 60:  # 安全限制：最多60页
                    break
            except Exception:
                break
        
        if all_records:
            return pd.DataFrame(all_records)
        return pd.DataFrame()

    def _parse_stock_list(self, diff_list):
        """解析股票列表数据（push2接口，fltt=2已是标准单位，无需除100）"""
        records = []
        for item in diff_list:
            try:
                records.append({
                    "代码": item.get("f12", ""),
                    "名称": item.get("f14", ""),
                    "最新价": item.get("f2"),
                    "涨跌幅": item.get("f3"),
                    "涨跌额": item.get("f4"),
                    "成交量": item.get("f5", 0),
                    "成交额": item.get("f6", 0),
                    "振幅": item.get("f7"),
                    "换手率": item.get("f8"),
                    "市盈率": item.get("f9"),
                    "量比": item.get("f10"),
                    "最高": item.get("f15"),
                    "最低": item.get("f16"),
                    "今开": item.get("f17"),
                    "昨收": item.get("f18"),
                    "总市值": item.get("f20", 0),
                    "流通市值": item.get("f21", 0),
                    "涨速": item.get("f22"),
                    "市净率": item.get("f23"),
                    "60日涨幅": item.get("f152"),
                    "年初至今涨幅": item.get("f124"),
                })
            except Exception:
                continue
        return pd.DataFrame(records)

    def _parse_quote_list(self, diff_list):
        """解析单只/多只股票行情"""
        records = []
        for item in diff_list:
            try:
                records.append({
                    "代码": item.get("f12", ""),
                    "名称": item.get("f14", ""),
                    "最新价": item.get("f2", 0),
                    "涨跌幅": item.get("f3", 0),
                    "涨跌额": item.get("f4", 0),
                    "成交量": item.get("f5", 0),
                    "成交额": item.get("f6", 0),
                    "振幅": item.get("f7", 0),
                    "换手率": item.get("f8", 0),
                    "市盈率": item.get("f9", 0),
                    "量比": item.get("f10", 0),
                    "最高": item.get("f15", 0),
                    "最低": item.get("f16", 0),
                    "今开": item.get("f17", 0),
                    "昨收": item.get("f18", 0),
                    "总市值": item.get("f20", 0),
                    "流通市值": item.get("f21", 0),
                    "涨速": item.get("f22", 0),
                    "市净率": item.get("f23", 0),
                    "涨停价": item.get("f15", 0),  # 最高=涨停价
                    "跌停价": item.get("f17", 0),  # 今开=跌停价
                })
            except Exception:
                continue
        return pd.DataFrame(records)

    # ==================== 历史K线 ====================

    def get_kline(self, stock_code, period="daily", start_date=None, end_date=None, count=120, timeout=15):
        """
        获取历史K线数据（多接口容错）
        stock_code: 股票代码，如 '600519'
        period: 'daily'(日线), 'weekly'(周线), 'monthly'(月线)
        start_date: 开始日期 '20240101'
        end_date: 结束日期 '20241231'
        count: 获取条数
        timeout: 请求超时（秒）
        """
        # 尝试多个数据源
        df = self._get_kline_dcweb(stock_code, period, start_date, end_date, count, timeout)
        if not df.empty:
            return df

        df = self._get_kline_push2his(stock_code, period, start_date, end_date, count, timeout)
        if not df.empty:
            return df

        df = self._get_kline_63(stock_code, period, start_date, end_date, count, timeout)
        if not df.empty:
            return df

        return pd.DataFrame()

    def _get_kline_dcweb(self, stock_code, period="daily", start_date=None, end_date=None, count=120, timeout=15):
        """数据源1: datacenter.eastmoney.com（最稳定）"""
        secid = self._code_to_secid(stock_code)
        if not secid:
            return pd.DataFrame()

        klt_map = {"daily": 101, "weekly": 102, "monthly": 103}
        klt = klt_map.get(period, 101)

        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        params = {
            "type": "RPT_LICO_FN_CPD",
            "sty": "ALL",
            "p": 1,
            "ps": count,
            "sr": -1,
            "st": "TRADE_DATE",
            "filter": f'(SECURITY_CODE="{stock_code}")',
            "columns": "ALL",
        }

        try:
            data = self._get(url, params, timeout=timeout)
            if data and data.get("result") and data["result"].get("data"):
                records = []
                for item in data["result"]["data"]:
                    try:
                        records.append({
                            "日期": item.get("TRADE_DATE", ""),
                            "名称": item.get("SECURITY_NAME_ABBR", ""),
                            "开盘": float(item.get("OPEN_PRICE", 0)),
                            "收盘": float(item.get("CLOSE_PRICE", 0)),
                            "最高": float(item.get("HIGH_PRICE", 0)),
                            "最低": float(item.get("LOW_PRICE", 0)),
                            "成交量": int(item.get("TRADE_VOL", 0)),
                            "成交额": float(item.get("TRADE_MONEY", 0)),
                            "振幅": float(item.get("AMPLITUDE", 0)),
                            "涨跌幅": float(item.get("CHANGE_RATE", 0)),
                            "涨跌额": float(item.get("CHANGE", 0)),
                            "换手率": float(item.get("TURNOVERRATE", 0)),
                        })
                    except (ValueError, TypeError):
                        continue
                df = pd.DataFrame(records)
                if not df.empty:
                    df["日期"] = pd.to_datetime(df["日期"])
                    df = df.sort_values("日期").reset_index(drop=True)
                    return df
        except Exception:
            pass
        return pd.DataFrame()

    def _get_kline_push2his(self, stock_code, period="daily", start_date=None, end_date=None, count=120, timeout=15):
        """数据源2: push2his.eastmoney.com（原始接口）"""
        secid = self._code_to_secid(stock_code)
        if not secid:
            return pd.DataFrame()

        klt_map = {"daily": 101, "weekly": 102, "monthly": 103}
        klt = klt_map.get(period, 101)

        fields = "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f11,f62,f128,f136,f115,f152,f124,f107,f104,f105"

        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": fields,
            "klt": klt,
            "fqt": 1,
            "beg": start_date or "0",
            "end": end_date or "20500101",
            "lmt": count,
            "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
        }

        try:
            data = self._get(url, params, timeout=timeout)
            if data and data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]
                name = data["data"].get("name", "")
                df = self._parse_klines(klines, name)
                return df
        except Exception:
            pass
        return pd.DataFrame()

    def _get_kline_63(self, stock_code, period="daily", start_date=None, end_date=None, count=120, timeout=15):
        """数据源3: money.finance.sina.com.cn（新浪财经备选）"""
        if stock_code.startswith("6"):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"

        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            "symbol": symbol,
            "scale": "240" if period == "daily" else "1200" if period == "weekly" else "7200",
            "ma": "no",
            "datalen": count,
        }

        try:
            data = self._get(url, params, timeout=timeout)
            if data and isinstance(data, list):
                records = []
                for item in data:
                    try:
                        records.append({
                            "日期": item.get("day", ""),
                            "名称": "",
                            "开盘": float(item.get("open", 0)),
                            "收盘": float(item.get("close", 0)),
                            "最高": float(item.get("high", 0)),
                            "最低": float(item.get("low", 0)),
                            "成交量": int(float(item.get("volume", 0))),
                            "成交额": 0,
                            "振幅": 0,
                            "涨跌幅": 0,
                            "涨跌额": 0,
                            "换手率": 0,
                        })
                    except (ValueError, TypeError):
                        continue
                df = pd.DataFrame(records)
                if not df.empty:
                    df["日期"] = pd.to_datetime(df["日期"])
                    df = df.sort_values("日期").reset_index(drop=True)
                    # 补算涨跌幅
                    if len(df) > 1:
                        df["涨跌额"] = df["收盘"].diff()
                        df["涨跌幅"] = (df["涨跌额"] / df["收盘"].shift(1) * 100).fillna(0)
                        df["振幅"] = ((df["最高"] - df["最低"]) / df["收盘"].shift(1) * 100).fillna(0)
                    return df
        except Exception:
            pass
        return pd.DataFrame()

    def _parse_klines(self, klines, name=""):
        """解析K线数据"""
        records = []
        for line in klines:
            parts = line.split(",")
            try:
                records.append({
                    "日期": parts[0],
                    "名称": name,
                    "开盘": float(parts[1]),
                    "收盘": float(parts[2]),
                    "最高": float(parts[3]),
                    "最低": float(parts[4]),
                    "成交量": int(parts[5]),
                    "成交额": float(parts[6]),
                    "振幅": float(parts[7]),
                    "涨跌幅": float(parts[8]),
                    "涨跌额": float(parts[9]),
                    "换手率": float(parts[10]),
                })
            except (IndexError, ValueError):
                continue
        df = pd.DataFrame(records)
        if not df.empty:
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values("日期").reset_index(drop=True)
        return df

    # ==================== 资金流向 ====================

    def get_money_flow(self, stock_code):
        """获取个股资金流向"""
        secid = self._code_to_secid(stock_code)
        if not secid:
            return pd.DataFrame()

        url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "lmt": 30,
            "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
        }
        try:
            data = self._get(url, params)
            if data and data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]
                records = []
                for line in klines:
                    parts = line.split(",")
                    try:
                        records.append({
                            "日期": parts[0],
                            "主力净流入": float(parts[1]),
                            "小单净流入": float(parts[2]),
                            "中单净流入": float(parts[3]),
                            "大单净流入": float(parts[4]),
                            "超大单净流入": float(parts[5]),
                            "主力净流入占比": float(parts[6]),
                            "小单流入占比": float(parts[7]),
                            "中单流入占比": float(parts[8]),
                            "大单流入占比": float(parts[9]),
                            "超大单流入占比": float(parts[10]),
                        })
                    except (IndexError, ValueError):
                        continue
                return pd.DataFrame(records)
        except Exception:
            pass
        return pd.DataFrame()

    # ==================== 板块数据 ====================

    def get_sector_list(self, sector_type="industry"):
        """
        获取板块列表
        sector_type: 'industry'(行业板块), 'concept'(概念板块), 'area'(地区板块)
        """
        fs_map = {
            "industry": "m:90+t:2+f:!50",
            "concept": "m:90+t:3+f:!50",
            "area": "m:90+t:1+f:!50",
        }
        fs = fs_map.get(sector_type, fs_map["industry"])

        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs,
            "fields": "f2,f3,f4,f8,f12,f14,f104,f105,f128,f136,f140,f141",
        }
        data = self._get(url, params)
        if data and data.get("data") and data["data"].get("diff"):
            records = []
            for item in data["data"]["diff"]:
                try:
                    records.append({
                        "代码": item.get("f12", ""),
                        "名称": item.get("f14", ""),
                        "涨跌幅": self._safe_div(item.get("f3"), 100),
                        "涨跌额": self._safe_div(item.get("f4"), 100),
                        "换手率": self._safe_div(item.get("f8"), 100),
                        "领涨股": item.get("f140", ""),
                        "领涨股涨幅": self._safe_div(item.get("f136"), 100),
                        "上涨家数": item.get("f104", 0),
                        "下跌家数": item.get("f105", 0),
                    })
                except Exception:
                    continue
            return pd.DataFrame(records)
        return pd.DataFrame()

    def get_sector_stocks(self, sector_code, sector_type="industry"):
        """获取板块内个股"""
        fs_map = {
            "industry": f"m:90+t:2+f:!50+{sector_code}",
            "concept": f"m:90+t:3+f:!50+{sector_code}",
        }
        fs = fs_map.get(sector_type, fs_map["industry"])

        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 500,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs,
            "fields": "f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18,f20,f21",
        }
        data = self._get(url, params)
        if data and data.get("data") and data["data"].get("diff"):
            return self._parse_stock_list(data["data"]["diff"])
        return pd.DataFrame()

    def get_sector_money_flow(self, sector_type="industry"):
        """获取板块资金流向"""
        fs_map = {
            "industry": "m:90+t:2+f:!50",
            "concept": "m:90+t:3+f:!50",
        }
        fs = fs_map.get(sector_type, fs_map["industry"])

        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 50,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f62",
            "fs": fs,
            "fields": "f2,f3,f4,f8,f12,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87",
        }
        data = self._get(url, params)
        if data and data.get("data") and data["data"].get("diff"):
            records = []
            for item in data["data"]["diff"]:
                try:
                    records.append({
                        "代码": item.get("f12", ""),
                        "名称": item.get("f14", ""),
                        "涨跌幅": self._safe_div(item.get("f3"), 100),
                        "主力净流入": item.get("f62", 0),
                        "超大单净流入": item.get("f184", 0),
                        "5日主力净流入": item.get("f66", 0),
                        "10日主力净流入": item.get("f69", 0),
                    })
                except Exception:
                    continue
            return pd.DataFrame(records)
        return pd.DataFrame()

    # ==================== 涨跌统计 ====================

    def get_market_overview(self):
        """获取市场概况（涨跌家数、涨停跌停等）"""
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": 2,
            "fields": "f2,f3,f4,f6,f12,f14",
            "secids": "1.000001,0.399001,0.399006,1.000688,0.399005",
            "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
        }
        data = self._get(url, params)
        if data and data.get("data") and data["data"].get("diff"):
            result = {}
            for item in data["data"]["diff"]:
                code = item.get("f12", "")
                name = item.get("f14", "")
                result[name] = {
                    "代码": code,
                    "最新价": self._safe_div(item.get("f2"), 1000),
                    "涨跌幅": self._safe_div(item.get("f3"), 100),
                    "涨跌额": self._safe_div(item.get("f4"), 1000),
                    "成交额": item.get("f6", 0),
                }
            return result
        return {}

    def get_limit_stats(self):
        """获取涨停跌停统计"""
        # 涨停
        url_up = "https://push2ex.eastmoney.com/getTopicZTPool"
        params_up = {
            "ut": "7eea3edcaed734bea9telecast",
            "dpt": "wz.ztzt",
            "Ession": "web",
            "date": datetime.now().strftime("%Y%m%d"),
        }
        try:
            data_up = self._get(url_up, params_up)
            zt_count = len(data_up.get("data", {}).get("pool", [])) if data_up.get("data") else 0
        except Exception:
            zt_count = 0

        # 跌停
        url_down = "https://push2ex.eastmoney.com/getTopicDTPool"
        params_down = {
            "ut": "7eea3edcaed734bea9telecast",
            "dpt": "wz.dtzt",
            "Ession": "web",
            "date": datetime.now().strftime("%Y%m%d"),
        }
        try:
            data_down = self._get(url_down, params_down)
            dt_count = len(data_down.get("data", {}).get("pool", [])) if data_down.get("data") else 0
        except Exception:
            dt_count = 0

        return {"涨停数": zt_count, "跌停数": dt_count}

    # ==================== 搜索股票 ====================

    def search_stock(self, keyword):
        """搜索股票（支持代码或名称模糊搜索）"""
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": keyword,
            "type": 14,
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": 10,
        }
        data = self._get(url, params)
        results = []
        if data and data.get("QuotationCodeTable"):
            for item in data["QuotationCodeTable"]["Data"]:
                # 支持：A股、沪A、深A、创业板、科创板、北交所
                type_name = item.get("SecurityTypeName", "")
                if any(t in type_name for t in ["A", "创", "科", "北"]):
                    results.append({
                        "代码": item.get("Code", ""),
                        "名称": item.get("Name", ""),
                        "市场": item.get("MktNum", ""),
                    })
        return results

    # ==================== 工具方法 ====================

    def _code_to_secid(self, code):
        """股票代码转东方财富secid格式"""
        code = str(code).strip()
        if code.startswith("6") or code.startswith("9"):
            return f"1.{code}"  # 上海
        elif code.startswith("0") or code.startswith("3") or code.startswith("2"):
            return f"0.{code}"  # 深圳
        elif code.startswith("8") or code.startswith("4"):
            return f"0.{code}"  # 北交所
        return None

    @staticmethod
    def _safe_div(value, divisor):
        """安全除法"""
        try:
            if value is None or value == "-":
                return None
            return round(float(value) / divisor, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return None


# ==================== 新浪免费实时行情（含五档盘口）====================

class SinaFetcher:
    """
    新浪财经免费实时行情获取器
    参考 easyquotation (https://github.com/shidenggui/easyquotation)
    特点：
    - 1秒级推送，速度快
    - 包含五档买卖盘（买一~买五、卖一~卖五）
    - 适合盘中快速刷新
    """

    BASE_URL = "http://hq.sinajs.cn/?rn={}&list={}"
    HEADERS = {
        "Referer": "https://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # A股字段映射（按逗号分割后的索引）
    # 返回格式: var hq_str_sh600000="名称,开盘,昨收,现价,最高,最低,竞买价,竞卖价,成交量,成交额,买1量,买1价,买2量,买2价,买3量,买3价,买4量,买4价,买5量,买5价,卖1量,卖1价,卖2量,卖2价,卖3量,卖3价,卖4量,卖4价,卖5量,卖5价,日期,时间";
    FIELDS = [
        "名称", "开盘价", "昨收", "最新价", "最高", "最低",
        "买一价", "卖一价", "成交量", "成交额",
        "买1量", "买1价", "买2量", "买2价", "买3量", "买3价",
        "买4量", "买4价", "买5量", "买5价",
        "卖1量", "卖1价", "卖2量", "卖2价", "卖3量", "卖3价",
        "卖4量", "卖4价", "卖5量", "卖5价",
        "日期", "时间",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.proxies = {"http": None, "https": None}
        self.session.headers.update(self.HEADERS)

    @staticmethod
    def _to_sina_code(code):
        """转为新浪代码格式: sh600000 / sz000001"""
        code = str(code).strip()
        if code.startswith(("6", "9", "5")):
            return f"sh{code}"
        return f"sz{code}"

    def get_realtime_quote(self, stock_codes):
        """
        获取新浪实时行情（含五档）
        stock_codes: 股票代码列表或单个字符串，如 ['600519', '000001']
        返回: DataFrame
        """
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]

        sina_codes = [self._to_sina_code(c) for c in stock_codes]
        # 新浪接口单次建议不超过 800 只
        chunks = [sina_codes[i:i + 800] for i in range(0, len(sina_codes), 800)]

        all_records = []
        for chunk in chunks:
            url = self.BASE_URL.format(random.randint(10_000_000, 99_999_999), ",".join(chunk))
            try:
                resp = self.session.get(url, timeout=15, verify=False)
                resp.encoding = "gbk"
                records = self._parse_response(resp.text)
                all_records.extend(records)
            except Exception:
                continue

        return pd.DataFrame(all_records)

    def _parse_response(self, text):
        """解析新浪返回的 JS 变量文本"""
        records = []
        for line in text.strip().split(";"):
            line = line.strip()
            if not line:
                continue
            # 提取等号后双引号内的内容
            if "=" not in line:
                continue
            parts = line.split("=", 1)
            left = parts[0].strip()
            right = parts[1].strip().strip('"')
            if not right:
                continue

            # 提取代码
            code_match = left.split("_")[-1] if "_" in left else ""
            code = code_match.replace("sh", "").replace("sz", "") if code_match else ""

            # 分割字段
            vals = right.split(",")
            if len(vals) < 33:
                continue

            record = {"代码": code}
            for i, field in enumerate(self.FIELDS):
                if i < len(vals):
                    val = vals[i].strip()
                    if field in ("名称", "日期", "时间"):
                        record[field] = val
                    else:
                        try:
                            record[field] = float(val) if val else 0.0
                        except (ValueError, TypeError):
                            record[field] = 0.0
                else:
                    record[field] = None
            records.append(record)
        return records

    def get_depth5(self, stock_code):
        """
        获取五档盘口（买一~买五、卖一~卖五）
        返回: dict
        """
        df = self.get_realtime_quote([stock_code])
        if df.empty:
            return {}
        row = df.iloc[0]
        depth = {
            "代码": row.get("代码", ""),
            "名称": row.get("名称", ""),
            "最新价": row.get("最新价", 0),
            "买一价": row.get("买一价", 0),
            "卖一价": row.get("卖一价", 0),
            "买盘": [],
            "卖盘": [],
        }
        for i in range(1, 6):
            b_qty = row.get(f"买{i}量", 0)
            b_prc = row.get(f"买{i}价", 0)
            s_qty = row.get(f"卖{i}量", 0)
            s_prc = row.get(f"卖{i}价", 0)
            depth["买盘"].append({"档": i, "价": b_prc, "量": int(b_qty / 100) if b_qty else 0})  # 转为手
            depth["卖盘"].append({"档": i, "价": s_prc, "量": int(s_qty / 100) if s_qty else 0})
        return depth


# ==================== 全局实例 ====================
fetcher = EastMoneyFetcher()
sina_fetcher = SinaFetcher()

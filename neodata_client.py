#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NeoData金融数据查询客户端"""
import json
import os
import sys
import requests
import time
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_SCRIPTS = "C:/Users/leo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/neodata-financial-search/scripts"
TOKEN_PATH = "C:/Users/leo/.workbuddy/.neodata_token"
API_URL = "https://copilot.tencent.com/agenttool/v1/neodata"


def get_token():
    """获取token"""
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as f:
            return f.read().strip()
    return None


def save_token(token):
    """保存token"""
    with open(TOKEN_PATH, 'w') as f:
        f.write(token)


def query_neodata(query_text, data_type="all"):
    """
    查询NeoData金融数据
    
    Args:
        query_text: 自然语言查询
        data_type: "all"(默认), "api"(仅结构化), "doc"(仅文章)
    
    Returns:
        dict: 查询结果
    """
    token = get_token()
    if not token:
        return {"error": "Token not found", "suc": False}
    
    payload = {
        "query": query_text,
        "channel": "neodata",
        "sub_channel": "workbuddy",
        "data_type": data_type
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        # Token过期处理
        if result.get("code") in ["40101", "401", "403"]:
            return {"error": "Token expired", "code": result.get("code"), "suc": False}
        
        return result
    except Exception as e:
        return {"error": str(e), "suc": False}


def get_stock_news(stock_name, stock_code="", limit=5, days=30):
    """
    获取个股财经新闻（只返回最近days天的数据）
    
    Args:
        stock_name: 股票名称
        stock_code: 股票代码
        limit: 返回数量
        days: 只返回最近多少天的数据（默认30天）
    
    Returns:
        list: 新闻列表
    """
    query = f"{stock_name} {stock_code} 最新新闻 公告 研报".strip()
    result = query_neodata(query, "all")
    
    if not result.get("suc"):
        return []
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days)
    
    news_list = []
    doc_data = result.get("data", {}).get("docData", {}).get("docRecall", [])
    
    for group in doc_data:
        for doc in group.get("docList", []):
            # 转换时间戳
            pub_time = doc.get("publishTime", 0)
            if pub_time:
                pub_date = datetime.fromtimestamp(pub_time)
                # 只保留最近days天的新闻
                if pub_date < cutoff_date:
                    continue
                pub_time_str = pub_date.strftime("%Y-%m-%d")
            else:
                continue  # 没有时间戳的跳过
            
            news_list.append({
                "title": doc.get("title", ""),
                "content": doc.get("content", "")[:500],  # 截取前500字
                "pub_time": pub_time_str,
                "url": doc.get("url", ""),
                "source": doc.get("source", "") or doc.get("site", "") or "财经"
            })
            
            if len(news_list) >= limit:
                break
        if len(news_list) >= limit:
            break
    
    return news_list


def get_stock_events(stock_name, stock_code="", days=30):
    """
    获取个股重大事件（股权变动等），只返回最近days天的数据
    
    Args:
        stock_name: 股票名称
        stock_code: 股票代码
        days: 只返回最近多少天的数据（默认30天）
    
    Returns:
        dict: 事件信息
    """
    query = f"{stock_name} {stock_code} 股权变动 股东人数 高管增持减持".strip()
    result = query_neodata(query, "api")
    
    if not result.get("suc"):
        return {}
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days)
    
    api_data = result.get("data", {}).get("apiData", {}).get("apiRecall", [])
    
    for item in api_data:
        if item.get("type") == "股权变动事件提醒":
            content = item.get("content", "")
            # 检查内容中是否包含最近日期的数据
            # 股权变动通常包含日期如 "2026-03-31"
            import re
            date_matches = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
            
            # 如果有日期，检查是否在最近days天内
            if date_matches:
                # 取最新的日期
                latest_date_str = date_matches[0]
                try:
                    latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
                    if latest_date >= cutoff_date:
                        return {
                            "type": item.get("type", ""),
                            "desc": item.get("desc", ""),
                            "content": content,
                            "tag": item.get("tag", "")
                        }
                    else:
                        # 数据太旧，返回空
                        return {}
                except:
                    pass
            
            # 如果没有日期或解析失败，返回数据（保守策略）
            return {
                "type": item.get("type", ""),
                "desc": item.get("desc", ""),
                "content": content,
                "tag": item.get("tag", "")
            }
    
    return {}


def get_capital_flow(stock_name, stock_code=""):
    """
    获取个股资金流向详情
    
    Args:
        stock_name: 股票名称
        stock_code: 股票代码
    
    Returns:
        dict: 资金流向信息
    """
    query = f"{stock_name} {stock_code} 资金流向 主力资金".strip()
    result = query_neodata(query, "api")
    
    if not result.get("suc"):
        return {}
    
    api_data = result.get("data", {}).get("apiData", {}).get("apiRecall", [])
    
    for item in api_data:
        if "资金流向" in item.get("type", "") or "资金" in item.get("desc", ""):
            return {
                "type": item.get("type", ""),
                "content": item.get("content", ""),
                "tag": item.get("tag", "")
            }
    
    return {}


def get_analysis_report(stock_name, stock_code="", days=30):
    """
    获取个股分析报告摘要，只返回最近days天的数据
    
    Args:
        stock_name: 股票名称
        stock_code: 股票代码
        days: 只返回最近多少天的数据（默认30天）
    
    Returns:
        dict: 分析报告信息
    """
    query = f"{stock_name} {stock_code} 分析 研报 机构评级 目标价".strip()
    result = query_neodata(query, "all")
    
    if not result.get("suc"):
        return {}
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days)
    
    reports = []
    doc_data = result.get("data", {}).get("docData", {}).get("docRecall", [])
    
    for group in doc_data:
        for doc in group.get("docList", []):
            pub_time = doc.get("publishTime", 0)
            if pub_time:
                pub_date = datetime.fromtimestamp(pub_time)
                # 只保留最近days天的研报
                if pub_date < cutoff_date:
                    continue
                pub_time_str = pub_date.strftime("%Y-%m-%d")
            else:
                continue  # 没有时间戳的跳过
            
            reports.append({
                "title": doc.get("title", ""),
                "content": doc.get("content", "")[:800],  # 截取前800字
                "pub_time": pub_time_str,
                "source": doc.get("source", "") or doc.get("site", "") or "财经"
            })
            
            if len(reports) >= 2:  # 只取前2篇
                break
        if len(reports) >= 2:
            break
    
    return {"reports": reports}


def format_news_for_display(news_list):
    """格式化新闻列表为可读文本"""
    if not news_list:
        return "暂无相关新闻"
    
    lines = []
    for i, news in enumerate(news_list, 1):
        lines.append(f"  {i}. 【{news['pub_time']}】{news['title']}")
        if news.get('content'):
            # 简化内容，取摘要
            content = news['content'][:150].replace('\n', ' ')
            lines.append(f"     {content}...")
        lines.append("")
    
    return '\n'.join(lines)


def format_events_for_display(events, days=30):
    """格式化事件信息为可读文本，只显示最近days天的数据"""
    if not events:
        return "暂无重大事件"
    
    content = events.get("content", "")
    if not content:
        return "暂无重大事件"
    
    # 解析内容，只保留最近days天的记录
    cutoff_date = datetime.now() - timedelta(days=days)
    lines = content.split('\n')
    filtered_lines = []
    
    import re
    for line in lines:
        if not line.strip():
            continue
        # 查找日期格式 YYYY-MM-DD
        date_matches = re.findall(r'(\d{4}-\d{2}-\d{2})', line)
        if date_matches:
            # 取第一个日期（发生日期）
            try:
                event_date = datetime.strptime(date_matches[0], "%Y-%m-%d")
                if event_date >= cutoff_date:
                    filtered_lines.append(line)
            except:
                # 日期解析失败，保留该行
                filtered_lines.append(line)
        else:
            # 没有日期的行（如标题），保留
            filtered_lines.append(line)
    
    if not filtered_lines:
        return "暂无近30天股权变动数据"
    
    return "  " + "\n  ".join(filtered_lines)


def format_capital_flow_for_display(capital):
    """格式化资金流向为可读文本"""
    if not capital:
        return "暂无资金流向数据"
    
    content = capital.get("content", "")
    return f"  {content}"


def get_institutional_sentiment(stock_name, stock_code="", days=30):
    """
    获取机构观点（目标价、基金持股、机构评级）

    Args:
        stock_name: 股票名称
        stock_code: 股票代码
        days: 只返回最近多少天的数据（默认30天）

    Returns:
        dict: 机构观点信息
    """
    query = f"{stock_name} {stock_code} 机构目标价 基金持股 机构评级 研究观点".strip()
    result = query_neodata(query, "api")

    if not result.get("suc"):
        return {}

    cutoff_date = datetime.now() - timedelta(days=days)
    api_data = result.get("data", {}).get("apiData", {}).get("apiRecall", [])

    for item in api_data:
        if item.get("type") == "市场观点":
            content = item.get("content", "")
            if not content:
                continue
            return {
                "type": item.get("type", ""),
                "content": content,
                "tag": item.get("tag", "")
            }

    return {}


def get_margin_trading_data(stock_name, stock_code=""):
    """
    获取融资融券数据

    Args:
        stock_name: 股票名称
        stock_code: 股票代码

    Returns:
        dict: 融资融券数据
    """
    query = f"{stock_name} {stock_code} 融资余额 融券余额 杠杆资金 两融".strip()
    result = query_neodata(query, "api")

    if not result.get("suc"):
        return {}

    api_data = result.get("data", {}).get("apiData", {}).get("apiRecall", [])

    for item in api_data:
        if item.get("type") == "A股融资融券情况":
            content = item.get("content", "")
            if not content:
                continue
            return {
                "type": item.get("type", ""),
                "content": content,
                "tag": item.get("tag", "")
            }

    return {}


def format_margin_for_display(data):
    """格式化融资融券数据为可读文本"""
    if not data:
        return "暂无融资融券数据"

    content = data.get("content", "")
    if not content:
        return "暂无融资融券数据"

    # 提取关键行
    lines = content.split('\n')
    key_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 保留包含关键数据的行
        if any(k in line for k in ['融资余额', '融券余额', '净买入', '增幅', '差额', '5连增', '5连降']):
            key_lines.append(line)

    if not key_lines:
        # 如果没找到关键行，取前3行
        key_lines = [l.strip() for l in lines[:3] if l.strip()]

    return "  " + "\n  ".join(key_lines[:6])


def format_sentiment_for_display(data):
    """格式化机构观点数据为可读文本"""
    if not data:
        return "暂无机构观点"

    content = data.get("content", "")
    if not content:
        return "暂无机构观点"

    # 提取关键行
    lines = content.split('\n')
    key_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 保留包含关键数据的行
        if any(k in line for k in ['目标价', '评级', '持股比例', '基金', '机构调研', '利好', '利空']):
            key_lines.append(line)

    if not key_lines:
        # 如果没找到关键行，取前3行
        key_lines = [l.strip() for l in lines[:3] if l.strip()]

    return "  " + "\n  ".join(key_lines[:6])


if __name__ == "__main__":
    # 测试
    print("=== 测试NeoData客户端 ===")

    # 测试新闻查询
    news = get_stock_news("贵州茅台", "600519", limit=3)
    print("\n【新闻】")
    print(format_news_for_display(news))

    # 测试资金流向
    capital = get_capital_flow("贵州茅台", "600519")
    print("\n【资金流向】")
    print(format_capital_flow_for_display(capital))

    # 测试股权变动
    events = get_stock_events("贵州茅台", "600519")
    print("\n【股权变动】")
    print(format_events_for_display(events))

    # 测试融资融券
    margin = get_margin_trading_data("贵州茅台", "600519")
    print("\n【融资融券】")
    print(format_margin_for_display(margin))

    # 测试机构观点
    sentiment = get_institutional_sentiment("贵州茅台", "600519")
    print("\n【机构观点】")
    print(format_sentiment_for_display(sentiment))

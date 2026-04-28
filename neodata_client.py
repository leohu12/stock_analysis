#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NeoData金融数据查询客户端"""
import json
import os
import sys
import requests
import time

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


def get_stock_news(stock_name, stock_code="", limit=5):
    """
    获取个股财经新闻
    
    Args:
        stock_name: 股票名称
        stock_code: 股票代码
        limit: 返回数量
    
    Returns:
        list: 新闻列表
    """
    query = f"{stock_name} {stock_code} 最新新闻 公告 研报".strip()
    result = query_neodata(query, "all")
    
    if not result.get("suc"):
        return []
    
    news_list = []
    doc_data = result.get("data", {}).get("docData", {}).get("docRecall", [])
    
    for group in doc_data:
        for doc in group.get("docList", []):
            # 转换时间戳
            pub_time = doc.get("publishTime", 0)
            if pub_time:
                pub_time = time.strftime("%Y-%m-%d", time.localtime(pub_time))
            
            news_list.append({
                "title": doc.get("title", ""),
                "content": doc.get("content", "")[:500],  # 截取前500字
                "pub_time": pub_time,
                "url": doc.get("url", ""),
                "source": doc.get("source", "") or doc.get("site", "") or "财经"
            })
            
            if len(news_list) >= limit:
                break
        if len(news_list) >= limit:
            break
    
    return news_list


def get_stock_events(stock_name, stock_code=""):
    """
    获取个股重大事件（股权变动等）
    
    Args:
        stock_name: 股票名称
        stock_code: 股票代码
    
    Returns:
        dict: 事件信息
    """
    query = f"{stock_name} {stock_code} 股权变动 股东人数 高管增持减持".strip()
    result = query_neodata(query, "api")
    
    if not result.get("suc"):
        return {}
    
    events = []
    api_data = result.get("data", {}).get("apiData", {}).get("apiRecall", [])
    
    for item in api_data:
        if item.get("type") == "股权变动事件提醒":
            return {
                "type": item.get("type", ""),
                "desc": item.get("desc", ""),
                "content": item.get("content", ""),
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


def get_analysis_report(stock_name, stock_code=""):
    """
    获取个股分析报告摘要
    
    Args:
        stock_name: 股票名称
        stock_code: 股票代码
    
    Returns:
        dict: 分析报告信息
    """
    query = f"{stock_name} {stock_code} 分析 研报 机构评级 目标价".strip()
    result = query_neodata(query, "all")
    
    if not result.get("suc"):
        return {}
    
    reports = []
    doc_data = result.get("data", {}).get("docData", {}).get("docRecall", [])
    
    for group in doc_data:
        for doc in group.get("docList", [])[:2]:  # 只取前2篇
            pub_time = doc.get("publishTime", 0)
            if pub_time:
                pub_time = time.strftime("%Y-%m-%d", time.localtime(pub_time))
            
            reports.append({
                "title": doc.get("title", ""),
                "content": doc.get("content", "")[:800],  # 截取前800字
                "pub_time": pub_time,
                "source": doc.get("source", "") or doc.get("site", "") or "财经"
            })
    
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


def format_events_for_display(events):
    """格式化事件信息为可读文本"""
    if not events:
        return "暂无重大事件"
    
    content = events.get("content", "")
    # 提取关键信息
    if "股东人数" in content:
        return f"  {content}"
    
    return f"  {content}"


def format_capital_flow_for_display(capital):
    """格式化资金流向为可读文本"""
    if not capital:
        return "暂无资金流向数据"
    
    content = capital.get("content", "")
    return f"  {content}"


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

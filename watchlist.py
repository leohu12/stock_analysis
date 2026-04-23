# -*- coding: utf-8 -*-
"""
自选股管理模块
支持：添加、删除、列表、持久化存储
"""

import os
import json
from display import Color

WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")


def load_watchlist():
    """加载自选股列表"""
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("stocks", [])
        except Exception:
            pass
    return []


def save_watchlist(stocks):
    """保存自选股列表"""
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump({"stocks": stocks, "updated": str(__import__('datetime').datetime.now())[:10]}, f, ensure_ascii=False, indent=2)


def add_stock(code):
    """添加自选股"""
    stocks = load_watchlist()
    code = code.strip().upper()
    
    # 规范化代码（去除后缀）
    if '.' in code:
        code = code.split('.')[0]
    
    # 检查是否已存在
    if code in stocks:
        print(f"  {Color.YELLOW}{code} 已在自选列表中{Color.RESET}")
        return False
    
    stocks.append(code)
    save_watchlist(stocks)
    print(f"  {Color.GREEN}[OK] 已添加 {code}{Color.RESET}")
    return True


def remove_stock(code):
    """删除自选股"""
    stocks = load_watchlist()
    code = code.strip().upper()
    
    if '.' in code:
        code = code.split('.')[0]
    
    if code not in stocks:
        print(f"  {Color.YELLOW}{code} 不在自选列表中{Color.RESET}")
        return False
    
    stocks.remove(code)
    save_watchlist(stocks)
    print(f"  {Color.GREEN}[OK] 已删除 {code}{Color.RESET}")
    return True


def list_stocks():
    """列出所有自选股"""
    return load_watchlist()


def clear_stocks():
    """清空自选股"""
    save_watchlist([])
    print(f"  {Color.GREEN}[OK] 已清空自选列表{Color.RESET}")


def show_watchlist_menu():
    """自选股管理菜单"""
    while True:
        stocks = load_watchlist()
        
        print(f"\n{Color.BOLD}{Color.CYAN}{'─'*50}{Color.RESET}")
        print(f"{Color.BOLD}  📋 自选股管理 ({len(stocks)} 只){Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'─'*50}{Color.RESET}")
        print()
        print("  1. 查看自选股")
        print("  2. 添加自选股")
        print("  3. 删除自选股")
        print("  4. 清空自选股")
        print("  5. 分析我的自选股")
        print("  0. 返回上级菜单")
        print()
        
        choice = input(f"  {Color.BOLD}请选择: {Color.RESET}").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            _show_watchlist(stocks)
        elif choice == "2":
            code = input(f"\n  {Color.BOLD}请输入股票代码: {Color.RESET}").strip()
            if code:
                add_stock(code)
        elif choice == "3":
            if not stocks:
                print(f"  {Color.YELLOW}自选列表为空{Color.RESET}")
            else:
                _show_watchlist(stocks)
                code = input(f"\n  {Color.BOLD}请输入要删除的代码: {Color.RESET}").strip()
                if code:
                    remove_stock(code)
        elif choice == "4":
            if stocks:
                confirm = input(f"\n  {Color.YELLOW}确定要清空所有自选股吗？(y/N): {Color.RESET}").strip().lower()
                if confirm == 'y':
                    clear_stocks()
            else:
                print(f"  {Color.YELLOW}自选列表已经是空的{Color.RESET}")
        elif choice == "5":
            if not stocks:
                print(f"  {Color.YELLOW}自选列表为空，请先添加自选股{Color.RESET}")
            else:
                return stocks
        else:
            print(f"  {Color.YELLOW}无效选择{Color.RESET}")
    
    return None


def _show_watchlist(stocks):
    """显示自选股列表"""
    if not stocks:
        print(f"\n  {Color.YELLOW}自选列表为空{Color.RESET}")
        return
    
    print(f"\n  {Color.BOLD}当前自选股 ({len(stocks)} 只):{Color.RESET}")
    for i, code in enumerate(stocks, 1):
        print(f"    {i}. {code}")

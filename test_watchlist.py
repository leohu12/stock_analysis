# -*- coding: utf-8 -*-
"""测试自选股功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from watchlist import add_stock, remove_stock, list_stocks, save_watchlist

# 清空并重新添加
print("=== 测试自选股功能 ===\n")

# 清空
save_watchlist([])
print("已清空自选列表\n")

# 添加自选股
print("添加自选股:")
add_stock("600519")  # 茅台
add_stock("600036")  # 招行
add_stock("601318")  # 平安
add_stock("000858")  # 五粮液

# 列出
print("\n当前自选股:")
stocks = list_stocks()
for i, s in enumerate(stocks, 1):
    print(f"  {i}. {s}")

# 删除一个
print("\n删除 600036:")
remove_stock("600036")

# 再列出
print("\n删除后自选股:")
stocks = list_stocks()
for i, s in enumerate(stocks, 1):
    print(f"  {i}. {s}")

print(f"\n共 {len(stocks)} 只股票")

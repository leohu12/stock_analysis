# -*- coding: utf-8 -*-
"""测试目标价和上涨空间功能"""
from screener import screen_realtime
from display import print_table, Color

print()
print(f"{Color.CYAN}{'='*60}{Color.RESET}")
print(f"{Color.BOLD}  测试：目标价 + 上涨空间 功能{Color.RESET}")
print(f"{Color.CYAN}{'='*60}{Color.RESET}")

# 场景1（追热点，包含涨停）
print()
print(f"{Color.YELLOW}[场景1: 追热点（包含涨停）]{Color.RESET}")
result1 = screen_realtime(
    top_n=8, 
    min_price=1, 
    max_price=100, 
    min_change=5, 
    min_turnover=5, 
    min_volume_ratio=2, 
    include_limit_up=True, 
    quiet=True
)
if not result1.empty:
    print_table(result1, title='', max_rows=10)

# 场景2（找补涨，排除涨停）
print()
print(f"{Color.YELLOW}[场景2: 找补涨（排除涨停）]{Color.RESET}")
result2 = screen_realtime(
    top_n=8, 
    min_price=1, 
    max_price=50, 
    min_change=2, 
    min_turnover=3, 
    min_volume_ratio=2, 
    include_limit_up=False, 
    quiet=True
)
if not result2.empty:
    print_table(result2, title='', max_rows=10)

print()
print(f"  {Color.DIM}注：涨停股目标价=次日涨停价；非涨停股目标价基于量比估算{Color.RESET}")

# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from screener import screen_realtime, SCREEN_SCENARIOS
from display import print_table, Color

sep = '=' * 60
for k, v in SCREEN_SCENARIOS.items():
    print(f'\n{sep}')
    print(f'场景{k}: {v["name"]}')
    print(sep)

    result = screen_realtime(
        top_n=8,
        min_price=1,
        max_price=v.get('max_price', 100),
        min_change=v['min_change'],
        min_turnover=v['min_turnover'],
        min_volume_ratio=v['min_volume_ratio'],
        include_limit_up=v['include_limit_up'],
        prefer_small_cap=v.get('prefer_small_cap', False)
    )

    if not result.empty:
        print_table(result, title='', max_rows=8)
    else:
        print('  无结果')

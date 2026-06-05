#!/usr/bin/env python3
"""快速验证四个榜单数据"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("AlphaEye 四大榜单快速验证\n")

# 1. 测试 iFinD Provider
print("=== 测试 iFinD Provider ===")
try:
    from src.data.providers.registry import get_provider
    provider = get_provider()
    print(f"✓ Provider: {provider.source_name}")
    print(f"✓ 是否配置: {provider.configured}")

    if provider.source_name == "ifind" and provider.configured:
        print("\n直接测试 iFinD 涨幅榜:")
        rows = provider.get_top_stocks(sort_field="changepercent", asc=False, limit=5)
        for i, s in enumerate(rows[:5], 1):
            print(f"  {i}. {s['code']:8s} {s['name']:6s} ¥{s['price']:7.2f} {s['change_pct']:+6.2f}%")

        print("\n直接测试 iFinD 跌幅榜:")
        rows = provider.get_top_stocks(sort_field="changepercent", asc=True, limit=5)
        for i, s in enumerate(rows[:5], 1):
            print(f"  {i}. {s['code']:8s} {s['name']:6s} ¥{s['price']:7.2f} {s['change_pct']:+6.2f}%")
    else:
        print("⚠️  iFinD 未配置，将使用公开数据源")
except Exception as e:
    print(f"✗ Provider 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 2. 测试完整数据流
print("\n=== 测试完整数据流（经过 realtime.py） ===")
try:
    from src.data.realtime import get_top_stocks, get_market_overview

    print("\n大盘指数:")
    ov = get_market_overview()
    for idx in ov.get("indices", [])[:3]:
        print(f"  {idx['name']:6s}: ¥{idx['price']:8.2f} ({idx['change_pct']:+.2f}%)")

    print("\n涨幅榜 Top5:")
    up = get_top_stocks("changepercent", False, 5)
    for i, s in enumerate(up[:5], 1):
        print(f"  {i}. {s['code']:8s} {s['name']:6s} ¥{s['price']:7.2f} {s['change_pct']:+6.2f}%")

    print("\n跌幅榜 Top5:")
    down = get_top_stocks("changepercent", True, 5)
    for i, s in enumerate(down[:5], 1):
        print(f"  {i}. {s['code']:8s} {s['name']:6s} ¥{s['price']:7.2f} {s['change_pct']:+6.2f}%")

    print("\n成交额榜 Top5:")
    amt = get_top_stocks("amount", False, 5)
    for i, s in enumerate(amt[:5], 1):
        print(f"  {i}. {s['code']:8s} {s['name']:6s} ¥{s['price']:7.2f} 成交额{s.get('amount', 0)/1e8:.1f}亿")

    print("\n换手率榜 Top5:")
    tr = get_top_stocks("turnoverratio", False, 5)
    for i, s in enumerate(tr[:5], 1):
        print(f"  {i}. {s['code']:8s} {s['name']:6s} ¥{s['price']:7.2f} 换手{s.get('turnover', 0):.2f}%")

except Exception as e:
    print(f"✗ 完整数据流测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 验证完成 ===")
print("\n数据说明:")
print("- 涨幅榜应该是正数在前，从高到低")
print("- 跌幅榜应该是负数在前，从低到高")
print("- 价格应该是真实股价（几元到几千元），不应该是 0.00")
print("- 如果所有价格都是 0，说明数据源有问题")

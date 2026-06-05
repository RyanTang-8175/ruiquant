#!/usr/bin/env python3
"""完整测试修复后的榜单"""

import sys
import os
sys.path.insert(0, "/Users/7yq/vibe coding项目/股票")
os.chdir("/Users/7yq/vibe coding项目/股票")

print("=" * 70)
print("AlphaEye 榜单修复验证")
print("=" * 70)

# 测试涨幅榜
print("\n📈 涨幅榜 (应该有价格、正确排序)")
try:
    from src.data.realtime import get_top_stocks

    up = get_top_stocks("changepercent", False, 20)
    print(f"返回 {len(up)} 条数据\n")

    valid_count = 0
    for i, s in enumerate(up[:10], 1):
        code = s.get("code", "")
        name = s.get("name", "")[:8]
        price = s.get("price", 0)
        chg = s.get("change_pct", 0)

        status = "✓" if price > 0 else "✗"
        print(f"{status} {i:2d}. {code:8s} {name:8s} ¥{price:7.2f} {chg:+6.2f}%")

        if price > 0:
            valid_count += 1

    print(f"\n有效数据: {valid_count}/10")
    if valid_count < 8:
        print("⚠️  有效数据太少，可能是北交所股票或数据源问题")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试跌幅榜
print("\n📉 跌幅榜 (应该有价格、正确排序)")
try:
    down = get_top_stocks("changepercent", True, 20)
    print(f"返回 {len(down)} 条数据\n")

    valid_count = 0
    for i, s in enumerate(down[:10], 1):
        code = s.get("code", "")
        name = s.get("name", "")[:8]
        price = s.get("price", 0)
        chg = s.get("change_pct", 0)

        status = "✓" if price > 0 else "✗"
        print(f"{status} {i:2d}. {code:8s} {name:8s} ¥{price:7.2f} {chg:+6.2f}%")

        if price > 0:
            valid_count += 1

    print(f"\n有效数据: {valid_count}/10")

except Exception as e:
    print(f"✗ 失败: {e}")

# 测试成交额榜
print("\n💰 成交额榜")
try:
    amt = get_top_stocks("amount", False, 20)
    print(f"返回 {len(amt)} 条数据\n")

    for i, s in enumerate(amt[:5], 1):
        code = s.get("code", "")
        name = s.get("name", "")[:8]
        price = s.get("price", 0)
        amount = s.get("amount", 0) / 1e8

        status = "✓" if price > 0 else "✗"
        print(f"{status} {i:2d}. {code:8s} {name:8s} ¥{price:7.2f} 成交 {amount:6.1f}亿")

except Exception as e:
    print(f"✗ 失败: {e}")

# 测试换手率榜
print("\n🔄 换手率榜")
try:
    tr = get_top_stocks("turnoverratio", False, 20)
    print(f"返回 {len(tr)} 条数据\n")

    for i, s in enumerate(tr[:5], 1):
        code = s.get("code", "")
        name = s.get("name", "")[:8]
        price = s.get("price", 0)
        turnover = s.get("turnover", 0)

        status = "✓" if price > 0 else "✗"
        print(f"{status} {i:2d}. {code:8s} {name:8s} ¥{price:7.2f} 换手 {turnover:5.2f}%")

except Exception as e:
    print(f"✗ 失败: {e}")

print("\n" + "=" * 70)
print("说明:")
print("  ✓ = 有价格数据（正常）")
print("  ✗ = 价格为0（异常，可能是北交所股票或数据源不支持）")
print("\n如果大部分是 ✓，说明修复成功")
print("如果仍有很多 ✗，可能需要进一步过滤或调整数据源")

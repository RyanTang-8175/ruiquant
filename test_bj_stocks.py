#!/usr/bin/env python3
"""测试 iFinD 北交所股票行情获取"""

import sys
import os
sys.path.insert(0, "/Users/7yq/vibe coding项目/股票")
os.chdir("/Users/7yq/vibe coding项目/股票")

print("测试北交所股票行情获取\n")

# 测试代码
bj_codes = ["920211", "920510", "920961", "920576", "920175"]

print("1️⃣  测试 _ths_code 映射:")
from src.data.providers.ifind_provider import IFindProvider
provider = IFindProvider()

for code in bj_codes:
    ths_code = provider._ths_code(code)
    print(f"   {code} → {ths_code}")

print("\n2️⃣  测试批量行情获取:")
try:
    quotes = provider.get_realtime_quotes(bj_codes)
    print(f"   返回 {len(quotes)} 条\n")

    for q in quotes:
        print(f"   {q.get('code')} {q.get('name'):8s} ¥{q.get('price', 0):.2f} {q.get('change_pct', 0):+.2f}%")

    if not quotes:
        print("   ⚠️  北交所行情获取失败（可能是 iFinD 不支持）")

except Exception as e:
    print(f"   ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n3️⃣  测试主板股票对比:")
main_codes = ["600519", "000001", "300750"]
try:
    quotes = provider.get_realtime_quotes(main_codes)
    print(f"   返回 {len(quotes)} 条\n")

    for q in quotes:
        print(f"   {q.get('code')} {q.get('name'):8s} ¥{q.get('price', 0):.2f} {q.get('change_pct', 0):+.2f}%")

except Exception as e:
    print(f"   ✗ 失败: {e}")

print("\n结论:")
print("如果北交所股票全部返回空，说明 iFinD 不支持北交所实时行情")
print("建议在榜单中过滤掉 92xxxx 开头的股票")

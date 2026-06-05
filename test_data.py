"""快速测试 - 无需 Bash 权限"""

import sys
import os

# 添加项目路径
project_dir = "/Users/7yq/vibe coding项目/股票"
sys.path.insert(0, project_dir)
os.chdir(project_dir)

print("AlphaEye 榜单数据验证\n")
print("=" * 60)

# 检查配置
print("\n1️⃣  配置检查")
try:
    import json
    with open("data/settings.json") as f:
        settings = json.load(f)

    provider = settings.get("data_provider", "not set")
    has_ifind = bool(settings.get("ifind_refresh_token"))

    print(f"   数据源配置: {provider}")
    print(f"   iFinD Token: {'✓ 已配置' if has_ifind else '✗ 未配置'}")

    if provider == "ifind" and has_ifind:
        print("   ✓ 应该使用 iFinD 实时数据")
    else:
        print("   ⚠️  将使用公开数据源")
except Exception as e:
    print(f"   ✗ 配置读取失败: {e}")

# 测试 Provider
print("\n2️⃣  测试数据源初始化")
try:
    from src.data.providers.registry import get_provider
    provider = get_provider()
    print(f"   ✓ Provider 类型: {provider.source_name}")
    print(f"   ✓ 是否就绪: {provider.configured}")
except Exception as e:
    print(f"   ✗ Provider 初始化失败: {e}")
    provider = None

# 测试指数
print("\n3️⃣  测试大盘指数")
try:
    from src.data.realtime import get_market_overview
    ov = get_market_overview()
    indices = ov.get("indices", [])

    if indices:
        for idx in indices:
            name = idx.get("name", "")
            price = idx.get("price", 0)
            chg = idx.get("change_pct", 0)
            print(f"   {name:8s}: {price:8.2f} 点  ({chg:+6.2f}%)")
    else:
        print("   ✗ 无指数数据")
except Exception as e:
    print(f"   ✗ 指数获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试涨幅榜
print("\n4️⃣  测试涨幅榜（应该正数在前，从高到低）")
try:
    from src.data.realtime import get_top_stocks
    up = get_top_stocks("changepercent", False, 10)

    if up:
        print(f"   返回 {len(up)} 条数据\n")
        for i, s in enumerate(up[:5], 1):
            code = s.get("code", "")
            name = s.get("name", "")[:6]
            price = s.get("price", 0)
            chg = s.get("change_pct", 0)
            print(f"   {i:2d}. {code:8s} {name:6s}  ¥{price:7.2f}  {chg:+6.2f}%")

        # 检查数据合理性
        if all(s.get("price", 0) == 0 for s in up[:5]):
            print("\n   ⚠️  警告: 所有价格都是 0，数据源有问题！")
        if up[0].get("change_pct", 0) < up[-1].get("change_pct", 0):
            print("\n   ⚠️  警告: 排序错误，应该涨幅最高在前！")
    else:
        print("   ✗ 无涨幅榜数据")
except Exception as e:
    print(f"   ✗ 涨幅榜获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试跌幅榜
print("\n5️⃣  测试跌幅榜（应该负数在前，从低到高）")
try:
    from src.data.realtime import get_top_stocks
    down = get_top_stocks("changepercent", True, 10)

    if down:
        print(f"   返回 {len(down)} 条数据\n")
        for i, s in enumerate(down[:5], 1):
            code = s.get("code", "")
            name = s.get("name", "")[:6]
            price = s.get("price", 0)
            chg = s.get("change_pct", 0)
            print(f"   {i:2d}. {code:8s} {name:6s}  ¥{price:7.2f}  {chg:+6.2f}%")

        # 检查数据合理性
        if all(s.get("price", 0) == 0 for s in down[:5]):
            print("\n   ⚠️  警告: 所有价格都是 0，数据源有问题！")
        if down[0].get("change_pct", 0) > down[-1].get("change_pct", 0):
            print("\n   ⚠️  警告: 排序错误，应该跌幅最大在前！")
    else:
        print("   ✗ 无跌幅榜数据")
except Exception as e:
    print(f"   ✗ 跌幅榜获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试成交额榜
print("\n6️⃣  测试成交额榜（应该从高到低）")
try:
    from src.data.realtime import get_top_stocks
    amt = get_top_stocks("amount", False, 10)

    if amt:
        print(f"   返回 {len(amt)} 条数据\n")
        for i, s in enumerate(amt[:5], 1):
            code = s.get("code", "")
            name = s.get("name", "")[:6]
            price = s.get("price", 0)
            amount = s.get("amount", 0) / 1e8
            print(f"   {i:2d}. {code:8s} {name:6s}  ¥{price:7.2f}  成交额 {amount:6.1f}亿")
    else:
        print("   ✗ 无成交额榜数据")
except Exception as e:
    print(f"   ✗ 成交额榜获取失败: {e}")

# 测试换手率榜
print("\n7️⃣  测试换手率榜（应该从高到低）")
try:
    from src.data.realtime import get_top_stocks
    tr = get_top_stocks("turnoverratio", False, 10)

    if tr:
        print(f"   返回 {len(tr)} 条数据\n")
        for i, s in enumerate(tr[:5], 1):
            code = s.get("code", "")
            name = s.get("name", "")[:6]
            price = s.get("price", 0)
            turnover = s.get("turnover", 0)
            print(f"   {i:2d}. {code:8s} {name:6s}  ¥{price:7.2f}  换手率 {turnover:5.2f}%")
    else:
        print("   ✗ 无换手率榜数据")
except Exception as e:
    print(f"   ✗ 换手率榜获取失败: {e}")

print("\n" + "=" * 60)
print("✅ 验证完成")
print("\n预期结果:")
print("  • 指数价格应该在 2000-4000 之间")
print("  • 涨幅榜应该正数在前，从大到小")
print("  • 跌幅榜应该负数在前，从小到大")
print("  • 价格应该是真实股价（几元到几千元）")
print("  • 如果价格全是 0.00，说明数据源有严重问题")

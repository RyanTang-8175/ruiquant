#!/usr/bin/env python3
"""诊断四个榜单数据问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_data_source():
    """测试数据源配置"""
    print("=== 1. 数据源配置检查 ===")

    from src.config import get_setting
    provider = get_setting("data_provider", "ALPHAEYE_DATA_PROVIDER", "open")
    print(f"配置的数据源: {provider}")

    if provider in {"ifind", "ths", "同花顺"}:
        print("✓ iFinD 已配置")
        ifind_token = get_setting("ifind_refresh_token", "IFIND_REFRESH_TOKEN", "")
        print(f"✓ iFinD refresh_token: {'已配置' if ifind_token else '未配置'}")
    else:
        print("⚠️  使用公开数据源")

    print()

def test_provider_init():
    """测试 iFinD Provider 初始化"""
    print("=== 2. iFinD Provider 初始化 ===")
    try:
        from src.data.providers.registry import get_provider
        provider = get_provider()
        print(f"✓ Provider: {provider.source_name}")
        print(f"✓ Configured: {provider.configured}")
        return provider
    except Exception as e:
        print(f"✗ Provider 初始化失败: {e}")
        return None

def test_indices(provider):
    """测试指数数据"""
    print("\n=== 3. 测试大盘指数 ===")
    try:
        if provider and provider.source_name == "ifind":
            snapshot = provider.get_market_snapshot()
            print("使用 iFinD 数据:")
        else:
            from src.data.realtime import _open_market_overview
            snapshot = _open_market_overview()
            print("使用公开数据源:")

        for idx in snapshot.get("indices", []):
            print(f"  {idx.get('name'):6s}: {idx.get('price'):8.2f}  {idx.get('change_pct'):+6.2f}%")

        if not snapshot.get("indices"):
            print("  ✗ 无指数数据")
    except Exception as e:
        print(f"  ✗ 指数测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_ranking(provider, sort_field, asc, name):
    """测试单个榜单"""
    print(f"\n=== 4. 测试{name} ===")
    print(f"sort_field={sort_field}, asc={asc}")

    try:
        if provider and provider.source_name == "ifind":
            print("尝试使用 iFinD 数据...")
            rows = provider.get_top_stocks(sort_field=sort_field, asc=asc, limit=10)
            print(f"✓ iFinD 返回 {len(rows)} 条")
        else:
            from src.data.realtime import _open_top_stocks
            print("使用公开数据源...")
            rows = _open_top_stocks(sort_field=sort_field, asc=asc, limit=10)
            print(f"✓ 公开源返回 {len(rows)} 条")

        if rows:
            print(f"\n前5名:")
            for i, s in enumerate(rows[:5], 1):
                code = s.get('code', '')
                name = s.get('name', '')[:6]
                price = s.get('price', 0)
                change = s.get('change_pct', 0)
                print(f"  {i}. {code:8s} {name:6s} {price:8.2f}  {change:+6.2f}%")
        else:
            print("  ✗ 无数据")

    except Exception as e:
        print(f"  ✗ {name}测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("AlphaEye 四大榜单诊断工具\n")

    # 1. 检查配置
    test_data_source()

    # 2. 初始化 Provider
    provider = test_provider_init()

    # 3. 测试指数
    test_indices(provider)

    # 4. 测试四个榜单
    test_ranking(provider, "changepercent", False, "涨幅榜 (asc=False 应该最高在前)")
    test_ranking(provider, "changepercent", True, "跌幅榜 (asc=True 应该最低在前)")
    test_ranking(provider, "amount", False, "成交额榜 (asc=False 应该最大在前)")
    test_ranking(provider, "turnoverratio", False, "换手率榜 (asc=False 应该最高在前)")

    print("\n=== 诊断完成 ===")

if __name__ == "__main__":
    main()

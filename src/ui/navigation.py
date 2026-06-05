"""Streamlit 页面导航辅助。

用于区分主导航页和临时子页面，避免 stock_detail 这类页面被顶部导航误覆盖。
"""

from __future__ import annotations

from typing import Iterable


TRANSIENT_PAGES = {"stock_detail", "trading"}


def resolve_main_navigation(
    current_page: str,
    selected_nav: str | None,
    last_nav_page: str | None,
    tab_pages: Iterable[str],
) -> dict:
    """计算主导航应该如何表现。

    返回值包含：
    - current_page: 保持或修正后的当前页面
    - selected_nav: 主导航应显示的选中项
    - show_main_nav: 当前是否应该渲染顶部主导航
    """

    tabs = list(tab_pages)
    nav_fallback = last_nav_page or (tabs[0] if tabs else "market")
    if current_page not in tabs:
        return {
            "current_page": current_page,
            "selected_nav": nav_fallback,
            "show_main_nav": False,
        }

    nav = selected_nav if selected_nav in tabs else nav_fallback
    return {
        "current_page": current_page,
        "selected_nav": nav,
        "show_main_nav": True,
    }

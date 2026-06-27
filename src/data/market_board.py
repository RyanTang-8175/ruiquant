"""A-share market board classification utilities.

The rules here intentionally stay conservative and deterministic. They are
used by radar, market lists, and AI context so board filters do not drift.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoardInfo:
    code: str
    board: str
    exchange: str
    scope: str
    tradable_for_main_board: bool
    transmission_role: str


MARKET_SCOPES = ("主板优先", "沪深A股", "全A含北交所")
BOARD_FILTERS = ("全A", "沪市主板", "深市主板", "创业板", "科创板", "北交所")


def normalize_plain_code(code: str | int | None) -> str:
    digits = "".join(ch for ch in str(code or "") if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else digits


def classify_a_share_board(code: str | int | None) -> BoardInfo:
    """Classify common A-share stock codes by exchange board.

    Current practical mapping:
    - Shanghai main board: 600/601/603/605
    - STAR Market: 688/689
    - Shenzhen main board: 000/001/002/003/004
    - ChiNext: 300/301
    - Beijing Stock Exchange: 920 after code unification; legacy 8/4 codes
      are still treated as BSE when encountered in local data.
    """

    plain = normalize_plain_code(code)
    if plain.startswith(("600", "601", "603", "605")):
        return BoardInfo(plain, "沪市主板", "上交所", "主板", True, "可交易主板候选")
    if plain.startswith(("000", "001", "002", "003", "004")):
        return BoardInfo(plain, "深市主板", "深交所", "主板", True, "可交易主板候选")
    if plain.startswith(("300", "301")):
        return BoardInfo(plain, "创业板", "深交所", "创业板", False, "情绪/成长风格传导参考")
    if plain.startswith(("688", "689")):
        return BoardInfo(plain, "科创板", "上交所", "科创板", False, "科技产业链传导参考")
    if plain.startswith("920") or (len(plain) == 6 and plain[0] in {"4", "8"}):
        return BoardInfo(plain, "北交所", "北交所", "北交所", False, "小盘流动性风险参考")
    return BoardInfo(plain, "未识别", "未知", "未知", False, "不纳入候选")


def board_label(code: str | int | None) -> str:
    return classify_a_share_board(code).board


def is_code_in_market_scope(code: str | int | None, market_scope: str) -> bool:
    info = classify_a_share_board(code)
    if market_scope == "全A含北交所":
        return info.scope in {"主板", "创业板", "科创板", "北交所"}
    if market_scope in {"沪深A股", "中国A股"}:
        return info.scope in {"主板", "创业板", "科创板"}
    return info.scope == "主板"


def is_code_in_board_filter(code: str | int | None, board_filter: str) -> bool:
    if board_filter in {"", "全A"}:
        return True
    return classify_a_share_board(code).board == board_filter


def board_scope_note(market_scope: str) -> str:
    if market_scope == "主板优先":
        return "当前只把沪市主板、深市主板纳入推荐池；创业板/科创板仅作为情绪和产业链传导参考，北交所默认排除。"
    if market_scope == "沪深A股":
        return "当前纳入沪深主板、创业板、科创板；北交所因流动性与代码体系差异暂不纳入。"
    return "当前纳入沪深主板、创业板、科创板、北交所；北交所需额外关注流动性、涨跌幅和成交连续性。"

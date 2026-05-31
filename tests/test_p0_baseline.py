from pathlib import Path

from src.trading.engine import TradingEngine


ROOT = Path(__file__).resolve().parents[1]


def test_buy_cost_includes_commission_floor_and_transfer_fee():
    engine = TradingEngine()
    try:
        cost = engine.calculate_buy_cost(price=10.0, quantity=100)
    finally:
        engine.close()

    assert cost == {
        "amount": 1000.0,
        "commission": 5.0,
        "transfer_fee": 0.02,
        "total": 1005.02,
    }


def test_sell_cost_includes_commission_stamp_tax_and_transfer_fee():
    engine = TradingEngine()
    try:
        cost = engine.calculate_sell_cost(price=10.0, quantity=100)
    finally:
        engine.close()

    assert cost == {
        "amount": 1000.0,
        "commission": 5.0,
        "stamp_tax": 0.5,
        "transfer_fee": 0.02,
        "net": 994.48,
    }


def test_trading_page_passes_stock_name_to_execute_buy():
    source = (ROOT / "src" / "pages" / "trading.py").read_text(encoding="utf-8")

    assert 'execute_buy(bc.strip(), q.get("name", bc.strip()), q["price"], bq)' in source


def test_scheduler_does_not_reference_removed_pipeline_apis():
    source = (ROOT / "src" / "scheduler.py").read_text(encoding="utf-8")

    assert "rescore_all" not in source
    assert "NewsFetcher" not in source


def test_health_check_script_exists():
    assert (ROOT / "scripts" / "health_check.py").exists()

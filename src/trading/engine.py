"""
模拟盘交易引擎
真实股市数据 + 虚拟资金 + 真实规则
"""

import logging
from datetime import datetime, date
from sqlalchemy.orm import Session
from src.trading.models import PaperAccount, Position, Trade
from src.data.models import DailyQuote
from src.utils.database import SessionLocal
from src.config import (
    COMMISSION_RATE, COMMISSION_MIN, STAMP_TAX_RATE, TRANSFER_FEE_RATE,
    MAX_POSITION_PCT, MAX_TOTAL_POSITION, STOP_LOSS_PCT, FORCE_SELL_PCT,
    CONSECUTIVE_LOSS_LIMIT
)

logger = logging.getLogger(__name__)


class TradingEngine:
    """模拟盘交易引擎"""

    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.db.close()
        except Exception:
            pass

    def get_account(self) -> PaperAccount:
        """获取模拟盘账户"""
        return self.db.query(PaperAccount).first()

    def get_current_price(self, code: str) -> float:
        """获取股票当前价格"""
        quote = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).first()
        return quote.close if quote else None

    def is_limit_up(self, code: str) -> bool:
        """检查是否涨停"""
        quote = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).first()
        if not quote:
            return False
        return quote.change_pct is not None and quote.change_pct >= 9.9

    def is_limit_down(self, code: str) -> bool:
        """检查是否跌停"""
        quote = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).first()
        if not quote:
            return False
        return quote.change_pct is not None and quote.change_pct <= -9.9

    def calculate_buy_cost(self, price: float, quantity: int) -> dict:
        """计算买入费用"""
        amount = price * quantity
        commission = max(amount * COMMISSION_RATE, COMMISSION_MIN)
        transfer_fee = amount * TRANSFER_FEE_RATE
        total = amount + commission + transfer_fee
        return {
            "amount": amount,
            "commission": round(commission, 2),
            "transfer_fee": round(transfer_fee, 2),
            "total": round(total, 2)
        }

    def calculate_sell_cost(self, price: float, quantity: int) -> dict:
        """计算卖出费用"""
        amount = price * quantity
        commission = max(amount * COMMISSION_RATE, COMMISSION_MIN)
        stamp_tax = amount * STAMP_TAX_RATE
        transfer_fee = amount * TRANSFER_FEE_RATE
        net = amount - commission - stamp_tax - transfer_fee
        return {
            "amount": amount,
            "commission": round(commission, 2),
            "stamp_tax": round(stamp_tax, 2),
            "transfer_fee": round(transfer_fee, 2),
            "net": round(net, 2)
        }

    def can_buy(self, code: str, price: float, quantity: int) -> tuple:
        """检查是否可以买入"""
        account = self.get_account()

        # 检查账户状态
        if account.status != "active":
            return False, f"账户状态异常: {account.status}"

        # 检查涨跌停
        if self.is_limit_up(code):
            return False, "涨停股票不能买入"

        # 检查买入数量
        if quantity < 100 or quantity % 100 != 0:
            return False, "买入数量必须是100的整数倍"

        # 检查现金是否充足
        cost = self.calculate_buy_cost(price, quantity)
        if account.cash < cost['total']:
            return False, f"现金不足，需要{cost['total']:.2f}，当前{account.cash:.2f}"

        # 检查仓位限制
        positions = self.db.query(Position).filter(Position.account_id == account.id).all()
        position_value = sum(p.quantity * p.cost_price for p in positions)
        total_value = account.cash + position_value

        if (position_value + cost['amount']) / total_value > MAX_TOTAL_POSITION:
            return False, f"总仓位超过{MAX_TOTAL_POSITION*100:.0f}%"

        existing = self.db.query(Position).filter(
            Position.account_id == account.id,
            Position.code == code
        ).first()
        existing_value = existing.quantity * existing.cost_price if existing else 0
        if (existing_value + cost['amount']) / total_value > MAX_POSITION_PCT:
            return False, f"单票仓位超过{MAX_POSITION_PCT*100:.0f}%"

        # 检查连续亏损
        if account.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            return False, f"连续{CONSECUTIVE_LOSS_LIMIT}笔亏损，暂停交易"

        return True, "可以买入"

    def can_sell(self, code: str, quantity: int) -> tuple:
        """检查是否可以卖出"""
        account = self.get_account()

        # 检查涨跌停
        if self.is_limit_down(code):
            return False, "跌停股票不能卖出"

        # 检查是否有持仓
        position = self.db.query(Position).filter(
            Position.account_id == account.id,
            Position.code == code
        ).first()

        if not position:
            return False, "没有持仓"

        # 检查持仓数量
        if quantity > position.quantity:
            return False, "卖出数量超过持仓"

        # 检查 T+1
        if position.buy_date == date.today():
            return False, "T+1限制：今天买入的股票不能今天卖出"

        return True, "可以卖出"

    def execute_buy(self, code: str, name: str, price: float, quantity: int) -> dict:
        """执行买入"""
        # 检查是否可以买入
        can, reason = self.can_buy(code, price, quantity)
        if not can:
            return {"success": False, "reason": reason}

        account = self.get_account()
        cost = self.calculate_buy_cost(price, quantity)

        try:
            # 更新现金
            account.cash -= cost['total']

            # 更新或创建持仓
            position = self.db.query(Position).filter(
                Position.account_id == account.id,
                Position.code == code
            ).first()

            if position:
                # 加仓：计算新的成本价
                total_quantity = position.quantity + quantity
                total_cost = position.cost_price * position.quantity + price * quantity
                position.cost_price = total_cost / total_quantity
                position.quantity = total_quantity
            else:
                position = Position(
                    account_id=account.id,
                    code=code,
                    name=name,
                    quantity=quantity,
                    cost_price=price,
                    buy_date=date.today()
                )
                self.db.add(position)

            # 记录交易
            trade = Trade(
                account_id=account.id,
                code=code,
                name=name,
                direction="buy",
                price=price,
                quantity=quantity,
                amount=cost['amount'],
                commission=cost['commission'],
                stamp_tax=0,
                transfer_fee=cost['transfer_fee'],
                total_cost=cost['total'],
                pnl=0,
                cash_before=account.cash + cost['total'],
                cash_after=account.cash,
                note=f"买入 {quantity}股 × {price:.2f}"
            )
            self.db.add(trade)
            self.db.commit()

            logger.info(f"买入成功: {name}({code}) {quantity}股 × {price:.2f}")
            return {"success": True, "trade": trade}

        except Exception as e:
            self.db.rollback()
            logger.error(f"买入失败: {e}")
            return {"success": False, "reason": str(e)}

    def execute_sell(self, code: str, price: float, quantity: int) -> dict:
        """执行卖出"""
        # 检查是否可以卖出
        can, reason = self.can_sell(code, quantity)
        if not can:
            return {"success": False, "reason": reason}

        account = self.get_account()
        cost = self.calculate_sell_cost(price, quantity)

        try:
            position = self.db.query(Position).filter(
                Position.account_id == account.id,
                Position.code == code
            ).first()

            # 计算盈亏
            pnl = (price - position.cost_price) * quantity
            pnl -= cost['commission'] + cost['stamp_tax'] + cost['transfer_fee']

            # 更新现金
            account.cash += cost['net']

            # 更新持仓
            if quantity == position.quantity:
                self.db.delete(position)
            else:
                position.quantity -= quantity

            # 更新连续亏损计数
            if pnl < 0:
                account.consecutive_losses += 1
            else:
                account.consecutive_losses = 0

            # 记录交易
            trade = Trade(
                account_id=account.id,
                code=code,
                name=position.name,
                direction="sell",
                price=price,
                quantity=quantity,
                amount=cost['amount'],
                commission=cost['commission'],
                stamp_tax=cost['stamp_tax'],
                transfer_fee=cost['transfer_fee'],
                total_cost=cost['amount'] - cost['net'],
                pnl=round(pnl, 2),
                cash_before=account.cash - cost['net'],
                cash_after=account.cash,
                note=f"卖出 {quantity}股 × {price:.2f}，盈亏 {pnl:+.2f}"
            )
            self.db.add(trade)
            self.db.commit()

            logger.info(f"卖出成功: {position.name}({code}) {quantity}股 × {price:.2f}，盈亏 {pnl:+.2f}")
            return {"success": True, "trade": trade, "pnl": pnl}

        except Exception as e:
            self.db.rollback()
            logger.error(f"卖出失败: {e}")
            return {"success": False, "reason": str(e)}

    def get_positions(self) -> list:
        """获取所有持仓"""
        account = self.get_account()
        return self.db.query(Position).filter(Position.account_id == account.id).all()

    def get_trades(self, limit: int = 50) -> list:
        """获取交易记录"""
        account = self.get_account()
        return self.db.query(Trade).filter(
            Trade.account_id == account.id
        ).order_by(Trade.created_at.desc()).limit(limit).all()

    def get_stats(self) -> dict:
        """获取交易统计"""
        account = self.get_account()
        trades = self.db.query(Trade).filter(
            Trade.account_id == account.id,
            Trade.direction == "sell"
        ).all()

        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "profit_loss_ratio": 0,
                "total_pnl": 0
            }

        winning = [t for t in trades if t.pnl and t.pnl > 0]
        losing = [t for t in trades if t.pnl and t.pnl < 0]

        win_rate = len(winning) / len(trades) if trades else 0
        avg_profit = sum(t.pnl for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.pnl for t in losing) / len(losing) if losing else 0
        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        total_pnl = sum(t.pnl for t in trades if t.pnl)

        return {
            "total_trades": len(trades),
            "win_rate": round(win_rate, 4),
            "avg_profit": round(avg_profit, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_loss_ratio": round(profit_loss_ratio, 2),
            "total_pnl": round(total_pnl, 2)
        }

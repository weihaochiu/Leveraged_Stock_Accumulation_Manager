from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from enum import StrEnum
from typing import Iterable


MONEY = Decimal("0.01")


def dec(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def money(value: object) -> Decimal:
    return dec(value).quantize(MONEY, rounding=ROUND_HALF_UP)


class FundingType(StrEnum):
    CASH = "CASH"
    LOAN = "LOAN"
    MIXED = "MIXED"


class LotStatus(StrEnum):
    CAPITAL_AT_RISK = "CAPITAL_AT_RISK"
    PRINCIPAL_RECOVERED = "PRINCIPAL_RECOVERED"
    FULL_COST_RECOVERED = "FULL_COST_RECOVERED"
    FREE_SHARES = "FREE_SHARES"
    CLOSED = "CLOSED"
    LOSS_CLOSED = "LOSS_CLOSED"
    ARCHIVED = "ARCHIVED"


class StrategyStatus(StrEnum):
    WAIT = "WAIT"
    NEAR_TARGET = "NEAR_TARGET"
    TARGET_REACHED = "TARGET_REACHED"
    PARTIAL_RECOVERY = "PARTIAL_RECOVERY"
    COMPLETED_WITH_TOLERANCE = "COMPLETED_WITH_TOLERANCE"
    PRINCIPAL_RECOVERED = "PRINCIPAL_RECOVERED"
    FULL_COST_RECOVERED = "FULL_COST_RECOVERED"
    FREE_SHARES = "FREE_SHARES"
    CLOSED = "CLOSED"


class RecoveryMode(StrEnum):
    PRINCIPAL = "PRINCIPAL"
    PRINCIPAL_TRADING_COST = "PRINCIPAL_TRADING_COST"
    FULL_COST = "FULL_COST"
    CUSTOM = "CUSTOM"


class OptimizationMode(StrEnum):
    KEEP_MAX_SHARES = "KEEP_MAX_SHARES"
    FULL_PRINCIPAL_RECOVERY = "FULL_PRINCIPAL_RECOVERY"
    CLOSEST_TO_PRINCIPAL = "CLOSEST_TO_PRINCIPAL"


ZH = {
    FundingType.CASH: "自有資金",
    FundingType.LOAN: "貸款",
    FundingType.MIXED: "混合資金",
    LotStatus.CAPITAL_AT_RISK: "本金仍有風險",
    LotStatus.PRINCIPAL_RECOVERED: "本金已回收",
    LotStatus.FULL_COST_RECOVERED: "完整成本已回收",
    LotStatus.FREE_SHARES: "已回本持股",
    LotStatus.CLOSED: "已結清",
    LotStatus.LOSS_CLOSED: "虧損結清",
    LotStatus.ARCHIVED: "已封存",
    StrategyStatus.WAIT: "等待",
    StrategyStatus.NEAR_TARGET: "接近目標",
    StrategyStatus.TARGET_REACHED: "已達目標",
    StrategyStatus.PARTIAL_RECOVERY: "部分回本",
    StrategyStatus.COMPLETED_WITH_TOLERANCE: "容許差額內完成回本",
    StrategyStatus.PRINCIPAL_RECOVERED: "本金已回收",
    StrategyStatus.FULL_COST_RECOVERED: "完整成本已回收",
    StrategyStatus.FREE_SHARES: "已回本持股",
    StrategyStatus.CLOSED: "已結清",
    RecoveryMode.PRINCIPAL: "回收原始本金",
    RecoveryMode.PRINCIPAL_TRADING_COST: "本金＋交易成本",
    RecoveryMode.FULL_COST: "完整成本",
    RecoveryMode.CUSTOM: "自訂金額",
    OptimizationMode.KEEP_MAX_SHARES: "優先保留最多股票",
    OptimizationMode.FULL_PRINCIPAL_RECOVERY: "必須完整回收",
    OptimizationMode.CLOSEST_TO_PRINCIPAL: "最接近目標金額",
}


def zh(value: object) -> str:
    try:
        return ZH[value]
    except (KeyError, TypeError):
        return str(value or "")


@dataclass(frozen=True)
class FeePolicy:
    commission_rate: Decimal = Decimal("0.001425")
    commission_discount: Decimal = Decimal("0.6")
    minimum_commission: Decimal = Decimal("1")
    sell_tax_rate: Decimal = Decimal("0.003")

    def commission(self, gross: Decimal) -> Decimal:
        fee = gross * self.commission_rate * self.commission_discount
        return money(max(self.minimum_commission, fee))

    def sell_tax(self, gross: Decimal) -> Decimal:
        return money(gross * self.sell_tax_rate)

    def sell_net(self, shares: int, price: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        gross = money(dec(shares) * price)
        commission = self.commission(gross)
        tax = self.sell_tax(gross)
        return gross, commission, tax, money(gross - commission - tax)


@dataclass(frozen=True)
class LotMetrics:
    original_shares: int
    sold_shares: int
    remaining_shares: int
    original_capital: Decimal
    net_cash_recovered: Decimal
    trading_costs: Decimal
    loan_interest: Decimal
    dividend_recovery: Decimal
    full_cost: Decimal
    capital_recovery_ratio: Decimal
    full_cost_recovery_ratio: Decimal
    cash_surplus: Decimal
    remaining_capital_at_risk: Decimal
    recovery_difference: Decimal
    current_price: Decimal
    market_value: Decimal
    free_shares: int
    free_share_value: Decimal
    strategy_value: Decimal
    current_return_pct: Decimal
    target_price: Decimal
    distance_to_target_pct: Decimal
    lot_status: LotStatus
    strategy_status: StrategyStatus


@dataclass(frozen=True)
class SimulationOption:
    shares: int
    gross_amount: Decimal
    commission: Decimal
    tax: Decimal
    net_cash: Decimal
    cumulative_recovered: Decimal
    difference: Decimal
    remaining_shares: int
    eligible_with_tolerance: bool
    fully_recovered: bool
    recommended: bool = False


def suggest_budget_shares(budget: object, price: object) -> int:
    budget_d, price_d = dec(budget), dec(price)
    if budget_d <= 0 or price_d <= 0:
        return 0
    return int((budget_d / price_d).to_integral_value(rounding=ROUND_FLOOR))


def calculate_lot_metrics(
    lot: dict,
    sells: Iterable[dict],
    *,
    current_price: object = 0,
    loan_interest: object = 0,
    dividend_recovery: object = 0,
    near_target_pct: object = 2,
) -> LotMetrics:
    sells = list(sells)
    original_shares = int(lot.get("original_shares") or 0)
    sold_shares = sum(int(row.get("shares") or 0) for row in sells)
    remaining_shares = original_shares - sold_shares
    if remaining_shares < 0:
        raise ValueError("累積賣出股數超過原始股數")
    original_capital = money(lot.get("original_capital") or 0)
    net_cash_recovered = money(sum(dec(row.get("net_cash")) for row in sells))
    trading_costs = money(sum(dec(row.get("commission")) + dec(row.get("tax")) + dec(row.get("other_fee")) for row in sells))
    interest = money(loan_interest)
    dividend = money(dividend_recovery)
    full_cost = money(original_capital + trading_costs + interest)
    recovery_cash = money(net_cash_recovered + dividend)
    capital_ratio = recovery_cash / original_capital if original_capital else Decimal("0")
    full_ratio = recovery_cash / full_cost if full_cost else Decimal("0")
    cash_surplus = money(max(Decimal("0"), recovery_cash - original_capital))
    remaining_risk = money(max(Decimal("0"), original_capital - recovery_cash))
    recovery_difference = money(recovery_cash - original_capital)
    price = money(current_price)
    buy_price = dec(lot.get("buy_price"))
    market_value = money(price * remaining_shares)
    target_return = dec(lot.get("target_return_pct"))
    target_price = money(buy_price * (Decimal("1") + target_return / 100))
    current_return = ((price - buy_price) / buy_price * 100) if buy_price and price else Decimal("0")
    distance = ((target_price - price) / price * 100) if price and target_price else Decimal("0")
    tolerance = max(dec(lot.get("recovery_tolerance_amount")), original_capital * dec(lot.get("recovery_tolerance_pct")) / 100)
    within_tolerance = remaining_risk > 0 and remaining_risk <= tolerance

    if remaining_shares == 0:
        lot_status = LotStatus.CLOSED if recovery_cash >= original_capital else LotStatus.LOSS_CLOSED
        strategy_status = StrategyStatus.CLOSED
    elif recovery_cash >= full_cost:
        lot_status = LotStatus.FREE_SHARES
        strategy_status = StrategyStatus.FREE_SHARES
    elif recovery_cash >= original_capital:
        lot_status = LotStatus.PRINCIPAL_RECOVERED
        strategy_status = StrategyStatus.PRINCIPAL_RECOVERED
    elif within_tolerance:
        lot_status = LotStatus.CAPITAL_AT_RISK
        strategy_status = StrategyStatus.COMPLETED_WITH_TOLERANCE
    elif recovery_cash > 0:
        lot_status = LotStatus.CAPITAL_AT_RISK
        strategy_status = StrategyStatus.PARTIAL_RECOVERY
    elif price >= target_price and target_price > 0:
        lot_status = LotStatus.CAPITAL_AT_RISK
        strategy_status = StrategyStatus.TARGET_REACHED
    elif distance <= dec(near_target_pct) and distance >= 0:
        lot_status = LotStatus.CAPITAL_AT_RISK
        strategy_status = StrategyStatus.NEAR_TARGET
    else:
        lot_status = LotStatus.CAPITAL_AT_RISK
        strategy_status = StrategyStatus.WAIT

    free_shares = remaining_shares if recovery_cash >= full_cost and remaining_shares > 0 else 0
    free_value = money(price * free_shares)
    strategy_value = money(cash_surplus + free_value)
    return LotMetrics(
        original_shares, sold_shares, remaining_shares, original_capital,
        net_cash_recovered, trading_costs, interest, dividend, full_cost,
        capital_ratio, full_ratio, cash_surplus, remaining_risk,
        recovery_difference, price, market_value, free_shares, free_value,
        strategy_value, current_return, target_price, distance, lot_status,
        strategy_status,
    )


def simulate_recovery(
    *,
    remaining_shares: int,
    price: object,
    already_recovered: object,
    target: object,
    tolerance: object,
    mode: OptimizationMode,
    fee_policy: FeePolicy,
) -> list[SimulationOption]:
    price_d = dec(price)
    recovered_d = money(already_recovered)
    target_d = money(target)
    tolerance_d = money(tolerance)
    if remaining_shares <= 0 or price_d <= 0:
        return []
    options: list[SimulationOption] = []
    for shares in range(1, remaining_shares + 1):
        gross, fee, tax, net = fee_policy.sell_net(shares, price_d)
        cumulative = money(recovered_d + net)
        difference = money(cumulative - target_d)
        options.append(SimulationOption(
            shares, gross, fee, tax, net, cumulative, difference,
            remaining_shares - shares,
            difference >= -tolerance_d,
            difference >= 0,
        ))
    if mode == OptimizationMode.KEEP_MAX_SHARES:
        eligible = [o for o in options if o.eligible_with_tolerance]
        chosen = min(eligible, key=lambda o: o.shares) if eligible else min(options, key=lambda o: abs(o.difference))
    elif mode == OptimizationMode.FULL_PRINCIPAL_RECOVERY:
        eligible = [o for o in options if o.fully_recovered]
        chosen = min(eligible, key=lambda o: o.shares) if eligible else options[-1]
    else:
        chosen = min(options, key=lambda o: (abs(o.difference), o.shares))
    neighbors = {chosen.shares}
    if chosen.shares > 1:
        neighbors.add(chosen.shares - 1)
    if chosen.shares < remaining_shares:
        neighbors.add(chosen.shares + 1)
    return [SimulationOption(**{**o.__dict__, "recommended": o.shares == chosen.shares}) for o in options if o.shares in neighbors]


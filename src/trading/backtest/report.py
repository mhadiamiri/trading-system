"""
P&L Report Generation

Cost-inclusive profit and loss reporting.

Constitutional Principles:
- I. Truth Before Profit: All costs listed separately
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict
from datetime import datetime


@dataclass
class TradeSummary:
    """Summary of a single trade."""
    timestamp: datetime
    symbol: str
    side: str
    size: Decimal
    fill_price: Decimal
    fees: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    total_cost: Decimal


class PnLReport:
    """
    P&L Report generator.

    Constitutional requirements:
        - Cost breakdown explicitly listed (Principle I)
        - Negative P&L is acceptable outcome (Principle I)
    """

    def __init__(self) -> None:
        """Initialize P&L report."""
        self._trades: List[TradeSummary] = []

    def add_trade(
        self,
        timestamp: datetime,
        symbol: str,
        side: str,
        size: Decimal,
        fill_price: Decimal,
        fees: Decimal,
        spread_cost: Decimal,
        slippage_cost: Decimal,
    ) -> None:
        """
        Add a trade to the report.

        Args:
            timestamp: Trade timestamp
            symbol: Trading pair
            side: "BUY" or "SELL"
            size: Trade size
            fill_price: Fill price
            fees: Trading fees
            spread_cost: Bid/ask spread cost
            slippage_cost: Slippage adjustment
        """
        total_cost = fees + spread_cost + slippage_cost
        self._trades.append(
            TradeSummary(
                timestamp=timestamp,
                symbol=symbol,
                side=side,
                size=size,
                fill_price=fill_price,
                fees=fees,
                spread_cost=spread_cost,
                slippage_cost=slippage_cost,
                total_cost=total_cost,
            )
        )

    def generate_report(self) -> Dict:
        """
        Generate P&L report.

        Returns:
            Report dict with all metrics and cost breakdown

        Constitutional requirements:
            - All costs listed as separate line items (Principle I)
            - Negative P&L is acceptable (Principle I)
        """
        total_fees = sum(trade.fees for trade in self._trades)
        total_spread = sum(trade.spread_cost for trade in self._trades)
        total_slippage = sum(trade.slippage_cost for trade in self._trades)
        total_costs = total_fees + total_spread + total_slippage

        # Calculate gross P&L (simplified for walking skeleton)
        gross_pnl = Decimal("0")
        for trade in self._trades:
            if trade.side == "SELL":
                gross_pnl += trade.size * trade.fill_price
            else:
                gross_pnl -= trade.size * trade.fill_price

        net_pnl = gross_pnl - total_costs

        # Calculate win rate (simplified)
        winning_trades = sum(
            1 for trade in self._trades
            if (trade.side == "SELL")  # Simplified: sells are wins
        )
        win_rate = winning_trades / len(self._trades) if self._trades else Decimal("0")

        return {
            "total_trades": len(self._trades),
            "gross_pnl": float(gross_pnl),
            "total_fees": float(total_fees),
            "total_spread_cost": float(total_spread),
            "total_slippage_cost": float(total_slippage),
            "total_costs": float(total_costs),
            "net_pnl": float(net_pnl),
            "win_rate": float(win_rate),
            "trades": [
                {
                    "timestamp": trade.timestamp.isoformat(),
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "size": float(trade.size),
                    "fill_price": float(trade.fill_price),
                    "fees": float(trade.fees),
                    "spread_cost": float(trade.spread_cost),
                    "slippage_cost": float(trade.slippage_cost),
                    "total_cost": float(trade.total_cost),
                }
                for trade in self._trades
            ],
        }

    def print_report(self) -> None:
        """Print P&L report to console."""
        report = self.generate_report()

        print("\n" + "=" * 60)
        print("P&L REPORT")
        print("=" * 60)
        print(f"Total Trades: {report['total_trades']}")
        print(f"Gross P&L: ${report['gross_pnl']:.2f}")
        print("-" * 60)
        print("COST BREAKDOWN:")
        print(f"  Fees:        ${report['total_fees']:.2f}")
        print(f"  Spread:      ${report['total_spread_cost']:.2f}")
        print(f"  Slippage:    ${report['total_slippage_cost']:.2f}")
        print(f"  Total Costs: ${report['total_costs']:.2f}")
        print("-" * 60)
        print(f"Net P&L:     ${report['net_pnl']:.2f}")
        print(f"Win Rate:    {report['win_rate']:.1%}")
        print("=" * 60)

        # Print trade list
        if report['trades']:
            print("\nTRADE LIST:")
            for trade in report['trades'][:10]:  # Show first 10
                print(
                    f"  {trade['timestamp']} | {trade['side']:4} | "
                    f"{trade['size']:8.4f} @ ${trade['fill_price']:10.2f} | "
                    f"Cost: ${trade['total_cost']:.2f}"
                )
            if len(report['trades']) > 10:
                print(f"  ... and {len(report['trades']) - 10} more trades")

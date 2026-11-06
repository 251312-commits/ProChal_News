"""Coin calculations shared by the bank and ranking views."""

from decimal import Decimal, InvalidOperation


def account_amount(value, *, strict=False) -> int:
    """Read integer coins from Sheets, including blank or formatted cells."""
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return 0
    try:
        number = Decimal(raw.replace(",", ""))
        amount = int(number)
        if strict and amount != number:
            raise ValueError("Fractional coin balance")
        return amount
    except (InvalidOperation, ValueError, OverflowError) as error:
        if strict:
            raise ValueError("Invalid coin balance") from error
        return 0


def net_coins(coins, loan=0) -> int:
    """Ranking balance after deducting the outstanding loan."""
    return account_amount(coins) - max(0, account_amount(loan))

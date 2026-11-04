from decimal import Decimal, ROUND_HALF_UP


def score_hundredths(normalized: float) -> int:
    """Map a 0–1 model output to hundredths of a point on the 0–100 game scale."""
    return int((Decimal(str(normalized)) * 10_000).to_integral_value(rounding=ROUND_HALF_UP))

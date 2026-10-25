"""Calculate money in decimal cents; keep existing database columns compatible."""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal('0.01')


def decimal(value):
    result = Decimal(str(value or 0))
    if not result.is_finite():
        raise ValueError('Pul miqdori chekli raqam bo‘lishi kerak')
    return result


def money(value):
    return float(decimal(value).quantize(CENT, rounding=ROUND_HALF_UP))


def money_sum(values):
    return money(sum((decimal(v) for v in values), Decimal(0)))


def percent(amount, rate):
    return money(decimal(amount) * decimal(rate) / Decimal(100))

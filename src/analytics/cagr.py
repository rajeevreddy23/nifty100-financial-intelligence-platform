"""Compound Annual Growth Rate (CAGR) calculation and turnaround logic."""
from typing import Tuple, Optional

def compute_cagr(base_val: Optional[float], end_val: Optional[float], n_years: int) -> Tuple[Optional[float], Optional[str]]:
    """
    Computes CAGR handling turnaround and sign change edge cases.
    Returns (cagr_percentage, flag_string).
    """
    if n_years <= 0:
        return None, "INVALID_PERIOD"
    if base_val is None or end_val is None:
        return None, "MISSING_DATA"

    try:
        base = float(base_val)
        end = float(end_val)
    except (ValueError, TypeError):
        return None, "PARSE_ERROR"

    if base == 0:
        return None, "ZERO_BASE"
    elif base > 0 and end > 0:
        cagr = ((end / base) ** (1.0 / n_years) - 1.0) * 100.0
        return round(cagr, 2), None
    elif base > 0 and end < 0:
        return None, "DECLINE_TO_LOSS"
    elif base < 0 and end > 0:
        return None, "TURNAROUND"
    elif base < 0 and end < 0:
        return None, "BOTH_NEGATIVE"

    return None, "UNKNOWN"

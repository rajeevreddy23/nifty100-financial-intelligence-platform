"""Cash Flow Intelligence and Capital Allocation classification."""
from typing import Tuple, Dict, Any

def classify_capital_allocation(cfo: float, cfi: float, cff: float, cfo_pat_ratio: float = 1.0) -> Tuple[str, str, str, str]:
    """
    Determines sign pattern (+/-) and assigns capital allocation label across 8 classes.
    Returns (cfo_sign, cfi_sign, cff_sign, pattern_label).
    """
    cfo_sign = '+' if cfo >= 0 else '-'
    cfi_sign = '+' if cfi >= 0 else '-'
    cff_sign = '+' if cff >= 0 else '-'
    
    pattern = (cfo_sign, cfi_sign, cff_sign)
    
    if pattern == ('+', '-', '-'):
        if cfo_pat_ratio > 1.0:
            label = "Shareholder Returns"
        else:
            label = "Reinvestor"
    elif pattern == ('+', '-', '+'):
        label = "Expansion via External Capital"
    elif pattern == ('+', '+', '-'):
        label = "Asset Divestment & Debt Repayment"
    elif pattern == ('+', '+', '+'):
        label = "Asset Liquidation & Capital Inflow"
    elif pattern == ('-', '-', '+'):
        label = "High Growth / CapEx External Funding"
    elif pattern == ('-', '-', '-'):
        label = "Severe Cash Distress"
    elif pattern == ('-', '+', '+'):
        label = "Asset Sale to Fund Operations"
    elif pattern == ('-', '+', '-'):
        label = "Divestment to Pay Debt Under Stress"
    else:
        label = "Unclassified"
        
    return cfo_sign, cfi_sign, cff_sign, label

def check_distress_pattern(cfo: float, cff: float) -> bool:
    """Flag as distress if CFO < 0 and CFF > 0 (external capital funding operational losses)."""
    return cfo < 0 and cff > 0

def get_cfo_quality(cfo_pat: float) -> str:
    """Classify CFO/PAT ratio: >1.0 High Quality, <0.5 Accrual Risk, else Normal."""
    if cfo_pat is None:
        return "N/A"
    if cfo_pat > 1.0:
        return "High Quality Earnings"
    elif cfo_pat < 0.5:
        return "Accrual Risk"
    return "Balanced"

def get_capex_intensity_label(capex_intensity: float) -> str:
    """Classify CapEx intensity: <3% Asset-Light, >8% Capital Intensive, else Moderate."""
    if capex_intensity is None:
        return "N/A"
    if capex_intensity < 3.0:
        return "Asset-Light"
    elif capex_intensity > 8.0:
        return "Capital Intensive"
    return "Moderate"

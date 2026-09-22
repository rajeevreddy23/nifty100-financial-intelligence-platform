"""Normalisation functions for company tickers and financial year strings."""
import re
from typing import Optional

MONTH_MAP = {
    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12',
    'JANUARY': '01', 'FEBRUARY': '02', 'MARCH': '03', 'APRIL': '04',
    'JUNE': '06', 'JULY': '07', 'AUGUST': '08', 'SEPTEMBER': '09',
    'OCTOBER': '10', 'NOVEMBER': '11', 'DECEMBER': '12'
}

def normalize_ticker(ticker: Optional[str]) -> str:
    """Normalize NSE ticker: strip whitespace, uppercase, validate."""
    if ticker is None:
        return 'MISSING'
    clean = str(ticker).strip().upper()
    if not clean or clean == 'NAN' or clean == 'NONE':
        return 'MISSING'
    if 2 <= len(clean) <= 15:
        return clean
    return 'INVALID'

def normalize_year(year_val: Optional[object]) -> str:
    """Standardise year string to YYYY-MM format. Handles multiple source patterns."""
    if year_val is None:
        return 'PARSE_ERROR'
    s = str(year_val).strip()
    if not s or s.upper() in ('NAN', 'NONE', 'XYZ', 'NULL'):
        return 'PARSE_ERROR'

    # Already YYYY-MM
    if re.match(r'^\d{4}-\d{2}$', s):
        return s

    # Integer 4-digit year like 2023 -> 2023-03
    if re.match(r'^\d{4}$', s):
        return f"{s}-03"

    # FY23, FY2023, FY 24
    m_fy = re.match(r'^FY\s*(\d{2}|\d{4})$', s, re.IGNORECASE)
    if m_fy:
        y = m_fy.group(1)
        if len(y) == 2:
            return f"20{y}-03"
        return f"{y}-03"

    # Mar-23, Mar 23, March-2023, Dec-22, Jun-23, Mar 2016 9m, Mar 2023 15
    # Pattern: Month (- or space) Year (2 or 4 digits) optionally followed by text
    m = re.match(r'^([A-Za-z]+)[\s\-_/]+(\d{4}|\d{2})', s)
    if m:
        mon_str = m.group(1).upper()
        y_str = m.group(2)
        if len(y_str) == 2:
            full_year = f"20{y_str}"
        else:
            full_year = y_str
        
        if mon_str in MONTH_MAP:
            return f"{full_year}-{MONTH_MAP[mon_str]}"
        
    # YYYY-Month like 2023-Mar
    m2 = re.match(r'^(\d{4})[\s\-_/]+([A-Za-z]+)$', s)
    if m2:
        full_year = m2.group(1)
        mon_str = m2.group(2).upper()
        if mon_str in MONTH_MAP:
            return f"{full_year}-{MONTH_MAP[mon_str]}"

    return 'PARSE_ERROR'

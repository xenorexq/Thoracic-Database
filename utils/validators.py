"""
Validation utilities for thoracic entry application.

This module centralises input validation and conversion routines used across
different parts of the GUI.  Functions return either a tuple (bool, str)
where the boolean indicates validity and the string contains an error
message, or they raise exceptions when appropriate.  Separating validation
logic from the UI simplifies testing and reuse.
"""

from __future__ import annotations

import datetime
from typing import Tuple, Optional


def validate_birth_ym4(value: str) -> Tuple[bool, str]:
    """Validate birth_ym4 input (four digits: yymm)."

    Accepts '9007' representing 1990-07. Years 00鈥?9 are assumed either 1900s or
    2000s; the exact century is not important for storage.  Months must be
    between 01 and 12.  Leading zeros are required.

    Returns:
        (True, "") if valid, otherwise (False, error message).
    """
    if not value or len(value) != 4 or not value.isdigit():
        return False, "出生年月必须为四位数字(yymm)"
    yy = int(value[:2])
    mm = int(value[2:])
    if mm < 1 or mm > 12:
        return False, "出生月份必须在01-12之间"
    return True, ""


def validate_date6(value: str) -> Tuple[bool, str]:
    """Validate a 6-digit date input (yymmdd)."

    Performs a simple check that year/month/day form a plausible date.  Only
    rejects clearly invalid month/day combinations; does not consider leap years
    or 30/31 day distinctions beyond basic sanity.

    Args:
        value: Six digits representing yymmdd.
    Returns:
        (True, "") if valid, otherwise (False, error message).
    """
    if not value or len(value) != 6 or not value.isdigit():
        return False, "手术日期必须为六位数字(yymmdd)"
    yy = int(value[:2])
    mm = int(value[2:4])
    dd = int(value[4:])
    if mm < 1 or mm > 12:
        return False, "月份必须在01-12之间"
    if dd < 1 or dd > 31:
        return False, "日期必须在01-31之间"
    # Additional simple check: limit February and April/June/Sept/Nov (max 30)
    if mm in {4, 6, 9, 11} and dd > 30:
        # April, June, September and November have max 30 days
        return False, f"{mm}月最多30天"
    if mm == 2 and dd > 29:
        # February has max 29 days (ignoring leap year)
        return False, "2月最多29天"
    return True, ""


def validate_hhmm(value: str) -> Tuple[bool, str]:
    """Validate a 4-digit time input (hhmm)."

    Hours must be 00鈥?3 and minutes 00鈥?9.
    """
    if not value or len(value) != 4 or not value.isdigit():
        return False, "时间必须为四位数字(hhmm)"
    hh = int(value[:2])
    mm = int(value[2:])
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return False, "时间格式错误，小时应为00-23，分钟应为00-59"
    return True, ""


def compute_duration(start_hhmm: str, end_hhmm: str) -> Optional[int]:
    """Compute duration in minutes between two hhmm strings."

    If end is earlier than start (cross-day), adds 24 hours.  Returns None if
    inputs are invalid.
    """
    valid_start, _ = validate_hhmm(start_hhmm)
    valid_end, _ = validate_hhmm(end_hhmm)
    if not (valid_start and valid_end):
        return None
    start_minutes = int(start_hhmm[:2]) * 60 + int(start_hhmm[2:])
    end_minutes = int(end_hhmm[:2]) * 60 + int(end_hhmm[2:])
    duration = end_minutes - start_minutes
    if duration < 0:
        duration += 24 * 60
    return duration


def format_date6(value: str) -> str:
    """Format 6-digit date yymmdd into yyyy-mm-dd for display."

    00鈥?0 prefix map to 2000鈥?030, otherwise 1900鈥?999.  Returns empty string
    if input invalid.
    """
    ok, _ = validate_date6(value)
    if not ok:
        return ""
    yy = int(value[:2])
    mm = value[2:4]
    dd = value[4:]
    if yy <= 30:
        year = f"20{yy:02d}"
    else:
        year = f"19{yy:02d}"
    return f"{year}-{mm}-{dd}"


def format_birth_ym4(value: str) -> str:
    """Format 4-digit yymm to a more user-friendly yyyy-mm display."

    This uses the same century rule as format_date6.
    """
    ok, _ = validate_birth_ym4(value)
    if not ok:
        return ""
    yy = int(value[:2])
    mm = value[2:]
    if yy <= 30:
        year = f"20{yy:02d}"
    else:
        year = f"19{yy:02d}"
    return f"{year}-{mm}"

# ==== 新增的出生年月(yyyymm)校验和格式化函数 ====
def validate_birth_ym6(value: str) -> Tuple[bool, str]:
    """Validate birth_ym6 input (six digits: yyyymm).

    Accepts values like '198507' representing 1985-07.  Years from 1900 to 2099
    are considered valid.  Months must be between 01 and 12.  Leading zeros are
    required.  Returns (True, "") if valid, otherwise (False, error message).
    """
    if not value or len(value) != 6 or not value.isdigit():
        return False, "出生年月必须为六位数字(yyyymm)"
        
    year = int(value[:4])
    month = int(value[4:])
    if year < 1900 or year > 2099:
        return False, "年份必须在1900-2099之间"
    if month < 1 or month > 12:
        return False, "月份必须在01-12之间"
    return True, ""


def format_birth_ym6(value: str) -> str:
    """Format 6-digit yyyymm to a more user-friendly yyyy-mm display."""
    ok, _ = validate_birth_ym6(value)
    if not ok:
        return ""
    year = value[:4]
    month = value[4:]
    return f"{year}-{month}"


# 新增: 验证住院号仅包含字母和数字
def validate_hospital_id(value: str) -> Tuple[bool, str]:
    """Validate hospital_id: only letters and digits are allowed.

    Args:
        value: The hospital_id string to validate.

    Returns:
        A tuple (True, "") if valid, otherwise (False, error message).
    """
    if not value:
        return False, "住院号为必填项"
    # Check for invalid characters
    if not value.isalnum():
        return False, "住院号格式错误，只能包含字母和数字"
    return True, ""

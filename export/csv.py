"""
CSV export utilities for thoracic entry application.

These functions write one CSV file per table.  For a single patient export,
files are named with a prefix (e.g. ``patient123_Patient.csv``).  For full
database export, file names are simply ``Patient.csv`` etc.

Column headers are written as the first row.  Values are written as strings.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

from db.models import Database
# 引入日期格式化函数以统一导出中的日期格式
from utils.validators import format_date6, format_birth_ym4, format_birth_ym6
# 引入分期查询函数用于导出时补充临床分期
from staging.lookup import get_lung_stage, get_eso_stage

# Fields that should not appear in exported files.  These columns either come from
# deprecated UI elements (e.g. vendor_lab) or have been removed from the
# current version of the application (e.g. lymph node totals).  We also
# remove the internal numeric patient_id in favour of hospital_id for unique
# identification in exported data.
EXCLUDE_FIELDS = {"vendor_lab", "ln_total", "ln_positive", "patient_id"}

# 日期字段映射。需要统一导出格式的列名列表。
# birth_ym4 将在格式化时保持为 yyyymm；其他列将格式化为 yyyymmdd。
DATE_FIELDS_8 = {
    "surgery_date6",
    "report_date",
    "test_date",
    "last_visit_date",
    "death_date",
    "relapse_date",
}

def _format_value(col: str, val: object) -> object:
    """根据列名格式化日期字段。

    对于 6 位的日期 (yymmdd) 使用 format_date6 转换为 yyyy-mm-dd 再去掉横杠。
    对于 birth_ym4 兼容旧的 4 位格式以及新的 6 位格式，输出 yyyymm。
    其他字段返回原值。
    """
    if val is None or val == "":
        return val
    # convert to string for processing
    s = str(val)
    # birth year-month
    if col == "birth_ym4":
        # 长度为 4 的旧格式 yymm
        if len(s) == 4 and s.isdigit():
            formatted = format_birth_ym4(s)
            return formatted.replace("-", "") if formatted else s
        # 长度为 6 的新格式 yyyymm
        if len(s) == 6 and s.isdigit():
            formatted = format_birth_ym6(s)
            return formatted.replace("-", "") if formatted else s
        # 其它情况不处理
        return s
    # 日期字段
    if col in DATE_FIELDS_8:
        # 如果已经是 8 位数字，则直接返回
        if len(s) == 8 and s.isdigit():
            return s
        # 如果包含横杠，则去除横杠
        if "-" in s:
            return s.replace("-", "")
        # 如果是 6 位数字 (yymmdd)，则转化为 yyyy-mm-dd 后再去除横杠
        if len(s) == 6 and s.isdigit():
            formatted = format_date6(s)
            return formatted.replace("-", "") if formatted else s
        # 其它情况不处理
        return s
    return val

def _format_row_dates(row_dict: dict) -> dict:
    """格式化行中的日期字段。"""
    new_row = {}
    for k, v in row_dict.items():
        if k in EXCLUDE_FIELDS:
            continue
        new_row[k] = _format_value(k, v)
    return new_row

def _annotate_stage(db: Database, patient_row: dict) -> dict:
    """根据患者的 TNM 信息补充临床分期字段。

    对于肺癌和食管癌分别计算分期，并返回包含新增字段的字典。
    如果无法计算分期，则对应字段值为 None。
    """
    cancer_type = patient_row.get("cancer_type")
    result = {}
    if cancer_type == "肺癌":
        t = patient_row.get("lung_t") or ""
        n = patient_row.get("lung_n") or ""
        m = patient_row.get("lung_m") or ""
        if t and n and m:
            stage = get_lung_stage(db, t, n, m)
            result["lung_stage"] = stage
        else:
            result["lung_stage"] = None
        # 不计算食管分期
        result["eso_stage"] = None
    elif cancer_type == "食管癌":
        t = patient_row.get("eso_t") or ""
        n = patient_row.get("eso_n") or ""
        m = patient_row.get("eso_m") or ""
        hist = patient_row.get("eso_histology") or ""
        grade = patient_row.get("eso_grade") or ""
        loc = patient_row.get("eso_location") or ""
        if t and n and m:
            stage = get_eso_stage(db, t, n, m, hist, grade, loc)
            result["eso_stage"] = stage
        else:
            result["eso_stage"] = None
        result["lung_stage"] = None
    else:
        # 未知癌种
        result["lung_stage"] = None
        result["eso_stage"] = None
    return result


def _clean_row(row_dict: dict) -> dict:
    """Remove unwanted fields from a row dictionary before export.

    在清理字段的同时，统一格式化日期字段。
    """
    # 先格式化日期
    formatted = _format_row_dates(row_dict)
    # 再删除排除字段
    return {k: v for k, v in formatted.items() if k not in EXCLUDE_FIELDS}


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    """Write a list of dictionaries to a CSV file after cleaning and formatting."""
    # Convert to list and remove excluded fields while formatting dates
    rows_list = []
    for row in rows:
        if not isinstance(row, dict):
            row_dict = dict(row)
        else:
            row_dict = row
        rows_list.append(_clean_row(row_dict))
    with path.open("w", newline="", encoding="utf-8") as f:
        if not rows_list:
            return
        writer = csv.DictWriter(f, fieldnames=list(rows_list[0].keys()))
        writer.writeheader()
        for row in rows_list:
            writer.writerow(row)


def export_patient_to_csv(db: Database, patient_id: int, dir_path: Path) -> List[Path]:
    """Export a single patient to CSV files.

    Returns list of file paths created.
    """
    files: List[Path] = []
    # Create directory if not exists
    dir_path.mkdir(parents=True, exist_ok=True)
    # Determine prefix for file names
    prefix = f"patient{patient_id}"
    # Prepare per-table rows
    tables = ["Patient", "Surgery", "Pathology", "Molecular", "FollowUp"]
    # Fetch patient once to retrieve hospital_id
    patient_row = db.get_patient_by_id(patient_id)
    hospital_id = None
    patient_dict_list: List[dict] = []
    if patient_row:
        # Convert to dict so we can add to export
        pr_dict = dict(patient_row)
        # 在导出患者信息前补充临床分期字段
        pr_dict.update(_annotate_stage(db, pr_dict))
        patient_dict_list = [pr_dict]
        hospital_id = pr_dict.get("hospital_id")
    for table in tables:
        rows: List[dict]
        if table == "Patient":
            rows = patient_dict_list
        elif table == "FollowUp":
            row = db.get_followup(patient_id)
            # If follow-up exists, attach hospital_id
            if row:
                rdict = dict(row)
                if hospital_id is not None:
                    # Prepend hospital_id for identification
                    rdict = {"hospital_id": hospital_id, **rdict}
                rows = [rdict]
            else:
                rows = []
        else:
            if table == "Surgery":
                items = db.get_surgeries_by_patient(patient_id)
            elif table == "Pathology":
                items = db.get_pathologies_by_patient(patient_id)
            elif table == "Molecular":
                items = db.get_molecular_by_patient(patient_id)
            else:
                items = []
            rows = []
            for row in items:
                rdict = dict(row)
                if hospital_id is not None:
                    # Add hospital_id to each row for unique identification
                    rdict = {"hospital_id": hospital_id, **rdict}
                rows.append(rdict)
        file_path = dir_path / f"{prefix}_{table}.csv"
        # Clean and write rows to CSV
        _write_csv(file_path, rows)
        files.append(file_path)
    return files


def export_all_to_csv(db: Database, dir_path: Path) -> List[Path]:
    """Export entire database to CSV files.

    Returns list of file paths created.
    """
    files: List[Path] = []
    dir_path.mkdir(parents=True, exist_ok=True)
    # Precompute mapping from patient_id to hospital_id for adding to other tables
    patient_rows = db.export_table("Patient")
    pat_map = {}
    for row in patient_rows:
        row_dict = dict(row)
        pat_map[row_dict.get("patient_id")] = row_dict.get("hospital_id")
    for table in ["Patient", "Surgery", "Pathology", "Molecular", "FollowUp"]:
        rows = db.export_table(table)
        rows_dicts: List[dict] = []
        for row in rows:
            rdict = dict(row)
            if table == "Patient":
                # 为每个患者行补充临床分期
                rdict.update(_annotate_stage(db, rdict))
            else:
                # For non-Patient tables, add hospital_id for unique identification
                pid = rdict.get("patient_id")
                if pid in pat_map:
                    rdict = {"hospital_id": pat_map[pid], **rdict}
            rows_dicts.append(rdict)
        file_path = dir_path / f"{table}.csv"
        # Clean and write rows to CSV
        _write_csv(file_path, rows_dicts)
        files.append(file_path)
    return files

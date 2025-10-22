"""
Excel export utilities using openpyxl.

These functions allow exporting either a single patient's data (across all
tables) or the entire database into an Excel workbook with multiple sheets.
The workbook will contain a sheet per table with column headers.  For a
single patient export, only the rows associated with that patient are included.

Requires openpyxl; ensure it is installed prior to packaging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from openpyxl import Workbook

from db.models import Database
# 引入日期格式化函数
from utils.validators import format_date6, format_birth_ym4, format_birth_ym6
# 引入分期查询函数
from staging.lookup import get_lung_stage, get_eso_stage

# Fields that should not appear in exported files.  These columns either come from
# deprecated UI elements (e.g. vendor_lab) or have been removed from the
# current version of the application (e.g. lymph node totals).
EXCLUDE_FIELDS = {"vendor_lab", "ln_total", "ln_positive", "patient_id"}

# 与 CSV 导出一致的日期字段集合
DATE_FIELDS_8 = {
    "surgery_date6",
    "report_date",
    "test_date",
    "last_visit_date",
    "death_date",
    "relapse_date",
}

def _format_value(col: str, val: object) -> object:
    """根据列名格式化日期字段。"""
    if val is None or val == "":
        return val
    s = str(val)
    if col == "birth_ym4":
        if len(s) == 4 and s.isdigit():
            formatted = format_birth_ym4(s)
            return formatted.replace("-", "") if formatted else s
        if len(s) == 6 and s.isdigit():
            formatted = format_birth_ym6(s)
            return formatted.replace("-", "") if formatted else s
        return s
    if col in DATE_FIELDS_8:
        if len(s) == 8 and s.isdigit():
            return s
        if "-" in s:
            return s.replace("-", "")
        if len(s) == 6 and s.isdigit():
            formatted = format_date6(s)
            return formatted.replace("-", "") if formatted else s
        return s
    return val

def _format_row_dates(row_dict: dict) -> dict:
    new_row = {}
    for k, v in row_dict.items():
        if k in EXCLUDE_FIELDS:
            continue
        new_row[k] = _format_value(k, v)
    return new_row

def _annotate_stage(db: Database, patient_row: dict) -> dict:
    """根据患者 TNM 信息补充分期字段。"""
    cancer_type = patient_row.get("cancer_type")
    result = {}
    if cancer_type == "肺癌":
        t = patient_row.get("lung_t") or ""
        n = patient_row.get("lung_n") or ""
        m = patient_row.get("lung_m") or ""
        if t and n and m:
            result["lung_stage"] = get_lung_stage(db, t, n, m)
        else:
            result["lung_stage"] = None
        result["eso_stage"] = None
    elif cancer_type == "食管癌":
        t = patient_row.get("eso_t") or ""
        n = patient_row.get("eso_n") or ""
        m = patient_row.get("eso_m") or ""
        hist = patient_row.get("eso_histology") or ""
        grade = patient_row.get("eso_grade") or ""
        loc = patient_row.get("eso_location") or ""
        if t and n and m:
            result["eso_stage"] = get_eso_stage(db, t, n, m, hist, grade, loc)
        else:
            result["eso_stage"] = None
        result["lung_stage"] = None
    else:
        result["lung_stage"] = None
        result["eso_stage"] = None
    return result


def _clean_row(row_dict: dict) -> dict:
    """Remove unwanted fields and format date values before export."""
    formatted = _format_row_dates(row_dict)
    return {k: v for k, v in formatted.items() if k not in EXCLUDE_FIELDS}


def _write_sheet(wb: Workbook, sheet_name: str, rows: Iterable[dict]) -> None:
    ws = wb.create_sheet(title=sheet_name)
    # Convert to list and remove excluded fields with date formatting
    rows_list = []
    for row in rows:
        if not isinstance(row, dict):
            row_dict = dict(row)
        else:
            row_dict = row
        rows_list.append(_clean_row(row_dict))
    if not rows_list:
        return
    # Write header based on cleaned row keys
    header = list(rows_list[0].keys())
    ws.append(header)
    for row in rows_list:
        ws.append([row.get(col) for col in header])


def export_patient_to_excel(db: Database, patient_id: int, file_path: Path) -> None:
    """Export data for a single patient to an Excel file."""
    wb = Workbook()
    # Remove the default sheet created by openpyxl
    wb.remove(wb.active)
    # Fetch rows per table
    tables = ["Patient", "Surgery", "Pathology", "Molecular", "FollowUp"]
    # Fetch the patient once to obtain hospital_id.  Convert sqlite3.Row to dict
    patient_row = db.get_patient_by_id(patient_id)
    # patient_dict_list is a list of dicts to feed into sheet writer
    patient_dict_list: List[dict] = []
    # Determine hospital_id from the converted dict
    hospital_id = None
    if patient_row:
        pr_dict = dict(patient_row)
        # 为患者行补充分期字段
        pr_dict.update(_annotate_stage(db, pr_dict))
        patient_dict_list = [pr_dict]
        hospital_id = pr_dict.get("hospital_id")
    for table in tables:
        if table == "Patient":
            rows = patient_dict_list
        elif table == "FollowUp":
            row = db.get_followup(patient_id)
            if row:
                rdict = dict(row)
                if hospital_id is not None:
                    rdict = {"hospital_id": hospital_id, **rdict}
                rows = [rdict]
            else:
                rows = []
        else:
            # Many-to-one tables
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
                    rdict = {"hospital_id": hospital_id, **rdict}
                rows.append(rdict)
        _write_sheet(wb, table, rows)
    wb.save(file_path)


def export_all_to_excel(db: Database, file_path: Path) -> None:
    """Export entire database to an Excel file (one sheet per table)."""
    wb = Workbook()
    # Remove default sheet
    wb.remove(wb.active)
    # Precompute mapping from patient_id to hospital_id
    patient_rows = db.export_table("Patient")
    pat_map = {}
    for row in patient_rows:
        rdict = dict(row)
        pat_map[rdict.get("patient_id")] = rdict.get("hospital_id")
    # For each table, fetch all rows and attach hospital_id for non-Patient tables
    for table in ["Patient", "Surgery", "Pathology", "Molecular", "FollowUp"]:
        rows = db.export_table(table)
        rows_dicts: List[dict] = []
        for row in rows:
            rdict = dict(row)
            if table == "Patient":
                # 为患者行补充分期字段
                rdict.update(_annotate_stage(db, rdict))
            else:
                pid = rdict.get("patient_id")
                if pid in pat_map:
                    rdict = {"hospital_id": pat_map[pid], **rdict}
            rows_dicts.append(rdict)
        _write_sheet(wb, table, rows_dicts)
    wb.save(file_path)

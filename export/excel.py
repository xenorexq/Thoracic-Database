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

# Fields that should not appear in exported files.  These columns either come from
# deprecated UI elements (e.g. vendor_lab) or have been removed from the
# current version of the application (e.g. lymph node totals).
EXCLUDE_FIELDS = {"vendor_lab", "ln_total", "ln_positive", "patient_id"}


def _clean_row(row_dict: dict) -> dict:
    """Remove unwanted fields from a row dictionary before export."""
    return {k: v for k, v in row_dict.items() if k not in EXCLUDE_FIELDS}


def _write_sheet(wb: Workbook, sheet_name: str, rows: Iterable[dict]) -> None:
    ws = wb.create_sheet(title=sheet_name)
    # Convert to list and remove excluded fields
    rows_list = [ _clean_row(dict(row)) if not isinstance(row, dict) else _clean_row(row) for row in rows ]
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
    patient_dict_list = [dict(patient_row)] if patient_row else []
    # Determine hospital_id from the converted dict
    hospital_id = None
    if patient_row:
        pr_dict = patient_dict_list[0]
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
            if table != "Patient":
                pid = rdict.get("patient_id")
                if pid in pat_map:
                    rdict = {"hospital_id": pat_map[pid], **rdict}
            rows_dicts.append(rdict)
        _write_sheet(wb, table, rows_dicts)
    wb.save(file_path)

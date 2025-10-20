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

# Fields that should not appear in exported files.  These columns either come from
# deprecated UI elements (e.g. vendor_lab) or have been removed from the
# current version of the application (e.g. lymph node totals).  We also
# remove the internal numeric patient_id in favour of hospital_id for unique
# identification in exported data.
EXCLUDE_FIELDS = {"vendor_lab", "ln_total", "ln_positive", "patient_id"}


def _clean_row(row_dict: dict) -> dict:
    """Remove unwanted fields from a row dictionary before export."""
    return {k: v for k, v in row_dict.items() if k not in EXCLUDE_FIELDS}


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    # Convert to list and remove excluded fields
    rows_list = [ _clean_row(dict(row)) if not isinstance(row, dict) else _clean_row(row) for row in rows ]
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
            # For non-Patient tables, add hospital_id for unique identification
            if table != "Patient":
                pid = rdict.get("patient_id")
                if pid in pat_map:
                    rdict = {"hospital_id": pat_map[pid], **rdict}
            rows_dicts.append(rdict)
        file_path = dir_path / f"{table}.csv"
        # Clean and write rows to CSV
        _write_csv(file_path, rows_dicts)
        files.append(file_path)
    return files

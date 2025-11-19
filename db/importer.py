"""
Utility functions for merging data from multiple SQLite databases into a single
destination database.  Import operations are organised at the patient level
using the `hospital_id` as the unique key.  Only patients that do not
already exist in the destination are inserted, along with all of their
associated records (surgery, pathology, molecular and follow‑up events).

The public function `import_databases` accepts a Database instance and a
sequence of file paths.  It handles opening each source file, reading
patients, and copying records using the Database API.  Basic error handling
and logging is provided to help trace failures during the merge process.

Note: Transactions are not explicitly managed here because the Database
API commits after each insert.  If improved performance is desired in the
future, consider exposing batch insert operations on the Database class.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import Database

# Configure a module‑level logger.  Logs will be written to ``importer.log``
# in the working directory.  If no handlers are present, add a basic one.
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("importer.log", encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def import_databases(db: Database, source_paths: Iterable[str | Path]) -> Dict[str, int]:
    """Merge patient data from multiple SQLite databases into the destination.

    Args:
        db: The destination ``Database`` instance into which records will be merged.
        source_paths: Iterable of file paths to SQLite databases to import.

    Returns:
        A dictionary summarising the number of records imported for each table
        (keys: ``Patient``, ``Surgery``, ``Pathology``, ``Molecular``,
        ``FollowUpEvent``).  Counts are cumulative across all source files.

    Behavior:
        * Patients are uniquely identified by ``hospital_id``.  If a hospital
          ID already exists in the destination, that patient and all of its
          related records are skipped.
        * For each new patient in a source database, all associated surgery,
          pathology, molecular and follow‑up event records are copied.
        * Any errors encountered while processing a particular source file are
          logged and suppressed; the import process will continue with the
          remaining files.
    """
    stats: Dict[str, int] = {
        "Patient": 0,
        "Surgery": 0,
        "Pathology": 0,
        "Molecular": 0,
        "FollowUpEvent": 0,
    }

    # Build a set of existing hospital_ids from the destination DB once.  Use
    # ``row[0]`` instead of ``row['hospital_id']`` for speed since the
    # destination cursor returns simple tuples by default.
    try:
        dest_hospital_ids = set(
            row[0]
            for row in db.conn.execute("SELECT hospital_id FROM Patient").fetchall()
            if row[0]
        )
    except Exception as e:
        logger.error(f"Failed to read destination hospital IDs: {e}")
        raise

    for path in source_paths:
        try:
            # Accept both string and Path objects
            src_path = Path(path)
            if not src_path.is_file():
                logger.warning(f"Source file {src_path} does not exist or is not a file; skipping")
                continue
            logger.info(f"Importing from {src_path}")
            src_conn = sqlite3.connect(src_path)
            src_conn.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"Unable to open {path}: {e}")
            continue

        # Mapping from src patient_id to dest patient_id for patients newly
        # inserted from this source.  Used to associate child records.
        id_map: Dict[int, int] = {}
        try:
            # Fetch all patients from the source
            cur_pat = src_conn.execute("SELECT * FROM Patient")
            for row in cur_pat:
                hospital_id = row["hospital_id"]
                if not hospital_id:
                    continue
                if hospital_id in dest_hospital_ids:
                    # Skip patients already present in destination
                    continue
                # Build a dict of patient fields excluding the primary key.
                patient_data = {k: row[k] for k in row.keys() if k != "patient_id"}
                try:
                    new_pid = db.insert_patient(patient_data)
                    id_map[row["patient_id"]] = new_pid
                    dest_hospital_ids.add(hospital_id)
                    stats["Patient"] += 1
                except Exception as ie:
                    logger.error(f"Failed to insert patient {hospital_id}: {ie}")
                    # Skip this patient (do not add to id_map)
                    continue

            # If no new patients were inserted, skip copying child tables
            if not id_map:
                logger.info(f"No new patients found in {src_path}; skipping child tables")
                src_conn.close()
                continue

            # Import surgeries
            for src_pid, dest_pid in id_map.items():
                try:
                    s_cur = src_conn.execute(
                        "SELECT * FROM Surgery WHERE patient_id = ?",
                        (src_pid,),
                    )
                    for srow in s_cur:
                        # Build data dictionary excluding primary and foreign keys
                        data = {k: srow[k] for k in srow.keys() if k not in ("surgery_id", "patient_id")}
                        try:
                            db.insert_surgery(dest_pid, data)
                            stats["Surgery"] += 1
                        except Exception as se:
                            logger.error(
                                f"Failed to insert surgery for patient {dest_pid} (src {src_pid}): {se}"
                            )
                except Exception as e:
                    logger.error(f"Error reading surgeries from {src_path}: {e}")

            # Import pathology
            for src_pid, dest_pid in id_map.items():
                try:
                    p_cur = src_conn.execute(
                        "SELECT * FROM Pathology WHERE patient_id = ?",
                        (src_pid,),
                    )
                    for prow in p_cur:
                        data = {k: prow[k] for k in prow.keys() if k not in ("path_id", "patient_id")}
                        try:
                            db.insert_pathology(dest_pid, data)
                            stats["Pathology"] += 1
                        except Exception as pe:
                            logger.error(
                                f"Failed to insert pathology for patient {dest_pid} (src {src_pid}): {pe}"
                            )
                except Exception as e:
                    logger.error(f"Error reading pathology from {src_path}: {e}")

            # Import molecular
            for src_pid, dest_pid in id_map.items():
                try:
                    m_cur = src_conn.execute(
                        "SELECT * FROM Molecular WHERE patient_id = ?",
                        (src_pid,),
                    )
                    for mrow in m_cur:
                        data = {k: mrow[k] for k in mrow.keys() if k not in ("mol_id", "patient_id")}
                        try:
                            db.insert_molecular(dest_pid, data)
                            stats["Molecular"] += 1
                        except Exception as me:
                            logger.error(
                                f"Failed to insert molecular for patient {dest_pid} (src {src_pid}): {me}"
                            )
                except Exception as e:
                    logger.error(f"Error reading molecular from {src_path}: {e}")

            # Import follow-up events
            for src_pid, dest_pid in id_map.items():
                try:
                    fu_cur = src_conn.execute(
                        "SELECT * FROM FollowUpEvent WHERE patient_id = ?",
                        (src_pid,),
                    )
                    for evrow in fu_cur:
                        # Extract event details; evrow is a sqlite3.Row
                        ev_dict = dict(evrow)
                        event_date = ev_dict.get("event_date")
                        event_type = ev_dict.get("event_type")
                        event_details = ev_dict.get("event_details") or ""
                        event_code = ev_dict.get("event_code")
                        try:
                            db.insert_followup_event(dest_pid, event_date, event_type, event_details, event_code)
                            stats["FollowUpEvent"] += 1
                        except Exception as fe:
                            logger.error(
                                f"Failed to insert follow-up event for patient {dest_pid} (src {src_pid}): {fe}"
                            )
                except Exception as e:
                    logger.error(f"Error reading follow-up events from {src_path}: {e}")

        except Exception as e:
            logger.error(f"Unexpected error importing from {path}: {e}")
        finally:
            try:
                src_conn.close()
            except Exception:
                pass

    return stats
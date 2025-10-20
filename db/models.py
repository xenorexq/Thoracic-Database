"""
Database models and data access functions for the thoracic entry application.

This module encapsulates all interactions with the underlying SQLite database.  It
defines the schema for each of the five primary tables (Patient, Surgery,
Pathology, Molecular, FollowUp) as well as three mapping tables used for
automated stage lookups.  When the database is first opened, the schema is
created if it does not already exist.  A simple Data Access Object (DAO)
pattern is used to abstract common CRUD operations.

Note: SQLite will enforce referential integrity via foreign keys.  The
``PRAGMA foreign_keys = ON`` statement is executed on connection.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterable


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "thoracic.db"




def row_to_dict(row):
    """将sqlite3.Row转换为字典"""
    if row is None:
        return None
    return dict(row)

class Database:
    """SQLite database wrapper for thoracic entry application."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.conn = sqlite3.connect(self.db_path)
        # Enable foreign key constraints
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        """Create tables and indexes if they do not already exist."""
        cur = self.conn.cursor()

        # Patient table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Patient (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_id TEXT UNIQUE,
                cancer_type TEXT,
                sex TEXT,
                birth_ym4 TEXT,
                pack_years REAL,
                multi_primary INTEGER,
                lung_t TEXT,
                lung_n TEXT,
                lung_m TEXT,
                eso_t TEXT,
                eso_n TEXT,
                eso_m TEXT,
                eso_histology TEXT,
                eso_grade TEXT,
                eso_location TEXT,
                nac_chemo INTEGER,
                nac_chemo_cycles INTEGER,
                nac_immuno INTEGER,
                nac_immuno_cycles INTEGER,
                nac_targeted INTEGER,
                nac_targeted_cycles INTEGER,
                adj_chemo INTEGER,
                adj_chemo_cycles INTEGER,
                adj_immuno INTEGER,
                adj_immuno_cycles INTEGER,
                adj_targeted INTEGER,
                adj_targeted_cycles INTEGER,
                notes_patient TEXT
            );
            """
        )
        # Index for cancer_type
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_patient_cancer_type ON Patient(cancer_type);"
        )

        # Surgery table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Surgery (
                surgery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                cancer_type TEXT,
                surgery_date6 TEXT,
                indication TEXT,
                planned INTEGER DEFAULT 1,
                completed INTEGER DEFAULT 1,
                start_hhmm INTEGER,
                end_hhmm INTEGER,
                duration_min INTEGER,
                ln_dissection INTEGER DEFAULT 1,
                r0 INTEGER DEFAULT 1,
                -- Lung specific
                approach TEXT,
                scope_lung TEXT,
                lobe TEXT,
                bilateral INTEGER,
                lesion_count INTEGER,
                main_lesion_size_cm REAL,
                -- Esophageal specific
                esophagus_site TEXT,
                notes_surgery TEXT,
                FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
            );
            """
        )
        # Index on patient_id for faster lookups
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_surgery_patient_id ON Surgery(patient_id);"
        )

        # Pathology table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Pathology (
                path_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                specimen_type TEXT,
                histology TEXT,
                differentiation TEXT,
                pt TEXT,
                pn TEXT,
                pm TEXT,
                p_stage TEXT,
                lvi INTEGER,
                pni INTEGER,
                pleural_invasion INTEGER,
                ln_total INTEGER,
                ln_positive INTEGER,
                trg INTEGER,
                report_date TEXT,
                notes_path TEXT,
                FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_path_patient_id ON Pathology(patient_id);"
        )

        # Molecular table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Molecular (
                mol_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                platform TEXT,
                vendor_lab TEXT,
                gene TEXT,
                variant TEXT,
                pdl1_percent REAL,
                tmb_msi TEXT,
                test_date TEXT,
                notes_mol TEXT,
                FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_mol_patient_id ON Molecular(patient_id);"
        )

        # FollowUp table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS FollowUp (
                patient_id INTEGER PRIMARY KEY,
                last_visit_date TEXT,
                status TEXT,
                death_date TEXT,
                relapse INTEGER,
                relapse_date TEXT,
                relapse_site TEXT,
                os_months_optional REAL,
                dfs_months_optional REAL,
                notes_fu TEXT,
                FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
            );
            """
        )

        # Mapping tables for staging
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS map_lung_v9 (
                t TEXT,
                n TEXT,
                m TEXT,
                stage TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS map_eso_v9_scc (
                t TEXT,
                n TEXT,
                m TEXT,
                grade TEXT,
                location TEXT,
                stage TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS map_eso_v9_ad (
                t TEXT,
                n TEXT,
                m TEXT,
                grade TEXT,
                location TEXT,
                stage TEXT
            );
            """
        )

        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------ Patient operations ------------------
    def insert_patient(self, data: Dict[str, Any]) -> int:
        """Insert a new patient and return its generated ID.

        Args:
            data: dictionary of column names to values. Missing columns will
                default to NULL in SQLite.  hospital_id, cancer_type, and sex
                should be provided.

        Returns:
            The newly assigned patient_id.
        """
        columns = ",".join(data.keys())
        placeholders = ":" + ",:".join(data.keys())
        sql = f"INSERT INTO Patient ({columns}) VALUES ({placeholders})"
        cur = self.conn.cursor()
        cur.execute(sql, data)
        self.conn.commit()
        return cur.lastrowid

    def update_patient(self, patient_id: int, data: Dict[str, Any]) -> None:
        """Update patient record with given fields."""
        set_clause = ",".join([f"{k} = :{k}" for k in data.keys()])
        sql = f"UPDATE Patient SET {set_clause} WHERE patient_id = :patient_id"
        params = {**data, "patient_id": patient_id}
        self.conn.execute(sql, params)
        self.conn.commit()

    def get_patient_by_id(self, patient_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM Patient WHERE patient_id=?", (patient_id,))
        return cur.fetchone()

    def get_patient_by_hospital_id(self, hospital_id: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM Patient WHERE hospital_id=?", (hospital_id,))
        return cur.fetchone()

    def delete_patient(self, patient_id: int) -> None:
        """Delete a patient record and cascade delete all associated records.

        Args:
            patient_id: The primary key of the patient to remove.

        Note:
            This operation relies on SQLite's ON DELETE CASCADE behavior to
            automatically remove related surgeries, pathologies, molecular and
            follow‑up records.
        """
        self.conn.execute("DELETE FROM Patient WHERE patient_id=?", (patient_id,))
        self.conn.commit()

    def search_patients(self, query: str) -> List[sqlite3.Row]:
        """Search patients by partial hospital_id or patient_id (string)."""
        q = f"%{query}%"
        cur = self.conn.execute(
            "SELECT * FROM Patient WHERE hospital_id LIKE ? OR CAST(patient_id AS TEXT) LIKE ? ORDER BY patient_id", (q, q)
        )
        return cur.fetchall()

    # ------------------ Surgery operations ------------------
    def insert_surgery(self, patient_id: int, data: Dict[str, Any]) -> int:
        data = {**data, "patient_id": patient_id}
        columns = ",".join(data.keys())
        placeholders = ":" + ",:".join(data.keys())
        sql = f"INSERT INTO Surgery ({columns}) VALUES ({placeholders})"
        cur = self.conn.cursor()
        cur.execute(sql, data)
        self.conn.commit()
        return cur.lastrowid

    def update_surgery(self, surgery_id: int, data: Dict[str, Any]) -> None:
        set_clause = ",".join([f"{k} = :{k}" for k in data.keys()])
        params = {**data, "surgery_id": surgery_id}
        sql = f"UPDATE Surgery SET {set_clause} WHERE surgery_id = :surgery_id"
        self.conn.execute(sql, params)
        self.conn.commit()

    def get_surgeries_by_patient(self, patient_id: int) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM Surgery WHERE patient_id=? ORDER BY surgery_date6 DESC", (patient_id,)
        )
        return cur.fetchall()

    def delete_surgery(self, surgery_id: int) -> None:
        self.conn.execute("DELETE FROM Surgery WHERE surgery_id=?", (surgery_id,))
        self.conn.commit()

    # ------------------ Pathology operations ------------------
    def insert_pathology(self, patient_id: int, data: Dict[str, Any]) -> int:
        data = {**data, "patient_id": patient_id}
        columns = ",".join(data.keys())
        placeholders = ":" + ",:".join(data.keys())
        cur = self.conn.cursor()
        cur.execute(f"INSERT INTO Pathology ({columns}) VALUES ({placeholders})", data)
        self.conn.commit()
        return cur.lastrowid

    def update_pathology(self, path_id: int, data: Dict[str, Any]) -> None:
        set_clause = ",".join([f"{k} = :{k}" for k in data.keys()])
        params = {**data, "path_id": path_id}
        sql = f"UPDATE Pathology SET {set_clause} WHERE path_id = :path_id"
        self.conn.execute(sql, params)
        self.conn.commit()

    def get_pathologies_by_patient(self, patient_id: int) -> List[sqlite3.Row]:
        """
        Return all pathology records for a patient ordered by path_id descending.  Previously
        this ordered by report_date, but pathology_no replaces report_date so ordering by
        autoincrementing ID makes more sense.
        """
        cur = self.conn.execute(
            "SELECT * FROM Pathology WHERE patient_id=? ORDER BY path_id DESC", (patient_id,)
        )
        return cur.fetchall()

    def delete_pathology(self, path_id: int) -> None:
        self.conn.execute("DELETE FROM Pathology WHERE path_id=?", (path_id,))
        self.conn.commit()

    # ------------------ Molecular operations ------------------
    def insert_molecular(self, patient_id: int, data: Dict[str, Any]) -> int:
        data = {**data, "patient_id": patient_id}
        columns = ",".join(data.keys())
        placeholders = ":" + ",:".join(data.keys())
        cur = self.conn.cursor()
        cur.execute(f"INSERT INTO Molecular ({columns}) VALUES ({placeholders})", data)
        self.conn.commit()
        return cur.lastrowid

    def update_molecular(self, mol_id: int, data: Dict[str, Any]) -> None:
        set_clause = ",".join([f"{k} = :{k}" for k in data.keys()])
        params = {**data, "mol_id": mol_id}
        sql = f"UPDATE Molecular SET {set_clause} WHERE mol_id = :mol_id"
        self.conn.execute(sql, params)
        self.conn.commit()

    def get_molecular_by_patient(self, patient_id: int) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM Molecular WHERE patient_id=? ORDER BY test_date DESC", (patient_id,)
        )
        return cur.fetchall()

    def delete_molecular(self, mol_id: int) -> None:
        self.conn.execute("DELETE FROM Molecular WHERE mol_id=?", (mol_id,))
        self.conn.commit()

    # ------------------ Follow-up operations ------------------
    def insert_or_update_followup(self, patient_id: int, data: Dict[str, Any]) -> None:
        """Insert a followup if not exists, otherwise update existing record."""
        cur = self.conn.execute(
            "SELECT patient_id FROM FollowUp WHERE patient_id=?", (patient_id,)
        )
        exists = cur.fetchone() is not None
        if exists:
            self.update_followup(patient_id, data)
        else:
            data_with_id = {**data, "patient_id": patient_id}
            columns = ",".join(data_with_id.keys())
            placeholders = ":" + ",:".join(data_with_id.keys())
            self.conn.execute(
                f"INSERT INTO FollowUp ({columns}) VALUES ({placeholders})", data_with_id
            )
            self.conn.commit()

    def update_followup(self, patient_id: int, data: Dict[str, Any]) -> None:
        set_clause = ",".join([f"{k} = :{k}" for k in data.keys()])
        params = {**data, "patient_id": patient_id}
        self.conn.execute(
            f"UPDATE FollowUp SET {set_clause} WHERE patient_id = :patient_id", params
        )
        self.conn.commit()

    def get_followup(self, patient_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM FollowUp WHERE patient_id=?", (patient_id,)
        )
        return cur.fetchone()

    # ------------------ General operations ------------------
    def export_table(self, table_name: str) -> List[sqlite3.Row]:
        """Return all rows for the given table for export purposes."""
        cur = self.conn.execute(f"SELECT * FROM {table_name}")
        return cur.fetchall()

    def list_tables(self) -> List[str]:
        """Return list of table names in current database (excluding sqlite internal)."""
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row[0] for row in cur.fetchall()]

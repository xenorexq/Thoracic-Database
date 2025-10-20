"""
Functions for staging lookup based on AJCC version 9 mapping tables.

These helper functions abstract the logic of querying the map tables for lung
and esophageal cancers.  If the tables are empty or a match is not found,
``None`` is returned.  A convenience function is provided to load mapping
data from CSV files packaged alongside the application.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from db.models import Database


def get_lung_stage(db: Database, t: str, n: str, m: str) -> Optional[str]:
    """Lookup stage in lung mapping table.

    Args:
        db: instance of Database.
        t, n, m: TNM strings.
    Returns:
        Stage string or None if not found.
    """
    cur = db.conn.execute(
        "SELECT stage FROM map_lung_v9 WHERE t=? AND n=? AND m=? LIMIT 1",
        (t, n, m),
    )
    row = cur.fetchone()
    return row["stage"] if row else None


def get_eso_stage(db: Database, t: str, n: str, m: str, histology: str, grade: str, location: str) -> Optional[str]:
    """Lookup stage in esophageal mapping tables.

    histology: 'SCC' or 'AD'.  grade and location may be empty strings.
    """
    table = "map_eso_v9_scc" if histology == "SCC" else "map_eso_v9_ad"
    cur = db.conn.execute(
        f"SELECT stage FROM {table} WHERE t=? AND n=? AND m=? AND grade=? AND location=? LIMIT 1",
        (t, n, m, grade or '', location or ''),
    )
    row = cur.fetchone()
    return row["stage"] if row else None


def load_mapping_from_csv(db: Database, csv_dir: Path) -> None:
    """Load mapping tables from CSV files, replacing existing entries.

    This function looks for the following files in ``csv_dir``: ``map_lung_v9.csv``,
    ``map_eso_v9_scc.csv``, and ``map_eso_v9_ad.csv``.  Each file must have
    column headers matching the schema of the corresponding table.  Existing
    records are deleted before insertion.
    """
    mappings = {
        "map_lung_v9": csv_dir / "map_lung_v9.csv",
        "map_eso_v9_scc": csv_dir / "map_eso_v9_scc.csv",
        "map_eso_v9_ad": csv_dir / "map_eso_v9_ad.csv",
    }
    for table, path in mappings.items():
        if not path.exists():
            continue
        # Remove existing rows
        db.conn.execute(f"DELETE FROM {table}")
        with path.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
        # Build placeholders and columns
        if rows:
            columns = rows[0].keys()
            col_list = ",".join(columns)
            placeholders = ",".join([f":{col}" for col in columns])
            db.conn.executemany(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                rows,
            )
    db.conn.commit()

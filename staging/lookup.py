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


def _fallback_lung_stage(t: str, n: str, m: str) -> Optional[str]:
    """粗略推断肺癌临床分期的备选算法。

    当映射表为空或找不到匹配项时，根据 T、N、M 的组合给出简化分期。
    此函数不保证完全符合 AJCC 标准，仅用于内置缺省分期。
    """
    # 若有远处转移（M 非 0），直接归为 IV 期
    if m and m != "0":
        return "IV"
    # 依据 N 分级
    # N 分级带字母时，取数字部分进行比较
    n_clean = n.lower() if isinstance(n, str) else ""
    # N2 或 N3 -> III
    if n_clean in {"2", "2a", "2b", "3"}:
        return "III"
    # N1 -> II
    if n_clean in {"1"}:
        return "II"
    # N0 -> 按 T 分期
    t_clean = t.lower() if isinstance(t, str) else ""
    if t_clean in {"1", "1a", "1b", "1c"}:
        return "I"
    if t_clean in {"2", "2a", "2b"}:
        return "II"
    if t_clean in {"3", "4"}:
        return "III"
    # 无法判断
    return None


def get_lung_stage(db: Database, t: str, n: str, m: str) -> Optional[str]:
    """
    Lookup stage in the lung mapping table.

    If a matching record is found in ``map_lung_v9`` it is returned;
    otherwise ``None`` is returned.  No fallback or default stage
    calculation is performed here to avoid误导性返回值。

    Args:
        db: Database instance
        t, n, m: normalised TNM values (case sensitive as stored in the table)

    Returns:
        The stage string if found, otherwise ``None``.
    """
    cur = db.conn.execute(
        "SELECT stage FROM map_lung_v9 WHERE t=? AND n=? AND m=? LIMIT 1",
        (t, n, m),
    )
    row = cur.fetchone()
    return row["stage"] if row else None


def _fallback_eso_stage(t: str, n: str, m: str) -> Optional[str]:
    """简易食管癌分期备选算法。

    根据简化的 TNM 组合推断 I–IV 期，仅在缺乏映射表时使用。
    """
    if m and m != "0":
        return "IV"
    n_clean = n.lower() if isinstance(n, str) else ""
    if n_clean in {"3", "2"}:
        return "III"
    if n_clean in {"1"}:
        return "II"
    t_clean = t.lower() if isinstance(t, str) else ""
    if t_clean in {"is", "1"}:
        return "I"
    if t_clean in {"2"}:
        return "II"
    if t_clean in {"3", "4", "4a", "4b"}:
        return "III"
    return None


def get_eso_stage(db: Database, t: str, n: str, m: str, histology: str, grade: str, location: str) -> Optional[str]:
    """
    Lookup stage in the esophageal mapping tables.

    ``histology`` must be either ``'SCC'`` or ``'AD'``.  The function
    attempts to find a matching record in the appropriate table
    ``map_eso_v9_scc`` or ``map_eso_v9_ad``.  ``grade`` and ``location``
    may be empty strings.  If no record is found, ``None`` is returned.

    Args:
        db: Database instance
        t, n, m: normalised TNM values
        histology: 'SCC' or 'AD'
        grade, location: additional stratification columns (may be empty)

    Returns:
        The stage string if a match is found, otherwise ``None``.
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

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

from typing import Iterable, List, Optional, Callable

from db.models import Database
# 引入并行处理工具
from export.parallel import parallel_fetch_tables, parallel_write_csv_files, ExportProgress

# 引入日期格式化函数以统一导出中的日期格式

from utils.validators import format_date6, format_birth_ym4, format_birth_ym6

# 引入分期查询函数用于导出时补充临床分期

# 已删除临床分期映射功能，不再导入 staging.lookup 中的分期函数

# Fields that should not appear in exported files.  These columns either come from

# deprecated UI elements (e.g. vendor_lab) or have been removed from the

# current version of the application (e.g. lymph node totals).  We also

# remove the internal numeric patient_id in favour of hospital_id for unique

# identification in exported data.

# 排除导出字段列表：新增 event_code 用于隐藏随访事件的内部编号
EXCLUDE_FIELDS = {"vendor_lab", "ln_total", "ln_positive", "patient_id", "event_code"}

# 日期字段映射。需要统一导出格式的列名列表。

# birth_ym4 将在格式化时保持为 yyyymm；其他列将格式化为 yyyymmdd。

DATE_FIELDS_8 = {

    "surgery_date6",

    "pathology_date",

    "report_date",

    "test_date",

    "last_visit_date",

    "death_date",

    "relapse_date",

    "nac_date",

    "adj_date",

    "event_date",

}

# ��Щ "����" �ֶβ�������淢�£����ڸ�ʽ��ȴȷ��Ϊ 6 λ������(yymmdd)�����ڴ˴�ͳһת���� yyyy-mm-dd ��ʽ��

DATE_LIKE_CYCLE_FIELDS = {

    "nac_chemo_cycles",

    "adj_chemo_cycles",

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

    if col in DATE_LIKE_CYCLE_FIELDS:

        if len(s) == 6 and s.isdigit():

            formatted = format_date6(s)

            return formatted or s

        return s

    return val

def _format_row_dates(row_dict: dict) -> dict:

    """Apply date formatting to all columns in a row."""

    new_row = {}

    for k, v in row_dict.items():

        if k in EXCLUDE_FIELDS:

            continue

        new_row[k] = _format_value(k, v)

    return new_row

# 移除 `_annotate_stage` 函数。临床分期映射功能已取消，不再补充分期字段。

def _clean_row(row_dict: dict) -> dict:

    """Remove unwanted fields and format date values before export."""

    formatted = _format_row_dates(row_dict)

    return {k: v for k, v in formatted.items() if k not in EXCLUDE_FIELDS}

def _reorder_pathology(row_dict: dict) -> dict:

    """Reorder pathology row so that airway_spread appears before pleural_invasion."""

    if "airway_spread" in row_dict and "pleural_invasion" in row_dict:

        airway_val = row_dict.pop("airway_spread")

        new_dict = {}

        for k, v in row_dict.items():

            if k == "pleural_invasion":

                new_dict["airway_spread"] = airway_val

            new_dict[k] = v

        return new_dict

    return row_dict

def _annotate_sequence(rows: List[dict], table_name: str) -> List[dict]:
    """Add a sequence number (1, 2, 3...) for each patient's records sorted by date.
    
    Applicable to Surgery, Pathology, Molecular, and FollowUpEvent tables.
    """
    if table_name not in ["Surgery", "Pathology", "Molecular", "FollowUpEvent"]:
        return rows
    
    # Sort all rows by date to ensure consistent numbering
    date_field_map = {
        "Surgery": "surgery_date6",
        "Pathology": "pathology_date",
        "Molecular": "test_date",
        "FollowUpEvent": "event_date"
    }
    date_col = date_field_map.get(table_name)
    if not date_col:
        return rows

    # Group rows by patient_id
    grouped = {}
    for row in rows:
        pid = row.get("patient_id")
        if pid not in grouped:
            grouped[pid] = []
        grouped[pid].append(row)
    
    annotated_rows = []
    # For each patient, sort by date ascending and assign sequence
    for pid in grouped:
        patient_rows = grouped[pid]
        # Sort by date ascending
        patient_rows.sort(key=lambda x: str(x.get(date_col) or ""))
        
        for i, row in enumerate(patient_rows, 1):
            # Create a new dict to avoid modifying original if shared
            new_row = row.copy()
            new_row["Seq"] = i
            annotated_rows.append(new_row)
            
    return annotated_rows


def _write_csv(path: Path, rows: Iterable[dict], table_name: str) -> None:

    """Write a list of dictionaries to a CSV file after cleaning and formatting."""

    try:

        # Convert to list
        rows_list_raw = [dict(row) if not isinstance(row, dict) else row for row in rows]
        
        # Add sequence numbers if applicable
        if table_name in ["Surgery", "Pathology", "Molecular", "FollowUpEvent"]:
            rows_list_raw = _annotate_sequence(rows_list_raw, table_name)

        # Clean and format
        rows_list = []

        for row in rows_list_raw:

            try:

                row_dict = dict(row)

                cleaned = _clean_row(row_dict)

                if table_name == "Pathology":

                    cleaned = _reorder_pathology(cleaned)

                rows_list.append(cleaned)

            except Exception as e:

                print(f"Warning: Failed to process row in {table_name}: {e}")

                continue

        if not rows_list:

            # Nothing to write

            path.parent.mkdir(parents=True, exist_ok=True)

            with path.open("w", newline="", encoding="utf-8") as f:

                pass

            return

        # 确保目录存在

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as f:
            
            # Ensure 'Seq' is the first column if present
            header = list(rows_list[0].keys())
            if "Seq" in header:
                header.remove("Seq")
                header = ["Seq"] + header

            writer = csv.DictWriter(f, fieldnames=header)

            writer.writeheader()

            for row in rows_list:

                writer.writerow(row)

    except PermissionError as e:

        raise PermissionError(f"无法写入文件 {path}，请检查文件权限或文件是否被占用") from e

    except Exception as e:

        raise Exception(f"导出CSV文件失败: {str(e)}") from e

def export_patient_to_csv(
    db: Database, 
    patient_id: int, 
    dir_path: Path, 
    prefix: str = None,
    progress_callback: Optional[Callable[[float], None]] = None
) -> List[Path]:
    """Export data for a single patient to CSV files (one file per table).

    Args:
        db: Database instance.
        patient_id: Primary key of the patient to export.
        dir_path: Directory where CSV files will be written.
        prefix: Optional prefix for file names (e.g. ``patient123``).
        progress_callback: 进度回调函数，接收 0-100 的进度值

    Returns:
        List of file paths created.
    """
    try:
        files: List[Path] = []
        dir_path.mkdir(parents=True, exist_ok=True)

        if prefix is None:
            prefix = f"patient{patient_id}"

        tables = ["Patient", "Surgery", "Pathology", "Molecular", "FollowUpEvent"]
        
        if progress_callback:
            progress_callback(5)
        
        # 使用多线程并行获取所有表的数据
        fetch_progress = ExportProgress(len(tables))
        if progress_callback:
            def fetch_progress_callback(p):
                # 数据获取阶段占 50% 进度
                progress_callback(5 + p * 0.5)
            fetch_progress.set_callback(fetch_progress_callback)
        
        table_data = parallel_fetch_tables(
            db, tables, patient_id=patient_id,
            max_workers=min(4, len(tables)),
            progress_tracker=fetch_progress
        )
        
        # 获取患者的 hospital_id
        patient_rows = table_data.get("Patient", [])
        if not patient_rows:
            raise ValueError(f"Patient with ID {patient_id} not found")
        
        # 如果hospital_id为空，使用patient_id作为备用标识
        hospital_id = patient_rows[0].get("hospital_id") or f"PID_{patient_id}"
        
        # 准备写入任务
        file_tasks = []
        for table in tables:
            if table == "Patient":
                rows = patient_rows
            else:
                # Attach hospital_id to each row
                rows = table_data.get(table, [])
                if hospital_id is not None:
                    for rdict in rows:
                        rdict["hospital_id"] = hospital_id
            
            file_path = dir_path / f"{prefix}_{table}.csv"
            file_tasks.append((file_path, rows, table))
        
        # 使用多线程并行写入 CSV 文件
        write_progress = ExportProgress(len(file_tasks))
        if progress_callback:
            def write_progress_callback(p):
                # 文件写入阶段占 45% 进度
                progress_callback(55 + p * 0.45)
            write_progress.set_callback(write_progress_callback)
        
        files = parallel_write_csv_files(
            file_tasks, _write_csv,
            max_workers=min(4, len(file_tasks)),
            progress_tracker=write_progress
        )
        
        if progress_callback:
            progress_callback(100)

        return files

    except Exception as e:
        raise Exception(f"导出患者CSV文件失败: {str(e)}") from e

def export_all_to_csv(
    db: Database, 
    dir_path: Path,
    progress_callback: Optional[Callable[[float], None]] = None
) -> List[Path]:
    """Export entire database to CSV files.
    
    Args:
        db: 数据库实例
        dir_path: 输出目录路径
        progress_callback: 进度回调函数，接收 0-100 的进度值

    Returns:
        成功创建的文件路径列表
    """
    try:
        files: List[Path] = []
        dir_path.mkdir(parents=True, exist_ok=True)
        
        tables = ["Patient", "Surgery", "Pathology", "Molecular", "FollowUpEvent"]
        
        if progress_callback:
            progress_callback(5)
        
        # 使用多线程并行获取所有表的数据
        fetch_progress = ExportProgress(len(tables))
        if progress_callback:
            def fetch_progress_callback(p):
                # 数据获取阶段占 50% 进度
                progress_callback(5 + p * 0.5)
            fetch_progress.set_callback(fetch_progress_callback)
        
        table_data = parallel_fetch_tables(
            db, tables, patient_id=None,
            max_workers=min(4, len(tables)),
            progress_tracker=fetch_progress
        )
        
        # Precompute mapping from patient_id to hospital_id
        patient_rows = table_data.get("Patient", [])
        pat_map = {}
        for rdict in patient_rows:
            pat_map[rdict.get("patient_id")] = rdict.get("hospital_id")
        
        # 准备写入任务
        file_tasks = []
        for table in tables:
            rows_dicts: List[dict] = table_data.get(table, [])
            
            # Attach hospital_id for non-Patient tables
            if table != "Patient":
                for rdict in rows_dicts:
                    pid = rdict.get("patient_id")
                    if pid in pat_map:
                        rdict["hospital_id"] = pat_map[pid]
            
            file_path = dir_path / f"{table}.csv"
            file_tasks.append((file_path, rows_dicts, table))
        
        # 使用多线程并行写入 CSV 文件
        write_progress = ExportProgress(len(file_tasks))
        if progress_callback:
            def write_progress_callback(p):
                # 文件写入阶段占 45% 进度
                progress_callback(55 + p * 0.45)
            write_progress.set_callback(write_progress_callback)
        
        files = parallel_write_csv_files(
            file_tasks, _write_csv,
            max_workers=min(4, len(file_tasks)),
            progress_tracker=write_progress
        )
        
        if progress_callback:
            progress_callback(100)
        
        return files

    except Exception as e:
        raise Exception(f"导出CSV文件失败: {str(e)}") from e


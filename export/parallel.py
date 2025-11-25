"""
并行导出工具模块

提供多线程/多进程支持以加速大批量数据导出。
使用 concurrent.futures 实现线程池，适用于 I/O 密集型操作。
"""

from __future__ import annotations

import concurrent.futures
from typing import List, Dict, Callable, Any, Optional, Tuple
from pathlib import Path

from db.models import Database
from utils.logger import log_error, log_warning, log_debug


class ExportProgress:
    """导出进度跟踪器"""
    
    def __init__(self, total_tasks: int):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.callback: Optional[Callable[[float], None]] = None
    
    def set_callback(self, callback: Callable[[float], None]):
        """设置进度回调函数，接收 0-100 的进度值"""
        self.callback = callback
    
    def update(self, increment: int = 1):
        """更新进度"""
        self.completed_tasks += increment
        if self.callback and self.total_tasks > 0:
            progress = (self.completed_tasks / self.total_tasks) * 100
            self.callback(progress)
        elif self.callback:
            # 如果total_tasks为0，直接报告100%
            self.callback(100.0)


def fetch_table_data(db: Database, table: str, patient_id: Optional[int] = None) -> Tuple[str, List[Dict]]:
    """
    从数据库获取表数据（线程安全 - 使用独立连接）
    
    Args:
        db: 数据库实例（仅用于获取db_path）
        table: 表名
        patient_id: 患者 ID（None 表示获取全部）
    
    Returns:
        (表名, 数据行列表)
    """
    import sqlite3
    
    # 为线程安全，每个线程使用独立的连接
    # 不需要check_same_thread=False，因为每个线程都创建自己的连接
    conn = None
    try:
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        
        if patient_id:
            # 获取单个患者数据
            if table == "Patient":
                row = conn.execute("SELECT * FROM Patient WHERE patient_id=?", (patient_id,)).fetchone()
                rows = [dict(row)] if row else []
            elif table == "Surgery":
                cursor = conn.execute("SELECT * FROM Surgery WHERE patient_id=? ORDER BY surgery_date6 DESC", (patient_id,))
                rows = [dict(r) for r in cursor.fetchall()]
            elif table == "Pathology":
                cursor = conn.execute("SELECT * FROM Pathology WHERE patient_id=? ORDER BY path_id DESC", (patient_id,))
                rows = [dict(r) for r in cursor.fetchall()]
            elif table == "Molecular":
                cursor = conn.execute("SELECT * FROM Molecular WHERE patient_id=? ORDER BY test_date DESC", (patient_id,))
                rows = [dict(r) for r in cursor.fetchall()]
            elif table == "FollowUpEvent":
                cursor = conn.execute("SELECT * FROM FollowUpEvent WHERE patient_id=? ORDER BY event_date DESC", (patient_id,))
                rows = [dict(r) for r in cursor.fetchall()]
            else:
                rows = []
        else:
            # 获取全部数据
            cursor = conn.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cursor.fetchall()]
        
        return (table, rows)
    except Exception as e:
        log_error(f"获取表 {table} 数据失败: {e}", e)
        return (table, [])
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def parallel_fetch_tables(
    db: Database,
    tables: List[str],
    patient_id: Optional[int] = None,
    max_workers: int = 4,
    progress_tracker: Optional[ExportProgress] = None
) -> Dict[str, List[Dict]]:
    """
    并行获取多个表的数据
    
    Args:
        db: 数据库实例
        tables: 表名列表
        patient_id: 患者 ID（None 表示导出全库）
        max_workers: 最大线程数
        progress_tracker: 进度跟踪器
    
    Returns:
        {表名: 数据行列表} 的字典
    """
    result = {}
    
    # 对于小数据量，直接串行处理更快
    if len(tables) <= 2:
        for table in tables:
            table_name, rows = fetch_table_data(db, table, patient_id)
            result[table_name] = rows
            if progress_tracker:
                progress_tracker.update()
        return result
    
    # 使用线程池并行获取
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_table = {
            executor.submit(fetch_table_data, db, table, patient_id): table
            for table in tables
        }
        
        # 等待完成并收集结果
        for future in concurrent.futures.as_completed(future_to_table):
            try:
                table_name, rows = future.result()
                result[table_name] = rows
                if progress_tracker:
                    progress_tracker.update()
            except Exception as e:
                table = future_to_table[future]
                log_error(f"处理表 {table} 失败: {e}", e)
                result[table] = []
    
    return result


def parallel_write_csv_files(
    file_tasks: List[Tuple[Path, List[Dict], str]],
    write_func: Callable[[Path, List[Dict], str], None],
    max_workers: int = 4,
    progress_tracker: Optional[ExportProgress] = None
) -> List[Path]:
    """
    并行写入多个 CSV 文件
    
    Args:
        file_tasks: [(文件路径, 数据行, 表名), ...] 列表
        write_func: CSV 写入函数
        max_workers: 最大线程数
        progress_tracker: 进度跟踪器
    
    Returns:
        成功写入的文件路径列表
    """
    written_files = []
    
    # 对于小批量文件，串行写入更快
    if len(file_tasks) <= 2:
        for path, rows, table_name in file_tasks:
            try:
                write_func(path, rows, table_name)
                written_files.append(path)
                if progress_tracker:
                    progress_tracker.update()
            except Exception as e:
                log_error(f"写入文件 {path} 失败: {e}", e)
        return written_files
    
    # 使用线程池并行写入
    def write_task(path, rows, table_name):
        write_func(path, rows, table_name)
        return path
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(write_task, path, rows, table_name): path
            for path, rows, table_name in file_tasks
        }
        
        for future in concurrent.futures.as_completed(future_to_path):
            try:
                path = future.result()
                written_files.append(path)
                if progress_tracker:
                    progress_tracker.update()
            except Exception as e:
                failed_path = future_to_path[future]
                log_error(f"写入文件 {failed_path} 失败: {e}", e)
    
    return written_files


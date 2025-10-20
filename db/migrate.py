#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
在线检测并添加缺失的字段
"""

import sqlite3
from pathlib import Path

def get_table_columns(conn, table_name):
    """获取表的所有列名"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}

def add_column_if_not_exists(conn, table_name, column_name, column_type, default=None):
    """如果列不存在则添加"""
    existing_columns = get_table_columns(conn, table_name)
    if column_name not in existing_columns:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_clause}"
        print(f"添加字段: {table_name}.{column_name}")
        conn.execute(sql)
        conn.commit()
        return True
    return False

def migrate_database(db_path):
    """执行数据库迁移"""
    print(f"开始迁移数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    changes_made = False
    
    # Patient表新增字段
    if add_column_if_not_exists(conn, "Patient", "eso_from_incisors_cm", "REAL"):
        changes_made = True

    # Patient表新增: 家族恶性肿瘤史
    if add_column_if_not_exists(conn, "Patient", "family_history", "INTEGER", default=0):
        changes_made = True
    
    # Pathology表修改
    if add_column_if_not_exists(conn, "Pathology", "airway_spread", "INTEGER"):
        changes_made = True
    if add_column_if_not_exists(conn, "Pathology", "pathology_no", "TEXT"):
        changes_made = True
    
    # Molecular表新增字段
    if add_column_if_not_exists(conn, "Molecular", "ctc_count", "INTEGER"):
        changes_made = True
    if add_column_if_not_exists(conn, "Molecular", "methylation_result", "TEXT"):
        changes_made = True
    
    conn.close()
    
    if changes_made:
        print("✓ 迁移完成")
    else:
        print("- 无需迁移")
    
    return changes_made

if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "thoracic.db"
    migrate_database(db_path)

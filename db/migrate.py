#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
在线检测并添加缺失的字段
"""

import random
import sqlite3
import string
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


def generate_unique_event_code(conn, patient_id: int, length: int = 6) -> str:
    """Ϊ指定患者生成唯一的随访事件编号"""
    digits = string.digits
    while True:
        candidate = "".join(random.choices(digits, k=length))
        exists = conn.execute(
            "SELECT 1 FROM FollowUpEvent WHERE patient_id=? AND event_code=?",
            (patient_id, candidate),
        ).fetchone()
        if not exists:
            return candidate

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
    if add_column_if_not_exists(conn, "Patient", "diabetes_history", "INTEGER", default=0):
        changes_made = True
    if add_column_if_not_exists(conn, "Patient", "family_history", "INTEGER", default=0):
        changes_made = True

    # Patient表新增: 新辅助及辅助放疗
    # 新增新辅助放疗和辅助放疗字段，默认值为0
    if add_column_if_not_exists(conn, "Patient", "nac_radiation", "INTEGER", default=0):
        changes_made = True
    if add_column_if_not_exists(conn, "Patient", "adj_radiation", "INTEGER", default=0):
        changes_made = True
    
    # Patient表新增: 新辅助和辅助治疗日期 (v2.12)
    if add_column_if_not_exists(conn, "Patient", "nac_date", "TEXT"):
        changes_made = True
    if add_column_if_not_exists(conn, "Patient", "adj_date", "TEXT"):
        changes_made = True
    
    # Patient表新增: 抗血管治疗 (v2.13)
    if add_column_if_not_exists(conn, "Patient", "nac_antiangio", "INTEGER", default=0):
        changes_made = True
    if add_column_if_not_exists(conn, "Patient", "nac_antiangio_cycles", "INTEGER"):
        changes_made = True
    if add_column_if_not_exists(conn, "Patient", "adj_antiangio", "INTEGER", default=0):
        changes_made = True
    if add_column_if_not_exists(conn, "Patient", "adj_antiangio_cycles", "INTEGER"):
        changes_made = True
    
    # Pathology表修改
    if add_column_if_not_exists(conn, "Pathology", "airway_spread", "INTEGER"):
        changes_made = True
    if add_column_if_not_exists(conn, "Pathology", "pathology_no", "TEXT"):
        changes_made = True
    # 新增: Pathology表添加肺腺癌主要亚型字段
    if add_column_if_not_exists(conn, "Pathology", "aden_subtype", "TEXT"):
        changes_made = True
    # 新增: Pathology表添加病理日期字段 (v2.13)
    if add_column_if_not_exists(conn, "Pathology", "pathology_date", "TEXT"):
        changes_made = True
    
    # Molecular表新增字段
    if add_column_if_not_exists(conn, "Molecular", "ctc_count", "INTEGER"):
        changes_made = True
    if add_column_if_not_exists(conn, "Molecular", "methylation_result", "TEXT"):
        changes_made = True
    
    # Surgery表新增字段: 左右打勾框
    if add_column_if_not_exists(conn, "Surgery", "left_side", "INTEGER", default=0):
        changes_made = True
    if add_column_if_not_exists(conn, "Surgery", "right_side", "INTEGER", default=0):
        changes_made = True
    
    # 创建FollowUpEvent表（v2.1新增）
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='FollowUpEvent'")
    if not cursor.fetchone():
        print("创建新表: FollowUpEvent")
        conn.execute("""
            CREATE TABLE FollowUpEvent (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                event_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_details TEXT,
                event_code TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX idx_followup_event_patient_id ON FollowUpEvent(patient_id)")
        conn.execute("CREATE INDEX idx_followup_event_date ON FollowUpEvent(event_date DESC)")
        conn.execute("CREATE UNIQUE INDEX idx_followup_event_code ON FollowUpEvent(patient_id, event_code)")
        conn.commit()
        changes_made = True
    else:
        if add_column_if_not_exists(conn, "FollowUpEvent", "event_code", "TEXT"):
            changes_made = True

    followup_columns = get_table_columns(conn, "FollowUpEvent")
    if "event_code" in followup_columns:
        cursor = conn.execute("SELECT event_id, patient_id FROM FollowUpEvent WHERE event_code IS NULL OR event_code = ''")
        rows = cursor.fetchall()
        if rows:
            print("为 FollowUpEvent 补全随机编号...")
            for event_id, patient_id in rows:
                code = generate_unique_event_code(conn, patient_id)
                conn.execute("UPDATE FollowUpEvent SET event_code=? WHERE event_id=?", (code, event_id))
            conn.commit()
            changes_made = True
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_followup_event_code ON FollowUpEvent(patient_id, event_code)")
        conn.commit()

    conn.close()
    
    if changes_made:
        print("✓ 迁移完成")
    else:
        print("- 无需迁移")
    
    return changes_made

if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "thoracic.db"
    migrate_database(db_path)

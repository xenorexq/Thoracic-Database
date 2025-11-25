"""
数据库导入预检查模块

在实际导入前分析源数据库文件，检测重复和冲突，提供详细的导入预览信息。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PatientInfo:
    """患者基本信息"""
    hospital_id: str
    cancer_type: Optional[str]
    sex: Optional[str]
    source_db: str  # 来源数据库文件名


@dataclass
class ImportAnalysis:
    """导入分析结果"""
    # 基本统计
    total_patients: int  # 所有源文件的总患者数
    new_patients: int  # 可以导入的新患者数
    duplicate_in_local: int  # 与本地库重复的患者数
    duplicate_in_sources: int  # 源文件之间重复的患者数
    
    # 详细信息
    new_patient_list: List[PatientInfo]  # 新患者列表
    duplicate_local_list: List[PatientInfo]  # 与本地重复的患者列表
    duplicate_source_list: List[Tuple[PatientInfo, PatientInfo]]  # 源文件间重复的患者对
    
    # 关联数据统计（预估）
    estimated_surgeries: int
    estimated_pathologies: int
    estimated_molecular: int
    estimated_followup_events: int
    
    # 文件信息
    source_files: List[str]  # 源文件列表


def check_source_databases(
    source_paths: List[Path],
    local_db_path: Path
) -> ImportAnalysis:
    """
    预检查要导入的数据库文件
    
    Args:
        source_paths: 要导入的数据库文件路径列表
        local_db_path: 本地数据库路径
    
    Returns:
        ImportAnalysis: 详细的分析结果
    """
    # 1. 读取本地数据库的所有 hospital_id
    local_hospital_ids = _get_local_hospital_ids(local_db_path)
    
    # 2. 读取所有源文件的患者信息
    all_source_patients: List[PatientInfo] = []
    source_hospital_id_map: Dict[str, List[PatientInfo]] = {}  # hospital_id -> [PatientInfo]
    
    valid_source_files = []
    
    for source_path in source_paths:
        try:
            patients = _read_patients_from_db(source_path)
            all_source_patients.extend(patients)
            valid_source_files.append(source_path.name)
            
            # 建立映射以检测源文件间的重复
            for patient in patients:
                if patient.hospital_id not in source_hospital_id_map:
                    source_hospital_id_map[patient.hospital_id] = []
                source_hospital_id_map[patient.hospital_id].append(patient)
        except Exception as e:
            print(f"Warning: Failed to read {source_path}: {e}")
            continue
    
    # 3. 分类患者
    new_patients = []
    duplicate_local = []
    duplicate_source_pairs = []
    
    # 检测源文件间的重复
    processed_duplicates = set()
    for hospital_id, patient_list in source_hospital_id_map.items():
        if len(patient_list) > 1:
            # 有重复，只取第一个，其余标记为重复
            new_patients.append(patient_list[0]) if hospital_id not in local_hospital_ids else duplicate_local.append(patient_list[0])
            
            # 记录重复对
            for i in range(len(patient_list) - 1):
                pair_key = f"{patient_list[i].source_db}:{patient_list[i+1].source_db}:{hospital_id}"
                if pair_key not in processed_duplicates:
                    duplicate_source_pairs.append((patient_list[i], patient_list[i+1]))
                    processed_duplicates.add(pair_key)
        else:
            # 无源间重复，检查是否与本地重复
            patient = patient_list[0]
            if hospital_id in local_hospital_ids:
                duplicate_local.append(patient)
            else:
                new_patients.append(patient)
    
    # 4. 统计关联数据（预估）
    estimated_stats = _estimate_related_records(source_paths, new_patients)
    
    # 5. 构建分析结果
    analysis = ImportAnalysis(
        total_patients=len(all_source_patients),
        new_patients=len(new_patients),
        duplicate_in_local=len(duplicate_local),
        duplicate_in_sources=len(duplicate_source_pairs),
        new_patient_list=new_patients,
        duplicate_local_list=duplicate_local,
        duplicate_source_list=duplicate_source_pairs,
        estimated_surgeries=estimated_stats['Surgery'],
        estimated_pathologies=estimated_stats['Pathology'],
        estimated_molecular=estimated_stats['Molecular'],
        estimated_followup_events=estimated_stats['FollowUpEvent'],
        source_files=valid_source_files
    )
    
    return analysis


def _get_local_hospital_ids(db_path: Path) -> Set[str]:
    """获取本地数据库的所有 hospital_id"""
    hospital_ids = set()
    
    if not db_path.exists():
        return hospital_ids
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT hospital_id FROM Patient WHERE hospital_id IS NOT NULL")
        for row in cursor:
            if row[0]:
                hospital_ids.add(row[0])
        conn.close()
    except Exception as e:
        print(f"Warning: Failed to read local database: {e}")
    
    return hospital_ids


def _read_patients_from_db(db_path: Path) -> List[PatientInfo]:
    """从数据库文件读取患者信息"""
    patients = []
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT hospital_id, cancer_type, sex FROM Patient WHERE hospital_id IS NOT NULL"
        )
        
        for row in cursor:
            patient = PatientInfo(
                hospital_id=row['hospital_id'],
                cancer_type=row['cancer_type'],
                sex=row['sex'],
                source_db=db_path.name
            )
            patients.append(patient)
        
        conn.close()
    except Exception as e:
        raise Exception(f"Failed to read patients from {db_path}: {e}")
    
    return patients


def _estimate_related_records(
    source_paths: List[Path],
    new_patients: List[PatientInfo]
) -> Dict[str, int]:
    """预估将要导入的关联记录数量"""
    stats = {
        'Surgery': 0,
        'Pathology': 0,
        'Molecular': 0,
        'FollowUpEvent': 0
    }
    
    # 建立新患者的 hospital_id 集合
    new_hospital_ids = {p.hospital_id for p in new_patients}
    
    for source_path in source_paths:
        try:
            conn = sqlite3.connect(source_path)
            conn.row_factory = sqlite3.Row
            
            # 获取这些新患者在源库中的 patient_id
            placeholders = ','.join('?' * len(new_hospital_ids))
            cursor = conn.execute(
                f"SELECT patient_id FROM Patient WHERE hospital_id IN ({placeholders})",
                list(new_hospital_ids)
            )
            source_patient_ids = [row[0] for row in cursor]
            
            if not source_patient_ids:
                conn.close()
                continue
            
            # 统计各表的记录数
            id_placeholders = ','.join('?' * len(source_patient_ids))
            
            for table in ['Surgery', 'Pathology', 'Molecular']:
                try:
                    cursor = conn.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE patient_id IN ({id_placeholders})",
                        source_patient_ids
                    )
                    count = cursor.fetchone()[0]
                    stats[table] += count
                except:
                    pass
            
            # 随访事件
            try:
                cursor = conn.execute(
                    f"SELECT COUNT(*) FROM FollowUpEvent WHERE patient_id IN ({id_placeholders})",
                    source_patient_ids
                )
                count = cursor.fetchone()[0]
                stats['FollowUpEvent'] += count
            except:
                pass
            
            conn.close()
            
        except Exception as e:
            print(f"Warning: Failed to estimate records from {source_path}: {e}")
            continue
    
    return stats


def format_analysis_report(analysis: ImportAnalysis) -> str:
    """格式化分析报告为可读文本"""
    lines = []
    
    lines.append("=" * 60)
    lines.append("数据库导入预检查报告")
    lines.append("=" * 60)
    lines.append("")
    
    # 源文件信息
    lines.append(f"源文件数量: {len(analysis.source_files)} 个")
    for i, filename in enumerate(analysis.source_files, 1):
        lines.append(f"  {i}. {filename}")
    lines.append("")
    
    # 患者统计
    lines.append("患者数据分析:")
    lines.append(f"  • 源文件总患者数: {analysis.total_patients} 位")
    lines.append(f"  • 可导入的新患者: {analysis.new_patients} 位")
    lines.append(f"  • 与本地库重复: {analysis.duplicate_in_local} 位")
    lines.append(f"  • 源文件间重复: {analysis.duplicate_in_sources} 对")
    lines.append("")
    
    # 关联数据预估
    if analysis.new_patients > 0:
        lines.append("预计导入的关联数据:")
        lines.append(f"  • 手术记录: 约 {analysis.estimated_surgeries} 条")
        lines.append(f"  • 病理记录: 约 {analysis.estimated_pathologies} 条")
        lines.append(f"  • 分子记录: 约 {analysis.estimated_molecular} 条")
        lines.append(f"  • 随访事件: 约 {analysis.estimated_followup_events} 条")
        lines.append("")
    
    # 重复详情
    if analysis.duplicate_in_local > 0:
        lines.append("与本地库重复的患者（将跳过）:")
        for i, patient in enumerate(analysis.duplicate_local_list[:10], 1):  # 最多显示10个
            lines.append(f"  {i}. {patient.hospital_id} ({patient.cancer_type or '未知'}) - 来自 {patient.source_db}")
        if len(analysis.duplicate_local_list) > 10:
            lines.append(f"  ... 还有 {len(analysis.duplicate_local_list) - 10} 位")
        lines.append("")
    
    if analysis.duplicate_in_sources > 0:
        lines.append("源文件间重复的患者（将使用第一次出现的）:")
        for i, (p1, p2) in enumerate(analysis.duplicate_source_list[:10], 1):
            lines.append(f"  {i}. {p1.hospital_id} - 出现在 {p1.source_db} 和 {p2.source_db}")
        if len(analysis.duplicate_source_list) > 10:
            lines.append(f"  ... 还有 {len(analysis.duplicate_source_list) - 10} 对")
        lines.append("")
    
    # 总结
    lines.append("=" * 60)
    if analysis.new_patients > 0:
        lines.append(f"✓ 可以导入 {analysis.new_patients} 位新患者及其关联数据")
    else:
        lines.append("✗ 没有可导入的新患者（所有患者均已存在）")
    lines.append("=" * 60)
    
    return "\n".join(lines)


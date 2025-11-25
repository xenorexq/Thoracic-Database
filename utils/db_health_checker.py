"""
数据库健康检查和修复工具

检测并修复可能导致保存失败的数据库状态问题。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    is_healthy: bool
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]


class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def check_all(self) -> HealthCheckResult:
        """执行完整的健康检查"""
        issues = []
        warnings = []
        suggestions = []
        
        # 1. 检查文件存在性和权限
        file_check = self._check_file_access()
        if not file_check[0]:
            issues.extend(file_check[1])
        
        # 2. 检查数据库完整性
        integrity_check = self._check_integrity()
        if not integrity_check[0]:
            issues.extend(integrity_check[1])
        else:
            warnings.extend(integrity_check[2])
        
        # 3. 检查事务状态
        transaction_check = self._check_transaction_state()
        if not transaction_check[0]:
            issues.extend(transaction_check[1])
            suggestions.extend(transaction_check[2])
        
        # 4. 检查外键约束
        fk_check = self._check_foreign_keys()
        if not fk_check[0]:
            warnings.extend(fk_check[1])
            suggestions.extend(fk_check[2])
        
        # 5. 检查表结构
        schema_check = self._check_schema()
        if not schema_check[0]:
            warnings.extend(schema_check[1])
        
        # 6. 检查数据一致性
        consistency_check = self._check_data_consistency()
        if not consistency_check[0]:
            warnings.extend(consistency_check[1])
            suggestions.extend(consistency_check[2])
        
        is_healthy = len(issues) == 0
        
        return HealthCheckResult(
            is_healthy=is_healthy,
            issues=issues,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _check_file_access(self) -> Tuple[bool, List[str]]:
        """检查文件访问权限"""
        issues = []
        
        if not self.db_path.exists():
            issues.append("数据库文件不存在")
            return False, issues
        
        try:
            # 尝试以读写模式打开
            with open(self.db_path, 'r+b') as f:
                f.seek(0)
                f.read(100)  # 尝试读取文件头
        except PermissionError:
            issues.append("数据库文件没有读写权限")
            return False, issues
        except Exception as e:
            issues.append(f"无法访问数据库文件: {e}")
            return False, issues
        
        return True, []
    
    def _check_integrity(self) -> Tuple[bool, List[str], List[str]]:
        """检查数据库完整性"""
        issues = []
        warnings = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result and result[0] != "ok":
                issues.append(f"数据库完整性检查失败: {result[0]}")
                return False, issues, warnings
            
            # 检查快速检查模式
            cursor = conn.execute("PRAGMA quick_check")
            result = cursor.fetchone()
            
            if result and result[0] != "ok":
                warnings.append(f"数据库快速检查发现问题: {result[0]}")
            
            conn.close()
            return True, issues, warnings
            
        except Exception as e:
            issues.append(f"无法执行完整性检查: {e}")
            return False, issues, warnings
    
    def _check_transaction_state(self) -> Tuple[bool, List[str], List[str]]:
        """检查是否有未提交的事务"""
        issues = []
        suggestions = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 检查是否有活跃的事务
            cursor = conn.execute("PRAGMA lock_status")
            locks = cursor.fetchall()
            
            for lock in locks:
                db_name, lock_type = lock[0], lock[1]
                if lock_type not in ("unlocked", ""):
                    issues.append(f"数据库 {db_name} 处于锁定状态: {lock_type}")
                    suggestions.append("尝试关闭所有打开的程序实例")
                    suggestions.append("重启程序可能解决此问题")
            
            conn.close()
            
            if issues:
                return False, issues, suggestions
            return True, [], []
            
        except Exception as e:
            issues.append(f"无法检查事务状态: {e}")
            return False, issues, suggestions
    
    def _check_foreign_keys(self) -> Tuple[bool, List[str], List[str]]:
        """检查外键约束"""
        warnings = []
        suggestions = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 检查外键是否启用
            cursor = conn.execute("PRAGMA foreign_keys")
            fk_status = cursor.fetchone()
            
            if not fk_status or fk_status[0] == 0:
                warnings.append("外键约束未启用（这可能导致数据不一致）")
                suggestions.append("程序启动时应自动启用外键约束")
            
            # 检查外键违规
            cursor = conn.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()
            
            if violations:
                warnings.append(f"发现 {len(violations)} 个外键约束违规")
                for v in violations[:5]:  # 最多显示5个
                    warnings.append(f"  表 {v[0]}, 行 {v[1]}: 外键违规")
                if len(violations) > 5:
                    warnings.append(f"  ... 还有 {len(violations) - 5} 个")
                suggestions.append("使用数据修复工具清理孤立记录")
            
            conn.close()
            return len(violations) == 0, warnings, suggestions
            
        except Exception as e:
            warnings.append(f"无法检查外键: {e}")
            return False, warnings, suggestions
    
    def _check_schema(self) -> Tuple[bool, List[str]]:
        """检查表结构完整性"""
        warnings = []
        
        required_tables = [
            "Patient",
            "Surgery", 
            "Pathology",
            "Molecular",
            "FollowUpEvent"
        ]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = []
            for table in required_tables:
                if table not in existing_tables:
                    missing_tables.append(table)
            
            if missing_tables:
                warnings.append(f"缺少必需的表: {', '.join(missing_tables)}")
            
            conn.close()
            return len(missing_tables) == 0, warnings
            
        except Exception as e:
            warnings.append(f"无法检查表结构: {e}")
            return False, warnings
    
    def _check_data_consistency(self) -> Tuple[bool, List[str], List[str]]:
        """检查数据一致性"""
        warnings = []
        suggestions = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 1. 检查重复的 hospital_id
            cursor = conn.execute("""
                SELECT hospital_id, COUNT(*) as cnt 
                FROM Patient 
                WHERE hospital_id IS NOT NULL 
                GROUP BY hospital_id 
                HAVING cnt > 1
            """)
            duplicates = cursor.fetchall()
            
            if duplicates:
                warnings.append(f"发现 {len(duplicates)} 个重复的住院号")
                for dup in duplicates[:5]:
                    warnings.append(f"  住院号 {dup[0]} 重复了 {dup[1]} 次")
                if len(duplicates) > 5:
                    warnings.append(f"  ... 还有 {len(duplicates) - 5} 个")
                suggestions.append("合并或删除重复的患者记录")
            
            # 2. 检查空的必填字段
            cursor = conn.execute("""
                SELECT COUNT(*) 
                FROM Patient 
                WHERE hospital_id IS NULL OR hospital_id = ''
            """)
            null_hospital_id = cursor.fetchone()[0]
            
            if null_hospital_id > 0:
                warnings.append(f"发现 {null_hospital_id} 个患者的住院号为空")
                suggestions.append("为这些患者补充住院号")
            
            # 3. 检查孤立的子记录（各个表）
            tables_to_check = [
                ("Surgery", "surgery_id"),
                ("Pathology", "path_id"),
                ("Molecular", "mol_id"),
                ("FollowUpEvent", "event_id")
            ]
            
            total_orphans = 0
            for table_name, id_field in tables_to_check:
                try:
                    cursor = conn.execute(f"""
                        SELECT COUNT(*) 
                        FROM {table_name} t 
                        WHERE NOT EXISTS (
                            SELECT 1 FROM Patient p WHERE p.patient_id = t.patient_id
                        )
                    """)
                    orphan_count = cursor.fetchone()[0]
                    
                    if orphan_count > 0:
                        warnings.append(f"发现 {orphan_count} 条孤立的{table_name}记录")
                        total_orphans += orphan_count
                except:
                    pass
            
            if total_orphans > 0:
                suggestions.append("清理这些孤立记录（运行快速修复可能有帮助）")
            
            # 4. 检查主键ID冲突（理论上不应该发生，但作为额外保障）
            for table_name, id_field in tables_to_check:
                try:
                    cursor = conn.execute(f"""
                        SELECT {id_field}, COUNT(*) as cnt
                        FROM {table_name}
                        GROUP BY {id_field}
                        HAVING cnt > 1
                    """)
                    id_duplicates = cursor.fetchall()
                    
                    if id_duplicates:
                        warnings.append(f"⚠ 严重：{table_name}表存在重复的主键ID")
                        for dup in id_duplicates[:3]:
                            warnings.append(f"  ID {dup[0]} 重复了 {dup[1]} 次")
                        suggestions.append(f"这是严重的数据库错误，请联系技术支持")
                except:
                    pass
            
            # 5. 检查ID范围和跳跃（信息性检查）
            try:
                cursor = conn.execute("SELECT MIN(patient_id), MAX(patient_id), COUNT(*) FROM Patient")
                min_id, max_id, count = cursor.fetchone()
                
                if min_id and max_id and count:
                    expected_range = max_id - min_id + 1
                    gap = expected_range - count
                    
                    if gap > count * 0.5:  # 如果间隙超过50%
                        warnings.append(f"Patient表ID存在较大跳跃（间隙：{gap}）")
                        warnings.append("  这通常是删除记录或合并数据库后的正常现象")
            except:
                pass
            
            conn.close()
            
            is_consistent = (
                len(duplicates) == 0 and 
                null_hospital_id == 0 and 
                total_orphans == 0
            )
            
            return is_consistent, warnings, suggestions
            
        except Exception as e:
            warnings.append(f"无法检查数据一致性: {e}")
            return False, warnings, suggestions
    
    def format_report(self, result: HealthCheckResult) -> str:
        """格式化健康检查报告"""
        lines = []
        
        lines.append("=" * 60)
        lines.append("数据库健康检查报告")
        lines.append("=" * 60)
        lines.append("")
        
        # 总体状态
        if result.is_healthy:
            lines.append("✓ 数据库状态：健康")
        else:
            lines.append("✗ 数据库状态：发现问题")
        lines.append("")
        
        # 严重问题
        if result.issues:
            lines.append("严重问题（需要立即修复）:")
            for i, issue in enumerate(result.issues, 1):
                lines.append(f"  {i}. {issue}")
            lines.append("")
        
        # 警告
        if result.warnings:
            lines.append("警告（建议修复）:")
            for i, warning in enumerate(result.warnings, 1):
                lines.append(f"  {i}. {warning}")
            lines.append("")
        
        # 建议
        if result.suggestions:
            lines.append("修复建议:")
            for i, suggestion in enumerate(result.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


def quick_fix_database(db_path: Path) -> List[str]:
    """
    快速修复数据库的常见问题
    
    Returns:
        修复操作列表
    """
    actions = []
    
    try:
        conn = sqlite3.connect(db_path)
        
        # 1. 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        actions.append("启用外键约束")
        
        # 2. 优化数据库
        conn.execute("VACUUM")
        actions.append("执行数据库优化（VACUUM）")
        
        # 3. 重建索引
        conn.execute("REINDEX")
        actions.append("重建所有索引")
        
        # 4. 提交任何待处理的事务
        conn.commit()
        actions.append("提交待处理的事务")
        
        conn.close()
        
    except Exception as e:
        actions.append(f"修复过程中出错: {e}")
    
    return actions


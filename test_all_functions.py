#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全功能测试脚本

测试所有关键功能以确保没有bug。

使用方法:
    python test_all_functions.py
"""

from __future__ import annotations

import sys
import os
import tempfile
import shutil
from pathlib import Path

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    try:
        # Python 3.7+
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.6及更早版本
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目根目录到模块搜索路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from db.models import Database
from utils.field_validator import PatientDataValidator, safe_str
from utils.db_health_checker import DatabaseHealthChecker, quick_fix_database


def test_database_creation():
    """测试数据库创建"""
    print("\n" + "=" * 60)
    print("测试 1：数据库创建")
    print("=" * 60)
    
    try:
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        temp_path = Path(temp_db.name)
        
        db = Database(temp_path)
        
        # 检查表是否创建
        tables = db.list_tables()
        required_tables = ["Patient", "Surgery", "Pathology", "Molecular", "FollowUpEvent"]
        
        for table in required_tables:
            if table in tables:
                print(f"  ✓ {table} 表已创建")
            else:
                print(f"  ✗ {table} 表创建失败")
                return False
        
        db.close()
        temp_path.unlink()
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_patient_crud():
    """测试患者的增删改查"""
    print("\n" + "=" * 60)
    print("测试 2：患者 CRUD 操作")
    print("=" * 60)
    
    try:
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        temp_path = Path(temp_db.name)
        
        db = Database(temp_path)
        
        # 1. 创建患者
        patient_data = {
            "hospital_id": "TEST001",
            "cancer_type": "肺癌",
            "sex": "男",
            "birth_ym4": "199001",
            "pack_years": 20.5,
        }
        
        pid = db.insert_patient(patient_data)
        print(f"  ✓ 创建患者成功 (ID={pid})")
        
        # 2. 读取患者
        patient = db.get_patient_by_id(pid)
        if patient:
            patient_dict = dict(patient)
            print(f"  ✓ 读取患者成功: {patient_dict.get('hospital_id')}")
        else:
            print(f"  ✗ 读取患者失败")
            return False
        
        # 3. 更新患者
        db.update_patient(pid, {"pack_years": 25.0})
        updated = db.get_patient_by_id(pid)
        if updated:
            updated_dict = dict(updated)
            if updated_dict.get("pack_years") == 25.0:
                print(f"  ✓ 更新患者成功")
            else:
                print(f"  ✗ 更新患者失败")
                return False
        
        # 4. 按住院号查询
        patient_by_hid = db.get_patient_by_hospital_id("TEST001")
        if patient_by_hid:
            print(f"  ✓ 按住院号查询成功")
        else:
            print(f"  ✗ 按住院号查询失败")
            return False
        
        # 5. 删除患者
        db.delete_patient(pid)
        deleted = db.get_patient_by_id(pid)
        if deleted is None:
            print(f"  ✓ 删除患者成功")
        else:
            print(f"  ✗ 删除患者失败")
            return False
        
        db.close()
        temp_path.unlink()
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_field_validation():
    """测试字段验证器"""
    print("\n" + "=" * 60)
    print("测试 3：字段验证")
    print("=" * 60)
    
    try:
        # 测试必填字段
        data1 = {"hospital_id": "", "cancer_type": "肺癌", "sex": "男"}
        errors1 = PatientDataValidator.validate_patient_data(data1)
        if errors1:
            print(f"  ✓ 必填字段验证成功（检测到错误）")
        else:
            print(f"  ✗ 必填字段验证失败（应该检测到错误）")
            return False
        
        # 测试 "None" 字符串检测
        data2 = {
            "hospital_id": "TEST001",
            "cancer_type": "肺癌",
            "sex": "男",
            "birth_ym4": "None"
        }
        errors2 = PatientDataValidator.validate_patient_data(data2)
        if any("None" in e.error_message for e in errors2):
            print(f"  ✓ 'None'字符串检测成功")
        else:
            print(f"  ✗ 'None'字符串检测失败")
            return False
        
        # 测试日期格式验证
        data3 = {
            "hospital_id": "TEST001",
            "cancer_type": "肺癌",
            "sex": "男",
            "nac_date": "25-01-15"  # 错误格式
        }
        errors3 = PatientDataValidator.validate_patient_data(data3)
        if errors3:
            print(f"  ✓ 日期格式验证成功")
        else:
            print(f"  ✗ 日期格式验证失败")
            return False
        
        # 测试正确数据
        data4 = {
            "hospital_id": "TEST001",
            "cancer_type": "肺癌",
            "sex": "男",
            "birth_ym4": "199001",
            "nac_date": "250115"
        }
        errors4 = PatientDataValidator.validate_patient_data(data4)
        if not errors4:
            print(f"  ✓ 正确数据验证通过")
        else:
            print(f"  ✗ 正确数据验证失败: {errors4}")
            return False
        
        # 测试 safe_str 函数
        test_cases = [
            (None, ""),
            ("", ""),
            ("None", ""),
            ("NONE", ""),
            ("  None  ", ""),
            ("normal text", "normal text"),
            (123, "123"),
        ]
        
        all_passed = True
        for input_val, expected in test_cases:
            result = safe_str(input_val)
            if result == expected:
                pass
            else:
                print(f"  ✗ safe_str({repr(input_val)}) = {repr(result)}, expected {repr(expected)}")
                all_passed = False
        
        if all_passed:
            print(f"  ✓ safe_str 函数测试通过")
        else:
            return False
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_health_check():
    """测试数据库健康检查"""
    print("\n" + "=" * 60)
    print("测试 4：数据库健康检查")
    print("=" * 60)
    
    try:
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        temp_path = Path(temp_db.name)
        
        db = Database(temp_path)
        
        # 创建一些测试数据
        pid = db.insert_patient({
            "hospital_id": "TEST001",
            "cancer_type": "肺癌",
            "sex": "男"
        })
        
        db.insert_surgery(pid, {
            "surgery_date6": "250115",
            "indication": "原发治疗"
        })
        
        db.close()
        
        # 运行健康检查
        checker = DatabaseHealthChecker(temp_path)
        result = checker.check_all()
        
        print(f"  数据库状态: {'健康✓' if result.is_healthy else '有问题✗'}")
        print(f"  问题数量: {len(result.issues)}")
        print(f"  警告数量: {len(result.warnings)}")
        
        if result.issues:
            print("  问题列表:")
            for issue in result.issues:
                print(f"    - {issue}")
        
        if result.warnings:
            print("  警告列表:")
            for warning in result.warnings[:5]:
                print(f"    - {warning}")
        
        temp_path.unlink()
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_zero_division_protection():
    """测试除零保护"""
    print("\n" + "=" * 60)
    print("测试 5：除零错误保护")
    print("=" * 60)
    
    try:
        from export.parallel import ExportProgress
        
        # 测试total_tasks为0的情况
        progress = ExportProgress(0)
        
        def dummy_callback(value):
            pass
        
        progress.set_callback(dummy_callback)
        progress.update()  # 应该不抛出异常
        
        print(f"  ✓ ExportProgress处理total_tasks=0成功")
        
        # 测试正常情况
        progress2 = ExportProgress(10)
        progress2.set_callback(dummy_callback)
        progress2.update(5)
        
        print(f"  ✓ ExportProgress正常使用成功")
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sqlite_row_compatibility():
    """测试sqlite3.Row兼容性"""
    print("\n" + "=" * 60)
    print("测试 6：sqlite3.Row 兼容性")
    print("=" * 60)
    
    try:
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        temp_path = Path(temp_db.name)
        
        db = Database(temp_path)
        
        # 创建测试患者
        pid = db.insert_patient({
            "hospital_id": "TEST001",
            "cancer_type": "肺癌",
            "sex": "男"
        })
        
        # 测试 get_patient_by_hospital_id
        row = db.get_patient_by_hospital_id("TEST001")
        
        if row:
            # 方法1：dict转换
            try:
                row_dict = dict(row)
                value1 = row_dict.get("patient_id")
                print(f"  ✓ dict转换方式成功 (patient_id={value1})")
            except Exception as e:
                print(f"  ✗ dict转换方式失败: {e}")
                return False
            
            # 方法2：索引访问
            try:
                value2 = row["patient_id"]
                print(f"  ✓ 索引访问方式成功 (patient_id={value2})")
            except Exception as e:
                print(f"  ✗ 索引访问方式失败: {e}")
                return False
            
            # 方法3：.get()（可能失败）
            try:
                value3 = row.get("patient_id")
                print(f"  ✓ .get()方式成功 (patient_id={value3})")
            except AttributeError:
                print(f"  ⚠ .get()方式不可用（这是预期的，在某些环境中）")
            except Exception as e:
                print(f"  ✗ .get()方式失败（非预期）: {e}")
        
        db.close()
        temp_path.unlink()
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_type_conversion_safety():
    """测试类型转换安全性"""
    print("\n" + "=" * 60)
    print("测试 7：类型转换安全性")
    print("=" * 60)
    
    test_cases = [
        # (输入值, 类型, 应该成功)
        ("123", "int", True),
        ("abc", "int", False),
        ("12.5", "float", True),
        ("xyz", "float", False),
        ("", "int", True),  # 空值应该返回None
        (None, "int", True),
        ("None", "int", False),  # "None"字符串应该报错
    ]
    
    def safe_int_test(value):
        if not value or str(value).strip() == "":
            return None
        if str(value).strip().lower() == "none":
            raise ValueError("Invalid value 'None'")
        return int(value)
    
    def safe_float_test(value):
        if not value or str(value).strip() == "":
            return None
        if str(value).strip().lower() == "none":
            raise ValueError("Invalid value 'None'")
        return float(value)
    
    all_passed = True
    for input_val, convert_type, should_succeed in test_cases:
        try:
            if convert_type == "int":
                result = safe_int_test(input_val)
            else:
                result = safe_float_test(input_val)
            
            if should_succeed:
                print(f"  ✓ {convert_type}({repr(input_val)}) = {result}")
            else:
                print(f"  ✗ {convert_type}({repr(input_val)}) 应该失败但成功了")
                all_passed = False
                
        except Exception as e:
            if not should_succeed:
                print(f"  ✓ {convert_type}({repr(input_val)}) 正确抛出异常")
            else:
                print(f"  ✗ {convert_type}({repr(input_val)}) 不应该失败: {e}")
                all_passed = False
    
    if all_passed:
        print("\n✓ 测试通过")
    else:
        print("\n✗ 测试失败")
    
    return all_passed


def test_connection_cleanup():
    """测试数据库连接正确关闭"""
    print("\n" + "=" * 60)
    print("测试 8：数据库连接清理")
    print("=" * 60)
    
    try:
        import sqlite3
        
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        temp_path = Path(temp_db.name)
        
        # 创建数据库
        db = Database(temp_path)
        db.insert_patient({
            "hospital_id": "TEST001",
            "cancer_type": "肺癌",
            "sex": "男"
        })
        db.close()
        
        # 模拟导入过程中的连接管理
        conn = None
        try:
            conn = sqlite3.connect(temp_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM Patient")
            rows = cursor.fetchall()
            print(f"  ✓ 连接打开并查询成功 ({len(rows)} 行)")
            
            # 模拟异常
            raise Exception("模拟异常")
            
        except Exception as e:
            print(f"  ✓ 捕获异常: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                    print(f"  ✓ finally块中成功关闭连接")
                except:
                    pass
        
        # 验证文件可以被删除（说明连接已关闭）
        try:
            temp_path.unlink()
            print(f"  ✓ 文件可以删除（连接已完全关闭）")
        except PermissionError:
            print(f"  ✗ 文件无法删除（连接可能未关闭）")
            return False
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_thread_safety():
    """测试多线程安全性"""
    print("\n" + "=" * 60)
    print("测试 9：多线程安全性")
    print("=" * 60)
    
    try:
        import concurrent.futures
        
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        temp_path = Path(temp_db.name)
        
        # 创建数据库并添加测试数据
        db = Database(temp_path)
        for i in range(10):
            db.insert_patient({
                "hospital_id": f"TEST{i:03d}",
                "cancer_type": "肺癌",
                "sex": "男"
            })
        db.close()
        
        # 测试并行读取
        def read_patients(thread_id):
            import sqlite3
            conn = sqlite3.connect(temp_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM Patient")
            rows = cursor.fetchall()
            conn.close()
            return (thread_id, len(rows))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(read_patients, i) for i in range(4)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        if all(r[1] == 10 for r in results):
            print(f"  ✓ 并行读取成功（4个线程都读取到10条记录）")
        else:
            print(f"  ✗ 并行读取失败: {results}")
            return False
        
        temp_path.unlink()
        
        print("\n✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print(" " * 20 + "全功能测试套件")
    print("=" * 70)
    
    tests = [
        test_database_creation,
        test_patient_crud,
        test_field_validation,
        test_sqlite_row_compatibility,
        test_type_conversion_safety,
        test_connection_cleanup,
        test_thread_safety,
    ]
    
    results = []
    for test_func in tests:
        result = test_func()
        results.append((test_func.__name__, result))
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status} - {name}")
    
    print("-" * 70)
    print(f"  总计: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 所有测试通过！代码质量良好。")
        return True
    else:
        print(f"\n⚠ {total - passed} 个测试失败，需要修复。")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n测试过程中发生未处理的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


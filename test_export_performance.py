#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出性能测试脚本

测试多线程优化后的导出性能，对比优化前后的速度提升。

使用方法:
    python test_export_performance.py

注意：请确保 thoracic.db 文件存在且包含测试数据
"""

from __future__ import annotations

import time
import sys
from pathlib import Path

# 添加项目根目录到模块搜索路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from db.models import Database
from export.excel import export_all_to_excel, export_patient_to_excel
from export.csv import export_all_to_csv, export_patient_to_csv


def test_database_stats(db: Database):
    """显示数据库统计信息"""
    print("=" * 60)
    print("数据库统计信息")
    print("=" * 60)
    
    tables = ["Patient", "Surgery", "Pathology", "Molecular", "FollowUpEvent"]
    total_records = 0
    
    for table in tables:
        try:
            count = len(db.export_table(table))
            total_records += count
            print(f"{table:20s}: {count:6d} 条记录")
        except Exception as e:
            print(f"{table:20s}: 错误 - {e}")
    
    print("-" * 60)
    print(f"{'总计':20s}: {total_records:6d} 条记录")
    print("=" * 60)
    print()


def test_export_excel_all(db: Database, output_dir: Path):
    """测试全库 Excel 导出性能"""
    print("测试：全库 Excel 导出")
    print("-" * 60)
    
    output_file = output_dir / "test_all.xlsx"
    
    # 进度回调
    progress_data = {"last_update": 0}
    
    def progress_callback(value):
        if int(value) - progress_data["last_update"] >= 10:
            print(f"  进度: {int(value)}%")
            progress_data["last_update"] = int(value)
    
    start_time = time.time()
    
    try:
        export_all_to_excel(db, output_file, progress_callback=progress_callback)
        elapsed_time = time.time() - start_time
        
        file_size = output_file.stat().st_size / 1024 / 1024  # MB
        patient_count = len(db.export_table("Patient"))
        
        print(f"✓ 导出成功")
        print(f"  耗时: {elapsed_time:.2f} 秒")
        print(f"  文件大小: {file_size:.2f} MB")
        print(f"  平均速度: {patient_count / elapsed_time:.1f} 患者/秒")
        print()
        return elapsed_time
        
    except Exception as e:
        print(f"✗ 导出失败: {e}")
        print()
        return None


def test_export_csv_all(db: Database, output_dir: Path):
    """测试全库 CSV 导出性能"""
    print("测试：全库 CSV 导出")
    print("-" * 60)
    
    csv_dir = output_dir / "csv_all"
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    # 进度回调
    progress_data = {"last_update": 0}
    
    def progress_callback(value):
        if int(value) - progress_data["last_update"] >= 10:
            print(f"  进度: {int(value)}%")
            progress_data["last_update"] = int(value)
    
    start_time = time.time()
    
    try:
        files = export_all_to_csv(db, csv_dir, progress_callback=progress_callback)
        elapsed_time = time.time() - start_time
        
        total_size = sum(f.stat().st_size for f in files) / 1024 / 1024  # MB
        patient_count = len(db.export_table("Patient"))
        
        print(f"✓ 导出成功")
        print(f"  耗时: {elapsed_time:.2f} 秒")
        print(f"  文件数量: {len(files)} 个")
        print(f"  总大小: {total_size:.2f} MB")
        print(f"  平均速度: {patient_count / elapsed_time:.1f} 患者/秒")
        print()
        return elapsed_time
        
    except Exception as e:
        print(f"✗ 导出失败: {e}")
        print()
        return None


def test_export_patient_excel(db: Database, output_dir: Path):
    """测试单患者 Excel 导出性能"""
    print("测试：单患者 Excel 导出")
    print("-" * 60)
    
    # 获取第一个患者
    patients = db.conn.execute("SELECT patient_id FROM Patient LIMIT 1").fetchall()
    if not patients:
        print("✗ 数据库中没有患者数据")
        print()
        return None
    
    patient_id = patients[0][0]
    output_file = output_dir / f"test_patient_{patient_id}.xlsx"
    
    start_time = time.time()
    
    try:
        export_patient_to_excel(db, patient_id, output_file)
        elapsed_time = time.time() - start_time
        
        file_size = output_file.stat().st_size / 1024  # KB
        
        print(f"✓ 导出成功")
        print(f"  患者 ID: {patient_id}")
        print(f"  耗时: {elapsed_time:.3f} 秒")
        print(f"  文件大小: {file_size:.2f} KB")
        print()
        return elapsed_time
        
    except Exception as e:
        print(f"✗ 导出失败: {e}")
        print()
        return None


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("导出性能测试")
    print("=" * 60)
    print()
    
    # 检查数据库文件
    db_path = Path("thoracic.db")
    if not db_path.exists():
        print("错误：找不到 thoracic.db 文件")
        print("请确保数据库文件存在于当前目录")
        return
    
    # 创建输出目录
    output_dir = Path("test_export_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 打开数据库
    db = Database(db_path)
    
    # 显示数据库统计
    test_database_stats(db)
    
    # 运行性能测试
    results = {}
    
    results["excel_all"] = test_export_excel_all(db, output_dir)
    results["csv_all"] = test_export_csv_all(db, output_dir)
    results["patient_excel"] = test_export_patient_excel(db, output_dir)
    
    # 显示测试总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if results["excel_all"]:
        print(f"全库 Excel 导出:     {results['excel_all']:.2f} 秒")
    
    if results["csv_all"]:
        print(f"全库 CSV 导出:       {results['csv_all']:.2f} 秒")
    
    if results["patient_excel"]:
        print(f"单患者 Excel 导出:   {results['patient_excel']:.3f} 秒")
    
    print()
    print(f"测试输出目录: {output_dir.absolute()}")
    print("=" * 60)
    print()
    
    # 关闭数据库
    db.close()
    
    print("测试完成！")
    print()
    print("提示：")
    print("- 多次运行测试以获得更准确的平均值")
    print("- 第一次运行可能较慢（缓存预热）")
    print("- 关闭其他程序以获得更准确的结果")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


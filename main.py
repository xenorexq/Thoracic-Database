# -*- coding: utf-8 -*-
from __future__ import annotations

import sys, os
import sqlite3
import threading
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))  # 关键:把项目根加入模块搜索路径

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# 下面全部用"绝对导入"（不带.或..）
from db.models import Database
from ui.patient_tab import PatientTab
from ui.surgery_tab import SurgeryTab
from ui.path_tab import PathologyTab
from ui.mol_tab import MolecularTab
from ui.fu_tab import FollowUpTab
from ui.export_tab import ExportTab
from staging.lookup import load_mapping_from_csv
from db.migrate import migrate_database


class ThoracicApp:
    """胸外科科研数据录入系统主程序"""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("胸外科科研数据录入系统")
        self.root.geometry("1400x800")

        # 初始化数据库
        self.db_path = Path("./thoracic.db")
        self.db = Database(self.db_path)
        
        # 执行数据库迁移
        migrate_database(self.db_path)

        # 加载分期映射表
        assets_dir = Path(__file__).parent / "assets"
        load_mapping_from_csv(self.db, assets_dir)

        # 当前患者状态
        # 统一使用 patient_id 和 hospital_id 保存当前选中患者的标识
        # patient_id 用于数据库主键；hospital_id 对应住院号
        self.current_patient_id = None
        self.current_hospital_id = None
        self.cancer_type = None

        # 创建主容器（使用PanedWindow实现左右分栏）
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill="both", expand=True)

        # 左侧患者列表面板
        left_frame = ttk.Frame(main_paned, width=250)
        main_paned.add(left_frame, weight=0)
        
        self._build_patient_list(left_frame)

        # 右侧标签页面板
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # 创建标签页
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill="both", expand=True)

        # 初始化各个页面
        self.patient_tab = PatientTab(self, self.notebook)
        self.surgery_tab = SurgeryTab(self.notebook, self)
        self.path_tab = PathologyTab(self.notebook, self)
        self.mol_tab = MolecularTab(self.notebook, self)
        self.fu_tab = FollowUpTab(self.notebook, self)
        self.export_tab = ExportTab(self.notebook, self)

        # 添加页签
        self.notebook.add(self.patient_tab, text="患者/治疗")
        self.notebook.add(self.surgery_tab, text="手术")
        self.notebook.add(self.path_tab, text="病理")
        self.notebook.add(self.mol_tab, text="分子")
        self.notebook.add(self.fu_tab, text="随访")
        self.notebook.add(self.export_tab, text="查询/导出")

        # 菜单栏
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新建患者 (Ctrl+N)", command=self.new_patient)
        file_menu.add_command(label="保存 (Ctrl+S)", command=self.save_current)
        file_menu.add_separator()
        file_menu.add_command(label="备份数据库...", command=self.backup_database)
        file_menu.add_command(label="导入数据库...", command=self.import_database)
        file_menu.add_separator()
        file_menu.add_command(label="数据库健康检查...", command=self.check_database_health)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于...", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menubar)

        # 快捷键绑定
        self.root.bind("<Control-n>", lambda e: self.new_patient())
        self.root.bind("<Control-s>", lambda e: self.save_current())

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status("数据库已加载：" + str(self.db_path))
        
        # 初始加载患者列表
        self.refresh_patient_list()

    def _build_patient_list(self, parent):
        """构建左侧患者列表面板"""
        # 标题
        title_label = ttk.Label(parent, text="患者列表", font=("Arial", 12, "bold"))
        title_label.pack(pady=5)

        # 搜索框
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(search_frame, text="快速查找:").pack(side="top", anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_patient_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(fill="x", pady=2)

        # 癌种筛选
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(filter_frame, text="癌种筛选:").pack(side="top", anchor="w")
        self.filter_var = tk.StringVar(value="全部")
        filter_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.filter_var,
            values=["全部", "肺癌", "食管癌"],
            state="readonly",
            width=15
        )
        filter_combo.pack(fill="x", pady=2)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_patient_list())

        # 患者列表（使用Treeview）
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        # Treeview
        self.patient_tree = ttk.Treeview(
            list_frame,
            columns=("id", "hospital_id", "cancer_type"),
            show="tree headings",
            yscrollcommand=scrollbar.set,
            selectmode="browse"
        )
        self.patient_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.patient_tree.yview)

        # 调整行高，避免选中条目显示不完整
        style = ttk.Style()
        try:
            style.configure("Treeview", rowheight=24)
        except Exception:
            # 某些主题可能不支持此配置
            pass

        # 列配置
        self.patient_tree.column("#0", width=0, stretch=False)
        self.patient_tree.column("id", width=50, anchor="center")
        self.patient_tree.column("hospital_id", width=100)
        self.patient_tree.column("cancer_type", width=60, anchor="center")

        self.patient_tree.heading("id", text="ID")
        self.patient_tree.heading("hospital_id", text="住院号")
        self.patient_tree.heading("cancer_type", text="癌种")

        # 双击加载患者
        self.patient_tree.bind("<Double-1>", self.on_patient_double_click)
        # 单击选择时即同步加载所有标签页，避免手动刷新
        self.patient_tree.bind("<<TreeviewSelect>>", self.on_patient_select)
        
        # 新建按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="新建患者", command=self.new_patient).pack(fill="x")

    def refresh_patient_list(self, select_patient_id=None, reload_data=False):
        """刷新患者列表
        
        Args:
            select_patient_id: 要选中的患者ID
            reload_data: 是否重新加载患者数据到所有标签页（默认False，避免递归）
        """
        # 清空现有列表
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)

        # 获取所有患者
        cursor = self.db.conn.execute(
            "SELECT patient_id, hospital_id, cancer_type FROM Patient ORDER BY patient_id DESC"
        )
        all_patients = cursor.fetchall()

        # 应用筛选
        search_text = self.search_var.get().strip().lower()
        filter_type = self.filter_var.get()

        for row in all_patients:
            patient_id, hospital_id, cancer_type = row
            
            # 筛选逻辑
            if filter_type != "全部" and cancer_type != filter_type:
                continue
            
            if search_text:
                if search_text not in str(patient_id).lower() and \
                   search_text not in (hospital_id or "").lower():
                    continue

            # 插入到列表
            item_id = self.patient_tree.insert(
                "", "end",
                values=(patient_id, hospital_id or "", cancer_type or "")
            )
            
            # 如果是要选中的患者，则选中
            if select_patient_id and patient_id == select_patient_id:
                self.patient_tree.selection_set(item_id)
                self.patient_tree.see(item_id)
        
        # v2.14: 只有在reload_data=True时才调用load_patient，避免递归
        if select_patient_id and reload_data:
            self.load_patient(select_patient_id)

    def filter_patient_list(self):
        """筛选患者列表"""
        self.refresh_patient_list(self.current_patient_id)

    def on_patient_double_click(self, event):
        """双击患者列表项时加载患者"""
        selection = self.patient_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.patient_tree.item(item, "values")
        if values:
            patient_id = int(values[0])
            self.load_patient(patient_id)

    def on_patient_select(self, event=None):
        """选择患者列表项时同步加载所有标签页数据。"""
        selection = self.patient_tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.patient_tree.item(item, "values")
        if not values:
            return
        try:
            patient_id = int(values[0])
        except (TypeError, ValueError):
            return
        if patient_id == self.current_patient_id:
            return
        self.load_patient(patient_id)

    def load_patient(self, patient_id: int):
        """加载患者数据到各个Tab"""
        """根据患者ID加载患者信息并更新当前状态。"""
        # 首先重置当前患者标识
        self.current_patient_id = None
        self.current_hospital_id = None

        # 获取患者信息
        row = self.db.get_patient_by_id(patient_id)
        if row:
            patient_dict = dict(row)
            # 更新全局当前患者状态
            self.current_patient_id = patient_id
            self.current_hospital_id = patient_dict.get("hospital_id") or None
            self.cancer_type = patient_dict.get("cancer_type")
            
            # 加载到各个Tab
            self.patient_tab.load_patient(patient_dict)
            # 其他标签页使用 patient_id 加载数据
            self.surgery_tab.load_patient(patient_id)
            self.path_tab.load_patient(patient_id)
            self.mol_tab.load_patient(patient_id)
            self.fu_tab.load_patient(patient_id)
            
            self.status(f"已加载患者: {patient_dict.get('hospital_id', '')} (ID: {patient_id})")
            
            # 切换到患者/治疗页
            self.notebook.select(0)

    def new_patient(self):
        """新建患者"""
        # 新建患者时，清空当前患者状态
        self.current_patient_id = None
        self.current_hospital_id = None
        self.cancer_type = None
        
        # 清空并刷新所有Tab
        # 患者/治疗页只需清空表单
        self.patient_tab.clear_form()
        # 手术标签页
        try:
            self.surgery_tab.clear_form()
            self.surgery_tab.load_patient(None)
        except Exception:
            pass
        # 病理标签页
        try:
            self.path_tab.clear_form()
            self.path_tab.load_patient(None)
        except Exception:
            pass
        # 分子标签页
        try:
            self.mol_tab.clear_form()
            self.mol_tab.load_patient(None)
        except Exception:
            pass
        # 随访标签页
        try:
            self.fu_tab.clear_form()
            self.fu_tab.load_patient(None)
        except Exception:
            pass
        # 切换到患者/治疗页并更新状态
        self.notebook.select(0)
        self.status("新建患者")

    def save_current(self):
        """保存当前页面"""
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:  # 患者/治疗
            self.patient_tab.save_patient()
        elif current_tab == 1:  # 手术
            self.surgery_tab.save_surgery()
        elif current_tab == 2:  # 病理
            self.path_tab.save_pathology()
        elif current_tab == 3:  # 分子
            self.mol_tab.save_molecular()
        elif current_tab == 4:  # 随访
            self.fu_tab.save_followup()

    def on_cancer_type_change(self, cancer_type: str):
        """癌种改变时的回调"""
        self.cancer_type = cancer_type
        # 通知各个Tab更新状态
        if hasattr(self.patient_tab, 'on_cancer_type_change'):
            self.patient_tab.on_cancer_type_change(cancer_type, notify_app=False)
        if hasattr(self.surgery_tab, 'on_cancer_type_change'):
            self.surgery_tab.on_cancer_type_change(cancer_type)
        if hasattr(self.path_tab, 'on_cancer_type_change'):
            self.path_tab.on_cancer_type_change(cancer_type)

    def status(self, text: str):
        """更新底部状态栏"""
        self.status_var.set(text)
    
    def show_progress(self, show: bool):
        """显示或隐藏进度条（线程安全）"""
        if show:
            # 如果已经存在且仍然有效，不重复创建
            if hasattr(self, 'progress_window') and self.progress_window and self.progress_window.winfo_exists():
                # 已经存在，重置进度
                if hasattr(self, 'progress_bar'):
                    self.progress_bar['value'] = 0
                return
            
            # 创建新窗口
            self.progress_window = tk.Toplevel(self.root)
            self.progress_window.title("导入进度")
            self.progress_window.geometry("400x100")
            self.progress_window.resizable(False, False)
            
            # 居中显示
            self.progress_window.transient(self.root)
            self.progress_window.grab_set()
            
            label = ttk.Label(self.progress_window, text="正在导入数据，请稍候...", font=("Arial", 10))
            label.pack(pady=10)
            
            self.progress_bar = ttk.Progressbar(
                self.progress_window, 
                mode='determinate',
                length=350
            )
            self.progress_bar.pack(pady=10)
            self.progress_bar['value'] = 0
        else:
            # 安全地关闭窗口
            if hasattr(self, 'progress_window'):
                try:
                    if self.progress_window and self.progress_window.winfo_exists():
                        self.progress_window.destroy()
                except:
                    pass
                finally:
                    self.progress_window = None
                    self.progress_bar = None
    
    def update_progress(self, value: float):
        """更新进度条的值（0-100）"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar['value'] = value
            self.progress_window.update()
    
    def import_database(self):
        """导入其他数据库并合并新患者数据 (带预检查和确认对话框)"""
        # 允许多选多个数据库文件
        source_dbs = filedialog.askopenfilenames(
            title="选择要导入的数据库文件",
            filetypes=[("SQLite数据库", "*.db"), ("所有文件", "*.*")]
        )

        if not source_dbs:
            return
        
        # === 第一阶段：预检查 ===
        self.status("正在分析导入文件...")
        
        try:
            from db.import_checker import check_source_databases
            from ui.import_preview_dialog import show_import_preview
            
            source_paths = [Path(db) for db in source_dbs]
            
            # 执行预检查分析
            analysis = check_source_databases(source_paths, self.db_path)
            
            # 显示预览对话框，等待用户确认
            user_confirmed = show_import_preview(self.root, analysis)
            
            if not user_confirmed:
                self.status("用户取消导入")
                return
            
            # 如果没有新患者，直接返回
            if analysis.new_patients == 0:
                self.status("没有可导入的新患者")
                return
                
        except Exception as e:
            messagebox.showerror("预检查失败", f"分析导入文件时出错：\n{e}")
            self.status("导入预检查失败")
            return
        
        # === 第二阶段：执行导入 ===

        # 准备在后台线程中运行
        def run_import():
            self.root.after(0, lambda: self.show_progress(True))
            self.root.after(0, lambda: self.status("正在准备导入..."))
            
            try:
                # 构建当前数据库已存在的 hospital_id 集合
                dest_ids = set(
                    row[0]
                    for row in self.db.conn.execute("SELECT hospital_id FROM Patient").fetchall()
                    if row[0]
                )

                total_imports = {
                    "Patient": 0,
                    "Surgery": 0,
                    "Pathology": 0,
                    "Molecular": 0,
                    "FollowUpEvent": 0,
                }

                db_count = len(source_dbs)
                for idx, source_db in enumerate(source_dbs):
                    db_name = Path(source_db).name
                    self.root.after(0, lambda m=f"正在导入 ({idx+1}/{db_count}): {db_name}": self.status(m))
                    
                    try:
                        src_conn = sqlite3.connect(source_db)
                        src_conn.row_factory = sqlite3.Row

                        # 获取所有患者
                        cursor = src_conn.execute("SELECT * FROM Patient")
                        patient_rows = cursor.fetchall()
                        
                        total_pats = len(patient_rows)
                        
                        # 映射：源 patient_id -> 目标 patient_id
                        id_map = {}

                        # 第一阶段：导入新患者并建立映射
                        # 使用事务：不在此处 commit，最后统一 commit
                        for i, row in enumerate(patient_rows):
                            if i % 50 == 0 and total_pats > 0: # 每50条更新一次进度条
                                progress_val = (i / total_pats) * 100 if total_pats > 0 else 0
                                self.root.after(0, lambda v=progress_val: self.update_progress(v))
                                
                            hospital_id = row["hospital_id"]
                            if not hospital_id or hospital_id in dest_ids:
                                continue
                            patient_data = dict(row)
                            patient_data.pop("patient_id", None)
                            # insert_patient now supports commit=False
                            new_pid = self.db.insert_patient(patient_data, commit=False)
                            dest_ids.add(hospital_id)
                            id_map[row["patient_id"]] = new_pid
                            total_imports["Patient"] += 1

                        # 如果没有新患者则不必处理子表
                        if id_map:
                            # 获取新患者源ID列表字符串用于IN语句
                            # 优化：如果是 huge list，SQLite IN limit 是 999。
                            # 分批处理 IN 查询
                            src_ids_all = list(id_map.keys())
                            chunk_size = 500
                            
                            for k in range(0, len(src_ids_all), chunk_size):
                                chunk = src_ids_all[k:k+chunk_size]
                                src_ids_list = ",".join(str(pid) for pid in chunk)
                                
                                # 导入 Surgery
                                try:
                                    cur_surg = src_conn.execute(
                                        f"SELECT * FROM Surgery WHERE patient_id IN ({src_ids_list})"
                                    )
                                    for srow in cur_surg:
                                        try:
                                            src_pid = srow["patient_id"]
                                            dest_pid = id_map.get(src_pid)
                                            if not dest_pid: continue
                                            surgery_data = dict(srow)
                                            surgery_data.pop("surgery_id", None)
                                            surgery_data.pop("patient_id", None)
                                            self.db.insert_surgery(dest_pid, surgery_data, commit=False)
                                            total_imports["Surgery"] += 1
                                        except Exception as surg_err:
                                            print(f"[WARNING] 导入单条Surgery记录失败 (患者{dest_pid}): {surg_err}")
                                except Exception as surg_table_err:
                                    print(f"[WARNING] 导入Surgery表失败: {surg_table_err}")

                                # 导入 Pathology
                                try:
                                    cur_path = src_conn.execute(
                                        f"SELECT * FROM Pathology WHERE patient_id IN ({src_ids_list})"
                                    )
                                    for prow in cur_path:
                                        try:
                                            src_pid = prow["patient_id"]
                                            dest_pid = id_map.get(src_pid)
                                            if not dest_pid: continue
                                            path_data = dict(prow)
                                            path_data.pop("path_id", None)
                                            path_data.pop("patient_id", None)
                                            self.db.insert_pathology(dest_pid, path_data, commit=False)
                                            total_imports["Pathology"] += 1
                                        except Exception as path_err:
                                            print(f"[WARNING] 导入单条Pathology记录失败 (患者{dest_pid}): {path_err}")
                                except Exception as path_table_err:
                                    print(f"[WARNING] 导入Pathology表失败: {path_table_err}")

                                # 导入 Molecular
                                try:
                                    cur_mol = src_conn.execute(
                                        f"SELECT * FROM Molecular WHERE patient_id IN ({src_ids_list})"
                                    )
                                    for mrow in cur_mol:
                                        try:
                                            src_pid = mrow["patient_id"]
                                            dest_pid = id_map.get(src_pid)
                                            if not dest_pid: continue
                                            mol_data = dict(mrow)
                                            mol_data.pop("mol_id", None)
                                            mol_data.pop("patient_id", None)
                                            self.db.insert_molecular(dest_pid, mol_data, commit=False)
                                            total_imports["Molecular"] += 1
                                        except Exception as mol_err:
                                            print(f"[WARNING] 导入单条Molecular记录失败 (患者{dest_pid}): {mol_err}")
                                except Exception as mol_table_err:
                                    print(f"[WARNING] 导入Molecular表失败: {mol_table_err}")

                                # 导入 FollowUpEvent
                                try:
                                    cur_fue = src_conn.execute(
                                        f"SELECT * FROM FollowUpEvent WHERE patient_id IN ({src_ids_list})"
                                    )
                                    for evrow in cur_fue:
                                        src_pid = evrow["patient_id"]
                                        dest_pid = id_map.get(src_pid)
                                        if not dest_pid: continue
                                        # 转换为dict确保兼容性
                                        ev_dict = dict(evrow)
                                        event_date = ev_dict.get("event_date")
                                        event_type = ev_dict.get("event_type")
                                        event_details = ev_dict.get("event_details", "")
                                        if event_date and event_type:
                                            self.db.insert_followup_event(dest_pid, event_date, event_type, event_details, event_code=None, commit=False)
                                            total_imports["FollowUpEvent"] += 1
                                except Exception as fue_err:
                                    # 记录详细错误而非静默跳过
                                    print(f"[WARNING] 导入FollowUpEvent失败: {fue_err}")
                                    import traceback
                                    traceback.print_exc()
                                
                                # 尝试导入旧版 FollowUp (兼容性)
                                try:
                                    cur_fu = src_conn.execute(
                                        f"SELECT * FROM FollowUp WHERE patient_id IN ({src_ids_list})"
                                    )
                                    for furow in cur_fu:
                                        try:
                                            src_pid = furow["patient_id"]
                                            dest_pid = id_map.get(src_pid)
                                            if not dest_pid: continue
                                            
                                            # 转换为dict确保兼容性
                                            fu_dict = dict(furow)
                                            last_visit = fu_dict.get("last_visit_date")
                                            status = fu_dict.get("status")
                                            death_date = fu_dict.get("death_date")
                                            notes = fu_dict.get("notes_fu") or ""
                                            
                                            if death_date:
                                                self.db.insert_followup_event(dest_pid, death_date, "死亡", f"旧版数据导入; {notes}", event_code=None, commit=False)
                                                total_imports["FollowUpEvent"] += 1
                                            if last_visit and last_visit != death_date:
                                                ev_type = "生存"
                                                if status and "死亡" in status:
                                                    ev_type = "失访" if "失访" in status else "生存"
                                                elif status and "失访" in status:
                                                    ev_type = "失访"
                                                detail_text = f"旧版数据导入 (状态:{status}); {notes}"
                                                self.db.insert_followup_event(dest_pid, last_visit, ev_type, detail_text, event_code=None, commit=False)
                                                total_imports["FollowUpEvent"] += 1
                                        except Exception as fu_err:
                                            print(f"[WARNING] 导入单条旧版FollowUp记录失败 (患者{dest_pid}): {fu_err}")
                                except Exception as fu_table_err:
                                    print(f"[WARNING] 导入旧版FollowUp表失败（可能该表不存在）: {fu_table_err}")

                    except Exception as e:
                        self.root.after(0, lambda err=str(e): messagebox.showerror("导入错误", f"导入 {source_db} 时出错：\n{err}"))
                    finally:
                        # 确保连接总是被关闭
                        try:
                            src_conn.close()
                        except:
                            pass

                # 所有文件处理完毕，执行一次性提交
                self.root.after(0, lambda: self.status("正在写入磁盘..."))
                self.db.commit() # CRITICAL: Commit transaction
                
                # UI 反馈
                def on_complete():
                    self.show_progress(False)
                    self.status("数据库导入完成")
                    if any(total_imports.values()):
                        summary_lines = []
                        for table, count in total_imports.items():
                            if count > 0:
                                summary_lines.append(f"{table}: {count} 条")
                        summary_text = "\n".join(summary_lines)
                        messagebox.showinfo("导入完成", f"已成功导入：\n\n{summary_text}\n\n请刷新患者列表。")
                        self.refresh_patient_list()
                    else:
                        messagebox.showinfo("导入完成", "未找到新数据或所有数据已存在。")
                        
                self.root.after(0, on_complete)

            except Exception as e:
                self.root.after(0, lambda: self.show_progress(False))
                self.root.after(0, lambda err=str(e): messagebox.showerror("严重错误", f"导入过程中发生严重错误：\n{err}"))

        # 启动线程
        threading.Thread(target=run_import, daemon=True).start()
    
    def check_database_health(self):
        """检查数据库健康状态"""
        from utils.db_health_checker import DatabaseHealthChecker, quick_fix_database
        
        self.status("正在检查数据库健康状态...")
        
        try:
            # 执行健康检查
            checker = DatabaseHealthChecker(self.db_path)
            result = checker.check_all()
            
            # 生成报告
            report = checker.format_report(result)
            
            # 显示报告对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("数据库健康检查报告")
            dialog.geometry("700x500")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 报告文本框
            from tkinter import scrolledtext
            text_frame = ttk.Frame(dialog, padding=10)
            text_frame.pack(fill="both", expand=True)
            
            report_text = scrolledtext.ScrolledText(
                text_frame,
                wrap=tk.WORD,
                width=80,
                height=20,
                font=("Courier", 9)
            )
            report_text.pack(fill="both", expand=True)
            report_text.insert("1.0", report)
            report_text.config(state="disabled")
            
            # 按钮栏
            button_frame = ttk.Frame(dialog, padding=10)
            button_frame.pack(fill="x")
            
            if not result.is_healthy or result.warnings:
                # 如果有问题，显示快速修复按钮
                def on_quick_fix():
                    if messagebox.askyesno(
                        "确认",
                        "快速修复将执行以下操作：\n\n"
                        "1. 启用外键约束\n"
                        "2. 优化数据库（VACUUM）\n"
                        "3. 重建索引\n"
                        "4. 提交待处理的事务\n\n"
                        "建议在执行前先备份数据库。\n\n"
                        "是否继续？"
                    ):
                        dialog.destroy()
                        self.status("正在执行快速修复...")
                        
                        # 先备份
                        if messagebox.askyesno("备份", "是否先备份数据库？（强烈建议）"):
                            self.backup_database()
                        
                        # 执行修复
                        actions = quick_fix_database(self.db_path)
                        
                        # 显示结果
                        result_msg = "快速修复已完成:\n\n" + "\n".join(f"✓ {action}" for action in actions)
                        messagebox.showinfo("修复完成", result_msg)
                        
                        # 重新检查
                        if messagebox.askyesno("重新检查", "是否重新检查数据库健康状态？"):
                            self.check_database_health()
                        
                        self.status("数据库修复完成")
                
                ttk.Button(
                    button_frame,
                    text="快速修复",
                    command=on_quick_fix,
                    width=15
                ).pack(side="left", padx=5)
            
            # 导出报告按钮
            def on_export():
                export_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("文本文件", "*.txt")],
                    initialfile=f"db_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                )
                if export_path:
                    with open(export_path, 'w', encoding='utf-8') as f:
                        f.write(report)
                    messagebox.showinfo("成功", f"报告已导出到:\n{export_path}")
            
            ttk.Button(
                button_frame,
                text="导出报告",
                command=on_export,
                width=15
            ).pack(side="left", padx=5)
            
            ttk.Button(
                button_frame,
                text="关闭",
                command=dialog.destroy,
                width=15
            ).pack(side="right", padx=5)
            
            self.status("数据库健康检查完成")
            
        except Exception as e:
            messagebox.showerror("错误", f"健康检查失败：\n\n{str(e)}")
            self.status("健康检查失败")
    
    def backup_database(self):
        """备份当前数据库文件"""
        # 生成默认备份文件名（使用当前日期）
        current_date = datetime.now().strftime("%Y%m%d")
        default_filename = f"thoracic_backup_{current_date}.db"
        
        # 让用户选择保存位置
        backup_path = filedialog.asksaveasfilename(
            title="备份数据库到...",
            defaultextension=".db",
            filetypes=[("SQLite数据库", "*.db"), ("所有文件", "*.*")],
            initialfile=default_filename
        )
        
        if not backup_path:
            return
        
        try:
            # 获取源数据库文件大小
            source_size = self.db_path.stat().st_size / 1024 / 1024  # MB
            
            # 复制数据库文件
            self.status(f"正在备份数据库...")
            shutil.copy2(self.db_path, backup_path)
            
            # 验证备份文件
            backup_size = Path(backup_path).stat().st_size / 1024 / 1024  # MB
            
            if backup_size == source_size:
                messagebox.showinfo(
                    "备份成功",
                    f"数据库已成功备份到：\n\n{backup_path}\n\n"
                    f"文件大小：{backup_size:.2f} MB\n"
                    f"备份时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                self.status(f"数据库备份成功：{Path(backup_path).name}")
            else:
                messagebox.showwarning(
                    "备份完成但有警告",
                    f"备份已完成，但文件大小不一致：\n\n"
                    f"源文件：{source_size:.2f} MB\n"
                    f"备份文件：{backup_size:.2f} MB\n\n"
                    f"请验证备份文件的完整性"
                )
        
        except PermissionError:
            messagebox.showerror(
                "权限错误",
                f"无法写入到目标位置：\n\n{backup_path}\n\n"
                "请检查文件夹权限或选择其他位置"
            )
            self.status("备份失败：权限不足")
        
        except Exception as e:
            messagebox.showerror(
                "备份失败",
                f"备份数据库时出错：\n\n{str(e)}"
            )
            self.status(f"备份失败：{str(e)}")
    
    def show_about(self):
        """显示关于对话框"""

        # 更新关于信息至 v3.7.0
        about_text = (
            "胸外科科研数据录入系统\n\n"
            "版本：v3.7.0\n\n"
            "功能特点：\n"
            "• 全流程患者数据管理（肺癌/食管癌）\n"
            "• 手术、病理、分子检测、随访等标签页均支持标准的新增/修改/删除，\n"
            "  列表统一为\"住院号 + 日期\"结构，移除历史的编号列\n"
            "• 全局状态管理：选择患者后，全局 current_patient_id 和 current_hospital_id 更新，\n"
            "  各标签页同步，不再各自维护独立状态\n"
            "• 多线程导出（v3.6.0 新增）：\n"
            "  - 并行数据获取，导出速度提升 2-4 倍\n"
            "  - 实时进度显示，后台处理不卡顿\n"
            "  - 支持 Excel 和 CSV 格式\n"
            "• 数据库管理（v3.6.2 新增）：\n"
            "  - 一键备份功能，自动日期命名\n"
            "  - 健康检查工具，自动诊断问题\n"
            "  - 导入预检查，查看重复和预估数据量\n"
            "• 稳定性改进（v3.7.0 新增）：\n"
            "  - 修复10个潜在bug，提升稳定性\n"
            "  - 改进异常处理，更好的错误提示\n"
            "  - 类型转换安全保护，防止崩溃\n"
            "• 数据导出（Excel/CSV），支持一键导出当前患者或整个数据库\n"
            "• 数据库导入：按住院号合并新患者，避免编号冲突，多库导入时统计导入结果\n"
            "• 查询与统计功能：快速查找患者、AJCC TNM 分期参考以及键盘快捷键支持\n\n"
            "开发者信息：\n"
            "GitHub: xenorexq\n"
            "邮箱: qinzhi100@gmail.com\n\n"
            "© 2025 胸外科科研团队"
        )
        messagebox.showinfo("关于", about_text)


def main():
    # 使用 ttkbootstrap 替换标准 Tk，应用现代化主题
    # themename 可选: cosmo, flatly, journal, litera, lumen, minty, pulse, sandstone, united, yeti (Light themes)
    # 或: cyborg, darkly, solar, superhero (Dark themes)
    root = tb.Window(themename="cosmo")
    app = ThoracicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()




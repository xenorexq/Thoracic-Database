# -*- coding: utf-8 -*-
from __future__ import annotations

import sys, os
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))  # 关键:把项目根加入模块搜索路径

import tkinter as tk
from tkinter import ttk, messagebox

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
        file_menu.add_command(label="导入数据库...", command=self.import_database)
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
    
    def import_database(self):
        """导入其他数据库并合并新患者数据

        此功能允许从一个或多个 SQLite 数据库文件中批量导入患者及其所有关联记录。
        导入逻辑仅以患者表 (`Patient`) 的 `hospital_id` 作为唯一标识，
        只有当源库中的住院号在当前数据库不存在时才会导入。
        对于已存在的患者，源库中的手术、病理、分子及随访记录都将被忽略，
        以保护当前库中经过编辑或补充的数据。
        """
        from tkinter import filedialog
        import sqlite3

        # 允许多选多个数据库文件
        source_dbs = filedialog.askopenfilenames(
            title="选择要导入的数据库文件",
            filetypes=[("SQLite数据库", "*.db"), ("所有文件", "*.*")]
        )

        if not source_dbs:
            return

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

        for source_db in source_dbs:
            try:
                src_conn = sqlite3.connect(source_db)
                src_conn.row_factory = sqlite3.Row

                # 获取所有患者
                cursor = src_conn.execute("SELECT * FROM Patient")
                patient_rows = cursor.fetchall()

                # 映射：源 patient_id -> 目标 patient_id
                id_map = {}

                # 第一阶段：导入新患者并建立映射
                for row in patient_rows:
                    hospital_id = row["hospital_id"]
                    if not hospital_id or hospital_id in dest_ids:
                        continue
                    patient_data = dict(row)
                    patient_data.pop("patient_id", None)
                    new_pid = self.db.insert_patient(patient_data)
                    dest_ids.add(hospital_id)
                    id_map[row["patient_id"]] = new_pid
                    total_imports["Patient"] += 1

                # 如果没有新患者则不必处理子表
                if id_map:
                    # 获取新患者源ID列表字符串用于IN语句
                    src_ids_list = ",".join(str(pid) for pid in id_map.keys())

                    # 导入 Surgery
                    try:
                        cur_surg = src_conn.execute(
                            f"SELECT * FROM Surgery WHERE patient_id IN ({src_ids_list})"
                        )
                        for srow in cur_surg:
                            src_pid = srow["patient_id"]
                            dest_pid = id_map.get(src_pid)
                            if not dest_pid:
                                continue
                            surgery_data = dict(srow)
                            surgery_data.pop("surgery_id", None)
                            surgery_data.pop("patient_id", None)
                            self.db.insert_surgery(dest_pid, surgery_data)
                            total_imports["Surgery"] += 1
                    except sqlite3.Error:
                        pass

                    # 导入 Pathology
                    try:
                        cur_path = src_conn.execute(
                            f"SELECT * FROM Pathology WHERE patient_id IN ({src_ids_list})"
                        )
                        for prow in cur_path:
                            src_pid = prow["patient_id"]
                            dest_pid = id_map.get(src_pid)
                            if not dest_pid:
                                continue
                            path_data = dict(prow)
                            path_data.pop("path_id", None)
                            path_data.pop("patient_id", None)
                            self.db.insert_pathology(dest_pid, path_data)
                            total_imports["Pathology"] += 1
                    except sqlite3.Error:
                        pass

                    # 导入 Molecular
                    try:
                        cur_mol = src_conn.execute(
                            f"SELECT * FROM Molecular WHERE patient_id IN ({src_ids_list})"
                        )
                        for mrow in cur_mol:
                            src_pid = mrow["patient_id"]
                            dest_pid = id_map.get(src_pid)
                            if not dest_pid:
                                continue
                            mol_data = dict(mrow)
                            mol_data.pop("mol_id", None)
                            mol_data.pop("patient_id", None)
                            self.db.insert_molecular(dest_pid, mol_data)
                            total_imports["Molecular"] += 1
                    except sqlite3.Error:
                        pass

                    # 导入 FollowUpEvent
                    try:
                        cur_fue = src_conn.execute(
                            f"SELECT * FROM FollowUpEvent WHERE patient_id IN ({src_ids_list})"
                        )
                        for evrow in cur_fue:
                            try:
                                src_pid = evrow["patient_id"]
                                dest_pid = id_map.get(src_pid)
                                if not dest_pid:
                                    continue
                                event_date = evrow["event_date"]
                                event_type = evrow["event_type"]
                                event_details = evrow.get("event_details", "")
                                # v3.5.1: 忽略源 event_code，让系统自动生成新编码，避免冲突
                                self.db.insert_followup_event(dest_pid, event_date, event_type, event_details, event_code=None)
                                total_imports["FollowUpEvent"] += 1
                            except sqlite3.Error:
                                pass
                    except sqlite3.Error:
                        # v3.5.2: 如果没有 FollowUpEvent 表，尝试从旧版 FollowUp 表导入
                        try:
                            cur_fu = src_conn.execute(
                                f"SELECT * FROM FollowUp WHERE patient_id IN ({src_ids_list})"
                            )
                            for furow in cur_fu:
                                try:
                                    src_pid = furow["patient_id"]
                                    dest_pid = id_map.get(src_pid)
                                    if not dest_pid:
                                        continue
                                    
                                    # 转换旧版字段
                                    last_visit = furow["last_visit_date"]
                                    status = furow["status"]
                                    death_date = furow["death_date"]
                                    notes = furow["notes_fu"] or ""
                                    
                                    # 1. 如果有死亡日期，创建死亡事件
                                    if death_date:
                                        self.db.insert_followup_event(dest_pid, death_date, "死亡", f"旧版数据导入; {notes}", event_code=None)
                                        total_imports["FollowUpEvent"] += 1
                                    
                                    # 2. 如果有末次随访日期，创建相应事件
                                    if last_visit:
                                        # 如果状态是死亡且日期相同，可能已在上面处理过，但为了保险起见，
                                        # 如果日期不同或者是其他状态，则创建新记录
                                        if last_visit != death_date:
                                            # 确定事件类型
                                            ev_type = "生存"
                                            if status and "死亡" in status:
                                                # 如果已经有 death_date 且日期不同，可能是一次复查
                                                ev_type = "失访" if "失访" in status else "生存"
                                            elif status and "失访" in status:
                                                ev_type = "失访"
                                            
                                            detail_text = f"旧版数据导入 (状态:{status}); {notes}"
                                            self.db.insert_followup_event(dest_pid, last_visit, ev_type, detail_text, event_code=None)
                                            total_imports["FollowUpEvent"] += 1
                                except sqlite3.Error:
                                    pass
                        except sqlite3.Error:
                            pass

                src_conn.close()
            except Exception as e:
                # 捕获每个文件的导入异常，但继续处理其他文件
                messagebox.showerror("导入错误", f"导入 {source_db} 时出错：\n{str(e)}")
                continue

        # 显示导入结果
        if any(total_imports.values()):
            summary_lines = []
            for table, count in total_imports.items():
                if count > 0:
                    summary_lines.append(f"{table}: {count} 条")
            summary_text = "\n".join(summary_lines)
            messagebox.showinfo(
                "导入完成",
                f"已成功导入以下数据：\n\n{summary_text}\n\n请刷新患者列表查看。"
            )
            self.refresh_patient_list()
        else:
            messagebox.showinfo("导入完成", "未找到新数据或所有数据已存在。")
        
        self.status("数据库导入完成")
    
    def show_about(self):
        """显示关于对话框"""

        # 更新关于信息至 v3.5.2
        about_text = (
            "胸外科科研数据录入系统\n\n"
            "版本：v3.5.2\n\n"
            "功能特点：\n"
            "• 全流程患者数据管理（肺癌/食管癌）\n"
            "• 手术、病理、分子检测、随访等标签页均支持标准的新增/修改/删除，\n"
            "  列表统一为\"住院号 + 日期\"结构，移除历史的编号列\n"
            "• 全局状态管理：选择患者后，全局 current_patient_id 和 current_hospital_id 更新，\n"
            "  各标签页同步，不再各自维护独立状态\n"
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
    root = tk.Tk()
    app = ThoracicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()




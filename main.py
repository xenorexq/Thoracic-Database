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
from db.importer import import_databases  # 用于后台数据库合并
import threading  # 用于后台线程导入
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
        self.current_patient_id = None
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
        self.current_patient_id = patient_id
        
        # 获取患者信息
        row = self.db.get_patient_by_id(patient_id)
        if row:
            patient_dict = dict(row)
            self.cancer_type = patient_dict.get("cancer_type")
            
            # 加载到各个Tab
            self.patient_tab.load_patient(patient_dict)
            self.surgery_tab.load_patient(patient_id)
            self.path_tab.load_patient(patient_id)
            self.mol_tab.load_patient(patient_id)
            self.fu_tab.load_patient(patient_id)
            
            self.status(f"已加载患者: {patient_dict.get('hospital_id', '')} (ID: {patient_id})")
            
            # 切换到患者/治疗页
            self.notebook.select(0)

    def new_patient(self):
        """新建患者"""
        self.current_patient_id = None
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
        """导入其他数据库并合并新患者数据。

        此功能允许从一个或多个 SQLite 数据库文件中批量导入患者及其所有关联记录。
        导入逻辑仅以患者表 (`Patient`) 的 `hospital_id` 作为唯一标识，
        只有当源库中的住院号在当前数据库不存在时才会导入。
        对于已存在的患者，源库中的手术、病理、分子及随访记录都将被忽略，
        以保护当前库中经过编辑或补充的数据。
        所有耗时的导入操作在后台线程中执行，避免阻塞用户界面。
        """
        from tkinter import filedialog
        source_dbs = filedialog.askopenfilenames(
            title="选择要导入的数据库文件",
            filetypes=[("SQLite数据库", "*.db"), ("所有文件", "*.*")],
        )
        if not source_dbs:
            return

        def run_import(paths):
            """在后台线程中执行导入逻辑。

            注意：SQLite 连接不能跨线程复用，因此这里在工作线程中
            单独打开一个新的 Database 实例（指向同一个 db_path），导入完成
            后再关闭连接，只通过 Tk 的 ``after`` 回到主线程更新界面。
            """

            from db.models import Database  # 局部导入以避免循环依赖

            # 在主线程中更新状态栏
            self.root.after(0, lambda: self.status("正在导入，请稍候..."))

            try:
                # 在当前线程重新打开一个数据库连接
                dest_path = getattr(self.db, "db_path", None)
                thread_db = Database(dest_path)
                try:
                    stats = import_databases(thread_db, paths)
                finally:
                    # 确保工作线程的连接被关闭
                    try:
                        thread_db.conn.close()
                    except Exception:
                        pass

                # 回到主线程显示结果
                def finish():
                    if any(stats.values()):
                        lines = [f"{tbl}: {cnt} 条" for tbl, cnt in stats.items() if cnt > 0]
                        summary = "\n".join(lines)
                        messagebox.showinfo(
                            "导入完成",
                            f"已成功导入以下数据：\n\n{summary}\n\n请刷新患者列表查看。",
                        )
                        self.refresh_patient_list()
                    else:
                        messagebox.showinfo("导入完成", "未找到新数据或所有数据已存在。")
                    self.status("数据库导入完成")

                self.root.after(0, finish)

            except Exception as e:
                # 报错信息在主线程弹框
                def show_err():
                    messagebox.showerror("导入错误", f"导入过程中出错：\n{e}")
                    self.status("导入失败")

                self.root.after(0, show_err)

        # 启动后台线程
        threading.Thread(target=run_import, args=(source_dbs,), daemon=True).start()
    
    def show_about(self):
        """显示关于对话框"""

        about_text = """胸外科科研数据录入系统

版本：v3.2

功能特点：
• 患者信息管理（肺癌/食管癌）
• 手术记录管理
• 病理报告管理
• 分子检测管理
• 随访数据管理（事件驱动）
• 数据导出（Excel/CSV）
• 数据库导入：可以一次选择多个 SQLite 数据库导入新患者，按住院号合并新患者数据并统计导入结果，导入过程在后台线程执行
• 模块化设计：导入逻辑抽离为独立模块，便于维护
• 输入校验：新增住院号格式和日期格式验证，减少录入错误
• 错误日志：导入过程中出现的错误会记录到 importer.log 文件，方便排查问题

开发者信息：
GitHub: xenorexq
邮箱: qinzhi100@gmail.com

© 2025 胸外科科研团队"""
        
        messagebox.showinfo("关于", about_text)


def main():
    root = tk.Tk()
    app = ThoracicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()




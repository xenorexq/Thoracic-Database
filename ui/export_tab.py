"""
Export tab for thoracic entry application.

Provides buttons to export the current patient's data or the entire database
into Excel or CSV files.  Uses tkinter's file and directory dialogs for
destination selection.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading

from db.models import Database
from export.excel import export_patient_to_excel, export_all_to_excel
from export.csv import export_patient_to_csv, export_all_to_csv


class ExportTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "ThoracicApp") -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self.progress_window = None
        self.progress_bar = None
        self._build_widgets()

    def _build_widgets(self) -> None:
        frame = ttk.LabelFrame(self, text="导出")
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        info_label = ttk.Label(
            frame, 
            text="提示：导出使用多线程加速，大数据量时可显著提升性能",
            foreground="blue"
        )
        info_label.pack(pady=5, anchor="w")
        
        ttk.Button(frame, text="导出当前患者 (Excel)", command=self.export_current_excel).pack(pady=3, anchor="w")
        ttk.Button(frame, text="导出当前患者 (CSV)", command=self.export_current_csv).pack(pady=3, anchor="w")
        ttk.Button(frame, text="导出全库 (Excel)", command=self.export_all_excel).pack(pady=3, anchor="w")
        ttk.Button(frame, text="导出全库 (CSV)", command=self.export_all_csv).pack(pady=3, anchor="w")
    
    def show_progress(self, title: str = "导出进度"):
        """显示进度条窗口"""
        if self.progress_window is None or not self.progress_window.winfo_exists():
            self.progress_window = tk.Toplevel(self.app.root)
            self.progress_window.title(title)
            self.progress_window.geometry("400x120")
            self.progress_window.resizable(False, False)
            
            # 居中显示
            self.progress_window.transient(self.app.root)
            self.progress_window.grab_set()
            
            self.progress_label = ttk.Label(
                self.progress_window, 
                text="正在导出数据，请稍候...", 
                font=("Arial", 10)
            )
            self.progress_label.pack(pady=10)
            
            self.progress_bar = ttk.Progressbar(
                self.progress_window, 
                mode='determinate',
                length=350
            )
            self.progress_bar.pack(pady=10)
            self.progress_bar['value'] = 0
            
            self.progress_status = ttk.Label(
                self.progress_window,
                text="0%",
                font=("Arial", 9)
            )
            self.progress_status.pack()
    
    def update_progress(self, value: float):
        """更新进度条的值（0-100）"""
        if self.progress_bar:
            self.progress_bar['value'] = value
            self.progress_status.config(text=f"{int(value)}%")
            self.progress_window.update()
    
    def close_progress(self):
        """关闭进度条窗口"""
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        self.progress_window = None
        self.progress_bar = None

    def export_current_excel(self) -> None:
        """导出当前患者数据到 Excel（后台线程 + 进度条）"""
        if not self.app.current_patient_id:
            messagebox.showerror("错误", "请选择要导出的患者")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
            initialfile=f"patient{self.app.current_patient_id}.xlsx",
        )
        if not path:
            return
        
        def run_export():
            try:
                self.app.root.after(0, lambda: self.show_progress("导出患者 Excel"))
                
                def progress_callback(value):
                    self.app.root.after(0, lambda v=value: self.update_progress(v))
                
                export_patient_to_excel(
                    self.db, 
                    self.app.current_patient_id, 
                    Path(path),
                    progress_callback=progress_callback
                )
                
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda: messagebox.showinfo("成功", f"导出成功: {path}"))
                
            except Exception as e:
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda err=str(e): messagebox.showerror("导出错误", f"导出失败：\n{err}"))
        
        threading.Thread(target=run_export, daemon=True).start()

    def export_current_csv(self) -> None:
        """导出当前患者数据到 CSV（后台线程 + 进度条）"""
        if not self.app.current_patient_id:
            messagebox.showerror("错误", "请选择要导出的患者")
            return
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return
        
        def run_export():
            try:
                self.app.root.after(0, lambda: self.show_progress("导出患者 CSV"))
                
                def progress_callback(value):
                    self.app.root.after(0, lambda v=value: self.update_progress(v))
                
                export_patient_to_csv(
                    self.db, 
                    self.app.current_patient_id, 
                    Path(dir_path),
                    progress_callback=progress_callback
                )
                
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda: messagebox.showinfo("成功", f"CSV 导出完成: {dir_path}"))
                
            except Exception as e:
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda err=str(e): messagebox.showerror("导出错误", f"导出失败：\n{err}"))
        
        threading.Thread(target=run_export, daemon=True).start()

    def export_all_excel(self) -> None:
        """导出全库数据到 Excel（后台线程 + 进度条）"""
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
            initialfile="thoracic_all.xlsx",
        )
        if not path:
            return
        
        def run_export():
            try:
                self.app.root.after(0, lambda: self.show_progress("导出全库 Excel"))
                
                def progress_callback(value):
                    self.app.root.after(0, lambda v=value: self.update_progress(v))
                
                export_all_to_excel(
                    self.db, 
                    Path(path),
                    progress_callback=progress_callback
                )
                
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda: messagebox.showinfo("成功", f"全库导出成功: {path}"))
                
            except Exception as e:
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda err=str(e): messagebox.showerror("导出错误", f"导出失败：\n{err}"))
        
        threading.Thread(target=run_export, daemon=True).start()

    def export_all_csv(self) -> None:
        """导出全库数据到 CSV（后台线程 + 进度条）"""
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return
        
        def run_export():
            try:
                self.app.root.after(0, lambda: self.show_progress("导出全库 CSV"))
                
                def progress_callback(value):
                    self.app.root.after(0, lambda v=value: self.update_progress(v))
                
                export_all_to_csv(
                    self.db, 
                    Path(dir_path),
                    progress_callback=progress_callback
                )
                
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda: messagebox.showinfo("成功", f"全库 CSV 导出完成: {dir_path}"))
                
            except Exception as e:
                self.app.root.after(0, lambda: self.close_progress())
                self.app.root.after(0, lambda err=str(e): messagebox.showerror("导出错误", f"导出失败：\n{err}"))
        
        threading.Thread(target=run_export, daemon=True).start()

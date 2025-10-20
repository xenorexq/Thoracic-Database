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

from db.models import Database
from export.excel import export_patient_to_excel, export_all_to_excel
from export.csv import export_patient_to_csv, export_all_to_csv


class ExportTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "ThoracicApp") -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self._build_widgets()

    def _build_widgets(self) -> None:
        frame = ttk.LabelFrame(self, text="导出")
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(frame, text="导出当前患者 (Excel)", command=self.export_current_excel).pack(pady=3, anchor="w")
        ttk.Button(frame, text="导出当前患者 (CSV)", command=self.export_current_csv).pack(pady=3, anchor="w")
        ttk.Button(frame, text="导出全库 (Excel)", command=self.export_all_excel).pack(pady=3, anchor="w")
        ttk.Button(frame, text="导出全库 (CSV)", command=self.export_all_csv).pack(pady=3, anchor="w")

    def export_current_excel(self) -> None:
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
        export_patient_to_excel(self.db, self.app.current_patient_id, Path(path))
        messagebox.showinfo("成功", f"导出成功: {path}")

    def export_current_csv(self) -> None:
        if not self.app.current_patient_id:
            messagebox.showerror("错误", "请选择要导出的患者")
            return
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return
        export_patient_to_csv(self.db, self.app.current_patient_id, Path(dir_path))
        messagebox.showinfo("成功", f"CSV 导出完成: {dir_path}")

    def export_all_excel(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
            initialfile="thoracic_all.xlsx",
        )
        if not path:
            return
        export_all_to_excel(self.db, Path(path))
        messagebox.showinfo("成功", f"全库导出成功: {path}")

    def export_all_csv(self) -> None:
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return
        export_all_to_csv(self.db, Path(dir_path))
        messagebox.showinfo("成功", f"全库 CSV 导出完成: {dir_path}")

"""
Follow-up tab for thoracic entry application.

Allows recording a single follow-up entry per patient.  If a follow-up entry
exists it is loaded and can be edited; otherwise a new entry can be created.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from db.models import Database
from utils.validators import validate_date6, format_date6


class FollowUpTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "ThoracicApp") -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self._build_widgets()

    def _build_widgets(self) -> None:
        form_frame = ttk.LabelFrame(self, text="随访信息")
        form_frame.pack(fill="both", expand=True, padx=5, pady=5)
        # Row 0: last_visit_date, status
        ttk.Label(form_frame, text="最近随访日期(yymmdd)").grid(row=0, column=0)
        self.last_visit_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.last_visit_var, width=8).grid(row=0, column=1)
        self.last_visit_disp = ttk.Label(form_frame, text="")
        self.last_visit_disp.grid(row=0, column=2)
        self.last_visit_var.trace_add("write", lambda *args: self.last_visit_disp.config(text=format_date6(self.last_visit_var.get())))
        ttk.Label(form_frame, text="状态").grid(row=0, column=3)
        self.status_var = tk.StringVar()
        status_cb = ttk.Combobox(
            form_frame,
            textvariable=self.status_var,
            values=["生存", "死亡", "失访"],
            state="readonly",
            width=6,
        )
        status_cb.grid(row=0, column=4)
        # Row 1: death_date (only when status=死亡)
        ttk.Label(form_frame, text="死亡日期 (yymmdd)").grid(row=1, column=0)
        self.death_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.death_var, width=8).grid(row=1, column=1)
        self.death_disp = ttk.Label(form_frame, text="")
        self.death_disp.grid(row=1, column=2)
        self.death_var.trace_add("write", lambda *args: self.death_disp.config(text=format_date6(self.death_var.get())))
        # Row 2: relapse
        self.relapse_var = tk.IntVar()
        ttk.Checkbutton(form_frame, text="复发", variable=self.relapse_var).grid(row=2, column=0)
        ttk.Label(form_frame, text="复发日期 (yymmdd)").grid(row=2, column=1)
        self.relapse_date_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.relapse_date_var, width=8).grid(row=2, column=2)
        self.relapse_date_disp = ttk.Label(form_frame, text="")
        self.relapse_date_disp.grid(row=2, column=3)
        self.relapse_date_var.trace_add("write", lambda *args: self.relapse_date_disp.config(text=format_date6(self.relapse_date_var.get())))
        ttk.Label(form_frame, text="复发部位").grid(row=2, column=4)
        self.relapse_site_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.relapse_site_var, width=15).grid(row=2, column=5)
        # Row 3: os, dfs
        ttk.Label(form_frame, text="OS(月)").grid(row=3, column=0)
        self.os_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.os_var, width=6).grid(row=3, column=1)
        ttk.Label(form_frame, text="DFS(月)").grid(row=3, column=2)
        self.dfs_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.dfs_var, width=6).grid(row=3, column=3)
        # Notes
        ttk.Label(form_frame, text="备注").grid(row=4, column=0, sticky="e")
        self.notes_text = tk.Text(form_frame, width=80, height=3)
        self.notes_text.grid(row=4, column=1, columnspan=5, sticky="w")
        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=6, pady=5)
        ttk.Button(btn_frame, text="保存/更新", command=self.save_record).pack(side="left", padx=2)
        # 刷新按钮：重新加载当前患者的随访记录
        ttk.Button(btn_frame, text="刷新", command=lambda: self.load_patient(self.app.current_patient_id)).pack(side="left", padx=2)
        # 清空按钮放置在刷新按钮之后
        ttk.Button(btn_frame, text="清空", command=self.clear_form).pack(side="left", padx=2)

    def load_patient(self, patient_id: Optional[int]) -> None:
        self.clear_form()
        if not patient_id:
            return
        row = self.db.get_followup(patient_id)
        if not row:
            return
        self.last_visit_var.set(row.get("last_visit_date") or "")
        self.status_var.set(row.get("status") or "")
        self.death_var.set(row.get("death_date") or "")
        self.relapse_var.set(row.get("relapse") or 0)
        self.relapse_date_var.set(row.get("relapse_date") or "")
        self.relapse_site_var.set(row.get("relapse_site") or "")
        self.os_var.set(str(row.get("os_months_optional") or ""))
        self.dfs_var.set(str(row.get("dfs_months_optional") or ""))
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, row.get("notes_fu") or "")

    def clear_form(self) -> None:
        self.last_visit_var.set("")
        self.status_var.set("")
        self.death_var.set("")
        self.relapse_var.set(0)
        self.relapse_date_var.set("")
        self.relapse_site_var.set("")
        self.os_var.set("")
        self.dfs_var.set("")
        self.notes_text.delete("1.0", tk.END)

    def save_record(self) -> None:
        if not self.app.current_patient_id:
            messagebox.showerror("错误", "请先选择或保存患者")
            return
        # Validate dates
        for name, value in [("最近随访日期", self.last_visit_var.get()), ("死亡日期", self.death_var.get()), ("复发日期", self.relapse_date_var.get())]:
            if value:
                ok, msg = validate_date6(value)
                if not ok:
                    messagebox.showerror("错误", f"{name}: {msg}")
                    return
        data = {
            "last_visit_date": self.last_visit_var.get() or None,
            "status": self.status_var.get() or None,
            "death_date": self.death_var.get() or None,
            "relapse": self.relapse_var.get(),
            "relapse_date": self.relapse_date_var.get() or None,
            "relapse_site": self.relapse_site_var.get() or None,
            "os_months_optional": float(self.os_var.get()) if self.os_var.get() else None,
            "dfs_months_optional": float(self.dfs_var.get()) if self.dfs_var.get() else None,
            "notes_fu": self.notes_text.get("1.0", tk.END).strip() or None,
        }
        try:
            self.db.insert_or_update_followup(self.app.current_patient_id, data)
            messagebox.showinfo("成功", "随访记录已保存")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ----- Wrapper methods for main application -----
    def save_followup(self) -> None:
        """
        保存随访记录的代理方法，便于 main.py 调用。
        """
        self.save_record()

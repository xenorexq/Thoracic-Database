"""
Surgery tab for thoracic entry application.

This module defines the ``SurgeryTab`` class, which handles data entry for
patient surgeries.  A tree view lists existing surgeries, and a form allows
creating or editing a single record.  The form dynamically shows either the
lung-specific or esophageal-specific fields depending on the patient's cancer
type.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from db.models import Database
from utils.validators import validate_date6, validate_hhmm, compute_duration, format_date6


class SurgeryTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "ThoracicApp") -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self.current_surgery_id: Optional[int] = None
        self.cancer_type: str = ""
        self._build_widgets()

    def _build_widgets(self) -> None:
        # Top list of surgeries
        list_frame = ttk.LabelFrame(self, text="手术列表")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        # v2.16: 新增序号列，每位患者内独立编号
        columns = ["seq", "date", "indication", "duration_min"]
        # 限制列表高度为3行，避免占用过多垂直空间
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse", height=3)
        self.tree.heading("seq", text="序号")
        self.tree.heading("date", text="日期")
        self.tree.heading("indication", text="手术适应症")
        self.tree.heading("duration_min", text="时长(分钟)")
        self.tree.column("seq", width=60, anchor="center")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("indication", width=150, anchor="w")
        self.tree.column("duration_min", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # 右键菜单：删除当前手术记录
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="删除当前手术记录", command=self.delete_record)
        # 绑定鼠标右键事件，仅在点击有效条目时显示菜单
        self.tree.bind("<Button-3>", self._on_right_click)

        # Form frame
        form_frame = ttk.LabelFrame(self, text="手术明细")
        form_frame.pack(fill="both", expand=False, padx=5, pady=5)
        # Row 0: date, indication
        ttk.Label(form_frame, text="日期 (yymmdd)*").grid(row=0, column=0, sticky="e")
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(form_frame, textvariable=self.date_var, width=8)
        self.date_entry.grid(row=0, column=1)
        self.date_display = ttk.Label(form_frame, text="")
        self.date_display.grid(row=0, column=2)
        self.date_var.trace_add("write", lambda *args: self._update_date_display())

        ttk.Label(form_frame, text="适应症").grid(row=0, column=3, sticky="e")
        self.indication_var = tk.StringVar()
        self.indication_cb = ttk.Combobox(
            form_frame,
            textvariable=self.indication_var,
            values=["原发治疗", "复发切除", "诊断性探查", "其他"],
            state="readonly",
            width=10,
        )
        self.indication_cb.grid(row=0, column=4)
        self.indication_var.set("原发治疗")

        # Row 1: planned, completed, start, end, duration
        self.planned_var = tk.IntVar(value=1)
        ttk.Checkbutton(form_frame, text="计划", variable=self.planned_var).grid(row=1, column=0)
        self.completed_var = tk.IntVar(value=1)
        ttk.Checkbutton(form_frame, text="完成", variable=self.completed_var).grid(row=1, column=1)
        ttk.Label(form_frame, text="开始时间 (hhmm)").grid(row=1, column=2)
        self.start_var = tk.StringVar()
        self.start_entry = ttk.Entry(form_frame, textvariable=self.start_var, width=6)
        self.start_entry.grid(row=1, column=3)
        ttk.Label(form_frame, text="结束 (hhmm)").grid(row=1, column=4)
        self.end_var = tk.StringVar()
        self.end_entry = ttk.Entry(form_frame, textvariable=self.end_var, width=6)
        self.end_entry.grid(row=1, column=5)
        self.start_var.trace_add("write", lambda *args: self._update_duration())
        self.end_var.trace_add("write", lambda *args: self._update_duration())
        # Row 2: 时长移到开始时间下方
        ttk.Label(form_frame, text="时长 (min)").grid(row=2, column=2)
        self.duration_var = tk.StringVar()
        self.duration_label = ttk.Label(form_frame, textvariable=self.duration_var)
        self.duration_label.grid(row=2, column=3)

        self.ln_dissect_var = tk.IntVar(value=1)
        ttk.Checkbutton(form_frame, text="淋巴清扫", variable=self.ln_dissect_var).grid(row=3, column=0)
        self.r0_var = tk.IntVar(value=1)
        ttk.Checkbutton(form_frame, text="R0", variable=self.r0_var).grid(row=3, column=1)

        # Lung-specific frame
        self.lung_frame = ttk.LabelFrame(form_frame, text="肺癌手术细节")
        self.lung_frame.grid(row=4, column=0, columnspan=8, sticky="nsew", padx=5, pady=5)
        ttk.Label(self.lung_frame, text="手术方式").grid(row=0, column=0)
        self.approach_var = tk.StringVar()
        # 调整手术方式顺序，将“胸腔镜”移动到第一位
        self.approach_cb = ttk.Combobox(
            self.lung_frame,
            textvariable=self.approach_var,
            values=["胸腔镜", "开胸", "机器人"],
            state="readonly",
            width=10,
        )
        self.approach_cb.grid(row=0, column=1)
        ttk.Label(self.lung_frame, text="切除范围").grid(row=0, column=2)
        self.scope_var = tk.StringVar()
        self.scope_cb = ttk.Combobox(
            self.lung_frame,
            textvariable=self.scope_var,
            values=["楔形切除", "解剖性肺段切除", "肺叶切除", "复合肺叶切除", "全肺切除"],
            state="readonly",
            width=16,
        )
        self.scope_cb.grid(row=0, column=3)
        ttk.Label(self.lung_frame, text="肺叶").grid(row=0, column=4)
        self.lobe_var = tk.StringVar()
        self.lobe_cb = ttk.Combobox(
            self.lung_frame,
            textvariable=self.lobe_var,
            values=["", "上叶", "中叶", "下叶", "多发"],
            state="readonly",
            width=8,
        )
        self.lobe_cb.grid(row=0, column=5)
        # 添加左和右打勾框
        self.left_var = tk.IntVar()
        ttk.Checkbutton(self.lung_frame, text="左", variable=self.left_var).grid(row=0, column=6)
        self.right_var = tk.IntVar()
        ttk.Checkbutton(self.lung_frame, text="右", variable=self.right_var).grid(row=0, column=7)
        self.bilateral_var = tk.IntVar()
        ttk.Checkbutton(self.lung_frame, text="双侧", variable=self.bilateral_var).grid(row=0, column=8)
        ttk.Label(self.lung_frame, text="病灶数").grid(row=1, column=0)
        self.lesion_count_var = tk.StringVar()
        self.lesion_count_entry = ttk.Entry(self.lung_frame, textvariable=self.lesion_count_var, width=5)
        self.lesion_count_entry.grid(row=1, column=1)
        ttk.Label(self.lung_frame, text="主病灶尺寸 (cm)").grid(row=1, column=2)
        self.main_size_var = tk.StringVar()
        self.main_size_entry = ttk.Entry(self.lung_frame, textvariable=self.main_size_var, width=6)
        self.main_size_entry.grid(row=1, column=3)

        # Esophageal-specific frame
        self.eso_frame = ttk.LabelFrame(form_frame, text="食管手术细节")
        self.eso_frame.grid(row=5, column=0, columnspan=8, sticky="nsew", padx=5, pady=5)
        ttk.Label(self.eso_frame, text="部位").grid(row=0, column=0)
        # 食管手术细节的部位改为下拉框，可选“食管”或“贲门”。
        self.eso_site_var = tk.StringVar()
        self.eso_site_cb = ttk.Combobox(
            self.eso_frame,
            textvariable=self.eso_site_var,
            values=["食管", "贲门"],
            state="readonly",
            width=10,
        )
        self.eso_site_cb.grid(row=0, column=1)

        # Notes
        # 调整备注输入框的位置：向右移动一列，使布局更居中。
        ttk.Label(form_frame, text="备注").grid(row=5, column=1, sticky="e")
        # Notes text width reduced to improve layout (originally 80 columns). Reduce by approximately one third.
        self.notes_text = tk.Text(form_frame, width=50, height=3)
        # 放置在第2列，减少宽度并向右移动。columnspan 相应减少一列
        self.notes_text.grid(row=5, column=2, columnspan=6, sticky="w")

        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=6, column=0, columnspan=8, pady=5)
        ttk.Button(btn_frame, text="新建", command=self.new_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="保存", command=self.save_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_record).pack(side="left", padx=2)
        # 刷新按钮：重新加载当前患者的手术记录
        ttk.Button(btn_frame, text="刷新", command=lambda: self.load_patient(self.app.current_patient_id)).pack(side="left", padx=2)
        # 清空按钮：重置当前表单为缺省值
        ttk.Button(btn_frame, text="清空", command=self.new_record).pack(side="left", padx=2)

    # Utility updates
    def _update_date_display(self) -> None:
        self.date_display.config(text=format_date6(self.date_var.get()))

    def _update_duration(self) -> None:
        dur = compute_duration(self.start_var.get(), self.end_var.get())
        self.duration_var.set(str(dur) if dur is not None else "")

    def set_cancer_type(self, cancer_type: str) -> None:
        self.cancer_type = cancer_type
        if cancer_type == "肺癌":
            self.lung_frame.grid()
            self.eso_frame.grid_remove()
        elif cancer_type == "食管癌":
            self.eso_frame.grid()
            self.lung_frame.grid_remove()
        else:
            self.lung_frame.grid_remove()
            self.eso_frame.grid_remove()

    def load_patient(self, patient_id: Optional[int]) -> None:
        """Populate the surgery list for the given patient."""
        self.current_surgery_id = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not patient_id:
            return
        surgeries = self.db.get_surgeries_by_patient(patient_id)
        # v2.13: 按日期降序排列（最近的在上）
        surgeries_sorted = sorted(surgeries, key=lambda x: dict(x).get("surgery_date6") or "", reverse=True)
        for seq, s in enumerate(surgeries_sorted, 1):
            s_dict = dict(s)  # 转换为字典
            raw_date = s_dict.get("surgery_date6")
            date_disp = ""
            if raw_date:
                raw_str = str(raw_date)
                if len(raw_str) == 6 and raw_str.isdigit():
                    date_disp = format_date6(raw_str)
                elif len(raw_str) == 8 and raw_str.isdigit():
                    date_disp = f"{raw_str[:4]}-{raw_str[4:6]}-{raw_str[6:]}"
                else:
                    date_disp = raw_str
            # v2.16: 增加每位患者内的序号列
            self.tree.insert(
                "",
                tk.END,
                iid=s_dict["surgery_id"],
                values=(seq, date_disp, s_dict.get("indication"), s_dict.get("duration_min")),
            )
        # Automatically select and load the first record if available
        children = self.tree.get_children()
        if children:
            first = children[0]
            self.tree.selection_set(first)
            try:
                self.load_record(int(first))
            except Exception as e:
                # 记录错误但不阻断程序运行
                print(f"Warning: Failed to load surgery record: {e}")

    def _on_tree_select(self, event) -> None:
        sel = self.tree.selection()
        if sel:
            self.load_record(int(sel[0]))

    def _on_right_click(self, event) -> None:
        """右键点击手术列表时弹出删除菜单。"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # 选中右键所在行
        self.tree.selection_set(item)
        # 仅在选中记录时显示菜单
        if self.current_surgery_id or self.tree.selection():
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def load_record(self, surgery_id: int) -> None:
        row = self.db.conn.execute("SELECT * FROM Surgery WHERE surgery_id=?", (surgery_id,)).fetchone()
        if not row:
            return
        row = dict(row)  # 转换为字典
        self.current_surgery_id = surgery_id
        self.date_var.set(row.get("surgery_date6") or "")
        self.indication_var.set(row.get("indication") or "原发治疗")
        self.planned_var.set(row.get("planned") or 1)
        self.completed_var.set(row.get("completed") or 1)
        self.start_var.set(f"{row.get('start_hhmm'):04d}" if row.get("start_hhmm") is not None else "")
        self.end_var.set(f"{row.get('end_hhmm'):04d}" if row.get("end_hhmm") is not None else "")
        self.duration_var.set(str(row.get("duration_min") or ""))
        self.ln_dissect_var.set(row.get("ln_dissection") or 1)
        self.r0_var.set(row.get("r0") or 1)
        self.approach_var.set(row.get("approach") or "")
        self.scope_var.set(row.get("scope_lung") or "")
        self.lobe_var.set(row.get("lobe") or "")
        self.left_var.set(row.get("left_side") or 0)
        self.right_var.set(row.get("right_side") or 0)
        self.bilateral_var.set(row.get("bilateral") or 0)
        self.lesion_count_var.set(str(row.get("lesion_count") or ""))
        self.main_size_var.set(str(row.get("main_lesion_size_cm") or ""))
        self.eso_site_var.set(row.get("esophagus_site") or "")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, row.get("notes_surgery") or "")

    def new_record(self) -> None:
        self.current_surgery_id = None
        self.date_var.set("")
        self.indication_var.set("原发治疗")
        self.planned_var.set(1)
        self.completed_var.set(1)
        self.start_var.set("")
        self.end_var.set("")
        self.duration_var.set("")
        self.ln_dissect_var.set(1)
        self.r0_var.set(1)
        self.approach_var.set("")
        self.scope_var.set("")
        self.lobe_var.set("")
        self.left_var.set(0)
        self.right_var.set(0)
        self.bilateral_var.set(0)
        self.lesion_count_var.set("")
        self.main_size_var.set("")
        self.eso_site_var.set("")
        self.notes_text.delete("1.0", tk.END)

    def save_record(self) -> None:
        if not self.app.current_patient_id:
            messagebox.showerror("错误", "请先选择或保存患者")
            return
        date6 = self.date_var.get().strip()
        ok, msg = validate_date6(date6)
        if not ok:
            messagebox.showerror("错误", msg)
            return
        if self.start_var.get():
            ok, msg = validate_hhmm(self.start_var.get())
            if not ok:
                messagebox.showerror("错误", f"开始时间 {msg}")
                return
        if self.end_var.get():
            ok, msg = validate_hhmm(self.end_var.get())
            if not ok:
                messagebox.showerror("错误", f"结束时间: {msg}")
                return
        dur = compute_duration(self.start_var.get(), self.end_var.get()) if self.start_var.get() and self.end_var.get() else None
        data = {
            "cancer_type": self.app.cancer_type or self.cancer_type,
            "surgery_date6": date6,
            "indication": self.indication_var.get() or None,
            "planned": self.planned_var.get(),
            "completed": self.completed_var.get(),
            "start_hhmm": int(self.start_var.get()) if self.start_var.get() else None,
            "end_hhmm": int(self.end_var.get()) if self.end_var.get() else None,
            "duration_min": dur,
            "ln_dissection": self.ln_dissect_var.get(),
            "r0": self.r0_var.get(),
            "approach": self.approach_var.get() or None,
            "scope_lung": self.scope_var.get() or None,
            "lobe": self.lobe_var.get() or None,
            "left_side": self.left_var.get(),
            "right_side": self.right_var.get(),
            "bilateral": self.bilateral_var.get(),
            "lesion_count": int(self.lesion_count_var.get()) if self.lesion_count_var.get() else None,
            "main_lesion_size_cm": float(self.main_size_var.get()) if self.main_size_var.get() else None,
            "esophagus_site": self.eso_site_var.get() or None,
            "notes_surgery": self.notes_text.get("1.0", tk.END).strip() or None,
        }
        try:
            if self.current_surgery_id is None:
                new_id = self.db.insert_surgery(self.app.current_patient_id, data)
                messagebox.showinfo("成功", f"手术记录已添加 (ID={new_id})")
            else:
                self.db.update_surgery(self.current_surgery_id, data)
                messagebox.showinfo("成功", "手术记录已更新")
            self.load_patient(self.app.current_patient_id)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def delete_record(self) -> None:
        """删除当前手术记录，删除前进行两次确认。"""
        if not self.current_surgery_id:
            return
        # 第一次确认
        if not messagebox.askyesno("确认删除", "确定删除当前手术记录吗？"):
            return
        # 第二次确认
        if not messagebox.askyesno("再次确认", "删除后不可恢复，是否继续？"):
            return
        try:
            self.db.delete_surgery(self.current_surgery_id)
            messagebox.showinfo("成功", "手术记录已删除")
            self.current_surgery_id = None
            self.load_patient(self.app.current_patient_id)
            self.new_record()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ----- Wrapper methods for main application -----
    def save_surgery(self) -> None:
        """
        保存手术记录的代理方法，使 main.py 可以统一调用。
        """
        self.save_record()

    def clear_form(self) -> None:
        """
        清空表单（等同于新建记录）。
        """
        self.new_record()

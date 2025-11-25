"""
Molecular tab for thoracic entry application.

Allows entry of molecular test results per patient.  Multiple entries may be
recorded.  Includes basic fields for platform, vendor lab, gene, variant,
PD-L1 percentage, TMB/MSI result, and test date.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from db.models import Database
from utils.validators import validate_date6, format_date6


class MolecularTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "ThoracicApp") -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        # 当前分子记录主键，用于区分新增与编辑状态
        self.current_record_id: Optional[int] = None
        self._build_widgets()

    def _build_widgets(self) -> None:
        list_frame = ttk.LabelFrame(self, text="分子列表")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        # v3.5: 列表改为“住院号 + 日期”，不再使用序号列
        columns = ["hospital_id", "date", "platform", "gene", "variant", "seq"]
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        # 设置列标题为中文
        self.tree.heading("hospital_id", text="住院号")
        self.tree.heading("date", text="日期")
        self.tree.heading("platform", text="平台")
        self.tree.heading("gene", text="基因")
        self.tree.heading("variant", text="突变")
        self.tree.heading("seq", text="序号")
        # 设置列宽
        self.tree.column("hospital_id", width=100, anchor="center")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("platform", width=100, anchor="center")
        self.tree.column("gene", width=120, anchor="center")
        self.tree.column("variant", width=200, anchor="w")
        self.tree.column("seq", width=50, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # 右键菜单：删除当前分子记录
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="删除当前分子记录", command=self.delete_record)
        # 绑定鼠标右键事件，仅在点击有效条目时显示菜单
        self.tree.bind("<Button-3>", self._on_right_click)

        # Form frame for molecular test details
        form_frame = ttk.LabelFrame(self, text="分子检测明细")
        form_frame.pack(fill="both", expand=False, padx=5, pady=5)
        # Row 0: platform, vendor_lab
        ttk.Label(form_frame, text="平台").grid(row=0, column=0)
        self.platform_var = tk.StringVar()
        # Include CTC and METHYLATION platforms
        self.platform_cb = ttk.Combobox(
            form_frame,
            textvariable=self.platform_var,
            values=["PCR", "NGS", "CTC", "METHYLATION", "免疫组化"],
            state="readonly",
            width=10,
        )
        self.platform_cb.grid(row=0, column=1)
        # Bind platform change to show/hide dynamic fields
        self.platform_cb.bind("<<ComboboxSelected>>", lambda e: self._on_platform_change())
        # 删除“检测机构”选项，根据最新需求不再收集检测机构信息。
        # 保留原来使用的列结构，但不放置任何控件，避免布局错乱。
        # 第0行的第2列和第3列将空出，以保持其余控件的位置。
        # Row 1: gene, variant
        ttk.Label(form_frame, text="基因").grid(row=1, column=0)
        self.gene_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.gene_var, width=15).grid(row=1, column=1)
        ttk.Label(form_frame, text="突变").grid(row=1, column=2)
        self.variant_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.variant_var, width=15).grid(row=1, column=3)
        # Row 2: PD-L1, TMB/MSI
        ttk.Label(form_frame, text="PD-L1 (%)").grid(row=2, column=0)
        self.pdl1_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.pdl1_var, width=10).grid(row=2, column=1)
        ttk.Label(form_frame, text="TMB/MSI").grid(row=2, column=2)
        self.tmb_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.tmb_var, width=15).grid(row=2, column=3)
        # Row 3: test date
        # Row 3: dynamic fields for CTC and methylation
        ttk.Label(form_frame, text="CTC计数").grid(row=3, column=0)
        self.ctc_count_var = tk.StringVar()
        self.ctc_entry = ttk.Entry(form_frame, textvariable=self.ctc_count_var, width=10)
        self.ctc_entry.grid(row=3, column=1)
        ttk.Label(form_frame, text="甲基化结果").grid(row=3, column=2)
        self.methylation_var = tk.StringVar()
        self.methylation_cb = ttk.Combobox(
            form_frame,
            textvariable=self.methylation_var,
            values=["", "阴", "阳"],
            state="readonly",
            width=8,
        )
        self.methylation_cb.grid(row=3, column=3)
        # Hide dynamic fields initially
        self.ctc_entry.grid_remove()
        self.methylation_cb.grid_remove()
        # Row 4: test date
        ttk.Label(form_frame, text="检测日期(yymmdd)").grid(row=4, column=0)
        self.test_date_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.test_date_var, width=8).grid(row=4, column=1)
        self.test_date_disp = ttk.Label(form_frame, text="")
        self.test_date_disp.grid(row=4, column=2)
        self.test_date_var.trace_add("write", lambda *args: self.test_date_disp.config(text=format_date6(self.test_date_var.get())))
        # Notes
        ttk.Label(form_frame, text="备注").grid(row=5, column=0, sticky="e")
        self.notes_text = tk.Text(form_frame, width=80, height=3)
        self.notes_text.grid(row=5, column=1, columnspan=3, sticky="w")
        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=6, column=0, columnspan=4, pady=5)
        ttk.Button(btn_frame, text="新建", command=self.new_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="保存", command=self.save_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_record).pack(side="left", padx=2)
        # 刷新按钮：重新加载当前患者的分子记录
        ttk.Button(btn_frame, text="刷新", command=lambda: self.load_patient(self.app.current_patient_id)).pack(side="left", padx=2)
        # 清空按钮：重置当前表单为缺省值
        ttk.Button(btn_frame, text="清空", command=self.new_record).pack(side="left", padx=2)

    def _on_platform_change(self) -> None:
        """Show or hide dynamic fields based on selected platform."""
        plat = self.platform_var.get()
        if plat == "CTC":
            # show CTC count, hide methylation
            self.ctc_entry.grid()
            self.methylation_cb.grid_remove()
        elif plat == "METHYLATION":
            # show methylation result, hide CTC count
            self.ctc_entry.grid_remove()
            self.methylation_cb.grid()
        else:
            # hide both for PCR/NGS
            self.ctc_entry.grid_remove()
            self.methylation_cb.grid_remove()

    def load_patient(self, patient_id: Optional[int]) -> None:
        # 切换患者时清除当前记录 ID
        self.current_record_id = None
        # 清空现有列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not patient_id:
            return
        # 根据患者ID查询分子记录
        moleculars = self.db.get_molecular_by_patient(patient_id)
        
        # 先按日期正序排列并生成序号
        moleculars_asc = sorted(
            moleculars,
            key=lambda x: dict(x).get("test_date") or "",
        )
        indexed_moleculars = []
        for idx, m in enumerate(moleculars_asc, 1):
            m_dict = dict(m)
            m_dict["_seq"] = idx
            indexed_moleculars.append(m_dict)
            
        # 按检测日期降序排列（最近的在上）
        moleculars_sorted = sorted(
            indexed_moleculars,
            key=lambda x: x.get("test_date") or "",
            reverse=True,
        )
        for m_dict in moleculars_sorted:
            # 转换日期显示
            test_date = m_dict.get("test_date")
            date_disp = ""
            if test_date:
                raw_str = str(test_date)
                if len(raw_str) == 6 and raw_str.isdigit():
                    date_disp = format_date6(raw_str)
                elif len(raw_str) == 8 and raw_str.isdigit():
                    date_disp = f"{raw_str[:4]}-{raw_str[4:6]}-{raw_str[6:]}"
                else:
                    date_disp = raw_str
            platform = m_dict.get("platform") or ""
            # 第一列显示住院号
            hosp_id = self.app.current_hospital_id or ""
            self.tree.insert(
                "",
                tk.END,
                iid=m_dict["mol_id"],
                values=(
                    hosp_id,
                    date_disp,
                    platform,
                    m_dict.get("gene"),
                    m_dict.get("variant"),
                    m_dict.get("_seq"),
                ),
            )
        # 自动选择并加载第一条记录以便显示明细
        children = self.tree.get_children()
        if children:
            first = children[0]
            self.tree.selection_set(first)
            try:
                # Treeview iid 为记录主键
                self.load_record(int(first))
            except Exception as e:
                # 记录错误但不阻断程序运行
                print(f"Warning: Failed to load molecular record: {e}")

    def _on_right_click(self, event) -> None:
        """右键点击树形列表时弹出删除菜单。"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # 选中右键所在的行
        self.tree.selection_set(item)
        # 仅在有选中记录时显示菜单
        if self.current_record_id or self.tree.selection():
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def _on_tree_select(self, event) -> None:
        sel = self.tree.selection()
        if sel:
            # Treeview iid 即为记录主键
            self.load_record(int(sel[0]))

    def load_record(self, record_id: int) -> None:
        row = self.db.conn.execute("SELECT * FROM Molecular WHERE mol_id=?", (record_id,)).fetchone()
        if not row:
            return
        row = dict(row)  # 转换为字典
        # 更新当前记录 ID
        self.current_record_id = record_id
        self.platform_var.set(row.get("platform") or "")
        self.gene_var.set(row.get("gene") or "")
        self.variant_var.set(row.get("variant") or "")
        self.pdl1_var.set(str(row.get("pdl1_percent") or ""))
        self.tmb_var.set(row.get("tmb_msi") or "")
        self.ctc_count_var.set(str(row.get("ctc_count") or ""))
        self.methylation_var.set(row.get("methylation_result") or "")
        self.test_date_var.set(row.get("test_date") or "")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, row.get("notes_mol") or "")
        # show/hide dynamic fields based on platform
        self._on_platform_change()

    def new_record(self) -> None:
        # 新建/清空记录时清空当前记录 ID
        self.current_record_id = None
        self.platform_var.set("")
        self.gene_var.set("")
        self.variant_var.set("")
        self.pdl1_var.set("")
        self.tmb_var.set("")
        self.ctc_count_var.set("")
        self.methylation_var.set("")
        self.test_date_var.set("")
        # hide dynamic fields when clearing
        self.ctc_entry.grid_remove()
        self.methylation_cb.grid_remove()
        self.notes_text.delete("1.0", tk.END)

    def save_record(self) -> None:
        if not self.app.current_patient_id:
            messagebox.showerror("错误", "请先选择或保存患者")
            return
        date6 = self.test_date_var.get().strip()
        # validate date if provided
        if date6:
            ok, msg = validate_date6(date6)
            if not ok:
                messagebox.showerror("错误", msg)
                return
        # 安全的类型转换函数
        def safe_float(value, field_name=""):
            if not value:
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValueError(f"字段【{field_name}】'{value}' 不是有效的数字")
        
        def safe_int(value, field_name=""):
            if not value:
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValueError(f"字段【{field_name}】'{value}' 不是有效的整数")
        
        # build data dict with dynamic fields
        try:
            data = {
                "platform": self.platform_var.get() or None,
                # 根据最新需求，不再保存检测机构信息（vendor_lab）。如果更新旧记录，不提供 vendor_lab 字段即可保持原值。
                "gene": self.gene_var.get() or None,
                "variant": self.variant_var.get() or None,
                "pdl1_percent": safe_float(self.pdl1_var.get(), "PD-L1百分比"),
                "tmb_msi": self.tmb_var.get() or None,
                "test_date": date6 or None,
                "notes_mol": self.notes_text.get("1.0", tk.END).strip() or None,
            }
            # include CTC or methylation results depending on platform
            plat = self.platform_var.get()
            if plat == "CTC":
                # convert to int if possible
                cnt = self.ctc_count_var.get().strip()
                data["ctc_count"] = safe_int(cnt, "CTC计数")
                data["methylation_result"] = None
            elif plat == "METHYLATION":
                data["ctc_count"] = None
                data["methylation_result"] = self.methylation_var.get() or None
            else:
                data["ctc_count"] = None
                data["methylation_result"] = None
        except ValueError as ve:
            messagebox.showerror("数据格式错误", str(ve))
            return
        
        try:
            # 根据当前记录 ID 决定新增或更新
            if self.current_record_id is None:
                new_id = self.db.insert_molecular(self.app.current_patient_id, data)
                messagebox.showinfo("成功", f"分子记录已添加 (ID={new_id})")
            else:
                # 编辑现有记录时，保留孤儿字段（UI中没有输入框的字段）的原值
                # 这样可以避免编辑后导致旧数据丢失
                try:
                    old_row = self.db.conn.execute(
                        "SELECT genes_tested, result_summary FROM Molecular WHERE mol_id=?",
                        (self.current_record_id,)
                    ).fetchone()
                    if old_row:
                        old_dict = dict(old_row)
                        # 保留原有的 genes_tested 和 result_summary
                        if old_dict.get("genes_tested") is not None:
                            data["genes_tested"] = old_dict["genes_tested"]
                        if old_dict.get("result_summary") is not None:
                            data["result_summary"] = old_dict["result_summary"]
                except Exception as e:
                    # 如果获取旧值失败，继续保存（不影响主流程）
                    print(f"Warning: Failed to preserve orphan fields: {e}")
                
                self.db.update_molecular(self.current_record_id, data)
                messagebox.showinfo("成功", "分子记录已更新")
            # 保存完成后刷新列表
            self.load_patient(self.app.current_patient_id)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def delete_record(self) -> None:
        """删除当前分子记录，删除前进行两次确认。"""
        if not self.current_record_id:
            return
        # 第一次确认
        if not messagebox.askyesno("确认删除", "确定删除当前分子记录吗？"):
            return
        # 第二次确认
        if not messagebox.askyesno("再次确认", "删除后不可恢复，是否继续？"):
            return
        try:
            # 删除指定记录
            self.db.delete_molecular(self.current_record_id)
            messagebox.showinfo("成功", "分子记录已删除")
            # 清除当前记录 ID 并刷新列表
            self.current_record_id = None
            self.load_patient(self.app.current_patient_id)
            self.new_record()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ----- Wrapper methods for main application -----
    def save_molecular(self) -> None:
        """保存分子记录的代理方法，便于 main.py 调用"""
        self.save_record()

    def clear_form(self) -> None:
        """清空表单（等同于新建记录）。"""
        self.new_record()

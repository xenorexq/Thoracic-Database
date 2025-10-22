"""
Pathology tab for thoracic entry application.

Provides a list and form for entering pathology reports for a patient.  Users
can create, edit, and delete multiple pathology records.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from db.models import Database
from utils.validators import validate_date6, format_date6


class PathologyTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "ThoracicApp") -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self.current_path_id: Optional[int] = None
        self._build_widgets()

    def _build_widgets(self) -> None:
        list_frame = ttk.LabelFrame(self, text="病理列表")
        list_frame.pack(fill="x", expand=False, padx=5, pady=5)
        # 列：ID、病理号、组织学、标本类型
        # 按要求删除分期列，改为标本类型列
        columns = ["path_id", "pathology_no", "histology", "specimen_type"]
        # 将列表高度限制为3行，以便下面的表单区域更容易显示完整内容
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=3,
        )
        # 标题设置为中文
        self.tree.heading("path_id", text="ID")
        self.tree.heading("pathology_no", text="病理号")
        self.tree.heading("histology", text="组织学")
        self.tree.heading("specimen_type", text="标本类型")
        # 列宽统一并居中
        for col in columns:
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="x", expand=False)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # 添加右键菜单用于删除病理记录
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="删除当前病理记录", command=self.delete_record)
        self.tree.bind("<Button-3>", self._on_right_click)

        form_frame = ttk.LabelFrame(self, text="病理明细")
        form_frame.pack(fill="both", expand=False, padx=5, pady=5)
        # Row 0: specimen_type, histology, differentiation
        ttk.Label(form_frame, text="标本类型").grid(row=0, column=0)
        self.specimen_var = tk.StringVar()
        # 标本类型改为下拉框：术前活检、手术病理、复发活检
        self.specimen_cb = ttk.Combobox(
            form_frame,
            textvariable=self.specimen_var,
            values=["术前活检", "手术病理", "复发活检"],
            state="readonly",
            width=12,
        )
        self.specimen_cb.grid(row=0, column=1)
        ttk.Label(form_frame, text="组织学").grid(row=0, column=2)
        self.histology_var = tk.StringVar()
        # 组织学改为下拉框：腺癌、鳞癌、小细胞癌、其他
        self.histology_cb = ttk.Combobox(
            form_frame,
            textvariable=self.histology_var,
            values=["腺癌", "鳞癌", "小细胞癌", "其他"],
            state="readonly",
            width=12,
        )
        self.histology_cb.grid(row=0, column=3)
        ttk.Label(form_frame, text="分化").grid(row=0, column=4)
        self.diff_var = tk.StringVar()
        # 分化改为下拉框：高、中、低
        self.diff_cb = ttk.Combobox(
            form_frame,
            textvariable=self.diff_var,
            values=["高", "中", "低"],
            state="readonly",
            width=8,
        )
        self.diff_cb.grid(row=0, column=5)
        # Row 1: pt, pn, pm, p_stage
        ttk.Label(form_frame, text="pT").grid(row=1, column=0)
        self.pt_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.pt_var, width=8).grid(row=1, column=1)
        ttk.Label(form_frame, text="pN").grid(row=1, column=2)
        self.pn_var = tk.StringVar()
        # pN改为手动输入框
        ttk.Entry(form_frame, textvariable=self.pn_var, width=8).grid(row=1, column=3)
        ttk.Label(form_frame, text="pM").grid(row=1, column=4)
        # pM 缺省值设置为 0，避免留空导致保存异常
        self.pm_var = tk.StringVar(value="0")
        ttk.Entry(form_frame, textvariable=self.pm_var, width=8).grid(row=1, column=5)
        # 删除分期字段
        self.p_stage_var = tk.StringVar()  # 保留变量以便数据库兼容
        # Row 2: 侵犯项
        self.lvi_var = tk.IntVar()
        ttk.Checkbutton(form_frame, text="脉管内癌栓", variable=self.lvi_var).grid(row=2, column=0)
        self.pni_var = tk.IntVar()
        ttk.Checkbutton(form_frame, text="周围神经侵犯", variable=self.pni_var).grid(row=2, column=1)
        # 删除淋巴结总数和阳性数，保留变量以便数据库兼容
        self.ln_total_var = tk.StringVar()
        self.ln_pos_var = tk.StringVar()
        self.pl_inv_var = tk.IntVar()
        # Row 3: 沿气道播散、胸膜侵犯、病理号
        self.airway_var = tk.IntVar()
        ttk.Checkbutton(form_frame, text="沿气道播散", variable=self.airway_var).grid(row=3, column=0)
        ttk.Checkbutton(form_frame, text="胸膜侵犯", variable=self.pl_inv_var).grid(row=3, column=1)
        ttk.Label(form_frame, text="病理号").grid(row=3, column=2)
        self.pathology_no_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.pathology_no_var, width=15).grid(row=3, column=3, columnspan=2, sticky="w")
        # 肺腺癌主要亚型：新增下拉框（NA/贴壁型/腺泡型/乳头型/微乳头型/实体型）
        ttk.Label(form_frame, text="肺腺癌主要亚型").grid(row=3, column=5)
        self.aden_subtype_var = tk.StringVar()
        self.aden_subtype_cb = ttk.Combobox(
            form_frame,
            textvariable=self.aden_subtype_var,
            values=["NA", "贴壁型", "腺泡型", "乳头型", "微乳头型", "实体型"],
            state="readonly",
            width=10,
        )
        self.aden_subtype_cb.grid(row=3, column=6)
        # Row 4: TRG独立一行
        ttk.Label(form_frame, text="TRG").grid(row=4, column=0)
        self.trg_var = tk.StringVar()
        trg_options = [
            "N/A",
            "1 无肿瘤细胞残留",
            "2 极少量肿瘤细胞残留",
            "3 纤维化多于残留肿瘤细胞",
            "4 残留肿瘤细胞多于纤维化",
            "5 几乎无肿瘤退缩改变",
        ]
        self.trg_cb = ttk.Combobox(
            form_frame,
            textvariable=self.trg_var,
            values=trg_options,
            state="readonly",
            width=20,
        )
        self.trg_cb.grid(row=4, column=1, columnspan=3, sticky="w")
        # 备注
        ttk.Label(form_frame, text="备注").grid(row=5, column=0, sticky="e")
        self.notes_text = tk.Text(form_frame, width=80, height=3)
        self.notes_text.grid(row=5, column=1, columnspan=7, sticky="w")
        # 操作按钮
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=6, column=0, columnspan=8, pady=5)
        ttk.Button(btn_frame, text="新建", command=self.new_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="保存", command=self.save_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_record).pack(side="left", padx=2)
        # 刷新按钮：重新加载当前患者的病理记录
        ttk.Button(btn_frame, text="刷新", command=lambda: self.load_patient(self.app.current_patient_id)).pack(side="left", padx=2)

    def load_patient(self, patient_id: Optional[int]) -> None:
        self.current_path_id = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not patient_id:
            return
        pathologies = self.db.get_pathologies_by_patient(patient_id)
        for p in pathologies:
            # 将 sqlite3.Row 转换为字典，避免使用 Row 的 .get 方法
            p_dict = dict(p)
            no = p_dict.get("pathology_no") or ""
            # 提取标本类型
            specimen = p_dict.get("specimen_type") or ""
            self.tree.insert(
                "",
                tk.END,
                iid=p_dict["path_id"],
                values=(
                    p_dict["path_id"],
                    no,
                    p_dict.get("histology"),
                    specimen,
                ),
            )
        # 自动选择并加载第一条记录以便显示明细
        children = self.tree.get_children()
        if children:
            first = children[0]
            self.tree.selection_set(first)
            try:
                self.load_record(int(first))
            except Exception:
                pass

    def _on_right_click(self, event) -> None:
        """右键点击病理列表时弹出删除菜单。"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # 选中右键所在行
        self.tree.selection_set(item)
        # 仅在选中记录时显示菜单
        if self.current_path_id or self.tree.selection():
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def _on_tree_select(self, event) -> None:
        sel = self.tree.selection()
        if sel:
            self.load_record(int(sel[0]))

    def load_record(self, path_id: int) -> None:
        row = self.db.conn.execute("SELECT * FROM Pathology WHERE path_id=?", (path_id,)).fetchone()
        if not row:
            return
        row = dict(row)  # 转换为字典
        self.current_path_id = path_id
        self.specimen_var.set(row.get("specimen_type") or "")
        self.histology_var.set(row.get("histology") or "")
        self.diff_var.set(row.get("differentiation") or "")
        self.pt_var.set(row.get("pt") or "")
        self.pn_var.set(row.get("pn") or "")
        self.pm_var.set(row.get("pm") or "")
        self.p_stage_var.set(row.get("p_stage") or "")
        self.lvi_var.set(row.get("lvi") or 0)
        self.pni_var.set(row.get("pni") or 0)
        self.pl_inv_var.set(row.get("pleural_invasion") or 0)
        self.airway_var.set(row.get("airway_spread") or 0)
        self.ln_total_var.set(str(row.get("ln_total") or ""))
        self.ln_pos_var.set(str(row.get("ln_positive") or ""))
        # 根据保存的数字值映射为下拉选项
        trg_value = row.get("trg")
        if trg_value:
            # 映射数字到带描述的字符串
            mapping = {
                1: "1 无肿瘤细胞残留",
                2: "2 极少量肿瘤细胞残留",
                3: "3 纤维化多于残留肿瘤细胞",
                4: "4 残留肿瘤细胞多于纤维化",
                5: "5 几乎无肿瘤退缩改变",
            }
            self.trg_var.set(mapping.get(trg_value, str(trg_value)))
        else:
            self.trg_var.set("")
        self.pathology_no_var.set(row.get("pathology_no") or "")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert(tk.END, row.get("notes_path") or "")
        # 新增：肺腺癌主要亚型
        if hasattr(self, "aden_subtype_var"):
            self.aden_subtype_var.set(row.get("aden_subtype") or "")

    def new_record(self) -> None:
        self.current_path_id = None
        self.specimen_var.set("")
        self.histology_var.set("")
        self.diff_var.set("")
        self.pt_var.set("")
        self.pn_var.set("")
        self.pm_var.set("")
        self.p_stage_var.set("")
        self.lvi_var.set(0)
        self.pni_var.set(0)
        self.pl_inv_var.set(0)
        self.ln_total_var.set("")
        self.ln_pos_var.set("")
        self.trg_var.set("N/A")
        # 重置沿气道播散与病理号字段
        self.airway_var.set(0)
        self.pathology_no_var.set("")
        self.notes_text.delete("1.0", tk.END)
        # 初始化肺腺癌主要亚型下拉框为空
        if hasattr(self, "aden_subtype_var"):
            self.aden_subtype_var.set("")

    def save_record(self) -> None:
        if not self.app.current_patient_id:
            messagebox.showerror("错误", "请先选择或保存患者")
            return
        # 构造字典，转换空字符串为 None
        data = {
            "specimen_type": self.specimen_var.get() or None,
            "histology": self.histology_var.get() or None,
            "differentiation": self.diff_var.get() or None,
            "pt": self.pt_var.get() or None,
            "pn": self.pn_var.get() or None,
            "pm": self.pm_var.get() or None,
            "p_stage": self.p_stage_var.get() or None,
            "lvi": self.lvi_var.get(),
            "pni": self.pni_var.get(),
            "pleural_invasion": self.pl_inv_var.get(),
            "airway_spread": self.airway_var.get(),
            "ln_total": int(self.ln_total_var.get()) if self.ln_total_var.get() else None,
            "ln_positive": int(self.ln_pos_var.get()) if self.ln_pos_var.get() else None,
            # TRG 转换: 首先检查是否选择了有效数字选项
            "trg": self._parse_trg(),
            "pathology_no": self.pathology_no_var.get() or None,
            "notes_path": self.notes_text.get("1.0", tk.END).strip() or None,
            # 新增肺腺癌主要亚型
            "aden_subtype": self.aden_subtype_var.get() or None,
        }
        try:
            if self.current_path_id is None:
                new_id = self.db.insert_pathology(self.app.current_patient_id, data)
                messagebox.showinfo("成功", f"病理记录已添加 (ID={new_id})")
            else:
                self.db.update_pathology(self.current_path_id, data)
                messagebox.showinfo("成功", "病理记录已更新")
            self.load_patient(self.app.current_patient_id)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def delete_record(self) -> None:
        """删除当前病理记录，删除前进行两次确认。"""
        if not self.current_path_id:
            return
        # 第一次确认
        if not messagebox.askyesno("确认删除", "确定删除当前病理记录吗？"):
            return
        # 第二次确认
        if not messagebox.askyesno("再次确认", "删除后不可恢复，是否继续？"):
            return
        try:
            self.db.delete_pathology(self.current_path_id)
            messagebox.showinfo("成功", "病理记录已删除")
            self.current_path_id = None
            self.load_patient(self.app.current_patient_id)
            self.new_record()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ----- Wrapper methods for main application -----
    def save_pathology(self) -> None:
        """
        保存病理记录的代理方法，使 main.py 可以统一调用。
        """
        self.save_record()

    def clear_form(self) -> None:
        """
        清空表单（等同于新建记录）。
        """
        self.new_record()

    # ========== 辅助函数 ==========
    def _parse_trg(self) -> Optional[int]:
        """解析TRG下拉框的值，返回整数级别或None。

        当选择为“N/A”或空值时，返回None；否则尝试解析首个数字。
        """
        val = self.trg_var.get().strip()
        if not val or val == "N/A":
            return None
        try:
            return int(val.split()[0])
        except Exception:
            return None

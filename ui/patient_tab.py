# -*- coding: utf-8 -*-
"""
患者/治疗页面
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict

from db.models import Database
from utils.validators import validate_birth_ym6, format_birth_ym6
from staging.lookup import get_lung_stage, get_eso_stage


class PatientTab(ttk.Frame):
    def __init__(self, app, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self.current_patient_id: Optional[int] = None
        self._build_widgets()

        # 为患者表单添加右键菜单以删除当前患者。
        # 由于患者/治疗页没有内置删除按钮，此处提供通过右键快捷删除患者记录的功能。
        # 创建右键菜单并绑定到整个 PatientTab 区域。
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="删除当前患者", command=self._confirm_delete_patient)
        # 绑定鼠标右键事件。使用 bind_all 可确保在该页任何子控件上右键点击时触发。
        self.bind_all("<Button-3>", self._show_context_menu, add="+")

    def _build_widgets(self) -> None:
        # 使用滚动框架
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # === 基本信息区域 ===
        general_frame = ttk.LabelFrame(scrollable_frame, text="基本信息")
        general_frame.pack(fill="x", padx=10, pady=5)

        row = 0
        # 住院号*
        ttk.Label(general_frame, text="住院号*:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        self.hospital_id_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.hospital_id_var, width=20).grid(row=row, column=1, sticky="w", padx=5)

        # 癌种*
        ttk.Label(general_frame, text="癌种*:").grid(row=row, column=2, sticky="e", padx=5)
        self.cancer_var = tk.StringVar()
        self.cancer_cb = ttk.Combobox(
            general_frame,
            textvariable=self.cancer_var,
            values=["肺癌", "食管癌"],
            state="readonly",
            width=10
        )
        self.cancer_cb.grid(row=row, column=3, sticky="w", padx=5)
        self.cancer_cb.bind("<<ComboboxSelected>>", lambda e: self.on_cancer_type_change(self.cancer_var.get()))

        # 性别*
        ttk.Label(general_frame, text="性别*:").grid(row=row, column=4, sticky="e", padx=5)
        self.sex_var = tk.StringVar()
        ttk.Combobox(
            general_frame,
            textvariable=self.sex_var,
            values=["男", "女"],
            state="readonly",
            width=6
        ).grid(row=row, column=5, sticky="w", padx=5)

        row += 1
        # 出生年月
        # 出生年月改为6位(yyyymm)
        ttk.Label(general_frame, text="出生年月(yyyymm):").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        self.birth_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.birth_var, width=12).grid(row=row, column=1, sticky="w", padx=5)
        self.birth_display = ttk.Label(general_frame, text="", foreground="gray")
        self.birth_display.grid(row=row, column=2, columnspan=2, sticky="w", padx=5)
        self.birth_var.trace_add("write", lambda *args: self._update_birth_display())

        # 吸烟包·年
        ttk.Label(general_frame, text="吸烟包·年:").grid(row=row, column=4, sticky="e", padx=5)
        self.pack_years_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.pack_years_var, width=10).grid(row=row, column=5, sticky="w", padx=5)

        row += 1
        # 多源发
        self.multi_primary_var = tk.IntVar()
        ttk.Checkbutton(
            general_frame,
            variable=self.multi_primary_var,
            text="多源发肿瘤"
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=3)

        # 备注
        ttk.Label(general_frame, text="备注:").grid(row=row, column=2, sticky="e", padx=5)
        self.notes_patient_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.notes_patient_var, width=40).grid(row=row, column=3, columnspan=3, sticky="w", padx=5)

        # 新增: 家族恶性肿瘤史勾选
        row += 1
        self.family_history_var = tk.IntVar()
        ttk.Checkbutton(
            general_frame,
            variable=self.family_history_var,
            text="家族恶性肿瘤史"
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=3)

        # === 肺癌cTNM区域 ===
        self.lung_frame = ttk.LabelFrame(scrollable_frame, text="肺癌 cTNM v9")
        self.lung_frame.pack(fill="x", padx=10, pady=5)

        lung_row = 0
        ttk.Label(self.lung_frame, text="cT:").grid(row=lung_row, column=0, sticky="e", padx=5, pady=3)
        self.lung_t_var = tk.StringVar()
        self.lung_t_cb = ttk.Combobox(
            self.lung_frame,
            textvariable=self.lung_t_var,
            values=["", "1a", "1b", "1c", "2a", "2b", "3", "4"],
            state="readonly",
            width=8
        )
        self.lung_t_cb.grid(row=lung_row, column=1, sticky="w", padx=5)
        self.lung_t_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        ttk.Label(self.lung_frame, text="cN:").grid(row=lung_row, column=2, sticky="e", padx=5)
        self.lung_n_var = tk.StringVar(value="0")
        self.lung_n_cb = ttk.Combobox(
            self.lung_frame,
            textvariable=self.lung_n_var,
            values=["0", "1", "2a", "2b", "3"],
            state="readonly",
            width=8
        )
        self.lung_n_cb.grid(row=lung_row, column=3, sticky="w", padx=5)
        self.lung_n_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        ttk.Label(self.lung_frame, text="cM:").grid(row=lung_row, column=4, sticky="e", padx=5)
        self.lung_m_var = tk.StringVar(value="0")
        self.lung_m_cb = ttk.Combobox(
            self.lung_frame,
            textvariable=self.lung_m_var,
            values=["0", "1a", "1b", "1c1", "1c2"],
            state="readonly",
            width=8
        )
        self.lung_m_cb.grid(row=lung_row, column=5, sticky="w", padx=5)
        self.lung_m_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        ttk.Label(self.lung_frame, text="临床分期:").grid(row=lung_row, column=6, sticky="e", padx=5)
        self.lung_stage_label = ttk.Label(self.lung_frame, text="", foreground="blue", font=("Arial", 10, "bold"))
        self.lung_stage_label.grid(row=lung_row, column=7, sticky="w", padx=5)

        # === 食管癌cTNM区域 ===
        self.eso_frame = ttk.LabelFrame(scrollable_frame, text="食管癌 cTNM v9")
        self.eso_frame.pack(fill="x", padx=10, pady=5)

        eso_row = 0
        # 第一行：cTNM
        ttk.Label(self.eso_frame, text="cT:").grid(row=eso_row, column=0, sticky="e", padx=5, pady=3)
        self.eso_t_var = tk.StringVar()
        self.eso_t_cb = ttk.Combobox(
            self.eso_frame,
            textvariable=self.eso_t_var,
            values=["", "is", "1", "2", "3", "4a", "4b"],
            state="readonly",
            width=8
        )
        self.eso_t_cb.grid(row=eso_row, column=1, sticky="w", padx=5)
        self.eso_t_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        ttk.Label(self.eso_frame, text="cN:").grid(row=eso_row, column=2, sticky="e", padx=5)
        self.eso_n_var = tk.StringVar(value="0")
        self.eso_n_cb = ttk.Combobox(
            self.eso_frame,
            textvariable=self.eso_n_var,
            values=["0", "1", "2", "3"],
            state="readonly",
            width=8
        )
        self.eso_n_cb.grid(row=eso_row, column=3, sticky="w", padx=5)
        self.eso_n_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        ttk.Label(self.eso_frame, text="cM:").grid(row=eso_row, column=4, sticky="e", padx=5)
        self.eso_m_var = tk.StringVar(value="0")
        self.eso_m_cb = ttk.Combobox(
            self.eso_frame,
            textvariable=self.eso_m_var,
            values=["0", "1"],
            state="readonly",
            width=8
        )
        self.eso_m_cb.grid(row=eso_row, column=5, sticky="w", padx=5)
        self.eso_m_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        eso_row += 1
        # 第二行：组织学、分级、部位
        ttk.Label(self.eso_frame, text="组织学:").grid(row=eso_row, column=0, sticky="e", padx=5, pady=3)
        self.eso_hist_var = tk.StringVar()
        self.eso_hist_cb = ttk.Combobox(
            self.eso_frame,
            textvariable=self.eso_hist_var,
            values=["", "SCC", "AD"],
            state="readonly",
            width=8
        )
        self.eso_hist_cb.grid(row=eso_row, column=1, sticky="w", padx=5)
        self.eso_hist_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        ttk.Label(self.eso_frame, text="分级:").grid(row=eso_row, column=2, sticky="e", padx=5)
        self.eso_grade_var = tk.StringVar()
        self.eso_grade_cb = ttk.Combobox(
            self.eso_frame,
            textvariable=self.eso_grade_var,
            values=["", "G1", "G2", "G3"],
            state="readonly",
            width=8
        )
        self.eso_grade_cb.grid(row=eso_row, column=3, sticky="w", padx=5)
        self.eso_grade_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        ttk.Label(self.eso_frame, text="部位:").grid(row=eso_row, column=4, sticky="e", padx=5)
        self.eso_loc_var = tk.StringVar()
        self.eso_loc_cb = ttk.Combobox(
            self.eso_frame,
            textvariable=self.eso_loc_var,
            values=["", "上段", "中段", "下段", "EGJ"],
            state="readonly",
            width=8
        )
        self.eso_loc_cb.grid(row=eso_row, column=5, sticky="w", padx=5)
        self.eso_loc_cb.bind("<<ComboboxSelected>>", lambda e: self._update_stage())

        eso_row += 1
        # 第三行：距门齿、临床分期
        ttk.Label(self.eso_frame, text="距门齿(cm):").grid(row=eso_row, column=0, sticky="e", padx=5, pady=3)
        self.eso_from_incisors_var = tk.StringVar()
        self.eso_from_incisors_entry = ttk.Entry(self.eso_frame, textvariable=self.eso_from_incisors_var, width=10)
        self.eso_from_incisors_entry.grid(row=eso_row, column=1, sticky="w", padx=5)

        ttk.Label(self.eso_frame, text="临床分期:").grid(row=eso_row, column=2, sticky="e", padx=5)
        self.eso_stage_label = ttk.Label(self.eso_frame, text="", foreground="blue", font=("Arial", 10, "bold"))
        self.eso_stage_label.grid(row=eso_row, column=3, columnspan=3, sticky="w", padx=5)

        # === 新辅助治疗区域 ===
        nac_frame = ttk.LabelFrame(scrollable_frame, text="新辅助治疗")
        nac_frame.pack(fill="x", padx=10, pady=5)

        nac_row = 0
        # 化疗
        self.nac_chemo_var = tk.IntVar()
        self.nac_chemo_cb = ttk.Checkbutton(nac_frame, text="化疗", variable=self.nac_chemo_var)
        self.nac_chemo_cb.grid(row=nac_row, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(nac_frame, text="周期:").grid(row=nac_row, column=1, sticky="e", padx=5)
        self.nac_chemo_cycles_var = tk.StringVar()
        ttk.Entry(nac_frame, textvariable=self.nac_chemo_cycles_var, width=8).grid(row=nac_row, column=2, sticky="w", padx=5)

        # 免疫
        self.nac_immuno_var = tk.IntVar()
        ttk.Checkbutton(nac_frame, text="免疫", variable=self.nac_immuno_var).grid(row=nac_row, column=3, sticky="w", padx=5)
        ttk.Label(nac_frame, text="周期:").grid(row=nac_row, column=4, sticky="e", padx=5)
        self.nac_immuno_cycles_var = tk.StringVar()
        ttk.Entry(nac_frame, textvariable=self.nac_immuno_cycles_var, width=8).grid(row=nac_row, column=5, sticky="w", padx=5)

        # 靶向
        self.nac_targeted_var = tk.IntVar()
        ttk.Checkbutton(nac_frame, text="靶向", variable=self.nac_targeted_var).grid(row=nac_row, column=6, sticky="w", padx=5)
        ttk.Label(nac_frame, text="周期:").grid(row=nac_row, column=7, sticky="e", padx=5)
        self.nac_targeted_cycles_var = tk.StringVar()
        ttk.Entry(nac_frame, textvariable=self.nac_targeted_cycles_var, width=8).grid(row=nac_row, column=8, sticky="w", padx=5)

        # === 术后辅助治疗区域 ===
        adj_frame = ttk.LabelFrame(scrollable_frame, text="术后辅助治疗")
        adj_frame.pack(fill="x", padx=10, pady=5)

        adj_row = 0
        # 化疗
        self.adj_chemo_var = tk.IntVar()
        ttk.Checkbutton(adj_frame, text="化疗", variable=self.adj_chemo_var).grid(row=adj_row, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(adj_frame, text="周期:").grid(row=adj_row, column=1, sticky="e", padx=5)
        self.adj_chemo_cycles_var = tk.StringVar()
        ttk.Entry(adj_frame, textvariable=self.adj_chemo_cycles_var, width=8).grid(row=adj_row, column=2, sticky="w", padx=5)

        # 免疫
        self.adj_immuno_var = tk.IntVar()
        ttk.Checkbutton(adj_frame, text="免疫", variable=self.adj_immuno_var).grid(row=adj_row, column=3, sticky="w", padx=5)
        ttk.Label(adj_frame, text="周期:").grid(row=adj_row, column=4, sticky="e", padx=5)
        self.adj_immuno_cycles_var = tk.StringVar()
        ttk.Entry(adj_frame, textvariable=self.adj_immuno_cycles_var, width=8).grid(row=adj_row, column=5, sticky="w", padx=5)

        # 靶向
        self.adj_targeted_var = tk.IntVar()
        ttk.Checkbutton(adj_frame, text="靶向", variable=self.adj_targeted_var).grid(row=adj_row, column=6, sticky="w", padx=5)
        ttk.Label(adj_frame, text="周期:").grid(row=adj_row, column=7, sticky="e", padx=5)
        self.adj_targeted_cycles_var = tk.StringVar()
        ttk.Entry(adj_frame, textvariable=self.adj_targeted_cycles_var, width=8).grid(row=adj_row, column=8, sticky="w", padx=5)

        # === 按钮区域 ===
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(btn_frame, text="保存患者", command=self.save_patient).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清空表单", command=self.clear_form).pack(side="left", padx=5)

    def _update_birth_display(self):
        """更新出生年月显示"""
        birth = self.birth_var.get().strip()
        # 使用新的6位日期格式 (yyyymm)
        if birth and len(birth) == 6:
            try:
                formatted = format_birth_ym6(birth)
                self.birth_display.config(text=f"→ {formatted}")
            except Exception:
                self.birth_display.config(text="")
        else:
            self.birth_display.config(text="")

    def _update_stage(self):
        """更新临床分期显示"""
        cancer_type = self.cancer_var.get()
        
        if cancer_type == "肺癌":
            t = self.lung_t_var.get()
            n = self.lung_n_var.get()
            m = self.lung_m_var.get()
            if t and n and m:
                stage = get_lung_stage(self.db.conn, t, n, m)
                self.lung_stage_label.config(text=stage or "未匹配")
            else:
                self.lung_stage_label.config(text="")
        
        elif cancer_type == "食管癌":
            t = self.eso_t_var.get()
            n = self.eso_n_var.get()
            m = self.eso_m_var.get()
            hist = self.eso_hist_var.get()
            grade = self.eso_grade_var.get()
            loc = self.eso_loc_var.get()
            if t and n and m and hist and grade and loc:
                stage = get_eso_stage(self.db.conn, t, n, m, hist, grade, loc)
                self.eso_stage_label.config(text=stage or "未匹配")
            else:
                self.eso_stage_label.config(text="")

    def on_cancer_type_change(self, cancer_type: str):
        """癌种改变时的回调 - 实现互斥禁用"""
        if cancer_type == "肺癌":
            # 启用肺癌字段
            self._set_frame_state(self.lung_frame, "normal")
            # 禁用食管癌字段
            self._set_frame_state(self.eso_frame, "disabled")
        elif cancer_type == "食管癌":
            # 禁用肺癌字段
            self._set_frame_state(self.lung_frame, "disabled")
            # 启用食管癌字段
            self._set_frame_state(self.eso_frame, "normal")
        else:
            # 都启用
            self._set_frame_state(self.lung_frame, "normal")
            self._set_frame_state(self.eso_frame, "normal")
        
        # 通知app
        self.app.on_cancer_type_change(cancer_type)
        
        # 更新分期
        self._update_stage()

    def _set_frame_state(self, frame, state):
        """设置框架内所有输入控件的状态。

        当 state 为 "normal" 时，恢复下拉框的只读状态（readonly）并允许输入框编辑；
        当 state 为其他值（如 "disabled"）时，将下拉框和输入框都设置为禁用状态，使其变灰且不可点击。
        这样可以解决选择肺癌时食管癌分期区域没有变灰的问题。
        """
        for child in frame.winfo_children():
            # 仅处理下拉框和输入框
            if isinstance(child, (ttk.Combobox, ttk.Entry)):
                if state == "normal":
                    # 启用控件。对于 Combobox 使用只读模式，不允许手动输入以避免意外输入；
                    # 对 Entry 使用 normal 允许自由输入。
                    if isinstance(child, ttk.Combobox):
                        child.config(state="readonly")
                    else:
                        child.config(state="normal")
                else:
                    # 禁用控件：所有控件都设置为 disabled，使其灰化并禁止操作。
                    child.config(state="disabled")

    def save_patient(self):
        """保存患者信息"""
        # 验证必填字段
        hospital_id = self.hospital_id_var.get().strip()
        cancer_type = self.cancer_var.get()
        sex = self.sex_var.get()

        if not hospital_id:
            messagebox.showerror("错误", "住院号为必填项")
            return
        if not cancer_type:
            messagebox.showerror("错误", "癌种为必填项")
            return
        if not sex:
            messagebox.showerror("错误", "性别为必填项")
            return

        # 验证出生年月 (6位: yyyymm)
        birth_val = self.birth_var.get().strip()
        if birth_val:
            ok, msg = validate_birth_ym6(birth_val)
            if not ok:
                messagebox.showerror("错误", msg)
                return

        # 构建数据字典
        data = {
            "hospital_id": hospital_id,
            "cancer_type": cancer_type,
            "sex": sex,
            # 存储出生年月到原 birth_ym4 字段中，虽然字段名包含 4，但此处可保存 6 位字符串
            "birth_ym4": birth_val or None,
            "pack_years": float(self.pack_years_var.get()) if self.pack_years_var.get().strip() else None,
            "multi_primary": self.multi_primary_var.get(),
            "lung_t": self.lung_t_var.get() or None,
            "lung_n": self.lung_n_var.get() or None,
            "lung_m": self.lung_m_var.get() or None,
            "eso_t": self.eso_t_var.get() or None,
            "eso_n": self.eso_n_var.get() or None,
            "eso_m": self.eso_m_var.get() or None,
            "eso_histology": self.eso_hist_var.get() or None,
            "eso_grade": self.eso_grade_var.get() or None,
            "eso_location": self.eso_loc_var.get() or None,
            "eso_from_incisors_cm": float(self.eso_from_incisors_var.get()) if self.eso_from_incisors_var.get().strip() else None,
            "nac_chemo": self.nac_chemo_var.get(),
            "nac_chemo_cycles": int(self.nac_chemo_cycles_var.get()) if self.nac_chemo_cycles_var.get().strip() else None,
            "nac_immuno": self.nac_immuno_var.get(),
            "nac_immuno_cycles": int(self.nac_immuno_cycles_var.get()) if self.nac_immuno_cycles_var.get().strip() else None,
            "nac_targeted": self.nac_targeted_var.get(),
            "nac_targeted_cycles": int(self.nac_targeted_cycles_var.get()) if self.nac_targeted_cycles_var.get().strip() else None,
            "adj_chemo": self.adj_chemo_var.get(),
            "adj_chemo_cycles": int(self.adj_chemo_cycles_var.get()) if self.adj_chemo_cycles_var.get().strip() else None,
            "adj_immuno": self.adj_immuno_var.get(),
            "adj_immuno_cycles": int(self.adj_immuno_cycles_var.get()) if self.adj_immuno_cycles_var.get().strip() else None,
            "adj_targeted": self.adj_targeted_var.get(),
            "adj_targeted_cycles": int(self.adj_targeted_cycles_var.get()) if self.adj_targeted_cycles_var.get().strip() else None,
            "notes_patient": self.notes_patient_var.get() or None,
            # 家族恶性肿瘤史
            "family_history": self.family_history_var.get(),
        }

        try:
            if self.current_patient_id:
                # 更新
                self.db.update_patient(self.current_patient_id, data)
                messagebox.showinfo("成功", "患者信息已更新")
            else:
                # 新建
                patient_id = self.db.insert_patient(data)
                self.current_patient_id = patient_id
                self.app.current_patient_id = patient_id
                messagebox.showinfo("成功", f"患者已创建，ID: {patient_id}")
            
            # 刷新患者列表
            self.app.refresh_patient_list(self.current_patient_id)
            self.app.status(f"已保存患者: {hospital_id}")
        
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def load_patient(self, patient_dict: Dict):
        """加载患者数据"""
        self.current_patient_id = patient_dict.get("patient_id")
        
        self.hospital_id_var.set(patient_dict.get("hospital_id", ""))
        self.cancer_var.set(patient_dict.get("cancer_type", ""))
        self.sex_var.set(patient_dict.get("sex", ""))
        self.birth_var.set(patient_dict.get("birth_ym4", ""))
        self.pack_years_var.set(patient_dict.get("pack_years", ""))
        self.multi_primary_var.set(patient_dict.get("multi_primary", 0))

        # 家族恶性肿瘤史
        self.family_history_var.set(patient_dict.get("family_history", 0))
        
        self.lung_t_var.set(patient_dict.get("lung_t", ""))
        self.lung_n_var.set(patient_dict.get("lung_n", ""))
        self.lung_m_var.set(patient_dict.get("lung_m", ""))
        
        self.eso_t_var.set(patient_dict.get("eso_t", ""))
        self.eso_n_var.set(patient_dict.get("eso_n", ""))
        self.eso_m_var.set(patient_dict.get("eso_m", ""))
        self.eso_hist_var.set(patient_dict.get("eso_histology", ""))
        self.eso_grade_var.set(patient_dict.get("eso_grade", ""))
        self.eso_loc_var.set(patient_dict.get("eso_location", ""))
        self.eso_from_incisors_var.set(patient_dict.get("eso_from_incisors_cm", ""))
        
        self.nac_chemo_var.set(patient_dict.get("nac_chemo", 0))
        self.nac_chemo_cycles_var.set(patient_dict.get("nac_chemo_cycles", ""))
        self.nac_immuno_var.set(patient_dict.get("nac_immuno", 0))
        self.nac_immuno_cycles_var.set(patient_dict.get("nac_immuno_cycles", ""))
        self.nac_targeted_var.set(patient_dict.get("nac_targeted", 0))
        self.nac_targeted_cycles_var.set(patient_dict.get("nac_targeted_cycles", ""))
        
        self.adj_chemo_var.set(patient_dict.get("adj_chemo", 0))
        self.adj_chemo_cycles_var.set(patient_dict.get("adj_chemo_cycles", ""))
        self.adj_immuno_var.set(patient_dict.get("adj_immuno", 0))
        self.adj_immuno_cycles_var.set(patient_dict.get("adj_immuno_cycles", ""))
        self.adj_targeted_var.set(patient_dict.get("adj_targeted", 0))
        self.adj_targeted_cycles_var.set(patient_dict.get("adj_targeted_cycles", ""))
        
        self.notes_patient_var.set(patient_dict.get("notes_patient", ""))
        
        # 触发癌种改变事件
        cancer_type = patient_dict.get("cancer_type", "")
        if cancer_type:
            self.on_cancer_type_change(cancer_type)

    def clear_form(self):
        """清空表单"""
        self.current_patient_id = None
        
        self.hospital_id_var.set("")
        self.cancer_var.set("")
        self.sex_var.set("")
        self.birth_var.set("")
        self.pack_years_var.set("")
        self.multi_primary_var.set(0)

        # 家族恶性肿瘤史
        self.family_history_var.set(0)
        
        self.lung_t_var.set("")
        self.lung_n_var.set("0")
        self.lung_m_var.set("0")
        
        self.eso_t_var.set("")
        self.eso_n_var.set("0")
        self.eso_m_var.set("0")
        self.eso_hist_var.set("")
        self.eso_grade_var.set("")
        self.eso_loc_var.set("")
        self.eso_from_incisors_var.set("")
        
        self.nac_chemo_var.set(0)
        self.nac_chemo_cycles_var.set("")
        self.nac_immuno_var.set(0)
        self.nac_immuno_cycles_var.set("")
        self.nac_targeted_var.set(0)
        self.nac_targeted_cycles_var.set("")
        
        self.adj_chemo_var.set(0)
        self.adj_chemo_cycles_var.set("")
        self.adj_immuno_var.set(0)
        self.adj_immuno_cycles_var.set("")
        self.adj_targeted_var.set(0)
        self.adj_targeted_cycles_var.set("")
        
        self.notes_patient_var.set("")
        
        self.lung_stage_label.config(text="")
        self.eso_stage_label.config(text="")
        self.birth_display.config(text="")
        
        # 恢复所有框架状态
        self._set_frame_state(self.lung_frame, "normal")
        self._set_frame_state(self.eso_frame, "normal")

    # ==================== 删除患者相关功能 ====================
    def _show_context_menu(self, event) -> None:
        """在右键点击时显示删除菜单。

        该方法仅在当前页为患者/治疗页且存在已加载患者时弹出右键菜单。
        """
        # 判断当前 Notebook 页索引；索引 0 对应患者/治疗页
        try:
            notebook = self.app.notebook
            current_tab = notebook.index(notebook.select())
        except Exception:
            return
        if current_tab != 0:
            return
        # 必须有已加载患者才能删除
        if not self.current_patient_id:
            return
        # 弹出菜单
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _confirm_delete_patient(self) -> None:
        """二次确认并删除当前患者及其所有关联记录。"""
        pid = self.current_patient_id
        if not pid:
            return
        # 读取住院号用于提示
        hospital_id = self.hospital_id_var.get() or ""
        # 第一次确认
        if not messagebox.askyesno("确认删除", f"确定要删除患者 {hospital_id} 及其所有关联记录吗？"):
            return
        # 第二次确认
        if not messagebox.askyesno("再次确认", "删除后不可恢复，是否继续？"):
            return
        try:
            # 调用数据库删除方法；若 Database 未定义 delete_patient，会抛出 AttributeError
            if hasattr(self.db, "delete_patient"):
                self.db.delete_patient(pid)  # type: ignore[call-arg]
            else:
                # 直接执行删除语句
                self.db.conn.execute("DELETE FROM Patient WHERE patient_id=?", (pid,))
                self.db.conn.commit()
            messagebox.showinfo("成功", "患者记录已删除")
            # 清空当前患者状态并刷新界面
            self.app.current_patient_id = None
            self.current_patient_id = None
            self.clear_form()
            self.app.refresh_patient_list()
        except Exception as e:
            messagebox.showerror("错误", str(e))

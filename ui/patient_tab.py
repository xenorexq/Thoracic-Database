# -*- coding: utf-8 -*-
"""
患者/治疗页面
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict

from db.models import Database
from utils.validators import validate_birth_ym6, format_birth_ym6, validate_date6
# 已弃用 TNM 分期映射功能，不再导入 get_lung_stage/get_eso_stage
from tkhtmlview import HTMLScrolledText


class PatientTab(ttk.Frame):
    def __init__(self, app, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self.current_patient_id: Optional[int] = None
        # 预加载 AJCC 分期规则，用于分期参考显示
        self._load_ajcc_content()
        self._build_widgets()

        # 为患者表单添加右键菜单以删除当前患者。
        # 由于患者/治疗页没有内置删除按钮，此处提供通过右键快捷删除患者记录的功能。
        # 创建右键菜单并绑定到整个 PatientTab 区域。
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="删除当前患者", command=self._confirm_delete_patient)
        # 绑定鼠标右键事件。使用 bind_all 可确保在该页任何子控件上右键点击时触发。
        self.bind_all("<Button-3>", self._show_context_menu, add="+")

    @staticmethod
    def _render_markdown(content: str) -> str:
        """将嵌入的 Markdown 简单转换为 HTML，当前主要处理粗体标记。"""
        if not content:
            return ""
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)

    def _build_widgets(self) -> None:
        # 创建一个水平分隔窗口，使左侧表单和右侧 AJCC 参考区宽度可调
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # 左侧容器，用于放置可滚动的患者表单
        left_container = ttk.Frame(paned)
        paned.add(left_container, weight=3)

        # 右侧容器：AJCC 分期参考区域
        self.stage_frame = ttk.LabelFrame(paned, text="AJCC 分期参考")
        paned.add(self.stage_frame, weight=1)

        # 在左侧容器中创建滚动框架
        canvas = tk.Canvas(left_container)
        # 垂直滚动条放在 canvas 左侧
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

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

        row += 1
        # 糖尿病史
        self.diabetes_history_var = tk.IntVar()
        ttk.Checkbutton(
            general_frame,
            variable=self.diabetes_history_var,
            text="糖尿病史"
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=3)

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
        # 废弃自动分期更新，不再绑定

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
        # 废弃自动分期更新，不再绑定

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
        # 废弃自动分期更新，不再绑定

        # 取消临床分期计算按钮和显示

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
        # 废弃自动分期更新，不再绑定

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
        # 废弃自动分期更新，不再绑定

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
        # 废弃自动分期更新，不再绑定

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
        # 废弃自动分期更新，不再绑定

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
        # 废弃自动分期更新，不再绑定

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
        # 废弃自动分期更新，不再绑定

        eso_row += 1
        # 第三行：距门齿、临床分期
        ttk.Label(self.eso_frame, text="距门齿(cm):").grid(row=eso_row, column=0, sticky="e", padx=5, pady=3)
        self.eso_from_incisors_var = tk.StringVar()
        self.eso_from_incisors_entry = ttk.Entry(self.eso_frame, textvariable=self.eso_from_incisors_var, width=10)
        self.eso_from_incisors_entry.grid(row=eso_row, column=1, sticky="w", padx=5)

        # 取消食管癌分期计算按钮和分期显示

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
        # 新增放疗勾选框，无周期设置
        self.nac_radiation_var = tk.IntVar()
        ttk.Checkbutton(nac_frame, text="放疗", variable=self.nac_radiation_var).grid(row=nac_row, column=9, sticky="w", padx=5)
        
        # 新增：抗血管治疗（在靶向下方）
        nac_row += 1
        self.nac_antiangio_var = tk.IntVar()
        ttk.Checkbutton(nac_frame, text="抗血管", variable=self.nac_antiangio_var).grid(row=nac_row, column=6, sticky="w", padx=5)
        ttk.Label(nac_frame, text="周期:").grid(row=nac_row, column=7, sticky="e", padx=5)
        self.nac_antiangio_cycles_var = tk.StringVar()
        ttk.Entry(nac_frame, textvariable=self.nac_antiangio_cycles_var, width=8).grid(row=nac_row, column=8, sticky="w", padx=5)
        
        # 新辅助治疗日期 (yymmdd格式)
        nac_row += 1
        ttk.Label(nac_frame, text="治疗日期 (yymmdd):").grid(row=nac_row, column=0, sticky="e", padx=5, pady=3)
        self.nac_date_var = tk.StringVar()
        ttk.Entry(nac_frame, textvariable=self.nac_date_var, width=10).grid(row=nac_row, column=1, columnspan=2, sticky="w", padx=5)

        # === 辅助治疗区域 ===
        # 文本“术后辅助治疗”改为“辅助治疗”，表示围手术期以外的治疗
        adj_frame = ttk.LabelFrame(scrollable_frame, text="辅助治疗")
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
        # 新增放疗勾选框，无周期设置
        self.adj_radiation_var = tk.IntVar()
        ttk.Checkbutton(adj_frame, text="放疗", variable=self.adj_radiation_var).grid(row=adj_row, column=9, sticky="w", padx=5)
        
        # 新增：抗血管治疗（在靶向下方）
        adj_row += 1
        self.adj_antiangio_var = tk.IntVar()
        ttk.Checkbutton(adj_frame, text="抗血管", variable=self.adj_antiangio_var).grid(row=adj_row, column=6, sticky="w", padx=5)
        ttk.Label(adj_frame, text="周期:").grid(row=adj_row, column=7, sticky="e", padx=5)
        self.adj_antiangio_cycles_var = tk.StringVar()
        ttk.Entry(adj_frame, textvariable=self.adj_antiangio_cycles_var, width=8).grid(row=adj_row, column=8, sticky="w", padx=5)
        
        # 辅助治疗日期 (yymmdd格式)
        adj_row += 1
        ttk.Label(adj_frame, text="治疗日期 (yymmdd):").grid(row=adj_row, column=0, sticky="e", padx=5, pady=3)
        self.adj_date_var = tk.StringVar()
        ttk.Entry(adj_frame, textvariable=self.adj_date_var, width=10).grid(row=adj_row, column=1, columnspan=2, sticky="w", padx=5)

        # === 按钮区域 ===
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(btn_frame, text="保存患者", command=self.save_patient).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清空表单", command=self.clear_form).pack(side="left", padx=5)

        # === 分期参考区域 ===
        # 在右侧 stage_frame 中添加按钮和文本区域
        btn_frame = ttk.Frame(self.stage_frame)
        btn_frame.pack(fill="x", padx=2, pady=2)
        ttk.Button(btn_frame, text="Lung", command=self.show_lung_reference).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Eso", command=self.show_eso_reference).pack(side="left", padx=2)
        # 使用自定义 HTMLScrolledText 显示已转换为 HTML 的分期内容。宽度由分隔窗口控制
        self.stage_text = HTMLScrolledText(self.stage_frame, wrap="word")
        self.stage_text.pack(fill="both", expand=True)

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

    def on_cancer_type_change(self, cancer_type: str, notify_app: bool = True):
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
        if notify_app:
            self.app.on_cancer_type_change(cancer_type)
        
        # 分期计算功能已取消，不更新临床分期

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

    def _load_ajcc_content(self) -> None:
        """
        预加载 AJCC 分期规则内容。

        为了在脱机环境中使用，本方法将 AJCC 肺癌和食管癌分期的 Markdown 文本嵌入为字符串。
        """
        # AJCC 肺癌 TNM 分期（第九版） – 预先转换为 HTML 以便在 HTMLScrolledText 中渲染
        self.ajcc_lung_content = """<h1>AJCC 肺癌 TNM 分期（第九版）</h1>
<p></p>
<hr />
<p></p>
<h2>一、 原发肿瘤 (T)</h2>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述</th></tr>
<tr><td>**TX**</td><td>原发肿瘤无法评估，或痰液/支气管灌洗液中找到癌细胞，但影像学或支气管镜未发现肿瘤。</td></tr>
<tr><td>**T0**</td><td>无原发肿瘤证据。</td></tr>
<tr><td>**Tis**</td><td>原位癌（包括鳞状细胞原位癌和腺原位癌）。</td></tr>
<tr><td>**T1**</td><td>肿瘤最大径 ≤ 3 cm，周围被肺或脏层胸膜包绕，支气管镜检查未侵及叶支气管（即未侵及主支气管）。</td></tr>
<tr><td>**T1mi**</td><td>微浸润性腺癌：肿瘤最大径 ≤ 3 cm，以贴壁生长为主，且浸润灶最大径 ≤ 5 mm。</td></tr>
<tr><td>**T1a**</td><td>肿瘤最大径 ≤ 1 cm。</td></tr>
<tr><td>**T1b**</td><td>肿瘤最大径 > 1 cm 且 ≤ 2 cm。</td></tr>
<tr><td>**T1c**</td><td>肿瘤最大径 > 2 cm 且 ≤ 3 cm。</td></tr>
<tr><td>**T2**</td><td>肿瘤最大径 > 3 cm 且 ≤ 5 cm；或具有以下任一特征：<br> • 侵及主支气管（不累及气管隆突）；<br> • 侵及脏层胸膜（PL1 或 PL2）；<br> • 伴有肺不张或阻塞性肺炎，延伸至肺门，累及部分或全肺。</td></tr>
<tr><td>**T2a**</td><td>肿瘤最大径 > 3 cm 且 ≤ 4 cm。</td></tr>
<tr><td>**T2b**</td><td>肿瘤最大径 > 4 cm 且 ≤ 5 cm。</td></tr>
<tr><td>**T3**</td><td>肿瘤最大径 > 5 cm 且 ≤ 7 cm；或具有以下任一特征：<br> • 直接侵犯胸壁（包括壁层胸膜、上纵隔沟瘤）、膈神经、心包（壁层）；<br> • 同一肺叶内出现单个或多个卫星结节。</td></tr>
<tr><td>**T4**</td><td>肿瘤最大径 > 7 cm；或具有以下任一特征：<br> • 侵犯纵隔、心脏、大血管、气管、喉返神经、食管、椎体、气管隆突；<br> • 侵犯膈肌；<br> • 同侧不同肺叶出现单个或多个卫星结节。</td></tr>
</table>
<p></p>
<hr />
<p></p>
<h2>二、 区域淋巴结 (N)</h2>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述</th></tr>
<tr><td>**NX**</td><td>区域淋巴结无法评估。</td></tr>
<tr><td>**N0**</td><td>无区域淋巴结转移。</td></tr>
<tr><td>**N1**</td><td>转移至同侧支气管旁和/或同侧肺门淋巴结，以及肺内淋巴结（包括直接侵犯）。</td></tr>
<tr><td>**N2**</td><td>转移至同侧纵隔和/或隆突下淋巴结。<br> *（第九版新增亚组）*</td></tr>
<tr><td>**N2a**</td><td>仅转移至单个 N2 淋巴结站（跳跃性转移或非跳跃性转移）。</td></tr>
<tr><td>**N2b**</td><td>转移至多个 N2 淋巴结站。</td></tr>
<tr><td>**N3**</td><td>转移至对侧纵隔、对侧肺门、同侧或对侧斜角肌或锁骨上淋巴结。</td></tr>
</table>
<p></p>
<hr />
<p></p>
<h2>三、 远处转移 (M)</h2>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述</th></tr>
<tr><td>**M0**</td><td>无远处转移。</td></tr>
<tr><td>**M1**</td><td>有远处转移。</td></tr>
<tr><td>**M1a**</td><td>出现以下任一情况：<br> • 对侧肺叶出现单个或多个结节；<br> • 胸膜或心包结节；<br> • 恶性胸腔积液或心包积液。</td></tr>
<tr><td>**M1b**</td><td>单个器官单个胸外转移病灶（不包括 M1a 所描述的情况）。</td></tr>
<tr><td>**M1c**</td><td>多个胸外转移病灶。<br> *（第九版新增亚组）*</td></tr>
<tr><td>**M1c1**</td><td>单个器官多个胸外转移病灶。</td></tr>
<tr><td>**M1c2**</td><td>多个器官多个胸外转移病灶。</td></tr>
</table>
<p></p>
<hr />"""
        # 转换 Markdown 粗体标记为 HTML
        self.ajcc_lung_content = self._render_markdown(self.ajcc_lung_content)

        # AJCC 食管癌与食管胃结合部癌 TNM分期（第八版） – HTML 格式
        self.ajcc_eso_content = """<h1>AJCC 第八版 食管癌与食管胃结合部(EGJ)癌 TNM分期规则</h1>
<p></p>
<hr />
<p></p>
<h2> T、N、M、G 定义</h2>
<p></p>
<h3>原发肿瘤 (T)</h3>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述</th></tr>
<tr><td>**TX**</td><td>原发肿瘤无法评估</td></tr>
<tr><td>**T0**</td><td>无原发肿瘤证据</td></tr>
<tr><td>**Tis**</td><td>高级别上皮内瘤变（重度异型增生）</td></tr>
<tr><td>**T1**</td><td>肿瘤侵及黏膜固有层、黏膜肌层或黏膜下层</td></tr>
<tr><td>**T1a**</td><td>肿瘤侵及黏膜固有层或黏膜肌层</td></tr>
<tr><td>**T1b**</td><td>肿瘤侵及黏膜下层</td></tr>
<tr><td>**T2**</td><td>肿瘤侵及固有肌层</td></tr>
<tr><td>**T3**</td><td>肿瘤侵及食管纤维膜（外膜）</td></tr>
<tr><td>**T4**</td><td>肿瘤侵及邻近结构</td></tr>
<tr><td>**T4a**</td><td>肿瘤侵及胸膜、心包、奇静脉、膈肌或腹膜</td></tr>
<tr><td>**T4b**</td><td>肿瘤侵及其他邻近结构，如主动脉、椎体或气管</td></tr>
</table>
<p></p>
<h3>区域淋巴结 (N)</h3>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述</th></tr>
<tr><td>**NX**</td><td>区域淋巴结无法评估</td></tr>
<tr><td>**N0**</td><td>无区域淋巴结转移</td></tr>
<tr><td>**N1**</td><td>1-2 枚区域淋巴结转移</td></tr>
<tr><td>**N2**</td><td>3-6 枚区域淋巴结转移</td></tr>
<tr><td>**N3**</td><td>≥ 7 枚区域淋巴结转移</td></tr>
</table>
<p></p>
<h3>远处转移 (M)</h3>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述</th></tr>
<tr><td>**M0**</td><td>无远处转移</td></tr>
<tr><td>**M1**</td><td>有远处转移</td></tr>
</table>
<p></p>
<h3>组织学分级 (G)</h3>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述（腺癌）</th><th>描述（鳞状细胞癌）</th></tr>
<tr><td>**GX**</td><td>分化程度无法评估</td><td>分化程度无法评估</td></tr>
<tr><td>**G1**</td><td>高分化（>95% 形成腺管）</td><td>高分化（角化明显）</td></tr>
<tr><td>**G2**</td><td>中分化（50%-95% 形成腺管）</td><td>中分化</td></tr>
<tr><td>**G3**</td><td>低分化（<50% 形成腺管）</td><td>低分化（基底样细胞为主）</td></tr>
</table>
<p></p>
<h3>肿瘤位置 (L) - 仅用于鳞癌病理分期</h3>
<p></p>
<table border="1" cellspacing="0" cellpadding="2">
<tr><th>分期</th><th>描述</th></tr>
<tr><td>**LX**</td><td>位置无法确定</td></tr>
<tr><td>**Upper**</td><td>颈段食管至奇静脉弓下缘</td></tr>
<tr><td>**Middle**</td><td>奇静脉弓下缘至下肺静脉下缘</td></tr>
<tr><td>**Lower**</td><td>下肺静脉下缘至胃（包括 EGJ）</td></tr>
</table>
<p></p>
<hr />"""
        self.ajcc_eso_content = self._render_markdown(self.ajcc_eso_content)

    def update_stage_reference(self) -> None:
        """
        默认不根据癌种自动显示任何内容。用户需点击右侧按钮查看分期参考。
        """
        # 如果阶段文本框尚未创建，直接返回
        if not hasattr(self, "stage_text"):
            return
        # 清空 HTML 显示。
        if hasattr(self, "stage_text"):
            try:
                # 对 HTML 视图使用 set_html 清空内容
                self.stage_text.set_html("")
            except Exception:
                # 回退到文本框清空
                self.stage_text.configure(state="normal")
                self.stage_text.delete("1.0", tk.END)
                self.stage_text.configure(state="disabled")
        # 说明：具体内容通过 show_lung_reference 或 show_eso_reference 显示

    def show_lung_reference(self) -> None:
        """显示肺癌 AJCC 分期定义。"""
        if not hasattr(self, "stage_text"):
            return
        content = self.ajcc_lung_content
        # 如果支持 HTML 视图则渲染为 HTML，否则插入纯文本
        try:
            # content 为 HTML 字符串
            self.stage_text.set_html(content)
        except Exception:
            # fallback to plain text
            self.stage_text.configure(state="normal")
            self.stage_text.delete("1.0", tk.END)
            self.stage_text.insert("1.0", content)
            self.stage_text.configure(state="disabled")

    def show_eso_reference(self) -> None:
        """显示食管癌 AJCC 分期定义。"""
        if not hasattr(self, "stage_text"):
            return
        content = self.ajcc_eso_content
        try:
            self.stage_text.set_html(content)
        except Exception:
            self.stage_text.configure(state="normal")
            self.stage_text.delete("1.0", tk.END)
            self.stage_text.insert("1.0", content)
            self.stage_text.configure(state="disabled")


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

        # 验证治疗日期 (可选项，格式需为 yymmdd)
        nac_date_val = self.nac_date_var.get().strip()
        if nac_date_val:
            ok, msg = validate_date6(nac_date_val)
            if not ok:
                messagebox.showerror("错误", f"新辅助治疗日期格式错误：{msg}")
                return

        adj_date_val = self.adj_date_var.get().strip()
        if adj_date_val:
            ok, msg = validate_date6(adj_date_val)
            if not ok:
                messagebox.showerror("错误", f"辅助治疗日期格式错误：{msg}")
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
            # 新辅助放疗勾选
            "nac_radiation": self.nac_radiation_var.get(),
            # 新辅助抗血管治疗
            "nac_antiangio": self.nac_antiangio_var.get(),
            "nac_antiangio_cycles": int(self.nac_antiangio_cycles_var.get()) if self.nac_antiangio_cycles_var.get().strip() else None,
            # 新辅助治疗日期
            "nac_date": nac_date_val or None,
            "adj_chemo": self.adj_chemo_var.get(),
            "adj_chemo_cycles": int(self.adj_chemo_cycles_var.get()) if self.adj_chemo_cycles_var.get().strip() else None,
            "adj_immuno": self.adj_immuno_var.get(),
            "adj_immuno_cycles": int(self.adj_immuno_cycles_var.get()) if self.adj_immuno_cycles_var.get().strip() else None,
            "adj_targeted": self.adj_targeted_var.get(),
            "adj_targeted_cycles": int(self.adj_targeted_cycles_var.get()) if self.adj_targeted_cycles_var.get().strip() else None,
            # 辅助放疗勾选
            "adj_radiation": self.adj_radiation_var.get(),
            # 辅助抗血管治疗
            "adj_antiangio": self.adj_antiangio_var.get(),
            "adj_antiangio_cycles": int(self.adj_antiangio_cycles_var.get()) if self.adj_antiangio_cycles_var.get().strip() else None,
            # 辅助治疗日期
            "adj_date": adj_date_val or None,
            "notes_patient": self.notes_patient_var.get() or None,
            # 糖尿病史
            "diabetes_history": self.diabetes_history_var.get(),
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
        self.diabetes_history_var.set(patient_dict.get("diabetes_history", 0))

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
        # 新辅助放疗
        self.nac_radiation_var.set(patient_dict.get("nac_radiation", 0))
        # 新辅助抗血管治疗
        self.nac_antiangio_var.set(patient_dict.get("nac_antiangio", 0))
        self.nac_antiangio_cycles_var.set(patient_dict.get("nac_antiangio_cycles", ""))
        # 新辅助治疗日期
        self.nac_date_var.set(patient_dict.get("nac_date", ""))
        
        self.adj_chemo_var.set(patient_dict.get("adj_chemo", 0))
        self.adj_chemo_cycles_var.set(patient_dict.get("adj_chemo_cycles", ""))
        self.adj_immuno_var.set(patient_dict.get("adj_immuno", 0))
        self.adj_immuno_cycles_var.set(patient_dict.get("adj_immuno_cycles", ""))
        self.adj_targeted_var.set(patient_dict.get("adj_targeted", 0))
        self.adj_targeted_cycles_var.set(patient_dict.get("adj_targeted_cycles", ""))
        # 辅助放疗
        self.adj_radiation_var.set(patient_dict.get("adj_radiation", 0))
        # 辅助抗血管治疗
        self.adj_antiangio_var.set(patient_dict.get("adj_antiangio", 0))
        self.adj_antiangio_cycles_var.set(patient_dict.get("adj_antiangio_cycles", ""))
        # 辅助治疗日期
        self.adj_date_var.set(patient_dict.get("adj_date", ""))
        
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

        # 糖尿病史
        self.diabetes_history_var.set(0)
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
        self.nac_radiation_var.set(0)
        self.nac_antiangio_var.set(0)
        self.nac_antiangio_cycles_var.set("")
        self.nac_date_var.set("")
        
        self.adj_chemo_var.set(0)
        self.adj_chemo_cycles_var.set("")
        self.adj_immuno_var.set(0)
        self.adj_immuno_cycles_var.set("")
        self.adj_targeted_var.set(0)
        self.adj_targeted_cycles_var.set("")
        self.adj_radiation_var.set(0)
        self.adj_antiangio_var.set(0)
        self.adj_antiangio_cycles_var.set("")
        self.adj_date_var.set("")
        
        self.notes_patient_var.set("")
        
        # 不再使用临床分期标签
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






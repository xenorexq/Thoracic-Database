"""
导入预览对话框

显示数据库导入前的预检查结果，让用户确认是否继续导入。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional

from db.import_checker import ImportAnalysis, format_analysis_report


class ImportPreviewDialog:
    """导入预览确认对话框"""
    
    def __init__(self, parent: tk.Widget, analysis: ImportAnalysis):
        self.result: Optional[bool] = None  # None=未决定, True=确认导入, False=取消
        self.analysis = analysis
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("数据库导入 - 确认导入")
        self.dialog.geometry("750x750")  # 增加尺寸确保按钮可见
        self.dialog.resizable(True, True)
        self.dialog.minsize(700, 700)  # 设置最小尺寸，防止用户缩得太小
        
        # 居中显示
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._build_widgets()
        
        # 等待用户响应
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.dialog.wait_window()
    
    def _build_widgets(self):
        """构建对话框组件"""
        # 主容器
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # 标题和说明
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        # 主标题
        main_title = ttk.Label(
            title_frame,
            text="📊 数据库导入预检查完成",
            font=("Arial", 14, "bold"),
            foreground="#2c3e50"
        )
        main_title.pack(anchor="w", pady=(0, 5))
        
        # 副标题（检查结果）
        if self.analysis.new_patients > 0:
            icon = "✓"
            title_text = f"检测到 {self.analysis.new_patients} 位新患者可以导入"
            title_color = "green"
            subtitle_text = "请确认下方信息后，点击底部的'确认导入'按钮开始导入"
        else:
            icon = "⚠"
            title_text = "没有可导入的新患者"
            title_color = "orange"
            subtitle_text = "所有患者均已存在于当前数据库"
        
        result_label = ttk.Label(
            title_frame,
            text=f"{icon} {title_text}",
            font=("Arial", 11, "bold"),
            foreground=title_color
        )
        result_label.pack(anchor="w", pady=(0, 2))
        
        # 操作提示
        subtitle_label = ttk.Label(
            title_frame,
            text=subtitle_text,
            font=("Arial", 9),
            foreground="gray"
        )
        subtitle_label.pack(anchor="w")
        
        # 摘要信息框
        summary_frame = ttk.LabelFrame(main_frame, text="导入摘要", padding=10)
        summary_frame.pack(fill="x", pady=(0, 10))
        
        summary_grid = ttk.Frame(summary_frame)
        summary_grid.pack(fill="x")
        
        # 左列
        left_col = ttk.Frame(summary_grid)
        left_col.pack(side="left", fill="both", expand=True)
        
        ttk.Label(left_col, text=f"源文件数量:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(left_col, text=f"{len(self.analysis.source_files)} 个", 
                 font=("Arial", 9, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(left_col, text=f"总患者数:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(left_col, text=f"{self.analysis.total_patients} 位", 
                 font=("Arial", 9, "bold")).grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Label(left_col, text=f"新患者:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(left_col, text=f"{self.analysis.new_patients} 位", 
                 font=("Arial", 9, "bold"), foreground="green").grid(row=2, column=1, sticky="w", padx=5)
        
        # 右列
        right_col = ttk.Frame(summary_grid)
        right_col.pack(side="left", fill="both", expand=True, padx=(20, 0))
        
        ttk.Label(right_col, text=f"本地重复:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(right_col, text=f"{self.analysis.duplicate_in_local} 位", 
                 font=("Arial", 9, "bold"), foreground="red").grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(right_col, text=f"源间重复:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(right_col, text=f"{self.analysis.duplicate_in_sources} 对", 
                 font=("Arial", 9, "bold"), foreground="orange").grid(row=1, column=1, sticky="w", padx=5)
        
        # 关联数据预估
        if self.analysis.new_patients > 0:
            related_frame = ttk.LabelFrame(main_frame, text="预计导入的关联数据", padding=10)
            related_frame.pack(fill="x", pady=(0, 10))
            
            related_grid = ttk.Frame(related_frame)
            related_grid.pack(fill="x")
            
            data_items = [
                ("手术记录:", self.analysis.estimated_surgeries),
                ("病理记录:", self.analysis.estimated_pathologies),
                ("分子记录:", self.analysis.estimated_molecular),
                ("随访事件:", self.analysis.estimated_followup_events)
            ]
            
            for i, (label, count) in enumerate(data_items):
                col = i % 2
                row = i // 2
                
                item_frame = ttk.Frame(related_grid)
                item_frame.grid(row=row, column=col, sticky="w", padx=(0, 20), pady=2)
                
                ttk.Label(item_frame, text=label).pack(side="left")
                ttk.Label(item_frame, text=f"约 {count} 条", 
                         font=("Arial", 9, "bold")).pack(side="left", padx=5)
        
        # 详细报告（可滚动文本框）
        detail_frame = ttk.LabelFrame(main_frame, text="详细报告", padding=5)
        detail_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        report_text = scrolledtext.ScrolledText(
            detail_frame,
            wrap=tk.WORD,
            width=80,
            height=12,  # 减小高度，为按钮留出空间
            font=("Courier", 9)
        )
        report_text.pack(fill="both", expand=True)
        
        # 插入报告内容
        report_content = format_analysis_report(self.analysis)
        report_text.insert("1.0", report_content)
        report_text.config(state="disabled")  # 只读
        
        # 提示信息
        if self.analysis.duplicate_in_local > 0 or self.analysis.duplicate_in_sources > 0:
            hint_frame = ttk.Frame(main_frame)
            hint_frame.pack(fill="x", pady=(0, 10))
            
            hint_label = ttk.Label(
                hint_frame,
                text="⚠ 提示：重复的患者将被自动跳过，不会覆盖现有数据",
                foreground="orange",
                font=("Arial", 9)
            )
            hint_label.pack(anchor="w")
        
        # 按钮栏 - 增加上方边距确保可见
        if self.analysis.new_patients > 0:
            # 有新数据可导入 - 添加明显的说明
            instruction_frame = ttk.Frame(main_frame)
            instruction_frame.pack(fill="x", pady=(15, 5))  # 增加上方边距
            
            instruction_label = ttk.Label(
                instruction_frame,
                text="👉 点击下方按钮开始导入数据：",
                foreground="blue",
                font=("Arial", 10, "bold")
            )
            instruction_label.pack(anchor="w")
            
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x", pady=(5, 10))  # 增加按钮区域的垂直边距
            
            confirm_btn = ttk.Button(
                button_frame,
                text=f"✓ 确认导入 ({self.analysis.new_patients} 位新患者)",
                command=self.on_confirm,
                bootstyle="success",  # 绿色按钮更醒目
                width=35
            )
            confirm_btn.pack(side="left", padx=5, pady=5)  # 增加按钮内边距
            
            cancel_btn = ttk.Button(
                button_frame,
                text="✗ 取消",
                command=self.on_cancel,
                width=15
            )
            cancel_btn.pack(side="left", padx=5, pady=5)
        else:
            # 没有新数据 - 显示清晰的提示
            no_data_frame = ttk.Frame(main_frame)
            no_data_frame.pack(fill="x", pady=(15, 10))  # 增加上方边距
            
            no_data_label = ttk.Label(
                no_data_frame,
                text="ℹ 所有患者均已存在于当前数据库中，无需导入",
                foreground="blue",
                font=("Arial", 10, "bold")
            )
            no_data_label.pack(anchor="w")
            
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x", pady=(5, 10))  # 增加按钮区域的垂直边距
            
            ttk.Button(
                button_frame,
                text="关闭",
                command=self.on_cancel,
                width=15
            ).pack(side="left", padx=5, pady=5)  # 增加按钮内边距
        
        # 导出报告按钮（始终显示在右侧）
        ttk.Button(
            button_frame,
            text="导出报告",
            command=self.on_export_report,
            width=15
        ).pack(side="right", padx=5, pady=5)
    
    def on_confirm(self):
        """用户确认导入"""
        self.result = True
        self.dialog.destroy()
    
    def on_cancel(self):
        """用户取消导入"""
        self.result = False
        self.dialog.destroy()
    
    def on_export_report(self):
        """导出报告到文本文件"""
        from tkinter import filedialog
        from datetime import datetime
        
        filename = f"import_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")],
            initialfile=filename
        )
        
        if filepath:
            try:
                report_content = format_analysis_report(self.analysis)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                
                from tkinter import messagebox
                messagebox.showinfo("成功", f"报告已导出到:\n{filepath}")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("错误", f"导出报告失败:\n{e}")


def show_import_preview(parent: tk.Widget, analysis: ImportAnalysis) -> bool:
    """
    显示导入预览对话框
    
    Args:
        parent: 父窗口
        analysis: 分析结果
    
    Returns:
        True=用户确认导入, False=用户取消
    """
    dialog = ImportPreviewDialog(parent, analysis)
    return dialog.result == True


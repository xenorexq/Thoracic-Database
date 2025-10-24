"""
Follow-up tab for thoracic entry application (v2.15 - Rebuilt).

This module implements an event-driven follow-up logging system where each
follow-up interaction is recorded as a separate, timestamped event.
Rebuilt based on surgery_tab.py structure to fix patient switching issues.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import ThoracicApp

from db.models import Database


class FollowUpTab(ttk.Frame):
    """Follow-up tab with event-driven logging system."""
    
    # 预定义的事件类型
    EVENT_TYPES = ["生存", "复发/转移", "进展", "死亡", "失访"]
    
    def __init__(self, parent: tk.Widget, app: ThoracicApp) -> None:
        super().__init__(parent)
        self.app = app
        self.db: Database = app.db
        self.current_patient_id: Optional[int] = None
        self.current_event_id: Optional[int] = None
        self._build_widgets()

    def _build_widgets(self) -> None:
        """构建UI组件：上部事件列表 + 下部输入面板"""
        
        # ========== 上部：事件列表 ==========
        list_frame = ttk.LabelFrame(self, text="随访事件列表")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建Treeview
        columns = ("event_date", "event_type", "event_details")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=10
        )
        
        # 设置列标题和宽度
        self.tree.heading("event_date", text="日期")
        self.tree.heading("event_type", text="事件类型")
        self.tree.heading("event_details", text="详情")
        
        self.tree.column("event_date", width=100, anchor="center")
        self.tree.column("event_type", width=100, anchor="center")
        self.tree.column("event_details", width=300, anchor="w")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        # 绑定右键菜单
        self.tree.bind("<Button-3>", self._on_right_click)
        
        # ========== 下部：输入面板 ==========
        input_frame = ttk.LabelFrame(self, text="新增/编辑随访事件")
        input_frame.pack(fill="x", padx=5, pady=5)
        
        # 第一行：事件类型 + 事件日期
        row1 = ttk.Frame(input_frame)
        row1.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(row1, text="事件类型:").pack(side="left")
        self.event_type_var = tk.StringVar()
        self.event_type_combo = ttk.Combobox(
            row1,
            textvariable=self.event_type_var,
            values=self.EVENT_TYPES,
            state="readonly",
            width=15
        )
        self.event_type_combo.pack(side="left", padx=5)
        self.event_type_combo.bind("<<ComboboxSelected>>", self._on_event_type_change)
        
        ttk.Label(row1, text="事件日期 (YYYYMMDD):").pack(side="left", padx=(20, 0))
        self.event_date_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.event_date_var, width=15).pack(side="left", padx=5)
        
        # 第二行：部位（条件性显示）
        row2 = ttk.Frame(input_frame)
        row2.pack(fill="x", padx=5, pady=5)
        
        self.site_label = ttk.Label(row2, text="部位:")
        self.site_var = tk.StringVar()
        self.site_entry = ttk.Entry(row2, textvariable=self.site_var, width=30)
        
        # 第三行：备注
        row3 = ttk.Frame(input_frame)
        row3.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(row3, text="备注:").pack(side="left")
        self.notes_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.notes_var, width=60).pack(side="left", padx=5, fill="x", expand=True)
        
        # 第四行：按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(btn_frame, text="保存", command=self.save_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="新建", command=self.new_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_record).pack(side="left", padx=2)

    def _on_event_type_change(self, event=None) -> None:
        """当事件类型改变时，显示或隐藏部位字段"""
        event_type = self.event_type_var.get()
        if event_type in ["复发/转移", "进展"]:
            # 显示部位字段
            self.site_label.pack(side="left")
            self.site_entry.pack(side="left", padx=5)
        else:
            # 隐藏部位字段
            self.site_label.pack_forget()
            self.site_entry.pack_forget()
            self.site_var.set("")  # 清空部位

    def load_patient(self, patient_id: int) -> None:
        """当切换患者时调用，加载该患者的所有随访事件"""
        self.current_patient_id = patient_id
        self.current_event_id = None
        
        # 清空事件列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 查询该患者的所有随访事件
        events = self.db.get_followup_events(patient_id)
        
        # 按日期降序排序（最新的在上）
        events_sorted = sorted(events, key=lambda e: dict(e).get("event_date") or "", reverse=True)
        
        # 填充到树形视图
        for e in events_sorted:
            e_dict = dict(e)
            event_id = e_dict["event_id"]
            event_date = e_dict.get("event_date") or ""
            event_type = e_dict.get("event_type") or ""
            event_details = e_dict.get("event_details") or ""
            
            # 插入到树形视图，使用event_id作为iid
            self.tree.insert("", tk.END, iid=event_id, values=(event_date, event_type, event_details))
        
        # 自动选择第一条记录
        children = self.tree.get_children()
        if children:
            first = children[0]
            self.tree.selection_set(first)
            try:
                self.load_record(int(first))
            except Exception as e:
                print(f"Warning: Failed to load follow-up event: {e}")
        else:
            # 没有记录时清空输入框
            self.new_record()

    def _on_tree_select(self, event) -> None:
        """当选择事件列表中的某一项时，加载该事件的详细信息"""
        sel = self.tree.selection()
        if sel:
            self.load_record(int(sel[0]))

    def _on_right_click(self, event) -> None:
        """右键点击事件列表时弹出删除菜单"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # 选中右键所在行
        self.tree.selection_set(item)
        # 显示菜单
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="删除", command=self.delete_record)
        menu.post(event.x_root, event.y_root)

    def load_record(self, event_id: int) -> None:
        """加载指定event_id的随访事件到输入框"""
        if not self.current_patient_id:
            return
        
        # 从数据库查询该事件
        events = self.db.get_followup_events(self.current_patient_id)
        row = None
        for e in events:
            if dict(e)["event_id"] == event_id:
                row = e
                break
        
        if not row:
            return
        
        row = dict(row)  # 转换为字典
        self.current_event_id = event_id
        
        # 填充输入框
        self.event_type_var.set(row.get("event_type") or "")
        self.event_date_var.set(row.get("event_date") or "")
        
        # 解析event_details
        event_details = row.get("event_details") or ""
        if "部位:" in event_details:
            # 提取部位和备注
            parts = event_details.split("部位:", 1)
            if len(parts) == 2:
                site_and_notes = parts[1]
                if "备注:" in site_and_notes:
                    site_part, notes_part = site_and_notes.split("备注:", 1)
                    self.site_var.set(site_part.strip())
                    self.notes_var.set(notes_part.strip())
                else:
                    self.site_var.set(site_and_notes.strip())
                    self.notes_var.set("")
            else:
                self.site_var.set("")
                self.notes_var.set(event_details)
        else:
            self.site_var.set("")
            self.notes_var.set(event_details)
        
        # 触发事件类型变化，显示/隐藏部位字段
        self._on_event_type_change()

    def new_record(self) -> None:
        """清空输入框，准备新建事件"""
        self.current_event_id = None
        self.event_type_var.set("")
        self.event_date_var.set("")
        self.site_var.set("")
        self.notes_var.set("")
        self._on_event_type_change()
        # 取消树形视图的选择
        self.tree.selection_remove(self.tree.selection())

    def save_record(self) -> None:
        """保存随访事件"""
        # v2.16: 从 app 获取当前患者ID（修复 Bug）
        if not self.current_patient_id:
            self.current_patient_id = self.app.current_patient_id
        
        if not self.current_patient_id:
            messagebox.showwarning("警告", "请先选择或创建患者")
            return
        
        event_type = self.event_type_var.get().strip()
        event_date = self.event_date_var.get().strip()
        
        if not event_type:
            messagebox.showwarning("警告", "请选择事件类型")
            return
        
        if not event_date:
            messagebox.showwarning("警告", "请输入事件日期")
            return
        
        # 构建event_details
        event_details_parts = []
        
        # 如果是复发/转移或进展，需要部位信息
        if event_type in ["复发/转移", "进展"]:
            site = self.site_var.get().strip()
            if site:
                event_details_parts.append(f"部位:{site}")
        
        # 添加备注
        notes = self.notes_var.get().strip()
        if notes:
            event_details_parts.append(f"备注:{notes}")
        
        event_details = " ".join(event_details_parts)
        
        try:
            if self.current_event_id:
                # 更新现有事件
                # 注意：当前数据库模型没有update_followup_event方法，需要先删除再插入
                self.db.delete_followup_event(self.current_event_id)
                event_id = self.db.insert_followup_event(
                    self.current_patient_id,
                    event_date,
                    event_type,
                    event_details
                )
                messagebox.showinfo("成功", "随访事件已更新")
            else:
                # 新建事件
                event_id = self.db.insert_followup_event(
                    self.current_patient_id,
                    event_date,
                    event_type,
                    event_details
                )
                messagebox.showinfo("成功", f"随访事件已创建，ID: {event_id}")
            
            # 重新加载患者的所有事件
            self.load_patient(self.current_patient_id)
            
            # 选中刚保存的事件
            if event_id:
                try:
                    self.tree.selection_set(str(event_id))
                    self.tree.see(str(event_id))
                except:
                    pass
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def delete_record(self) -> None:
        """删除当前选中的随访事件"""
        if not self.current_event_id:
            messagebox.showwarning("警告", "请先选择要删除的事件")
            return
        
        if not messagebox.askyesno("确认", "确定要删除这条随访事件吗？"):
            return
        
        try:
            self.db.delete_followup_event(self.current_event_id)
            messagebox.showinfo("成功", "随访事件已删除")
            
            # 重新加载患者的所有事件
            self.load_patient(self.current_patient_id)
            
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {str(e)}")


# Thoracic-Database v2.01 更新日志

**发布日期:** 2025年10月22日  
**基于版本:** v2.0

## 📋 更新内容

### 1. 新增功能

#### 1.1 手术标签页UI增强
- **位置:** `ui/surgery_tab.py`
- **功能描述:** 在肺叶下拉栏后面，与双侧打勾框同一垂直线位置上增加"左"和"右"打勾框
- **默认状态:** 不勾选
- **用途:** 更精确地记录手术侧别信息

**UI布局变化:**
```
原布局: [肺叶下拉栏] [双侧☐]
新布局: [肺叶下拉栏] [左☐] [右☐] [双侧☐]
```

### 2. 数据库架构更新

#### 2.1 Surgery表新增字段
- **字段名:** `left_side` (INTEGER, DEFAULT 0)
- **字段名:** `right_side` (INTEGER, DEFAULT 0)
- **说明:** 用于存储左右打勾框的状态

#### 2.2 其他表字段补充
为确保数据完整性，补充了以下字段到表定义中：

**Patient表:**
- `eso_from_incisors_cm` (REAL) - 食管癌距门齿距离
- `family_history` (INTEGER, DEFAULT 0) - 家族恶性肿瘤史

**Pathology表:**
- `airway_spread` (INTEGER) - 气道播散
- `pathology_no` (TEXT) - 病理号

**Molecular表:**
- `genes_tested` (TEXT) - 检测基因列表
- `result_summary` (TEXT) - 结果摘要
- `ctc_count` (INTEGER) - 循环肿瘤细胞计数
- `methylation_result` (TEXT) - 甲基化检测结果

### 3. 数据迁移支持

#### 3.1 迁移脚本更新
- **文件:** `db/migrate.py`
- **新增迁移:** Surgery表的left_side和right_side字段
- **兼容性:** 自动检测并添加缺失字段，不影响现有数据

### 4. 导出功能验证

#### 4.1 Excel导出
- ✅ 确认left_side字段正确导出
- ✅ 确认right_side字段正确导出
- ✅ 所有Surgery表字段完整导出

#### 4.2 CSV导出
- ✅ 确认left_side字段正确导出
- ✅ 确认right_side字段正确导出
- ✅ 所有Surgery表字段完整导出

### 5. 测试结果

#### 5.1 完整导出测试
```
测试项目: v2.01完整导出测试
通过: 12/12 (100%)
问题: 0

验证字段:
✓ Surgery.left_side (Excel & CSV)
✓ Surgery.right_side (Excel & CSV)
✓ Surgery.lobe (Excel & CSV)
✓ Surgery.bilateral (Excel & CSV)
✓ Surgery.approach (Excel & CSV)
✓ Surgery.scope_lung (Excel & CSV)
```

## 🔄 升级指南

### 从v2.0升级到v2.01

**方法一：使用迁移脚本（推荐）**
1. 备份当前数据库文件
2. 替换程序文件为v2.01版本
3. 运行迁移脚本：
   ```bash
   python db/migrate.py
   ```
4. 迁移脚本会自动添加新字段，无需手动操作

**方法二：全新安装**
1. 备份当前数据库文件
2. 在新目录安装v2.01版本
3. 将备份的数据库文件复制到新目录
4. 运行迁移脚本添加新字段

### 数据兼容性
- ✅ 完全兼容v2.0数据库
- ✅ 自动添加新字段，默认值为0（未勾选）
- ✅ 不影响现有数据和功能

## 📊 技术细节

### UI实现
```python
# 在surgery_tab.py的肺叶下拉栏后添加
self.left_var = tk.IntVar()
ttk.Checkbutton(self.lung_frame, text="左", variable=self.left_var).grid(row=0, column=6)

self.right_var = tk.IntVar()
ttk.Checkbutton(self.lung_frame, text="右", variable=self.right_var).grid(row=0, column=7)
```

### 数据保存
```python
# 在save_record方法中
data = {
    # ... 其他字段 ...
    "left_side": self.left_var.get(),
    "right_side": self.right_var.get(),
    "bilateral": self.bilateral_var.get(),
}
```

### 数据加载
```python
# 在load_record方法中
self.left_var.set(row.get("left_side") or 0)
self.right_var.set(row.get("right_side") or 0)
```

## ⚠️ 注意事项

1. **数据库备份:** 升级前务必备份数据库文件
2. **迁移脚本:** 首次运行v2.01时会自动执行字段迁移
3. **默认值:** 新字段默认为0（未勾选），不影响现有记录的显示
4. **导出兼容:** 所有导出功能已更新，包含新字段

## 🐛 已知问题

无

## 📚 相关文档

- `CHANGELOG_v2.0.md` - v2.0版本更新日志
- `RELEASE_NOTES_v2.0.md` - v2.0版本发布说明
- `README.md` - 使用说明

---

**版本:** v2.01  
**发布日期:** 2025年10月22日  
**下载:** Thoracic-Database-v2.01.zip


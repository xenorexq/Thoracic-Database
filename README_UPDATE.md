# 胸外科科研录入工具 - 更新说明

## 快速开始

### 运行程序
```bash
python main.py
```

### 首次运行
程序会自动：
1. 创建数据库文件 `thoracic.db`
2. 执行数据库迁移（添加新字段）
3. 尝试加载分期映射CSV文件（如果存在）

### 打包为exe
```bash
pip install pyinstaller openpyxl
pyinstaller --noconfirm --clean --onefile --windowed \
  --name thoracic_entry \
  --icon=assets/app.ico \
  --add-data "assets;assets" \
  main.py
```

打包后的exe文件位于 `dist/thoracic_entry.exe`

## 主要改进

### 1. 左侧患者列表
- 显示所有患者的住院号、ID和癌种
- 顶部快速查找框：输入住院号或患者ID即时筛选
- 癌种筛选：全部/肺癌/食管癌
- 双击患者加载详细信息
- 新建患者按钮

### 2. 患者页面改进
- **cTNM前缀**：标签显示为"cT"、"cN"、"cM"
- **癌种互斥**：选择肺癌时食管字段变灰，反之亦然
- **距门齿字段**：食管癌专用，位于食管cTNM区域
- **优化布局**：食管癌分期分三行显示，不会超出屏幕

### 3. 修复关键错误
- **中文乱码**：所有界面中文正常显示
- **sqlite3.Row错误**：修复保存手术记录时的崩溃问题
- **数据库字段**：自动添加缺失的字段

### 4. 快捷键支持
- **Ctrl+N**：新建患者
- **Ctrl+S**：保存当前页面

## 数据库变更

程序启动时会自动执行迁移，添加以下字段：

### Patient表
- `eso_from_incisors_cm` REAL - 距门齿距离（厘米）

### Pathology表
- `airway_spread` INTEGER - 沿气道播散（STAS）
- `pathology_no` TEXT - 病理号

### Molecular表
- `ctc_count` INTEGER - CTC计数
- `methylation_result` TEXT - 甲基化结果（阴/阳）

## 未完成的功能

由于时间限制，以下功能数据库已准备好，但UI未完成：

### 病理页面重构
- 按肺癌/食管癌拆分模板
- 侵袭项改为中文复选框
- 组织学、分化、pTNM改为下拉选项
- 标本类型改为下拉菜单

### 分子页面扩展
- 添加CTC和METHYLATION平台选项
- 动态显示对应字段

如需完成这些功能，请参考 `CHANGES.md` 文档。

## 测试建议

### 基本测试流程
1. 启动程序
2. 点击"新建患者"或按Ctrl+N
3. 填写住院号、癌种、性别（必填）
4. 选择肺癌 → 验证食管字段变灰
5. 选择食管癌 → 验证肺癌字段变灰
6. 填写cTNM信息 → 查看自动分期
7. 保存患者（Ctrl+S）
8. 在左侧列表中双击患者 → 验证加载正确
9. 切换到手术页 → 新建手术记录 → 保存
10. 验证不再出现错误提示

### 搜索测试
1. 在左侧快速查找框输入住院号
2. 在左侧快速查找框输入患者ID
3. 使用癌种筛选下拉框

## 文件结构

```
thoracic_entry_clean/
├── main.py                 # 主程序（已修改）
├── db/
│   ├── models.py          # 数据库模型（已修改）
│   └── migrate.py         # 迁移脚本（新增）
├── ui/
│   ├── patient_tab.py     # 患者页面（重写）
│   ├── surgery_tab.py     # 手术页面（修复）
│   ├── path_tab.py        # 病理页面（修复）
│   ├── mol_tab.py         # 分子页面（修复）
│   ├── fu_tab.py          # 随访页面（修复）
│   └── export_tab.py      # 导出页面（修复）
├── utils/
│   └── validators.py      # 验证工具
├── staging/
│   └── lookup.py          # 分期查询
├── export/
│   ├── excel.py           # Excel导出
│   └── csv.py             # CSV导出
├── assets/
│   └── app.ico            # 程序图标
├── thoracic.db            # 数据库文件（自动创建）
├── README.md              # 原始说明
├── README_UPDATE.md       # 本文档
└── CHANGES.md             # 详细修改说明
```

## 常见问题

### Q: 程序启动报错找不到模块
A: 确保安装了所有依赖：
```bash
pip install -r requirements.txt
```

### Q: 自动分期显示为空
A: 需要在 `assets/` 目录下放置分期映射CSV文件：
- map_lung_v9.csv
- map_eso_v9_scc.csv
- map_eso_v9_ad.csv

### Q: 打包后exe无法运行
A: 检查是否添加了 `--add-data "assets;assets"` 参数

### Q: 数据库字段未更新
A: 删除 `thoracic.db` 文件后重新运行程序

## 技术支持

详细的修改说明请参考 `CHANGES.md` 文档。
原始需求文档请参考 `123.txt`。

## 版本信息
- 修改日期：2025-10-19
- Python版本：3.10+
- 主要依赖：tkinter, sqlite3, openpyxl


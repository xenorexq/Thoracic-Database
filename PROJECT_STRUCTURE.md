# 项目结构说明

## 📁 目录结构

```
Thoracic-Database/
├── assets/                 # 资源文件
│   └── app.ico            # 应用图标
│
├── db/                    # 数据库模块
│   ├── __init__.py
│   ├── models.py          # 数据库模型和操作
│   ├── migrate.py         # 数据库迁移
│   ├── importer.py        # 数据库导入
│   └── import_checker.py  # 导入预检查
│
├── ui/                    # 用户界面模块
│   ├── __init__.py
│   ├── patient_tab.py     # 患者管理界面
│   ├── surgery_tab.py     # 手术记录界面
│   ├── path_tab.py        # 病理记录界面
│   ├── mol_tab.py         # 分子检测界面
│   ├── fu_tab.py          # 随访管理界面
│   ├── export_tab.py      # 导出功能界面
│   └── import_preview_dialog.py  # 导入预览对话框
│
├── export/                # 导出模块
│   ├── __init__.py
│   ├── excel.py           # Excel导出
│   ├── csv.py             # CSV导出
│   └── parallel.py        # 并行导出工具
│
├── utils/                 # 工具模块
│   ├── __init__.py
│   ├── db_health_checker.py  # 数据库健康检查
│   ├── field_validator.py    # 字段验证
│   ├── logger.py             # 日志工具
│   └── validators.py         # 验证函数
│
├── docs/                  # 文档目录
│   ├── USER_GUIDE.md      # 用户指南
│   ├── DATABASE_MERGE_SAFETY.md  # 数据库合并安全指南
│   └── ID_CONFLICT_FAQ.md        # ID冲突常见问题
│
├── main.py                # 主程序入口
├── requirements.txt       # Python依赖
├── VERSION.txt            # 版本号
│
├── README.md              # 项目说明
├── CHANGELOG.md           # 更新日志
├── RELEASE_NOTES.md       # 发布说明
├── LICENSE                # 许可证
│
├── IMPORT_GUIDE.md        # 导入指南
├── BACKUP_GUIDE.md        # 备份指南
├── TROUBLESHOOTING_GUIDE.md  # 故障排除指南
├── BUILD_INSTRUCTIONS.md  # 打包说明
├── FINAL_VERIFICATION_REPORT.md  # 最终验证报告
│
├── thoracic_ultimate.spec # PyInstaller配置（推荐）
├── thoracic_entry.spec    # PyInstaller配置（简化版）
│
├── build_exe_ultimate.bat # Windows打包脚本（推荐）
├── build_windows.bat      # Windows打包脚本
├── build_macos.sh         # macOS打包脚本
├── build_exe.bat          # 简化打包脚本
└── build_exe.py           # Python打包脚本
```

---

## 📄 核心文件说明

### 主程序

- **main.py**: 应用程序主入口，包含`ThoracicApp`类和主窗口逻辑

### 数据库模块

- **db/models.py**: 
  - 数据库模型定义
  - CRUD操作封装
  - 智能路径检测（支持开发/EXE环境）
  
- **db/migrate.py**: 数据库版本迁移和schema更新

- **db/importer.py**: 数据库导入核心逻辑

- **db/import_checker.py**: 导入前数据分析和预检查

### UI模块

所有UI模块继承自Tkinter/ttkbootstrap，采用标签页结构：

- **patient_tab.py**: 患者基本信息管理
- **surgery_tab.py**: 手术记录管理（支持肺癌/食管癌）
- **path_tab.py**: 病理报告管理（TNM分期、TRG评分）
- **mol_tab.py**: 分子检测管理（PCR/NGS/CTC/甲基化）
- **fu_tab.py**: 随访事件管理（生存/复发/转移/失访/死亡）
- **export_tab.py**: 数据导出功能（Excel/CSV）
- **import_preview_dialog.py**: 导入预览对话框

### 导出模块

- **export/excel.py**: Excel格式导出（使用openpyxl）
- **export/csv.py**: CSV格式导出
- **export/parallel.py**: 多线程并行导出工具

### 工具模块

- **utils/db_health_checker.py**: 数据库健康检查和自动修复
- **utils/field_validator.py**: 字段验证和错误提示
- **utils/logger.py**: 应用日志记录
- **utils/validators.py**: 日期、数值等验证函数

---

## 🗄️ 数据库结构

### 主表

- **Patient**: 患者基本信息（31个字段）
- **Surgery**: 手术记录（22个字段）
- **Pathology**: 病理报告（20个字段）
- **Molecular**: 分子检测（14个字段）
- **FollowUpEvent**: 随访事件（6个字段）
- **FollowUp**: 随访汇总（已废弃，保留兼容）

### 辅助表

- **map_lung_v9**: 肺癌AJCC第9版分期映射
- **map_eso_v9_scc**: 食管鳞癌AJCC第9版分期映射
- **map_eso_v9_ad**: 食管腺癌AJCC第9版分期映射

### 关系

```
Patient (1) ─┬─ (N) Surgery
             ├─ (N) Pathology
             ├─ (N) Molecular
             └─ (N) FollowUpEvent
```

所有子表通过`patient_id`外键关联，支持级联删除。

---

## 🔧 配置文件

### requirements.txt

Python依赖包列表：
- ttkbootstrap: 现代化UI主题
- openpyxl: Excel文件操作
- Pillow: 图像处理

### thoracic_ultimate.spec

PyInstaller打包配置（推荐使用）：
- 包含所有必需的数据文件
- 配置了图标和版本信息
- 隐藏控制台窗口

---

## 📝 文档文件

### 用户文档

- **README.md**: 项目概述和快速开始
- **docs/USER_GUIDE.md**: 完整的用户使用指南
- **IMPORT_GUIDE.md**: 数据导入详细步骤
- **BACKUP_GUIDE.md**: 数据备份和恢复指南
- **TROUBLESHOOTING_GUIDE.md**: 常见问题和解决方案

### 技术文档

- **CHANGELOG.md**: 版本更新历史
- **RELEASE_NOTES.md**: 当前版本发布说明
- **BUILD_INSTRUCTIONS.md**: EXE打包详细说明
- **FINAL_VERIFICATION_REPORT.md**: 质量验证报告
- **PROJECT_STRUCTURE.md**: 本文档

### 专题文档

- **docs/DATABASE_MERGE_SAFETY.md**: 数据库合并安全指南
- **docs/ID_CONFLICT_FAQ.md**: ID冲突处理FAQ

---

## 🚀 打包脚本

### Windows

- **build_exe_ultimate.bat**: 推荐使用，包含完整配置
- **build_windows.bat**: 标准打包脚本
- **build_simple.bat**: 简化打包脚本

### macOS/Linux

- **build_macos.sh**: macOS打包脚本

### 通用

- **build_exe.py**: Python打包脚本（跨平台）

---

## 📦 生成文件

### 运行时生成

- **thoracic.db**: SQLite数据库文件
- **importer.log**: 导入操作日志
- **app.log**: 应用运行日志

### 打包生成

- **build/**: PyInstaller构建目录
- **dist/**: 最终可执行文件目录
  - **thoracic_entry.exe**: Windows可执行文件

---

## 🔒 忽略文件

`.gitignore`配置忽略以下文件：

- Python缓存文件（`__pycache__`, `*.pyc`）
- 数据库文件（`*.db`, `*.log`）
- 构建产物（`build/`, `dist/`）
- IDE配置（`.vscode/`, `.idea/`）
- 临时文件（`*.tmp`, `~$*`）

---

## 🎯 关键设计模式

### 1. MVC架构

- **Model**: `db/models.py` - 数据模型和业务逻辑
- **View**: `ui/*.py` - 用户界面
- **Controller**: `main.py` - 应用控制逻辑

### 2. 单例模式

- `Database`类在应用中保持单一实例
- 通过`ThoracicApp.db`访问

### 3. 观察者模式

- UI组件监听数据变化
- 自动刷新显示

### 4. 工厂模式

- 动态创建UI组件
- 根据癌种切换字段显示

---

## 💡 开发建议

### 添加新功能

1. 在相应模块中添加代码
2. 更新相关文档
3. 运行测试验证
4. 更新CHANGELOG.md

### 修复Bug

1. 在相应模块中修复
2. 添加测试用例
3. 更新CHANGELOG.md
4. 更新版本号

### 发布新版本

1. 更新VERSION.txt
2. 更新CHANGELOG.md
3. 更新RELEASE_NOTES.md
4. 运行完整测试
5. 打包EXE
6. 创建GitHub Release

---

*最后更新: 2025-11-25*  
*版本: v3.7.2*


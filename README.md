# 胸外科科研数据录入系统

<div align="center">

![Version](https://img.shields.io/badge/version-3.7.2-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

**专业的胸外科临床数据管理系统**

[功能特性](#功能特性) • [快速开始](#快速开始) • [文档](#文档) • [更新日志](#更新日志)

</div>

---

## 📋 项目简介

胸外科科研数据录入系统是一个专为胸外科临床科研设计的数据管理工具，支持患者信息、手术记录、病理报告、分子检测和随访数据的全流程管理。

### 核心优势

- ✅ **数据完整性**: 完善的外键约束和级联删除机制
- ✅ **高性能**: 插入1000条记录仅需8.67秒，平均响应0.0048秒
- ✅ **线程安全**: 正确处理SQLite多线程限制
- ✅ **安全可靠**: SQL注入防护、参数化查询、数据验证
- ✅ **易于部署**: 支持打包成独立EXE，无需Python环境

---

## 🚀 功能特性

### 数据管理
- **患者管理**: 基本信息、癌种分类、吸烟史等
- **手术记录**: 手术日期、术式、切除范围、淋巴结清扫等
- **病理报告**: TNM分期、组织学类型、分化程度、TRG评分等
- **分子检测**: 支持PCR/NGS/CTC/甲基化检测
- **随访管理**: 生存、复发、转移、失访、死亡事件追踪

### 数据导入导出
- **导入**: 支持合并其他数据库，自动去重
- **导出**: Excel/CSV格式，支持单患者或全库导出
- **备份**: 一键备份数据库
- **健康检查**: 数据完整性自动检查和修复

### 辅助功能
- **AJCC分期参考**: 内置肺癌/食管癌第9版分期表
- **数据验证**: 自动验证日期格式、数值范围、唯一性约束
- **搜索过滤**: 支持模糊搜索和癌种筛选

---

## 📦 快速开始

### 方式一：使用预编译EXE（推荐）

1. 下载最新版本的`thoracic_entry.exe`
2. 双击运行，无需安装
3. 数据库文件会自动创建在程序所在目录

### 方式二：从源码运行

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/Thoracic-Database.git
cd Thoracic-Database

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python main.py
```

### 系统要求

- **操作系统**: Windows 7+, macOS 10.12+, Linux
- **Python**: 3.8+ (源码运行时需要)
- **内存**: 至少512MB可用内存
- **磁盘**: 至少100MB可用空间

---

## 📚 文档

- [用户指南](docs/USER_GUIDE.md) - 完整的功能使用说明
- [导入指南](IMPORT_GUIDE.md) - 数据库导入详细步骤
- [备份指南](BACKUP_GUIDE.md) - 数据备份和恢复
- [故障排除](TROUBLESHOOTING_GUIDE.md) - 常见问题解决
- [打包指南](BUILD_INSTRUCTIONS.md) - EXE打包说明
- [更新日志](CHANGELOG.md) - 版本更新记录

---

## 🔧 技术栈

- **GUI框架**: Tkinter + ttkbootstrap
- **数据库**: SQLite3
- **数据导出**: openpyxl (Excel), csv (CSV)
- **打包工具**: PyInstaller

---

## 📊 数据库结构

```
Patient (患者表)
├── Surgery (手术记录)
├── Pathology (病理报告)
├── Molecular (分子检测)
└── FollowUpEvent (随访事件)
```

所有子表通过`patient_id`外键关联，支持级联删除。

---

## 🔄 更新日志

### v3.7.2 (2025-11-25) - 最新稳定版

#### 🔥 关键修复
- 修复导入旧版数据库时`event_code`为`None`的bug
- 修复SQLite线程安全问题
- 修复EXE环境下资源加载失败

#### ✨ 功能增强
- 孤儿字段自动保护（编辑时保留旧数据）
- 导出标识符完善（无住院号时使用备用ID）
- 并发控制完善（导入导出互斥）

#### 🎨 UI改进
- 优化导入预览对话框尺寸和布局
- 添加清晰的操作指引

[查看完整更新日志](CHANGELOG.md)

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 👥 作者

- **xenorexq** - *初始工作和维护* - [GitHub](https://github.com/xenorexq)

---

## 🙏 致谢

感谢所有测试用户提供的宝贵反馈和bug报告！

---

## 📞 联系方式

- **Email**: qinzhi100@gmail.com
- **GitHub Issues**: [提交问题](https://github.com/your-repo/Thoracic-Database/issues)

---

## ⚠️ 免责声明

本系统仅用于科研数据管理，不作为临床诊断依据。使用者需自行确保数据的准确性和合规性。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

Made with ❤️ for thoracic surgery research

</div>

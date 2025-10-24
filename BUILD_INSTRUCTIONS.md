# 打包说明文档

本文档说明如何将 Thoracic-Database v2.1 打包成独立的可执行文件。

---

## 📦 打包概述

使用 **PyInstaller** 将Python应用打包成独立的可执行文件，用户无需安装Python环境即可运行。

### 支持的平台
- ✅ **Windows** (Windows 10/11, 64-bit)
- ✅ **macOS** (macOS 10.13+, Intel/Apple Silicon)
- ✅ **Linux** (Ubuntu 20.04+, 64-bit)

### 打包结果
- **Windows:** `ThoracicDatabase.exe` (~40-50MB)
- **macOS:** `ThoracicDatabase.app` (~40-50MB)
- **Linux:** `thoracic_entry` (~35-45MB)

---

## 🪟 Windows 打包

### 前置要求
1. **操作系统:** Windows 10 或 Windows 11 (64-bit)
2. **Python:** Python 3.10 或更高版本
3. **依赖库:** openpyxl, pyinstaller

### 打包步骤

#### 方法一：使用自动化脚本（推荐）

1. **打开命令提示符 (CMD) 或 PowerShell**

2. **进入项目目录**
   ```cmd
   cd path\to\Thoracic-Database-v2.1
   ```

3. **运行打包脚本**
   ```cmd
   build_windows.bat
   ```

4. **等待打包完成**
   脚本会自动：
   - 检查Python版本
   - 安装缺失的依赖
   - 清理旧的构建文件
   - 使用PyInstaller打包
   - 显示打包结果

5. **获取可执行文件**
   打包完成后，可执行文件位于：
   ```
   dist\ThoracicDatabase.exe
   ```

#### 方法二：手动打包

1. **安装依赖**
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **运行PyInstaller**
   ```cmd
   pyinstaller --clean --onefile --windowed --name ThoracicDatabase --icon=assets/app.ico --add-data "db;db" --add-data "ui;ui" --add-data "export;export" --add-data "utils;utils" --add-data "staging;staging" --add-data "assets;assets" --add-data "README.md;." --add-data "CHANGELOG_v2.1.md;." --add-data "VERSION.txt;." --hidden-import=tkinter --hidden-import=tkinter.ttk --hidden-import=tkinter.messagebox --hidden-import=tkinter.filedialog --hidden-import=sqlite3 --hidden-import=openpyxl main.py
   ```

3. **获取可执行文件**
   ```
   dist\ThoracicDatabase.exe
   ```

### 测试可执行文件

1. **双击运行** `ThoracicDatabase.exe`
2. **验证功能:**
   - 创建测试患者
   - 录入手术、病理、分子、随访数据
   - 导出Excel和CSV
   - 检查随访事件日志功能

### 分发说明

- ✅ 可以直接分发 `.exe` 文件
- ✅ 用户无需安装Python
- ✅ 双击即可运行
- ⚠️ 杀毒软件可能误报，需添加信任

---

## 🍎 macOS 打包

### 前置要求
1. **操作系统:** macOS 10.13 (High Sierra) 或更高版本
2. **Python:** Python 3.10 或更高版本
3. **依赖库:** openpyxl, pyinstaller

### 打包步骤

#### 方法一：使用自动化脚本（推荐）

1. **打开终端 (Terminal)**

2. **进入项目目录**
   ```bash
   cd /path/to/Thoracic-Database-v2.1
   ```

3. **给脚本添加执行权限**
   ```bash
   chmod +x build_macos.sh
   ```

4. **运行打包脚本**
   ```bash
   ./build_macos.sh
   ```

5. **等待打包完成**
   脚本会自动：
   - 检查Python版本
   - 安装缺失的依赖
   - 清理旧的构建文件
   - 使用PyInstaller打包
   - 显示打包结果

6. **获取应用程序**
   打包完成后，应用程序位于：
   ```
   dist/ThoracicDatabase
   ```

#### 方法二：手动打包

1. **安装依赖**
   ```bash
   pip3 install -r requirements.txt
   pip3 install pyinstaller
   ```

2. **运行PyInstaller**
   ```bash
   pyinstaller --clean --onefile --windowed --name ThoracicDatabase --icon=assets/app.ico --add-data "db:db" --add-data "ui:ui" --add-data "export:export" --add-data "utils:utils" --add-data "staging:staging" --add-data "assets:assets" --add-data "README.md:." --add-data "CHANGELOG_v2.1.md:." --add-data "VERSION.txt:." --hidden-import=tkinter --hidden-import=tkinter.ttk --hidden-import=tkinter.messagebox --hidden-import=tkinter.filedialog --hidden-import=sqlite3 --hidden-import=openpyxl main.py
   ```

3. **获取应用程序**
   ```
   dist/ThoracicDatabase
   ```

### 测试应用程序

1. **双击运行** `ThoracicDatabase`
2. **如果提示"无法打开":**
   - 打开 **系统偏好设置 > 安全性与隐私**
   - 点击 **"仍要打开"**
3. **验证功能** (同Windows)

### 分发说明

- ✅ 可以直接分发应用程序
- ✅ 用户无需安装Python
- ⚠️ 首次运行需要在安全设置中允许
- 💡 建议压缩为 `.zip` 文件分发

---

## 🐧 Linux 打包

### 前置要求
1. **操作系统:** Ubuntu 20.04+ 或其他主流发行版
2. **Python:** Python 3.10 或更高版本
3. **依赖库:** openpyxl, pyinstaller, binutils, libpython3.x

### 打包步骤

#### 使用现有spec文件

1. **安装系统依赖**
   ```bash
   sudo apt-get update
   sudo apt-get install -y binutils libpython3.11
   ```

2. **安装Python依赖**
   ```bash
   pip3 install -r requirements.txt
   pip3 install pyinstaller
   ```

3. **运行打包**
   ```bash
   pyinstaller --clean thoracic_entry.spec
   ```

4. **获取可执行文件**
   ```
   dist/thoracic_entry
   ```

### 测试可执行文件

1. **添加执行权限**
   ```bash
   chmod +x dist/thoracic_entry
   ```

2. **运行程序**
   ```bash
   ./dist/thoracic_entry
   ```

3. **验证功能** (同Windows)

### 分发说明

- ✅ 可以直接分发可执行文件
- ✅ 用户无需安装Python
- ⚠️ 需要确保目标系统有相同的glibc版本
- 💡 建议在目标系统上重新打包

---

## ⚠️ 常见问题

### Q1: 打包后文件很大？
**A:** PyInstaller会打包Python解释器和所有依赖库，通常40-50MB是正常的。

### Q2: Windows Defender报毒？
**A:** PyInstaller打包的程序可能被误报。解决方法：
- 添加到Windows Defender排除列表
- 使用代码签名证书签名
- 向杀毒软件厂商报告误报

### Q3: macOS提示"已损坏"？
**A:** 这是因为应用未签名。解决方法：
```bash
xattr -cr /path/to/ThoracicDatabase
```

### Q4: 打包失败提示缺少模块？
**A:** 在打包命令中添加 `--hidden-import=模块名`

### Q5: 运行时提示找不到文件？
**A:** 检查 `--add-data` 参数是否正确添加了所有资源文件。

### Q6: 不同平台能否交叉编译？
**A:** 不能。必须在目标平台上打包：
- Windows可执行文件必须在Windows上打包
- macOS应用必须在macOS上打包
- Linux可执行文件必须在Linux上打包

---

## 📊 打包参数说明

### 常用参数

| 参数 | 说明 |
| :--- | :--- |
| `--onefile` | 打包成单个可执行文件 |
| `--windowed` | 不显示控制台窗口（GUI应用） |
| `--name` | 指定可执行文件名称 |
| `--icon` | 指定应用图标 |
| `--add-data` | 添加资源文件 |
| `--hidden-import` | 添加隐藏导入的模块 |
| `--clean` | 清理缓存后重新打包 |

### 数据文件格式

- **Windows:** `源路径;目标路径`
- **macOS/Linux:** `源路径:目标路径`

### 示例
```bash
# Windows
--add-data "db;db"

# macOS/Linux
--add-data "db:db"
```

---

## 🔧 高级配置

### 使用spec文件

PyInstaller支持使用 `.spec` 文件进行高级配置：

1. **生成spec文件**
   ```bash
   pyi-makespec --onefile --windowed main.py
   ```

2. **编辑spec文件**
   修改 `datas`, `hiddenimports` 等配置

3. **使用spec文件打包**
   ```bash
   pyinstaller thoracic_entry.spec
   ```

### 优化打包大小

1. **使用虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

2. **排除不需要的模块**
   ```bash
   --exclude-module=模块名
   ```

3. **使用UPX压缩**
   ```bash
   --upx-dir=/path/to/upx
   ```

---

## 📝 打包清单

打包前请确认：

- [ ] 所有功能正常运行
- [ ] requirements.txt包含所有依赖
- [ ] 资源文件（assets/）完整
- [ ] 图标文件存在
- [ ] 文档文件完整
- [ ] 版本号正确

打包后请测试：

- [ ] 程序能正常启动
- [ ] 所有标签页功能正常
- [ ] 数据库创建和读写正常
- [ ] 导出功能正常
- [ ] 随访事件日志功能正常

---

## 📚 参考资源

- **PyInstaller官方文档:** https://pyinstaller.org/
- **PyInstaller GitHub:** https://github.com/pyinstaller/pyinstaller
- **常见问题:** https://pyinstaller.org/en/stable/common-problems.html

---

**版本:** v2.1  
**最后更新:** 2025年10月23日

**本项目所有代码均由ChatGPT和Manus完成。**


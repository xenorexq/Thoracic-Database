# Package Guide - How to Build EXE

## 🚀 EASIEST METHOD: Use the build script

### Windows:
Double-click `build_exe.bat` or run in Command Prompt:
```bash
build_exe.bat
```

### Any OS (Windows/Linux/Mac):
```bash
python build_exe.py
```

The script will automatically:
1. Install dependencies (pyinstaller, openpyxl)
2. Clean previous builds
3. Build the executable
4. Show you where the exe is located

---

## Method 1: Using spec file

```bash
# 1. Install dependencies
pip install pyinstaller openpyxl

# 2. Build using spec file
pyinstaller thoracic_entry.spec

# 3. Get the exe
# Located at: dist/thoracic_entry.exe
```

---

## Method 2: Using command line

### For Windows:
```bash
pyinstaller --noconfirm --clean ^
  --onefile ^
  --windowed ^
  --name thoracic_entry ^
  --icon=assets/app.ico ^
  --add-data "assets;assets" ^
  --paths . ^
  --collect-submodules ui ^
  --collect-submodules db ^
  --collect-submodules utils ^
  --collect-submodules staging ^
  --collect-submodules export ^
  main.py
```

### For Linux/Mac:
```bash
pyinstaller --noconfirm --clean \
  --onefile \
  --windowed \
  --name thoracic_entry \
  --icon=assets/app.ico \
  --add-data "assets:assets" \
  --paths . \
  --collect-submodules ui \
  --collect-submodules db \
  --collect-submodules utils \
  --collect-submodules staging \
  --collect-submodules export \
  main.py
```

---

## 🔧 Troubleshooting "ModuleNotFoundError: No module named 'utils.validators'"

This error means PyInstaller didn't include the submodules. Here are solutions:

### Solution 1: Use the build scripts (RECOMMENDED)
- `build_exe.bat` (Windows)
- `build_exe.py` (Any OS)

These scripts use `--collect-submodules` which automatically finds ALL modules.

### Solution 2: Verify you're using the correct command
Make sure you include these flags:
```
--collect-submodules ui
--collect-submodules db
--collect-submodules utils
--collect-submodules staging
--collect-submodules export
```

### Solution 3: Try --onedir instead of --onefile
If --onefile keeps failing, use --onedir:
```bash
pyinstaller --onedir --windowed ... (rest of the flags)
```

This creates a folder with the exe and all dependencies, which is more reliable.

### Solution 4: Check your directory structure
Make sure all folders have `__init__.py`:
```
thoracic_entry_clean/
├── ui/__init__.py          ← Must exist
├── db/__init__.py          ← Must exist
├── utils/__init__.py       ← Must exist
├── staging/__init__.py     ← Must exist
└── export/__init__.py      ← Must exist
```

### Solution 5: Use console mode to see errors
Change `--windowed` to `--console` to see error messages:
```bash
pyinstaller --console ... (rest of the flags)
```

---

## Testing the built exe

1. Copy `dist/thoracic_entry.exe` to a new folder
2. Double-click to run
3. The program will create `thoracic.db` automatically
4. Start using!

---

## Common Issues

**Q: Still getting module errors after trying everything?**
A: Try this nuclear option - manually copy all .py files:
```bash
pyinstaller --noconfirm --clean ^
  --onedir ^
  --windowed ^
  --name thoracic_entry ^
  --icon=assets/app.ico ^
  --add-data "assets;assets" ^
  --add-data "ui;ui" ^
  --add-data "db;db" ^
  --add-data "utils;utils" ^
  --add-data "staging;staging" ^
  --add-data "export;export" ^
  main.py
```

**Q: The exe is large (>50MB)?**
A: Normal. It includes Python interpreter and all dependencies.

**Q: Want to see build details?**
A: Add `--log-level DEBUG` flag.

**Q: Build works but exe crashes on startup?**
A: Use `--console` instead of `--windowed` to see error messages.

---

## Clean up

After building, you can delete:
- `build/` folder
- `__pycache__/` folders
- `*.pyc` files
- `thoracic_entry.spec` (if you used command line method)

Keep only `dist/thoracic_entry.exe` or `dist/thoracic_entry/` folder.

---

## File Checklist

Before building, verify these files exist:
- ✅ main.py
- ✅ requirements.txt
- ✅ assets/app.ico
- ✅ ui/__init__.py
- ✅ db/__init__.py
- ✅ utils/__init__.py
- ✅ staging/__init__.py
- ✅ export/__init__.py

If any `__init__.py` is missing, create an empty file:
```bash
# Windows
type nul > ui\__init__.py

# Linux/Mac
touch ui/__init__.py
```


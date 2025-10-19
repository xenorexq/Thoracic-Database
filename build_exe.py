#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-platform build script for thoracic_entry
Usage: python build_exe.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print status"""
    print(f"\n[{description}]")
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {description} failed!")
        print(result.stderr)
        return False
    return True

def main():
    print("=" * 50)
    print("Thoracic Entry - Build Script")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required, you have {sys.version}")
        return 1
    
    print(f"Python version: {sys.version}")
    
    # Step 1: Install dependencies
    print("\n[1/4] Installing dependencies...")
    if not run_command([sys.executable, "-m", "pip", "install", "pyinstaller", "openpyxl"], 
                       "Install dependencies"):
        return 1
    
    # Step 2: Clean previous build
    print("\n[2/4] Cleaning previous build...")
    for dir_name in ["build", "dist", "__pycache__"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removed {dir_name}/")
    
    # Step 3: Build
    print("\n[3/4] Building executable...")
    
    # Determine separator for --add-data based on OS
    separator = ";" if sys.platform == "win32" else ":"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "thoracic_entry",
        "--icon=assets/app.ico",
        f"--add-data=assets{separator}assets",
        "--paths", ".",
        "--collect-submodules", "ui",
        "--collect-submodules", "db",
        "--collect-submodules", "utils",
        "--collect-submodules", "staging",
        "--collect-submodules", "export",
        "main.py"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode != 0:
        print("\nERROR: Build failed!")
        return 1
    
    # Step 4: Check output
    print("\n[4/4] Checking output...")
    
    exe_name = "thoracic_entry.exe" if sys.platform == "win32" else "thoracic_entry"
    exe_path = Path("dist") / exe_name
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 50)
        print("SUCCESS!")
        print("=" * 50)
        print(f"\nExecutable location: {exe_path.absolute()}")
        print(f"File size: {size_mb:.1f} MB")
        print("\nYou can now:")
        print("  1. Copy the exe to any computer")
        print("  2. Double-click to run (no Python needed)")
        print("  3. Program will create thoracic.db automatically")
        return 0
    else:
        print("\nERROR: Executable was not created!")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


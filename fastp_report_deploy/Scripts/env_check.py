#!/usr/bin/env python3
import sys
import subprocess

# 包列表：(导入名, pip包名, 是否标准库)
PACKAGES = [
    ("os", None, True), ("base64", None, True), ("re", None, True),
    ("subprocess", None, True), ("argparse", None, True), ("pathlib", None, True),
    ("time", None, True), ("json", None, True), ("typing", None, True),
    ("yaml", "pyyaml", False), ("matplotlib", "matplotlib", False),
    ("numpy", "numpy", False), ("pandas", "pandas", False), 
    ("jinja2", "jinja2", False), ("playwright", "playwright", False),
    ("PyPDF2", "PyPDF2", False)  # 添加 PyPDF2 检查
]

failed = False
to_install = []
playwright_installed = False

print("检查包依赖...")
for import_name, pip_name, is_stdlib in PACKAGES:
    try:
        __import__(import_name)
        print(f"✓ {import_name}")
        # 记录playwright是否已安装
        if import_name == "playwright":
            playwright_installed = True
    except:
        print(f"✗ {import_name}")
        failed = True
        if not is_stdlib and pip_name:
            to_install.append(pip_name)

# 如果playwright已安装，检查浏览器
if playwright_installed:
    try:
        # 尝试导入playwright并检查是否有浏览器
        import playwright
        # 简单检查playwright命令行工具是否可用
        result = subprocess.run(["playwright", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ playwright 浏览器已安装")
        else:
            print("⚠ playwright 浏览器未安装")
            print("  请运行: playwright install chromium")
    except:
        print("⚠ playwright 检查失败")

print()
if failed:
    print("✗ 环境检查失败")
    if to_install:
        print(f"需要安装: pip install {' '.join(to_install)}")
        if "playwright" in to_install:
            print("\n安装playwright后还需要运行:")
            print("playwright install chromium")
    sys.exit(1)
else:
    print("✓ 所有包已安装")
    sys.exit(0)